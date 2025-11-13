## Claude **Backfilling Historical DynamoDB Data**

https://github.com/Michael-Lubinsky/michael-lubinsky.github.com/blob/0089444a861c931fefbbe287a67065465274ebd5/aws/dynamodb_dump_reading.md

## **Option 1: DynamoDB Export to S3 (Recommended)**

AWS has a **native export feature** that's the most efficient way to get historical data.

### **A. Export DynamoDB Table to S3**

```bash
# Using AWS CLI
aws dynamodb export-table-to-point-in-time \
    --table-arn arn:aws:dynamodb:us-east-1:123456789012:table/YourTable \
    --s3-bucket your-bucket-name \
    --s3-prefix dynamodb-exports/historical/ \
    --export-format DYNAMODB_JSON  # or ION
```

**Or via AWS Console:**
1. Go to DynamoDB → Tables → Your Table
2. Click "Exports and streams" → "Export to S3"
3. Choose S3 bucket and prefix
4. Select format: `DYNAMODB_JSON` or `ION`

### **B. Transform Export Format to Match Streaming Format**

The export format differs from DynamoDB Stream records. You need to transform it:

```python
# Databricks job to process DynamoDB export
from pyspark.sql.functions import *
from pyspark.sql.types import *

def process_dynamodb_export():
    """
    Process DynamoDB export files (DYNAMODB_JSON format)
    Transform to match the format your streaming Lambda produces
    """
    
    # Read the export (these are in data/ subfolder of your export)
    export_path = "s3://your-bucket/dynamodb-exports/historical/*/data/*.json.gz"
    
    raw_export = spark.read.json(export_path)
    
    # DynamoDB export format looks like:
    # {"Item": {"id": {"S": "123"}, "name": {"S": "John"}, "age": {"N": "30"}}}
    
    # Transform DynamoDB JSON format to regular JSON
    transformed_df = raw_export.select(
        col("Item").alias("dynamodb_item")
    )
    
    # Parse DynamoDB typed format to regular values
    # You'll need to flatten the DynamoDB type descriptors (S, N, BOOL, etc.)
    
    return transformed_df

# Example of flattening DynamoDB types
def flatten_dynamodb_item(item_col):
    """
    Flatten DynamoDB Item format:
    {"id": {"S": "123"}} -> {"id": "123"}
    """
    return select_expr(
        "transform(map_keys(Item), k -> k) as field_names",
        """transform(map_values(Item), v -> 
            CASE 
                WHEN v.S IS NOT NULL THEN v.S
                WHEN v.N IS NOT NULL THEN CAST(v.N AS DOUBLE)
                WHEN v.BOOL IS NOT NULL THEN v.BOOL
                WHEN v.NULL IS NOT NULL THEN NULL
                -- Add more types as needed: L (list), M (map), SS, NS, BS
            END
        ) as field_values"""
    )
```

### **C. Better Approach: Transform Export to Match Lambda Output**

Write a **one-time transformation job** that converts export to your streaming format:

```python
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Read DynamoDB export
export_df = spark.read.json("s3://your-bucket/dynamodb-exports/historical/*/data/*.json.gz")

# Transform to match your Lambda's streaming output format
def transform_dynamodb_export_to_stream_format(df):
    """
    Convert DynamoDB export format to match Lambda streaming output
    """
    
    # If your Lambda outputs NewImage format (like DynamoDB Streams)
    transformed = df.select(
        lit("INSERT").alias("eventName"),  # Mark as INSERT for historical data
        current_timestamp().alias("approximateCreationDateTime"),
        struct(
            col("Item").alias("NewImage")
        ).alias("dynamodb")
    )
    
    return transformed

# Transform and write to your regular S3 location
stream_format_df = transform_dynamodb_export_to_stream_format(export_df)

# Write to same S3 location that your streaming Lambda uses
# Use a separate prefix to distinguish backfill from streaming
stream_format_df.write \
    .mode("overwrite") \
    .json("s3://your-bucket/dynamodb-stream-output/backfill/")

# Now your existing Databricks job can process this!
```

---

## **Option 2: Scan DynamoDB with Backfill Script**

Write a **one-time backfill script** that mimics your Lambda function:

### **A. Python Script (AWS Lambda or EC2)**

