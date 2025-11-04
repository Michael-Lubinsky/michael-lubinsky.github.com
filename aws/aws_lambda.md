
## DynamoDB Streams → Lambda → S3 → Databricks (Auto Loader)  

<https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html>

<https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions> All functions 

<https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/function?intent=authorFromScratch>  Create Lambda function

<https://docs.aws.amazon.com/lambda/latest/dg/testing-functions.html> Testing Lambda

 
```
----------------------------------------------------------------------
HIGH-LEVEL FLOW
----------------------------------------------------------------------
1) DynamoDB Stream (on chargeminder-car-telemetry) emits INSERT/MODIFY/REMOVE.
2) Lambda (Python) is triggered by the stream, converts records to JSON Lines.
3) Lambda writes gzip’d batches to S3 in a partitioned layout:
   s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/ingest_dt=YYYY-MM-DD/hour=HH/part-<ts>-<uuid>.json.gz
4) Databricks Auto Loader continuously ingests from that prefix into a Bronze Delta table.
5) Optional: add a DLQ (SQS) and CloudWatch alarms.

----------------------------------------------------------------------
PREREQS
----------------------------------------------------------------------
A) Stream enabled on the table (view type often: NEW_AND_OLD_IMAGES).
B) An IAM role for Lambda with:
   - dynamodb:DescribeStream, GetShardIterator, GetRecords, ListStreams (read the stream)
   - s3:PutObject (+ s3:AbortMultipartUpload, s3:PutObjectAcl if needed) into your bucket/prefix
   - logs:* for CloudWatch logging

C) S3 bucket policy allowing that role to PutObject to the target prefix (least privilege).

----------------------------------------------------------------------
IAM: LAMBDA EXECUTION ROLE (TRUST POLICY)
----------------------------------------------------------------------
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaAssume",
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

----------------------------------------------------------------------
IAM: LAMBDA PERMISSIONS POLICY (ATTACH TO THE ROLE ABOVE)
----------------------------------------------------------------------
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DdbStreamRead",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3WriteRaw",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/*"
      ]
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```
----------------------------------------------------------------------
OPTIONAL: S3 BUCKET POLICY (IF YOU WANT TO LIMIT PUTS TO THE LAMBDA ROLE)
----------------------------------------------------------------------
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowLambdaPutsToRaw",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<ACCOUNT_ID>:role/<YourLambdaRoleName>" },
      "Action": ["s3:PutObject","s3:AbortMultipartUpload"],
      "Resource": "arn:aws:s3:::chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/*"
    }
  ]
}
```
----------------------------------------------------------------------
LAMBDA: PYTHON RUNTIME (3.11+), HANDLER: app.lambda_handler
----------------------------------------------------------------------

# file: app.py
```python
import base64
import gzip
import io
import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.types import TypeDeserializer

S3_BUCKET = os.environ.get("S3_BUCKET", "chargeminder-2")
S3_PREFIX = os.environ.get(
    "S3_PREFIX",
    "raw/dynamodb/chargeminder-car-telemetry"
)

s3 = boto3.client("s3")
deser = TypeDeserializer()

def _ddb_val_to_py(attr):
    # Convert DynamoDB AttributeValue to native Python via TypeDeserializer
    # attr is like {"S":"x"} or {"N":"1"} or {"M":{...}} etc.
    return deser.deserialize(attr)

def _record_to_json_line(rec):
    # Build a CDC-like envelope for downstream processing
    event_name = rec["eventName"]  # INSERT | MODIFY | REMOVE
    event_id = rec["eventID"]
    approx_ts_ms = rec["dynamodb"].get("ApproximateCreationDateTime")
    # AWS provides seconds as float; normalize to ms int if present
    if isinstance(approx_ts_ms, (int, float)):
        approx_ts_ms = int(approx_ts_ms * 1000)

    new_image = rec["dynamodb"].get("NewImage")
    old_image = rec["dynamodb"].get("OldImage")

    new_obj = {k: _ddb_val_to_py(v) for k, v in (new_image or {}).items()}
    old_obj = {k: _ddb_val_to_py(v) for k, v in (old_image or {}).items()}

    out = {
        "event_name": event_name,
        "event_id": event_id,
        "approx_creation_time_ms": approx_ts_ms,
        "keys": {k: _ddb_val_to_py(v) for k, v in rec["dynamodb"].get("Keys", {}).items()},
        "new_image": new_obj if new_obj else None,
        "old_image": old_obj if old_obj else None,
        "sequence_number": rec["dynamodb"].get("SequenceNumber"),
        "size_bytes": rec["dynamodb"].get("SizeBytes"),
        "source_table": os.environ.get("TABLE_NAME", "chargeminder-car-telemetry")
    }
    return json.dumps(out, separators=(",", ":"), ensure_ascii=False)

