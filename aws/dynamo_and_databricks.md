## Read  DynamoDB table *into* your Databricks notebook 


## 1) Easiest + scalable: **Export DynamoDB → S3**, then read with Spark

**Why:** It’s serverless, doesn’t consume RCUs, and you can do **full** or **incremental** exports (PITR window). Data lands in S3 as **DynamoDB JSON** or **Amazon Ion** files; Databricks can read them directly. ([AWS Documentation][1])

**Steps (one-time / per-run):**

1. In the DynamoDB console: *Exports to S3* → choose **Full** (or **Incremental**) export, pick S3 bucket/prefix, format **DynamoDB JSON** (simplest), and run. (PITR must be enabled.) ([AWS Documentation][2])
2. In Databricks, read the S3 prefix that contains `data/` files (ignore the `manifest-files.json`):

```python
# Spark (PySpark) on Databricks
s3_path = "s3://your-bucket/prefix/<export-id>/data/"  # or .../incremental/data/
df_raw = spark.read.json(s3_path)  # reads DynamoDB JSON (typed)
df_raw.printSchema()
df_raw.show(3, truncate=False)
```

DynamoDB JSON is *typed* (e.g., `{"attr":{"S":"value"}}`). A quick normalizer to unwrap common types:

```python
from pyspark.sql import functions as F

def unwrap(col):
    # unwrap common DynamoDB JSON types; add others (BOOL, L, M, NULL, BS, NS) as needed
    return F.coalesce(col.getField("S"), col.getField("N"), col.getField("B"))

# Example: suppose items have keys "id", "updated_at", "payload"
df = df_raw.select(
    unwrap(F.col("id")).alias("id"),
    unwrap(F.col("updated_at")).cast("timestamp").alias("updated_at"),
    F.col("payload")  # if this is a map (M), handle similarly by drilling into fields
)
df.display()
```

**Pros:** No load on the live table; supports incremental refreshes you can schedule. **Cons:** Export is asynchronous; format is typed JSON/Ion you may need to unwrap. ([AWS Documentation][1])

---

## 2) Quick, small/medium tables: **AWS SDK for pandas (awswrangler)** inside Databricks

Great when you want to **scan/query now** without setting up an export. Use `wr.dynamodb.read_items` (scan) or `wr.dynamodb.read_partiql_query` (filter). Returns a pandas DataFrame; convert to Spark if needed. ([aws-sdk-pandas.readthedocs.io][3])

```python
# %pip install awswrangler
import awswrangler as wr
import boto3

session = boto3.Session(region_name="us-east-1")  # set your region

# 2a) Full read (scan) -- careful on big tables
pdf = wr.dynamodb.read_items(
    table_name="your_table",
    boto3_session=session,
)

# 2b) Filter with PartiQL (server-side)
pdf = wr.dynamodb.read_partiql_query(
    query="SELECT * FROM your_table WHERE updated_at >= ?",
    parameters=["2025-09-01T00:00:00Z"],
    boto3_session=session,
)

# Convert to Spark if you prefer Spark APIs
df = spark.createDataFrame(pdf)
df.display()
```

**Pros:** Minimal setup, flexible queries. **Cons:** Scans can be slow/pricey at scale; mind RCUs; better for small/medium pulls or targeted PartiQL. ([aws-sdk-pandas.readthedocs.io][3])

---

## 3) Advanced: **Spark ↔ DynamoDB connector (EMR DynamoDB Connector)**

You can wire the EMR DynamoDB Hadoop/Spark connector jars to Databricks and use the `DynamoDBInputFormat`. This is powerful but more involved (jars, configs, IAM, throttling). If you manage heavy reads/writes frequently, consider running this on EMR; on Databricks it’s doable but fiddly. ([GitHub][4])

**Sketch (Scala/Python pyspark style):**