```python
import boto3
import json
from datetime import datetime
import os

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = 'YourTableName'
BUCKET_NAME = 'your-bucket-name'
S3_PREFIX = 'dynamodb-stream-output/backfill/'

def scan_and_upload_to_s3():
    """
    Scan entire DynamoDB table and write to S3 in the same format 
    as your streaming Lambda
    """
    table = dynamodb.Table(TABLE_NAME)
    
    # Pagination for large tables
    last_evaluated_key = None
    batch_num = 0
    batch_size = 1000  # Items per S3 file
    
    while True:
        # Scan with pagination
        if last_evaluated_key:
            response = table.scan(
                ExclusiveStartKey=last_evaluated_key,
                Limit=batch_size
            )
        else:
            response = table.scan(Limit=batch_size)
        
        items = response.get('Items', [])
        
        if items:
            # Transform to match streaming Lambda format
            stream_records = []
            for item in items:
                # Convert to DynamoDB Stream format
                stream_record = {
                    'eventName': 'INSERT',  # Mark as INSERT
                    'eventID': f'backfill-{batch_num}',
                    'eventSource': 'aws:dynamodb',
                    'dynamodb': {
                        'NewImage': item,
                        'ApproximateCreationDateTime': datetime.utcnow().timestamp()
                    }
                }
                stream_records.append(stream_record)
            
            # Write to S3 (same format as Lambda)
            file_name = f"{S3_PREFIX}backfill-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{batch_num}.json"
            
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=file_name,
                Body=json.dumps({'Records': stream_records}),
                ContentType='application/json'
            )
            
            print(f"Uploaded batch {batch_num}: {len(items)} items to {file_name}")
            batch_num += 1
        
        # Check if there are more items
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    print(f"Backfill complete: {batch_num} batches uploaded")

if __name__ == '__main__':
    scan_and_upload_to_s3()
```

### **B. Run as AWS Lambda (for smaller tables)**

```python
# Lambda function for backfill
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    """
    Backfill Lambda - run multiple times with pagination
    Store LastEvaluatedKey in event for continuation
    """
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    
    table_name = os.environ['TABLE_NAME']
    bucket = os.environ['BUCKET_NAME']
    s3_prefix = os.environ['S3_PREFIX']
    
    table = dynamodb.Table(table_name)
    
    # Get pagination token from event (for recursive invocation)
    last_key = event.get('LastEvaluatedKey')
    
    # Scan batch
    scan_kwargs = {'Limit': 1000}
    if last_key:
        scan_kwargs['ExclusiveStartKey'] = last_key
    
    response = table.scan(**scan_kwargs)
    
    # Transform and upload
    items = response.get('Items', [])
    if items:
        stream_records = [
            {
                'eventName': 'INSERT',
                'dynamodb': {
                    'NewImage': item,
                    'ApproximateCreationDateTime': datetime.utcnow().timestamp()
                }
            }
            for item in items
        ]
        
        file_name = f"{s3_prefix}backfill-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.json"
        s3.put_object(
            Bucket=bucket,
            Key=file_name,
            Body=json.dumps({'Records': stream_records})
        )
    
    # Continue if more data
    next_key = response.get('LastEvaluatedKey')
    if next_key:
        # Invoke itself recursively for next batch
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',  # Async
            Payload=json.dumps({'LastEvaluatedKey': next_key})
        )
        return {'status': 'continuing', 'next_key': next_key}
    
    return {'status': 'complete'}
```

### **C. AWS Step Functions for Orchestration (Best for Large Tables)**

```json
{
  "Comment": "DynamoDB Backfill State Machine",
  "StartAt": "ScanBatch",
  "States": {
    "ScanBatch": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:backfill-scan-lambda",
      "Next": "CheckCompletion"
    },
    "CheckCompletion": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.LastEvaluatedKey",
          "IsPresent": true,
          "Next": "Wait"
        }
      ],
      "Default": "Complete"
    },
    "Wait": {
      "Type": "Wait",
      "Seconds": 1,
      "Next": "ScanBatch"
    },
    "Complete": {
      "Type": "Succeed"
    }
  }
}
```

---

## **Option 3: Parallel Scan with EMR or Databricks**

For **very large tables** (millions of records), use parallel scanning:

### **Databricks Job for Backfill**

