
# Is polling DynamoDB tables  from Databricks   using DynamoDB Streams?

**It depends on the implementation** - the policies allow for both approaches:

## Two Ways to "Poll" DynamoDB from Databricks:

### 1. **Direct Table Access (Batch Reads)**
- Uses: `Scan`, `Query`, `GetItem`, `BatchGetItem`
- How it works: Databricks periodically reads data directly from the DynamoDB table
- Use case: Full table scans, point-in-time queries, batch ETL jobs
- **Not using DynamoDB Streams**

### 2. **DynamoDB Streams (Change Data Capture)**
- Uses: `DescribeStream`, `GetRecords`, `GetShardIterator`
- How it works: Databricks reads the stream of changes (inserts, updates, deletes) from DynamoDB
- Use case: Real-time or near-real-time data ingestion, incremental updates
- **This IS using DynamoDB Streams**

## What Your Policies Support:
Both policies grant permissions for **both approaches**:
- ✅ Direct table reads (`Query`, `Scan`, etc.)
- ✅ DynamoDB Streams reads (`GetRecords`, `GetShardIterator`, etc.)

## Determining Which is Used:
To know which approach Databricks is actually using, you'd need to check:
- The Databricks connector configuration
- The Spark code/notebooks being executed
- CloudTrail logs showing which API calls are being made

**Common pattern**: Many Databricks implementations use **DynamoDB Streams** for incremental/streaming workloads because it's more efficient than repeatedly scanning entire tables.





Excellent question — and the short answer is:

> **No, polling DynamoDB tables directly is *not* the same as consuming DynamoDB Streams.**
> They’re two distinct access patterns — often used together, but for different purposes.

Here’s the detailed breakdown:

---

### 1. **Polling DynamoDB tables**

**What it means:**
Your Databricks job periodically queries the table itself — for example, using `Query`, `Scan`, or `BatchGetItem` — to fetch data.

**Use case:**

* Periodic batch ingestion (e.g., every 5 min / 1 hour).
* When you don’t have Streams enabled or don’t care about near-real-time updates.
* You might filter on `updated_at` or a sequence key to pick up new records since the last run.

**Access required:**

* `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan`, etc.
* No need for any `DescribeStream` / `GetRecords` permissions.
* Reads go directly to the base table and consume standard **RCU** (Read Capacity Units).

**Pros / Cons:**

| Pros                          | Cons                                            |
| ----------------------------- | ----------------------------------------------- |
| Simpler setup                 | Inefficient — you re-scan or query large ranges |
| Works even if Streams are off | Higher cost for frequent polling                |
| Easy to schedule as batch     | Higher latency (not real time)                  |

---

### 2. **Consuming DynamoDB Streams**

**What it means:**
Instead of reading the table directly, you subscribe to **change events** emitted by DynamoDB whenever items are inserted, modified, or deleted.

**Use case:**

* Near-real-time CDC (Change Data Capture).
* Trigger downstream pipelines or Lambda functions.
* Stream ingestion into Databricks / Kinesis / S3 / Snowflake.

**Access required:**

* `dynamodb:DescribeStream`, `dynamodb:GetShardIterator`, `dynamodb:GetRecords`, and `dynamodb:ListStreams`.
* Streams must be **enabled** on each table.
* Reads consume **stream read capacity** (not RCU).

**Pros / Cons:**

| Pros                               | Cons                                  |
| ---------------------------------- | ------------------------------------- |
| Real-time incremental updates      | Requires enabling Streams per table   |
| Much lower data volume             | Can expire after 24 h if not consumed |
| Perfect for event-driven ingestion | More complex to integrate             |

---

### 3. **Typical Databricks Patterns**

In Databricks, you can implement either:

* **Batch polling** via `boto3` (Python) or the `spark-dynamodb` connector — simple, but periodic.
* **Stream consumption** using an intermediary:

  * AWS Lambda → Kinesis → S3 → Databricks Autoloader
  * or AWS DMS (Change Data Capture) → S3 → Delta ingestion

Databricks itself doesn’t natively subscribe to DynamoDB Streams directly — you’d usually integrate via **Kinesis** or **S3**.

---

### ✅ Recommendation for you

If your goal is:

* **Periodic table sync:** you only need the **read actions** (`GetItem`, `Query`, `Scan`).
* **Near-real-time incremental ingestion:** you need **Streams** (`DescribeStream`, `GetRecords`, etc.), but Databricks will probably read them indirectly via another AWS service (Lambda → Kinesis → S3).

---

Would you like me to show you an example **Databricks ingestion architecture** for DynamoDB Streams (CDC → S3 → Delta table)?
It’s a common production pattern and would clarify where Streams fit in.



# Polling DynamoDB directly from a Databricks job with boto3, 
but it’s usually only a good idea for **small/medium** tables and **simple** needs.   
For anything high-volume or near-real-time, Streams/Firehose or DMS → S3 → Auto Loader is far more robust.

Why polling is “simpler” but risky
- scan() is easy to write, but:
  - It reads in 1 MB pages (you must loop with LastEvaluatedKey).
  - It burns RCUs and can throttle; FilterExpression doesn’t reduce RCU cost (it filters after read).
  - There’s no built-in CDC; you must track a **watermark** yourself (e.g., updated_at).
  - Single-driver Python loops don’t scale like Spark streaming.
- query() is better than scan() if (and only if) you have a **GSI on updated_at** (or another monotonic change key) so you can pull “only new since T”.


### What is a GSI?

In DynamoDB, a **Global Secondary Index (GSI)** is an *alternate way to query a table* using a different key than the table’s primary key.

---

### DynamoDB Basics
- Every table has a **primary key**:
  - Partition key (hash key), or
  - Partition key + Sort key (composite).
- All queries are normally limited to this key schema.

If you want to query by another attribute (say `updated_at`), you need an **index**.

---

### What a GSI is
- A **Global Secondary Index** lets you define a **different partition/sort key** from the base table.
- It’s “global” because it spans all partitions of the table (not restricted like Local Secondary Indexes).
- You can project all or only some attributes into the index.
- After creation, DynamoDB automatically keeps the GSI in sync with the base table.

---

### Example
Suppose you have a table:

```text
Table: Orders
Primary Key: order_id (partition key)
Attributes: order_id, customer_id, updated_at, status
````

If you want to query “all orders where `updated_at > 2025-09-01`” → not possible efficiently, because `updated_at` is not part of the primary key.

**Solution**: Create a GSI.

```text
Index: updated_at_index
Partition key: dummy_hash (e.g., constant value or bucketed value)
Sort key: updated_at
Projected attributes: order_id, status, customer_id
```

Then you can `Query` by:

```python
table.query(
  IndexName="updated_at_index",
  KeyConditionExpression=Key("dummy_hash").eq("X") & Key("updated_at").gt("2025-09-01")
)
```

This lets you pull *only new items* since the last watermark.

---

## Why it matters for polling

If you rely on boto3 `scan()`:

* Reads everything (expensive, slow, throttling risk).

If you create a GSI on `updated_at`:

* You can `query()` for just “records after last checkpoint”.
* Much cheaper and scalable for incremental ingestion into Databricks.



Steps:

1) **Ensure a change key** exists on each table (e.g., `updated_at` ISO8601 or epoch seconds) that updates on every insert/update.
    
2) **Create a GSI** on `updated_at` (HASH or RANGE depending on design; commonly make it the sort key with a dummy/hash partition key so you can `Query` by a time window).
   
3) In Databricks, run a job every N minutes that:
   - Reads the last watermark from a small Delta checkpoint table.
   - Queries DynamoDB by `updated_at > watermark` (via the GSI), paginating with `LastEvaluatedKey`.
   - Writes results to **Delta Bronze** (append), then MERGE into **Silver**.

Minimal Databricks (Python) example using boto3 + GSI
(works for small/moderate rates; you can later pivot to Streams/Firehose without changing Bronze→Silver logic)

```python
# Databricks cluster needs: boto3 installed and AWS creds via instance profile / assumed role
import boto3, os, time
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from pyspark.sql import functions as F

TABLE_NAME = "your-table"
UPDATED_GSI = "updated_at_gsi"  # <- create this in DynamoDB
WATERMARK_TABLE = "chk.dynamodb_watermarks"  # small Delta table: (table STRING, watermark TIMESTAMP)
BRONZE_TABLE = "bronze.dynamodb_your_table"