```python
# After attaching the EMR DynamoDB connector JARs to the cluster:
conf = {
  "dynamodb.input.tableName": "your_table",
  "dynamodb.region": "us-east-1",
  "dynamodb.throughput.read.percent": "0.25",  # throttle to 25% RCUs
}

rdd = sc.newAPIHadoopRDD(
    "org.apache.hadoop.dynamodb.read.DynamoDBInputFormat",
    "org.apache.hadoop.io.Text",
    "org.apache.hadoop.io.MapWritable",
    conf
)

# Convert to DataFrame (you'll need a mapper to flatten MapWritable)
```

**Pros:** Parallel Spark reads direct from DynamoDB. **Cons:** Setup complexity; need to manage RCUs/backoff; less “plug-and-play” on Databricks. ([GitHub][4])

---

## 4) Very small tables / ad-hoc: **boto3 scan** then parallelize

Fine for a few thousand items; not recommended at scale.

```python
import boto3
from itertools import islice

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("your_table")

items = []
resp = table.scan()
items.extend(resp.get("Items", []))
while "LastEvaluatedKey" in resp:
    resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
    items.extend(resp.get("Items", []))

df = spark.createDataFrame(items)
df.count(), df.display()
```

---

## Credentials / IAM notes (Databricks on AWS)

* Prefer attaching an **instance profile**/IAM role to the cluster so Spark & libraries can talk to S3 and DynamoDB without embedding keys.
* For S3 reads (Option 1), make sure the cluster has `s3:GetObject` on the export bucket/prefix.
* For exports (Option 1), the exporting principal needs `dynamodb:ExportTableToPointInTime` and S3 `PutObject` on the target bucket. PITR must be enabled to export. ([AWS Documentation][2])

---

## Which should you pick?

* **Batch analytics** (your case sounds like this): **Export→S3** then read with Spark. Use **incremental export** on a schedule (e.g., every 5–15 min) to keep Databricks up to date without hammering DynamoDB. ([Amazon Web Services, Inc.][5])
* **Small/targeted pulls**: `awswrangler` with PartiQL. ([aws-sdk-pandas.readthedocs.io][6])
* **Heavy direct access**: EMR connector (or just run on EMR Serverless). ([AWS Documentation][7])

If you want, I can give you a ready-to-run Databricks notebook that:

1. starts an **incremental export** (CLI/API),
2. reads the **new files** from S3, normalizes the DynamoDB JSON, and
3. merges into a Delta table.

[1]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.HowItWorks.html?utm_source=chatgpt.com "DynamoDB data export to Amazon S3: how it works"
[2]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport_Requesting.html?utm_source=chatgpt.com "Requesting a table export in DynamoDB - AWS Documentation"
[3]: https://aws-sdk-pandas.readthedocs.io/en/3.10.1/stubs/awswrangler.dynamodb.read_items.html?utm_source=chatgpt.com "awswrangler.dynamodb.read_items - AWS SDK for pandas"
[4]: https://github.com/awslabs/emr-dynamodb-connector?utm_source=chatgpt.com "awslabs/emr-dynamodb-connector"
[5]: https://www.amazonaws.cn/en/blog-selection/introducing-incremental-export-from-amazon-dynamodb-to-amazon-s3/?nc1=h_ls&utm_source=chatgpt.com "Introducing incremental export from Amazon DynamoDB to Amazon ..."
[6]: https://aws-sdk-pandas.readthedocs.io/en/3.10.0/stubs/awswrangler.dynamodb.read_partiql_query.html?utm_source=chatgpt.com "awswrangler.dynamodb.read_partiql_query"
[7]: https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-ddb-connector.html?utm_source=chatgpt.com "Connecting to DynamoDB with Amazon EMR Serverless"


Here's how to periodically read a DynamoDB table from a Databricks notebook:

## Setup and Configuration

First, you'll need to configure AWS credentials and install necessary libraries:

```python
# Install AWS SDK
%pip install boto3

# Configure AWS credentials (use Databricks secrets for production)
import boto3
from pyspark.sql import SparkSession

# Option 1: Using Databricks secrets (recommended)
aws_access_key = dbutils.secrets.get(scope="aws", key="access_key_id")
aws_secret_key = dbutils.secrets.get(scope="aws", key="secret_access_key")

# Option 2: Direct configuration (not recommended for production)
# aws_access_key = "your_access_key"
# aws_secret_key = "your_secret_key"

dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)
```

## Reading DynamoDB Data

Here are several approaches depending on your needs:

### 1. **Simple Periodic Read with Boto3**

```python
from datetime import datetime
import time

def read_dynamodb_table(table_name):
    """Read entire DynamoDB table and convert to Spark DataFrame"""
    table = dynamodb.Table(table_name)
    
    # Scan the table (use query if you have specific keys)
    response = table.scan()
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    # Convert to Spark DataFrame
    if items:
        df = spark.createDataFrame(items)
        return df
    return None

# Read once
df = read_dynamodb_table('your_table_name')
if df:
    display(df)
```

### 2. **Using Spark with DynamoDB Connector**

```python
# Configure Spark to read from DynamoDB
df = spark.read \
    .format("dynamodb") \
    .option("tableName", "your_table_name") \
    .option("region", "us-east-1") \
    .option("awsAccessKeyId", aws_access_key) \
    .option("awsSecretAccessKey", aws_secret_key) \
    .load()

display(df)
```

### 3. **Periodic Reading with Databricks Jobs**

For truly periodic execution, create a scheduled job:

```python
# Save this as your notebook code
from datetime import datetime

def process_dynamodb_data():
    """Main function to read and process DynamoDB data"""
    
    print(f"Reading DynamoDB at {datetime.now()}")
    
    # Read data
    df = read_dynamodb_table('your_table_name')
    
    if df and df.count() > 0:
        # Process your data
        # Example: Write to Delta Lake
        df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("/mnt/delta/dynamodb_data")
        
        print(f"Processed {df.count()} records")
    else:
        print("No data found")

# Execute
process_dynamodb_data()
```

Then schedule this notebook:
- Go to **Workflows** → **Create Job**
- Add your notebook as a task
- Set schedule (e.g., every 5 minutes, hourly, etc.)

### 4. **Incremental Read with Timestamp Tracking**

If your DynamoDB table has a timestamp field:

```python
from pyspark.sql.functions import col, max as spark_max

def read_dynamodb_incremental(table_name, last_timestamp=None):
    """Read only new records since last timestamp"""
    table = dynamodb.Table(table_name)
    
    if last_timestamp:
        # Query with filter (requires GSI on timestamp)
        response = table.scan(
            FilterExpression='#ts > :last_ts',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={':last_ts': last_timestamp}
        )
    else:
        response = table.scan()
    
    items = response['Items']
    
    while 'LastEvaluatedKey' in response:
        if last_timestamp:
            response = table.scan(
                FilterExpression='#ts > :last_ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={':last_ts': last_timestamp},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
        else:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    return spark.createDataFrame(items) if items else None

# Track last processed timestamp
last_ts = None
try:
    last_ts = spark.read.format("delta").load("/mnt/delta/dynamodb_data") \
        .agg(spark_max("timestamp")).collect()[0][0]
except:
    pass

df = read_dynamodb_incremental('your_table_name', last_ts)
```

### 5. **Using Databricks Auto Loader with S3 Export**

For large tables, use DynamoDB's S3 export feature:

```python
# After setting up DynamoDB to S3 export pipeline
df = spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.schemaLocation", "/mnt/schema/dynamodb") \
    .load("s3://your-bucket/dynamodb-exports/")

# Write to Delta
df.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/mnt/checkpoints/dynamodb") \
    .start("/mnt/delta/dynamodb_data")
```

## Best Practices