```python
from pyspark.sql import SparkSession
import boto3
from concurrent.futures import ThreadPoolExecutor

def parallel_dynamodb_scan(table_name, num_segments=10):
    """
    Parallel scan of DynamoDB using multiple segments
    Each segment scans a portion of the table
    """
    
    def scan_segment(segment_num):
        """Scan a specific segment"""
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        items = []
        last_key = None
        
        while True:
            scan_kwargs = {
                'Segment': segment_num,
                'TotalSegments': num_segments,
                'Limit': 1000
            }
            
            if last_key:
                scan_kwargs['ExclusiveStartKey'] = last_key
            
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        return items
    
    # Parallel scan using thread pool
    with ThreadPoolExecutor(max_workers=num_segments) as executor:
        segment_results = list(executor.map(scan_segment, range(num_segments)))
    
    # Flatten results
    all_items = [item for segment in segment_results for item in segment]
    
    return all_items

# Use in Databricks
table_name = 'YourTable'
items = parallel_dynamodb_scan(table_name, num_segments=20)

# Convert to Spark DataFrame
df = spark.createDataFrame(items)

# Transform to match streaming format
stream_format_df = df.select(
    lit("INSERT").alias("eventName"),
    struct(
        col("*").alias("NewImage")
    ).alias("dynamodb")
)

# Write to S3
stream_format_df.write \
    .mode("overwrite") \
    .json("s3://your-bucket/dynamodb-stream-output/backfill/")
```

---

## **Option 4: Use AWS Glue**

AWS Glue can read from DynamoDB and write to S3:

```python
# AWS Glue Job
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read from DynamoDB
dynamodb_df = glueContext.create_dynamic_frame.from_options(
    connection_type="dynamodb",
    connection_options={
        "dynamodb.input.tableName": "YourTable",
        "dynamodb.throughput.read.percent": "0.5"  # Use 50% of table capacity
    }
)

# Convert to Spark DataFrame
df = dynamodb_df.toDF()

# Transform to match streaming format
from pyspark.sql.functions import *

stream_format = df.select(
    lit("INSERT").alias("eventName"),
    struct(col("*").alias("NewImage")).alias("dynamodb")
)

# Write to S3
stream_format.write \
    .mode("overwrite") \
    .json("s3://your-bucket/dynamodb-stream-output/backfill/")

job.commit()
```

---

## **Complete End-to-End Strategy**

Here's my recommended approach:

### **1. Initial Setup (One-Time Backfill)**

```bash
# Step 1: Export historical data
aws dynamodb export-table-to-point-in-time \
    --table-arn arn:aws:dynamodb:us-east-1:123456789012:table/YourTable \
    --s3-bucket your-bucket \
    --s3-prefix dynamodb-exports/backfill-$(date +%Y%m%d)/ \
    --export-format DYNAMODB_JSON
```

### **2. Transform Export (Databricks Job)**

```python
# Databricks notebook: transform_dynamodb_export.py

from pyspark.sql.functions import *
from pyspark.sql.types import *

# Read the export
export_path = "s3://your-bucket/dynamodb-exports/backfill-*/*/data/*.json.gz"
raw_export = spark.read.json(export_path)

# Transform DynamoDB JSON to regular JSON
def parse_dynamodb_type(item_struct):
    """
    Parse DynamoDB type descriptors (S, N, BOOL, M, L, etc.)
    """
    return select_expr(
        """
        transform_values(
            Item,
            (k, v) -> 
                CASE 
                    WHEN v.S IS NOT NULL THEN v.S
                    WHEN v.N IS NOT NULL THEN v.N
                    WHEN v.BOOL IS NOT NULL THEN CAST(v.BOOL AS STRING)
                    WHEN v.NULL = true THEN NULL
                    WHEN v.M IS NOT NULL THEN to_json(v.M)
                    WHEN v.L IS NOT NULL THEN to_json(v.L)
                    ELSE NULL
                END
        ) as parsed_item
        """
    )

# Transform to match streaming Lambda format
transformed = raw_export.select(
    lit("INSERT").alias("eventName"),
    lit("backfill").alias("source"),
    current_timestamp().alias("processingTime"),
    struct(
        col("Item").alias("NewImage")  # Keep DynamoDB format if Lambda outputs it
    ).alias("dynamodb")
)

# Write to same location as streaming data
# Use date partition to separate backfill from streaming
transformed \
    .withColumn("date", lit("backfill-2025-11-12")) \
    .write \
    .mode("overwrite") \
    .partitionBy("date") \
    .json("s3://your-bucket/dynamodb-stream-output/")

print("✓ Backfill transformation complete")
```

