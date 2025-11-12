## Databricks Job

It Streamining we use readStream() and writeStream(), checkpoint required

Explain the difference
cloudFiles.useNotifications=true (or use cloudFiles.useManagedFileEvents=true
 

## Trigger Type: File Arrival

S3 (event) → SNS topic → SQS queue → Databricks Auto Loader
```
1. Lambda writes file → s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/file.json                   ↓
2. S3 Event Notification → SQS Queue                       ↓
3. Databricks File Arrival Trigger monitors SQS → Detects new file                       ↓
4. Starts your Databricks Job (streaming query)                      ↓
5. Auto Loader reads from SQS notification → Processes new file(s)                      ↓
6. Checkpoint tracks processed files → No duplicates                     ↓
7. Query completes (if using availableNow) → Cluster stops
```

### Code modification
```
# Change this line from:
.option("cloudFiles.useNotifications", "false")  # ❌ Current

# To this:
.option("cloudFiles.useNotifications", "true")   # ✅ For File Arrival
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

```
writer = (
            flat_stream.writeStream
                .option("checkpointLocation", CONFIG["checkpoint_path"])
                .foreachBatch(upsert_batch)
                .option("mergeSchema", "true")
                .trigger(processingTime="30 seconds") # continuousl watch  for new files
                .trigger(availableNow=True)    #  Good for reprocessing current dta and stop File-Arrival job DOES NOT WAIT FOR NEW FILES
        )
```

If trigger is not speccified to writeStream default is   
.trigger(processingTime="100ms")  
which is 100 times per second






## IAM Requirements: GROK

### 1. Give Databricks permission to create SNS/SQS for you
```
aws iam create-policy --policy-name DatabricksAutoLoaderNotifications \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["sns:CreateTopic","sns:Subscribe"],"Resource":"*"},
      {"Effect":"Allow","Action":["sqs:*"],"Resource":"*"}
    ]
  }'
```
### Attach the policy to the role
that your Databricks workspace uses for S3 access  
Databricks will now auto-provision an SNS topic + SQS queue 
the first time you start the stream with useNotifications=true.


## 🔐 AWS IAM Permissions (Claude)

### IAM Policy for Databricks

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SQSAccessForAutoLoader",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:*:*:databricks-auto-ingest-*"
    },
    {
      "Sid": "SQSListQueues",
      "Effect": "Allow",
      "Action": "sqs:ListQueues",
      "Resource": "*"
    }
  ]
}
```

### S3 Event Notification to SQS

```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksAutoLoaderNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```

### SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/databricks-instance-role"
      },
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder"
    }
  ]
}
```

## 🎯 Two Modes of Operation

### Mode 1: Continuous Streaming (Your Current Code)
```python
if CONFIG["trigger_mode"] == "availableNow":
    writer = writer.trigger(availableNow=True)  # ✅ Process files then stop
else:
    writer = writer.trigger(processingTime=CONFIG["processing_time"])  # Continuous
```

**For File Arrival Trigger, use:**
```python
CONFIG = {
    "trigger_mode": "availableNow",  # ✅ Recommended for cost efficiency
    # When file arrives → job starts → processes all files → stops
}
```

### Mode 2: Always-On Streaming
```python
CONFIG = {
    "trigger_mode": "processingTime",
    "processing_time": "1 minute",
    # Cluster stays running, checks every minute
}
```

## 📊 Comparison: Batch vs Streaming with File Arrival

| Approach | Trigger | Processing | Checkpoints | Duplicates | Cost |
|----------|---------|------------|-------------|------------|------|
| **Batch (read + merge)** | Manual/Orchestrated | Each file separately | No | Possible | Lower if infrequent |
| **Streaming + File Arrival** ✅ | Automatic on file | Incremental with checkpoints | Yes | Prevented | Optimal with availableNow |
| **Continuous Streaming** | Always running | Continuous micro-batches | Yes | Prevented | Higher (always on) |

## ✅ Your Code is Already Correct!

The only actual modifications needed:

### 1. Change One Option (Critical)
```python
.option("cloudFiles.useNotifications", "true")  # Changed from "false"
```

### 2. Optionally Add Queue Name (For Multiple Jobs)
```python
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")  # Optional but recommended
```

### 3. Recommended: Use availableNow Trigger
```python
CONFIG = {
    "trigger_mode": "availableNow",  # Process files and stop (cost-efficient)
    # ... rest of config unchanged
}
```

## 🚀 Setup Steps

### 1. Create SQS Queue
```bash
aws sqs create-queue \
  --queue-name databricks-auto-ingest-chargeminder \
  --attributes MessageRetentionPeriod=86400