1. **Use Databricks Secrets** for credentials
2. **Implement error handling** for network issues
3. **Monitor DynamoDB read capacity** to avoid throttling
4. **Use filtering** when possible to reduce data transfer
5. **Consider DynamoDB Streams** if real-time processing is needed
6. **Store processed data in Delta Lake** for better query performance

## Recommended Approach

For periodic external updates, I recommend:
- **Short intervals (< 1 hour)**: Use Databricks Jobs with scheduled notebook runs
- **Long intervals or large data**: Use DynamoDB S3 export + Auto Loader
- **Near real-time**: Set up DynamoDB Streams → Kinesis → Databricks

 Below is a **ready-to-run Databricks notebook** you can paste into a new notebook. It:

1. **Starts a DynamoDB incremental export → S3** (via `boto3` using the `ExportTableToPointInTime` API with `ExportType="INCREMENTAL_EXPORT"` and `IncrementalExportSpecification`),
2. **Polls** until the export completes,
3. **Reads only the new export files** from S3, **normalizes DynamoDB JSON** (`S`, `N`, `BOOL`, `M`, `L`, etc.) into plain JSON, and
4. **MERGEs into a Delta table** (upsert on your DynamoDB key(s); deletes are applied when the export indicates a delete).

References for the incremental export API and the S3 layout/JSON structure: ([AWS Documentation][1])

---

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # DynamoDB → S3 (Incremental Export) → Databricks Delta
# MAGIC
# MAGIC This notebook:
# MAGIC 1. Starts an **incremental export** from **Amazon DynamoDB** to **Amazon S3**.
# MAGIC 2. Waits for the export to finish.
# MAGIC 3. Reads the new JSON Lines (gz) files from S3 (DynamoDB JSON format), normalizes them.
# MAGIC 4. MERGE (upsert & delete) into a Delta table.
# MAGIC
# MAGIC **Requirements**
# MAGIC * PITR enabled on the DynamoDB table.
# MAGIC * Databricks cluster has an **instance profile / IAM role** with permissions to call DynamoDB Export APIs and read S3 paths.
# MAGIC * Bucket policy allows read/write by DynamoDB export and read by your Databricks role.
# MAGIC
# MAGIC **Docs**:
# MAGIC * Incremental export API & fields (ExportType, IncrementalExportSpecification, ExportViewType): see AWS API docs. :contentReference[oaicite:1]{index=1}
# MAGIC * S3 output layout, manifest files, incremental `/data/` folder, and record structure (`Keys`, `NewImage`, `OldImage`, `Metadata.WriteTimestampMicros`): see Developer Guide. :contentReference[oaicite:2]{index=2}
```

```python
# Databricks notebook source
# MAGIC %python
# --- Install/Import ---
# If your cluster image doesn't include boto3:
# %pip install boto3

import os, time, json, datetime
import boto3
from botocore.config import Config
from pyspark.sql import functions as F, types as T

# ---------- CONFIGURE ME ----------
AWS_REGION            = "us-east-1"
TABLE_ARN             = "arn:aws:dynamodb:us-east-1:123456789012:table/your-table"
S3_BUCKET             = "your-export-bucket"
S3_PREFIX             = "dynamodb/exports/mytable"   # no leading slash
EXPORT_FORMAT         = "DYNAMODB_JSON"              # or "ION"
EXPORT_VIEW_TYPE      = "NEW_AND_OLD_IMAGES"         # or "NEW_IMAGES"
# Incremental window (UTC). Typically last successful watermark to now.
# For first run, set EXPORT_FROM_UTC_ISO to the time of your last full export, or some historical time.
EXPORT_FROM_UTC_ISO   = dbutils.widgets.get("export_from_utc_iso") if "export_from_utc_iso" in [w.name for w in dbutils.widgets.get()] else "2025-09-01T00:00:00Z"
EXPORT_TO_UTC_ISO     = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# Target Delta table & keys for merge
DELTA_DATABASE        = "raw"                         # or your schema
DELTA_TABLE           = "ddb_mytable"
DELTA_PATH            = f"/mnt/delta/{DELTA_DATABASE}/{DELTA_TABLE}"  # or use catalog path
PRIMARY_KEYS          = ["PK", "SK"]                  # set to your DynamoDB keys (after normalization)
APPLY_DELETES         = True                          # delete target rows if item is a delete in export

