# PostgreSQL best practices, and a bronze → silver → gold pipeline

## Part 1: Best practices

### Standard columns on every table

`updated_at` alone isn't enough. A `DEFAULT now()` sets the value on INSERT but **doesn't change it on UPDATE**, so you need a trigger:

```sql
CREATE TABLE silver.executive_comp (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- business columns ...
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    load_id     bigint      NOT NULL REFERENCES meta.load_runs(load_id)   -- lineage
);

CREATE OR REPLACE FUNCTION meta.set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

CREATE TRIGGER trg_executive_comp_updated_at
BEFORE UPDATE ON silver.executive_comp
FOR EACH ROW EXECUTE FUNCTION meta.set_updated_at();
```

Django's `auto_now=True` updates the column only when changes go through the ORM. Raw SQL and ETL scripts bypass it, so the trigger is the dependable option.

Other useful standard columns:
- **`created_by` / `updated_by`**: who made the change, useful for SOC 2 audit trails.
- **`load_id` / `source_file`**: which pipeline run and which file the row came from. This is lineage: "where did this number come from?"
- **`deleted_at`** (soft delete): only where you really need to undo deletes or keep history. Every query then has to filter it out.

### Data types

| Do | Avoid | Why |
| --- | --- | --- |
| `timestamptz` | `timestamp` | Stores an absolute moment; avoids time-zone bugs |
| `numeric(14,2)` for money | `float` / `real` | Floats give rounding errors, and these are compensation figures |
| `text` (+ a `CHECK` on length if needed) | `varchar(n)` everywhere | Same performance in Postgres; fewer migrations |
| `bigint GENERATED ALWAYS AS IDENTITY` | `serial` | The modern standard; avoids `serial` quirks |
| UUID keys **only when needed** (IDs from several systems, IDs exposed in URLs) | UUIDv4 on huge tables | Random UUIDs scatter index writes; prefer `uuidv7()` (time-ordered, built in from Postgres 18) |
| `jsonb` for truly variable data | Putting everything in JSON | You lose types, constraints and good statistics |
| `date` for fiscal-year-end dates | Strings like `'2025-12-31'` | Correct comparisons and validation |

### Constraints: let the database enforce correctness

```sql
CONSTRAINT uq_exec_year UNIQUE (company_id, executive_name, fiscal_year),
CONSTRAINT ck_salary_nonneg CHECK (salary >= 0),
CONSTRAINT ck_fy CHECK (fiscal_year BETWEEN 1990 AND 2100)
```

- `NOT NULL` by default; allow NULL only when it means something.
- Foreign keys between core tables.
- **Index your foreign key columns.** Postgres doesn't do it automatically, and unindexed FKs make joins and deletes slow.

### Indexing

- Index what you filter, join and sort on. Look at real queries with `pg_stat_statements` and `EXPLAIN (ANALYZE, BUFFERS)`.
- **Composite indexes:** equality columns first, then range columns: `(company_id, fiscal_year)`.
- **Partial indexes** for hot subsets: `WHERE status = 'FAILURE'`.
- **Covering indexes** with `INCLUDE (...)` to allow index-only scans.
- Don't over-index; every index slows writes. Periodically drop indexes that are never used (`pg_stat_user_indexes.idx_scan = 0`).

### Organization and naming

- **Schemas** as namespaces and security boundaries: `bronze`, `silver`, `gold`, `meta`.
- Lower snake_case names, singular or plural consistently, and constraint names with prefixes: `pk_`, `fk_`, `uq_`, `ck_`, `ix_`.

### Schema changes (migrations)

