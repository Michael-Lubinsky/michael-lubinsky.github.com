## BigQuery
 

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


BigQuery doesn't have version numbers. It's a fully managed service that Google updates continuously, so there's no "BigQuery 3.x" to upgrade to. BigQuery automatically updates to the latest release and cannot be downgraded to a previous version. Two things do carry versions: the client pieces (the Python/Java SDKs, the `bq` CLI, the JDBC/ODBC drivers) and the Airflow provider package. The **release notes page** works as the changelog, and each feature moves from Preview to GA.

This is different from Databricks, where the Runtime (DBR 16.x, 17.x) and the Spark version are things you choose per cluster.

## Notable changes in 2026

The highlights below come from the official release notes, grouped by theme.  

**Engine and SQL**
- The BigQuery advanced runtime became the default runtime for all projects as of March 12, 2026. It's the performance engine upgrade, with things like enhanced vectorization.
- Legacy SQL is being phased out. From June 1, 2026, projects that didn't use legacy SQL between November 1, 2025 and June 1, 2026 can no longer use it. Projects that did use it keep existing workloads running, but new ones might not.
- **Global queries** (February 2026) let a single SQL statement explore data distributed across regions. This loosens the "datasets must be in the same location" rule I mentioned in the first lesson.
- October 2026: you can copy tables across regions (GA), and GoogleSQL now supports reusable column aliases.
- Query results can now be retrieved directly in Apache Arrow format for faster retrieval and better serialization efficiency (Preview, Oct 30).
- A new REGEXP_EXTRACT_GROUPS function returns substrings that match multiple capturing groups in a regex (Preview).
- Parameterized queries can now be run from the query editor in the console (GA, Feb 2026).

**Graph**
- BigQuery Graph is GA, with support for the CALL graph query statement and path-inspection GQL functions such as IS_ACYCLIC, IS_SIMPLE and IS_TRAIL. This lets you run property-graph queries (GQL) directly over BigQuery tables. One caveat for planning: starting April 26, 2027, core graph processing will be restricted to the Enterprise and Enterprise Plus editions.

**Lakehouse, Iceberg and cross-cloud**
- Federation from SAP BDC lets you create Delta Sharing catalogs in Lakehouse that automatically sync shares, schemas and tables.
- October 2026 added guides for migrating Delta Lake and Apache Iceberg CDC data into Lakehouse using Dataflow. That's relevant if you're bridging from Databricks.
- In August, new connections arrived for data in AWS, Azure, and Salesforce Data 360 from all BigQuery regions, which support more BigQuery features and are more cost-efficient than standard BigQuery Omni connections.

**AI in SQL (most of the release volume)**
- New generative SQL functions: AI.IF, AI.SCORE, and AI.CLASSIFY, which can analyze unstructured data stored in Object Tables.
- AI.CHUNK_DOCUMENT is a table-valued function that splits unstructured documents into semantically coherent chunks for embeddings and RAG. In the same month, AI.AGG gained an output_schema argument (GA).
- **Autonomous embeddings** (June): when enabled on a table via CREATE TABLE or ALTER TABLE, BigQuery maintains a column of embeddings based on a source column.
- Vector indexes can be rebuilt without downtime (GA).
- Time series: the TimesFM 3.0 model is in Preview, and AI.CAUSAL_EFFECT quantifies the impact of interventions on time series data.
- BQML: models can now be trained with XGBoost 2.1 using the XGBOOST_VERSION option.

**Agents and conversational analytics**
- Conversational analytics in BigQuery is now GA. It lets you ask questions in natural language over datasets.
- The Data Engineering Agent was introduced for pipeline maintenance, alongside a Data Science Agent for feature suggestions and notebook generation.
- The run_bq_command tool exposes the bq CLI through the Cloud CLI remote MCP server, so AI agents can drive BigQuery.

**Governance, ops and ingestion**
- The BigQuery Security center is now available in the console (September 30).
- Data governance tags are Resource Manager tags you attach to sensitive columns and use in data policies for conditional access (Preview). They're similar to Unity Catalog's tag-based ABAC.
- In the console, Capacity management was renamed Workload management.
- Real-time logs for Python UDFs are now viewable in Cloud Logging (GA).
- Data Transfer Service: PostgreSQL to BigQuery transfers became GA, and incremental transfers for PostgreSQL and ServiceNow became GA in October.



Most of the AI and agent items are product marketing. For a data engineering conversation, these are the ones worth being able to discuss:

