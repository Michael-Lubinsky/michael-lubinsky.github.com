How to run your PySpark code every minute **outside a notebook** and manage it end-to-end.

# 1) Package your notebook logic as a Python entrypoint

Refactor your notebook into a tiny callable module plus a `main.py` runner. Put this in a Databricks Repo (recommended) or upload to DBFS.

```
repo-root/
  ingest/
    __init__.py
    job_logic.py      # your existing function(s)
    main.py           # entrypoint that calls your function
```

`job_logic.py` (sketch)

```
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

`main.py`

```
from ingest.job_logic import run_job

if __name__ == "__main__":
    run_job()
```

Push this repo to Git and use **Repos** in Databricks to keep it synced.

# 2) Create a Databricks Job (non-interactive)

You have three good compute choices:

* **Serverless compute for Jobs** (best if available): fully managed, quick starts, no cluster babysitting.
* **Job cluster**: ephemeral cluster created per run (simple, but cold-start overhead every minute can be costly).
* **Existing all-purpose cluster**: fastest per-minute cadence (no cold start), but you pay for it to stay running.

For a true **every-minute** cadence, prefer **Serverless** or an **Existing cluster kept warm**. A Job cluster spinning up every minute is usually too slow/expensive.

## Create the Job (UI)

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

## Create the Job (JSON + CLI)

If you automate with the new `databricks` CLI:

`job.json` (example; adjust paths)

```
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

Create/update:

```
databricks jobs create --json-file job.json
# or
databricks jobs reset --job-id <id> --json-file job.json
```

**Tip:** In the UI, selecting “Every minute” will populate a correct Quartz cron; if you’re unsure about the expression, use the UI first.

# 3) Credentials to DynamoDB/S3

Because you’re on **Serverless/Jobs**, the clean path is an **instance profile / IAM role** that grants read to DynamoDB and write to your S3/Delta location. In the job’s compute settings:

* For **Serverless compute**: attach the workspace’s **serverless access**/instance profile (your admin might need to map it).
* For **Existing or Job clusters**: set the **Instance Profile / IAM role**.
  Then your Spark code can use the default provider chain (no hardcoded keys). In Python, `boto3` (if used) will pick up the role automatically.

# 4) If you truly need “every minute,” consider streaming

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

# 5) How to stop the non-interactive job

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

# 6) Quick checklist for your case

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

---

There is DynamoDB table populated by external process.
Goal is to build almost real-time pipeline which 
reads the new records from DynamoDB, transform it  using PySpark and append transformed records into DataBricks Unity catalog table.

I consider following options:

Option 1:  Direct DynamoDB Table Access (Batch Reads)
---------------------------------------------------
Direct polling from DynamoDB table to Databricks using GSI global secondry index on column updated_at
Create Global Secondary Index (GSI) on updated_at column.
Periodically call table.query() 
Store max(updated_at) of already processed records in persistent storage, in order to read
only new recors:   max(updated_at) will be passed as argument to  tab.query() 


Option 2: DynamoDB Streams (Change Data Capture)
----------------------------------------------
AWS Lambda ->  S3 -> Databricks


 
Here’s a pragmatic comparison + a concrete reference design for a near-real-time (sub-minute to a few minutes) DynamoDB → PySpark → Unity Catalog pipeline. I’ll keep it punchy and actionable.

──────────────────────────────────────────────────────────────────────────────
- If you want “robust + low-ops + ~1–2 min latency”: **Use DynamoDB Streams → (EventBridge Pipes or Kinesis Firehose) → S3 → Databricks Auto Loader → Delta/Unity**. This is the sweet spot for cost, reliability, and simplicity.
- If volume is small and you need a quick start with minute polling: **Use a GSI on (tenant, updated_at)** and batch pull with a persisted cursor + idempotent MERGE into Delta.
- If you truly need sub-second to tens-of-seconds latency without an S3 landing zone: **Streams → Kinesis Data Streams → Databricks Structured Streaming**, but this adds complexity.

──────────────────────────────────────────────────────────────────────────────
Option 1 — Direct DynamoDB table access (batch pulls via GSI)
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

Notes
- If you have deletes, propagate a tombstone flag and handle it in MERGE (DELETE WHEN MATCHED AND s.is_deleted = true).
- Batch schedule: Databricks Job every 1–5 minutes is reasonable. Avoid per-minute if you expect large scans—tune to your RCU & batch size.

──────────────────────────────────────────────────────────────────────────────
Option 2 — DynamoDB Streams (CDC) → S3 → Databricks Auto Loader
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

Notes
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




---

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