```

### 2. Configure S3 Event Notifications
```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://s3-notification.json
```

### 3. Update Your Code
```python
# In read_stream() function:
.option("cloudFiles.useNotifications", "true")
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

### 4. Create Databricks Job
- **No File Arrival Trigger needed in Databricks UI!**
- Just create a regular scheduled job or run it manually first
- Auto Loader will automatically poll the SQS queue
- When files arrive → Auto Loader processes them automatically

## 🎓 Key Takeaways

1. ✅ **File Arrival = Streaming, not batch**
2. ✅ **Auto Loader with useNotifications=true handles everything**
3. ✅ **checkpointLocation is required**
4. ✅ **schemaLocation is required**
5. ✅ **Your original code is correct**, just change one option
6. ✅ **availableNow trigger is recommended** for cost efficiency

 
## Another opinion on IAM permisiions for File arrive Trigger


🔐 AWS IAM Permissions Required
Option A: Using S3 Event Notifications + SQS (Recommended)
This is the standard approach for File Arrival triggers.

1. IAM Policy for Databricks Instance Profile/Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "S3WriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2/archived/*",
        "arn:aws:s3:::chargeminder-2/quarantine/*"
      ]
    },
    {
      "Sid": "SQSAccess",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue"
    }
  ]
}
```
2. S3 Bucket Notification Configuration
   
```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksFileArrivalNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```
3. SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    }
  ]
}
```

## Option B: Using S3 Event Notifications + SNS
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SNSAccess",
      "Effect": "Allow",
      "Action": [
        "sns:Subscribe",
        "sns:Unsubscribe",
        "sns:GetTopicAttributes"
      ],
      "Resource": "arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-topic"
    }
  ]
}
```

📋 Setup Steps for File Arrival Trigger
### Option B: Step 1: Create SQS Queue

```bash
aws sqs create-queue \
  --queue-name databricks-file-arrival-queue \
  --attributes '{
    "MessageRetentionPeriod": "86400",
    "VisibilityTimeout": "300"
  }'

```

### Option B: Step 2: Configure S3 Event Notifications

```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://notification-config.json
```

###   Option B: Step 3: Create Databricks Job with File Arrival Trigger

In Databricks UI:
```
1. **Create Job**
2. **Add Task:**
   - Task name: `process_telemetry`
   - Type: `Python script` or `Notebook`
   - Source: Your modified script
   - Cluster: Select appropriate cluster

3. **Configure Trigger:**
   - Click **Add trigger**
   - Select **File arrival**
   - Configure:


File notification service: SQS (or SNS)
Queue/Topic URL:
https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
#### Advanced Options:
```
Wait for all tasks: ✓
Max concurrent runs: 1 (or higher for parallel processing)
Timeout: 60 minutes
```


###  Test the Setup - Upload a test file to S3
 
