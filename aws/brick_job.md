How to run your PySpark code every minute **outside a notebook** and manage it end-to-end.

## Step 1) Package your notebook logic as a Python entrypoint

Refactor your notebook into a tiny callable module plus a `main.py` runner. Put this in a Databricks Repo (recommended) or upload to DBFS.

```
repo-root/
  ingest/
    __init__.py
    job_logic.py      # your existing function(s)
    main.py           # entrypoint that calls your function
```

### File: job_logic.py (sketch)

```python
from pyspark.sql import SparkSession

def run_job():
    spark = SparkSession.builder.getOrCreate()

    # 1) Read from DynamoDB (however you currently do it)
    # ddb = spark.read.format("dynamodb")...  (or your connector)
    # 2) Transform
    # 3) Write to your Databricks table (on S3 / Delta)

    # example:
    # df.write.format("delta").mode("append").saveAsTable("my_catalog.my_schema.my_table")
```

### File main.py

```python
from ingest.job_logic import run_job

if __name__ == "__main__":
    run_job()
```

Push this repo to Git and use **Repos** in Databricks to keep it synced.

## Step 2) Create a Databricks Job (non-interactive)

You have three good compute choices:

* **Serverless compute for Jobs** (best if available): fully managed, quick starts, no cluster babysitting.
* **Job cluster**: ephemeral cluster created per run (simple, but cold-start overhead every minute can be costly).
* **Existing all-purpose cluster**: fastest per-minute cadence (no cold start), but you pay for it to stay running.

For a true **every-minute** cadence, prefer **Serverless** or an **Existing cluster kept warm**. A Job cluster spinning up every minute is usually too slow/expensive.

### Create the Job (UI)

* Workflows → Jobs → Create Job
* Task type: **Python script**
* Source: **Repo** → pick your `main.py`
* Compute:

  * **Use Serverless compute** (if your workspace supports it), or
  * **Use existing cluster** (kept running; set Auto-Terminate to something long), or
  * **New job cluster** (only if you can tolerate startup time)
* Schedule: **Every 1 minute** (Scheduler uses UTC)
* Set **Timeout** (e.g., 50 seconds) and **Max concurrent runs = 1** to avoid overlaps
* Add **Retry** policy (e.g., 3 attempts, 10s backoff)
* Save

### Create the Job (JSON + CLI)

If you automate with the new `databricks` CLI:

### File: `job.json` (example; adjust paths)

```json
{
  "name": "ddb-to-delta-every-minute",
  "max_concurrent_runs": 1,
  "timeout_seconds": 50,
  "tasks": [
    {
      "task_key": "ingest-task",
      "python_wheel_task": null,
      "spark_python_task": {
        "python_file": "repos/you/your-repo/ingest/main.py"
      },
      "job_cluster_key": "job-cluster",
      "timeout_seconds": 50,
      "max_retries": 3,
      "min_retry_interval_millis": 10000,
      "retry_on_timeout": true
    }
  ],
  "job_clusters": [
    {
      "job_cluster_key": "job-cluster",
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 1
      }
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 0/1 * * * ?",
    "timezone_id": "UTC",
    "pause_status": "UNPAUSED"
  }
}
```

### Create/update job :

```
databricks jobs create --json-file job.json
# or
databricks jobs reset --job-id <id> --json-file job.json
```

**Tip:** In the UI, selecting “Every minute” will populate a correct Quartz cron; if you’re unsure about the expression, use the UI first.

## Step 3) Credentials to DynamoDB/S3

Because you’re on **Serverless/Jobs**, the clean path is an **instance profile / IAM role** that grants read to DynamoDB and write to your S3/Delta location. In the job’s compute settings:

* For **Serverless compute**: attach the workspace’s **serverless access**/instance profile (your admin might need to map it).
* For **Existing or Job clusters**: set the **Instance Profile / IAM role**.
  Then your Spark code can use the default provider chain (no hardcoded keys). In Python, `boto3` (if used) will pick up the role automatically.

## Step  4) If you truly need “every minute,” consider streaming

A Structured Streaming job is often better than cron-style runs. You can:

* Wrap your logic as a streaming pipeline (e.g., `Trigger.ProcessingTime("1 minute")`).
* Deploy as a **continuous** job (no schedule; it runs once and keeps going).
* Use **Serverless** or an **existing cluster** to keep it alive.
  This avoids per-run startup, improves latency, and handles backpressure.

Minimal pattern:

```
(
  spark.readStream.format("...dynamodb-source...")
  .load()
  # transforms
  .writeStream
  .format("delta")
  .option("checkpointLocation", "s3://…/chk/ingest-ddb")
  .trigger(processingTime="1 minute")
  .toTable("my_catalog.my_schema.my_table")
)
```

## Step 5) How to stop the non-interactive job

You have several options:

* **Cancel the active run:** Workflows → Runs → select run → **Cancel**
  CLI: `databricks runs cancel --run-id <run-id>`
* **Pause the schedule:** Workflows → Job → **Pause**
  CLI: `databricks jobs pause --job-id <job-id>`
* **Delete the job:** Workflows → Job → **Delete**
  CLI: `databricks jobs delete --job-id <job-id>`
* **Stop compute:**

  * Serverless: stopping the run is enough; there’s no cluster to manage.
  * Existing cluster: **Terminate** it in Compute if you used one for the job.

## Step 6) Quick checklist for your case

* [ ] Move your notebook logic into `job_logic.run_job()`
* [ ] Put code in a Repo (so Jobs → Python script can point to it)
* [ ] Choose **Serverless compute for Jobs** (or an existing warm cluster)
* [ ] Schedule “Every minute” (UTC), timeout < 60s, retries, max concurrent = 1
* [ ] Ensure IAM role/instance profile grants DynamoDB read + S3 write
* [ ] (Optional but recommended) Convert to a single **streaming** job instead of per-minute batch

 
  **Databricks notebook scheduling (via the UI)** only supports hourly, daily, or weekly intervals — not per-minute execution.

# How to achieve **every-minute runs** :  several  patterns  
 

## 🧭 1. Use a Databricks **Job** with a cron schedule

Databricks **Jobs** (not the simple “Schedule” in a notebook) can use **custom cron expressions**.

**Steps:**

1. Open **Workflows → Jobs** in the left sidebar.
2. Click **Create Job**.
3. Under **Task**, select your notebook.
4. In **Schedule**, click **Advanced** and enter this cron expression:

   ```
   * * * * *    → every minute
   ```
5. Save and run.

✅ Runs every minute
✅ Fully managed by Databricks
✅ Viewable in the Job Runs history
⚠️ But: a new cluster may start for each run — use a **“Continuous job” cluster** or **existing job cluster** to minimize overhead.

---

## ⚙️ 2. Use **Databricks REST API** to trigger the job every minute

You can have an external scheduler (like Azure Function, AWS Lambda, or a local cron job) call:

```
POST /api/2.1/jobs/run-now
```

Example Python script:

```python
import time
import requests

DATABRICKS_INSTANCE = "https://<your-instance>.cloud.databricks.com"
JOB_ID = "<your-job-id>"
TOKEN = "<your-personal-access-token>"

while True:
    response = requests.post(
        f"{DATABRICKS_INSTANCE}/api/2.1/jobs/run-now",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"job_id": JOB_ID}
    )
    print(response.json())
    time.sleep(60)  # wait 1 minute
```

✅ Fine control over timing
✅ Can handle retries or conditions
⚠️ Requires an always-on process somewhere

---

## 🔁 3. Loop inside the notebook itself

You can make your notebook run continuously, executing the code every minute inside a loop:

```python
import time

while True:
    print("Running task...")
    # your PySpark or Python logic here
    time.sleep(60)
```