def lambda_handler(event, context):
    # event["Records"] is a batch from a single shard
    lines = []
    for r in event.get("Records", []):
        # Kinesis-style records have base64; DynamoDB Streams already decoded body is in r["dynamodb"]
        if r.get("eventSource") != "aws:dynamodb":
            continue
        lines.append(_record_to_json_line(r))

    if not lines:
        return {"status": "empty"}

    # Partition by UTC date/hour of Lambda write time (ingest time partitioning)
    now = datetime.now(timezone.utc)
    dstr = now.strftime("%Y-%m-%d")
    hstr = now.strftime("%H")

    body_bytes = ("\n".join(lines)).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(body_bytes)
    gz_bytes = buf.getvalue()

    key = f"{S3_PREFIX}/ingest_dt={dstr}/hour={hstr}/part-{int(time.time()*1000)}-{uuid.uuid4().hex}.json.gz"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=gz_bytes,
        ContentEncoding="gzip",
        ContentType="application/json"
    )

    return {"status": "ok", "count": len(lines), "s3_key": key}
```

----------------------------------------------------------------------
LAMBDA ENV VARS
----------------------------------------------------------------------
TABLE_NAME=chargeminder-car-telemetry
S3_BUCKET=chargeminder-2
S3_PREFIX=raw/dynamodb/chargeminder-car-telemetry

----------------------------------------------------------------------
EVENT SOURCE MAPPING (CONNECT LAMBDA TO THE STREAM)
----------------------------------------------------------------------
```bash
# 1) Get the stream ARN (example CLI)
aws dynamodb describe-table \
  --table-name chargeminder-car-telemetry \
  --query "Table.LatestStreamArn" \
  --output text

# 2) Create mapping
aws lambda create-event-source-mapping \
  --function-name <YourLambdaName> \
  --event-source <LATEST_STREAM_ARN_FROM_ABOVE> \
  --starting-position LATEST \
  --batch-size 100 \
  --maximum-batching-window-in-seconds 1
```
### Notes:
 - Batch size up to 1000 is allowed; 100–500 is typical.  
 - maximum-batching-window-in-seconds (0–300) can trade latency vs. S3 object count.  

----------------------------------------------------------------------
RELIABILITY / OPERATIONS
----------------------------------------------------------------------
• Retries & DLQ:
  - Configure Lambda on-failure destination to SQS or use an SQS DLQ.
  - Set maximum retry attempts on the event source mapping (bisect on function error if needed).

• Idempotency:
  - Downstream is at-least-once. The Lambda writes new object names (timestamp + uuid) so S3 side is naturally idempotent for append-only raw.
  - Deduplicate later using a stable key (e.g., event_id or primary key + sequence_number) in Silver.

• Ordering:
  - Ordering is guaranteed per shard; not across shards. Auto Loader should not assume global order.

• Re-sharding:
  - Streams can re-shard; Lambda mapping handles this automatically.

----------------------------------------------------------------------
DATABRICKS: AUTO LOADER (BRONZE INGEST)
----------------------------------------------------------------------
-- Python in a Databricks notebook (Serverless or classic cluster)

```python
from pyspark.sql.functions import col, to_timestamp, from_unixtime

raw_path = "s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry"
checkpoint = "s3://chargeminder-2/_checkpoints/auto-loader/chargeminder-car-telemetry-bronze"

df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")
      .option("cloudFiles.inferColumnTypes", "true")
      .option("cloudFiles.includeExistingFiles", "true")
      .option("cloudFiles.validateOptions", "false")
      .load(raw_path))

# Optional: normalize time fields
# df = df.withColumn("approx_creation_time",
#                    to_timestamp(from_unixtime((col("approx_creation_time_ms")/1000).cast("double"))))

