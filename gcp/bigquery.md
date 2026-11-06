## BigQuery
Since you already know Databricks and Snowflake well, I'll teach BigQuery by comparing it to those and focus on what's actually different.

## 1. The mental model

BigQuery is a **serverless** warehouse. There are no clusters or warehouses for you to size, start, or stop. You send SQL, and Google runs it on a shared fleet. There are two layers:

- **Storage (Colossus):** a columnar format called Capacitor. This plays the role of Delta or Parquet files plus Snowflake micro-partitions, but you never see the files.
- **Compute (Dremel):** queries run on **slots**, which are units of CPU, RAM, and shuffle. A slot is roughly like one Spark executor core, except Google schedules it for you.

Shuffle goes through a separate in-memory shuffle tier instead of local disks. That's a big reason huge joins and GROUP BYs don't fail with out-of-memory errors the way Spark jobs sometimes do.

## 2. Resource hierarchy (vs. Unity Catalog)

| BigQuery | Unity Catalog | Snowflake |
|---|---|---|
| Project | Catalog (roughly, plus the billing boundary) | Account / database |
| Dataset | Schema | Schema |
| Table / view / routine | Table / view / function | Table / view / UDF |

A fully qualified name looks like `` `my-project.my_dataset.my_table` ``. You need the backticks when the project ID contains hyphens. Each dataset has a fixed **location** (`US`, `EU`, `us-central1`…), and a single query can't join datasets in different locations.

## 3. How you pay

This shapes how you write queries, so it comes before SQL.

- **On-demand:** you pay per TiB your queries scan. The first 1 TiB per month is free, and after that the rate is $6.25 per TiB in U.S. regions. You don't buy slots directly. Google allocates up to 2,000 shared slots per project in the background.
- **Capacity (Editions):** billing is per slot-hour instead of per byte processed, which gives you dedicated compute capacity over time. The tiers are Standard, Enterprise, and Enterprise Plus. Google retired the legacy flat-rate model and replaced it entirely with editions-based pricing.

The rule that follows from on-demand pricing: **you pay for the columns you read, not the rows you return.** So:

```sql
SELECT * FROM t LIMIT 10;          -- scans EVERY column of the whole table. LIMIT doesn't reduce cost.
SELECT user_id, ts FROM t WHERE dt = '2026-11-01';  -- scans 2 columns of 1 partition
```

Always check the bytes estimate before you run a query. It appears in the UI, or you can get it with `bq query --dry_run`. You can also cap a query's cost with `maximum_bytes_billed`.

## 4. Table design: partitioning and clustering

These are your two main levers. They correspond to Delta partitioning and Z-order/liquid clustering.

```sql
CREATE TABLE analytics.events (
  event_ts   TIMESTAMP,
  user_id    STRING,
  device_id  STRING,
  event_type STRING,
  payload    JSON
)
PARTITION BY DATE(event_ts)              -- or an INTEGER range, or ingestion time
CLUSTER BY device_id, event_type         -- up to 4 columns, order matters
OPTIONS (
  partition_expiration_days = 400,
  require_partition_filter = TRUE        -- rejects queries that forget a dt filter
);
```

- **Partitioning** prunes data predictably, and the dry-run estimate reflects it. A table can have at most about 10k partitions, so partition by day, not by hour or user.
- **Clustering** sorts data inside each partition. Google re-clusters automatically in the background for free. The pruning shows up in the actual bytes billed, often well below the dry-run estimate.
- `require_partition_filter` is the most useful safety rail when other people query your tables.

## 5. Nested and repeated data

This is the biggest change in mindset. BigQuery encourages **denormalizing with `STRUCT` and `ARRAY`** instead of joining.

```sql
CREATE TABLE shop.orders (
  order_id STRING,
  customer STRUCT<id STRING, name STRING, tier STRING>,
  items    ARRAY<STRUCT<sku STRING, qty INT64, price NUMERIC>>
);

-- Flatten with UNNEST (like Spark's explode)
SELECT o.order_id, o.customer.tier, i.sku, i.qty * i.price AS line_total
FROM shop.orders AS o, UNNEST(o.items) AS i
WHERE i.qty > 1;

-- Aggregate back into arrays
SELECT customer.id, ARRAY_AGG(STRUCT(order_id, ts) ORDER BY ts DESC LIMIT 5) AS last_5
FROM shop.orders GROUP BY 1;
```

The comma before `UNNEST` is an implicit `CROSS JOIN`. Use `LEFT JOIN UNNEST(...)` if you want to keep rows that have empty arrays.

## 6. GoogleSQL features worth knowing