✅ Simplest approach
⚠️ Runs forever — must keep the notebook/cluster alive manually
⚠️ No job-level monitoring or retries

---

## 🪶 4. Use **Databricks Workflows → Continuous jobs (Streaming mode)**

If your code reads from streaming sources or can be adapted to a long-running pattern, you can enable **continuous execution**.
That’s ideal for incremental ingestion or minute-based aggregation.

In Job settings:

* Toggle **“Run continuously”**
* The code runs non-stop instead of restarting every minute.

✅ Ideal for event processing or streaming data
⚠️ Not good for batch-style jobs that must start/finish each time

---

## 🧰 5. Alternative external schedulers

If Databricks isn’t strict about scheduling precision:

* Use **Azure Function (Timer Trigger)** every minute to call your Databricks job.
* Or use **Apache Airflow** DAG with `schedule_interval="@minutely"`.

---

### ✅ Summary

| Method                    | Granularity  | Recommended for       | Notes                 |
| ------------------------- | ------------ | --------------------- | --------------------- |
| Databricks Job (cron)     | Every minute | Standard automation   | Use `* * * * *`       |
| REST API loop             | Every minute | Custom orchestration  | Flexible, external    |
| Infinite loop in notebook | Every minute | Quick tests           | No retries            |
| Continuous job            | Real-time    | Streaming tasks       | Keeps cluster running |
| External scheduler        | Every minute | Integration pipelines | Use Function/Airflow  |

#  Problem statement
```
There is DynamoDB table populated by external process.
Goal is to build almost real-time pipeline which 
reads the new records from DynamoDB, transform it  using PySpark and append transformed records into DataBricks Unity catalog table.
```
I consider following options:

## Option 1:  Direct DynamoDB Table Access (Batch Reads)

Direct polling from DynamoDB table to Databricks using GSI global secondry index on column updated_at
Create Global Secondary Index (GSI) on updated_at column.
Periodically call table.query() 
Store max(updated_at) of already processed records in persistent storage, in order to read
only new recors:   max(updated_at) will be passed as argument to  tab.query() 


## Option 2: DynamoDB Streams (Change Data Capture)
 
AWS Lambda ->  S3 -> Databricks
 
### Comparison and  reference design
for a near-real-time (sub-minute to a few minutes)
DynamoDB → PySpark → Unity Catalog pipeline. 
 
```
- If you want “robust + low-ops + ~1–2 min latency”: **Use DynamoDB Streams → (EventBridge Pipes or Kinesis Firehose) → S3 → Databricks Auto Loader → Delta/Unity**. This is the sweet spot for cost, reliability, and simplicity.
- If volume is small and you need a quick start with minute polling: **Use a GSI on (tenant, updated_at)** and batch pull with a persisted cursor + idempotent MERGE into Delta.
- If you truly need sub-second to tens-of-seconds latency without an S3 landing zone: **Streams → Kinesis Data Streams → Databricks Structured Streaming**, but this adds complexity.
```

 
## Option 1 — Direct DynamoDB table access (batch pulls via GSI)  
Good for: low/medium volume, simple ops, minute-level cadence.

Design  
1) Model your GSI carefully:
   - **Partition key (HASH)**: something selective you can query per batch, e.g. tenant/account/org_id (or a fixed bucket key if global).
   - **Sort key (RANGE)**: updated_at (ISO-8601 or epoch millis).
   - If you have many tenants, you’ll query per tenant; otherwise shard into a small set of buckets (e.g. pk = “bucket#00..99”) so queries are bounded.

2) Pull pattern:  
   - Keep a persistent cursor per (partition key) = **last_processed_updated_at** in a tiny Delta “state” table.
   - Query GSI with `KeyConditionExpression: pk=:tenant AND updated_at BETWEEN :cursor AND :cursor + window`.
   - **Paginate** (1 MB limit/page) and **backoff** on throttling (RCU).
   - Allow **overlap** (e.g., re-read last 1–2 minutes) to tolerate clock skew & eventual consistency; dedupe with MERGE on primary keys.

3) Write pattern (idempotent):
   - Stage incoming micro-batch to a temp Delta table / view, then **MERGE** into your Unity table on (pk, sort_key) or a true unique id.

Pros
- Simple to reason about, no extra AWS infra required.
- Easy to backfill: just move the cursor back.

Cons & gotchas
- You must manage cursor, retries, and dedupe yourself.
- Hot partitions possible if updated_at is monotonically increasing and the GSI partition key is too coarse (watch RCU).
- Deletes and TTL expirations won’t be seen unless you model soft-deletes or do periodic reconciliations.

Code sketch (Databricks notebook, using your provided credential handle)
- Assumes your admin exposed AWS creds via `dbutils.credentials.getServiceCredentialsProvider("chargeminder-dynamodb-creds")`.
- Replace `TENANT_IDS` with your partition keys or iterate all tenants you own.
 
```python
from pyspark.sql import functions as F

# 1) Read state (last processed updated_at per tenant)
 
state_tbl = "hcai_databricks_dev.chargeminder2.ddb_state"   # tenant, last_ts
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {state_tbl} (
  tenant STRING,
  last_ts BIGINT
) USING DELTA
""")

def get_boto3():
    import boto3
    sess = boto3.Session(
        botocore_session=dbutils.credentials.getServiceCredentialsProvider("chargeminder-dynamodb-creds"),
        region_name="us-east-1"
    )
    return sess.resource("dynamodb"), sess.client("dynamodb")

table_name = "your_ddb_table"
gsi_name   = "tenant_updated_at_gsi"   # HASH = tenant, RANGE = updated_at

TENANT_IDS = ["tenantA","tenantB"]     # or discover/maintain this list elsewhere
MAX_LAG_MS = 120000                    # re-read last 2 minutes for overlap

ddb_resource, ddb_client = get_boto3()
tbl = ddb_resource.Table(table_name)

import time, decimal
now_ms = int(time.time() * 1000)

rows = []
for tenant in TENANT_IDS:
    last = spark.table(state_tbl).where(F.col("tenant")==tenant).limit(1).collect()
    last_ts = last[0]["last_ts"] if last else (now_ms - 3600_000)  # default: 1 hour back for first run
    start_ts = max(0, last_ts - MAX_LAG_MS)
    kwargs = {
        "IndexName": gsi_name,
        "KeyConditionExpression": "#t = :tenant AND #u BETWEEN :from AND :to",
        "ExpressionAttributeNames": {"#t":"tenant", "#u":"updated_at"},
        "ExpressionAttributeValues": {":tenant": tenant, ":from": start_ts, ":to": now_ms},
        "Limit": 1000
    }
    while True:
        resp = tbl.query(**kwargs)
        for item in resp.get("Items", []):
            rows.append(item)
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

# Convert to Spark (handle Decimal)
def to_native(o):
    import decimal
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, dict):
        return {k: to_native(v) for k,v in o.items()}
    if isinstance(o, list):
        return [to_native(v) for v in o]
    return o

clean = [to_native(r) for r in rows]
df = spark.createDataFrame(clean) if clean else spark.createDataFrame([], "tenant STRING")  # empty safe

# 2) Transform with PySpark
transformed = (
    df
    # .withColumn(...)  # your business transforms
)

# 3) Upsert into UC Delta table
target_tbl = "hcai_databricks_dev.chargeminder2.fact_events"

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {target_tbl} (
  tenant STRING,
  id STRING,
  updated_at BIGINT,
  -- other columns...
  _ingest_ts TIMESTAMP
) USING DELTA TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

transformed = transformed.withColumn("_ingest_ts", F.current_timestamp())

transformed.createOrReplaceTempView("stage_incoming")

spark.sql(f"""
MERGE INTO {target_tbl} t
USING (SELECT * FROM stage_incoming) s
ON t.tenant = s.tenant AND t.id = s.id
WHEN MATCHED AND s.updated_at >= t.updated_at THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

# 4) Advance state cautiously (set to the max obs updated_at in this batch)

if clean:
    import numpy as np
    by_tenant = (
        spark.table("stage_incoming")
        .groupBy("tenant").agg(F.max("updated_at").alias("max_ts"))
        .collect()
    )
    for r in by_tenant:
        spark.sql(f"""
        MERGE INTO {state_tbl} dst
        USING (SELECT '{r['tenant']}' AS tenant, {int(r['max_ts'])} AS last_ts) s
        ON dst.tenant = s.tenant
        WHEN MATCHED THEN UPDATE SET dst.last_ts = GREATEST(dst.last_ts, s.last_ts)
        WHEN NOT MATCHED THEN INSERT *
        """)
```
Notes
- If you have deletes, propagate a tombstone flag and handle it in MERGE (DELETE WHEN MATCHED AND s.is_deleted = true).
- Batch schedule: Databricks Job every 1–5 minutes is reasonable. Avoid per-minute if you expect large scans—tune to your RCU & batch size.