### **3. Update Databricks Job to Handle Both**

```python
# Your existing Databricks job - now handles both streaming and backfill

from pyspark.sql.functions import *

# Read from S3 (both streaming and backfill data)
df = spark.read.json("s3://your-bucket/dynamodb-stream-output/")

# Process normally - your code doesn't need to know if it's backfill or streaming
processed_df = df.select(
    col("dynamodb.NewImage.*"),
    col("eventName"),
    col("processingTime")
)

# Write to Databricks table with merge to handle duplicates
processed_df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable("catalog.schema.your_table")
```

### **4. Handle Duplicates (Important!)**

Since you might have overlap between backfill and streaming, use MERGE:

```python
from delta.tables import *

def upsert_to_table(batch_df, batch_id):
    """Upsert to avoid duplicates between backfill and streaming"""
    
    delta_table = DeltaTable.forName(spark, "catalog.schema.your_table")
    
    delta_table.alias("target").merge(
        batch_df.alias("source"),
        "target.id = source.id"  # Your primary key
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()

# Use this in your streaming or batch job
df.writeStream \
    .foreachBatch(upsert_to_table) \
    .option("checkpointLocation", "s3://bucket/checkpoints/") \
    .start()
```

---

## **Comparison of Approaches**

| Approach | Best For | Pros | Cons | Time |
|----------|----------|------|------|------|
| **DynamoDB Export** | Large tables (>1M records) | ✅ Fastest<br>✅ No table impact<br>✅ Point-in-time consistent | ⚠️ Needs transformation<br>⚠️ Different format | Minutes |
| **Scan Script** | Small-medium tables (<1M) | ✅ Matches streaming format<br>✅ Simple | ⚠️ Impacts table performance<br>⚠️ Slow for large tables | Hours |
| **Parallel Scan (Databricks)** | Medium tables (1M-10M) | ✅ Fast<br>✅ Built-in transformation | ⚠️ More complex<br>⚠️ Table impact | Minutes-Hours |
| **AWS Glue** | Large tables, existing Glue setup | ✅ Managed service<br>✅ Scalable | ⚠️ Extra cost<br>⚠️ Needs transformation | Minutes-Hours |

---

## **My Recommendation for ChargeMinder**

Given your setup, I recommend:

1. **Use DynamoDB Export** for the initial backfill (fastest, no table impact)
2. **Write a Databricks transformation job** to convert export format to match your Lambda's output
3. **Use MERGE/UPSERT** in your Databricks job to handle any overlap between backfill and streaming
4. **Separate prefixes** in S3: `backfill/` vs `streaming/` for clarity

**Estimated timeline:**
- Export: 15-30 minutes for typical table
- Transformation: 5-15 minutes in Databricks
- Load to Databricks: Depends on table size

Want me to help you write the complete transformation code for your specific ChargeMinder telemetry data structure?

## ChatGPT

Short answer: use a one-time **full export from DynamoDB to S3** for the historical backfill, run a **Databricks backfill job** over that export using the *same* transform you already use for streaming, then let your existing **Streams → Lambda → S3 → Databricks** pipeline keep you current.

Why: DynamoDB Streams only contain **future modifications** (and for ~24h), so old rows won’t ever appear on the stream. ([AWS Documentation][1])

# Recommended plan

1. **Do a full export of the table to S3 (once).**
   Use DynamoDB “Export to S3”. It’s async, has **no impact on table RCUs**, and writes either **DynamoDB JSON** or **Amazon Ion** into S3 with a manifest. Pick a distinct prefix, e.g. `s3://bucket/dynamodb-export/2025-11-12/`. ([AWS Documentation][2])

2. **Run a Databricks backfill job** over that export prefix.
   Reuse your existing transformation function (the logic that maps the nested item into your target schema). Write the output into the same Unity Catalog Delta table, using **idempotent** semantics (e.g., `MERGE` on your business key with `updated_at` tie-breakers). Enable schema evolution:

   * `spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")`
   * `mergeSchema=true` if you’re appending.
     This ensures any new attributes present in export also materialize as new columns. ([Amazon Web Services, Inc.][3])