- All DDL goes through **versioned migrations** (Django migrations, Alembic, or Flyway). No manual changes in production, and every migration gets a reviewed PR. That's also SOC 2 change-management evidence.
- Changes that don't lock tables for long:
  - `CREATE INDEX CONCURRENTLY` (doesn't block writes).
  - Add a column as nullable or with a constant default first (fast since Postgres 11), backfill in batches, then add `NOT NULL`.
  - Set `SET lock_timeout = '5s'` in migrations so a blocked change gives up instead of freezing the application.

### Security

- Separate roles: an **owner** role (runs migrations), an **app** role (reads and writes data only), a **read-only** role (analysts and BI). No application connects as superuser.
- `REVOKE ALL ON SCHEMA public FROM PUBLIC;` then grant privileges schema by schema.
- Use row-level security if different users must see different clients' data.
- Use TLS for connections and keep passwords out of Git. `pgaudit` can log access when you need an audit trail.

### Operations

- **Backups:** pgBackRest or WAL archiving for **point-in-time recovery**, and **test restores** regularly. An untested backup isn't a backup.
- **Autovacuum:** leave it on. Tune it for large, frequently updated tables, and monitor dead tuples and bloat.
- **Timeouts:** set `statement_timeout` and `idle_in_transaction_session_timeout` for application roles, so a forgotten transaction can't hold locks for hours.
- **Connection pooling:** PgBouncer or an application pool. Postgres connections are processes and expensive.
- **Bulk loading:** use `COPY` or batched inserts, never row-by-row inserts.
- **Large time-based tables:** partition by date, which makes dropping old data and maintenance cheap.
- **Monitoring:** `pg_stat_statements`, slow-query logging (`log_min_duration_statement`), disk space, replication lag and locks.

## Part 2: Bronze → silver → gold in Postgres

The idea, usually called the **medallion architecture**, is three layers with increasing trust:

| Layer | Schema | Contents | Rule |
| --- | --- | --- | --- |
| **Bronze** | `bronze` | Raw data exactly as received, plus load metadata | Append-only. Loading never fails on content |
| **Silver** | `silver` | Cleaned, typed, deduplicated, validated, conformed | Constraints enforced; bad rows go to quarantine |
| **Gold** | `gold` | Business-ready aggregates and data marts for consultants | Views / materialized views; easy to query |

Applied to Data Hub, with consultant Excel files as the source:

### Step 0: Load tracking (`meta`)

```sql
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE meta.load_runs (
    load_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file   text        NOT NULL,
    file_sha256   text        NOT NULL,
    template      text,                       -- detected template version
    status        text        NOT NULL DEFAULT 'STARTED'
                  CHECK (status IN ('STARTED','BRONZE_DONE','SILVER_DONE','FAILED')),
    rows_bronze   int, rows_silver int, rows_rejected int,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    error_message text,
    CONSTRAINT uq_file_hash UNIQUE (file_sha256)   -- the same file is never loaded twice
);
```

### Step 1: Bronze. Store raw rows as JSONB.

Consultant templates differ, so bronze stores **each row as JSONB**, keyed by the header names. That way the load never fails because of a new column or a bad value.

```sql
CREATE TABLE bronze.excel_rows (
    load_id     bigint NOT NULL REFERENCES meta.load_runs(load_id),
    sheet_name  text   NOT NULL,
    row_num     int    NOT NULL,
    raw         jsonb  NOT NULL,              -- {"Executive": "Jane Doe", "Salary": "450,000", ...}
    ingested_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (load_id, sheet_name, row_num)
);
```

The Python side (in a Celery task) reads the workbook in streaming mode and uses `COPY` to load fast:

```python
with conn.cursor().copy(
    "COPY bronze.excel_rows (load_id, sheet_name, row_num, raw) FROM STDIN"
) as copy:
    for i, row in enumerate(rows, start=2):
        copy.write_row((load_id, sheet, i, json.dumps(dict(zip(headers, row)), default=str)))
```

### Step 2: Silver. Typed, validated, deduplicated.

A helper converts text to a number, returning NULL instead of raising an error:

```sql
CREATE OR REPLACE FUNCTION meta.to_numeric_or_null(v text) RETURNS numeric
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  RETURN replace(replace(trim(v), ',', ''), '$', '')::numeric;
EXCEPTION WHEN others THEN
  RETURN NULL;
END $$;
```

```sql
CREATE TABLE silver.executive_comp (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name   text          NOT NULL,
    executive_name text          NOT NULL,
    fiscal_year    int           NOT NULL CHECK (fiscal_year BETWEEN 1990 AND 2100),
    salary         numeric(14,2) CHECK (salary >= 0),
    bonus          numeric(14,2) CHECK (bonus  >= 0),
    load_id        bigint        NOT NULL REFERENCES meta.load_runs(load_id),
    created_at     timestamptz   NOT NULL DEFAULT now(),
    updated_at     timestamptz   NOT NULL DEFAULT now(),
    CONSTRAINT uq_exec_comp UNIQUE (company_name, executive_name, fiscal_year)
);

CREATE TABLE silver.rejects (
    load_id   bigint NOT NULL,
    sheet_name text, row_num int,
    raw       jsonb  NOT NULL,
    reason    text   NOT NULL,
    rejected_at timestamptz NOT NULL DEFAULT now()
);
```

The transform runs **for one load_id, in one transaction**, so it's all-or-nothing and safe to rerun:

```sql
BEGIN;

-- 1. Parse and validate into a temporary table
CREATE TEMP TABLE parsed ON COMMIT DROP AS
SELECT b.load_id, b.sheet_name, b.row_num, b.raw,
       nullif(trim(b.raw->>'Company'), '')                  AS company_name,
       nullif(trim(b.raw->>'Executive'), '')                AS executive_name,
       meta.to_numeric_or_null(b.raw->>'Fiscal Year')::int  AS fiscal_year,
       meta.to_numeric_or_null(b.raw->>'Salary')            AS salary,
       meta.to_numeric_or_null(b.raw->>'Bonus')             AS bonus
FROM bronze.excel_rows b
WHERE b.load_id = %(load_id)s;

-- 2. Bad rows go to quarantine, each with a reason
INSERT INTO silver.rejects (load_id, sheet_name, row_num, raw, reason)
SELECT load_id, sheet_name, row_num, raw,
       CASE WHEN company_name   IS NULL THEN 'missing company'
            WHEN executive_name IS NULL THEN 'missing executive'
            WHEN fiscal_year    IS NULL THEN 'bad fiscal year'
            WHEN salary < 0              THEN 'negative salary' END
FROM parsed
WHERE company_name IS NULL OR executive_name IS NULL
   OR fiscal_year IS NULL OR salary < 0;

-- 3. Good rows: dedupe within the file, then upsert (writes only if something changed)
INSERT INTO silver.executive_comp
       (company_name, executive_name, fiscal_year, salary, bonus, load_id)
SELECT DISTINCT ON (company_name, executive_name, fiscal_year)
       company_name, executive_name, fiscal_year, salary, bonus, load_id
FROM parsed
WHERE company_name IS NOT NULL AND executive_name IS NOT NULL
  AND fiscal_year IS NOT NULL AND coalesce(salary, 0) >= 0
ORDER BY company_name, executive_name, fiscal_year, row_num DESC   -- last row wins
ON CONFLICT (company_name, executive_name, fiscal_year) DO UPDATE
SET salary  = EXCLUDED.salary,
    bonus   = EXCLUDED.bonus,
    load_id = EXCLUDED.load_id
WHERE (silver.executive_comp.salary, silver.executive_comp.bonus)
      IS DISTINCT FROM (EXCLUDED.salary, EXCLUDED.bonus);

UPDATE meta.load_runs SET status = 'SILVER_DONE', finished_at = now()
WHERE load_id = %(load_id)s;

COMMIT;
```

(The `updated_at` trigger from Part 1 keeps `updated_at` current on the upserted rows.)

If you need **history** (for example, pay restated in a later filing), make silver an **SCD Type 2** table: add `valid_from`, `valid_to` and `is_current`. On a change, close the old row and insert a new one rather than updating in place.

### Step 3: Gold. Business-ready data.

```sql
CREATE MATERIALIZED VIEW gold.comp_benchmarks AS
SELECT fiscal_year,
       count(*)                                                 AS n_execs,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY salary)     AS salary_p25,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY salary)     AS salary_p50,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY salary)     AS salary_p75,
       avg(salary + coalesce(bonus, 0))                         AS avg_cash_comp
FROM silver.executive_comp
GROUP BY fiscal_year;

-- A unique index is required for REFRESH ... CONCURRENTLY
CREATE UNIQUE INDEX ux_comp_benchmarks ON gold.comp_benchmarks (fiscal_year);

REFRESH MATERIALIZED VIEW CONCURRENTLY gold.comp_benchmarks;   -- readers aren't blocked
```

How to choose the gold form:
- **Plain view:** always current, computed at query time. Use it when the query is fast.
- **Materialized view:** precomputed and fast to read. Refresh it after loads or on a schedule.
- **Real gold table:** when you need incremental updates or indexes on very large aggregates.

### Step 4: Orchestration with Celery

```python
from celery import chain

chain(
    load_bronze.s(file_path),      # registers load_runs (rejects duplicate hash), COPY rows → returns load_id
    build_silver.s(),              # runs the transform SQL for that load_id
    refresh_gold.si(),             # REFRESH ... CONCURRENTLY
).delay()
```

Add a **Beat** job that refreshes gold nightly as a safety net, and another that alerts on `load_runs` stuck in `STARTED` or with a high reject count.

### Why this design holds up

- **Bronze never loses data.** You can always rebuild silver from bronze when the rules change, without asking consultants for their files again.
- **Each layer is rerunnable:** the file hash blocks duplicate loads, silver runs per load_id in one transaction, and gold rebuilds from silver.
- **Traceability:** a gold number → silver rows → `load_id` → the source file and its row number. That's the audit trail for client-facing numbers and for SOC 2.
- **Data quality is visible:** the `silver.rejects` table is a ready-made report to send back to consultants: "row 14: salary is text."
- **Separate permissions:** consultants and BI tools get read access to `gold` only, the pipeline role writes to `bronze` and `silver`, and nobody else touches raw data.

**Interview one-liner:** "I'd do medallion in Postgres with schemas: bronze holds raw JSONB plus load metadata and is append-only, silver is typed and constrained with a reject table, upserted per load in one transaction, and gold is materialized views refreshed concurrently. Celery chains the layers, and everything traces back to a load_id and a source file."
