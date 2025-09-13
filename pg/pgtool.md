# There is managed Postgres on Azure Cloud.
The database has several huge always growing tables with timestamptz column.
We are approaching Postgres instance capacity.
Some Postgres tables are created with timescaledb extension.
What is the best practice to archive the old data ( 90 days back fro now) in such tables?


## ChatGPT

Short version: move those “always-growing” tables to **time-based partitions** and enforce a **90-day hot-data retention policy**. Keep ≤90 days in Postgres for speed and cost, and **archive partitions older than 90 days** to cheaper storage (ADLS/S3/Snowflake) before dropping them. This is the most battle-tested pattern and it scales smoothly.

Below is a practical, copy-pasteable plan you can run on Azure Database for PostgreSQL (managed). It uses **native declarative partitioning** (works on Postgres 11+) plus `pg_cron` to automate creation and eviction. If your service tier also supports TimescaleDB, I include that option at the end.

---

# 1) Target state (hot/warm-cold split)

* **Hot (Postgres):** last 90 days, in a **partitioned** table by `timestamptz` (daily or monthly, pick based on volume).
* **Warm/Cold (Archive):** older than 90 days, **compressed parquet/csv in ADLS Gen2** (or Snowflake), with an optional view/FDW to query on demand.

Benefits:

* Inserts & queries stay fast due to partition pruning.
* Autovacuum scales better (per-partition).
* Dropping old data is a fast `DROP TABLE PARTITION`, not a huge `DELETE`.

---

# 2) Partition design

Choose **RANGE partitioning on your time column** (here: `event_ts timestamptz`).
Rule of thumb:

* **Daily partitions** if you ingest > 5–10M rows/day or need frequent backfills.
* **Monthly partitions** if daily volume is modest.

Example uses **daily**. Adjust `"INTERVAL '1 day'"` and names if you prefer monthly.

```sql
-- 2.1 New partitioned table (same columns as your current big table)
CREATE TABLE weavix.silver.mytable_part
(
  -- your actual columns:
  id           bigint       NOT NULL,
  event_ts     timestamptz  NOT NULL,
  payload      jsonb,
  -- ... indexes/constraints will be added per partition
  PRIMARY KEY (id, event_ts)  -- example; choose a realistic PK for your workload
)
PARTITION BY RANGE (event_ts);
```

Create a **rolling window of partitions** (e.g., ±120 days around “now” to cover backfills):

```sql
DO $$
DECLARE
  d date := date_trunc('day', now())::date - INTERVAL '120 days';
  stop date := date_trunc('day', now())::date + INTERVAL '30 days';
  part_name text;
BEGIN
  WHILE d < stop LOOP
    part_name := format('mytable_part_%s', to_char(d, 'YYYYMMDD'));
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS weavix.silver.%I
         PARTITION OF weavix.silver.mytable_part
         FOR VALUES FROM (%L) TO (%L);',
      part_name,
      d::timestamptz, (d + INTERVAL '1 day')::timestamptz
    );
    -- Optional: create per-partition indexes commonly used by queries
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I_event_ts_idx ON weavix.silver.%I (event_ts);',
                   part_name || '_ts', part_name);
    d := d + INTERVAL '1 day';
  END LOOP;
END $$;
```

---

# 3) Migrate existing big table → partitioned table

You have two common migration patterns:

### A) Shadow-copy + rename (safest)

1. **Create** `mytable_part` (above) and pre-create partitions for full history (loop by month/day, as needed).
2. **Copy in batches** from old heap table to the new partitioned one (keeps WAL & locks sane):

```sql
-- Repeat in reasonable time buckets; adjust WHERE ranges to your history.
INSERT INTO weavix.silver.mytable_part
SELECT * 
FROM   weavix.silver.mytable_old
WHERE  event_ts >= '2024-01-01' AND event_ts < '2024-02-01';
-- …repeat for each month/day
```

3. **Swap names** during a brief maintenance window:

```sql
ALTER TABLE weavix.silver.mytable_old RENAME TO mytable_old_bk;
ALTER TABLE weavix.silver.mytable_part RENAME TO mytable;
```

### B) Attach existing chunks (only if you already had CHECK constraints)

If your old table has **per-range child tables with CHECKs**, you can `ALTER TABLE ... ATTACH PARTITION ...`. Most monolithic tables don’t—so A) is typically easier.

---

# 4) Enforce 90-day retention (create & drop jobs)

Use `pg_cron` to:

* create upcoming partitions daily,
* archive & drop partitions older than 90 days.

### 4.1 Helper functions

```sql
-- Create tomorrow's partition each night
CREATE OR REPLACE FUNCTION weavix.silver.ensure_tomorrow_partition() RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  d date := (date_trunc('day', now()) + INTERVAL '1 day')::date;
  part_name text := format('mytable_%s', to_char(d, 'YYYYMMDD'));
BEGIN
  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS weavix.silver.%I
       PARTITION OF weavix.silver.mytable
       FOR VALUES FROM (%L) TO (%L);',
    part_name, d::timestamptz, (d + INTERVAL '1 day')::timestamptz
  );
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I_ts ON weavix.silver.%I (event_ts);',
                 part_name || '_ts', part_name);
END $$;

-- Return partitions older than 90 days (name & range) so your external job can export them
CREATE OR REPLACE VIEW weavix.silver.mytable_old_partitions AS
SELECT
  c.relname               AS partition_name,
  to_char((pg_get_expr(p.boundexpr, p.parsedatatype)), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS from_bound,
  to_char((pg_get_expr(p.boundexpr, p.parsedatatype) + interval '1 day'), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS to_bound
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_partitioned_table pt ON pt.partrelid = (SELECT oid FROM pg_class WHERE relname = 'mytable' AND relnamespace = n.oid)
JOIN pg_inherits i ON i.inhparent = pt.partrelid AND i.inhrelid = c.oid
JOIN pg_partition p ON p.partrelid = c.oid
WHERE n.nspname = 'weavix' AND c.relname ~ '^mytable_\d{8}$'   -- if regex not desired, filter by relname prefix and length
  AND (pg_get_expr(p.boundexpr, p.parsedatatype))::timestamptz < now() - interval '90 days';
```

> If your Postgres version doesn’t expose those internal catalogs the same way, you can derive old partitions simply by **name prefix** + **date suffix** and compare to `current_date - 90`.

### 4.2 Cron the tasks

```sql
-- Create tomorrow’s partition at 00:05 daily
SELECT cron.schedule('ensure_tomorrow_mytable', '5 0 * * *',
  $$SELECT weavix.silver.ensure_tomorrow_partition();$$);

-- (External step) Nightly: for each partition in weavix.silver.mytable_old_partitions
-- 1) export to ADLS/Snowflake (CSV/Parquet)
-- 2) then call this SQL to drop:
--    EXECUTE format('DROP TABLE IF EXISTS weavix.silver.%I', partition_name);

-- You can wrap step #2 into a function:
CREATE OR REPLACE FUNCTION weavix.silver.drop_partitions_older_than_90_days() RETURNS void LANGUAGE plpgsql AS $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname AS partition_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname='weavix' AND c.relname LIKE 'mytable_%'
      AND substring(c.relname from 'mytable_(\d{8})')::int < to_char(now() - interval '90 days','YYYYMMDD')::int
  LOOP
    RAISE NOTICE 'Dropping %', r.partition_name;
    EXECUTE format('DROP TABLE IF EXISTS weavix.silver.%I', r.partition_name);
  END LOOP;
END $$;

-- Schedule the drop (after your archive/export completes)
SELECT cron.schedule('drop_old_mytable', '30 1 * * *',  -- 01:30 nightly
  $$SELECT weavix.silver.drop_partitions_older_than_90_days();$$);
```

> Important: **Export first, drop second.** You can drive the export with your existing pipelines (ADF/Databricks/Snowflake “COPY INTO”) using the per-partition time range (or simply the partition’s name-derived date).

---

# 5) Query patterns (get pruning for free)

* Always filter (or join) on `event_ts` (the partition key).
  Postgres will prune partitions automatically when it sees the range.
* For analysts, provide a **stable view** so they don’t need to care about partition names:

```sql
CREATE OR REPLACE VIEW weavix.silver.mytable_last_90d AS
SELECT * FROM weavix.silver.mytable
WHERE event_ts >= now() - INTERVAL '90 days';
```

Optionally create a **federated view** that `UNION ALL`s hot data (Postgres) with an external table (Snowflake/ADLS) for old slices, if you need single-pane access to history.

---

# 6) Indexing & maintenance

* Prefer **local indexes** per partition (created automatically when you define them on each child).
  Keep them minimal (e.g., `(event_ts)`, plus any highly-selective business keys).
* Keep an eye on **autovacuum** thresholds per partition. Because partitions are smaller, vacuum works better and doesn’t block the entire table.
* Consider a **fillfactor** tweak if you have updates; append-only workloads usually don’t need it.
* **Avoid `DELETE` for retention**—`DROP PARTITION` is instantaneous from the user’s perspective.

---

# 7) Archiving formats & tools

* **ADLS Gen2 + Parquet** is great for cost/perf (columnar, compressed).
  Paths like: `abfss://telemetry@yourlake.dfs.core.windows.net/weavix/silver/mytable/ingest_dt=YYYY-MM-DD/part-*.parquet`
* Export methods:

  * Databricks/Spark reading via JDBC then writing Parquet.
  * ADF copy activity (JDBC → ADLS Parquet).
  * Your existing **`pgtool.sh` / `pgtool.py`** to CSV.gz per partition date, then convert to Parquet (optional).

---

# 8) TimescaleDB (if your tier allows the extension)

If you can enable TimescaleDB:

* `SELECT create_hypertable('weavix.silver.mytable', 'event_ts');`
* **Retention policy**: `SELECT add_retention_policy('weavix.silver.mytable', INTERVAL '90 days');`
* **Compression** for older chunks (huge storage wins):

  ```sql
  ALTER TABLE weavix.silver.mytable SET (timescaledb.compress, timescaledb.compress_segmentby = 'some_dim');
  SELECT add_compression_policy('weavix.silver.mytable', INTERVAL '7 days');
  ```
* You still can **export chunks** older than 90 days to ADLS before dropping, using chunk metadata.

If Timescale isn’t available in your Azure plan, stick with native partitioning as above—it’s solid.

---

# 9) Safety & rollout checklist

* [ ] Create partitioned twin table in **staging**, validate queries & explain plans (pruning).
* [ ] Backfill in batches; compare counts and sample checksums vs. old table.
* [ ] Swap names during a quiet window; update writers to point at the new table.
* [ ] Turn on cron jobs (create tomorrow’s partition; nightly archive+drop).
* [ ] Add **alerts** for: missing future partition, failed archive, or unusually big partitions.

---

If you want, I can:

* generate the **exact SQL** for your table(s) given schema/columns,
* provide an **ADF/Databricks** job that exports a partition to ADLS as **Parquet**,
* or adapt your `pgtool.py` to automatically iterate **partitions older than 90 days**: export → verify → drop.


Short answer: you’re right to be cautious. On **Azure Database for PostgreSQL (Flexible Server)**, TimescaleDB is available but **feature support can lag and certain features (including compression in some versions/tiers) may not be available or reliable**. Multiple Microsoft Q\&A threads and community posts note gaps and version friction around TimescaleDB on Azure-managed Postgres, so treating compression as “not guaranteed” on Flexible Server is prudent. ([Microsoft Learn][1])

Given that, here’s a safe, proven archiving pattern that works great **without** Timescale compression:

# Best-practice plan (no Timescale compression required)

1. Partition by time & keep only 90 days “hot” in Postgres

   * If you already use Timescale **hypertables**, use **retention** (drop old chunks) but skip compression policies.

     ```sql
     -- If you have a hypertable already:
     -- keep only 90 days in Postgres
     SELECT add_retention_policy('weavix.silver.mytable', INTERVAL '90 days');
     ```

     If Timescale’s retention isn’t available in your Azure plan, do **native declarative partitioning** on `timestamptz` and drop old partitions instead (very fast vs. DELETE).