3. **Keep your live pipeline running** for new changes.
   The stream (Lambda → S3 → Databricks) continues to deliver fresh updates while the backfill loads historical data. If overlap is possible, let the **MERGE** resolve duplicates by key + last-write-wins. ([AWS Static][4])

# Databricks backfill: practical starter

**Reading the DynamoDB export** (DynamoDB JSON) into Spark:

```python
EXPORT_PREFIX = "s3://your-bucket/dynamodb-export/2025-11-12/"
CHECKPOINT    = "s3://your-bucket/_checkpoints/ddb_backfill"
TARGET_TABLE  = "hcai_databricks_dev.chargeminder2.events"

# If your export is a one-time batch, use read (not readStream).
raw = (spark.read
       .format("json")
       .load(EXPORT_PREFIX))

# raw rows are in DynamoDB JSON ("S","N","M","L" wrappers).
# Write or import a small UDF to unwrap these to native types,
# OR pre-convert with AWS Glue (DDB JSON -> Parquet).
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# Example placeholder: you’d replace with a robust unwrap for S/N/M/L/BOOL/NULL
@udf("string")
def unwrap_example(d): 
    # d looks like {"S":"abc"} or {"N":"123"} etc.
    # ... implement full unwrap here ...
    return d.get("S") if isinstance(d, dict) and "S" in d else None

# Apply your existing transformation function to produce df_out
# df_out must match your Delta target schema (or superset, with autoMerge)
df_out = (raw
          # .withColumn("id", unwrap_example(raw["yourKey"]))
          # ... your existing mapping logic here ...
          )

spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

# Prefer MERGE for idempotency (dedupe by key/updated_at)
from delta.tables import DeltaTable
tgt = DeltaTable.forName(spark, TARGET_TABLE)
(tgt.alias("t")
   .merge(df_out.alias("s"), "t.id = s.id")
   .whenMatchedUpdateAll()
   .whenNotMatchedInsertAll()
   .execute())
```

Notes:

* If you’d rather avoid writing an “unwrap DDB JSON” UDF, an **AWS Glue job** can convert the export to **Parquet** first; then your Databricks backfill reads cleanly typed Parquet. (This is a common path and easy to automate.) ([AWS Documentation][5])
* For massive tables, run the backfill in parallel (partition on the export folder structure) and **checkpoint** only your Databricks job state (the export itself is immutable).

# Alternative (not recommended unless you must)

* **“Self-replay” the table via writes**: do a full Scan and issue a no-op `UpdateItem` per row to force a stream record so your existing Lambda sees “historical” rows. This **consumes RCUs/WCUs**, is slow/pricey, and risks side effects (TTL, triggers). Prefer Export→S3 backfill. (Streams emit only on modifications; they won’t produce events for existing items.) ([AWS Documentation][1])

# Format & governance tips

* DynamoDB Export creates **manifests + gzipped object shards**; point Databricks at the prefix; don’t forget to recurse folders. ([AWS Documentation][6])
* Keep a **max `source_updated_at`** watermark in your Delta table so the backfill MERGE can skip newer rows if needed (or let last-write-wins).
* If your streaming Lambda writes in a different JSON shape than the export, keep two reader paths but a **single transform()** that normalizes to a common intermediate schema before writing.
* For ongoing sync use cases, AWS now documents **full export + incremental exports** patterns that complement streams. ([Amazon Web Services, Inc.][3])

# TL;DR

1. One-time **Export to S3** → Databricks **backfill job** (MERGE, auto-evolve schema).
2. Keep **Streams→Lambda→S3→Databricks** for new changes.
   This cleanly covers “historical + real-time” with minimal risk and strong performance. ([AWS Documentation][2])