```bash
aws s3 cp test-file.json s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/
```
### Check SQS queue for message
```
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
### Monitor Databricks job runs
  The job should trigger automatically within a few seconds





#### Limitations
| Aspect | Details |
|--------|---------|
| **Polling Frequency** | Every ~1 minute (affected by storage perf; faster with "file events" enabled on Unity Catalog external locations). |
| **File Detection** | Triggers on *any* new/updated file in the path (no native filtering). Multiple files in one minute → single trigger. |
| **Path Scope** | Root or subpath only; no regex/wildcards in UI. |
| **Max Triggers** | Up to 1,000 per workspace (with file events enabled). |
| **Cost** | Free (beyond S3 listing costs); no extra DBUs for polling. |

If files arrive irregularly (e.g., Lambda dumps), it may delay ~1 minute—use **file events** (enable on external locations) for <10s latency.

#  How to Filter Input Files Effectively
Since the trigger fires on *any* file, implement filtering **in your PySpark job code** (e.g., using Auto Loader options).  
This is the recommended pattern—no UI changes needed.

 ## 1. **Filter in Auto Loader (cloudFiles Options)**
   Use `.option("cloudFiles.includeExistingFiles", "false")` + pattern matching to ignore non-target files.

   ```python
   # In your read_stream() function
   return (
       spark.readStream
           .format("cloudFiles")
           .option("cloudFiles.format", "json")
           .option("cloudFiles.schemaLocation", CONFIG["schema_path"])
           .option("cloudFiles.useNotifications", "true")  # For low-latency events
           .option("cloudFiles.maxFilesPerTrigger", "1000")
           # ----- FILE PATTERN FILTERING -----
           .option("cloudFiles.fileNamePattern", ".*\\.jsonl$")  # <--------    Only *.jsonl files
           # Or more complex: .option("cloudFiles.filterFunction", "lambda path: 'telemetry' in path")
           .option("cloudFiles.schemaEvolutionMode", "rescue")
           .option("rescuedDataColumn", "_rescued_data")
           .schema(raw_schema)
           .load(SOURCE_PATH)
           .withColumn("source_file", F.col("_metadata.file_path"))
   )
   ```

   - **Patterns Supported**: Regex (e.g., `.*telemetry-.*\\.jsonl$`) or custom functions.
   - **Behavior**: Auto Loader scans and filters *before* processing—ignores mismatches without triggering MERGE.

## 2. **Filter in Your Batch Function (upsert_batch)**
   If patterns vary, filter post-read:

   ```python
   # In upsert_batch(micro_df, batch_id)
   # Filter to only process *.jsonl
   filtered_df = micro_df.filter(F.regexp_extract(F.col("source_file"), r"([^/]+)$", 1).like("%jsonl"))
   
   if filtered_df.count() == 0:
       print(f"No matching files in batch {batch_id} — skipping")
       return
   
   # Then validate/dedup/MERGE on filtered_df
   valid_df, invalid_df, _ = validate_batch(filtered_df)
   # ... rest of MERGE
   ```

 ## 3. **Use Subpaths for "Patterns"**
   - Structure your S3 like: `s3://bucket/raw/telemetry/jsonl/` (only JSONL here).
   - Trigger monitors the subpath—no code changes.

 ## 4. **Advanced: Custom SNS Filtering (If Using Events)**
   - In AWS SNS: Add a **filter policy** on S3 events (e.g., `{"object.key[0]": [{"prefix": "telemetry-"}]}`).
   - This prevents the trigger from firing on non-matches.

 ## Testing & Best Practices