# 1) Get last watermark
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {WATERMARK_TABLE} (table STRING, watermark TIMESTAMP) USING DELTA
""")
wm = (spark.table(WATERMARK_TABLE)
        .filter(F.col("table")==TABLE_NAME)
        .agg(F.max("watermark").alias("wm"))
        .collect()[0]["wm"])

# Default start watermark if none yet
if wm is None:
    # backfill a little, or set to epoch
    wm = datetime(1970,1,1,tzinfo=timezone.utc)

# 2) Query DynamoDB for items > watermark (via GSI)
session = boto3.Session()
dynamodb = session.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

items = []
last_evaluated_key = None
now_ts = datetime.now(timezone.utc)  # end watermark for this run
# Use a time window (wm, now_ts]; adapt KeyConditionExpression to your GSI schema
while True:
    kwargs = {
        "IndexName": UPDATED_GSI,
        "KeyConditionExpression": Key("updated_at").gt(wm.isoformat()),
        "Limit": 1000,  # tune
        "ConsistentRead": False,  # set True if you need it and can afford RCUs
    }
    if last_evaluated_key:
        kwargs["ExclusiveStartKey"] = last_evaluated_key
    resp = table.query(**kwargs)
    items.extend(resp.get("Items", []))
    last_evaluated_key = resp.get("LastEvaluatedKey")
    if not last_evaluated_key:
        break

# 3) Write to Bronze (append) if anything arrived
if items:
    # Convert to Spark DataFrame (schema inference for JSON-ish dicts is OK at small scale)
    df = spark.createDataFrame(items)
    df = (df
          .withColumn("_ingest_ts", F.current_timestamp())
          .withColumn("_source", F.lit(TABLE_NAME)))
    df.write.mode("append").format("delta").saveAsTable(BRONZE_TABLE)

# 4) Advance watermark (idempotent: use the "now" we captured at start)
spark.sql(f"""
MERGE INTO {WATERMARK_TABLE} t
USING (SELECT '{TABLE_NAME}' AS table, TIMESTAMP('{now_ts.isoformat()}') AS watermark) s
ON t.table = s.table
WHEN MATCHED THEN UPDATE SET t.watermark = s.watermark
WHEN NOT MATCHED THEN INSERT (table, watermark) VALUES (s.table, s.watermark)
""")
````

Silver merge (example)

```sql
-- assumes Bronze has a stable primary key column pk and updated_at
CREATE TABLE IF NOT EXISTS silver.your_table USING DELTA AS
SELECT * FROM (SELECT NULL AS pk) WHERE 1=0;

MERGE INTO silver.your_table s
USING (
  SELECT
    b.pk,
    b.*,
    b._ingest_ts
  FROM bronze.dynamodb_your_table b
) c
ON s.pk = c.pk
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
;
```

### When is this okay?

* Tables are modest in size and write rate.
* You control/guarantee an `updated_at` you can index and query by time.
* You accept occasional duplicates and resolve with upserts (MERGE).
* You’re fine managing backoff, pagination, and RCUs.

### When to avoid direct polling

* High write rates, large tables, or many tables → scanning/querying every few minutes will be costly, slow, and brittle.
* You need robust CDC, replay, and ordering semantics → use **DynamoDB Streams → Firehose/DMS → S3 → Auto Loader**.

If you want, I can:

* Show how to set up the **updated_at GSI** (key schema + throughput).
* Add **parallelism** (Segment/TotalSegments) for faster scans if you must scan.
* Swap the direct write to Bronze for **writing JSONL to S3**, then let **Auto Loader** ingest (more scalable).

 

## Implementation of the direct polling approach :


1. **Main Polling Script** (`dynamodb_polling` artifact):
   - Complete `DynamoDBPoller` class with checkpoint management
   - Automatic pagination handling
   - Configurable polling interval (default 1 minute)
   - Proper error logging
   - Both continuous and single-run modes

2. **Databricks Job Configuration** (`databricks_job_config` artifact):
   - JSON configuration for scheduling the job
   - Set to run every minute using cron expression
   - Includes cluster configuration with instance profile

3. **IAM Policies** (`iam_policies` artifact):
   - Complete trust and permission policies
   - AWS CLI commands for setup
   - Minimal required permissions for DynamoDB read access

4. **Advanced Features** (`advanced_polling` artifact):
   - Query-based loading (more efficient than Scan)
   - Data type conversion for DynamoDB types (Decimal, Set)
   - Deduplication logic
   - Merge/upsert functionality
   - Retry mechanisms
   - Data transformation examples

5. **Complete Setup Guide** (`setup_guide` artifact):
   - Step-by-step instructions
   - Testing procedures
   - Monitoring and optimization tips
   - Troubleshooting common issues
   - Production best practices

## Key Features:

- **Incremental Loading**: Uses checkpoint table to track last processed timestamp
- **Automatic Pagination**: Handles large result sets from DynamoDB
- **Error Handling**: Logging and retry logic included
- **Flexible Deployment**: Can run as continuous loop or scheduled job
- **Production Ready**: Includes monitoring, validation, and optimization code

The simplest way to get started is to copy the main polling script into a Databricks notebook,  
update the configuration parameters, 
and run it!


  
 
## Prerequisites
- DynamoDB table with a timestamp column (e.g., `created_at`)
- Databricks workspace on AWS
- AWS credentials with appropriate permissions


## Step 1: Configure AWS IAM

### 1.1 Create IAM Role

trust-policy.json

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Create the role
```
aws iam create-role \
  --role-name databricks-dynamodb-role \
  --assume-role-policy-document file://trust-policy.json
```

###  Attach Permissions

permission-policy.json
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_TABLE_NAME",
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_TABLE_NAME/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_DATABRICKS_BUCKET",
        "arn:aws:s3:::YOUR_DATABRICKS_BUCKET/*"
      ]
    }
  ]
}
```

### Attach policy to role
```
aws iam put-role-policy \
  --role-name databricks-dynamodb-role \
  --policy-name DynamoDBAccess \
  --policy-document file://permission-policy.json
```

### Create Instance Profile

```bash
# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name databricks-dynamodb-role

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name databricks-dynamodb-role \
  --role-name databricks-dynamodb-role

# Get the ARN (save this for Databricks)
aws iam get-instance-profile \
  --instance-profile-name databricks-dynamodb-role
```

## Step 2: Configure Databricks

### 2.1 Add Instance Profile to Databricks

1. Go to Databricks **Admin Console**
2. Navigate to **Instance Profiles**
3. Click **Add Instance Profile**
4. Enter the ARN: `arn:aws:iam::YOUR_ACCOUNT:instance-profile/databricks-dynamodb-role`
5. Click **Add**

### 2.2 Create a Notebook

1. Create a new notebook in Databricks
2. Copy the `DynamoDBPoller` code from the artifact
3. Update the configuration at the bottom:

```python
DYNAMODB_TABLE_NAME = "your-actual-table-name"
DYNAMODB_REGION = "us-east-1"  # Your region
DELTA_TABLE_PATH = "main.default.dynamodb_data"
CHECKPOINT_TABLE_PATH = "main.default.dynamodb_checkpoint"
TIMESTAMP_COLUMN = "created_at"  # Your timestamp column
POLL_INTERVAL = 60
```

### 2.3 Create Cluster with Instance Profile

Create a cluster with these settings:
- **Runtime**: DBR 13.3 LTS or later
- **Node type**: i3.xlarge (or as needed)
- **Workers**: 2-4 (based on data volume)
- **Advanced Options** → **Instances** → Select your instance profile

---

## Step 3: Test the Setup

### 3.1 Verify DynamoDB Access

Run this in a notebook cell:

```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('your-table-name')

# Try to describe the table
response = table.table_status
print(f"Table status: {response}")

# Try a small scan
response = table.scan(Limit=5)
print(f"Sample records: {len(response['Items'])}")
```

### 3.2 Test Single Poll

Run a single poll cycle:

```python
from dynamodb_poller import DynamoDBPoller

poller = DynamoDBPoller(
    dynamodb_table_name="your-table-name",
    dynamodb_region="us-east-1",
    delta_table_path="main.default.dynamodb_data",
    checkpoint_table_path="main.default.dynamodb_checkpoint",
    timestamp_column="created_at",
    poll_interval_seconds=60
)

# Run once to test
poller.poll_once()
```

### 3.3 Verify Delta Table

```python
# Check if data was written
df = spark.read.format("delta").table("main.default.dynamodb_data")
df.show()
df.count()

# Check checkpoint
checkpoint_df = spark.read.format("delta").table("main.default.dynamodb_checkpoint")
checkpoint_df.show()
```

## Step 4: Deploy Continuous Polling

You have three options for running continuous polling:

### Option 4.1: Databricks Job with Continuous Run

**Create Job via UI:**
1. Go to **Workflows** → **Jobs**
2. Click **Create Job**
3. Configure:
   - **Name**: "DynamoDB Continuous Polling"
   - **Task type**: Notebook
   - **Notebook path**: Select your notebook
   - **Cluster**: Select your cluster with instance profile
   - **Schedule**: Leave empty (we'll run continuously)
4. In the notebook, use:

```python
poller.start_continuous_polling()  # Runs indefinitely
```

### Option 4.2: Databricks Job with 1-Minute Schedule

**Better for production - automatic restarts and monitoring**

1. Create job as above
2. Set **Schedule**: 
   - **Trigger type**: Scheduled
   - **Schedule**: `* * * * *` (every minute using cron)
3. In the notebook, use:

```python
poller.poll_once()  # Runs once per job execution
```

**Job JSON Configuration:**
```json
{
  "name": "DynamoDB Polling Job",
  "schedule": {
    "quartz_cron_expression": "0 * * * * ?",
    "timezone_id": "UTC",
    "pause_status": "UNPAUSED"
  },
  "max_concurrent_runs": 1,
  "tasks": [{
    "task_key": "poll_dynamodb",
    "notebook_task": {
      "notebook_path": "/Users/your-email/DynamoDB_Poller"
    },
    "new_cluster": {
      "spark_version": "13.3.x-scala2.12",
      "node_type_id": "i3.xlarge",
      "num_workers": 2,
      "aws_attributes": {
        "instance_profile_arn": "arn:aws:iam::ACCOUNT:instance-profile/databricks-dynamodb-role"
      }
    }
  }]
}
```

### Option 4.3: Long-Running Cluster

Run on an always-on cluster:

```python
# In notebook with detached cluster
poller.start_continuous_polling()
```

**Note:** This is least recommended as it requires manual monitoring.

---

## Step 5: Monitor and Optimize

### 5.1 Add Monitoring

Create a monitoring notebook:

```python
from pyspark.sql.functions import col, count, max as spark_max, min as spark_min
from datetime import datetime, timedelta

# Check recent ingestion
df = spark.read.format("delta").table("main.default.dynamodb_data")

print("=== Ingestion Stats (Last 24 Hours) ===")
recent_df = df.filter(
    col("_ingestion_timestamp") >= datetime.now() - timedelta(hours=24)
)

stats = recent_df.agg(
    count("*").alias("record_count"),
    spark_min("_ingestion_timestamp").alias("first_ingestion"),
    spark_max("_ingestion_timestamp").alias("last_ingestion")
).collect()[0]

print(f"Records ingested: {stats['record_count']}")
print(f"First ingestion: {stats['first_ingestion']}")
print(f"Last ingestion: {stats['last_ingestion']}")

# Check for gaps in ingestion
print("\n=== Records per Hour (Last 24 Hours) ===")
from pyspark.sql.functions import date_trunc, count

hourly_df = (recent_df
    .withColumn("hour", date_trunc("hour", "_ingestion_timestamp"))
    .groupBy("hour")
    .agg(count("*").alias("records"))
    .orderBy("hour", ascending=False)
)
hourly_df.show(24)
```

### 5.2 Set Up Alerts

Create a notebook for alerts:

```python
from datetime import datetime, timedelta

# Check if data is being ingested
checkpoint_df = spark.read.format("delta").table("main.default.dynamodb_checkpoint")
last_checkpoint = checkpoint_df.select("checkpoint_time").first()[0]

time_since_last = datetime.now() - last_checkpoint
threshold_minutes = 5

if time_since_last.total_seconds() > (threshold_minutes * 60):
    print(f"ALERT: No data ingested for {time_since_last.total_seconds()/60:.1f} minutes!")
    # Send notification (email, Slack, PagerDuty, etc.)
else:
    print(f"✓ Data pipeline healthy. Last ingestion: {time_since_last.total_seconds()/60:.1f} minutes ago")
```

### 5.3 Optimize Performance

**For Large Tables (> 1M records):**

1. **Use Query Instead of Scan** (if possible):
   - Create a Global Secondary Index (GSI) on your timestamp column
   - Use the `AdvancedDynamoDBPoller` with query support

2. **Adjust Read Capacity**:
   - Monitor DynamoDB consumed capacity
   - Consider provisioned capacity if costs are high
   - Use on-demand mode for unpredictable workloads

3. **Optimize Databricks Cluster**:
   - Use Delta cache for faster reads
   - Enable auto-scaling for variable workloads
   - Use Spot instances for cost savings

```python
# Cluster configuration for optimization
spark.conf.set("spark.databricks.delta.properties.defaults.autoOptimize.optimizeWrite", "true")
spark.conf.set("spark.databricks.delta.properties.defaults.autoOptimize.autoCompact", "true")
```

4. **Partition Delta Table**:

```python
# When creating the table, partition by date
df.write.format("delta") \
    .partitionBy("ingestion_date") \
    .mode("append") \
    .saveAsTable("main.default.dynamodb_data")
```

### 5.4 Handle DynamoDB Types

If your DynamoDB table uses special types (Decimal, Set, Binary), add conversion:

```python
from decimal import Decimal

def convert_dynamodb_item(item):
    """Convert DynamoDB types to Spark-compatible types"""
    converted = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            converted[key] = float(value)
        elif isinstance(value, set):
            converted[key] = list(value)
        elif isinstance(value, bytes):
            converted[key] = value.decode('utf-8')
        else:
            converted[key] = value
    return converted

# Use before creating DataFrame
items = [convert_dynamodb_item(item) for item in raw_items]
df = spark.createDataFrame(items)
```

---

## Step 6: Troubleshooting

### Issue: "Access Denied" Error

**Solution:**
1. Verify instance profile is attached to cluster
2. Check IAM role permissions include your DynamoDB table ARN
3. Restart cluster after adding instance profile

```python
# Verify credentials
import boto3
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print(f"Current AWS Identity: {identity}")
```

### Issue: No New Records Detected

**Solution:**
1. Check timestamp format in DynamoDB vs. checkpoint
2. Verify timestamp column name matches
3. Reset checkpoint if needed:

```python
# Reset checkpoint to specific date
from datetime import datetime

checkpoint_df = spark.createDataFrame(
    [(datetime(2024, 1, 1), datetime.now())],
    ["last_processed_timestamp", "checkpoint_time"]
)
checkpoint_df.write.format("delta").mode("overwrite").saveAsTable("main.default.dynamodb_checkpoint")
```

### Issue: Scan is Slow

**Solutions:**
1. Use parallel scanning:

```python
# In the DynamoDBPoller class, modify _scan_dynamodb_incremental
def parallel_scan(self, last_timestamp, total_segments=4):
    """Perform parallel scan with multiple segments"""
    from concurrent.futures import ThreadPoolExecutor
    
    def scan_segment(segment):
        items = []
        response = self.table.scan(
            FilterExpression=f'#{self.timestamp_column} > :last_ts',
            ExpressionAttributeNames={f'#{self.timestamp_column}': self.timestamp_column},
            ExpressionAttributeValues={':last_ts': last_timestamp},
            Segment=segment,
            TotalSegments=total_segments
        )
        items.extend(response.get('Items', []))
        
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                FilterExpression=f'#{self.timestamp_column} > :last_ts',
                ExpressionAttributeNames={f'#{self.timestamp_column}': self.timestamp_column},
                ExpressionAttributeValues={':last_ts': last_timestamp},
                ExclusiveStartKey=response['LastEvaluatedKey'],
                Segment=segment,
                TotalSegments=total_segments
            )
            items.extend(response.get('Items', []))
        
        return items
    
    with ThreadPoolExecutor(max_workers=total_segments) as executor:
        results = executor.map(scan_segment, range(total_segments))
    
    all_items = []
    for segment_items in results:
        all_items.extend(segment_items)
    
    return all_items
```

2. Create GSI and use Query (recommended)

### Issue: High Costs

**Solutions:**
1. Reduce polling frequency (2-5 minutes instead of 1 minute)
2. Use DynamoDB on-demand pricing
3. Use smaller Databricks cluster
4. Enable cluster auto-termination

```python
# Adjust poll interval
POLL_INTERVAL = 120  # Poll every 2 minutes instead of 1
```

---

## Step 7: Production Best Practices

### 7.1 Data Quality Checks

```python
from pyspark.sql.functions import col, isnan, isnull

def validate_data(df):
    """Add data quality validation"""
    
    # Check for nulls in critical columns
    critical_cols = ['id', 'created_at']
    for col_name in critical_cols:
        null_count = df.filter(col(col_name).isNull()).count()
        if null_count > 0:
            print(f"WARNING: {null_count} null values in {col_name}")
    
    # Check for duplicates
    total_count = df.count()
    distinct_count = df.select('id').distinct().count()
    if total_count != distinct_count:
        print(f"WARNING: {total_count - distinct_count} duplicate records found")
    
    return df
```

### 7.2 Error Handling

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    poller.poll_once()
except Exception as e:
    logger.error(f"Polling failed: {e}", exc_info=True)
    # Send alert notification
    # Don't raise - let it retry on next cycle
```

### 7.3 Metrics Collection

```python
# Add to your polling code
metrics = {
    'poll_start_time': datetime.now(),
    'records_fetched': 0,
    'records_written': 0,
    'poll_duration_seconds': 0,
    'errors': []
}

# After successful poll
metrics['records_fetched'] = len(items)
metrics['poll_duration_seconds'] = (datetime.now() - metrics['poll_start_time']).total_seconds()

# Write metrics to a separate Delta table
metrics_df = spark.createDataFrame([metrics])
metrics_df.write.format("delta").mode("append").saveAsTable("main.default.polling_metrics")
```

---

## Summary

You now have a complete direct polling solution that:
- ✅ Polls DynamoDB every 1 minute
- ✅ Tracks processed records via checkpoint
- ✅ Writes incrementally to Delta Lake
- ✅ Handles errors and retries
- ✅ Can be monitored and scaled

For production use, consider upgrading to the DynamoDB Streams + Lambda architecture for true real-time processing and lower costs.

### IAM Policies
```json
{
  "iam_role_trust_policy": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  },
  
  "iam_permission_policy": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DynamoDBReadAccess",
        "Effect": "Allow",
        "Action": [
          "dynamodb:DescribeTable",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:BatchGetItem"
        ],
        "Resource": [
          "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/your-dynamodb-table",
          "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/your-dynamodb-table/index/*"
        ]
      },
      {
        "Sid": "S3AccessForDeltaLake",
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ],
        "Resource": [
          "arn:aws:s3:::your-databricks-bucket",
          "arn:aws:s3:::your-databricks-bucket/*"
        ]
      }
    ]
  },

  "setup_instructions": {
    "step_1": "Create IAM Role",
    "commands": [
      "aws iam create-role --role-name databricks-dynamodb-role --assume-role-policy-document file://trust-policy.json",
      "aws iam put-role-policy --role-name databricks-dynamodb-role --policy-name DynamoDBAccess --policy-document file://permission-policy.json"
    ],
    
    "step_2": "Create Instance Profile",
    "commands_2": [
      "aws iam create-instance-profile --instance-profile-name databricks-dynamodb-role",
      "aws iam add-role-to-instance-profile --instance-profile-name databricks-dynamodb-role --role-name databricks-dynamodb-role"
    ],
    
    "step_3": "Add to Databricks",
    "instructions": "In Databricks Admin Console -> Instance Profiles -> Add the ARN: arn:aws:iam::YOUR_ACCOUNT_ID:instance-profile/databricks-dynamodb-role"
  }
}
```

### Databricks json config

```json
{
  "name": "DynamoDB Polling Job",
  "email_notifications": {
    "on_failure": ["your-email@example.com"]
  },
  "timeout_seconds": 0,
  "max_concurrent_runs": 1,
  "tasks": [
    {
      "task_key": "poll_dynamodb",
      "notebook_task": {
        "notebook_path": "/Workspace/Users/your-user/dynamodb_poller",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "polling_cluster",
      "timeout_seconds": 0,
      "email_notifications": {}
    }
  ],
  "job_clusters": [
    {
      "job_cluster_key": "polling_cluster",
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 2,
        "aws_attributes": {
          "instance_profile_arn": "arn:aws:iam::YOUR_ACCOUNT:instance-profile/databricks-dynamodb-role",
          "availability": "SPOT_WITH_FALLBACK"
        },
        "spark_conf": {
          "spark.databricks.delta.preview.enabled": "true"
        }
      }
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 * * * * ?",
    "timezone_id": "UTC",
    "pause_status": "UNPAUSED"
  }
}
```

## Polls DynamoDB table every 1 minute and ingests new records into Delta Lake
 
```python
import boto3
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp
from delta.tables import DeltaTable
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DynamoDBPoller:
    """
    Polls DynamoDB table and writes new records to Delta Lake
    """
    
    def __init__(self, 
                 dynamodb_table_name,
                 dynamodb_region,
                 delta_table_path,
                 checkpoint_table_path,
                 timestamp_column='created_at',
                 poll_interval_seconds=60):
        """
        Initialize the DynamoDB poller
        
        Args:
            dynamodb_table_name: Name of the DynamoDB table
            dynamodb_region: AWS region of the DynamoDB table
            delta_table_path: Path to Delta Lake table (e.g., "catalog.schema.table")
            checkpoint_table_path: Path to checkpoint Delta table
            timestamp_column: Column name in DynamoDB that tracks record creation time
            poll_interval_seconds: How often to poll (default 60 seconds)
        """
        self.dynamodb_table_name = dynamodb_table_name
        self.dynamodb_region = dynamodb_region
        self.delta_table_path = delta_table_path
        self.checkpoint_table_path = checkpoint_table_path
        self.timestamp_column = timestamp_column
        self.poll_interval_seconds = poll_interval_seconds
        
        # Initialize Spark session
        self.spark = SparkSession.builder.getOrCreate()
        
        # Initialize DynamoDB resource
        self.dynamodb = boto3.resource('dynamodb', region_name=dynamodb_region)
        self.table = self.dynamodb.Table(dynamodb_table_name)
        
        # Initialize checkpoint table if it doesn't exist
        self._initialize_checkpoint_table()
    
    def _initialize_checkpoint_table(self):
        """Create checkpoint table if it doesn't exist"""
        try:
            # Check if checkpoint table exists
            self.spark.sql(f"DESCRIBE TABLE {self.checkpoint_table_path}")
            logger.info(f"Checkpoint table {self.checkpoint_table_path} exists")
        except:
            # Create checkpoint table
            checkpoint_df = self.spark.createDataFrame(
                [(datetime(2020, 1, 1), datetime.now())],
                ["last_processed_timestamp", "checkpoint_time"]
            )
            checkpoint_df.write.format("delta").mode("overwrite").saveAsTable(self.checkpoint_table_path)
            logger.info(f"Created checkpoint table {self.checkpoint_table_path}")
    
    def _get_last_processed_timestamp(self):
        """Retrieve the last processed timestamp from checkpoint table"""
        try:
            checkpoint_df = self.spark.read.format("delta").table(self.checkpoint_table_path)
            last_timestamp = checkpoint_df.agg({"last_processed_timestamp": "max"}).collect()[0][0]
            logger.info(f"Last processed timestamp: {last_timestamp}")
            return last_timestamp
        except Exception as e:
            logger.error(f"Error reading checkpoint: {e}")
            # Return a default old timestamp if checkpoint read fails
            return datetime(2020, 1, 1)
    
    def _save_checkpoint(self, timestamp):
        """Save the current processed timestamp to checkpoint table"""
        try:
            checkpoint_df = self.spark.createDataFrame(
                [(timestamp, datetime.now())],
                ["last_processed_timestamp", "checkpoint_time"]
            )
            checkpoint_df.write.format("delta").mode("overwrite").saveAsTable(self.checkpoint_table_path)
            logger.info(f"Checkpoint saved: {timestamp}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def _scan_dynamodb_incremental(self, last_timestamp):
        """
        Scan DynamoDB table for records newer than last_timestamp
        
        Args:
            last_timestamp: Only fetch records with timestamp > this value
            
        Returns:
            List of items from DynamoDB
        """
        items = []
        
        try:
            # Convert datetime to timestamp (assuming DynamoDB stores as Unix timestamp or ISO string)
            # Adjust the format based on how your DynamoDB stores timestamps
            if isinstance(last_timestamp, datetime):
                # If storing as Unix timestamp (number)
                last_ts_value = int(last_timestamp.timestamp())
                # If storing as ISO string, use: last_ts_value = last_timestamp.isoformat()
            else:
                last_ts_value = last_timestamp
            
            logger.info(f"Scanning DynamoDB for records after {last_ts_value}")
            
            # Initial scan with filter
            response = self.table.scan(
                FilterExpression=f'#{self.timestamp_column} > :last_ts',
                ExpressionAttributeNames={f'#{self.timestamp_column}': self.timestamp_column},
                ExpressionAttributeValues={':last_ts': last_ts_value}
            )
            
            items.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                logger.info(f"Fetching next page... (current items: {len(items)})")
                response = self.table.scan(
                    FilterExpression=f'#{self.timestamp_column} > :last_ts',
                    ExpressionAttributeNames={f'#{self.timestamp_column}': self.timestamp_column},
                    ExpressionAttributeValues={':last_ts': last_ts_value},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            logger.info(f"Fetched {len(items)} new records from DynamoDB")
            return items
            
        except Exception as e:
            logger.error(f"Error scanning DynamoDB: {e}")
            return []
    
    def _write_to_delta(self, items):
        """
        Write items to Delta Lake table
        
        Args:
            items: List of items from DynamoDB
        """
        if not items:
            logger.info("No new records to write")
            return
        
        try:
            # Convert items to Spark DataFrame
            df = self.spark.createDataFrame(items)
            
            # Add processing metadata
            df = df.withColumn("_ingestion_timestamp", current_timestamp())
            
            # Write to Delta Lake
            df.write.format("delta").mode("append").saveAsTable(self.delta_table_path)
            
            logger.info(f"Successfully wrote {len(items)} records to {self.delta_table_path}")
            
        except Exception as e:
            logger.error(f"Error writing to Delta Lake: {e}")
            raise
    
    def poll_once(self):
        """Execute one polling cycle"""
        try:
            logger.info("=" * 50)
            logger.info(f"Starting poll cycle at {datetime.now()}")
            
            # Get last processed timestamp
            last_timestamp = self._get_last_processed_timestamp()
            
            # Scan DynamoDB for new records
            items = self._scan_dynamodb_incremental(last_timestamp)
            
            # Write to Delta Lake
            if items:
                self._write_to_delta(items)
                
                # Update checkpoint with current time
                self._save_checkpoint(datetime.now())
            else:
                logger.info("No new records found")
            
            logger.info(f"Poll cycle completed at {datetime.now()}")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Error in poll cycle: {e}")
            raise
    
    def start_continuous_polling(self):
        """Start continuous polling loop"""
        logger.info(f"Starting continuous polling every {self.poll_interval_seconds} seconds")
        logger.info(f"DynamoDB Table: {self.dynamodb_table_name}")
        logger.info(f"Delta Table: {self.delta_table_path}")
        
        while True:
            try:
                self.poll_once()
                logger.info(f"Sleeping for {self.poll_interval_seconds} seconds...")
                time.sleep(self.poll_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Polling stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                logger.info(f"Retrying in {self.poll_interval_seconds} seconds...")
                time.sleep(self.poll_interval_seconds)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Configure your settings
    DYNAMODB_TABLE_NAME = "your-dynamodb-table"
    DYNAMODB_REGION = "us-east-1"
    DELTA_TABLE_PATH = "main.default.dynamodb_data"  # Or use path like "/mnt/delta/dynamodb_data"
    CHECKPOINT_TABLE_PATH = "main.default.dynamodb_checkpoint"
    TIMESTAMP_COLUMN = "created_at"  # Your timestamp column name in DynamoDB
    POLL_INTERVAL = 60  # Poll every 60 seconds
    
    # Initialize and start poller
    poller = DynamoDBPoller(
        dynamodb_table_name=DYNAMODB_TABLE_NAME,
        dynamodb_region=DYNAMODB_REGION,
        delta_table_path=DELTA_TABLE_PATH,
        checkpoint_table_path=CHECKPOINT_TABLE_PATH,
        timestamp_column=TIMESTAMP_COLUMN,
        poll_interval_seconds=POLL_INTERVAL
    )
    
    # Option 1: Run continuously
    poller.start_continuous_polling()
    
    # Option 2: Run once (useful for scheduled jobs)
    # poller.poll_once()
```    
### Advanced polling
```python
"""
Advanced features for DynamoDB polling including:
- Query-based incremental load (more efficient than Scan)
- Deduplication
- Data transformation
- Error handling and retry logic
"""

from pyspark.sql.functions import col, max as spark_max, sha2, concat_ws
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from decimal import Decimal
import boto3
from datetime import datetime


class AdvancedDynamoDBPoller:
    """
    Advanced DynamoDB poller with query-based incremental load
    Assumes your DynamoDB table has a GSI on timestamp column
    """
    
    def __init__(self, spark, dynamodb_table_name, region, delta_table_path, 
                 checkpoint_table_path, timestamp_column='created_at',
                 partition_key=None, sort_key=None, gsi_name=None):
        """
        Args:
            partition_key: Primary partition key name (if using Query)
            sort_key: Primary sort key name (if using Query)
            gsi_name: Global Secondary Index name that has timestamp as sort key
        """
        self.spark = spark
        self.dynamodb_table_name = dynamodb_table_name
        self.region = region
        self.delta_table_path = delta_table_path
        self.checkpoint_table_path = checkpoint_table_path
        self.timestamp_column = timestamp_column
        self.partition_key = partition_key
        self.sort_key = sort_key
        self.gsi_name = gsi_name
        
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(dynamodb_table_name)
    
    def query_by_timestamp(self, last_timestamp):
        """
        Query DynamoDB using GSI on timestamp (more efficient than Scan)
        
        This assumes you have a GSI with:
        - Partition key: A status field or constant value
        - Sort key: Your timestamp field
        """
        items = []
        
        if not self.gsi_name:
            raise ValueError("GSI name required for query-based polling")
        
        try:
            # Convert timestamp to appropriate format
            last_ts_value = int(last_timestamp.timestamp())
            
            # Query using GSI
            response = self.table.query(
                IndexName=self.gsi_name,
                KeyConditionExpression=f'#ts > :last_ts',
                ExpressionAttributeNames={'#ts': self.timestamp_column},
                ExpressionAttributeValues={':last_ts': last_ts_value}
            )
            
            items.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    IndexName=self.gsi_name,
                    KeyConditionExpression=f'#ts > :last_ts',
                    ExpressionAttributeNames={'#ts': self.timestamp_column},
                    ExpressionAttributeValues={':last_ts': last_ts_value},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            return items
            
        except Exception as e:
            print(f"Error querying DynamoDB: {e}")
            return []


def convert_dynamodb_types(item):
    """
    Convert DynamoDB specific types to Python types
    Handles Decimal, Set types, etc.
    """
    def convert_value(value):
        if isinstance(value, Decimal):
            # Convert Decimal to float or int
            return float(value) if value % 1 else int(value)
        elif isinstance(value, set):
            # Convert set to list
            return list(value)
        elif isinstance(value, dict):
            # Recursively convert nested dicts
            return {k: convert_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            # Recursively convert lists
            return [convert_value(v) for v in value]
        else:
            return value
    
    return {k: convert_value(v) for k, v in item.items()}


def deduplicate_records(spark, df, primary_keys):
    """
    Deduplicate records based on primary keys
    Keeps the latest version of each record
    
    Args:
        df: Spark DataFrame
        primary_keys: List of column names that form the primary key
    """
    from pyspark.sql.window import Window
    from pyspark.sql.functions import row_number, desc
    
    # Create window partitioned by primary keys, ordered by timestamp
    window = Window.partitionBy(*primary_keys).orderBy(desc("_ingestion_timestamp"))
    
    # Add row number and filter to keep only the first row in each partition
    deduped_df = (df
                  .withColumn("_row_num", row_number().over(window))
                  .filter(col("_row_num") == 1)
                  .drop("_row_num"))
    
    return deduped_df


def merge_to_delta(spark, new_df, delta_table_path, primary_keys):
    """
    Merge new records into Delta table (upsert operation)
    
    Args:
        new_df: DataFrame with new records
        delta_table_path: Path to Delta table
        primary_keys: List of columns that form the primary key
    """
    from delta.tables import DeltaTable
    
    # Check if Delta table exists
    if DeltaTable.isDeltaTable(spark, delta_table_path):
        delta_table = DeltaTable.forPath(spark, delta_table_path)
        
        # Build merge condition
        merge_condition = " AND ".join([f"target.{key} = source.{key}" for key in primary_keys])
        
        # Perform merge (upsert)
        (delta_table.alias("target")
         .merge(new_df.alias("source"), merge_condition)
         .whenMatchedUpdateAll()
         .whenNotMatchedInsertAll()
         .execute())
        
        print(f"Merged records into {delta_table_path}")
    else:
        # Create new table if it doesn't exist
        new_df.write.format("delta").mode("overwrite").save(delta_table_path)
        print(f"Created new Delta table at {delta_table_path}")


def transform_data(df):
    """
    Apply transformations to the data
    Add your custom business logic here
    """
    from pyspark.sql.functions import to_timestamp, current_timestamp
    
    # Example transformations
    transformed_df = df
    
    # Convert timestamp column if needed
    if 'created_at' in df.columns:
        transformed_df = transformed_df.withColumn(
            'created_at_ts',
            to_timestamp(col('created_at'))
        )
    
    # Add processing timestamp
    transformed_df = transformed_df.withColumn(
        '_processing_timestamp',
        current_timestamp()
    )
    
    # Add data quality checks
    # Example: Flag records with missing required fields
    required_fields = ['id', 'created_at']
    for field in required_fields:
        if field in df.columns:
            transformed_df = transformed_df.withColumn(
                f'_{field}_is_null',
                col(field).isNull()
            )
    
    return transformed_df


def poll_with_retry(poller_func, max_retries=3, retry_delay=5):
    """
    Execute polling function with retry logic
    
    Args:
        poller_func: Function to execute
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return poller_func()
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Raising exception.")
                raise


# ============================================================================
# USAGE EXAMPLE WITH ADVANCED FEATURES
# ============================================================================

def main():
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder.getOrCreate()
    
    # Initialize poller with Query support
    poller = AdvancedDynamoDBPoller(
        spark=spark,
        dynamodb_table_name="your-table",
        region="us-east-1",
        delta_table_path="/mnt/delta/dynamodb_data",
        checkpoint_table_path="/mnt/delta/dynamodb_checkpoint",
        timestamp_column="created_at",
        gsi_name="timestamp-index"  # Your GSI name
    )
    
    # Get last timestamp
    last_ts = datetime(2024, 1, 1)  # Get from checkpoint
    
    # Query with retry
    items = poll_with_retry(
        lambda: poller.query_by_timestamp(last_ts),
        max_retries=3
    )
    
    if items:
        # Convert DynamoDB types
        converted_items = [convert_dynamodb_types(item) for item in items]
        
        # Create DataFrame
        df = spark.createDataFrame(converted_items)
        
        # Transform data
        transformed_df = transform_data(df)
        
        # Deduplicate
        deduped_df = deduplicate_records(spark, transformed_df, primary_keys=['id'])
        
        # Merge to Delta Lake (upsert)
        merge_to_delta(
            spark,
            deduped_df,
            "/mnt/delta/dynamodb_data",
            primary_keys=['id']
        )
        
        print(f"Successfully processed {len(items)} records")


if __name__ == "__main__":
    main()
```



### ChatGPT

**No, you do NOT need a GSI for this code** - but that's actually part of the problem!

Let me explain:

---

## Why No GSI is Needed (But It Doesn't Help Either)

Your current code uses **`scan()`** with a `FilterExpression`:

```python
scan_kwargs = {
    'FilterExpression': 'recorded_at > :last_ts',
    'ExpressionAttributeValues': {':last_ts': last_timestamp}
}
```

**`scan()` doesn't use indexes at all** - it reads the entire table regardless of whether you have a GSI or not. The `FilterExpression` only filters *after* reading all the data.

---

## The Problem with Your Current Approach

Given your keys:
- **Partition Key (HASH)**: `user_id`
- **Sort Key (RANGE)**: `recorded_at`

Your `scan()` approach:
1. ❌ Reads **every single item** in the table
2. ❌ Then filters by `recorded_at > last_timestamp`
3. ❌ You pay for reading ALL items, even old ones
4. ❌ Very slow and expensive

**Example:** If you have 1 million items and only 1,000 are new:
- Scan reads: 1,000,000 items 💸
- Filter keeps: 1,000 items
- **You pay for 1 million reads!**

---

## Should You Create a GSI?

### Option 1: Create a GSI on `recorded_at` ✅ **Recommended**

**Create this GSI:**
```json
{
  "IndexName": "recorded_at-index",
  "KeySchema": [
    {
      "AttributeName": "recorded_at",
      "KeyType": "HASH"
    }
  ],
  "Projection": {
    "ProjectionType": "ALL"
  }
}
```

**Then modify your code to use `query()` instead of `scan()`:**

```python
def incremental_load_dynamodb(table_name):
    """
    Load incremental data from DynamoDB to Delta Lake using GSI
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Get last processed timestamp
    last_timestamp = get_last_processed_timestamp(table_name)
    print(f"Processing {table_name} from {last_timestamp}")
    
    items = []
    
    # Query the GSI instead of scanning
    # This only reads items with recorded_at > last_timestamp
    query_kwargs = {
        'IndexName': 'recorded_at-index',
        'KeyConditionExpression': 'recorded_at > :last_ts',
        'ExpressionAttributeValues': {':last_ts': last_timestamp}
    }
    
    try:
        response = table.query(**query_kwargs)
        items.extend(response['Items'])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = table.query(**query_kwargs)
            items.extend(response['Items'])
            
        print(f"Found {len(items)} new records in {table_name}")
        
        if items:
            df = spark.createDataFrame(items)
            df.createOrReplaceTempView("new_data")
            
            spark.sql(f"""
                MERGE INTO {table_name}_delta as target
                USING new_data as source
                ON target.user_id = source.user_id 
                   AND target.recorded_at = source.recorded_at
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)
            
            print(f"Successfully loaded {len(items)} records to {table_name}_delta")
        else:
            print(f"No new records for {table_name}")
            
    except Exception as e:
        print(f"Error processing {table_name}: {str(e)}")
        raise
```

**Wait, there's a problem!** ⚠️

GSI with `recorded_at` as HASH key means you can only query **exact matches**, not ranges (`>`). 

---

## Better GSI Design

**Create a GSI with a dummy partition key + `recorded_at` as sort key:**

```json
{
  "IndexName": "all-by-time-index",
  "KeySchema": [
    {
      "AttributeName": "record_type",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "recorded_at",
      "KeyType": "RANGE"
    }
  ],
  "Projection": {
    "ProjectionType": "ALL"
  }
}
```

**Then add a `record_type` attribute to all items:**

```python
# When writing to DynamoDB, add this attribute
item = {
    'user_id': 'user123',
    'recorded_at': '2025-10-01T12:00:00',
    'record_type': 'event',  # Same value for all items in this table
    # ... other attributes
}
```

**Query using the GSI:**

```python
query_kwargs = {
    'IndexName': 'all-by-time-index',
    'KeyConditionExpression': 'record_type = :type AND recorded_at > :last_ts',
    'ExpressionAttributeValues': {
        ':type': 'event',  # Same value for all items
        ':last_ts': last_timestamp
    }
}
```

This works because:
- All items have the same `record_type` (acts as a single partition)
- `recorded_at` is the sort key, so range queries work
- Only reads items with `recorded_at > last_timestamp` ✅

---

## Cost Comparison

**Without GSI (current scan approach):**
- Table has 1M items, 1KB each
- Every scan: 1M reads = $0.25
- Running every 5 minutes: 288 scans/day = **$72/day** 💸

**With GSI (query approach):**
- Only 10K new items per scan
- Every query: 10K reads = $0.0025
- Running every 5 minutes: 288 queries/day = **$0.72/day** ✅

**Savings: 99% reduction in cost!**

---

## My Recommendation: Skip GSI, Use DynamoDB Streams

Instead of creating a GSI and modifying your scan code, **use DynamoDB Streams** (the Lambda + S3 approach we discussed earlier):

### Why Streams is Better:
1. ✅ **Real-time** - get changes as they happen
2. ✅ **No scanning** - only changed items are sent
3. ✅ **Cheaper** - only pay for actual changes
4. ✅ **No GSI needed** - works with existing table structure
5. ✅ **More reliable** - guaranteed delivery of all changes

### Comparison:

| Approach | Cost (1M items, 10K changes/day) | Latency | Complexity |
|----------|----------------------------------|---------|------------|
| **Scan (current)** | $72/day 💸 | 5 min | Low |
| **GSI + Query** | $0.72/day | 5 min | Medium |
| **Streams + Lambda** | $0.02/day ✅ | Real-time | Medium |

---

## Final Answer

**Do you need a GSI?**
- ❌ No, for your current `scan()` code
- ✅ Yes, if you want to use `query()` for better performance
- 🎯 But honestly, **use DynamoDB Streams instead** - it's the best solution

**If you must stick with scanning:**
1. Create the GSI with `record_type` (HASH) + `recorded_at` (RANGE)
2. Add `record_type` attribute to all items
3. Modify code to use `query()` instead of `scan()`

**Better solution:**
Use the DynamoDB Streams + Lambda + S3 + Databricks approach we discussed earlier. It's cheaper, faster, and more scalable.

## GROK

The provided code is a PySpark script that incrementally loads data from a DynamoDB table into a Delta Lake table in Databricks, using a Global Secondary Index (GSI) for efficient querying. Below is a detailed review of the code, covering its structure, functionality, potential improvements, and best practices.

### **Overall Assessment**
The code is well-structured and follows a logical flow for incremental data loading from DynamoDB to Delta Lake. It uses a checkpoint mechanism to track the last processed timestamp, queries DynamoDB using a GSI, handles pagination, converts DynamoDB-specific data types (e.g., `Decimal`), and performs an upsert operation using Delta Lake's `MERGE` command. However, there are areas for improvement in terms of robustness, performance, and maintainability.

### **Detailed Review**

#### **1. Functionality and Correctness**
- **Purpose**: The script incrementally loads data from a DynamoDB table into a Delta Lake table in Databricks, using a GSI (`all-records-by-time-index`) to query records based on `record_type` (hash key) and `recorded_at` (range key) after the last processed timestamp.
- **Key Components**:
  - `get_last_processed_timestamp`: Retrieves the maximum `recorded_at` timestamp from the Delta table to determine the starting point for incremental loading.
  - `incremental_load_dynamodb`: Queries DynamoDB, processes the results, converts data types, creates a DataFrame, and merges it into the Delta table.
- **Correctness**:
  - The use of `KeyConditionExpression` with `Key('record_type').eq('ALL') & Key('recorded_at').gt(last_timestamp)` is correct for querying a GSI.
  - Pagination is handled properly using `LastEvaluatedKey`.
  - The `MERGE` operation correctly handles upserts based on `user_id` and `recorded_at`.
  - The script accounts for DynamoDB's `Decimal` type by converting it to Python `int` or `float`.

#### **2. Strengths**
- **Checkpoint Mechanism**: Using the maximum `recorded_at` timestamp from the Delta table as a checkpoint is a good approach for incremental loading.
- **Error Handling**: The script includes try-catch blocks to handle exceptions and prints error messages with stack traces, which aids debugging.
- **Type Conversion**: The `convert_decimals` function appropriately handles DynamoDB's `Decimal` type to ensure compatibility with Spark.
- **Delta Lake Integration**: The use of Delta Lake's `MERGE` command ensures idempotent upserts, which is ideal for handling incremental updates.
- **Pagination**: The code correctly handles DynamoDB's paginated responses using `LastEvaluatedKey`.

#### **3. Potential Issues**
1. **Hardcoded Values**:
   - The GSI name (`all-records-by-time-index`) and `record_type` value (`ALL`) are hardcoded. These should be configurable (e.g., via function arguments or a configuration file) to make the code reusable across different tables or GSIs.
   - The default timestamp (`1970-01-01T00:00:00`) assumes a specific format, which may not match the `recorded_at` format in DynamoDB.
2. **Schema Assumptions**:
   - The script assumes specific columns (`user_id`, `recorded_at`, `data`) in the DynamoDB table and Delta table. If the schema varies, the code will fail.
   - The Delta table schema (`data MAP<STRING, STRING>`) assumes `data` is a key-value map. If the `data` field has a different structure, this will cause issues.
3. **Error Handling in `get_last_processed_timestamp`**:
   - If the Delta table doesn’t exist, the `spark.sql` query will fail, and the fallback to the epoch timestamp may not be ideal. It would be better to check if the table exists first.
4. **Performance Concerns**:
   - Querying DynamoDB with a GSI can be expensive if the table or index is large, especially with a broad condition like `record_type = 'ALL'`. Consider adding a filter to reduce the number of records scanned.
   - The `convert_decimals` function processes all items in memory, which could be problematic for very large datasets.
   - The `MERGE` operation may be slow for large datasets if not optimized (e.g., no partitioning or Z-ordering on the Delta table).
5. **Logging and Monitoring**:
   - The script uses `print` statements for logging, which is not ideal in a production environment. Structured logging (e.g., using Python’s `logging` module or Databricks’ logging) would be better.
   - There’s no mechanism to track metrics (e.g., number of records processed, query latency).
6. **Security**:
   - AWS credentials are not explicitly configured in the code. Ensure they are securely provided (e.g., via Databricks secrets or IAM roles).
7. **Table Creation**:
   - The `CREATE TABLE` statement is executed every time, which is unnecessary if the table already exists. It should be separated into an initialization step.
   - The schema is hardcoded and may not match the actual DynamoDB data.

#### **4. Recommendations for Improvement**
1. **Make Configuration Flexible**:
   - Pass GSI name, `record_type` value, and table schema as parameters or load them from a configuration file.
   - Example:
     ```python
     def incremental_load_dynamodb(table_name, gsi_name, record_type='ALL', region_name='us-east-1', schema=None):
         ...
     ```

2. **Validate Table Existence**:
   - Check if the Delta table exists before querying it in `get_last_processed_timestamp`.
   - Example:
     
     ```python
     def get_last_processed_timestamp(table_name):
         try:
             if spark.catalog.tableExists(f"{table_name}_delta"):
                 checkpoint_df = spark.sql(f"SELECT MAX(recorded_at) as last_timestamp FROM {table_name}_delta")
                 last_ts = checkpoint_df.first()['last_timestamp']
                 return last_ts if last_ts else '1970-01-01T00:00:00'
             else:
                 print(f"Table {table_name}_delta does not exist, starting from epoch")
                 return '1970-01-01T00:00:00'
         except Exception as e:
             print(f"Error checking checkpoint: {str(e)}")
             return '1970-01-01T00:00:00'
     ```

3. **Dynamic Schema Handling**:
   - Infer the schema from the DynamoDB items or allow the user to specify it.
   - Example using inferred schema:
     ```python
     if items:
         df = spark.createDataFrame(items)
         # Dynamically create Delta table with inferred schema
         df.write(f"{table_name}_delta", format="delta", mode="overwrite")
     ```

4. **Optimize DynamoDB Queries**:
   - Add a `FilterExpression` to reduce the amount of data scanned if possible.
   - Example:
     
     ```python
     response = table.query(
         IndexName='all-records-by-time-index',
         KeyConditionExpression=Key('record_type').eq('ALL') & Key('recorded_at').gt(last_timestamp),
         FilterExpression=Attr('some_field').exists(),  # Example filter
         ProjectionExpression='user_id, recorded_at, #data',
         ExpressionAttributeNames={'#data': 'data'}
     )
     ```

5. **Improve Performance**:
   - Partition the Delta table by a high-cardinality column (e.g., `recorded_at` truncated to date) to improve `MERGE` performance.
   - Example:
     ```python
     spark.sql(f"""
         CREATE TABLE IF NOT EXISTS {table_name}_delta (
             user_id STRING,
             recorded_at STRING,
             data MAP<STRING, STRING>,
             partition_date STRING
         )
         USING DELTA
         PARTITIONED BY (partition_date)
     """)
     df = df.withColumn("partition_date", df.recorded_at.substr(1, 10))
     ```

   - Use Z-ordering for frequently queried columns:
     ```python
     spark.sql(f"OPTIMIZE {table_name}_delta ZORDER BY (user_id, recorded_at)")
     ```

6. **Structured Logging**:
   - Replace `print` statements with a logging framework.
   - Example:
     ```python
     import logging
     logging.basicConfig(level=logging.INFO)
     logger = logging.getLogger(__name__)
     logger.info(f"Processing {table_name} from {last_timestamp}")
     ```

7. **Handle Large Datasets**:
   - Process items in batches to avoid memory issues during `convert_decimals`.
   - Example:
     ```python
     def process_in_batches(items, batch_size=1000):
         for i in range(0, len(items), batch_size):
             batch = items[i:i + batch_size]
             yield [convert_decimals(item) for item in batch]
     ```

8. **Add Metrics**:
   - Track metrics like the number of records processed, query time, and merge time using Databricks’ metrics or a custom solution.
   - Example:
     ```python
     from time import time
     start_time = time()
     # Query and process
     query_time = time() - start_time
     logger.info(f"Query took {query_time:.2f} seconds")
     ```

9. **Separate Table Creation**:
   - Move the `CREATE TABLE` logic to a separate initialization script to avoid redundant execution.
   - Example:
     ```python
     def initialize_delta_table(table_name, schema_definition):
         spark.sql(f"""
             CREATE TABLE IF NOT EXISTS {table_name}_delta ({schema_definition})
             USING DELTA
         """)
     ```

10. **Validate Timestamp Format**:
    - Ensure the `recorded_at` format in DynamoDB matches the expected format in the Delta table. Add validation or parsing logic if needed.

#### **5. Security Considerations**
- **AWS Credentials**: Ensure AWS credentials are securely configured (e.g., via Databricks secrets or an IAM role attached to the cluster).
- **Data Sensitivity**: If the DynamoDB table contains sensitive data, ensure proper encryption and access controls are in place.
- **ProjectionExpression**: The use of `ProjectionExpression` is good for reducing data transfer, but ensure all necessary fields are included.

#### **6. Example Refactored Code Snippet**
Here’s a partial refactored version incorporating some of the recommendations:

```python
import logging
from datetime import datetime
from pyspark.sql import SparkSession
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_last_processed_timestamp(spark, table_name):
    try:
        if spark.catalog.tableExists(f"{table_name}_delta"):
            checkpoint_df = spark.sql(f"SELECT MAX(recorded_at) as last_timestamp FROM {table_name}_delta")
            last_ts = checkpoint_df.first()['last_timestamp']
            return last_ts if last_ts else '1970-01-01T00:00:00'
        else:
            logger.info(f"Table {table_name}_delta does not exist, starting from epoch")
            return '1970-01-01T00:00:00'
    except Exception as e:
        logger.error(f"Error checking checkpoint: {str(e)}")
        return '1970-01-01T00:00:00'

def incremental_load_dynamodb(spark, table_name, gsi_name, record_type='ALL', region_name='us-east-1'):
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)
    
    last_timestamp = get_last_processed_timestamp(spark, table_name)
    logger.info(f"Processing {table_name} from {last_timestamp}")
    
    items = []
    try:
        response = table.query(
            IndexName=gsi_name,
            KeyConditionExpression=Key('record_type').eq(record_type) & Key('recorded_at').gt(last_timestamp),
            ProjectionExpression='user_id, recorded_at, #data',
            ExpressionAttributeNames={'#data': 'data'}
        )
        items.extend(response['Items'])
        
        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName=gsi_name,
                KeyConditionExpression=Key('record_type').eq(record_type) & Key('recorded_at').gt(last_timestamp),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
            
        logger.info(f"Found {len(items)} new records in {table_name}")
        
        if items:
            from decimal import Decimal
            def convert_decimals(obj):
                if isinstance(obj, list):
                    return [convert_decimals(i) for i in obj]
                elif isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, Decimal):
                    return float(obj) if obj % 1 else int(obj)
                else:
                    return obj
            
            items = [convert_decimals(item) for item in items]
            df = spark.createDataFrame(items)
            df = df.withColumn("partition_date", df.recorded_at.substr(1, 10))
            df.createOrReplaceTempView("new_data")
            
            # Merge data
            spark.sql(f"""
                MERGE INTO {table_name}_delta as target
                USING new_data as source
                ON target.user_id = source.user_id 
                   AND target.recorded_at = source.recorded_at
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)
            
            logger.info(f"Successfully loaded {len(items)} records to {table_name}_delta")
        else:
            logger.info(f"No new records for {table_name}")
            
    except Exception as e:
        logger.error(f"Error processing {table_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# Example usage
spark = SparkSession.builder.appName("DynamoDBToDelta").getOrCreate()
incremental_load_dynamodb(spark, table_name="my_table", gsi_name="all-records-by-time-index")
```

### **Summary**
The code is functional and follows a solid approach for incremental data loading from DynamoDB to Delta Lake. However, it can be improved by:
- Making configurations (e.g., GSI name, schema) flexible.
- Enhancing error handling and logging.
- Optimizing performance with partitioning and batch processing.
- Adding metrics and security best practices.

Great question! Let me show you how to securely access DynamoDB from Databricks. There are several approaches depending on where your Databricks is hosted.

---

### **Solution Overview**

You need to:
1. **Create AWS IAM credentials** (Role or User) with DynamoDB read permissions
2. **Configure Databricks** to use these credentials
3. **Read DynamoDB data** using Spark in Databricks

 

### **Option 1: IAM User with Access Keys (Simplest)**

This works for any Databricks deployment (AWS, Azure, or GCP).

## **Step 1: Create IAM Policy for DynamoDB Read Access**

In AWS Console:

1. Go to **IAM** → **Policies** → **Create policy**
2. Click **JSON** tab
3. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBReadAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:DescribeStream",
                "dynamodb:GetRecords",
                "dynamodb:GetShardIterator",
                "dynamodb:ListStreams"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:123456789012:table/YourTableName",
                "arn:aws:dynamodb:us-east-1:123456789012:table/YourTableName/stream/*"
            ]
        },
        {
            "Sid": "ListTables",
            "Effect": "Allow",
            "Action": [
                "dynamodb:ListTables"
            ],
            "Resource": "*"
        }
    ]
}
```

**Customize:**
- Replace `us-east-1` with your region
- Replace `123456789012` with your AWS account ID
- Replace `YourTableName` with your table name
- For all tables, use: `"Resource": "arn:aws:dynamodb:*:*:table/*"`

4. Click **Next**
5. **Name**: `DatabricksDynamoDBReadPolicy`
6. **Description**: "Read-only access to DynamoDB tables for Databricks"
7. Click **Create policy**

## **Step 2: Create IAM User**

1. Go to **IAM** → **Users** → **Create user**
2. **User name**: `databricks-dynamodb-reader`
3. Click **Next**
4. **Attach policies directly**
5. Search and select: `DatabricksDynamoDBReadPolicy`
6. Click **Next** → **Create user**

## **Step 3: Create Access Keys**

1. Click on the user you just created
2. Go to **Security credentials** tab
3. Scroll to **Access keys** section
4. Click **Create access key**
5. Select use case: **Application running outside AWS**
6. Click **Next**
7. Description: "Databricks DynamoDB access"
8. Click **Create access key**
9. **⚠️ Copy both:**
   - **Access Key ID** (e.g., `AKIAIOSFODNN7EXAMPLE`)
   - **Secret Access Key** (e.g., `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)
10. **Download .csv file** (you won't see the secret again!)

## **Step 4: Configure Databricks Secret Scope**

### **Create Secret Scope (Databricks-backed):**

```python
# In Databricks notebook
from databricks.sdk.runtime import *

# Create secret scope (run once)
# Note: Use Databricks CLI or UI for this
```

**Better: Use Databricks UI or CLI:**

#### **Via Databricks UI:**
1. Go to your Databricks workspace
2. Navigate to: `https://<databricks-instance>/#secrets/createScope`
3. **Scope Name**: `aws-dynamodb`
4. **Manage Principal**: Choose who can manage
5. Click **Create**

#### **Via Databricks CLI:**

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure
databricks configure --token

# Create secret scope
databricks secrets create-scope --scope aws-dynamodb

# Add secrets
databricks secrets put --scope aws-dynamodb --key aws-access-key-id
# (Opens editor, paste the Access Key ID, save and exit)

databricks secrets put --scope aws-dynamodb --key aws-secret-access-key
# (Opens editor, paste the Secret Access Key, save and exit)
```

## **Step 5: Read DynamoDB from Databricks**

### **Method A: Using AWS SDK (boto3)**

```python
# Install boto3 if not available
%pip install boto3

import boto3
from pyspark.sql import SparkSession

# Get credentials from Databricks secrets
aws_access_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-access-key-id")
aws_secret_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-secret-access-key")
region = "us-east-1"  # Your AWS region

# Create DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    region_name=region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

# Read table
table = dynamodb.Table('YourTableName')

# Scan table (for small tables)
response = table.scan()
items = response['Items']

# Handle pagination for large tables
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

# Convert to Spark DataFrame
from pyspark.sql import Row

spark_data = [Row(**item) for item in items]
df = spark.createDataFrame(spark_data)

display(df)
```

### **Method B: Using Spark DynamoDB Connector**

```python
# Configure Spark to use AWS credentials
spark.conf.set("spark.hadoop.fs.s3a.access.key", 
               dbutils.secrets.get(scope="aws-dynamodb", key="aws-access-key-id"))
spark.conf.set("spark.hadoop.fs.s3a.secret.key", 
               dbutils.secrets.get(scope="aws-dynamodb", key="aws-secret-access-key"))

# Read DynamoDB using Spark connector
# Note: Requires DynamoDB connector JAR

df = spark.read \
    .format("dynamodb") \
    .option("tableName", "YourTableName") \
    .option("region", "us-east-1") \
    .load()

display(df)
```

### **Method C: Export to S3 then Read (Best for Large Tables)**

```python
import boto3
from datetime import datetime

# Get credentials
aws_access_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-access-key-id")
aws_secret_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-secret-access-key")

# DynamoDB client
dynamodb = boto3.client(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

# Export table to S3 (requires additional IAM permissions)
s3_bucket = "your-bucket"
s3_prefix = f"dynamodb-exports/{datetime.now().strftime('%Y%m%d')}"

response = dynamodb.export_table_to_point_in_time(
    TableArn='arn:aws:dynamodb:us-east-1:123456789012:table/YourTableName',
    S3Bucket=s3_bucket,
    S3Prefix=s3_prefix,
    ExportFormat='DYNAMODB_JSON'  # or 'ION'
)

export_arn = response['ExportDescription']['ExportArn']
print(f"Export started: {export_arn}")

# Wait for export to complete (check status)
# Then read from S3
df = spark.read.json(f"s3a://{s3_bucket}/{s3_prefix}/")
display(df)
```

---

### **Option 2: IAM Role (Best Practice - for Databricks on AWS)**

If your Databricks is running on AWS, use IAM Roles instead of access keys.

## **Step 1: Create IAM Role**

1. **IAM** → **Roles** → **Create role**
2. **Trusted entity type**: Custom trust policy
3. **Custom trust policy**:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::414351767826:role/databricks-cross-account-role"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "your-databricks-external-id"
                }
            }
        }
    ]
}
```

**Note:** Get the correct External ID from your Databricks workspace settings.

4. Click **Next**
5. Attach policy: `DatabricksDynamoDBReadPolicy`
6. **Role name**: `databricks-dynamodb-read-role`
7. Click **Create role**

## **Step 2: Configure Instance Profile in Databricks**

1. In Databricks workspace, go to **Admin Console**
2. **Instance Profiles** → **Add Instance Profile**
3. Enter the role ARN: `arn:aws:iam::123456789012:role/databricks-dynamodb-read-role`
4. Click **Add**

## **Step 3: Use Role in Cluster**

When creating/editing a cluster:
1. **Advanced Options** → **Instances**
2. **Instance Profile**: Select `databricks-dynamodb-read-role`
3. Start the cluster

Now your cluster has automatic access to DynamoDB!

## **Step 4: Read DynamoDB (No Explicit Credentials)**

```python
import boto3

# boto3 automatically uses instance profile credentials
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

table = dynamodb.Table('YourTableName')
response = table.scan()

# Convert to DataFrame
items = response['Items']
df = spark.createDataFrame(items)
display(df)
```

---

### **Complete Example: Read DynamoDB Table**

```python
# ============================================
# Complete Example: Read DynamoDB in Databricks
# ============================================

# Install required libraries
%pip install boto3

import boto3
from pyspark.sql import Row
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# Configuration
TABLE_NAME = "your-table-name"
AWS_REGION = "us-east-1"

# Get credentials from Databricks secrets
# (Skip this if using IAM Role)
aws_access_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-access-key-id")
aws_secret_key = dbutils.secrets.get(scope="aws-dynamodb", key="aws-secret-access-key")

# Create DynamoDB resource
dynamodb = boto3.resource(
    'dynamodb',
    region_name=AWS_REGION,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

table = dynamodb.Table(TABLE_NAME)

print(f"Reading from table: {TABLE_NAME}")
print(f"Table status: {table.table_status}")
print(f"Item count: {table.item_count}")

# Function to scan entire table with pagination
def scan_table(dynamodb_table):
    """Scan entire DynamoDB table handling pagination"""
    items = []
    response = dynamodb_table.scan()
    items.extend(response['Items'])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        print(f"Fetching more items... (current count: {len(items)})")
        response = dynamodb_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])
    
    print(f"Total items fetched: {len(items)}")
    return items

# Scan table
items = scan_table(table)

# Convert to Spark DataFrame
if items:
    # Convert DynamoDB items to Spark Rows
    spark_rows = [Row(**item) for item in items]
    df = spark.createDataFrame(spark_rows)
    
    print("\nDataFrame Schema:")
    df.printSchema()
    
    print("\nSample Data:")
    display(df.limit(10))
    
    # Save to Delta Lake (optional)
    df.write.format("delta").mode("overwrite").saveAsTable("dynamodb_table_data")
    print("Data saved to Delta table: dynamodb_table_data")
else:
    print("No items found in table")
```

---

### **Query Operations (Instead of Scan)**

For better performance, use Query instead of Scan:

```python
# Query with partition key
response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq('user123')
)

# Query with partition key and sort key
from boto3.dynamodb.conditions import Key

response = table.query(
    KeyConditionExpression=Key('userId').eq('user123') & Key('timestamp').between(
        '2025-01-01', '2025-01-31'
    )
)

# Query with filter
response = table.query(
    KeyConditionExpression=Key('userId').eq('user123'),
    FilterExpression='attribute_exists(email) AND #status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={':status': 'active'}
)

items = response['Items']
```

## **Security**

✅ **Use IAM Roles** instead of access keys when possible  
✅ **Store credentials in Databricks Secrets**, never in code  
✅ **Use least privilege** - only grant necessary permissions  
✅ **Rotate access keys** regularly if using IAM users  
✅ **Enable CloudTrail** to audit DynamoDB access

## **Performance**

✅ **Use Query instead of Scan** when possible  
✅ **Use parallel scans** for large tables:

```python
from concurrent.futures import ThreadPoolExecutor

def scan_segment(segment, total_segments):
    response = table.scan(
        Segment=segment,
        TotalSegments=total_segments
    )
    items = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            Segment=segment,
            TotalSegments=total_segments,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])
    
    return items

# Parallel scan with 4 segments
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(scan_segment, i, 4) for i in range(4)]
    all_items = []
    for future in futures:
        all_items.extend(future.result())
```

✅ **Export to S3 for large datasets** (> 100K items)  
✅ **Use DynamoDB Streams** for incremental updates  
✅ **Cache data in Delta Lake** for repeated queries

## **Cost Optimization**

✅ **Minimize scans** - they consume read capacity units  
✅ **Use ProjectionExpression** to read only needed attributes:

```python
response = table.scan(
    ProjectionExpression='userId, email, createdAt'
)
```

✅ **Consider DynamoDB on-demand pricing** for sporadic access  
✅ **Export to S3 for analytics** - cheaper than repeated scans



### **Error: "Access Denied"**

Check:
- IAM policy allows `dynamodb:Scan` or `dynamodb:Query`
- Table ARN in policy matches your table
- Credentials are correct

### **Error: "Rate Exceeded"**

- DynamoDB has read/write capacity limits
- Use exponential backoff
- Consider increasing provisioned capacity

### **Error: "Module not found: boto3"**

```python
%pip install boto3
dbutils.library.restartPython()
```

### **Summary: Quick Start**

1. ✅ Create IAM policy with DynamoDB read permissions
2. ✅ Create IAM user and generate access keys
3. ✅ Store keys in Databricks secrets
4. ✅ Use boto3 to read DynamoDB
5. ✅ Convert to Spark DataFrame

 
