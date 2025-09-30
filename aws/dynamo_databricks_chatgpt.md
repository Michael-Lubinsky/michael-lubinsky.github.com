 
# DynamoDB → Databricks (every few minutes): Recommended pipelines

Below are three proven patterns. Pick the one that best fits your constraints. 

## Option A (default): DynamoDB Streams → Kinesis Firehose → S3 → Databricks Auto Loader → Delta
**When to use:** You want near-real-time (1–5 min) with simple ops and strong exactly-once semantics in Databricks.

### Flow
1) **DynamoDB Streams** (NEW_IMAGE + REMOVE)  
   - Enable on each table; choose `NEW_AND_OLD_IMAGES` or at least `NEW_IMAGE` if you don’t need the old state.
   - Streams will carry inserts/updates/deletes (TTL expirations appear as REMOVE if TTL is enabled).
2) **Kinesis Data Streams** (optional but common)  
   - Streams provide scalable buffering and replay, used as source for Firehose.
3) **Kinesis Data Firehose → S3 (raw landing)**  
   - Delivery stream buffers for N MB or N minutes (e.g., `64 MB` or `300 sec`) and writes **raw JSON** or **Parquet** to S3.
   - S3 prefix suggestion: `s3://<lake>/raw/dynamodb/<table>/ingest_date=YYYY/MM/DD/HH/`
4) **Databricks Auto Loader (cloudFiles)** reads S3 continuously or every few minutes into **Delta Bronze**  
   - Auto Loader tracks new files with a scalable file notification mechanism and stores checkpoints.
5) **Delta Live Tables (DLT) or Jobs** refine Bronze → Silver (dedupe/merge) → Gold (analytics)  
   - Use MERGE to upsert on the table’s primary key and handle deletes (from REMOVE events).

### Pros
- Low-latency ~minutes, scalable, cost-effective; durable S3 landing; easy schema evolution; exactly-once with checkpoints + MERGE.
### Cons
- Requires stream plumbing (Streams/Firehose).  
- Slightly more AWS config than DMS.

### Databricks code (PySpark, Auto Loader → Bronze)
```python
from pyspark.sql.functions import col, input_file_name, current_timestamp

raw_path = "s3://<lake>/raw/dynamodb/my_table/"
bronze_path = "s3://<lake>/bronze/dynamodb/my_table"     # Delta table storage
chkpt_path = "s3://<lake>/_chk/dynamodb/my_table_bronze" # Auto Loader checkpoint

df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")        # or "parquet" if Firehose writes Parquet
      .option("cloudFiles.inferColumnTypes", "true")
      .option("cloudFiles.schemaLocation", chkpt_path + "_schema")
      .load(raw_path)
      .withColumn("_ingest_file", input_file_name())
      .withColumn("_ingest_ts", current_timestamp())
     )

(df.writeStream
   .format("delta")
   .option("checkpointLocation", chkpt_path)
   .outputMode("append")
   .trigger(processingTime="2 minutes")           # or "availableNow" for catch-up
   .start(bronze_path))
````

### Silver upsert (handle I/U/D with MERGE)

Assume each record carries a stable business key `pk` and an op field like `op` in (`INSERT`,`MODIFY`,`REMOVE`) from Streams.

```sql
-- Create Silver as Delta (run once)
CREATE TABLE IF NOT EXISTS silver.my_table (
  pk STRING,
  -- ... other columns ...,
  updated_at TIMESTAMP,
  is_deleted BOOLEAN
) USING DELTA;

-- Continuous job (SQL cell in a scheduled Job) that upserts from Bronze micro-batch
MERGE INTO silver.my_table s
USING (
  SELECT
    b.record.pk as pk,
    b.record.* EXCEPT(pk),
    b.op as op,
    b._ingest_ts as _ingest_ts
  FROM bronze.dynamodb_my_table b
  -- optionally filter only the last few hours to limit scanned set
) c
ON s.pk = c.pk
WHEN MATCHED AND c.op = 'REMOVE' THEN
  UPDATE SET is_deleted = TRUE, updated_at = c._ingest_ts