## Option 2 — DynamoDB Streams (CDC) → S3 → Databricks Auto Loader
Good for: “hands-off” CDC with ordered updates per partition key (+ low ops).

Design
1) Enable **DynamoDB Streams** on the table with **New and old images** (or at least New image).
2) Wire up one of:
   A) **EventBridge Pipes**: Source= DynamoDB Streams → Target= Kinesis Firehose (or S3) with optional input transform (Lambda or Enrichment).  
   B) **Lambda consumer** for Streams → batch to S3 (Parquet/JSON) in small files (e.g., 5–50 MB).
   C) Streams → **Kinesis Data Streams** (via adapter) → **Kinesis Data Firehose** → S3.

3) Land to **S3** with sensible partitioning: `s3://bucket/ddb/table_name/dt=YYYY-MM-dd/HH=HH/` and gzip/snappy parquet if you can.
4) **Databricks Auto Loader** reads the S3 path continuously and appends to a Delta table in Unity Catalog.
5) Do your PySpark transforms inline (Structured Streaming) and **MERGE for upserts** (using foreachBatch with MERGE).

Pros
- At-least-once CDC with built-in ordering per partition key from Streams.
- No cursor management in your code; retries handled by AWS service (Lambda/Firehose).
- Auto Loader handles schema inference/evolution + backpressure + exactly-once sink semantics (with Delta).

Cons & gotchas
- Slightly more AWS wiring (Streams + Pipes/Firehose or Lambda).
- You still need to MERGE to handle upserts (new images) & deletes (remove from Delta).

Auto Loader sketch (S3 JSON payloads with “Image”)

```python
from pyspark.sql import functions as F

source_path = "s3://your-bucket/ddb/your-table/"
checkpoint = "s3://your-bucket/_checkpoints/your-table-stream"
schema_loc = "s3://your-bucket/_schemas/your-table-stream"

raw = (
  spark.readStream
       .format("cloudFiles")
       .option("cloudFiles.format", "json")
       .option("cloudFiles.inferColumnTypes", "true")
       .option("cloudFiles.schemaLocation", schema_loc)
       .load(source_path)
)

# Unwrap DDB stream record if needed (structure depends on your Lambda/Firehose transform)
# Example assumes payload like: {"eventName":"INSERT","dynamodb":{"NewImage": {...}, "Keys": {...}, "ApproximateCreationDateTime": 169...}}
df = raw  # apply select/transform to flatten NewImage → columns

# Your business transform(s)
tx = (
  df
  # .withColumn(...)
  .withColumn("_ingest_ts", F.current_timestamp())
)

target_tbl = "hcai_databricks_dev.chargeminder2.fact_events"

def upsert_batch(micro_batch_df, batch_id: int):
    micro_batch_df.createOrReplaceTempView("incoming")
    spark.sql(f"""
    MERGE INTO {target_tbl} t
    USING (SELECT * FROM incoming) s
    ON t.tenant = s.tenant AND t.id = s.id
    WHEN MATCHED AND s.updated_at >= t.updated_at THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
    """)
    # Optional: handle DELETE records: issue DELETE WHERE pk IN (...) for those eventName='REMOVE'

(
  tx.writeStream
    .option("checkpointLocation", checkpoint)
    .trigger(processingTime="30 seconds")   # adjust: “availableNow” for catch-ups or “continuous” for low latency
    .foreachBatch(upsert_batch)
    .start()
)
```
### Notes

```
- For deletions (`eventName='REMOVE'`), either land a tombstone record (is_deleted=true) in S3 and handle in MERGE, or run a post-upsert DELETE step for those keys inside `foreachBatch`.
- Use **DLT** (Delta Live Tables) if you want managed expectations/quality & lineage.

──────────────────────────────────────────────────────────────────────────────
Option 3 — DMS (full + CDC) → S3 → Auto Loader / DLT
- DMS supports DynamoDB → S3 with CDC. Good for full backfills + ongoing changes with minimal code.
- Trade-offs: DMS operational overhead and cost; still end at S3 → Delta with same downstream transform.

──────────────────────────────────────────────────────────────────────────────
Option 4 — Streams → Kinesis Data Streams → Databricks streaming (no S3)
- Lowest latency (seconds), but you’ll need the Spark Kinesis connector + KCL adapter for DynamoDB Streams or a Lambda bridge to Kinesis.
- More moving parts; often not necessary unless strict real-time is required.

──────────────────────────────────────────────────────────────────────────────
Security & credentials (Databricks on AWS)
- For **Serverless** compute, your workspace typically has a **Serverless Access Role**. To call DynamoDB directly (Option 1) from a notebook:
  - If your admin gave you **“chargeminder-dynamodb-creds”**, use `dbutils.credentials.getServiceCredentialsProvider("chargeminder-dynamodb-creds")` with `boto3.Session(botocore_session=..., region_name=...)` exactly as in the sketch above.
  - Make sure that role grants: `dynamodb:DescribeTable`, `Query` (and/or `Scan` if used), and if Streams path: `dynamodb:DescribeStream`, `GetShardIterator`, `GetRecords`.
- For **S3 landing** (Options 2–3), prefer **Kinesis Firehose** or **Lambda** to write into an S3 prefix that your Unity Catalog external location / storage credential can read. Auto Loader needs `s3:GetObject`, `ListBucket` on that prefix.

──────────────────────────────────────────────────────────────────────────────
Data modeling & correctness checklist
- **Primary key**: have a deterministic id (pk, sk) or a composite key you can use in MERGE.
- **Event time**: keep source `updated_at` and a `_ingest_ts`. Use watermarks if you do any time-based aggregates later.
- **Idempotency**: ALL sinks must be idempotent. Always MERGE on keys with `updated_at` guard.
- **Ordering**: Streams preserve order per partition key; batch pulls do not—MERGE with a “latest-wins” rule.
- **Deletes**: Either soft-delete in DynamoDB and propagate a tombstone, or consume `REMOVE` from Streams and translate to Delta DELETE.
- **Schema evolution**: With Auto Loader, use `cloudFiles.schemaLocation` and set `spark.databricks.cloudFiles.schemaEvolutionMode` = “addNewColumns” if needed.
- **Backfills**: For Option 2, drop historical exports in S3 under the same prefix and run Auto Loader with `availableNow`. For Option 1, rewind the cursor and reprocess (MERGE makes it safe).

──────────────────────────────────────────────────────────────────────────────
What I recommend for you
Given your stack (Unity Catalog, PySpark, minute-ish SLAs, desire to keep ops light):
1) **Enable DynamoDB Streams** with New Images.  
2) **EventBridge Pipes → Kinesis Firehose → S3 (Parquet, snappy, 64–256 MB)**, partitioned by date/hour.  
3) **Databricks Auto Loader (Structured Streaming)** to transform and **MERGE** into `hcai_databricks_dev.chargeminder2.<your_table>`.  
4) Use a **DLT pipeline** if you want managed expectations and cleaner ops.  
5) Keep a tiny “dead-letter” S3 prefix for records that fail transformation and alert on it.

If you need to start today and test quickly with small volumes, begin with **Option 1 (GSI pull)** using the sample code, then graduate to Streams → S3 → Auto Loader once you’re happy with the transform and table contract.

If you want, tell me your expected TPS, item size, tenants/partitioning model, and latency goal, and I’ll size the RCU/Throughput, Firehose buffer hints, and Auto Loader trigger/checkpoint settings precisely.
```