[1]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html?utm_source=chatgpt.com "Change data capture for DynamoDB Streams"
[2]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.HowItWorks.html?utm_source=chatgpt.com "DynamoDB data export to Amazon S3: how it works"
[3]: https://aws.amazon.com/solutions/guidance/incremental-data-exports-from-amazon-dynamodb-to-amazon-s3/?utm_source=chatgpt.com "Guidance for Incremental Data Exports from Amazon ..."
[4]: https://d1.awsstatic.com/solutions/guidance/architecture-diagrams/incremental-data-exports-on-aws.pdf?utm_source=chatgpt.com "Guidance for Incremental Data Exports on AWS - awsstatic.com"
[5]: https://docs.aws.amazon.com/prescriptive-guidance/latest/dynamodb-full-table-copy-options/amazon-s3.html?utm_source=chatgpt.com "Using DynamoDB with Amazon S3 to export and import ..."
[6]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.Output.html?utm_source=chatgpt.com "DynamoDB table export output format"

## Grok: Backfilling Historical DynamoDB Data into Your Streaming Pipeline

Your existing pipeline (DynamoDB Streams → Lambda → S3 → Databricks Job) is designed for **incremental** processing of new/modified records via streams, which capture only changes made *after* the stream is enabled (with a 24-hour retention limit). Historical records (pre-pipeline data) won't trigger the stream automatically, so you need a **one-time backfill** process to export them to the same S3 location in a compatible format. This ensures the Databricks job can process them seamlessly, populating your Unity Catalog table with full historical data before ongoing streams take over.

The recommended approach uses DynamoDB's native **Export to S3** feature, which is serverless, doesn't consume read capacity units (RCUs), and exports data asynchronously without impacting table performance. It supports Point-in-Time Recovery (PITR) for consistent snapshots from up to 35 days ago (or full table if PITR is enabled). Exports land in S3 as DynamoDB JSON files (or Amazon Ion), which your Lambda likely parses—ensure the backfill format matches (e.g., via Lambda transformation if needed).