# Optional: throttle read/load (not export) and export poll
EXPORT_POLL_SECONDS   = 20
EXPORT_POLL_TIMEOUT_S = 60 * 30   # 30 min
```

```python
# Databricks notebook source
# MAGIC %python
# --- Helper: parse ISO 8601 to epoch seconds ---
from dateutil import parser as _parser
def _iso_to_epoch_s(iso: str) -> int:
    return int(_parser.isoparse(iso).timestamp())

EXPORT_FROM_EPOCH = _iso_to_epoch_s(EXPORT_FROM_UTC_ISO)
EXPORT_TO_EPOCH   = _iso_to_epoch_s(EXPORT_TO_UTC_ISO)

print(f"Incremental window UTC: {EXPORT_FROM_UTC_ISO} .. {EXPORT_TO_UTC_ISO}")
```

```python
# Databricks notebook source
# MAGIC %python
# --- Start incremental export ---
cfg = Config(region_name=AWS_REGION, retries={"max_attempts": 10, "mode": "standard"})
ddb = boto3.client("dynamodb", config=cfg)

export_req = {
    "TableArn": TABLE_ARN,
    "S3Bucket": S3_BUCKET,
    "S3Prefix": S3_PREFIX,
    "ExportFormat": EXPORT_FORMAT,                           # DYNAMODB_JSON | ION
    "ExportType": "INCREMENTAL_EXPORT",                      # <-- key bit
    "IncrementalExportSpecification": {
        "ExportFromTime": EXPORT_FROM_EPOCH,                 # epoch seconds
        "ExportToTime":   EXPORT_TO_EPOCH,                   # epoch seconds
        "ExportViewType": EXPORT_VIEW_TYPE                   # NEW_AND_OLD_IMAGES | NEW_IMAGES
    }
}

resp = ddb.export_table_to_point_in_time(**export_req)
export_arn = resp["ExportDescription"]["ExportArn"]
print("Started export:", export_arn)
# API & fields shown in docs. :contentReference[oaicite:3]{index=3}
```

```python
# Databricks notebook source
# MAGIC %python
# --- Poll for export completion ---
start = time.time()
status = "IN_PROGRESS"
while status in ("IN_PROGRESS",) and (time.time() - start) < EXPORT_POLL_TIMEOUT_S:
    time.sleep(EXPORT_POLL_SECONDS)
    d = ddb.describe_export(ExportArn=export_arn)  # :contentReference[oaicite:4]{index=4}
    ed = d["ExportDescription"]
    status = ed["ExportStatus"]
    billed = ed.get("BilledSizeBytes")
    icount = ed.get("ItemCount")
    print(f"[{datetime.datetime.utcnow().isoformat()}Z] {status} billed={billed} bytes items={icount}")

if status != "COMPLETED":
    raise RuntimeError(f"Export did not complete in time. Last status: {status}")
    