```sql
-- QUALIFY: dedupe/latest-row without a subquery (same as Snowflake/Databricks)
SELECT * FROM raw.telemetry
QUALIFY ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY event_ts DESC) = 1;

-- SAFE_ functions return NULL instead of failing the query
SELECT SAFE_CAST(x AS INT64), SAFE_DIVIDE(a, b), SAFE.PARSE_DATE('%Y%m%d', s);

-- SELECT * EXCEPT / REPLACE
SELECT * EXCEPT (payload) REPLACE (LOWER(event_type) AS event_type) FROM analytics.events;

-- Wildcard tables (legacy sharded tables like events_20261101)
SELECT COUNT(*) FROM `proj.ga4.events_*` WHERE _TABLE_SUFFIX BETWEEN '20261101' AND '20261107';

-- Approximate aggregates (cheap at scale)
SELECT APPROX_COUNT_DISTINCT(user_id), APPROX_QUANTILES(latency_ms, 100)[OFFSET(99)] AS p99 FROM t;

-- Time travel (7 days by default)
SELECT * FROM analytics.events FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);
```

A few differences that trip people up:
- Types are `INT64`, `FLOAT64`, `NUMERIC`/`BIGNUMERIC`, `STRING`, and `BYTES`. There's no `VARCHAR(n)` or `INT`; they're accepted only as aliases.
- `TIMESTAMP` is always UTC. `DATETIME` has no timezone. Mixing them up is a common bug.
- Array indexing uses `arr[OFFSET(0)]` (0-based) or `arr[ORDINAL(1)]`. `arr[SAFE_OFFSET(n)]` returns NULL when out of range.
- There are no indexes and no enforced primary or foreign keys. You can declare them `NOT ENFORCED` so the optimizer can use them.

## 7. Getting data in and out

| Method | Use when | Databricks analogue |
|---|---|---|
| `LOAD DATA` / `bq load` from GCS | Batch files (Parquet, Avro, ORC, CSV, JSON). **Free**, you pay only for storage | `COPY INTO` |
| **Storage Write API** | Streaming or high-throughput writes with exactly-once semantics | Structured Streaming sink |
| External / **BigLake** tables | Query files in GCS (or S3/Azure via Omni) without loading them, including Iceberg | External tables |
| Datastream / Pub/Sub → BQ subscriptions | CDC from Postgres/MySQL, or event streams | DLT / Auto Loader |
| Storage Read API | Spark, pandas, or Arrow reading BQ in parallel | Delta Sharing / direct reads |

Upserts use `MERGE`, as in Delta:

```sql
MERGE analytics.devices T
USING staging.devices_delta S
ON T.device_id = S.device_id
WHEN MATCHED THEN UPDATE SET T.status = S.status, T.updated_at = S.updated_at
WHEN NOT MATCHED THEN INSERT ROW;
```

BigQuery handles DML in batches. Lots of tiny `UPDATE`s or single-row `INSERT`s are an anti-pattern. Stage the changes and `MERGE` them in bulk.

## 8. Precomputation and performance

- **Materialized views:** maintained incrementally, and the optimizer can **automatically rewrite** queries against the base table to use them.
- **Search indexes and vector indexes:** for needle-in-haystack lookups and `VECTOR_SEARCH`.
- **Query plan:** the "Execution details" tab shows each stage's slot time, bytes shuffled, and skew. Read it the way you'd read the Spark UI. Watch for one stage taking most of the time, or a large gap between max and average worker time (skew).
- **INFORMATION_SCHEMA.JOBS:** your best tool for cost auditing.

```sql
SELECT user_email, query, total_bytes_billed/POW(1024,4) AS tib, total_slot_ms
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY total_bytes_billed DESC LIMIT 20;
```

## 9. Beyond SQL