- Editions vs. on-demand pricing
- The advanced runtime being the default
- The legacy SQL sunset
- Global queries and cross-region copy
- Iceberg/Lakehouse interop and Delta CDC migration
- Graph going GA
- Governance tags

You can skim the full feed at the release notes link below. It's also exposed as a BigQuery public dataset, so you can query it with SQL.

Sources:
- [BigQuery release notes](https://docs.cloud.google.com/bigquery/docs/release-notes)
- [BigQuery global queries (Google Cloud blog)](https://cloud.google.com/blog/products/data-analytics/new-global-queries-in-bigquery-span-data-from-multiple-regions)
- [What's new in BigQuery AI (Google Cloud blog)](https://cloud.google.com/blog/topics/developers-practitioners/bigquery-ai-hackathon-celebrating-innovation-and-a-look-at-whats-new)
- [GCP Technology Nuggets, June 16–30, 2026](https://gcptechnuggets.substack.com/p/google-cloud-platform-technology-da9)

 
##   Object Tables

An **Object Table** is a read-only external table over **unstructured files** in Cloud Storage, such as images, PDFs, audio, and video. Each row is one file. The rows hold metadata and a reference to the file, not the file's contents:

```sql
CREATE EXTERNAL TABLE docs.invoices
WITH CONNECTION `my-project.us.gcs_conn`
OPTIONS (object_metadata = 'SIMPLE', uris = ['gs://my-bucket/invoices/*.pdf']);

SELECT uri, size, content_type, updated FROM docs.invoices;
```

Columns include `uri`, `size`, `content_type`, `updated`, `md5_hash`, and similar fields. Object Tables are useful because they bring unstructured data under the same SQL, IAM, and row-level security as your tables, and you can run AI functions or BQML models over the files:

```sql
-- Ask Gemini to extract fields from each PDF
SELECT uri, AI.GENERATE(('Extract invoice total and vendor from this file', ref)) AS extracted
FROM docs.invoices;

-- Or classify images
SELECT uri, AI.CLASSIFY(ref, categories => ['damaged', 'ok']) FROM photos.parts;
```

In Databricks terms, it's closest to a **Unity Catalog Volume** combined with `ai_query()` / `ai_extract()`. The difference is that BigQuery shows the files as a queryable table. Google is also adding `ObjectRef` (a `STRUCT` that points to a GCS object), so a row in a normal table can reference a file. For example, a `products` table can include an `image` column.

##   Editions vs. on-demand pricing

Both are ways to pay for **compute**. Storage is billed separately either way.

**On-demand** (the default):
- You pay for **bytes scanned**. The rate is $6.25 per TiB, with the first 1 TiB per month free per project. You don't buy slots; Google allocates up to 2,000 shared slots per project in the background.
- A query that scans 10 TiB costs about $62.50, whether it takes 5 seconds or 5 minutes.
- What you optimize is **bytes**: partitioning, clustering, selecting fewer columns.

**Editions** (capacity pricing):
- You pay for **slot-hours**, which is CPU time, no matter how many bytes are scanned.
- You create a **reservation** with a baseline (always-on slots) and a max (autoscale ceiling), then **assign** projects or folders to it. Autoscaling adds slots in small increments when needed and scales back down to the baseline.
- There are three tiers: **Standard**, **Enterprise**, and **Enterprise Plus**. Higher tiers cost more per slot-hour and add features. Enterprise adds things like BQML, BI Engine, row/column security, and longer commitments. Enterprise Plus adds things like CMEK and managed disaster recovery. For scale, at $0.06 per slot-hour, 100 Enterprise Edition slots running continuously for a month cost about $4,380, which is equivalent to scanning about 700 TiB on-demand at $6.25 per TiB.
- You can buy 1- or 3-year commitments for a discount on the baseline.
- What you optimize is **slot time**: avoiding heavy shuffles, skewed joins, and huge sorts. Bytes scanned don't matter directly.

**How to choose:**

| | On-demand | Editions |
|---|---|---|
| Bill driven by | Data scanned | Compute time |
| Best for | Spiky or ad-hoc workloads, small teams, exploration | Steady, heavy ETL and BI; predictable budgets |
| Risk | One bad `SELECT *` on a PB table is expensive | Idle baseline slots cost money; slots can cap throughput |
| Analogy | Snowflake/Databricks serverless "per query" | Snowflake warehouse / Databricks SQL warehouse billed by DBU-hour |

A common pattern is to put production ETL on an Enterprise reservation and leave analysts' sandbox projects on on-demand with `maximum_bytes_billed` caps. To decide with data, run your workload for a month and pull `total_bytes_billed` and `total_slot_ms` from `INFORMATION_SCHEMA.JOBS`. That gives you the on-demand cost and the slot-hours, so you can compare the two directly. Google's console also has a slot estimator that runs this calculation for you.

Sources:
- [DoiT: BigQuery cost optimization 2026](https://www.doit.com/blog/bigquery-cost-optimization)
- [BigQuery pricing (Google Cloud)](https://cloud.google.com/bigquery/pricing.html)


For a BigQuery Data Engineer interview, I recommend expanding your bigquery.md beyond explaining BigQuery architecture and SQL syntax.

Your existing topics provide a good foundation. The most valuable additions would focus on practical engineering decisions, troubleshooting, performance optimization, and production data pipelines.

An interviewer is likely to ask not only how BigQuery works, but also:
- Why did you choose a particular table design?
- Why is a query slow or expensive?
- How do you implement incremental ingestion and deduplication?
- How do you handle late-arriving events and backfills?
- How do you build reliable pipelines and control costs?
- How does BigQuery differ from Snowflake and Databricks in real-world workloads?
I would organize the additions into the following priorities.
1. Recommended new sections
Priority	Topic	What you should be able to explain
High	Query execution and troubleshooting	Slots, stages, shuffle, skew, execution plans
High	Partitioning and clustering	Partition pruning, clustering tradeoffs, reclustering
High	Incremental ELT and CDC	MERGE, deduplication, late events, idempotency
High	Cost optimization	Bytes scanned, slot consumption, reservations
High	Production data pipelines	Pub/Sub, Dataflow, GCS, BigQuery, Airflow
High	Data quality and testing	Assertions, reconciliation, schema evolution
Medium	Security and governance	IAM, row access policies, column masking
Medium	BigQuery internals	Dremel execution, shuffle, Capacitor
Medium	Monitoring and observability	INFORMATION_SCHEMA, job metrics, alerts
Medium	Dimensional modeling	Facts, dimensions, SCD Type 2
Medium	Semi-structured data	JSON, nested and repeated fields
Medium	BigQuery vs. Snowflake vs. Databricks	Architecture, optimization, workload selection

Some of these topics already appear in your document. I would deepen those sections with SQL examples, failure scenarios, and interview questions rather than repeat introductory explanations.
2. Five additions I would write first
A. How to debug a slow BigQuery query
This is one of the most valuable interview topics.

Add an example that investigates:
- High slot consumption versus high bytes scanned
- Broadcast joins versus hash/shuffle joins
- Data skew and high-cardinality joins
- Shuffle spill and insufficient shuffle capacity
- Slot contention and query concurrency
For example, add a diagnostic SQL query:
```sql
SELECT
  job_id,
  ROUND(total_bytes_processed / POW(1024, 3), 2)
    AS gb_processed,
  ROUND(total_slot_ms / 1000, 2)
    AS slot_seconds,
  TIMESTAMP_DIFF(
    end_time, start_time, SECOND
  ) AS duration_seconds
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(
    CURRENT_TIMESTAMP(), INTERVAL 1 DAY
  )
  AND job_type = 'QUERY'
  AND state = 'DONE'
  AND error_result IS NULL
ORDER BY total_slot_ms DESC
LIMIT 20;
```

Interview question: A query previously completed in 20 seconds. Today it takes 3 minutes, although the table size has not changed. How do you investigate?

A strong answer would compare execution plans, slot contention, shuffle volume, skew, and changes in query inputs or competing workloads. Google's execution graph and performance insights expose several of these diagnostics. 

Google Cloud Docs+1

B. CDC, deduplication, and idempotent MERGE
Your document already introduces MERGE, but production scenarios deserve more attention.

Consider a pipeline:
PostgreSQL

Datastream

BigQuery raw



Deduplicate + MERGE
Incremental transformation
BigQuery curated
Analytics-ready tables


Include the following SQL:
```sql
MERGE analytics.users AS target
USING (
  SELECT * EXCEPT(rn)
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY user_id
        ORDER BY updated_at DESC, sequence_num DESC
      ) AS rn
    FROM staging.users
  )
  WHERE rn = 1
) AS source
ON target.user_id = source.user_id

WHEN MATCHED
  AND source.updated_at > target.updated_at
THEN UPDATE SET
  name = source.name,
  updated_at = source.updated_at

WHEN NOT MATCHED THEN
  INSERT (user_id, name, updated_at)
  VALUES (source.user_id, source.name,
          source.updated_at);
```

Explain the assumptions: sequence_num provides deterministic ordering, the staging data has been validated, and the update policy must handle equal timestamps correctly.

Interview question: What happens if two source rows match the same target row in a BigQuery MERGE?

Explain why source deduplication is essential for an updating MERGE, and how to make repeated pipeline runs safe.
C. Incremental processing and backfills
Add a comparison of three strategies:
Strategy	Best use case	Risk
Watermark using updated_at	Incremental batch	Late-arriving records
Partition overwrite	Rebuild specific dates	Accidentally replacing incomplete partitions
MERGE by business key	CDC and upserts	Expensive target scans

A particularly good interview scenario:

You ingest 500 million telemetry events daily. Yesterday, you discovered that 10 days of data were processed incorrectly. How do you backfill without rebuilding the entire table?

Explain partition-scoped reprocessing, staging, validation, atomic replacement where applicable, and idempotency.
D. BigQuery data modeling: nested versus star schema
Your document recommends nested STRUCT and ARRAY fields. Add a more nuanced explanation of when not to denormalize.

For example, compare:
- A star schema with fact_orders, dim_customer, and dim_product.
- A denormalized orders table with repeated line items.
- Slowly changing dimensions requiring historical attributes.
Interview question: Should every BigQuery analytical model use nested data instead of a star schema?

Answer: No. Nested repeated data can avoid expensive joins for hierarchical records, but dimensional models remain valuable for shared dimensions, historical tracking, and consistent reporting.
E. BigQuery monitoring and cost governance
Add operational SQL examples covering:
- Identifying expensive users and queries
- Detecting queries scanning unexpected volumes
- Measuring slot utilization
- Monitoring failed jobs
- Detecting pipeline SLA violations
- Budget controls and maximum bytes billed
Also explain the distinction between reducing query runtime and reducing query cost. They are not necessarily the same optimization problem, especially across on-demand and capacity-based pricing.

Google's query optimization documentation is a useful reference. 

Google Cloud Docs

3. Add a dedicated interview questions section
I would finish the document with 15–20 questions, each answered in approximately 1–3 minutes.

Here are ten especially useful ones:
1.Why can SELECT * LIMIT 10 still scan a large amount of data?  
LIMIT restricts returned rows, not necessarily the storage scanned. 
Column projection and partition pruning are more useful.  



2.What is a BigQuery slot?

3.How does BigQuery execute a large JOIN?

4.What is the difference between partitioning and clustering?

5.Why might a MERGE be expensive?

6.How do you process late-arriving events?

7.How do you implement SCD Type 2?

8.How do you optimize a query with high shuffle volume?

9.How do you monitor BigQuery costs?

10.When would you choose BigQuery over Databricks?

4. Corrections worth making in the existing document
   
After reading your actual Markdown, I also noticed several points worth refining before an interview.
- Slots versus Spark executor cores: Your analogy is useful, but a slot is not literally one Spark executor core. Describe it as BigQuery's unit of compute capacity.
- Shuffle and memory failures: The statement that BigQuery's shuffle architecture prevents out-of-memory failures is too strong. BigQuery queries can still encounter resource limits, skew, and shuffle quota problems.
- Exactly-once streaming: Clarify that the Storage Write API's exactly-once guarantees depend on the stream type and use of offsets.
- Primary and foreign keys: BigQuery constraints are not enforced, and incorrect declarations can produce incorrect optimizer assumptions.
- Time travel: Explain configurable time-travel windows and their relationship to recovery and fail-safe retention.
- SQL examples: In your nested orders example, ts is referenced but is not declared in the table definition. Fix that before using it in interview preparation.
5. The best hands-on project to add
Given your experience building telemetry pipelines with Databricks and AWS, I would create a small equivalent implementation on GCP:

Vehicle Telemetry Analytics with BigQuery

Use simulated GPS and vehicle telemetry, with a pipeline that ingests raw events, deduplicates records, builds daily summaries, and exposes dashboard metrics.

Include event-time handling, partitioning, clustering, backfills, data quality tests, and a comparison of query costs before and after optimization.

This would allow you to discuss the same engineering problems across BigQuery, Snowflake, and Databricks, while demonstrating platform-specific knowledge.

 First expand query troubleshooting, CDC/MERGE, incremental processing, and cost optimization. 
 Then implement the telemetry example.   