WHEN MATCHED AND c.op IN ('INSERT', 'MODIFY') THEN
  UPDATE SET
    -- set all mutable columns from c.*,
    updated_at = c._ingest_ts,
    is_deleted = FALSE
WHEN NOT MATCHED AND c.op IN ('INSERT', 'MODIFY') THEN
  INSERT (pk, /* other cols */, updated_at, is_deleted)
  VALUES (c.pk, /* other cols */, c._ingest_ts, FALSE);
```

**Notes**

* If you need de-duplication (e.g., rare replays), compute a deterministic `_event_id` such as `(pk, stream_sequence_number)` and keep last-write-wins by `updated_at` or a version counter.
* For deletes: propagate `REMOVE` to `is_deleted=TRUE` (soft delete) or physically delete with `WHEN MATCHED AND op='REMOVE' THEN DELETE`.
* Add a **watermark** in Bronze/streaming reads to guard infinite late data if needed.

---

## Option B: AWS DMS → S3 → Databricks Auto Loader → Delta

**When to use:** You want an **initial full copy + CDC** without building a Streams/Firehose pipeline, or you need table-level snapshots easily.

### Flow

1. **DMS Task** per table (or a few) with Full Load + CDC from DynamoDB → **S3**

   * Configure DMS to write JSON/Parquet and include `op` (I/U/D) and commit timestamps.
2. **Databricks Auto Loader** ingests the S3 folders to Bronze.
3. **MERGE** into Silver (same as Option A).

### Pros

* Simplifies initial backfill + CDC in one tool.
* Easy to throttle and monitor; robust retry.

### Cons

* Slightly higher DMS overhead/cost; latency ~1–5 min typical.

---

## Option C: Minimal setup (Batch exports) → S3 → Auto Loader

**When to use:** Streams not available yet, near-real-time not critical; you can tolerate **5–15 minute** batches.

### Variants

* **DynamoDB export to S3 (PITR Export)** hourly + incremental diffs via Streams later.
* **Custom Lambda** every N minutes: Scan/Query changes since last watermark → write to S3.

  * Keep a **high-watermark** (e.g., `updated_at` or `sequence_number`) in DynamoDB/SSM Parameter Store to avoid re-reads.
  * Not recommended for very large tables due to Scan costs/throttling.

---

## Cross-cutting Design Details

### S3 Layout (suggested)

* Raw landing (append-only):
  `s3://<lake>/raw/dynamodb/<table>/ingest_date=YYYY/MM/DD/HH/`
* Bronze Delta tables (1:1 with source tables):
  `s3://<lake>/bronze/dynamodb/<table>`
* Silver Delta tables (curated, de-duplicated, merged):
  `s3://<lake>/silver/<domain>/<table>`
* Gold Delta tables (business aggregates):
  `s3://<lake>/gold/<subject_area>/<mart>`

### Schema evolution

* Prefer **Parquet** from Firehose/DMS to lock types.
* If JSON, enable `cloudFiles.inferColumnTypes` and persist schema to a stable path; consider **schema hints** for key columns:

```python
spark.readStream.format("cloudFiles") \
  .option("cloudFiles.format", "json") \
  .option("cloudFiles.schemaLocation", chkpt) \
  .schema("pk string, updated_at timestamp, ...") \
  .load(raw_path)
```

### Exactly-once & Ordering

* Use **Delta + MERGE** and a **checkpoint** on every streaming write.
* Choose a **deterministic key** and **update_ts/version** to resolve late or out-of-order events.
* If DynamoDB has no `updated_at`, use Streams sequence number or DMS commit timestamp.

### Deletes / TTL

* If TTL is enabled, Streams emits `REMOVE`. Map it to `is_deleted=TRUE` or `DELETE` row in Silver.
* If you only receive periodic snapshots, derive deletes by **anti-join** vs latest snapshot.

### Triggers & Latency

* Firehose buffer: e.g., 1–5 minutes (or smaller MB thresholds).
* Auto Loader trigger: `processingTime="2 minutes"` (commonly 1–5 minutes).
* For backfills, run `availableNow` once to drain the backlog quickly.