#### Prerequisites
- **Enable PITR** on your DynamoDB table (if not already): This is required for exports and allows point-in-time snapshots. In the AWS Console: DynamoDB → Tables → Your Table → Backups → Edit → Enable Point-in-Time Recovery (PITR). It's free for the first 35 days of retention.
- **S3 Bucket Permissions**: Grant the DynamoDB service principal (`dynamodb.amazonaws.com`) `PutObject` access to your target S3 bucket/prefix (the same one your Lambda uses). Use an IAM policy like:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "dynamodb.amazonaws.com" },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::your-bucket/your-prefix/*"
      }
    ]
  }
  ```
- **IAM Role for DynamoDB Export**: Attach `AmazonDynamoDBFullAccess` (or scoped to `dynamodb:ExportTableToPointInTime`) to your IAM user/role.
- **Databricks Access**: Ensure your Databricks workspace has S3 read access (via instance profile or access keys) to ingest the exported files.

#### Step-by-Step: Export Historical Data to S3
1. **Via AWS Console (Simplest for One-Off)**:
   - Go to DynamoDB Console → Tables → Your Table → Exports to S3 tab.
   - Click **Export to S3**.
   - **S3 Bucket and Prefix**: Enter your existing S3 location (e.g., `s3://your-bucket/streaming-prefix/historical/` to avoid overwriting live files—use a sub-prefix and merge in Databricks if needed).
   - **Point-in-Time**: Select "Full export" for all historical data, or specify a timestamp (e.g., pipeline start time) for a snapshot.
   - **Format**: Choose DynamoDB JSON (matches stream events; convert to standard JSON if your Lambda expects it).
   - Click **Export**. Monitor progress in the Exports tab (typically minutes to hours, based on table size; up to 100 TB supported).
   - Files appear in S3 as compressed JSON manifests (e.g., `data/*.json.gz`), partitioned by hash/range keys for efficiency.

2. **Via AWS CLI (For Automation/Scripting)**:
   ```bash
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:region:account:table/your-table \
     --s3-bucket your-bucket \
     --s3-s3-prefix streaming-prefix/historical/ \
     --export-format DynamoDBJson
   ```
   - Track with `aws dynamodb describe-export --export-arn <export-arn>`.
   - Costs: $0.10/GB exported (full export based on table size at export time).

3. **Handling Large Tables**:
   - Exports are parallelized across shards; no RCU impact.
   - If >100 TB or cross-region/account: Exports support it natively (grant cross-account S3 perms).
   - Incremental exports (for changes since last export) are possible but not needed for one-time backfill.

#### Integrate with Your Pipeline: Process in Databricks
Once exported to S3, trigger your Databricks job manually (or via a File Arrival sensor on the historical prefix) to read and ingest the files—just like streaming data. This populates the Unity Catalog table with historical records.

- **Databricks Job/Task Code Example** (PySpark; assumes Delta table for schema evolution):
  ```python
  # Read historical JSON from S3 (matches Lambda output format)
  df = (spark.read
      .format("json")  # Or "cloudFiles" for Auto Loader if using incremental mode
      .option("multiline", "true")  # For nested JSON
      .load("s3://your-bucket/streaming-prefix/historical/")  # Your export path
  )

  # Optional: Flatten/transform if needed (e.g., extract from stream event wrapper)
  from pyspark.sql.functions import col
  df = df.select("dynamodb.NewImage.*")  # Adjust based on stream format (OldImage/NewImage)

  # Write to Unity Catalog table (append with schema evolution)
  df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable("my_catalog.my_schema.your_table")
  ```
  - **Schema Evolution**: As discussed previously, `mergeSchema=true` auto-adds columns for any schema drift between historical and streaming data.
  - **DynamoDB JSON Handling**: Exports use DynamoDB's binary JSON (with types like `N` for numbers). Use `from_dynamodb_json` UDF if needed:
    ```python
    from pyspark.sql.functions import udf
    from pyspark.sql.types import StringType
    import json
    def parse_ddb_json(col):
        return json.loads(col)  # Or use boto3.dynamodb.types.TypeDeserializer
    parse_udf = udf(parse_ddb_json, StringType())
    df = df.withColumn("parsed_data", parse_udf(col("data")))
    ```
  - Run the job: In Databricks Workflows, trigger manually or schedule once.

- **Verify Ingestion**:
  - Query the Delta table: `SELECT COUNT(*) FROM my_catalog.my_schema.your_table;`
  - Check for duplicates: Add a watermark or processed flag in your Lambda/Databricks to dedupe (e.g., based on DynamoDB sequence number).

#### Ongoing Streaming: Seamless Handoff
- After backfill, your Lambda continues writing new stream events to the same S3 prefix (e.g., without `/historical/`).
- To merge: Configure Databricks to read from the root prefix, or use Auto Loader (`cloudFiles`) for unified incremental + historical processing:
  ```python
  df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")
      .load("s3://your-bucket/streaming-prefix/")  # Includes historical + new
  )
  # Write stream as before
  ```
- **Idempotency**: Ensure your Databricks transform handles `INSERT`/`MODIFY`/`REMOVE` stream records (e.g., via MERGE for upserts).

#### Alternatives If Export Doesn't Fit
| Method | Pros | Cons | When to Use |
|--------|------|------|-------------|
| **DynamoDB Export to S3** (Recommended) | Serverless, no RCU cost, scalable to TBs, PITR snapshots. | Requires PITR; format conversion if mismatched. | Large tables; one-time full backfill. |
| **Scan via Lambda/EC2 Script** | Customizable; direct to S3. | Consumes RCUs; Lambda timeout (15 min); manual scaling. | Small tables (<1 GB); if no PITR. Example: Loop `scan()` API, batch-write to S3. |
| **Update Existing Items to Trigger Stream** | Reuses exact pipeline. | High cost (write RCUs); risk of duplicates/outages. | Very small tables; testing only. Add/remove a flag field via script. |
| **AWS Glue/EMR** | Handles transforms; ETL jobs. | Extra cost (~$0.44/hour per DPU); setup overhead. | Complex schema changes during backfill. |

#### Costs and Best Practices
- **Export Cost**: $0.10/GB (e.g., 100 GB table = $10 one-time).
- **S3 Storage**: ~$0.023/GB/month; use lifecycle policies to archive/delete historical files post-ingestion.
- **Monitoring**: Track export status via CloudWatch (`DynamoDBExport*` metrics); Databricks job logs for ingestion errors.
- **Testing**: Export a small PITR window first; validate row counts match `scan` estimates.
- **Edge Cases**: If data >35 days old (no PITR history), use full export. For cross-account S3, add bucket policies.

This backfill keeps your pipeline unchanged while ensuring complete data in Databricks. If your Lambda outputs a specific format (e.g., Parquet), add a post-export Glue job to transform. Share more details (e.g., table size, Lambda code snippet) for tweaks!