manifest_prefix = f"s3://{ed['S3Bucket']}/{ed['S3Prefix']}/AWSDynamoDB/{ed['ExportArn'].split('/')[-1]}"
print("Manifest prefix:", manifest_prefix)
# Note: incremental exports store *data files* under a shared S3 .../AWSDynamoDB/data/ folder. :contentReference[oaicite:5]{index=5}
```

```python
# Databricks notebook source
# MAGIC %python
# --- Resolve the data files produced by this export ---
# We read the manifest-files.json to get the S3 keys for this export's files.
manifest_files_path = f"{manifest_prefix}/manifest-files.json"
mf = spark.read.text(manifest_files_path)  # jsonlines
files = (spark.read.json(mf.rdd.map(lambda r: r.value))
         .select("dataFileS3Key")
         .withColumn("s3_uri", F.concat(F.lit(f"s3://{S3_BUCKET}/"), F.col("dataFileS3Key")))
)
display(files.limit(10))
```

```python
# Databricks notebook source
# MAGIC %python
# --- Read the data files (JSON Lines, gz) and produce a raw DataFrame ---
# Each line is a JSON object. For incremental exports with NEW_AND_OLD_IMAGES,
# records follow { Metadata, Keys, NewImage?, OldImage? }, with typed DynamoDB JSON. :contentReference[oaicite:6]{index=6}

paths = [r["s3_uri"] for r in files.collect()]
if not paths:
    print("No data files found for this export window (possible if no changes occurred).")
raw_df = spark.read.json(paths)
raw_df.printSchema()
display(raw_df.limit(3))
```

```python
# Databricks notebook source
# MAGIC %python
# --- Utilities: unmarshal DynamoDB JSON recursively into plain types ---
# Handles scalar types S,N,BOOL,NULL,B and set types SS,NS,BS; also M (map) and L (list).
# You can extend for Binary (B/BS) to convert byte buffers as needed.

@F.udf(returnType=T.StringType())
def _dyn_to_json_str(obj):
    import json
    def _unwrap(x):
        if x is None:
            return None
        if isinstance(x, dict):
            # DynamoDB JSON object has single top-level key for scalars/sets, or 'M'/'L'
            if "S" in x:   return x["S"]
            if "N" in x:   return float(x["N"]) if "." in x["N"] else int(x["N"])
            if "BOOL" in x:return bool(x["BOOL"])
            if "NULL" in x:return None
            if "B" in x:   return x["B"]  # base64 str; customize if needed
            if "SS" in x:  return list(x["SS"])
            if "NS" in x:  return [float(v) if "." in v else int(v) for v in x["NS"]]
            if "BS" in x:  return list(x["BS"])
            if "M" in x:   return {k: _unwrap(v) for k, v in x["M"].items()}
            if "L" in x:   return [_unwrap(v) for v in x["L"]]
            # If already plain dict, unwrap each value
            return {k: _unwrap(v) for k, v in x.items()}
        if isinstance(x, list):
            return [_unwrap(v) for v in x]
        return x

    return json.dumps(_unwrap(obj), separators=(",",":"))

# Helper to project a struct<... DDB JSON ...> into a proper Spark struct via from_json
def unwrap_struct(col, schema_json=None):
    # Convert DynamoDB JSON to normalized JSON string, then parse to struct if schema provided
    s = _dyn_to_json_str(col)
    if schema_json:
        return F.from_json(s, T.StructType.fromJson(json.loads(schema_json)))
    else:
        return F.from_json(s, T.MapType(T.StringType(), T.StringType()))  # generic map if no schema
```

```python
# Databricks notebook source
# MAGIC %python
# --- Build a typed, normalized DataFrame with operation semantics ---
# We expose:
#   write_ts_us: long
#   op: 'INSERT' | 'UPDATE' | 'DELETE'
#   keys: struct<...>
#   new_image: struct<...> (nullable)
#   old_image: struct<...> (nullable)

norm_df = (
    raw_df
    .withColumn("write_ts_us", F.col("Metadata.WriteTimestampMicros").cast("long"))
    .withColumn("keys_json",      _dyn_to_json_str(F.col("Keys")))
    .withColumn("new_image_json", _dyn_to_json_str(F.col("NewImage")))
    .withColumn("old_image_json", _dyn_to_json_str(F.col("OldImage")))
)