### Databricks Jobs / DLT

* Put Bronze ingestion as a **streaming job**, then run a **DLT pipeline** for Bronze→Silver→Gold with expectations:

```python
@dlt.table(comment="Cleaned and deduped")
def silver_my_table():
    df = dlt.read_stream("bronze_my_table")

    # example dedup by pk + latest updated_at
    from pyspark.sql import functions as F, Window as W
    w = W.partitionBy("pk").orderBy(F.col("updated_at").desc())
    return (df
      .withColumn("rn", F.row_number().over(w))
      .filter("rn=1")
      .drop("rn"))
```

### Security (IAM)

* Attach an **instance profile** to your Databricks cluster/job with least-privilege S3 access.
* Firehose bucket policy allows delivery role.
* Optional: use **SSE-KMS** for S3 encryption and pass the KMS key in Firehose + Databricks.

### Monitoring & Ops

* CloudWatch alarms on Firehose/DMS errors & S3 delivery failures.
* Databricks: monitor streaming query progress, trigger status, input rows/sec, and checkpoint liveness.
* Add data quality checks in DLT expectations; route bad rows to a quarantine Delta table.

### Cost & Scale Tips

* Prefer **Parquet** in raw landing to reduce size & CPU.
* Partition S3 by hour or by hash buckets for very hot tables (`partitionKeys=["ingest_date","bucket=hash(pk)%16"]`).
* Use **OPTIMIZE** + **ZORDER** in Silver/Gold for selective queries; schedule auto-compaction if needed.

---

## Quick Decision Guide

* **Need simple, near-real-time, durable landing?** → **Option A (Streams → Firehose → S3)**
* **Want integrated full-load + CDC with minimal custom glue?** → **Option B (DMS → S3)**
* **Okay with coarser latency and minimal infra now?** → **Option C (batch export/Lambda → S3)**

If you tell me:

* target tables & PKs,
* whether Streams/TTL are enabled,
* your desired SLA (e.g., <5 min),
  I’ll drop in exact Terraform + Databricks code for your setup.
 
# What is DMS?
**AWS Database Migration Service (DMS)** is a managed service from AWS that helps you move data between databases and other data stores.  
- It supports migrations from **DynamoDB → S3**, **RDS → Snowflake**, etc.  
- You can configure DMS to do a **full load** (copy all data once) and then apply **ongoing replication (CDC)** so that new changes (inserts, updates, deletes) keep flowing.  
- For DynamoDB specifically, DMS reads from **DynamoDB Streams** under the hood and writes to your target (often S3 in JSON/Parquet).  
- Latency is typically **seconds to a few minutes**, making it useful for near-real-time pipelines into a lakehouse (like Databricks).

---

# What is PITR Export?
**Point-in-Time Recovery (PITR) Export** is a DynamoDB feature that lets you **export your entire table at a specific point in time** to **Amazon S3**.  
- You first enable **PITR backups** on your DynamoDB table.  
- Then you can request an export, for example “give me the table exactly as it was at 2025-09-01 12:00 UTC.”  
- DynamoDB will dump the full dataset into S3 (usually as Parquet files).  
- This is good for **full historical snapshots** but **not for streaming CDC**, since it always exports the full table rather than just new records.  
- Typical use: load a full snapshot into Databricks for backfill, then switch to Streams/DMS for incremental updates.

---

# How they differ
- **DMS** → continuous **incremental replication** (new records every few minutes). Best for ongoing pipeline.  
- **PITR Export** → full **snapshot at a point in time**. Best for one-time historical load or recovery.

In practice, people often use:
1. **PITR Export → Databricks** for the initial bulk load.  
2. **DMS (or Streams→Firehose→S3)** for incremental updates.  
This combo keeps Databricks always in sync with DynamoDB.

Would you like me to sketch a combined **“backfill + incremental” design** that shows exactly how to use PITR Export once and then switch over to DMS/Firehose for continuous sync?
```