(df.writeStream
   .option("checkpointLocation", checkpoint)
   .option("mergeSchema", "true")
   .trigger(processingTime="1 minute")
   .format("delta")
   .outputMode("append")
   .toTable("hcai_databricks_dev.chargeminder2.bronze_car_telemetry_cdc"))
```
### Notes:
 - Ensure your workspace/cluster has access to the S3 bucket (instance profile / assumed role).  
 - If you prefer to keep it entirely path-based instead of Unity catalog table, use .start("s3://.../delta/bronze/...").

----------------------------------------------------------------------
TYPICAL SILVER TRANSFORM (DEDUP + LATEST IMAGE PER KEY)
----------------------------------------------------------------------
-- Example idea (Delta SQL), adjust keys/columns to your table
-- Deduplicate CDC events by (keys, sequence_number) and pick latest per key.
-- For MODIFY/INSERT, prefer new_image; for REMOVE, you can tombstone.

-- Pseudocode sketch:

```sql

CREATE OR REPLACE TABLE hcai_databricks_dev.chargeminder2.silver_car_telemetry AS
SELECT * FROM (
  SELECT
    COALESCE(new_image.pk, old_image.pk) AS pk,  -- replace with your primary key(s)
    event_name,
    event_id,
    sequence_number,
    approx_creation_time_ms,
    new_image,
    old_image,
    ROW_NUMBER() OVER (PARTITION BY COALESCE(new_image.pk, old_image.pk)
                       ORDER BY CAST(sequence_number AS BIGINT) DESC) AS rn
  FROM hcai_databricks_dev.chargeminder2.bronze_car_telemetry_cdc
)
WHERE rn = 1;
```
----------------------------------------------------------------------
VALIDATION / SMOKE TESTS
----------------------------------------------------------------------
• Put a test item into the table and confirm a new object arrives in:
  s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/ingest_dt=YYYY-MM-DD/hour=HH/

• In Databricks:  
  SELECT COUNT(*) FROM hcai_databricks_dev.chargeminder2.bronze_car_telemetry_cdc;

• CloudWatch Logs for Lambda should show batch counts and s3_key.

----------------------------------------------------------------------
KNOBS YOU CAN TUNE
----------------------------------------------------------------------
• Lambda batch-size: 100–500 strikes a balance between latency and S3 object overhead.
• Maximum batching window: 0–5s for “near real-time”; increase for fewer objects.
• Compression: gzip (default here). You can switch to snappy or write Parquet in Lambda if you want schema-on-write (requires pyarrow).
• Partitioning: ingest time (as shown) is robust; if you have a stable “event time” field, you can partition on that instead.

----------------------------------------------------------------------
ALTERNATIVES (WHEN THROUGHPUT OR SCHEMA EVOLUTION DEMANDS GROW)
----------------------------------------------------------------------
• Streams → Kinesis Data Streams → Kinesis Data Firehose → S3 (managed fan-out, buffering, Parquet conversion).
• DynamoDB TTL + Export to S3 (bulk, not streaming).
• Direct Databricks Autoloader on S3 (this design) vs. pushing into Kafka/MSK if you need multi-consumer fan-out.

----------------------------------------------------------------------
NEXT STEPS (SPECIFIC TO YOUR RESOURCES)
----------------------------------------------------------------------
1) Create/confirm the Lambda role using the JSON above (replace <ACCOUNT_ID>, <YourLambdaRoleName>).
2) Deploy the Lambda with app.py and set ENV:
   TABLE_NAME=chargeminder-car-telemetry
   S3_BUCKET=chargeminder-2
   S3_PREFIX=raw/dynamodb/chargeminder-car-telemetry
3) Create the event source mapping to the table’s LatestStreamArn (starting-position LATEST).
4) In Databricks, run the Auto Loader cell and confirm the Bronze table starts growing.

If you want, paste your current IAM role names/ARNs and I’ll tailor the policy documents exactly to your account and your Databricks access pattern (serverless vs. classic cluster).
 

## DynamoDB Streams → Lambda → S3 → Databricks Auto Loader → Unity Catalog
``` 
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
```
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
```
Two common file formats:

(A) **NDJSON.gz** (newline-delimited JSON, gzipped)
- Simple, schema-agnostic, great for rapid iteration.
- Auto Loader can infer schema; you can add evolution later.

(B) **Parquet** (snappy)
- Smaller + faster in Spark.
- Requires schema control; good once your schema stabilizes.

Below is **NDJSON.gz** variant with robust deserialization, batching, partitioning and minimal transform:
```
### File lambda_function.py
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
```
- S3_BUCKET=your-bucket
- S3_PREFIX=ddb/your_table
- MAX_RECORDS=2000
- MAX_PAYLOAD_BYTES=8000000
- MAX_SECONDS=15
```
Notes
```
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
```
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
```
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
```
Short answer: NO, you don’t have to use 2 Lambdas — one Lambda right off the DynamoDB Stream can write straight to S3 and that’s enough for Databricks Auto Loader.

But… sometimes people deliberately split it into 2. Here’s when.

──────────────────────────────────────────────────────────────────────────────
Pattern A (most common): 1 Lambda is enough
DynamoDB Stream → (event source mapping) → Lambda → S3 → Databricks

What Lambda does:
1. Read stream batch (INSERT/MODIFY/REMOVE)
2. Normalize/flatten to your target JSON shape
3. Buffer N records / M seconds
4. Write 1 object to S3 (ndjson.gz or parquet)
5. Done

Databricks then:
- Auto Loader reads S3
- foreachBatch MERGE into Unity
- Handles deletes based on `_eventName` or `is_deleted`

Use this if:
- Transform is light (rename fields, make sure pk/sk/updated_at exist)
- You don’t need to call other services per record
- You’re fine with the stream → S3 latency that this single Lambda gives

This is the design I described in the previous message.

──────────────────────────────────────────────────────────────────────────────
Pattern B (sometimes better): 2 Lambdas
1) DynamoDB Stream → Lambda #1 → S3 (raw-ish, minimal, lossless)
2) S3 (PutObject event) → Lambda #2 → S3 (curated) or → something else

Why do 2?
- You want Lambda #1 to be ultra-simple and **never fail** (just dump the stream to S3 as-is).
- You want a **separate place** to do heavier or more fragile logic (schema mapping, enrichment, calling APIs) so that stream consumption doesn’t get stuck.
- You want **raw immutable** S3 (landing) + **processed** S3 (curated) like a mini data lake:
  - s3://bucket/landing/ddb/...
  - s3://bucket/curated/ddb/...
- You want to **reprocess** older files without replaying the DynamoDB Stream (just re-trigger Lambda #2 on S3 objects).
- You need **different IAM** or **different timeout/memory** for the heavy part.

So:
- Lambda #1: tiny, fast, 128–256 MB, 3–5s timeout → “just write the file”
- Lambda #2: bigger, can run longer, can call other services, can produce Parquet / normalized schema

Databricks can then read either:
- directly from curated/ (Lambda #2 output), or
- directly from landing/ (if the raw format is already fine)

──────────────────────────────────────────────────────────────────────────────
Pattern C (no second Lambda, let Databricks do all transforms)
DynamoDB Stream → Lambda → S3 (raw) → Databricks (all transforms, MERGE)

This is also perfectly fine. In fact, if your Databricks job is already doing business transforms in PySpark, keeping Lambda thin is a good idea. That’s probably the best fit for you, since you already plan to “transform it using PySpark”.

──────────────────────────────────────────────────────────────────────────────
How to decide

Use 1 Lambda if:
- You control the stream schema
- You only need light normalization
- You trust Databricks to do all business logic
- You want fewer moving parts

Consider 2 Lambdas if:
- You want a guaranteed raw copy in S3
- You expect schema to change often and want to reprocess old files
- You need heavier logic than is comfortable in the stream Lambda
- You need to fan out (write to S3 + send to SNS, etc.)

──────────────────────────────────────────────────────────────────────────────
What I’d tell your team
“We can start with **one** Lambda (DDB Stream → S3). If later we see we need a stable raw zone or heavier transforms we can add a **second** Lambda that’s triggered by S3. Databricks stays the same.”

If you show me the exact DDB item shape (pk/sk or id + updated_at) I can give you the minimal single-Lambda code that lands exactly what Auto Loader wants.




You can absolutely **deploy with SAM without creating any new roles**. Two separate roles are involved—don’t mix them up:

1. **CloudFormation deploy role** (optional).
   • This is what the SAM CLI is asking about: a role **for CloudFormation** to assume while creating resources.
   • Trust policy must allow `cloudformation.amazonaws.com`.
   • If you say **No**, SAM will just use your current AWS credentials (from your profile) to deploy.

2. **Lambda execution role** (required for your function at runtime).
   • This is the role your Lambda *runs as*.
   • Trust policy must allow `lambda.amazonaws.com`.
   • This is the role you want to reuse: `chargeminder-lambda-processing-production`.

---

## A) Answering the prompt during `sam deploy --guided`

When prompted:

```
Allow SAM CLI IAM role creation [Y/n]:
```

choose **n**.

From there, you have two options:

* **No dedicated CloudFormation deploy role**: let SAM/CFN use your current profile credentials (requires your user/role to have permissions to create/update the stack and resources, including `CAPABILITY_IAM`/`CAPABILITY_NAMED_IAM` if your template manages IAM).
* **Provide your own CloudFormation deploy role** (if you’ve created one with `cloudformation.amazonaws.com` in its trust policy):

  ```
  sam deploy --guided --role-arn arn:aws:iam::<ACCOUNT_ID>:role/Your-CloudFormation-Deploy-Role
  ```

  (This role is different from your Lambda execution role.)

You’ll also need to acknowledge capabilities if your template touches IAM:

```
Capabilities: CAPABILITY_NAMED_IAM
```

If you want to make this persistent, set it in `samconfig.toml` (see example below).

---

## B) Reusing your existing **Lambda execution role** in the template

In `template.yaml`, point your function to the **existing role ARN** (and **remove** `Policies:` from that function, because when `Role` is set, SAM won’t attach inline policies):

```yaml
Resources:
  TelemetryStreamProcessor:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: TelemetryStreamProcessor
      Runtime: python3.12
      Architectures:
        - x86_64
      Handler: app.lambda_handler
      CodeUri: src/
      Role: arn:aws:iam::<ACCOUNT_ID>:role/chargeminder-lambda-processing-production
      # DO NOT include "Policies:" here since you're supplying Role directly
      Timeout: 30
      MemorySize: 512