# Infer operation type from presence of NewImage / OldImage per AWS docs. :contentReference[oaicite:7]{index=7}
norm_df = (
    norm_df
    .withColumn(
        "op",
        F.when(F.col("NewImage").isNotNull() & F.col("OldImage").isNotNull(), F.lit("UPDATE"))
         .when(F.col("NewImage").isNotNull() & F.col("OldImage").isNull(),    F.lit("INSERT"))
         .when(F.col("NewImage").isNull()    & F.col("OldImage").isNotNull(), F.lit("DELETE"))
         .otherwise(F.lit("UNKNOWN"))
    )
)

display(norm_df.select("write_ts_us","op","keys_json","new_image_json","old_image_json").limit(10))
```

```python
# Databricks notebook source
# MAGIC %python
# --- Parse keys & images into columns (as generic maps) ---
keys_col      = F.from_json(F.col("keys_json"),      T.MapType(T.StringType(), T.StringType()))
new_image_col = F.from_json(F.col("new_image_json"), T.MapType(T.StringType(), T.StringType()))
old_image_col = F.from_json(F.col("old_image_json"), T.MapType(T.StringType(), T.StringType()))

proj = (norm_df
        .select(
            "write_ts_us","op",
            keys_col.alias("keys"),
            new_image_col.alias("new_image"),
            old_image_col.alias("old_image")
        ))

display(proj.limit(5))
```

```python
# Databricks notebook source
# MAGIC %python
# --- (Optional) Promote known columns from new_image into top-level columns ---
# If you know your schema, list the fields you want to cast to specific types.
KNOWN_COLS = {
    # "SomeNumericAttr": "double",
    # "UpdatedAt": "timestamp",
}

def promote_columns(df, img_col="new_image"):
    cols = [c for c in df.columns if c not in ("new_image","old_image")]
    for name, spark_type in KNOWN_COLS.items():
        cols.append(F.col(f"{img_col}").getItem(name).cast(spark_type).alias(name))
    return df.select(*cols, F.col(img_col), F.col("old_image"))

proj2 = promote_columns(proj, "new_image")
display(proj2.limit(5))
```

```python
# Databricks notebook source
# MAGIC %python
# --- Prepare a DataFrame for MERGE ---
# We require PRIMARY_KEYS list to exist in both 'keys' and 'new_image' (for upsert).
# For DELETE ops, we only need keys.

def extract_key_cols(df, keys_map_col="keys"):
    out = df
    for k in PRIMARY_KEYS:
        out = out.withColumn(k, F.col(keys_map_col).getItem(k).cast("string"))
    return out

staged = extract_key_cols(proj2, "keys")

# For upserts, build a struct of all columns from new_image (kept as a map here).
# Optionally, expand/flatten if you know schema.
staged = staged.withColumn("payload", F.col("new_image")) \
               .withColumn("updated_at_ts", (F.col("write_ts_us")/1_000_000.0).cast("timestamp"))

