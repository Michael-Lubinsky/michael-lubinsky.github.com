
### DynamoDB Streams → Lambda → S3 → Databricks Auto Loader → Unity Catalog
 
──────────────────────────────────────────────────────────────────────────────
1) High-level flow

DynamoDB table (Streams = NEW_AND_OLD_IMAGES)
   ⭢ Event source mapping
      ⭢ AWS Lambda (Python 3.11)
         - Deserialize Stream images
         - Minimal transform/normalize
         - Batch buffer (size/time) → write objects to S3 (Parquet OR NDJSON.gz)
         - Optionally emit tombstones for REMOVE
   ⭢ S3 prefix (partitioned by date/hour, e.g. s3://bucket/ddb/your_table/dt=YYYY-MM-dd/HH=HH/)
      ⭢ Databricks Auto Loader (Structured Streaming)
         - Read as `cloudFiles`
         - Business transforms
         - MERGE into Delta/Unity table (idempotent upsert on pk + updated_at)
         - Handle deletes (remove rows matching tombstone keys)

Latency target: 10–90 seconds typical (tune Lambda batching + S3 buffer size/time).

──────────────────────────────────────────────────────────────────────────────
2) DynamoDB settings

- Enable Streams on the source table:
  - StreamViewType: **NEW_AND_OLD_IMAGES** (or at least NEW_IMAGE).
- Keys: ensure a deterministic primary key (e.g., pk + sk OR a unique id).
- If you use TTL or physical deletes, plan how to propagate deletions (see §6).

──────────────────────────────────────────────────────────────────────────────
3) Event source mapping → Lambda

Recommended Lambda event source mapping (per consumer):
- Batch size: 100–1000 (start small, e.g., 200)
- Batch window: 1–30 seconds (start ~5s)
- Maximum concurrent batches: 2–5 (start small, scale later)
- On failure: send to SQS DLQ (configure on Lambda).

These settings give near-real-time while producing S3 files big enough for efficient downstream reads.

──────────────────────────────────────────────────────────────────────────────
4) IAM policies (minimal)

Lambda execution role needs:
- CloudWatch Logs
- Read from the stream (granted automatically via event source mapping on the table or explicitly)
- Write to S3 prefix

Example policy statements to attach to the Lambda role (adjust ARNs):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:123456789012:*"
    },
    {
      "Sid": "S3Write",
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:AbortMultipartUpload","s3:ListBucket","s3:PutObjectAcl"],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/ddb/your_table/*"
      ]
    },
    {
      "Sid": "DDBDescribeStream",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      "Resource": "*"
    }
  ]
}
```
──────────────────────────────────────────────────────────────────────────────
5) Lambda: Python handler (Streams → S3)

Two common file formats:

(A) **NDJSON.gz** (newline-delimited JSON, gzipped)
- Simple, schema-agnostic, great for rapid iteration.
- Auto Loader can infer schema; you can add evolution later.

(B) **Parquet** (snappy)
- Smaller + faster in Spark.
- Requires schema control; good once your schema stabilizes.

Below is **NDJSON.gz** variant with robust deserialization, batching, partitioning and minimal transform:

# lambda_function.py
```python
import base64
import boto3
import gzip
import io
import json
import os
import time
from datetime import datetime, timezone
from boto3.dynamodb.types import TypeDeserializer

S3_BUCKET = os.environ.get("S3_BUCKET", "your-bucket")
S3_PREFIX = os.environ.get("S3_PREFIX", "ddb/your_table")

# Buffer thresholds
MAX_RECORDS = int(os.environ.get("MAX_RECORDS", "2000"))
MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", "8_000_000"))  # ~8MB before gzip
MAX_SECONDS = int(os.environ.get("MAX_SECONDS", "15"))

deser = TypeDeserializer()
s3 = boto3.client("s3")

def ddb_to_python(image: dict) -> dict:
    # Convert DDB JSON to native Python
    return {k: deser.deserialize(v) for k, v in (image or {}).items()}