2. Export partitions/chunks older than 90 days to cheap storage, then drop

   * Nightly job:

     * Find partitions/chunks < now() - 90 days
     * **Export to ADLS Gen2** as **Parquet** (or CSV.gz)
     * Verify counts → **DROP** partition/chunk
   * Tools that work well on Azure:

     * **ADF** (JDBC → ADLS Parquet), or
     * **Databricks**/**Spark** (read via JDBC, write Parquet), or
     * Your `pgtool.py`/`.sh` to stream **CSV.gz** per day/month, then (optionally) a small Spark/ADF step to convert to Parquet.

3. Keep a convenience view for analysts

   ```sql
   CREATE OR REPLACE VIEW weavix.silver.mytable_last_90d AS
   SELECT * FROM weavix.silver.mytable
   WHERE event_ts >= now() - INTERVAL '90 days';
   ```

4. Optional: downsample before archiving

   * Use **continuous aggregates** (if available) or plain SQL jobs to persist daily/weekly rollups you *do* want to keep hot. Store the raw >90d in ADLS only.

5. Automate with `pg_cron`

   * Create tomorrow’s partition (or ensure future chunks)
   * Nightly archive+drop >90d
   * Alert if a future partition/chunk is missing or an export fails

---

## Concrete starter templates

### A) Native Postgres (no Timescale features assumed)

* Partitioned table by day:

```sql
CREATE TABLE weavix.silver.mytable_part (LIKE weavix.silver.mytable INCLUDING ALL)
PARTITION BY RANGE (event_ts);

DO $$
DECLARE d date := (date_trunc('day', now()) - interval '120 days')::date;
BEGIN
  WHILE d < (date_trunc('day', now()) + interval '30 days')::date LOOP
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS weavix.silver.mytable_%s
         PARTITION OF weavix.silver.mytable_part
         FOR VALUES FROM (%L) TO (%L);',
      to_char(d,'YYYYMMDD'), d::timestamptz, (d + interval '1 day')::timestamptz
    );
    EXECUTE format('CREATE INDEX IF NOT EXISTS mytable_%s_ts_idx ON weavix.silver.mytable_%s (event_ts);',
                   to_char(d,'YYYYMMDD'), to_char(d,'YYYYMMDD'));
    d := d + interval '1 day';
  END LOOP;
END $$;
```

* Nightly archive+drop (pseudo-flow):

  1. List partitions older than 90d (by name suffix or by `pg_inherits` bounds)
  2. For each partition date **D**:

     * Export `SELECT * FROM weavix.silver.mytable_D` → ADLS (Parquet/CSV.gz)
     * Validate counts → `DROP TABLE weavix.silver.mytable_D;`

You can drive (2) with ADF/Databricks or the Python `pgtool.py` I gave you (add a small loop that walks daily dates < now()-90d and calls `backup` then executes a `DROP TABLE`).

### B) Timescale hypertables (retention only)

If you already have a hypertable but can’t rely on compression:

```sql
-- keep 90 days hot, drop older chunks after your export completes
SELECT add_retention_policy('weavix.silver.mytable', INTERVAL '90 days');
```

For exporting old ranges, use your external tool to query by `WHERE event_ts >= $from AND event_ts < $to` (chunk boundary). After a successful export, the retention policy (or a custom job) will remove them safely.

---

## Where compression stands on Azure managed Postgres

* **Feature availability is inconsistent across Azure Flexible Server versions** and can change over time; users report issues enabling Timescale across PG major versions and mention limitations vs. running TimescaleDB yourself or on Timescale Cloud. That’s why planning **without** depending on compression is safest on Flexible Server. ([Microsoft Learn][1])
* Community threads from Azure/Timescale ecosystems also note that **compression may not be supported** in the Azure-managed TimescaleDB combination you get on Flexible Server. If compression is a hard requirement, the two clean options are:

  1. **Timescale Cloud** (fully managed, supports compression), or
  2. **Self-manage Postgres+Timescale on an Azure VM/AKS**, where you control the TimescaleDB build and can enable compression as documented by Timescale. ([TigerData][2])

---

## TL;DR recommendation for you

* Keep ≤90 days in Postgres (partitioned or hypertable).
* **Export >90 days to ADLS as Parquet** nightly, then drop the old slice.
* Add lightweight rollups (continuous aggregates or scheduled SQL) to keep recent summaries hot.
* Don’t depend on Timescale compression on Azure Flexible Server; design the pipeline so it’s great even without it.

If you want, I can:

* Extend your `pgtool.py` to **iterate dates older than 90d**: export (CSV.gz), validate, and execute the corresponding `DROP` (partition or `DELETE WHERE` guarded by day range if you’re not partitioned yet).
* Or generate an **ADF pipeline** (JDBC→ADLS Parquet) + a tiny SQL script to drop yesterday’s “now()-90d” slice after a successful copy run.

[1]: https://learn.microsoft.com/en-us/answers/questions/1534809/timescaledb-on-azure-postgresql-v16?utm_source=chatgpt.com "TimescaleDB on Azure PostgreSQL v16"
[2]: https://www.tigerdata.com/blog/how-to-install-timescaledb-on-azure?utm_source=chatgpt.com "How to Install TimescaleDB on Azure"



# Write the bash script pgtool.sh for backup and recovery postgres table. 
It should be compatible with bash   version 3.2.57

It could be a full or partial content of the table.
Output format: csv (optionally - compressed by gzip).

It should be possible to dump just part of the table based on  
date range filter applied to some column. 

Script should accept command line arguments:
- postgres instance (dev or prod or test or local)
- full table name (example: weavix.silver.mytable)
- optional: column with timestamptz datatype
- optional: date in format YYYY-MM-DD or YYYY-MM
- optional: compress it or not (default: compress)
- optional: destination folder (default folder should be in the script,
  ( it depend on postgres instance name)

 delete records from table after backup was validated

The output: csv or compressed csv, depending of command line flag.
The output file name is concatenation of input parameters:
- postgres instance (dev, prod, test)
- table name
- column with timestamptz datatype
- date in format YYYY-MM-DD or YYYY-MM (one day or one month)

Example of backup of 1 month:  
pgtool.sh backup dev weavix.silver.mytable 2025-01  
Output file:  /destination_folder/dev_weavix.silver.mytable_2025-01.csv

Also this script should be able to restore data to the Postgres table.
pgtool.sh restore dev  weavix.silver.mytable_timecol_2025-01.csv

The destination table should be created automatically, based on input file name 
(without suffix .csv ot csv.gz), it should include the date, if it is part of file name.

If destination table already exists then show warning.

## chat.mistral.ai
```bash
#!/bin/bash

# pgtool.sh - PostgreSQL table backup and recovery tool (Bash 3.2.5 compatible)
# Usage:
#   Backup: ./pgtool.sh backup <instance> <table> [<time_column>] [<date>] [--no-compress] [--dest <folder>]
#   Restore: ./pgtool.sh restore <instance> <file>

set -euo pipefail

# --- Config ---
# Use environment variables or case statements for instance config
# Example: export PG_DEV="user=dev_user dbname=dev_db host=dev-host port=5432"
# Or set here:
PG_DEV="user=dev_user dbname=dev_db host=dev-host port=5432"
PG_PROD="user=prod_user dbname=prod_db host=prod-host port=5432"
PG_TEST="user=test_user dbname=test_db host=test-host port=5432"
PG_LOCAL="user=postgres dbname=postgres host=localhost port=5432"
DEFAULT_DEST_FOLDER="/var/backups/postgres"
COMPRESS=true
# --- End Config ---

function usage() {
    cat <<EOF
Usage:
  Backup: $0 backup <instance> <table> [<time_column>] [<date>] [--no-compress] [--dest <folder>]
  Restore: $0 restore <instance> <file>

  <instance>: dev, prod, test, or local
  <table>: full table name, e.g. weavix.silver.mytable
  <time_column>: column with timestamptz datatype (for date filtering)
  <date>: YYYY-MM-DD or YYYY-MM (for date filtering)
  <file>: backup file to restore
EOF
    exit 1
}

function get_conn() {
    local instance="$1"
    case "$instance" in
        dev)    echo "$PG_DEV" ;;
        prod)   echo "$PG_PROD" ;;
        test)   echo "$PG_TEST" ;;
        local)  echo "$PG_LOCAL" ;;
        *)      echo "" ;;
    esac
}

function backup() {
    local instance="$1"
    local table="$2"
    local time_column="${3:-}"
    local date_filter="${4:-}"
    local compress="${5:-true}"
    local dest_folder="${6:-${DEFAULT_DEST_FOLDER}}"

    local conn=$(get_conn "$instance")
    if [[ -z "$conn" ]]; then
        echo "Error: Unknown instance '$instance'"
        usage
    fi

    local schema=$(echo "$table" | cut -d. -f1,2)
    local table_name=$(echo "$table" | cut -d. -f3)
    local dest_file="$dest_folder/${instance}_${table//./_}"

    if [[ -n "$time_column" && -n "$date_filter" ]]; then
        dest_file="${dest_file}_${time_column}_${date_filter}"
        local where_clause="WHERE date_trunc('day', \"$time_column\")"
        if [[ "$date_filter" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
            where_clause+=" BETWEEN '${date_filter}-01' AND '${date_filter}-01' + INTERVAL '1 month'"
        else
            where_clause+=" = '$date_filter'"
        fi
    fi

    dest_file+=".csv"

    echo "Backing up $table to $dest_file (compress: $compress)"

    local query="COPY (SELECT * FROM $table"
    [[ -n "$time_column" && -n "$date_filter" ]] && query+=" $where_clause"
    query+=") TO STDOUT WITH CSV HEADER"

    mkdir -p "$dest_folder"
    if [[ "$compress" == "true" ]]; then
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "$query" | gzip > "$dest_file.gz"
        echo "Backup saved to $dest_file.gz"
    else
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "$query" > "$dest_file"
        echo "Backup saved to $dest_file"
    fi
}

function restore() {
    local instance="$1"
    local file="$2"
    local conn=$(get_conn "$instance")
    if [[ -z "$conn" ]]; then
        echo "Error: Unknown instance '$instance'"
        usage
    fi

    local filename=$(basename "$file")
    local table_name=$(echo "$filename" | sed 's/\.csv\(\.gz\)\?$//')
    table_name=$(echo "$table_name" | sed "s/^${instance}_//")

    local schema=$(echo "$table_name" | cut -d_ -f1,2)
    local table=$(echo "$table_name" | cut -d_ -f3-)

    # If table_name contains date, extract the base table name
    if [[ "$table" =~ ^([^_]+_[^_]+)_[^_]+_[0-9]{4}-[0-9]{2}(-[0-9]{2})?$ ]]; then
        table=$(echo "$table" | sed 's/_[^_]*_[0-9]\{4\}-[0-9]\{2\}-*[0-9]*$//')
    fi

    # Check if table exists
    local exists=$(PGPASSWORD=${PGPASSWORD:-} psql "$conn" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema || '.' || table_name = '$schema.$table'")
    if [[ "$exists" == "1" ]]; then
        echo "Warning: Table $schema.$table already exists. Data will be appended."
    else
        echo "Creating table $schema.$table from backup..."
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "CREATE TABLE IF NOT EXISTS $schema.$table (LIKE $schema.$table INCLUDING ALL);"
    fi

    if [[ "$file" == *.gz ]]; then
        gunzip -c "$file" | PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "\COPY $schema.$table FROM STDIN WITH CSV HEADER"
    else
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "\COPY $schema.$table FROM '$file' WITH CSV HEADER"
    fi
    echo "Data restored to $schema.$table"
}

# --- Main ---
if [[ $# -lt 2 ]]; then
    usage
fi

case "$1" in
    backup)
        shift
        local instance="$1"
        local table="$2"
        local time_column="${3:-}"
        local date_filter="${4:-}"
        local compress=true
        local dest_folder="$DEFAULT_DEST_FOLDER"

        while [[ $# -gt 0 ]]; do
            case "$1" in
                --no-compress) compress=false ;;
                --dest) dest_folder="$2"; shift ;;
            esac
            shift
        done

        backup "$instance" "$table" "$time_column" "$date_filter" "$compress" "$dest_folder"
        ;;
    restore)
        shift
        local instance="$1"
        local file="$2"
        restore "$instance" "$file"
        ;;
    *)
        usage
        ;;
esac

```

### Usage
```backup
# Full table backup (compressed)
./pgtool.sh backup dev weavix.silver.mytable

# Partial backup (by month, compressed)
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01

# Partial backup (by day, uncompressed)
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01-15 --no-compress

# Custom destination folder
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01 --dest /my/backups
```

### restore
```bash
# Restore from compressed file
./pgtool.sh restore dev /var/backups/postgres/dev_weavix_silver_mytable_created_at_2025-01.csv.gz

# Restore from uncompressed file
./pgtool.sh restore dev /var/backups/postgres/dev_weavix_silver_mytable_created_at_2025-01-15.csv

```
## python
```python
#!/usr/bin/env python3
"""
pgtool.py — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)

Requires: Python 3.8+, psycopg2-binary
  pip install psycopg2-binary

Usage:
  # Full-table backup (gzip by default)
  python pgtool.py backup dev weavix.silver.mytable

  # Month partial backup (January 2025) using timestamptz column "timecol"
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01

  # Day partial backup, no compression, custom dest dir
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01-15 --no-compress --dest /tmp

  # Restore from file; auto-creates table (TEXT cols) if it doesn't exist; appends if it does
  python pgtool.py restore dev /backups/dev_weavix.silver.mytable_timecol_2025-01.csv.gz
"""

import argparse
import csv
import gzip
import io
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import sql

# -------- Instance configuration (override with env) --------
DEST_DEFAULTS = {
    "dev":   os.environ.get("PGTOOL_DEST_DEV",   "/var/backups/pg/dev"),
    "prod":  os.environ.get("PGTOOL_DEST_PROD",  "/var/backups/pg/prod"),
    "test":  os.environ.get("PGTOOL_DEST_TEST",  "/var/backups/pg/test"),
    "local": os.environ.get("PGTOOL_DEST_LOCAL", "/var/backups/pg/local"),
}

PGURI = {
    "dev":   os.environ.get("PGURI_DEV",   "postgres://localhost:5432/postgres"),
    "prod":  os.environ.get("PGURI_PROD",  "postgres://localhost:5432/postgres"),
    "test":  os.environ.get("PGURI_TEST",  "postgres://localhost:5432/postgres"),
    "local": os.environ.get("PGURI_LOCAL", "postgres://localhost:5432/postgres"),
}
# ------------------------------------------------------------

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SCHEMA_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")
MONTH_FMT_RE = re.compile(r"^\d{4}-\d{2}$")
DAY_FMT_RE   = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def info(msg: str):
    print(f"INFO:  {msg}", file=sys.stderr)

def warn(msg: str):
    print(f"WARN:  {msg}", file=sys.stderr)

def assert_ident(name: str, kind: str = "identifier"):
    if not IDENT_RE.match(name or ""):
        die(f"Invalid {kind}: {name!r}")

def assert_schema_table(qual: str):
    if not SCHEMA_TABLE_RE.match(qual or ""):
        die(f"Invalid table name {qual!r} (expected schema.table)")

@contextmanager
def connect(instance: str):
    dsn = PGURI.get(instance)
    if not dsn:
        die(f"Unknown instance {instance!r} (expected dev|prod|test|local)")
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()

def qualify(schema_table: str):
    assert_schema_table(schema_table)
    schema, table = schema_table.split(".", 1)
    return schema, table

def time_window_sql(timecol: str, date_arg: str) -> sql.SQL:
    assert_ident(timecol, "column")
    if MONTH_FMT_RE.match(date_arg):
        # [first day of month, first day of next month)
        return sql.SQL(
            "({col} >= date_trunc('month', to_date(%s,'YYYY-MM-DD')) "
            "AND {col} < (date_trunc('month', to_date(%s,'YYYY-MM-DD')) + interval '1 month'))"
        ).format(col=sql.Identifier(timecol)), [f"{date_arg}-01", f"{date_arg}-01"]
    if DAY_FMT_RE.match(date_arg):
        # [day, next day)
        return sql.SQL(
            "({col} >= to_timestamp(%s,'YYYY-MM-DD') "
            "AND {col} < (to_timestamp(%s,'YYYY-MM-DD') + interval '1 day'))"
        ).format(col=sql.Identifier(timecol)), [date_arg, date_arg]
    die("Invalid --date (use YYYY-MM or YYYY-MM-DD)")

def validate_timecol(conn, schema: str, table: str, col: str):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s
              AND data_type='timestamp with time zone'
        """, (schema, table, col))
        if not cur.fetchone():
            die(f"Column {schema}.{table}.{col} not found or not timestamptz")

def default_dest(instance: str) -> Path:
    d = DEST_DEFAULTS.get(instance)
    if not d:
        die(f"No default destination configured for instance {instance!r}")
    return Path(d)

def build_backup_filename(instance: str, schema: str, table: str,
                          timecol: str | None, date_arg: str | None) -> str:
    if timecol and date_arg:
        return f"{instance}_{schema}.{table}_{timecol}_{date_arg}.csv"
    return f"{instance}_{schema}.{table}.csv"

def backup(args):
    instance = args.instance
    schema, table = qualify(args.schema_table)
    dest_dir = Path(args.dest or default_dest(instance))
    dest_dir.mkdir(parents=True, exist_ok=True)

    timecol = args.timecol
    date_arg = args.date

    with connect(instance) as conn, conn.cursor() as cur:
        where_sql = None
        where_params = []
        if (timecol and not date_arg) or (date_arg and not timecol):
            die("Partial backup requires BOTH --timecol and --date")
        if timecol and date_arg:
            validate_timecol(conn, schema, table, timecol)
            where_sql, where_params = time_window_sql(timecol, date_arg)

        filename = build_backup_filename(instance, schema, table, timecol, date_arg)
        out_path = dest_dir / filename
        compress = not args.no_compress

        # Build COPY command
        if where_sql is None:
            copy_sql = sql.SQL("COPY {}.{} TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
            params = None
        else:
            copy_sql = sql.SQL(
                "COPY (SELECT * FROM {}.{} WHERE {} ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
            ).format(
                sql.Identifier(schema),
                sql.Identifier(table),
                where_sql
            )
            params = where_params

        info(f"Backing up {schema}.{table} -> {out_path}{'.gz' if compress else ''}")

        if compress:
            with gzip.open(str(out_path) + ".gz", "wb") as gz:
                cur.copy_expert(copy_sql.as_string(conn), gz, vars=params)
            info(f"Backup complete: {out_path}.gz")
        else:
            with open(out_path, "wb") as f:
                cur.copy_expert(copy_sql.as_string(conn), f, vars=params)
            info(f"Backup complete: {out_path}")

def sanitize_colname(raw: str) -> str:
    # Strip quotes and spaces, keep A-Za-z0-9_, replace others with _
    raw = raw.replace('"', '').strip()
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', raw)
    if not cleaned:
        cleaned = "col"
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned

def ensure_schema(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s) THEN
            EXECUTE format('CREATE SCHEMA %I', %s);
          END IF;
        END $$;
        """, (schema, schema))
        conn.commit()

def table_exists(conn, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname=%s AND c.relname=%s AND c.relkind='r'
        """, (schema, table))
        return cur.fetchone() is not None

def create_table_from_csv_header(conn, schema: str, table: str, header_line: str):
    # Build TEXT columns from CSV header
    reader = csv.reader([header_line])
    cols = next(reader)
    if not cols:
        die("Empty CSV header; cannot create table")

    cleaned = [sanitize_colname(c) for c in cols]
    # Build DDL
    col_list = sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in cleaned)
    ddl = sql.SQL("CREATE TABLE {}.{} (").format(sql.Identifier(schema), sql.Identifier(table))
    ddl = sql.SQL("").join([ddl, col_list, sql.SQL(")")])

    ensure_schema(conn, schema)
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()

def parse_dest_table_from_filename(path: Path, instance: str) -> tuple[str, str]:
    """
    Accepts file names like:
      <instance>_<schema.table>.csv[.gz]
      <instance>_<schema.table>_<timecol>_<YYYY-MM>.csv[.gz]
      <schema.table>_<timecol>_<YYYY-MM-DD>.csv
      <schema.table>.csv
    Restored table name includes any suffix after schema.table, appended to the base table.
    """
    base = path.name
    if base.endswith(".gz"): base = base[:-3]
    if base.endswith(".csv"): base = base[:-4]

    # Strip leading "<instance>_"
    prefix = f"{instance}_"
    if base.startswith(prefix):
        base = base[len(prefix):]

    # schema.table is up to first underscore (if any)
    parts = base.split("_", 1)
    schema_table = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if not SCHEMA_TABLE_RE.match(schema_table):
        die(f"Cannot parse schema.table from filename: {path.name}")

    schema, table = schema_table.split(".", 1)
    if rest:
        table = f"{table}_{rest}"
    return schema, table

def restore(args):
    instance = args.instance
    infile = Path(args.input)
    if not infile.exists():
        die(f"Input file not found: {infile}")

    with connect(instance) as conn:
        # Open file (gzip or plain)
        if infile.suffix == ".gz":
            opener = lambda p: io.TextIOWrapper(gzip.open(p, "rb"), newline="")
        else:
            opener = lambda p: open(p, "rt", newline="")

        with opener(str(infile)) as f:
            # Peek header safely without losing it
            header_pos = f.tell()
            header_line = f.readline()
            if not header_line:
                die("Input file is empty")
            # Normalize header (ensure one line without trailing newline)
            header_line = header_line.rstrip("\r\n")
            f.seek(header_pos)

            schema, table = parse_dest_table_from_filename(infile, instance)
            info(f"Restoring into: {schema}.{table}")

            # Create table if not exists; warn otherwise
            if table_exists(conn, schema, table):
                warn(f"Destination table {schema}.{table} already exists; rows will be appended.")
                if not args.force_append:
                    warn("Pass --force-append to suppress this warning.")
            else:
                info("Creating table from CSV header (all columns TEXT)")
                create_table_from_csv_header(conn, schema, table, header_line)

            # COPY FROM STDIN
            with conn.cursor() as cur:
                copy_sql = sql.SQL("COPY {}.{} FROM STDIN WITH (FORMAT csv, HEADER)").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
                cur.copy_expert(copy_sql.as_string(conn), f)
            conn.commit()
            info("Restore complete.")

def main():
    parser = argparse.ArgumentParser(prog="pgtool.py", description="Postgres CSV backup/restore (gzip by default)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_b = sub.add_parser("backup", help="Backup a table to CSV/.csv.gz")
    p_b.add_argument("instance", choices=PGURI.keys())
    p_b.add_argument("schema_table", help="Fully-qualified table name, e.g. weavix.silver.mytable")
    p_b.add_argument("--timecol", help="timestamptz column for date filtering")
    p_b.add_argument("--date", help="YYYY-MM or YYYY-MM-DD to filter by")
    p_b.add_argument("--no-compress", action="store_true", help="Write plain .csv instead of .csv.gz")
    p_b.add_argument("--dest", help="Destination folder (defaults by instance)")
    p_b.set_defaults(func=backup)

    p_r = sub.add_parser("restore", help="Restore CSV/.csv.gz into a table (auto-creates if needed)")
    p_r.add_argument("instance", choices=PGURI.keys())
    p_r.add_argument("input", help="Path to .csv or .csv.gz file")
    p_r.add_argument("--force-append", action="store_true", help="Suppress warning when table exists")
    p_r.set_defaults(func=restore)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

```



### GEMINI
```
#!/bin/bash

# ==============================================================================
# Script: pgtool.sh
# Description: A tool for backing up and restoring PostgreSQL table data.
# This version is compatible with Bash 3.2.5.
# ==============================================================================

# --- Helper Functions ---

# Function to get the PostgreSQL connection string for a given instance
get_pg_conn() {
    local instance=$1
    case "$instance" in
        dev)
            echo "PGHOST=$PGHOST_dev PGDATABASE=$PGDATABASE_dev PGUSER=$PGUSER_dev PGPASSWORD=$PGPASSWORD_dev"
            ;;
        prod)
            echo "PGHOST=$PGHOST_prod PGDATABASE=$PGDATABASE_prod PGUSER=$PGUSER_prod PGPASSWORD=$PGPASSWORD_prod"
            ;;
        test)
            echo "PGHOST=$PGHOST_test PGDATABASE=$PGDATABASE_test PGUSER=$PGUSER_test PGPASSWORD=$PGPASSWORD_test"
            ;;
        local)
            echo "PGHOST=$PGHOST_local PGDATABASE=$PGDATABASE_local PGUSER=$PGUSER_local PGPASSWORD=$PGPASSWORD_local"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to display script usage
usage() {
    echo "Usage: $0 <command> <instance> <full_table_name> [options]"
    echo "Commands:"
    echo "  backup    Backup a PostgreSQL table."
    echo "  restore   Restore a PostgreSQL table from a file."
    echo ""
    echo "Backup options:"
    echo "  <full_table_name>       Required. Format: <schema>.<table_name>"
    echo "  [timestamptz_column]    Optional. Column for date filtering."
    echo "  [date]                  Optional. YYYY-MM-DD or YYYY-MM for filtering."
    echo "  --no-compress           Optional. Do not compress the output file."
    echo "  --dest-dir <path>       Optional. Destination folder."
    echo ""
    echo "Restore options:"
    echo "  <backup_file>           Required. Path to the backup file (.csv or .csv.gz)."
    echo ""
    exit 1
}

# --- Main Logic ---

# Check for a command and instance argument
if [ "$#" -lt 3 ]; then
    usage
fi

COMMAND=$1
INSTANCE=$2
FULL_TABLE_NAME_OR_FILE=$3

# Get the connection string using the helper function
PG_CONN=$(get_pg_conn "$INSTANCE")

# Check if the instance is valid
if [ -z "$PG_CONN" ]; then
    echo "Error: Invalid instance '$INSTANCE'. Supported instances: dev, prod, test, local"
    usage
fi

# --- Backup Command ---
if [ "$COMMAND" = "backup" ]; then
    echo "Starting backup process for instance '$INSTANCE'..."

    SCHEMA_NAME=$(echo "$FULL_TABLE_NAME_OR_FILE" | cut -d'.' -f1-2)
    TABLE_NAME=$(echo "$FULL_TABLE_NAME_OR_FILE" | cut -d'.' -f3)

    # Validate table name format
    if [[ ! "$FULL_TABLE_NAME_OR_FILE" =~ ^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$ ]]; then
        echo "Error: Invalid table name format. Use <schema>.<table_name>."
        exit 1
    fi

    TIMESTAMP_COL=""
    DATE_FILTER=""
    DEFAULT_COMPRESS=true
    COMPRESS=$DEFAULT_COMPRESS
    DEFAULT_DEST_DIR="/var/backups"
    DEST_DIR="$DEFAULT_DEST_DIR/$INSTANCE"

    # Parse optional arguments
    shift 3
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --no-compress)
                COMPRESS=false
                shift
                ;;
            --dest-dir)
                if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
                    DEST_DIR=$2
                    shift 2
                else
                    echo "Error: --dest-dir requires a path."
                    exit 1
                fi
                ;;
            *)
                if [ -z "$TIMESTAMP_COL" ]; then
                    TIMESTAMP_COL=$1
                    shift
                elif [ -z "$DATE_FILTER" ]; then
                    DATE_FILTER=$1
                    shift
                else
                    echo "Error: Unknown argument: $1"
                    usage
                fi
                ;;
        esac
    done

    # Create destination directory if it doesn't exist
    mkdir -p "$DEST_DIR" || { echo "Error: Failed to create directory $DEST_DIR"; exit 1; }

    # Build the WHERE clause for date filtering
    WHERE_CLAUSE=""
    if [ -n "$TIMESTAMP_COL" ] && [ -n "$DATE_FILTER" ]; then
        if [[ "$DATE_FILTER" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER' AND \"$TIMESTAMP_COL\" < ('$DATE_FILTER'::date + INTERVAL '1 day')::text"
            OUTPUT_DATE_PART="_$(echo "$DATE_FILTER" | tr '-' '_')"
        elif [[ "$DATE_FILTER" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER-01' AND \"$TIMESTAMP_COL\" < ('$DATE_FILTER-01'::date + INTERVAL '1 month')::text"
            OUTPUT_DATE_PART="_$(echo "$DATE_FILTER" | tr '-' '_')"
        else
            echo "Error: Invalid date format. Use YYYY-MM-DD or YYYY-MM."
            exit 1
        fi
    fi

    # Construct the output file name
    FILE_NAME="${INSTANCE}_${SCHEMA_NAME}_${TABLE_NAME}"
    if [ -n "$TIMESTAMP_COL" ]; then
        FILE_NAME+="_${TIMESTAMP_COL}"
    fi
    if [ -n "$DATE_FILTER" ]; then
        FILE_NAME+="_$(echo "$DATE_FILTER" | tr '-' '_')"
    fi
    FILE_EXTENSION=".csv"
    if [ "$COMPRESS" = true ]; then
        FILE_EXTENSION=".csv.gz"
    fi
    OUTPUT_FILE="${DEST_DIR}/${FILE_NAME}${FILE_EXTENSION}"

    echo "Dumping data from '$FULL_TABLE_NAME_OR_FILE'..."
    echo "Output file: '$OUTPUT_FILE'"
    echo "SQL Query: SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE;"

    # The actual backup command using psql and COPY
    if [ "$COMPRESS" = true ]; then
        psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO STDOUT WITH (FORMAT CSV, HEADER)" $PG_CONN | gzip > "$OUTPUT_FILE"
    else
        psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO '$OUTPUT_FILE' WITH (FORMAT CSV, HEADER)" $PG_CONN
    fi

    if [ "$?" -eq 0 ]; then
        echo "Backup completed successfully."
    else
        echo "Error: Backup failed. Check the parameters and database connection."
        exit 1
    fi

# --- Restore Command ---
elif [ "$COMMAND" = "restore" ]; then
    BACKUP_FILE=$FULL_TABLE_NAME_OR_FILE

    # Validate file existence
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file '$BACKUP_FILE' not found."
        exit 1
    fi

    echo "Starting restore process to instance '$INSTANCE'..."
    echo "Restoring from file '$BACKUP_FILE'..."

    # Extract original table name from backup file name.
    TEMP_FILE_NAME=$(basename "$BACKUP_FILE")
    ORIGINAL_TABLE_INFO=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_.*/\1/")
    ORIGINAL_SCHEMA=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f1-2)
    ORIGINAL_TABLE=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f3)

    # Determine the new table name based on the backup file name.
    DEST_TABLE_NAME=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_(.*)\.csv\.?gz?/\1_\2/")
    DEST_SCHEMA=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f1-2)
    DEST_TABLE=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f3)

    # Check if the destination table exists
    psql -t -c "SELECT 1 FROM pg_tables WHERE schemaname = '$DEST_SCHEMA' AND tablename = '$DEST_TABLE';" $PG_CONN | grep -q 1
    if [ "$?" -eq 0 ]; then
        echo "Warning: Destination table '$DEST_TABLE_NAME' already exists. Data will be appended. Press Enter to continue, or Ctrl+C to cancel."
        read -r
    else
        echo "Destination table '$DEST_TABLE_NAME' does not exist. Creating schema and table..."
        
        # Create schema if it doesn't exist.
        psql -c "CREATE SCHEMA IF NOT EXISTS \"$DEST_SCHEMA\";" $PG_CONN
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create schema '$DEST_SCHEMA'."
            exit 1
        fi

        # Use pg_dump to get the schema of the original table, then modify it to create the new table.
        SCHEMA_DUMP=$(pg_dump -s -t "$ORIGINAL_SCHEMA.$ORIGINAL_TABLE" --no-owner --no-privileges --no-comments --schema-only $PG_CONN)
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to dump schema for '$ORIGINAL_SCHEMA.$ORIGINAL_TABLE'."
            exit 1
        fi
        
        MODIFIED_SCHEMA_DUMP=$(echo "$SCHEMA_DUMP" | sed -E "s/CREATE TABLE \"$ORIGINAL_SCHEMA\"\.\"$ORIGINAL_TABLE\"/CREATE TABLE \"$DEST_SCHEMA\"\.\"$DEST_TABLE\"/")

        # Execute the modified schema dump to create the new table.
        psql -c "$MODIFIED_SCHEMA_DUMP" $PG_CONN
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create destination table '$DEST_TABLE_NAME'."
            exit 1
        fi
        echo "Table '$DEST_TABLE_NAME' created successfully."
    fi

    # The actual restore command
    if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
        echo "Restoring compressed data..."
        gunzip -c "$BACKUP_FILE" | psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT CSV, HEADER)" $PG_CONN
    else
        echo "Restoring uncompressed data..."
        psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM '$BACKUP_FILE' WITH (FORMAT CSV, HEADER)" $PG_CONN
    fi

    if [ "$?" -eq 0 ]; then
        echo "Restore completed successfully."
    else
        echo "Error: Restore failed. Check the file and table schema."
        exit 1
    fi