1. **Test Setup**: Upload a non-matching file (e.g., `.txt`) → Trigger should fire, but your code filters it out (check logs).
2. **Monitor**: Use Job runs/logs; query `_rescued_data` for mismatches.
3. **Docs Links**:
   - [File Arrival Triggers](https://docs.databricks.com/aws/en/jobs/file-arrival-triggers.html) (confirms no pattern UI).
   - [Auto Loader Patterns](https://docs.databricks.com/en/ingestion/cloud-object-storage/auto-loader/patterns.html) (for code filtering).
4. **Community Workaround**: Users on forums (e.g., Reddit, Databricks Community) confirm UI limitation—code-based filtering is standard.



# You cannot use dbutils inside foreachBatch (or any Spark job) when running in File Arrival / Streaming mode — it is not serializable and will throw the error

 You cannot use `dbutils` inside `foreachBatch` (or any Spark job) when running in **File Arrival / Streaming mode** —  
 it is **not serializable** and will throw the exact error you saw.**  

**Fix:**  
1. **Never call `dbutils.fs.mv()` inside `upsert_batch`.**  
2. **Use pure PySpark (`spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem`) or AWS SDK (`boto3`) to move files.**  
3. **Or: Do the move *outside* the stream (e.g., in a separate scheduled job).**

---

## Why `dbutils` Fails in `foreachBatch`

| Feature | `dbutils` | Spark Job (`foreachBatch`) |
|--------|-----------|----------------------------|
| **Serializable?** | No | **Must be** |
| **Runs on** | Driver (Databricks-specific) | Driver **via Spark Connect** |
| **Pickling** | Contains live JVM objects | **Cannot be pickled** |
| **Error** | `You cannot use dbutils within a spark job or otherwise pickle it` | Exactly what you got |

> `dbutils` is a **Databricks-specific utility** that wraps the notebook/driver context.  
> Spark **cannot send it to executors** or **serialize it** for `foreachBatch`.

---

## Correct Way to Move Files in Streaming Job

### Option 1: **Pure PySpark (Hadoop FS) – Recommended**

```python
def move_file_hadoop(src_path: str, dst_path: str, spark):
    """Move file using Hadoop FileSystem (no dbutils)."""
    fs = spark._jsc.hadoopConfiguration()
    path_src = spark._jvm.org.apache.hadoop.fs.Path(src_path)
    path_dst = spark._jvm.org.apache.hadoop.fs.Path(dst_path)
    file_system = spark._jvm.org.apache.hadoop.fs.FileSystem.get(fs)
    
    if file_system.exists(path_src):
        file_system.rename(path_src, path_dst)
        print(f"Moved: {src_path} → {dst_path}")
    else:
        print(f"File not found: {src_path}")
```

Use it in `upsert_batch`:

```python
# Inside upsert_batch (after MERGE)
spark = micro_df.sparkSession
for file_path in micro_df.select("source_file").distinct().collect():
    src = file_path["source_file"]
    dst = src.replace("/raw/", "/archived/")
    move_file_hadoop(src, dst, spark)
```

---

### Option 2: **Use `boto3` (AWS SDK)**

```python
import boto3

s3 = boto3.client('s3')

def move_file_boto3(src_bucket, src_key, dst_bucket, dst_key):
    # Copy
    s3.copy_object(
        Bucket=dst_bucket,
        Key=dst_key,
        CopySource={'Bucket': src_bucket, 'Key': src_key}
    )
    # Delete original
    s3.delete_object(Bucket=src_bucket, Key=src_key)
    print(f"Moved: s3://{src_bucket}/{src_key} → s3://{dst_bucket}/{dst_key}")
```

Call it:

```python
bucket = "chargeminder-2"
for row in micro_df.select("source_file").distinct().collect():
    src_key = row["source_file"].replace(f"s3://{bucket}/", "")
    dst_key = src_key.replace("raw/", "archived/")
    move_file_boto3(bucket, src_key, bucket, dst_key)
```

**Note:** Requires IAM role with `s3:CopyObject`, `s3:DeleteObject`.

---

### Option 3: **Move Files Outside the Stream (Best Practice)**

Run a **separate scheduled job** (e.g., every 5 min) that:
1. Queries the **metrics table** or **Delta `_commit` logs** to find processed files.
2. Uses `dbutils.fs.mv()` safely (since it's not in a Spark job).

```python
# Separate job: archive_processed.py
processed_files = spark.sql("""
    SELECT DISTINCT source_file 
    FROM telemetry_metrics 
    WHERE status = 'SUCCESS' AND run_timestamp > date_sub(current_date(), 1)
""")

for row in processed_files.collect():
    src = row.source_file
    dst = src.replace("/raw/", "/archived/")
    dbutils.fs.mv(src, dst)
```

**Pros:**  
- `dbutils` is safe  
- No serialization issues  
- Cleaner separation

---

## Updated `archive_processed_files` (Safe for Streaming)

```python
def archive_processed_files(micro_df: DataFrame, spark):
    """Move processed files using Hadoop FS (no dbutils)."""
    bucket = CONFIG["s3_bucket"]
    archive_prefix = CONFIG["archive_prefix"]

    files = [row["source_file"] for row in micro_df.select("source_file").distinct().collect()]
    fs = spark._jsc.hadoopConfiguration()
    hdfs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(fs)

    for src_path in files:
        if not src_path.startswith("s3://"):
            continue
        src_key = src_path.replace(f"s3://{bucket}/", "")
        dst_key = src_key.replace(CONFIG["s3_prefix"].rstrip("/"), archive_prefix.rstrip("/"))
        dst_path = f"s3://{bucket}/{dst_key}"

        src = spark._jvm.org.apache.hadoop.fs.Path(src_path)
        dst = spark._jvm.org.apache.hadoop.fs.Path(dst_path)
        if hdfs.exists(src):
            hdfs.rename(src, dst)
            print(f"Archived: {src_path} → {dst_path}")
```

Call from `upsert_batch`:

```python
archive_processed_files(micro_df, spark)
```

---

## Final `upsert_batch` Snippet (No `dbutils`)

```python
def upsert_batch(micro_df: DataFrame, batch_id: int):
    spark = micro_df.sparkSession  # Fresh session

    # ... validation, MERGE ...

    # Archive using Hadoop FS
    archive_processed_files(micro_df, spark)
```

---

## Summary

| Method | Can use in `foreachBatch`? | Needs IAM? | Recommended? |
|-------|----------------------------|-----------|--------------|
| `dbutils.fs.mv()` | No | No | No |
| Hadoop FS (`FileSystem`) | Yes | No | Yes |
| `boto3` | Yes | Yes (`CopyObject`, `DeleteObject`) | Yes |
| Separate job | Yes (outside stream) | Yes | Yes (cleanest) |

---

## Summary

> **No, you cannot use `dbutils` to move files inside `foreachBatch` in File Arrival mode.**  
> **Use Hadoop FS (`spark._jvm.org.apache.hadoop.fs.FileSystem`) or `boto3` instead.**  
> **Or move files in a separate scheduled job using `dbutils` safely.**

# How to avoid  providing  S3 input folder in 2 places: Task File Arrival trigger and Python task code


Problem statement:  The S3 location with input files should be hardcoded in 2 places :

1) Databricks task trigger on file arrival
2) PySpark code which is invoked by this trigger
 

Below is a **complete, production-ready pattern** that lets you **declare the S3 location only once** and have it flow automatically into:

1. **Databricks file-arrival trigger** (the *Job* that wakes up when a new file lands)  
2. **Your PySpark script** (the code that actually reads the files)

---

## 1. Declare the location **once** – in a **Databricks Job parameter**

| UI | CLI | API |
|----|-----|-----|
| **Jobs → Edit → Parameters** | `databricks jobs configure --job-id <id> --json '{ "parameters": { "s3_source": "s3://my-bucket/raw/telemetry" } }'` | `POST /api/2.1/jobs/update` with `settings.parameters` |

> **Only one place to change** when the bucket/prefix moves.

---

## 2. Trigger the job **on file arrival** using **S3 Event → SNS → Databricks Job**

### Step-by-step (one-time)

| Step | What you do |
|------|-------------|
| **a.** Create an **SNS topic** (Databricks can do it for you – see below) |
| **b.** Configure **S3 bucket** → **Event Notification** → **SNS topic** on `*.jsonl` (or `*.gz`) |
| **c.** Give Databricks permission to **subscribe** to that topic and **run the job** |

```bash
# 1. Create SNS policy (run once)
aws sns create-topic --name databricks-file-arrival

# 2. S3 bucket event (via console or CLI)
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:123456789012:databricks-file-arrival",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": { "Key": { "FilterRules": [{ "Name": "suffix", "Value": ".jsonl" }]}}
    }]
  }'
```

> **Databricks will auto-subscribe** the first time you run the job with `cloudFiles.useNotifications=true`.

---

## 3. PySpark script – **read the parameter** (no hard-coded path)

```python
# -------------------------------------------------
#  databricks_file_arrival_job.py
# -------------------------------------------------
import sys
from pyspark.sql import functions as F

# ---------- 1. Get the S3 path from job parameter ----------
# Databricks injects parameters into sys.argv when you use "Parameters" in the UI
if len(sys.argv) < 2:
    raise ValueError("Missing required parameter: s3_source")
S3_SOURCE = sys.argv[1]                     # <-- ONLY ONE PLACE

# Optional: fallback for local testing
# S3_SOURCE = S3_SOURCE or "s3://my-bucket/raw/telemetry"

print(f"Job started for path: {S3_SOURCE}")

# ---------- 2. Auto Loader (file-notification mode) ----------
df = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{S3_SOURCE}/_schema")
        .option("cloudFiles.useNotifications", "true")   # <-- reacts to SNS
        .option("cloudFiles.maxFilesPerTrigger", "500")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(raw_schema)
        .load(S3_SOURCE)
        .withColumn("source_file", F.col("_metadata.file_path"))
)

# ---------- 3. Rest of your pipeline (transform → MERGE) ----------
# ... (same as before) ...

# ---------- 4. Start the stream ----------
query = (
    df.writeStream
      .option("checkpointLocation", f"{S3_SOURCE}/_checkpoint")
      .trigger(processingTime="30 seconds")
      .foreachBatch(upsert_batch)
      .start()
)

query.awaitTermination()
```

---

## 4. Databricks **Job configuration** (UI)

| Field | Value |
|-------|-------|
| **Task type** | Python script |
| **Python file** | `dbfs:/FileStore/jobs/databricks_file_arrival_job.py` |
| **Parameters** | `{{s3_source}}`  *(you will fill this in the job definition)* |
| **Cluster** | All-Purpose (auto-terminate = 10 min) |
| **Schedule** | **None** – the job is **triggered by SNS**, not cron |

### How to set the parameter in the job definition

```json
{
  "name": "Telemetry File-Arrival Ingestion",
  "tasks": [
    {
      "task_key": "ingest",
      "python_wheel_task": { ... },
      "spark_python_task": {
        "python_file": "dbfs:/FileStore/jobs/databricks_file_arrival_job.py",
        "parameters": ["s3://my-bucket/raw/telemetry"]
      }
    }
  ],
  "triggers": {
    "file_arrival": {
      "file_patterns": ["*.jsonl"],
      "folder": "s3://my-bucket/raw/telemetry"
    }
  }
}
```

> **Databricks 13.3+ supports native `file_arrival` trigger** – you **don’t even need SNS** if you enable it in the UI.

---

## 5. Alternative: **Native Databricks File-Arrival Trigger** (no AWS SNS)

Databricks now offers **built-in file-arrival triggers** (DBR 13.3+):

1. **Jobs → Create Job → Trigger type → File arrival**  
2. **Folder**: `s3://my-bucket/raw/telemetry`  
 

The job **starts automatically** when a matching file appears.

**Your script still reads the path from `sys.argv[1]`** – **no duplication**.

---

## 6. Summary – **Zero duplication**

| Where the path lives | How it’s used |
|----------------------|---------------|
| **Job definition** (UI / JSON / CLI) | `parameters: ["s3://..."]` |
| **Python script** | `S3_SOURCE = sys.argv[1]` |
| **Auto Loader** | `.load(S3_SOURCE)` |
| **Checkpoint / Schema** | derived from `S3_SOURCE` |

> **Change the bucket/prefix?** → Edit **one line** in the job definition. Everything else updates automatically.

---

### TL;DR

1. **Put the S3 path in a Databricks Job parameter** (`sys.argv[1]`).  
2. **Use native `file_arrival` trigger** **or** **S3 → SNS → Databricks**.  
3. **Never hard-code the path in the script** – read it from the parameter. 



## How to specify S3 location for Trigger and PySpark code in single place only?

Below is a **complete, production-ready pattern** that lets you **declare the S3 location only once** and have it flow automatically into:

1. **Databricks file-arrival trigger** (the *Job* that wakes up when a new file lands)  
2. **Your PySpark script** (the code that actually reads the files)

---




> **Databricks 13.3+ supports native `file_arrival` trigger** – you **don’t even need SNS** if you enable it in the UI.

---

## 5. Alternative: **Native Databricks File-Arrival Trigger** (no AWS SNS)

Databricks now offers **built-in file-arrival triggers** (DBR 13.3+):

1. **Jobs → Create Job → Trigger type → File arrival**  
2. **Folder**: `s3://my-bucket/raw/telemetry`  


The job **starts automatically** when a matching file appears.

**Your script still reads the path from `sys.argv[1]`** – **no duplication**.

---

## 6. Summary – **Zero duplication**

| Where the path lives | How it’s used |
|----------------------|---------------|
| **Job definition** (UI / JSON / CLI) | `parameters: ["s3://..."]` |
| **Python script** | `S3_SOURCE = sys.argv[1]` |
| **Auto Loader** | `.load(S3_SOURCE)` |
| **Checkpoint / Schema** | derived from `S3_SOURCE` |

> **Change the bucket/prefix?** → Edit **one line** in the job definition. Everything else updates automatically.

---

### TL;DR

1. **Put the S3 path in a Databricks Job parameter** (`sys.argv[1]`).  
2. **Use native `file_arrival` trigger** **or** **S3 → SNS → Databricks**.  
3. **Never hard-code the path in the script** – read it from the parameter.  

You now have **one source of truth** and **zero duplication**.



## 1. Declare the location **once** – in a **Databricks Job parameter**

| UI | CLI | API |
|----|-----|-----|
| **Jobs → Edit → Parameters** | `databricks jobs configure --job-id <id> --json '{ "parameters": { "s3_source": "s3://my-bucket/raw/telemetry" } }'` | `POST /api/2.1/jobs/update` with `settings.parameters` |

> **Only one place to change** when the bucket/prefix moves.

---

## 2. Trigger the job **on file arrival** using **S3 Event → SNS → Databricks Job**

### Step-by-step (one-time)

| Step | What you do |
|------|-------------|
| **a.** Create an **SNS topic** (Databricks can do it for you – see below) |
| **b.** Configure **S3 bucket** → **Event Notification** → **SNS topic** on `*.jsonl` (or `*.gz`) |
| **c.** Give Databricks permission to **subscribe** to that topic and **run the job** |

```bash
# 1. Create SNS policy (run once)
aws sns create-topic --name databricks-file-arrival

# 2. S3 bucket event (via console or CLI)
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:123456789012:databricks-file-arrival",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": { "Key": { "FilterRules": [{ "Name": "suffix", "Value": ".jsonl" }]}}
    }]
  }'
```

> **Databricks will auto-subscribe** the first time you run the job with `cloudFiles.useNotifications=true`.

---



## 3. PySpark script – **read the parameter** (no hard-coded path)

```python
# -------------------------------------------------
#  databricks_file_arrival_job.py
# -------------------------------------------------
import sys
from pyspark.sql import functions as F

# ---------- 1. Get the S3 path from job parameter ----------
# Databricks injects parameters into sys.argv when you use "Parameters" in the UI
if len(sys.argv) < 2:
    raise ValueError("Missing required parameter: s3_source")
S3_SOURCE = sys.argv[1]                     # <-- ONLY ONE PLACE

# Optional: fallback for local testing
# S3_SOURCE = S3_SOURCE or "s3://my-bucket/raw/telemetry"

print(f"Job started for path: {S3_SOURCE}")

# ---------- 2. Auto Loader (file-notification mode) ----------
df = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{S3_SOURCE}/_schema")
        .option("cloudFiles.useNotifications", "true")   # <-- reacts to SNS
        .option("cloudFiles.maxFilesPerTrigger", "500")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(raw_schema)
        .load(S3_SOURCE)
        .withColumn("source_file", F.col("_metadata.file_path"))
)

# ---------- 3. Rest of your pipeline (transform → MERGE) ----------
# ... (same as before) ...

# ---------- 4. Start the stream ----------
query = (
    df.writeStream
      .option("checkpointLocation", f"{S3_SOURCE}/_checkpoint")
      .trigger(processingTime="30 seconds")
      .foreachBatch(upsert_batch)
      .start()
)

query.awaitTermination()
```

---

## 4. Databricks **Job configuration** (UI)

| Field | Value |
|-------|-------|
| **Task type** | Python script |
| **Python file** | `dbfs:/FileStore/jobs/databricks_file_arrival_job.py` |
| **Parameters** | `{{s3_source}}`  *(you will fill this in the job definition)* |
| **Cluster** | All-Purpose (auto-terminate = 10 min) |
| **Schedule** | **None** – the job is **triggered by SNS**, not cron |

### How to set the parameter in the job definition

```json
{
  "name": "Telemetry File-Arrival Ingestion",
  "tasks": [
    {
      "task_key": "ingest",
      "python_wheel_task": { ... },
      "spark_python_task": {
        "python_file": "dbfs:/FileStore/jobs/databricks_file_arrival_job.py",
        "parameters": ["s3://my-bucket/raw/telemetry"]
      }
    }
  ],
  "triggers": {
    "file_arrival": {
      "file_patterns": ["*.jsonl"],
      "folder": "s3://my-bucket/raw/telemetry"
    }
  }
}
```

## 🔍 **cloudFiles.useNotifications: True vs False**

This option controls **how Databricks Auto Loader discovers new files** in your S3 bucket.

---

## 📊 **Architecture Comparison**

### **useNotifications = true (Event-Driven)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. File arrives in S3                                      │
│     s3://chargeminder-2/data/file001.json                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. S3 sends event notification                             │
│     S3 Event → SNS Topic → SQS Queue                        │
│     (Auto Loader sets these up automatically)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Databricks polls SQS queue                              │
│     Gets instant notification: "file001.json arrived!"      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Databricks processes the file immediately               │
│     Latency: Seconds                                        │
└─────────────────────────────────────────────────────────────┘
```

**Requirements:**
- ✅ Storage Credential in Unity Catalog
- ✅ Permissions to create SNS/SQS resources
- ✅ S3 bucket permissions for notifications

---

### **useNotifications = false (Directory Listing)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. File arrives in S3                                      │
│     s3://chargeminder-2/data/file001.json                   │
└─────────────────────────────────────────────────────────────┘
                     
                     (File just sits there, no notification)
                     
┌─────────────────────────────────────────────────────────────┐
│  2. Databricks periodically lists S3 directory              │
│     s3.listObjectsV2("s3://chargeminder-2/data/")          │
│     Interval: Every few seconds to minutes                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Compares file list to previous scan                     │
│     New file detected: "file001.json"                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Databricks processes the file                           │
│     Latency: Seconds to minutes (depends on polling)        │
└─────────────────────────────────────────────────────────────┘
```

**Requirements:**
- ✅ Instance Profile with S3 ListBucket permission
- ✅ No Unity Catalog Storage Credential needed
- ✅ No SNS/SQS setup required

---

## ⚡ **Performance Comparison**

| Metric | useNotifications = **true** | useNotifications = **false** |
|--------|---------------------------|------------------------------|
| **Latency** | 1-5 seconds | 10 seconds - 5 minutes |
| **How it discovers files** | Event-driven (push) | Polling (pull) |
| **S3 API calls** | Minimal (only reads) | Frequent LIST operations |
| **S3 costs** | Lower | Higher (more LIST calls) |
| **Setup complexity** | High (needs Unity Catalog) | Low (just IAM role) |
| **Scalability** | Excellent (instant notification) | Good (but polls all paths) |
| **Works with** | Unity Catalog required | Instance profile only |

---

## 💰 **Cost Implications**

### **With Notifications (true):**
```
S3 Event Notifications: Free
SNS: ~$0.50 per million notifications
SQS: ~$0.40 per million requests
S3 LIST calls: Minimal

Example: 10,000 files/day
- SNS: $0.005/day
- SQS: $0.004/day
- Total: ~$0.01/day
```

### **Without Notifications (false):**
```
S3 LIST calls: $0.005 per 1,000 requests

Example: Polling every 30 seconds
- 2,880 LIST calls/day
- Cost: ~$0.014/day

With 100 subdirectories:
- 288,000 LIST calls/day
- Cost: ~$1.44/day
```

**For high-volume or many directories:** Notifications are cheaper ✅

---

## 🎯 **When to Use Each**

### **Use `useNotifications = true` when:**
- ✅ You need **low latency** (real-time processing)
- ✅ High file volume (thousands+ per day)
- ✅ Many subdirectories to monitor
- ✅ You have Unity Catalog configured
- ✅ Cost optimization matters

**Example use cases:**
- Real-time dashboards
- Streaming analytics
- IoT data ingestion
- Transaction processing

---

### **Use `useNotifications = false` when:**
- ✅ You **don't have Unity Catalog** Storage Credential
- ✅ Low to medium file volume (< 1,000/day)
- ✅ Latency of minutes is acceptable
- ✅ Simple setup preferred
- ✅ Few directories to monitor

**Example use cases:**
- Daily batch jobs
- Hourly data loads
- Development/testing
- Quick prototypes

---

## 🔧 **Code Examples**

### **Example 1: High-Performance Real-Time (Notifications)**

```python
# Real-time vehicle telemetry processing
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "true")  # Event-driven
  .option("cloudFiles.region", "us-east-1")
  .option("cloudFiles.queueUrl", "auto")  # Auto-creates SQS queue
  .load("s3://chargeminder-2/telemetry/"))

# Process and write
(df.writeStream
  .format("delta")
  .option("checkpointLocation", "/checkpoints/telemetry")
  .table("vehicle_telemetry"))
```

**Requirements:** Storage Credential must exist

---

### **Example 2: Simple Batch Processing (Directory Listing)**

```python
# Hourly batch processing - latency OK
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "false")  # Directory listing
  .option("cloudFiles.maxFilesPerTrigger", 1000)  # Throttle processing
  .load("s3://chargeminder-2/telemetry/"))

# Process and write
(df.writeStream
  .trigger(processingTime="10 minutes")  # Batch every 10 min
  .format("delta")
  .option("checkpointLocation", "/checkpoints/telemetry")
  .table("vehicle_telemetry"))
```

**Requirements:** Only instance profile needed

---

## 🐛 **Why Your Job Failed**

### **What Happened:**

```python
# Your file arrival trigger used this:
.option("cloudFiles.useNotifications", "true")
```

**Execution flow:**
1. ✅ File arrival trigger fires
2. ❌ Auto Loader tries to set up SNS/SQS
3. ❌ **Needs Storage Credential** to authenticate with AWS
4. ❌ Storage Credential doesn't exist
5. ❌ **Error: Unable to load AWS credentials**

### **With Scheduled Trigger:**

Your scheduled trigger likely either:
- Used `useNotifications = false` (directory listing)
- Or didn't use Auto Loader at all (regular `spark.read`)

That's why it worked - it only needed the instance profile, not a Storage Credential.

---

## 🎯 **Your Decision Matrix**

For your ChargeMinder use case:

| Scenario | Recommendation |
|----------|----------------|
| **Need it working TODAY** | `useNotifications = false` |
| **Processing < 1,000 files/day** | `useNotifications = false` |
| **Can wait for admin to create Storage Credential** | `useNotifications = true` |
| **Processing > 10,000 files/day** | `useNotifications = true` (get admin help) |
| **Need sub-second latency** | `useNotifications = true` (get admin help) |
| **Cost-sensitive, high volume** | `useNotifications = true` (get admin help) |

---

## 📝 **Summary**

```
useNotifications = true:
✅ Fast (seconds)
✅ Event-driven
✅ Cost-efficient at scale
❌ Requires Storage Credential (you don't have)
❌ Complex setup

useNotifications = false:
✅ Simple setup
✅ Works with instance profile only
✅ No Unity Catalog needed
⚠️ Slower (polling)
⚠️ More expensive at high scale
```

---

**For your immediate needs:** Use `false` to unblock yourself today, then work with your admin to set up Storage Credential for `true` later if you need better performance.

Does this help clarify the difference?