def normalize(rec: dict) -> dict:
    """
    Minimal normalization:
    - Ensure we keep pk / sk (or id) and updated_at
    - Add metadata: _eventName, _approxStreamTs, _ingestTs
    """
    event_name = rec.get("eventName")
    ddb = rec.get("dynamodb", {})
    new_img = ddb_to_python(ddb.get("NewImage"))
    old_img = ddb_to_python(ddb.get("OldImage"))
    keys = ddb_to_python(ddb.get("Keys"))

    approx_ts = ddb.get("ApproximateCreationDateTime")
    approx_ms = int(approx_ts * 1000) if isinstance(approx_ts, (int, float)) else None

    out = new_img if event_name in ("INSERT", "MODIFY") else keys
    out = out or {}
    # REQUIRED: ensure primary keys are present (pk/sk or id)
    # If your table uses pk/sk, rename or preserve appropriately:
    # out["pk"] = out.get("pk") or keys.get("pk")
    # out["sk"] = out.get("sk") or keys.get("sk")

    out["_eventName"] = event_name
    out["_approxStreamTs"] = approx_ms
    out["_ingestTs"] = int(time.time() * 1000)
    # If you have a canonical updated_at, ensure it exists (fallback to ApproximateCreationDateTime):
    if "updated_at" not in out and approx_ms is not None:
        out["updated_at"] = approx_ms

    return out

class NDJsonBuffer:
    def __init__(self):
        self.buf = io.BytesIO()
        self.count = 0
        self.uncompressed_size = 0
        self.start_time = time.time()

    def add(self, obj: dict):
        line = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        self.buf.write(line)
        self.count += 1
        self.uncompressed_size += len(line)

    def should_flush(self) -> bool:
        if self.count == 0:
            return False
        if self.count >= MAX_RECORDS:
            return True
        if self.uncompressed_size >= MAX_PAYLOAD_BYTES:
            return True
        if (time.time() - self.start_time) >= MAX_SECONDS:
            return True
        return False

    def flush_to_s3(self):
        if self.count == 0:
            return

        # Partition path by UTC date/hour
        now = datetime.now(timezone.utc)
        dt = now.strftime("%Y-%m-%d")
        hh = now.strftime("%H")

        # Compose a deterministic-ish name (ts + random suffix) to avoid collisions
        # You can also include shardId/batchId if desired.
        fname = f"dt={dt}/HH={hh}/batch_{int(now.timestamp())}_{self.count}.ndjson.gz"
        key = f"{S3_PREFIX}/{fname}"

        # Gzip the buffer
        gz_buf = io.BytesIO()
        with gzip.GzipFile(fileobj=gz_buf, mode="wb") as gz:
            gz.write(self.buf.getvalue())

        gz_buf.seek(0)
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=gz_buf.getvalue())

        # Reset buffer
        self.buf = io.BytesIO()
        self.count = 0
        self.uncompressed_size = 0
        self.start_time = time.time()

def handler(event, context):
    buf = NDJsonBuffer()

    # Records arrive grouped by stream shard
    for r in event.get("Records", []):
        # (optional) dedupe across retries: eventID is unique per stream record
        # If strict idempotency is required, write eventIDs to a small DynamoDB table with TTL and skip duplicates.

        if r.get("eventSource") != "aws:dynamodb":
            continue
        obj = normalize(r)
        buf.add(obj)
        if buf.should_flush():
            buf.flush_to_s3()

    # Final flush
    buf.flush_to_s3()

    return {"status": "ok"}
```
Environment variables to set on Lambda:
- S3_BUCKET=your-bucket
- S3_PREFIX=ddb/your_table
- MAX_RECORDS=2000
- MAX_PAYLOAD_BYTES=8000000
- MAX_SECONDS=15

Notes
- This writes GZIPed NDJSON. If you prefer Parquet, use pyarrow fastparquet (bundle as Lambda layer or container image) and write .parquet with robust schema mapping.
- NDJSON works great with Auto Loader; you can later switch to Parquet after schema stabilizes.

──────────────────────────────────────────────────────────────────────────────
6) Deletions (REMOVE) handling

You have two patterns:

A) Tombstones
- In Lambda, when eventName == "REMOVE", emit a record with keys (pk/sk) + `is_deleted=true`.
- Downstream MERGE treats `is_deleted=true` as DELETE (or sets a deleted flag).

B) Hard deletes
- Collect DELETE keys separately and in `foreachBatch` perform a Delta DELETE:
  DELETE FROM target WHERE pk = ? AND sk = ?
- This is easy if you split your incoming micro-batch into upserts vs deletes.

The NDJSON above encodes `_eventName`. In Databricks you can branch on it.

──────────────────────────────────────────────────────────────────────────────
7) Databricks Auto Loader (Structured Streaming)

Spark (Python) sketch consuming NDJSON.gz:
```python
from pyspark.sql import functions as F

source_path = "s3://your-bucket/ddb/your_table"
checkpoint  = "s3://your-bucket/_checkpoints/your_table"
schema_loc  = "s3://your-bucket/_schemas/your_table"

raw = (
  spark.readStream
       .format("cloudFiles")
       .option("cloudFiles.format", "json")
       .option("cloudFiles.inferColumnTypes", "true")
       .option("cloudFiles.schemaLocation", schema_loc)
       .load(source_path)
)