## 2️⃣ How the pipeline avoids reprocessing already processed JSONL files

This is handled automatically by **Auto Loader** using its **checkpoint** mechanism and internal **file notification logs**.

### Key configs in your code:

```python
.option("cloudFiles.format", "json")
.option("cloudFiles.schemaLocation", SCHEMA_LOC)
.option("checkpointLocation", CHECKPOINT)
```

Here’s what happens behind the scenes:

| Component                               | Path                                              | Purpose                                                                                                                       |
| --------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **`schemaLocation`** (`SCHEMA_LOC`)     | `s3://chargeminder-2/_schemas/fact_telemetry`     | Auto Loader stores its **inferred schema** and evolution metadata. It’s used to track JSON field types and changes over time. |
| **`checkpointLocation`** (`CHECKPOINT`) | `s3://chargeminder-2/_checkpoints/fact_telemetry` | Delta Streaming engine stores **progress state**, offsets, and a list of files already processed. This ensures idempotency.   |

### How Auto Loader tracks files:

* On first run, it lists or subscribes to S3 events.
* For each file found, it records a unique **file ID and modification timestamp** in the checkpoint metadata.
* On subsequent runs, Auto Loader queries S3 and **skips any file already recorded** in the checkpoint.
* If a file is modified or re-uploaded with the same name, Auto Loader still ignores it because its internal file ID (ETag) hasn’t changed — unless you explicitly delete the checkpoint.

So:

> ✅ Even if your Lambda keeps writing new `batch_YYYY-MM-DD-HH-MM-SS_N.jsonl` files into S3,
> only new files will be picked up by Databricks.

If you ever **delete the checkpoint folder**, the pipeline will reprocess **everything** in that S3 path.

---

## 3️⃣ Purpose of `"schema_path": "s3://chargeminder-2/_schemas/fact_telemetry"`

This directory has **nothing to do with incremental tracking**.
It is purely for **schema inference + evolution tracking** for Auto Loader.

### Specifically:

* On the first read, Auto Loader inspects your JSONL files and infers schema.
* It saves the schema as a **Delta JSON file** in the `_schemas/fact_telemetry` directory.
* Next time you restart the stream, it reuses that schema — so you don’t have to infer it again.
* If new fields appear later (say, your Lambda starts adding `battery_level`), Auto Loader detects them and **updates** the schema JSON in `_schemas/…`.

> This prevents repeated full scans of historical data and avoids schema drift errors between batches.

---

## 4️⃣ TL;DR summary

| Topic                                          | What It Does                                                      |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `spark.databricks.delta.optimizeWrite.enabled` | Optional optimization toggle; safe to remove.                     |
| `checkpointLocation`                           | Tracks already processed files and offsets → prevents duplicates. |
| `schemaLocation`                               | Stores JSON schema evolution → prevents re-inference.             |
| Reprocessing old files                         | Prevented by checkpoint; files are logged as “seen”.              |
| Deleting checkpoint                            | Reprocesses **all** files in S3 prefix.                           |

---

Short answer: **yes**, that will work—just do it cleanly and in the right order.

#  **Reprocess all existing .jsonl files**:

1. **Stop any running stream**

* Make sure no active query is using that checkpoint.
* In notebooks: `q.stop()` if you kept the handle, or use the UI to stop the stream.

2. **Clear the target table**

```sql
USE CATALOG hcai_databricks_dev;
USE SCHEMA chargeminder2;
TRUNCATE TABLE fact_telemetry;
```

(If you also want to remove history to keep the Delta log tiny: `DELETE FROM fact_telemetry; VACUUM fact_telemetry RETAIN 0 HOURS;` — only if you know what you’re doing.)

3. **Reset the checkpoint (recommended: delete the whole directory)**

```python
dbutils.fs.rm("s3://chargeminder-2/_checkpoints/fact_telemetry", recurse=True)
```

* Deleting only `commits/`, `offsets/`, `sources/` is usually fine, but wiping the **entire** checkpoint folder avoids stray state files.
* Alternatively, point your job to a **new checkpoint path** (e.g., add a datestamp suffix). This is the least error-prone.

4. **Leave `schema_path` alone**

* You can keep `s3://chargeminder-2/_schemas/fact_telemetry` as-is. It’s for schema evolution metadata and doesn’t control reprocessing.
* If you provided an explicit schema in code, that folder may stay empty—totally fine.

5. **Run your Python stream again**

* With an **empty/nonexistent checkpoint**, Auto Loader treats the run as first-time and will pick up **all existing files** under your `s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry` prefix.
* Using `availableNow` trigger is perfect for a one-shot backfill:

```python
writer = writer.trigger(availableNow=True)
q = writer.start()
q.awaitTermination()
```

Notes / gotchas:

* Make sure your source files are still present in S3 (not expired/overwritten).
* If your Lambda is still writing new files while you backfill, you’ll ingest **both** old and new—usually fine, but just be aware.
* You do **not** need to touch `schema_path` to force reprocessing. That path doesn’t control file progress.
* If you want to reprocess **only a subset**, temporarily change `SOURCE_PATH` to a narrower S3 prefix, run `availableNow`, then switch back.

Optional quick sanity checks before/after:

```python
# How many source files do we see?
print(spark.read.format("json").load(SOURCE_PATH).count())

# Checkpoint exists?
display(dbutils.fs.ls("s3://chargeminder-2/_checkpoints/"))
```

If you want, I can give you a tiny cell that flips your job to a **new checkpoint path** automatically (e.g., `_checkpoints/fact_telemetry_reprocess_2025-11-04`) so you don’t have to delete anything.



# Reprocessing Archived Files in Your Databricks Streaming Job

Your code's archiving logic (`archive_processed_files()`) moves successfully processed files from the source S3 prefix (e.g., `s3://chargeminder-2/raw/dynamodb/chargeminder-mlubinsky-telemetry/`) to the archive prefix (e.g., `s3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/`) using `dbutils.fs.mv()`. This is a common pattern for data lakes to prevent re-ingestion, but it makes reprocessing intentional (e.g., for errors or schema evolution).

Reprocessing is straightforward: **Manually move files back to the source path**, then **restart the stream** to let Auto Loader detect and process them again. Auto Loader's checkpointing ensures it tracks what's been ingested, but you can override with a new checkpoint or schema tweaks. Below, I'll cover scenarios (errors vs. schema changes) and step-by-step instructions.

#### Key Concepts
- **Checkpoint Safety**: Your stream uses `checkpointLocation` (e.g., `s3://chargeminder-2/_checkpoints/mlubinsky-telemetry`). It logs processed files/metadata—moving files back won't auto-reprocess unless you clear/rename the checkpoint.
- **Schema Evolution**: Auto Loader supports adding columns (`cloudFiles.schemaEvolutionMode="addNewColumn"`) without full reprocessing.
- **No Data Loss**: Archived files remain intact; MERGE in `upsert_batch` handles upserts idempotently (via `event_id` PK).