else
    echo "Error: Invalid command '$COMMAND'."
    usage
fi

```

### python

```python
#!/usr/bin/env python3

import argparse
import os
import sys
import re
import subprocess
import gzip
import shutil
import psycopg2
from psycopg2 import sql

def get_pg_conn_params(instance):
    """
    Retrieves PostgreSQL connection parameters from environment variables
    for a given instance.
    """
    prefix = f"PG_{instance.upper()}"
    return {
        "host": os.getenv(f"PGHOST_{instance}"),
        "dbname": os.getenv(f"PGDATABASE_{instance}"),
        "user": os.getenv(f"PGUSER_{instance}"),
        "password": os.getenv(f"PGPASSWORD_{instance}")
    }

def backup_table(instance, full_table_name, timestamp_col, date_filter, no_compress, dest_dir):
    """
    Backs up a PostgreSQL table.
    """
    print(f"Starting backup process for instance '{instance}'...")

    try:
        schema, table = full_table_name.split('.', 1)
    except ValueError:
        print("Error: Invalid table name format. Use <schema>.<table_name>.")
        sys.exit(1)

    # Set up destination directory
    dest_dir_path = dest_dir or os.path.join("/var/backups", instance)
    os.makedirs(dest_dir_path, exist_ok=True)

    # Build WHERE clause for date filtering
    where_clause = ""
    output_date_part = ""
    if timestamp_col and date_filter:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})$", date_filter)
        if match:
            where_clause = f"WHERE \"{timestamp_col}\" >= '{date_filter}' AND \"{timestamp_col}\" < ('{date_filter}'::date + INTERVAL '1 day')::text"
            output_date_part = f"_{date_filter.replace('-', '_')}"
        else:
            match = re.match(r"^(\d{4}-\d{2})$", date_filter)
            if match:
                where_clause = f"WHERE \"{timestamp_col}\" >= '{date_filter}-01' AND \"{timestamp_col}\" < ('{date_filter}-01'::date + INTERVAL '1 month')::text"
                output_date_part = f"_{date_filter.replace('-', '_')}"
            else:
                print("Error: Invalid date format. Use YYYY-MM-DD or YYYY-MM.")
                sys.exit(1)
    
    # Construct output file name
    file_name = f"{instance}_{schema}_{table}"
    if timestamp_col:
        file_name += f"_{timestamp_col}"
    file_name += output_date_part

    if no_compress:
        output_file = os.path.join(dest_dir_path, f"{file_name}.csv")
    else:
        output_file = os.path.join(dest_dir_path, f"{file_name}.csv.gz")

    print(f"Dumping data from '{full_table_name}'...")
    print(f"Output file: '{output_file}'")

    conn_params = get_pg_conn_params(instance)
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Use psycopg2's copy_to method
                query = sql.SQL("SELECT * FROM {schema}.{table} {where_clause}").format(
                    schema=sql.Identifier(schema),
                    table=sql.Identifier(table),
                    where_clause=sql.Literal(where_clause)
                )

                if no_compress:
                    with open(output_file, 'wb') as f:
                        cur.copy_to(f, f"{schema}.{table}", sep=',', null='', header=True, columns=None, binary=False, with_oids=False)
                else:
                    with gzip.open(output_file, 'wb') as f:
                        cur.copy_to(f, f"{schema}.{table}", sep=',', null='', header=True, columns=None, binary=False, with_oids=False)

        print("Backup completed successfully.")
    except psycopg2.Error as e:
        print(f"Error: Backup failed. Check parameters and database connection. {e}")
        sys.exit(1)