display(staged.select(PRIMARY_KEYS + ["op","updated_at_ts","payload"]).limit(10))
```

```python
# Databricks notebook source
# MAGIC %python
# --- Create the Delta table if not exists ---
spark.sql(f"CREATE DATABASE IF NOT EXISTS {DELTA_DATABASE}")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {DELTA_DATABASE}.{DELTA_TABLE} 
(
  {', '.join([f'{k} STRING' for k in PRIMARY_KEYS])},
  updated_at_ts TIMESTAMP,
  payload MAP<STRING,STRING>
)
USING delta
LOCATION '{DELTA_PATH}'
""")
```

```python
# Databricks notebook source
# MAGIC %python
# --- MERGE logic ---
target = f"{DELTA_DATABASE}.{DELTA_TABLE}"

# Register staged changes as temp view
staged.createOrReplaceTempView("staged_changes")

merge_on = " AND ".join([f"t.{k} = s.{k}" for k in PRIMARY_KEYS])

if APPLY_DELETES:
    merge_sql = f"""
    MERGE INTO {target} t
    USING staged_changes s
    ON {merge_on}
    WHEN MATCHED AND s.op = 'DELETE' THEN DELETE
    WHEN MATCHED AND s.op IN ('UPDATE','INSERT') THEN
      UPDATE SET
        {', '.join([f"t.{k} = s.{k}" for k in PRIMARY_KEYS])},
        t.updated_at_ts = s.updated_at_ts,
        t.payload       = s.payload
    WHEN NOT MATCHED AND s.op IN ('UPDATE','INSERT') THEN
      INSERT ({', '.join(PRIMARY_KEYS)}, updated_at_ts, payload)
      VALUES ({', '.join([f's.{k}' for k in PRIMARY_KEYS])}, s.updated_at_ts, s.payload)
    """
else:
    merge_sql = f"""
    MERGE INTO {target} t
    USING staged_changes s
    ON {merge_on}
    WHEN MATCHED THEN
      UPDATE SET
        {', '.join([f"t.{k} = s.{k}" for k in PRIMARY_KEYS])},
        t.updated_at_ts = s.updated_at_ts,
        t.payload       = s.payload
    WHEN NOT MATCHED THEN
      INSERT ({', '.join(PRIMARY_KEYS)}, updated_at_ts, payload)
      VALUES ({', '.join([f's.{k}' for k in PRIMARY_KEYS])}, s.updated_at_ts, s.payload)
    """

print(merge_sql)
spark.sql(merge_sql)
```

```python
# Databricks notebook source
# MAGIC %python
# --- Verify ---
df_target = spark.table(f"{DELTA_DATABASE}.{DELTA_TABLE}")
print("Target count:", df_target.count())
display(df_target.orderBy(F.col("updated_at_ts").desc()).limit(20))
```

```python
# Databricks notebook source
# MAGIC %md
# MAGIC ## Notes & Tips
# MAGIC * **Incremental export** requires PITR; you specify `ExportType="INCREMENTAL_EXPORT"` and the `IncrementalExportSpecification` (from/to and view type). :contentReference[oaicite:8]{index=8}
# MAGIC * **S3 layout**: each export has its own `AWSDynamoDB/<ExportId>/manifest-*.json`, while **incremental data files** are placed under a shared `AWSDynamoDB/data/` folder; we use `manifest-files.json` to get the file list. :contentReference[oaicite:9]{index=9}
# MAGIC * **Record structure** for incremental exports includes `Metadata.WriteTimestampMicros`, `Keys`, plus `NewImage` and/or `OldImage` depending on operation and `ExportViewType`. We infer `"INSERT" | "UPDATE" | "DELETE"` from presence of those images. :contentReference[oaicite:10]{index=10}
# MAGIC * The **DynamoDB JSON** typing (`S`, `N`, `BOOL`, `M`, `L`, sets) is normalized by a small recursive converter; customize for Binary/sets and strong typing as needed. :contentReference[oaicite:11]{index=11}
# MAGIC * For production: persist a **watermark** (the `ExportToTime` or the max `write_ts_us`) to drive the next run's `ExportFromTime`, add error handling & idempotency (use `ClientToken`), and schedule in a job.
```

---

### What you’ll likely customize

* `TABLE_ARN`, `S3_BUCKET`, `S3_PREFIX`, `AWS_REGION`
* `PRIMARY_KEYS` (e.g., `["PK","SK"]` or `["id"]`)
* The normalization step (map → typed columns) in the “Promote known columns” cell
* Where you store the Delta table (`DELTA_DATABASE`, `DELTA_PATH`)
* A persisted **watermark** (e.g., a small Delta table with the last successful `EXPORT_TO_UTC_ISO`)

If you want this turned into a **Databricks job** with a persisted watermark and retries, say the word and I’ll add that variant.

[1]: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_ExportTableToPointInTime.html "ExportTableToPointInTime - Amazon DynamoDB"