| Scenario | Trigger | Reprocessing Impact | Best Tool |
|----------|---------|---------------------|-----------|
| **Job Error** (e.g., transform fail) | Partial batch fails; some files archived, others not. | Reprocess only failed files; no schema change. | S3 Console or AWS CLI. |
| **Schema Change** (e.g., add column) | Update `raw_schema` or DDL; run stream with evolution. | Full reprocess if needed; append-only for new cols. | Databricks SQL + Auto Loader. |

#### Step-by-Step: Reprocessing Archived Files

##### 1. **Stop the Running Job/Stream**
   - In Databricks UI: Go to **Workflows** → Your Job → **Runs** → Stop the active run.
   - Or via API: `POST /api/2.0/jobs/runs/cancel` with run ID.
   - This prevents conflicts during file moves.

##### 2. **Identify Files to Reprocess**
   - **For Errors**: Check Job logs/metrics (`METRICS_TABLE`) for batch IDs/files that failed (e.g., `status="FAILED"`, `error_message`).
     ```sql
     SELECT * FROM hcai_databricks_dev.chargeminder2.telemetry_metrics 
     WHERE status = 'FAILED' ORDER BY run_timestamp DESC;
     ```
     - From logs, note archived file paths (e.g., via `source_file` in quarantined data).
   - **For Schema Changes**: Query the archive for all files (or date range).
     ```sql
     -- List archived files (use Databricks SQL or AWS CLI)
     LIST 's3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/';
     ```
   - **Tip**: If high volume, use AWS CLI: `aws s3 ls s3://chargeminder-2/archived/... --recursive | grep jsonl`.

##### 3. **Move Files Back to Source Path**
   - **Manual (Small Scale)**: Use Databricks Notebook (attach to your cluster):
     ```python
     # In a notebook cell
     from delta.utils import DeltaFiles

     # Example: Move specific files back
     source_prefix = "s3://chargeminder-2/raw/dynamodb/chargeminder-mlubinsky-telemetry/"
     archive_prefix = "s3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/"
     
     # List archived files (adapt for your needs)
     archived_files = dbutils.fs.ls(archive_prefix)  # Returns list of FileInfo
     for file_info in archived_files:
         if file_info.name.endswith('.jsonl'):  # Filter JSONL
             archive_path = file_info.path
             source_path = archive_path.replace(archive_prefix, source_prefix)
             dbutils.fs.mv(archive_path, source_path, recurse=True)
             print(f"Moved back: {source_path}")
     ```
     - Run this in a one-off notebook; test with `--dryrun` if available.

   - **Bulk (AWS CLI/S3 Console)**:
     - CLI: `aws s3 mv s3://chargeminder-2/archived/.../file.jsonl s3://chargeminder-2/raw/.../file.jsonl --recursive`
     - Console: Select files in S3 → Actions → Copy/Move.
     - **Caution**: Add a timestamp suffix (e.g., `_reprocess_v2.jsonl`) to avoid name conflicts.




### ✅ Recommendation

Keep both schema and checkpoint paths persistent and unique per stream:

```python
"schema_path": "s3://chargeminder-2/_schemas/fact_telemetry",
"checkpoint_path": "s3://chargeminder-2/_checkpoints/fact_telemetry"
```

That ensures your stream is:

* **Incremental** (processes only new batches),
* **Idempotent** (no duplicates),
* **Schema-aware** (adapts to new columns).

 The content type `application/x-ndjson` is actually correct for NDJSON format - the mismatch with `.jsonl` extension is just a naming convention thing (both `.jsonl` and `.ndjson` are valid). However, let's make this Lambda **much more robust** for production use:Perfect! Here's everything you need to make your Lambda production-ready:

## 📥 Download Links