def restore_table(instance, backup_file):
    """
    Restores a PostgreSQL table from a CSV file.
    """
    print(f"Starting restore process to instance '{instance}'...")

    if not os.path.isfile(backup_file):
        print(f"Error: Backup file '{backup_file}' not found.")
        sys.exit(1)

    # Extract original table name from backup file name
    base_name = os.path.basename(backup_file)
    try:
        parts = base_name.split('_')
        schema_table = parts[1] + "." + parts[2] + "." + parts[3]
        original_schema = parts[1] + "." + parts[2]
        original_table = parts[3]
    except IndexError:
        print("Error: Invalid backup file name format.")
        sys.exit(1)

    # Determine the new table name
    dest_table_name = os.path.splitext(os.path.basename(backup_file))[0]
    dest_table_name = dest_table_name.replace(f"{instance}_", "").replace(".csv", "").replace(".gz", "")
    
    # Check if a date part is present in the filename
    match = re.search(r"(_\d{4}_\d{2}(_\d{2})?)", dest_table_name)
    if match:
        dest_table_name = dest_table_name.replace(match.group(0), "")
        dest_table_name = f"{dest_table_name}{match.group(0)}"
    
    try:
        dest_schema, dest_table = dest_table_name.split('.', 1)
    except ValueError:
        print("Error: Could not determine destination table name.")
        sys.exit(1)
        
    print(f"Restoring from file '{backup_file}' to table '{dest_table_name}'...")

    conn_params = get_pg_conn_params(instance)
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Check if destination table exists
                cur.execute(sql.SQL(
                    "SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s"
                ), [dest_schema, dest_table])
                if cur.fetchone():
                    print(f"Warning: Destination table '{dest_table_name}' already exists. Data will be appended.")
                    input("Press Enter to continue, or Ctrl+C to cancel.")
                else:
                    print(f"Destination table '{dest_table_name}' does not exist. Creating schema and table...")

                    # Create schema if it doesn't exist
                    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {schema}").format(
                        schema=sql.Identifier(dest_schema)
                    ))

                    # Use pg_dump to get schema and recreate the table
                    try:
                        # Construct a DSN string for pg_dump
                        dsn = " ".join([f"{k}='{v}'" for k, v in conn_params.items()])
                        pg_dump_cmd = f"pg_dump -s -t {original_schema}.{original_table} --no-owner --no-privileges --no-comments --schema-only {dsn}"
                        
                        result = subprocess.run(
                            pg_dump_cmd,
                            shell=True,
                            check=True,
                            capture_output=True,
                            text=True,
                            env=os.environ
                        )
                        schema_dump = result.stdout
                        
                        # Modify the CREATE TABLE statement for the new name
                        modified_schema_dump = re.sub(
                            rf'CREATE TABLE "{original_schema}"\."{original_table}"',
                            f'CREATE TABLE "{dest_schema}"."{dest_table}"',
                            schema_dump
                        )
                        
                        cur.execute(modified_schema_dump)
                        conn.commit()
                        print(f"Table '{dest_table_name}' created successfully.")

                    except subprocess.CalledProcessError as e:
                        print(f"Error: Failed to dump schema. {e.stderr}")
                        sys.exit(1)
                    except Exception as e:
                        print(f"Error: Failed to create destination table. {e}")
                        sys.exit(1)

                # Restore data using COPY
                with open(backup_file, 'rb') as f_in:
                    if backup_file.endswith('.gz'):
                        f = gzip.open(f_in, 'rb')
                    else:
                        f = f_in
                    
                    cur.copy_from(f, f"{dest_schema}.{dest_table}", sep=',', null='', size=8192)

                conn.commit()
                print("Restore completed successfully.")

    except psycopg2.Error as e:
        print(f"Error: Restore failed. Check the file and database connection. {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="A tool for backing up and restoring PostgreSQL table data.",
        epilog="Note: Database connection details should be provided via environment variables (e.g., PGHOST_dev)."
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="command to execute")

    # Backup command parser
    backup_parser = subparsers.add_parser("backup", help="Backup a PostgreSQL table.")
    backup_parser.add_argument("instance", help="Postgres instance (dev, prod, test, or local).")
    backup_parser.add_argument("full_table_name", help="Full table name (e.g., weavix.silver.mytable).")
    backup_parser.add_argument("timestamp_col", nargs="?", default="", help="Optional: column with timestamptz datatype.")
    backup_parser.add_argument("date_filter", nargs="?", default="", help="Optional: date in YYYY-MM-DD or YYYY-MM format.")
    backup_parser.add_argument("--no-compress", action="store_true", help="Do not compress the output file.")
    backup_parser.add_argument("--dest-dir", help="Optional: destination folder.")

    # Restore command parser
    restore_parser = subparsers.add_parser("restore", help="Restore a PostgreSQL table from a file.")
    restore_parser.add_argument("instance", help="Postgres instance to restore to.")
    restore_parser.add_argument("backup_file", help="Path to the backup file (.csv or .csv.gz).")

    args = parser.parse_args()

    if args.command == "backup":
        backup_table(
            args.instance,
            args.full_table_name,
            args.timestamp_col,
            args.date_filter,
            args.no_compress,
            args.dest_dir
        )
    elif args.command == "restore":
        restore_table(
            args.instance,
            args.backup_file
        )