# Optional: Do selective casts / struct normalization here
df = (
  raw
  # Ensure pk/sk or id, updated_at, and event markers are present
  .withColumn("_ingest_ts", F.current_timestamp())
)

target_tbl = "hcai_databricks_dev.chargeminder2.fact_events"

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {target_tbl} (
  pk STRING,
  sk STRING,
  updated_at BIGINT,
  -- other columns...
  _ingest_ts TIMESTAMP
) USING DELTA TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

def upsert_batch(micro_df, batch_id: int):
    micro_df.createOrReplaceTempView("incoming")

    # Upserts
    spark.sql(f"""
      MERGE INTO {target_tbl} t
      USING (
        SELECT * FROM incoming
        WHERE _eventName IN ('INSERT','MODIFY') OR is_deleted = false
      ) s
      ON t.pk = s.pk AND t.sk = s.sk
      WHEN MATCHED AND s.updated_at >= t.updated_at THEN UPDATE SET *
      WHEN NOT MATCHED THEN INSERT *
    """)

    # Deletes (either use `_eventName='REMOVE'` or `is_deleted=true`)
    spark.sql(f"""
      DELETE FROM {target_tbl}
      WHERE (pk, sk) IN (
        SELECT pk, sk FROM incoming
        WHERE _eventName = 'REMOVE' OR is_deleted = true
      )
    """)

(
  df.writeStream
    .option("checkpointLocation", checkpoint)
    .trigger(processingTime="30 seconds")  # tune to your latency goal
    .foreachBatch(upsert_batch)
    .start()
)
```
Tips
- If you want simpler logic, store upserts and deletes in two separate prefixes from Lambda (e.g., ddb/your_table/upserts/..., ddb/your_table/deletes/...) and have two streams.
- Use `availableNow` to catch up large backfills without leaving a running cluster.

──────────────────────────────────────────────────────────────────────────────
8) Backfills & reprocessing

- Historical export: Use AWS Data Pipeline/DMS/Glue Script or ad-hoc scan to dump the full table to S3 under the SAME partition scheme (`dt=YYYY-MM-dd/HH=HH`).
- Then run your Auto Loader in `availableNow` mode to ingest history → up to date.
- Since the sink is MERGE-based and idempotent, replays are safe (latest updated_at wins).

──────────────────────────────────────────────────────────────────────────────
9) Idempotency & retries

- Lambda may re-deliver a batch on transient errors. You can:
  - Rely on MERGE “latest-wins” (simple; works if updated_at is monotonic per key).
  - Add a dedupe key (DDB stream `eventID`) to an idempotency store (DynamoDB table with TTL). Check before writing to S3 to avoid duplicates. (Usually not necessary if sink MERGE is correct.)
- When writing to S3, object names are unique (timestamp + count). If you want stronger idempotency, incorporate a deterministic hash of concatenated eventIDs into the filename.

──────────────────────────────────────────────────────────────────────────────
10) Operational guardrails

- DLQ: Configure Lambda → SQS on failure with a retention policy; add CloudWatch alarm on DLQ depth.
- CloudWatch metrics to watch: Lambda errors, throttles, duration; DDB Stream IteratorAgeMilliseconds (should stay low); S3 4xx/5xx.
- Size: Aim for 5–64 MB gz files per flush. If objects are too tiny, increase batch window and/or MAX_RECORDS.
- Schema evolution: With NDJSON, Auto Loader’s `schemaLocation` handles adds. For Parquet, maintain a schema version header in S3 path or payload.

──────────────────────────────────────────────────────────────────────────────
11) (Optional) Parquet instead of NDJSON.gz

- Add a Lambda layer with pyarrow (or ship a container image Lambda).
- In the handler, batch rows → pandas DataFrame → to_parquet(BytesIO(), compression="snappy") → PutObject.
- Keep partitioning identical. Databricks will read much faster.

──────────────────────────────────────────────────────────────────────────────
12) Quick checklist to go live

[ ] Enable Streams (NEW_AND_OLD_IMAGES) on the DDB table  
[ ] Create S3 bucket/prefix + encryption + lifecycle  
[ ] Create Lambda (Python 3.11), set env vars, attach IAM role (S3 + Logs + DDB Streams)  
[ ] Add Event Source Mapping (batch size/window tuned)  
[ ] Test: insert/modify/delete a few items → see S3 files land  
[ ] Create Auto Loader notebook/Job with foreachBatch MERGE+DELETE  
[ ] Create Unity table and validate dedupe/idempotency  
[ ] Add DLQ + CloudWatch alarms + cost/logging dashboards