```

> Your role file `chargeminder-lambda-dynamodb-s3-prod-role.yaml` looks like a **Lambda execution role** (it includes `AWSLambdaBasicExecutionRole`). Keep using that as the `Role` above.

---

## C) Optional: provide a **CloudFormation deploy role** (if org requires it)

Only if your org mandates CFN to assume a deploy role, create one with this **trust** (note: *not* the Lambda trust):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "cloudformation.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Attach permissions so CFN can create/update all resources in your stack (IAM, Lambda, S3, Logs, etc.). Then deploy with:

```bash
sam deploy --guided \
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/Your-CloudFormation-Deploy-Role \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## D) Example `samconfig.toml` (so you don’t have to retype)

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "chargeminder-lambda-processing"
region = "us-east-1"
s3_bucket = "your-sam-artifacts-bucket"      # or let SAM create one the first time
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true
resolve_s3 = true
# If you have a CFN deploy role, uncomment:
# role_arn = "arn:aws:iam::<ACCOUNT_ID>:role/Your-CloudFormation-Deploy-Role"
```

Run:

```bash
sam deploy
```

---

## E) Quick role sanity checks

* **Lambda execution role** (your existing role):

  * Trust: `lambda.amazonaws.com`
  * Policies: `AWSLambdaBasicExecutionRole` + your DynamoDB/S3 permissions

* **CloudFormation deploy role** (only if you choose to use one):

  * Trust: `cloudformation.amazonaws.com`
  * Policies: permissions to create/update/delete the resources in your template

---

### TL;DR

* When `sam deploy --guided` asks “Allow SAM CLI IAM role creation?”, answer **No**.
* Keep using your **existing Lambda execution role** by setting `Properties.Role` with its ARN in `template.yaml`.
* Only supply `--role-arn` (a **CloudFormation** deploy role) if your org requires CFN to assume a specific role; otherwise your current AWS profile is fine.