if __name__ == "__main__":
    main()

```

## ChatGPT
```bash
#!/usr/bin/env bash
# pgtool.sh — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)
# Compatible with Bash 3.2 (macOS default). No regex used.
#
# Features
#   • BACKUP: full table, or partial by date window on a timestamptz column.
#   • RESTORE: auto-creates destination table from CSV header (TEXT columns). Warns if table exists (appends).
#   • Compression: gzip by default (.csv.gz). Use --no-compress for plain .csv.
#   • File naming:
#       FULL:     <dest>/<instance>_<schema.table>.csv[.gz]
#       PARTIAL:  <dest>/<instance>_<schema.table>_<timecol>_<YYYY-MM | YYYY-MM-DD>.csv[.gz]
#
# Usage
#   Backup:
#     pgtool.sh backup <instance> <schema.table> [<timestamptz_col> <YYYY-MM|YYYY-MM-DD>] [--no-compress] [--dest DIR]
#     pgtool.sh backup dev weavix.silver.mytable
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01-15 --no-compress --dest /tmp
#
#   Restore:
#     pgtool.sh restore <instance> </path/to/file.csv|.csv.gz> [--force-append]
#     pgtool.sh restore dev /backups/dev_weavix.silver.mytable_2025-01.csv.gz
#
# Defaults (edit if desired) ----------------------------------------------
DEST_DEV="/var/backups/pg/dev"
DEST_PROD="/var/backups/pg/prod"
DEST_TEST="/var/backups/pg/test"
DEST_LOCAL="/var/backups/pg/local"

# Connection URIs (override via env: PGURI_DEV, PGURI_PROD, PGURI_TEST, PGURI_LOCAL)
PGURI_DEV="${PGURI_DEV:-postgres://localhost:5432/postgres}"
PGURI_PROD="${PGURI_PROD:-postgres://localhost:5432/postgres}"
PGURI_TEST="${PGURI_TEST:-postgres://localhost:5432/postgres}"
PGURI_LOCAL="${PGURI_LOCAL:-postgres://localhost:5432/postgres}"
# -------------------------------------------------------------------------

set -euo pipefail

die()  { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN:  $*" >&2; }
info() { echo "INFO:  $*" >&2; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

PSQL() { local uri="$1"; shift; psql $uri "$@"; }

usage() {
  sed -n '1,120p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

resolve_instance() {
  case "${1:-}" in
    dev)   PGURI="$PGURI_DEV";   DEST_DIR_DEFAULT="$DEST_DEV" ;;
    prod)  PGURI="$PGURI_PROD";  DEST_DIR_DEFAULT="$DEST_PROD" ;;
    test)  PGURI="$PGURI_TEST";  DEST_DIR_DEFAULT="$DEST_TEST" ;;
    local) PGURI="$PGURI_LOCAL"; DEST_DIR_DEFAULT="$DEST_LOCAL" ;;
    *) die "Unknown instance '${1:-}' (expected: dev|prod|test|local)";;
  esac
}

# Identifier checks without regex
is_valid_ident() {
  # letters, digits, underscore; must not be empty
  local s="${1:-}"
  [ -n "$s" ] || return 1
  case "$s" in
    *[!A-Za-z0-9_]* ) return 1 ;;
    * ) return 0 ;;
  esac
}

split_qualname() {
  local qual="${1:-}"
  case "$qual" in
    *.*) : ;;
    *) die "Invalid table name '$qual' (expected schema.table)";;
  esac
  SCHEMA="${qual%%.*}"
  TABLE="${qual##*.}"
  is_valid_ident "$SCHEMA" || die "Invalid schema identifier '$SCHEMA'"
  is_valid_ident "$TABLE"  || die "Invalid table identifier '$TABLE'"
  QSCHEMA="\"$SCHEMA\""; QTABLE="\"$TABLE\""
}

# Date format helpers (no regex)
is_month_fmt() {
  # YYYY-MM
  local d="${1:-}"
  case "$d" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}