### Production-Ready Lambda Files
- **[lambda_robust.py](computer:///mnt/user-data/outputs/lambda_robust.py)** - Production Lambda with all improvements
- **[deploy_robust.sh](computer:///mnt/user-data/outputs/deploy_robust.sh)** - Automated deployment script
- **[LAMBDA_IMPROVEMENTS.md](computer:///mnt/user-data/outputs/LAMBDA_IMPROVEMENTS.md)** - Detailed documentation
- **[LAMBDA_COMPARISON.md](computer:///mnt/user-data/outputs/LAMBDA_COMPARISON.md)** - Side-by-side comparison

---

## ✅ Your Questions Answered

### 1. Content Type vs File Extension

**Your Question:** Why `.jsonl` extension with `application/x-ndjson` content type?

**Answer:** Both are correct! 
- `.jsonl` and `.ndjson` are both valid extensions for newline-delimited JSON
- `application/x-ndjson` is the standard MIME type
- **For consistency**, the robust version uses `.ndjson` extension to match the content type

### 2. How to Make Lambda More Robust

Your basic Lambda has **5 critical issues**:

| Issue | Impact | Solution |
|-------|--------|----------|
| ❌ **No error handling** | One bad record crashes everything | ✅ Try-catch per record |
| ❌ **No retry logic** | Transient S3 failures are permanent | ✅ 3 retries with backoff |
| ❌ **No validation** | Bad data goes to S3 | ✅ Validate required fields |
| ❌ **No monitoring** | Can't track failures | ✅ CloudWatch metrics |
| ❌ **No DLQ** | Failed records are lost forever | ✅ Dead Letter Queue |

---

## 🎯 What Gets Added

### **10 Production Features:**

1. ✅ **Per-record error handling** - Bad records don't crash the batch
2. ✅ **Retry logic** - 3 attempts with exponential backoff (1s, 2s, 4s)
3. ✅ **Data validation** - Checks required fields before processing
4. ✅ **Dead Letter Queue** - Failed records go to SQS for recovery
5. ✅ **Partial batch failures** - Only retry failed records (AWS best practice)
6. ✅ **CloudWatch metrics** - 5 custom metrics for monitoring
7. ✅ **Processing metadata** - Track when/how records were processed
8. ✅ **S3 metadata** - Rich object metadata for debugging
9. ✅ **Type hints** - Better code quality and IDE support
10. ✅ **Structured logging** - Clear, searchable logs

---

## 📊 Comparison Table

| Feature | Your Lambda | Robust Lambda |
|---------|-------------|---------------|
| Lines of code | ~70 | ~320 |
| Error handling | ❌ None | ✅ Comprehensive |
| Retry logic | ❌ No | ✅ 3 attempts |
| Validation | ❌ No | ✅ Yes |
| Monitoring | ❌ No | ✅ 5 metrics |
| DLQ support | ❌ No | ✅ Yes |
| Partial failures | ❌ No | ✅ Yes |
| Cost/month (1M records) | $1.00 | $1.50 |
| Production-ready | ❌ No | ✅ Yes |

**Cost increase: $0.50/month for huge reliability gains!**

---

## 🚀 Quick Deployment

```bash
# 1. Download files
# Download lambda_robust.py and deploy_robust.sh

# 2. Update configuration in deploy_robust.sh
nano deploy_robust.sh
# Set: ROLE_ARN, S3_BUCKET, DYNAMODB_TABLE

# 3. Deploy everything (10 minutes)
chmod +x deploy_robust.sh
./deploy_robust.sh
```

**The script automatically sets up:**
- Lambda function with new code
- Dead Letter Queue (SQS)
- IAM permissions (CloudWatch, SQS)
- DynamoDB Stream trigger with partial batch failure support
- CloudWatch alarms (errors, failed records, S3 failures)
- SNS topic for alerts

---

## 🔍 Key Improvements Explained

### **1. Error Handling**
```python
# Before: Crashes on any error
obj = {k: deser.deserialize(v) for k, v in new_image.items()}

# After: Catches errors per record
try:
    obj = {k: deser.deserialize(v) for k, v in new_image.items()}
    if not validate_record(obj):
        raise ProcessingError("Validation failed")
except Exception as e:
    send_to_dlq(record, str(e))
    continue  # Process remaining records
```

### **2. Partial Batch Failures**
```python
# Tell DynamoDB Streams which records to retry
return {
    "batchItemFailures": [
        {"itemIdentifier": "event-id-123"},  # Only retry this one
        {"itemIdentifier": "event-id-456"}   # And this one
    ]
}
```

**Benefit:** Prevents reprocessing successful records!

### **3. Retry Logic**
```python
def write_to_s3(lines, key, attempt=1):
    try:
        s3_client.put_object(...)
    except Exception as e:
        if attempt < 3:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
            return write_to_s3(lines, key, attempt + 1)
```

### **4. CloudWatch Metrics**
```python
publish_metric("RecordsProcessed", 100)
publish_metric("RecordsFailed", 2)
publish_metric("ProcessingDuration", 1.5, "Seconds")
```

---

## 📈 Monitoring

### CloudWatch Metrics Available
- `RecordsProcessed` - Successfully processed
- `RecordsFailed` - Failed validation/processing
- `RecordsSkipped` - Skipped (wrong event type)
- `ProcessingDuration` - Lambda execution time
- `S3WriteSuccess` - Successful S3 writes
- `S3WriteFailure` - Failed S3 writes

### CloudWatch Insights Queries

**Failed Records:**
```sql
fields @timestamp, @message
| filter @message like /Failed to process record/
| sort @timestamp desc
```

**Processing Summary:**
```sql
fields @timestamp, @message
| filter @message like /Processing Summary/
| parse @message /Processed: (?<processed>\d+)/
| stats sum(processed) by bin(5m)
```

---

## 🎓 Migration Guide

### Option 1: Direct Update (Recommended)
```bash
# Just run the deployment script
./deploy_robust.sh
# Your function is immediately updated
```

### Option 2: Test First
```bash
# Deploy as new function
FUNCTION_NAME="chargeminder-stream-processor-v2" ./deploy_robust.sh

# Test with sample data
# Switch DynamoDB Stream trigger to new function
# Delete old function
```

---

## ✅ After Deployment

### 1. Subscribe to Alerts
```bash
aws sns subscribe \
    --topic-arn arn:aws:sns:region:account:chargeminder-lambda-alerts \
    --protocol email \
    --notification-endpoint your-email@example.com
```

### 2. Test the Function
```python
# Insert test record into DynamoDB
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('chargeminder-car-telemetry')
table.put_item(Item={'event_id': 'test-123', 'recorded_at': '2025-10-31 12:00:00'})
```

### 3. Monitor
```bash
# Check logs
aws logs tail /aws/lambda/chargeminder-stream-processor --follow

# Check metrics
aws cloudwatch get-metric-statistics \
    --namespace ChargeMinder/Lambda \
    --metric-name RecordsProcessed \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum

# Check DLQ (if any failures)
aws sqs receive-message --queue-url YOUR_DLQ_URL
```


## 💡 Bottom Line

**Your Lambda works**, but it's not production-ready. The robust version adds:

1. **Reliability** - Handles errors gracefully
2. **Observability** - Know what's happening
3. **Recoverability** - Failed records go to DLQ
4. **Best Practices** - Follows AWS recommendations

**Cost:** Only +$0.50/month for 1M records

**Recommendation:** Use the robust version for production! 🚀









 ## 4. **Handle Schema Changes (If Applicable)**
   - **Add Columns**: Update `raw_schema` (e.g., add `StructField("new_field", StringType(), True)`) and DDL (`create_or_update_table()`).
     - Re-run the job: Auto Loader's `"addNewColumn"` mode appends without reprocessing old data.
   - **Breaking Changes** (e.g., type changes): 
     - Set `cloudFiles.schemaEvolutionMode="rescue"` to quarantine bad rows.
     - Or full reprocess: Clear checkpoint (delete contents of `checkpoint_path`) before restart—**warning: loses ingestion history**.
   - **Test**: Run a dry-run job with `maxFilesPerTrigger=1` on a subset.

## 5. **Restart the Stream and Monitor**
   - **Restart Job**: In UI, **Run Now** or resume schedule (now "Continuously" if using notifications).
   - **Verify Reprocessing**:
     - Watch logs for "Processing Batch X" with your files.
     - Query target table: `SELECT COUNT(*) FROM {FULL_TABLE} WHERE pipeline_ingest_ts > '2025-11-09';` (post-reprocess).
     - Check metrics: New rows in `METRICS_TABLE` with updated counts.
   - **Checkpoint Reset (If Needed)**: To force re-detection:
     ```python
     # In notebook: Clear checkpoint (one-time)
     dbutils.fs.rm(CONFIG["checkpoint_path"], recurse=True)
     ```
     - Then restart—Auto Loader rescans from scratch.

## 6. **Prevention and Best Practices**
   - **Error Handling**: In `upsert_batch`, add try-catch around archiving—only move on full success.
     ```python
     # In upsert_batch, after MERGE
     try:
         archive_processed_files(micro_df)
     except Exception as ae:
         print(f"⚠️ Archiving failed: {ae} — Files remain in source for retry")
     ```
   - **Dry Runs**: Add a config flag (`"dry_run": True`) to skip archiving/MERGE for testing schema changes.
   - **Versioned Archives**: Append timestamps to archive paths (e.g., `/archived/YYYY/MM/DD/`) for easier rollback.
   - **Alternatives to Archiving**:
     - Use Auto Loader's **file filtering** (e.g., `cloudFiles.includeExistingFiles=true` for re-runs) instead of moving.
     - Or soft-archive: Add a `processed` tag via S3 metadata, filter in Auto Loader.
   - **Monitoring**: Set Job alerts for failures; use Delta Lake's time travel (`AS OF TIMESTAMP`) to rollback bad inserts.

This process typically takes 5-15 minutes for small batches. If reprocessing large volumes (>1TB), consider partitioning by date in your source S3 structure. Let me know your error details or schema mods for tailored tweaks!


## Explanation of `rescuedDataColumn` Option

The `.option("rescuedDataColumn", "_rescued_data")` line in your Auto Loader (`cloudFiles`) configuration tells Databricks to **automatically rescue (save) malformed or unparsable records** during ingestion, rather than failing the entire batch. Here's a breakdown:

## What It Does
- **Purpose**: When Auto Loader reads JSON files (or other formats) against your explicit `raw_schema`, some rows might not conform:
  - Missing required fields.
  - Type mismatches (e.g., expected `string` but got `int`).
  - Malformed JSON (e.g., syntax errors from DynamoDB Lambda exports).
  - Without this, the job would **fail** (throwing a schema validation error), halting processing.
- **How It Works**:
  - Auto Loader parses each row against `raw_schema`.
  - If a row fails, it's **not dropped**—instead, the **raw, unparsed content** (as a JSON string) is inserted into a new column named `_rescued_data`.
  - Valid rows proceed normally.
  - The `_rescued_data` column is added to your DataFrame schema (nullable `string` type).
- **Example**:
  - Input JSON row: `{"event_id": "abc", "recorded_at": 123}` (type mismatch: `recorded_at` should be `string`).
  - Output: Row has all normal columns as `null` (or defaults), but `_rescued_data` = `'{"event_id": "abc", "recorded_at": 123}'`.
- **Benefits**:
  - **Resilience**: Job continues; no full failure.
  - **Debugging**: Query `_rescued_data` to inspect/fix issues (e.g., `df.filter(F.col("_rescued_data").isNotNull()).show()`).
  - **Downstream Handling**: In `upsert_batch`, filter out rescued rows or route to quarantine.

#### When to Use/Configure
- **Default**: No rescued column (fails on errors).
- **Your Code**: Naming it `"_rescued_data"` is conventional—keep it if you plan to query it.
- **Trade-Offs**:
  | Pro | Con |
  |-----|-----|
  | Prevents job crashes | Adds a column (slight schema bloat) |
  | Easy error triage | Rescued rows may need manual cleanup |

If unused, you can drop it later: `.drop("_rescued_data")`.

### Explanation of `schemaEvolutionMode` Option (Missing in Snippet)

The `option("schemaEvolutionMode", "rescue")` is **not present** in the code snippet you shared (it uses `"addNewColumn"` in the full code from earlier responses). This option controls how Auto Loader **adapts to schema changes** over time (e.g., new fields in DynamoDB exports). Adding it is optional but recommended for evolving data like telemetry signals.

#### What It Does
- **Purpose**: Auto Loader infers/evolves the schema at `CONFIG["schema_path"]` based on new files. Without this, it fails on mismatches. With it, it handles changes gracefully.
- **Modes** (All are "permissive"—no failures):
  | Mode | Description | Best For | Impact on Data |
  |------|-------------|----------|----------------|
  | **"addNewColumn"** (Your Current) | Adds new fields as nullable columns to the schema. Existing rows get `null` for new fields. | Non-breaking adds (e.g., new signal like "battery_temp"). | Minimal data loss; appends columns. |
  | **"rescue"** (You Asked About) | Like "addNewColumn", but **any row with schema mismatches** (new/missing fields) is routed to `rescuedDataColumn`. Valid rows evolve the schema. | Strict validation + error isolation (e.g., old files with outdated JSON). | Mismatches become raw strings in rescued column; schema still evolves. |
  | **"failOnNewColumn"** (Strict) | Fails if new fields appear. | Frozen schemas (rare). | Stops processing. |
  | **"none"** (Default) | No evolution; strict match to initial schema. | Stable data only. | Fails on changes. |

- **"rescue" Specifics**:
  - Combines evolution with rescue: New columns are added, but problematic rows (e.g., missing new required field) go to `_rescued_data` as raw JSON.
  - Example: New file has `{"event_id": "abc", "new_signal": "xyz"}`. Schema adds `new_signal`; old rows get `null`; mismatched rows (e.g., bad types) → rescued.
  - **Why "rescue" over "addNewColumn"?** Better for auditing—isolates "dirty" rows without polluting the main table.

#### Why It's Missing & How to Add It
- **In Snippet**: Omitted for brevity; full code had `"addNewColumn"`.
- **Recommendation**: Use `"rescue"` if you have `rescuedDataColumn` enabled (synergistic). Add it right after `.option("cloudFiles.validateOptions", "true")`:
  ```python
  .option("cloudFiles.schemaEvolutionMode", "rescue")  # Handles changes + rescues mismatches
  ```
- **Trade-Offs**:
  | Pro | Con |
  |-----|-----|
  | Evolves schema dynamically | More rescued rows if data varies wildly |
  | Integrates with rescuedDataColumn | Slight perf hit on validation |

#### Quick Test
In a notebook:
```python
# Simulate: Add a mismatched file, run stream, query rescued rows
df.filter(F.col("_rescued_data").isNotNull()).count()  # Should show issues
```


### Does a Dedicated Databricks Cluster Need to Be Always Running for a Job Task Scheduled Every Minute?

**Short Answer**: Not strictly "always," but practically **yes**—you'll want it **running and ready** at all times to avoid delays, queuing, or failures. For ultra-frequent schedules like every minute, Databricks recommends using an **All-Purpose Cluster** (often called "dedicated" in this context) with **auto-termination** enabled after idle periods. This ensures near-instant job starts without the spin-up overhead of Job Clusters.

#### Why This Setup?
- **Job Clusters** (ephemeral, on-demand): These spin up when a job starts and shut down after. Great for infrequent runs, but:
  - **Spin-up time**: 1-5 minutes (depending on size/policies), so a 1-minute schedule would cause massive overlap/queuing—jobs wait for the cluster to provision.
  - Not ideal for <5-10 minute intervals; Databricks docs advise against it for high-frequency workloads.
- **All-Purpose Clusters** (persistent/shared): Always provisioned and ready. Jobs attach instantly.
  - Enable **auto-termination** (e.g., after 10-30 minutes of idle) to shut down when not in use, restarting on the next job trigger.
  - Best for your scenario: Low latency, but managed costs.

If your job runtime is <1 minute (e.g., quick stream micro-batch), the cluster can auto-terminate between runs, but keep it in a "running" state via scheduling or manual start for reliability.

#### Comparison: Job vs. All-Purpose Clusters for Frequent Scheduling

| Aspect | Job Clusters | All-Purpose Clusters |
|--------|--------------|----------------------|
| **Startup Time** | 1-5 min (provisioning) | Instant (already running) |
| **Suitability for 1-Min Schedules** | Poor (queuing/delays) | Excellent (with auto-terminate) |
| **When to Use** | Infrequent/batch jobs (e.g., hourly/daily) | Frequent/interactive (e.g., streaming, every min) |
| **Termination** | Auto after job ends | Manual or auto after idle (configurable) |
| **Sharing** | Job-only (isolated) | Multi-user (interactive notebooks/jobs) |

### Is It Costly to Have an Always-Running Databricks Cluster?

**Short Answer**: It *can* be, but not excessively if optimized—expect **$50-500/month** for a small cluster running 24/7 with auto-scaling and discounts, depending on size/location. All-Purpose Clusters cost ~2x more per DBU than Job Clusters, but for every-minute jobs, the time savings outweigh this. Use commitments and idle controls to cut 30-50%.

#### Cost Breakdown (2025 Pricing Estimates)
Databricks bills via **Databricks Units (DBUs)** per hour (processing power) + underlying cloud VM costs (e.g., AWS EC2). Pricing varies by tier (Standard/Premium), cloud (AWS/Azure/GCP), and commitments. From recent data:

- **DBU Rates** (Premium Tier, per DBU-hour):
  | Workload Type | AWS | Azure | Notes |
  |---------------|-----|-------|-------|
  | **Job Clusters** | ~$0.15-0.30 | ~$0.30-0.40 | Lower for non-interactive; spin-up only. |
  | **All-Purpose Clusters** | ~$0.40-0.60 | ~$0.55-0.80 | ~2x higher; charged while running. |

- **Example Monthly Cost** (small cluster, e.g., 2-4 nodes, AWS Premium, no commitments):
  | Scenario | DBU-Hour Cost | VM Cost (est.) | Total/Month (24/7) | With 30% DBCU Discount |
  |----------|---------------|----------------|---------------------|-------------------------|
  | **Job Cluster** (infrequent) | $0.20/DBU | $0.10-0.20/node-hr | $10-50 (on-demand only) | $7-35 |
  | **All-Purpose** (every min, auto-terminate 10-min idle) | $0.50/DBU | $0.20-0.40/node-hr | $200-800 (if always-on) | $140-560 |
  | **Optimized All-Purpose** (spot instances + scale-to-zero) | $0.50/DBU | $0.10-0.30/node-hr | $100-400 | $70-280 |

- **Factors Driving Cost**:
  - **Always-On Penalty**: Charged per second while active (even idle). A 4-node cluster idling 24/7 could hit $300+/month in DBUs alone.
  - **Savings Tips** (30-50% reduction):
    - **Databricks Commit Units (DBCUs)**: Pre-buy for 1/3-year terms; up to 37% off pay-as-you-go.
    - **Auto-Termination**: Set to 10-15 min idle—cluster shuts down between jobs if no activity.
    - **Auto-Scaling**: Min 1 node, max based on load; use spot/preemptible VMs for 50-90% VM savings.
    - **Serverless SQL/Jobs**: Emerging in 2025; pay-per-query, no cluster management (~20-40% cheaper for light workloads).
    - **Reservations**: Cloud-side (e.g., AWS Reserved Instances) for VMs.

For your every-minute streaming job, an All-Purpose cluster is cost-justified if jobs are short/light. Monitor via Databricks Cost Reports or third-party tools like CloudZero. If costs spike, switch to Serverless (if available for your workload) or batch less frequently.

#  Achieving Near-Real-Time Processing for  Databricks Job

Yes, for **almost real-time (near-RT) processing** of DynamoDB streams (via S3 JSONL exports), introducing a second AWS Lambda function to trigger your Databricks job immediately after the first Lambda (DynamoDB stream handler) completes is a **viable but not optimal** approach.  
It's better suited for **batch-oriented jobs**, but your code uses **streaming Auto Loader** (`spark.readStream.format("cloudFiles")`), which is already designed for incremental, low-latency ingestion. 
The best path forward is to **enable S3 event notifications directly in Auto Loader** for true event-driven processing without extra components. 

##  Why Not Always the Best: Lambda 2 + Databricks Jobs API Trigger
This setup would work: Lambda 1 (DynamoDB → S3) completes → Triggers S3 Event Notification → Lambda 2 invokes Databricks Jobs API (`/api/2.1/jobs/run-now`) to start your job.

- **How It Works**:
  1. Configure S3 bucket for **Event Notifications** on object creation (e.g., new JSONL file).
  2. Route to SNS/SQS → Lambda 2.
  3. In Lambda 2 (Python): Use `requests` to POST to Databricks API with your job ID and auth token (stored in Secrets Manager).
     ```python
     import requests
     import json

     def lambda_handler(event, context):
         # Extract S3 key from event
         s3_key = event['Records'][0]['s3']['object']['key']
         
         # Databricks API call
         url = "https://<your-databricks-workspace>.cloud.databricks.com/api/2.1/jobs/run-now"
         headers = {
             "Authorization": "Bearer <your-personal-access-token>",
             "Content-Type": "application/json"
         }
         payload = {
             "job_id": <your-databricks-job-id>,  # From your job config
             "notebook_params": {"s3_path": f"s3://{CONFIG['s3_bucket']}/{s3_key}"}  # Pass file path dynamically
         }
         
         response = requests.post(url, headers=headers, data=json.dumps(payload))
         if response.status_code == 200:
             print(f"Triggered Databricks job for {s3_key}")
         else:
             raise Exception(f"API error: {response.text}")
     ```
  - Latency: ~5-30 seconds end-to-end (S3 event → Lambda → API → Databricks start).

- **Pros**:
  - Simple if your job is **batch-only** (non-streaming): Triggers a full run per file.
  - Flexible: Pass params (e.g., specific file path) to process only new data.
  - No polling waste.

- **Cons**:
  - **Added Complexity/Cost**: Extra Lambda (cold starts add 100ms-1s latency; ~$0.20/million invocations).
  - **Overkill for Streaming**: Your code is already set up for continuous ingestion—re-triggering the whole job per file causes overlap/restarts, wasting resources.
  - **Spin-Up Delays**: If using Job Clusters, each trigger waits 1-5 min to provision; All-Purpose helps but still ~10-20s.
  - **Reliability**: API rate limits (100/min), token management, error retries needed.

- **When to Use**: If switching to a **batch job** (e.g., `spark.read.json(single_file)` instead of streaming), or if notifications aren't feasible.

## Better Alternative: Enable S3 Event Notifications in Auto Loader (Native Near-RT)
Your code uses **Auto Loader streaming**, which supports **file notification mode**—S3 sends events directly to Databricks (via auto-provisioned SNS/SQS). This turns your 1-minute polling into **event-driven micro-batches** (processes new files in ~10-60 seconds). No Lambda 2 needed!

- **How It Works** (As of Nov 2025 Docs):
  1. S3 bucket notifies on new object (JSONL file from Lambda 1).
  2. Databricks auto-sets up SNS topic + SQS queue (one-time via code or UI).
  3. Auto Loader subscribes and triggers micro-batches on events—no fixed schedule.
  - End-to-End Latency: ~5-20 seconds (S3 event → Databricks process).

- **Pros**:
  - **True Near-RT**: Processes files as they land; scales to high volume without manual triggers.
  - **Zero Extra Cost/Components**: Built-in; no Lambda invocations.
  - **Fault-Tolerant**: Handles retries, schema evolution, exactly-once semantics.
  - **Your Code is Ready**: Just flip a flag and one-time setup.

- **Cons**:
  - Requires **S3 permissions** for Databricks (IAM role with SNS/SQS access).
  - One-time setup (~5 min); queue backlogs if cluster is down.
  - Still needs a running cluster (but auto-terminate works).

- **Implementation Steps**:
  1. **Grant Permissions** (One-Time):
     - In AWS IAM: Add Databricks service role to S3 bucket policy for SNS/SQS (docs: [Auto Loader File Notification Setup](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/file-notification-mode)).
     - Example Policy Snippet:
       ```json
       {
         "Effect": "Allow",
         "Principal": {"Service": "sqs.amazonaws.com"},
         "Action": "sns:Publish",
         "Resource": "arn:aws:sns:*:*:AutoLoader-*"
       }
       ```

  2. **Update Your Code** (In `read_stream()`):
     ```python
     @retry(max_attempts=3, delay=10)
     def read_stream():
         print(f"Reading from: {SOURCE_PATH}")
         
         return (
             spark.readStream
                  .format("cloudFiles")
                  .option("cloudFiles.format", "json")
                  .option("cloudFiles.schemaLocation", CONFIG["schema_path"])
                  .option("cloudFiles.useNotifications", "true")  # Enable events (key change!)
                  .option("cloudFiles.maxFilesPerTrigger", CONFIG["max_files_per_trigger"])
                  .option("cloudFiles.validateOptions", "true")
                  .option("cloudFiles.schemaEvolutionMode", "addNewColumn")
                  .option("rescuedDataColumn", "_rescued_data")
                  .schema(raw_schema)
                  .load(SOURCE_PATH)
                  .withColumn("source_file", F.col("_metadata.file_path"))  # As discussed
         )
     ```
     - Remove the 1-minute schedule—run the job continuously (e.g., "Continuously" in Job config).

  3. **Job Config**:
     - Use **All-Purpose Cluster** with auto-terminate (10 min idle).
     - Schedule: "Continuously" or manual start (notifications keep it active).
     - Monitor: Check SQS queue depth in AWS Console.

- **Latency Comparison**:
  | Approach | End-to-End Delay | Setup Effort | Extra Cost/Month |
  |----------|------------------|--------------|------------------|
  | **Current (Poll Every Min)** | 30s-1min | Low | Low (polling overhead) |
  | **Lambda 2 + API Trigger** | 10-40s | Medium | $1-5 (Lambda + API calls) |
  | **Auto Loader Notifications** | 5-20s | Low-Medium | $0 (native) |

#### Cost Implications
- **No Major Change**: Notifications don't add DBU costs—same as polling, but more efficient (processes only new files).
- **Cluster**: Still needs to be "always ready" (All-Purpose, ~$100-300/month optimized, as before). Events keep it active minimally.
- **Total**: For near-RT, expect +10-20% vs. batch (due to more frequent micro-batches), but far cheaper than over-provisioning.

#### Recommendation
- **Go with Auto Loader Notifications**: It's the **cleanest, most scalable** for your streaming setup—achieves near-RT without Lambda 2. Implement the code change and permissions today.
- **Fallback**: If notifications fail (e.g., IAM issues), add Lambda 2 for API triggers—it's a quick win (~30 min setup).
- **Test**: Start with `maxFilesPerTrigger=1` and a dev bucket; measure latency with timestamps in your data.

If you hit setup snags (e.g., SNS permissions), share error logs!