- **Scripting and procedures:** `DECLARE`, `IF`, `LOOP`, `BEGIN TRANSACTION` (multi-statement transactions).
- **UDFs** in SQL or JavaScript, **remote functions** that call Cloud Run or Cloud Functions, and table functions.
- **BigQuery ML:** `CREATE MODEL ... OPTIONS(model_type='boosted_tree_classifier')`, `ML.PREDICT`, plus remote models over Vertex/Gemini (`AI.GENERATE`-style functions).
- **Security:** IAM at the project, dataset, and table level, plus row-level access policies, column-level security through policy tags, and authorized views. This is Google's version of Unity Catalog's grants and row filters.
- **Orchestration:** scheduled queries, Dataform (BigQuery's built-in dbt-like tool), or Composer (Airflow).

## 10. A two-hour hands-on path

1. Open the BigQuery console in a free sandbox project, which needs no credit card.
2. Query public data, for example `bigquery-public-data.github_repos` or `bigquery-public-data.thelook_ecommerce`. Before running each query, predict the bytes scanned and compare it with the dry run.
3. Copy a table into your own dataset with `PARTITION BY` and `CLUSTER BY`. Run the same filtered query against the original and your copy, and compare bytes billed and slot time.
4. Rewrite a two-table join (orders and order_items) as a nested `ARRAY<STRUCT>` table and query it with `UNNEST`.
5. Run the `INFORMATION_SCHEMA.JOBS` query above on your own history.

## Cheat sheet: habits to unlearn

- **No cluster tuning.** Your levers are the bytes scanned (on-demand) and slot usage (editions).
- **`LIMIT` doesn't save money,** and `SELECT *` is expensive.
- **Denormalize with nested types** instead of designing a star schema with many joins.
- **No `OPTIMIZE` or `VACUUM`.** Compaction and re-clustering happen automatically.
- **Batch your DML.** BigQuery isn't an OLTP store.

If you want, I can write a set of practice exercises with answers, compare BigQuery with Databricks side by side in more depth, or turn this into a cheat-sheet doc you can keep.

Sources:
- [BigQuery pricing (Google Cloud)](https://cloud.google.com/bigquery/pricing.html)
- [DoiT: BigQuery cost optimization 2026](https://www.doit.com/blog/bigquery-cost-optimization)
- [Revefi: Definitive Guide to BigQuery Pricing](https://www.revefi.com/blog/google-bigquery-pricing-guide)
- [Yuki: BigQuery Costs guide](https://yukidata.com/google-bigquery-costs/)
- [nOps: BigQuery editions pricing](https://www.nops.io/?p=33316)


## 1. Does BigQuery have its own storage?

Yes. BigQuery is both a storage system and a query engine. By default it keeps data in Google's own managed columnar storage (Capacitor files on Colossus). You never see those files, can't list them, and can't read them with another engine, except through the BigQuery Storage Read API.

It can also act as a plain SQL engine over data stored somewhere else. That's where its version of managed vs. external tables comes in.

## 2. Managed vs. external tables

The idea maps closely to Databricks:

| BigQuery | What it is | Databricks analogue |
|---|---|---|
| **Native (managed) table** | Data in BigQuery's internal storage. Full DML, time travel, clustering, streaming. `DROP TABLE` deletes the data. | Managed Delta table |
| **External table** | Only metadata in BigQuery. Files stay in GCS (or Google Drive or Bigtable). Read-only, slower, and no caching or clustering benefits. `DROP` leaves the files alone. | External table (`LOCATION 's3://...'`) |
| **BigLake table** | An external table plus a *connection*. Users don't need GCS permissions, and you get BigQuery's row- and column-level security, metadata caching, and Iceberg/Delta/Hudi support. Can also point at S3 or ADLS (BigQuery Omni). | Unity Catalog external table with a storage credential |
| **BigLake Iceberg tables in BigQuery** | BigQuery *writes* Iceberg/Parquet into **your** GCS bucket. You get full DML, and other engines (Spark, Trino) can read the same files. | Managed table with an open format, or Delta + UniForm |
| **Federated queries** | `EXTERNAL_QUERY()` against Cloud SQL, AlloyDB, or Spanner. The query is pushed down live. | Lakehouse Federation |

Examples:

```sql
-- External table over Parquet in GCS
CREATE EXTERNAL TABLE raw.events_ext
OPTIONS (format = 'PARQUET', uris = ['gs://my-bucket/events/*.parquet']);

-- With Hive-style partitions (dt=2026-11-01/)
CREATE EXTERNAL TABLE raw.events_ext
WITH PARTITION COLUMNS
OPTIONS (format='PARQUET',
         uris=['gs://my-bucket/events/*'],
         hive_partition_uri_prefix='gs://my-bucket/events');

-- BigLake (governed) table: add a connection
CREATE EXTERNAL TABLE raw.events_lake
WITH CONNECTION `my-project.us.my_gcs_conn`
OPTIONS (format='PARQUET', uris=['gs://my-bucket/events/*']);

-- Federated query to Cloud SQL Postgres
SELECT * FROM EXTERNAL_QUERY('my-project.us.pg_conn',
  'SELECT id, status FROM orders WHERE updated_at > now() - interval ''1 day''');
```

**Rule of thumb:**
- Use native tables for anything that's queried often. They're faster, and storage that hasn't been modified for 90 days gets a lower price automatically.
- Use external or BigLake tables for raw landing zones, or for data other engines also need to own.
- If you want an open format that Spark can also write to, use Iceberg.

## 3. BigQuery with Airflow

You'd usually run Airflow either as **Cloud Composer** (Google's managed Airflow) or self-hosted, with the `apache-airflow-providers-google` package. Authentication uses the `google_cloud_default` connection, backed by a service account or Workload Identity.

The main building blocks:

| Task | Operator / sensor |
|---|---|
| Run any SQL (query, DML, DDL) | `BigQueryInsertJobOperator`, the modern catch-all |
| Load GCS files into a table | `GCSToBigQueryOperator` |
| Export a table to GCS | `BigQueryToGCSOperator` |
| Wait for files to land | `GCSObjectExistenceSensor` / `GCSObjectsWithPrefixExistenceSensor` |
| Wait for a table or partition | `BigQueryTableExistenceSensor`, `BigQueryTablePartitionExistenceSensor` |
| Data-quality gates | `BigQueryCheckOperator`, `BigQueryValueCheckOperator`, `BigQueryColumnCheckOperator` |
| Create or drop datasets and tables | `BigQueryCreateEmptyDatasetOperator`, etc. (or just DDL through InsertJob) |

Older guides use `BigQueryExecuteQueryOperator`. It's deprecated, so use `BigQueryInsertJobOperator` instead.

A typical daily ELT DAG: wait for files, load them to staging, MERGE into the target, then check quality.

```python
from datetime import datetime
from airflow import DAG
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator, BigQueryCheckOperator,
)

PROJECT = "my-project"
BUCKET = "my-landing-bucket"

with DAG(
    dag_id="events_daily",
    start_date=datetime(2026, 11, 1),
    schedule="@daily",
    catchup=True,
    max_active_runs=1,
    default_args={"retries": 2},
) as dag:

    wait_for_files = GCSObjectsWithPrefixExistenceSensor(
        task_id="wait_for_files",
        bucket=BUCKET,
        prefix="events/dt={{ ds }}/",
        mode="reschedule",            # frees the worker slot while waiting
        poke_interval=300,
        timeout=6 * 3600,
    )

    load_staging = GCSToBigQueryOperator(
        task_id="load_staging",
        bucket=BUCKET,
        source_objects=["events/dt={{ ds }}/*.parquet"],
        source_format="PARQUET",
        # $YYYYMMDD decorator = write only that partition → idempotent reruns
        destination_project_dataset_table=f"{PROJECT}.staging.events${{{{ ds_nodash }}}}",
        write_disposition="WRITE_TRUNCATE",
        time_partitioning={"type": "DAY", "field": "event_ts"},
    )

    merge_into_target = BigQueryInsertJobOperator(
        task_id="merge_into_target",
        configuration={
            "query": {
                "query": """
                    MERGE analytics.events T
                    USING (
                      SELECT * FROM staging.events
                      WHERE DATE(event_ts) = '{{ ds }}'
                      QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_ts DESC) = 1
                    ) S
                    ON T.event_id = S.event_id AND DATE(T.event_ts) = '{{ ds }}'
                    WHEN MATCHED THEN UPDATE SET payload = S.payload
                    WHEN NOT MATCHED THEN INSERT ROW
                """,
                "useLegacySql": False,
                "maximumBytesBilled": str(500 * 1024**3),   # cost guardrail
            },
            "labels": {"dag": "events_daily"},              # shows up in INFORMATION_SCHEMA.JOBS
        },
        location="US",
    )

    quality_check = BigQueryCheckOperator(
        task_id="quality_check",
        sql="""
            SELECT COUNT(*) > 0 AND COUNTIF(device_id IS NULL) = 0
            FROM analytics.events WHERE DATE(event_ts) = '{{ ds }}'
        """,
        use_legacy_sql=False,
        location="US",
    )

    wait_for_files >> load_staging >> merge_into_target >> quality_check
```

**Patterns that matter in practice:**
- **Make tasks idempotent per partition.** Write with `WRITE_TRUNCATE` to `table$YYYYMMDD`, or MERGE on a key restricted to `{{ ds }}`. That way retries and backfills are safe. It's the same discipline as `replaceWhere` in Delta.
- **Keep SQL in `.sql` files.** Set `template_searchpath` on the DAG and pass `"query": "{% include 'sql/merge_events.sql' %}"`.
- **Let BigQuery do the work.** Airflow should only orchestrate. Don't pull data into the worker with `BigQueryHook().get_pandas_df()` unless it's small.
- **Use `deferrable=True`** on InsertJob and the sensors. Long BigQuery jobs then wait in the triggerer instead of occupying a worker.
- **Add job labels and `maximumBytesBilled`.** They let you attribute cost per DAG and stop a bad query before it becomes expensive.
- **Consider Dataform or dbt for the transformation layer.** Many teams have Airflow trigger a Dataform or dbt run for the SQL models, and keep Airflow for ingestion, sensors, and cross-system dependencies.

If you'd like, I can sketch how the same pipeline would look as a Databricks Workflow next to this Airflow version. That kind of comparison tends to come up in interviews.