is_day_fmt() {
  # YYYY-MM-DD
  local d="${1:-}"
  case "$d" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

build_time_window_sql() {
  # Builds TIME_WINDOW_SQL using to_date/to_timestamp and date_trunc
  local col="$1" date_arg="$2"
  is_valid_ident "$col" || die "Invalid column name '$col'"
  if is_month_fmt "$date_arg"; then
    # [first day of month, first day of next month)
    TIME_WINDOW_SQL="($col >= date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) AND $col < (date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) + interval '1 month'))"
  elif is_day_fmt "$date_arg"; then
    # [day, next day)
    TIME_WINDOW_SQL="($col >= to_timestamp('$date_arg','YYYY-MM-DD') AND $col < (to_timestamp('$date_arg','YYYY-MM-DD') + interval '1 day'))"
  else
    die "Invalid date '$date_arg' (use YYYY-MM or YYYY-MM-DD)"
  fi
}

validate_timecol() {
  local schema="$1" table="$2" col="$3"
  # Check timestamptz by data_type
  local q="
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema=$$${schema}$$
      AND table_name=$$${table}$$
      AND column_name=$$${col}$$
      AND data_type='timestamp with time zone';
  "
  PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$' || die "Column '$schema.$table.$col' not found or not timestamptz"
}

# ---------- BACKUP ----------
do_backup() {
  local instance="$1" qualname="$2"; shift 2
  local timecol="" date_arg="" dest_dir="" compress=1

  # Optionals: <timecol> <date>
  if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then timecol="$1"; shift; fi
  if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then date_arg="$1"; shift; fi

  # Flags
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-compress) compress=0; shift ;;
      --dest) dest_dir="${2:-}"; [ -n "$dest_dir" ] || die "--dest requires a directory"; shift 2 ;;
      -h|--help) usage ;;
      *) die "Unknown option for backup: $1" ;;
    esac
  done

  resolve_instance "$instance"
  split_qualname "$qualname"

  local out_dir="${dest_dir:-$DEST_DIR_DEFAULT}"
  mkdir -p "$out_dir"

  local filename where_sql=""
  if [ -n "$timecol" ] || [ -n "$date_arg" ]; then
    [ -n "$timecol" ] && [ -n "$date_arg" ] || die "Partial backup requires BOTH <timestamptz_col> and <date>"
    validate_timecol "$SCHEMA" "$TABLE" "$timecol"
    build_time_window_sql "$timecol" "$date_arg"
    where_sql="WHERE $TIME_WINDOW_SQL"
    filename="${instance}_${SCHEMA}.${TABLE}_${timecol}_${date_arg}.csv"
  else
    filename="${instance}_${SCHEMA}.${TABLE}.csv"
  fi

  local out_csv="$out_dir/$filename"
  local sql
  if [ -n "$where_sql" ]; then
    sql="\\copy (SELECT * FROM $QSCHEMA.$QTABLE $where_sql ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
  else
    sql="\\copy $QSCHEMA.$QTABLE TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
  fi

  info "Backing up $SCHEMA.$TABLE -> $out_csv"
  if [ "$compress" -eq 1 ]; then
    need_cmd gzip
    PSQL "$PGURI" -qAt -c "$sql" | gzip > "${out_csv}.gz"
    info "Backup complete: ${out_csv}.gz"
  else
    PSQL "$PGURI" -qAt -c "$sql" > "$out_csv"
    info "Backup complete: $out_csv"
  fi
}

# ---------- RESTORE HELPERS ----------
ensure_schema() {
  local schema="$1"
  local sql="DO $$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = '$schema') THEN
      EXECUTE format('CREATE SCHEMA %I', '$schema');
    END IF;
  END
  $$;"
  PSQL "$PGURI" -q -c "$sql"
}

table_exists() {
  local schema="$1" table="$2"
  local q="SELECT 1
           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=$$${schema}$$ AND c.relname=$$${table}$$ AND c.relkind='r';"
  PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$'
}

sanitize_colname() {
  # Keep letters/digits/_ ; replace others with _ ; ensure starts with letter/_.
  local raw="$1"
  # strip CR and quotes and trim spaces
  raw="${raw%$'\r'}"
  raw="${raw//\"/}"
  # squeeze spaces around
  # shellcheck disable=SC2001
  raw="$(echo "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  local cleaned
  cleaned="$(echo "$raw" | tr -cs 'A-Za-z0-9_' '_' )"
  # ensure not empty
  [ -n "$cleaned" ] || cleaned="col"
  # ensure first char not a digit
  case "$cleaned" in
    [0-9]* ) cleaned="_$cleaned" ;;
  esac
  echo "$cleaned"
}

create_table_from_csv_header() {
  local schema="$1" table="$2" csv_path="$3"
  local header
  IFS= read -r header < "$csv_path" || die "Failed to read header from $csv_path"
  [ -n "$header" ] || die "Empty CSV header in $csv_path"

  # Split by commas into array (Bash 3.2 supports arrays)
  local IFS=',' cols=()
  # shellcheck disable=SC2206
  cols=($header)

  local coldefs=""
  local i
  for i in "${!cols[@]}"; do
    local c
    c="$(sanitize_colname "${cols[$i]}")"
    if [ "$i" -gt 0 ]; then coldefs="$coldefs, "; fi
    coldefs="$coldefs\"$c\" text"
  done

  ensure_schema "$schema"
  local ddl="CREATE TABLE \"$schema\".\"$table\" ( $coldefs );"
  PSQL "$PGURI" -q -c "$ddl"
}

# Derive destination table from filename base (no regex)
# Accepts names like:
#   <instance>_<schema.table>
#   <instance>_<schema.table>_<timecol>_<YYYY-MM or YYYY-MM-DD>
#   or without the instance prefix.
derive_dest_table_from_base() {
  local base="$1" instance="$2"

  # If starts with "<instance>_", strip it
  case "$base" in
    "${instance}_"*) base="${base#${instance}_}" ;;
  esac

  # schema.table is up to first underscore, or whole string if none
  local schema_table rest
  case "$base" in
    *_*)
      schema_table="${base%%_*}"
      rest="${base#${schema_table}_}"
      ;;
    *)
      schema_table="$base"
      rest=""
      ;;
  esac

  case "$schema_table" in
    *.*) : ;;
    *) die "Cannot parse schema.table from '$base'";;
  esac

  DEST_SCHEMA="${schema_table%%.*}"
  DEST_TABLE="${schema_table##*.}"

  # If there is "rest", append to table to keep timecol/date suffix in table name
  if [ -n "$rest" ]; then
    DEST_TABLE="${DEST_TABLE}_$rest"
  fi

  is_valid_ident "$DEST_SCHEMA" || die "Invalid schema parsed from filename: '$DEST_SCHEMA'"
  # Allow underscores in appended parts; sanitize double underscores later if needed
}

# ---------- RESTORE ----------
do_restore() {
  local instance="$1" input="$2"; shift 2
  resolve_instance "$instance"

  [ -f "$input" ] || die "File not found: $input"

  local work_csv="$input"
  local tmp_csv=""
  case "$input" in
    *.gz)
      need_cmd gunzip
      tmp_csv="$(mktemp -t pgtool_restore_XXXX).csv"
      gunzip -c "$input" > "$tmp_csv"
      work_csv="$tmp_csv"
      ;;
    *.csv)
      : ;; # use as-is
    *)
      die "Input must be .csv or .csv.gz"
      ;;
  esac

  local base
  base="$(basename "$work_csv")"
  base="${base%.csv}"  # strip suffix

  derive_dest_table_from_base "$base" "$instance"

  info "Restoring into: $DEST_SCHEMA.$DEST_TABLE"

  if table_exists "$DEST_SCHEMA" "$DEST_TABLE"; then
    warn "Destination table $DEST_SCHEMA.$DEST_TABLE already exists; rows will be appended."
    warn "Pass --force-append to suppress this warning."
  else
    info "Creating $DEST_SCHEMA.$DEST_TABLE from CSV header (all columns TEXT)"
    create_table_from_csv_header "$DEST_SCHEMA" "$DEST_TABLE" "$work_csv"
  fi

  local copy_sql="\\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT csv, HEADER)"
  PSQL "$PGURI" -q -c "$copy_sql" < "$work_csv"
  info "Restore complete into: $DEST_SCHEMA.$DEST_TABLE"

  [ -n "${tmp_csv:-}" ] && rm -f "$tmp_csv"
}

# ---------- MAIN ----------
[ $# -lt 1 ] && usage
cmd="$1"; shift || true

case "$cmd" in
  backup)
    [ $# -ge 2 ] || usage
    need_cmd psql
    do_backup "$@"
    ;;
  restore)
    [ $# -ge 2 ] || usage
    need_cmd psql
    do_restore "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    die "Unknown command '$cmd' (use backup|restore)"
    ;;
esac
```
### python
```python
#!/usr/bin/env python3
"""
pgtool.py — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)

Requires: Python 3.8+, psycopg2-binary
  pip install psycopg2-binary

Usage:
  # Full-table backup (gzip by default)
  python pgtool.py backup dev weavix.silver.mytable

  # Month partial backup (January 2025) using timestamptz column "timecol"
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01

  # Day partial backup, no compression, custom dest dir
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01-15 --no-compress --dest /tmp

  # Restore from file; auto-creates table (TEXT cols) if it doesn't exist; appends if it does
  python pgtool.py restore dev /backups/dev_weavix.silver.mytable_timecol_2025-01.csv.gz
"""

import argparse
import csv
import gzip
import io
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import sql

# -------- Instance configuration (override with env) --------
DEST_DEFAULTS = {
    "dev":   os.environ.get("PGTOOL_DEST_DEV",   "/var/backups/pg/dev"),
    "prod":  os.environ.get("PGTOOL_DEST_PROD",  "/var/backups/pg/prod"),
    "test":  os.environ.get("PGTOOL_DEST_TEST",  "/var/backups/pg/test"),
    "local": os.environ.get("PGTOOL_DEST_LOCAL", "/var/backups/pg/local"),
}

PGURI = {
    "dev":   os.environ.get("PGURI_DEV",   "postgres://localhost:5432/postgres"),
    "prod":  os.environ.get("PGURI_PROD",  "postgres://localhost:5432/postgres"),
    "test":  os.environ.get("PGURI_TEST",  "postgres://localhost:5432/postgres"),
    "local": os.environ.get("PGURI_LOCAL", "postgres://localhost:5432/postgres"),
}
# ------------------------------------------------------------

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SCHEMA_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")
MONTH_FMT_RE = re.compile(r"^\d{4}-\d{2}$")
DAY_FMT_RE   = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def info(msg: str):
    print(f"INFO:  {msg}", file=sys.stderr)

def warn(msg: str):
    print(f"WARN:  {msg}", file=sys.stderr)

def assert_ident(name: str, kind: str = "identifier"):
    if not IDENT_RE.match(name or ""):
        die(f"Invalid {kind}: {name!r}")

def assert_schema_table(qual: str):
    if not SCHEMA_TABLE_RE.match(qual or ""):
        die(f"Invalid table name {qual!r} (expected schema.table)")

@contextmanager
def connect(instance: str):
    dsn = PGURI.get(instance)
    if not dsn:
        die(f"Unknown instance {instance!r} (expected dev|prod|test|local)")
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()

def qualify(schema_table: str):
    assert_schema_table(schema_table)
    schema, table = schema_table.split(".", 1)
    return schema, table

def time_window_sql(timecol: str, date_arg: str) -> sql.SQL:
    assert_ident(timecol, "column")
    if MONTH_FMT_RE.match(date_arg):
        # [first day of month, first day of next month)
        return sql.SQL(
            "({col} >= date_trunc('month', to_date(%s,'YYYY-MM-DD')) "
            "AND {col} < (date_trunc('month', to_date(%s,'YYYY-MM-DD')) + interval '1 month'))"
        ).format(col=sql.Identifier(timecol)), [f"{date_arg}-01", f"{date_arg}-01"]
    if DAY_FMT_RE.match(date_arg):
        # [day, next day)
        return sql.SQL(
            "({col} >= to_timestamp(%s,'YYYY-MM-DD') "
            "AND {col} < (to_timestamp(%s,'YYYY-MM-DD') + interval '1 day'))"
        ).format(col=sql.Identifier(timecol)), [date_arg, date_arg]
    die("Invalid --date (use YYYY-MM or YYYY-MM-DD)")

def validate_timecol(conn, schema: str, table: str, col: str):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s
              AND data_type='timestamp with time zone'
        """, (schema, table, col))
        if not cur.fetchone():
            die(f"Column {schema}.{table}.{col} not found or not timestamptz")

def default_dest(instance: str) -> Path:
    d = DEST_DEFAULTS.get(instance)
    if not d:
        die(f"No default destination configured for instance {instance!r}")
    return Path(d)

def build_backup_filename(instance: str, schema: str, table: str,
                          timecol: str | None, date_arg: str | None) -> str:
    if timecol and date_arg:
        return f"{instance}_{schema}.{table}_{timecol}_{date_arg}.csv"
    return f"{instance}_{schema}.{table}.csv"

def backup(args):
    instance = args.instance
    schema, table = qualify(args.schema_table)
    dest_dir = Path(args.dest or default_dest(instance))
    dest_dir.mkdir(parents=True, exist_ok=True)

    timecol = args.timecol
    date_arg = args.date

    with connect(instance) as conn, conn.cursor() as cur:
        where_sql = None
        where_params = []
        if (timecol and not date_arg) or (date_arg and not timecol):
            die("Partial backup requires BOTH --timecol and --date")
        if timecol and date_arg:
            validate_timecol(conn, schema, table, timecol)
            where_sql, where_params = time_window_sql(timecol, date_arg)

        filename = build_backup_filename(instance, schema, table, timecol, date_arg)
        out_path = dest_dir / filename
        compress = not args.no_compress

        # Build COPY command
        if where_sql is None:
            copy_sql = sql.SQL("COPY {}.{} TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
            params = None
        else:
            copy_sql = sql.SQL(
                "COPY (SELECT * FROM {}.{} WHERE {} ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
            ).format(
                sql.Identifier(schema),
                sql.Identifier(table),
                where_sql
            )
            params = where_params

        info(f"Backing up {schema}.{table} -> {out_path}{'.gz' if compress else ''}")

        if compress:
            with gzip.open(str(out_path) + ".gz", "wb") as gz:
                cur.copy_expert(copy_sql.as_string(conn), gz, vars=params)
            info(f"Backup complete: {out_path}.gz")
        else:
            with open(out_path, "wb") as f:
                cur.copy_expert(copy_sql.as_string(conn), f, vars=params)
            info(f"Backup complete: {out_path}")

def sanitize_colname(raw: str) -> str:
    # Strip quotes and spaces, keep A-Za-z0-9_, replace others with _
    raw = raw.replace('"', '').strip()
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', raw)
    if not cleaned:
        cleaned = "col"
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned

def ensure_schema(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s) THEN
            EXECUTE format('CREATE SCHEMA %I', %s);
          END IF;
        END $$;
        """, (schema, schema))
        conn.commit()

def table_exists(conn, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname=%s AND c.relname=%s AND c.relkind='r'
        """, (schema, table))
        return cur.fetchone() is not None

def create_table_from_csv_header(conn, schema: str, table: str, header_line: str):
    # Build TEXT columns from CSV header
    reader = csv.reader([header_line])
    cols = next(reader)
    if not cols:
        die("Empty CSV header; cannot create table")

    cleaned = [sanitize_colname(c) for c in cols]
    # Build DDL
    col_list = sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in cleaned)
    ddl = sql.SQL("CREATE TABLE {}.{} (").format(sql.Identifier(schema), sql.Identifier(table))
    ddl = sql.SQL("").join([ddl, col_list, sql.SQL(")")])

    ensure_schema(conn, schema)
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()

def parse_dest_table_from_filename(path: Path, instance: str) -> tuple[str, str]:
    """
    Accepts file names like:
      <instance>_<schema.table>.csv[.gz]
      <instance>_<schema.table>_<timecol>_<YYYY-MM>.csv[.gz]
      <schema.table>_<timecol>_<YYYY-MM-DD>.csv
      <schema.table>.csv
    Restored table name includes any suffix after schema.table, appended to the base table.
    """
    base = path.name
    if base.endswith(".gz"): base = base[:-3]
    if base.endswith(".csv"): base = base[:-4]

    # Strip leading "<instance>_"
    prefix = f"{instance}_"
    if base.startswith(prefix):
        base = base[len(prefix):]

    # schema.table is up to first underscore (if any)
    parts = base.split("_", 1)
    schema_table = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if not SCHEMA_TABLE_RE.match(schema_table):
        die(f"Cannot parse schema.table from filename: {path.name}")

    schema, table = schema_table.split(".", 1)
    if rest:
        table = f"{table}_{rest}"
    return schema, table

def restore(args):
    instance = args.instance
    infile = Path(args.input)
    if not infile.exists():
        die(f"Input file not found: {infile}")

    with connect(instance) as conn:
        # Open file (gzip or plain)
        if infile.suffix == ".gz":
            opener = lambda p: io.TextIOWrapper(gzip.open(p, "rb"), newline="")
        else:
            opener = lambda p: open(p, "rt", newline="")

        with opener(str(infile)) as f:
            # Peek header safely without losing it
            header_pos = f.tell()
            header_line = f.readline()
            if not header_line:
                die("Input file is empty")
            # Normalize header (ensure one line without trailing newline)
            header_line = header_line.rstrip("\r\n")
            f.seek(header_pos)

            schema, table = parse_dest_table_from_filename(infile, instance)
            info(f"Restoring into: {schema}.{table}")

            # Create table if not exists; warn otherwise
            if table_exists(conn, schema, table):
                warn(f"Destination table {schema}.{table} already exists; rows will be appended.")
                if not args.force_append:
                    warn("Pass --force-append to suppress this warning.")
            else:
                info("Creating table from CSV header (all columns TEXT)")
                create_table_from_csv_header(conn, schema, table, header_line)

            # COPY FROM STDIN
            with conn.cursor() as cur:
                copy_sql = sql.SQL("COPY {}.{} FROM STDIN WITH (FORMAT csv, HEADER)").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
                cur.copy_expert(copy_sql.as_string(conn), f)
            conn.commit()
            info("Restore complete.")

def main():
    parser = argparse.ArgumentParser(prog="pgtool.py", description="Postgres CSV backup/restore (gzip by default)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_b = sub.add_parser("backup", help="Backup a table to CSV/.csv.gz")
    p_b.add_argument("instance", choices=PGURI.keys())
    p_b.add_argument("schema_table", help="Fully-qualified table name, e.g. weavix.silver.mytable")
    p_b.add_argument("--timecol", help="timestamptz column for date filtering")
    p_b.add_argument("--date", help="YYYY-MM or YYYY-MM-DD to filter by")
    p_b.add_argument("--no-compress", action="store_true", help="Write plain .csv instead of .csv.gz")
    p_b.add_argument("--dest", help="Destination folder (defaults by instance)")
    p_b.set_defaults(func=backup)

    p_r = sub.add_parser("restore", help="Restore CSV/.csv.gz into a table (auto-creates if needed)")
    p_r.add_argument("instance", choices=PGURI.keys())
    p_r.add_argument("input", help="Path to .csv or .csv.gz file")
    p_r.add_argument("--force-append", action="store_true", help="Suppress warning when table exists")
    p_r.set_defaults(func=restore)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

```


## Grok

## Claude


