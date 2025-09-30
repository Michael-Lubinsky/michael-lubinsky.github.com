# Accessing DynamoDB from Databricks

You can access DynamoDB tables from Databricks using the AWS SDK for Python (boto3)  
or by reading data through Spark with appropriate connectors.

## Access Methods

### 1. **Using boto3 (Python SDK)**
This is the most straightforward approach for smaller datasets:

```python
import boto3
from pyspark.sql import SparkSession

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('your-table-name')

# Scan the table
response = table.scan()
items = response['Items']

# Convert to Spark DataFrame
spark = SparkSession.builder.getOrCreate()
df = spark.createDataFrame(items)
df.show()
```

### 2. **Using Spark with DynamoDB Connector**
For larger datasets, use the emr-dynamodb-hadoop connector:

```python
df = spark.read \
    .format("dynamodb") \
    .option("tableName", "your-table-name") \
    .option("region", "us-east-1") \
    .load()
```

You'll need to install the connector library in your Databricks cluster.

## Minimal IAM Roles Required

### **For Databricks Instance Profile (EC2 Role)**

Create an IAM role with these permissions and attach it to your Databricks workspace:

**Trust Policy:**
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

**Permission Policy (minimal):**
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
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME",
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME/index/*"
      ]
    }
  ]
}
```

### **Additional Permissions (if needed)**

If you need to write back to DynamoDB:
```json
{
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME"
}
```

## Configuration Steps

1. **Create the IAM role** with the policies above
2. **Attach the role to Databricks**:
   - Go to AWS Console → Databricks workspace settings
   - Add the IAM role as an instance profile
3. **Configure in Databricks**:
   - Admin Console → Instance Profiles → Add the role ARN
4. **Assign to cluster**:
   - When creating/editing a cluster, select the instance profile under "Advanced Options"

## Best Practices

- **Use Query instead of Scan** when possible (more efficient and cost-effective)
- **Implement pagination** for large tables to avoid timeouts
- **Consider reading capacity** - DynamoDB scans consume read capacity units
- **Cache results** in Databricks if you need to access the data multiple times
- **Use Global Secondary Indexes** if available for better query performance


# Real-time DynamoDB to Databricks Data Pipeline

For near real-time processing of DynamoDB changes, you have several architectural options:

## Recommended Architecture: DynamoDB Streams + AWS Lambda + Databricks

This is the most efficient approach for continuous data ingestion:

### **Architecture Flow**
1. **DynamoDB Streams** captures all changes (inserts/updates/deletes)
2. **AWS Lambda** processes stream records
3. **Lambda writes to S3** (or Kinesis/Kafka)
4. **Databricks Auto Loader** ingests and processes data continuously

### **Step 1: Enable DynamoDB Streams**

```python
# Enable streams via boto3
dynamodb = boto3.client('dynamodb')
dynamodb.update_table(
    TableName='your-table',
    StreamSpecification={
        'StreamEnabled': True,
        'StreamViewType': 'NEW_AND_OLD_IMAGES'  # or 'NEW_IMAGE' for inserts only
    }
)
```

### **Step 2: Create Lambda Function**

```python
import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'your-databricks-bucket'
PREFIX = 'dynamodb-changes/'

def lambda_handler(event, context):
    records = []
    
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            # Extract the new image
            new_image = record['dynamodb'].get('NewImage', {})
            
            # Convert DynamoDB format to regular JSON
            item = {
                'event_id': record['eventID'],
                'event_name': record['eventName'],
                'event_time': record['dynamodb']['ApproximateCreationDateTime'],
                'data': deserialize_dynamodb_item(new_image)
            }
            records.append(item)
    
    if records:
        # Write to S3 as JSON lines
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        key = f"{PREFIX}{timestamp}.json"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body='\n'.join([json.dumps(r) for r in records])
        )
    
    return {'statusCode': 200, 'body': f'Processed {len(records)} records'}

def deserialize_dynamodb_item(item):
    """Convert DynamoDB JSON format to regular JSON"""
    from boto3.dynamodb.types import TypeDeserializer
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in item.items()}
```

### **Step 3: Configure Lambda Trigger**

Set up Lambda to trigger from DynamoDB Streams:
- Batch size: 100-1000 (based on record size)
- Batch window: 1-10 seconds
- Starting position: LATEST or TRIM_HORIZON

### **Step 4: Databricks Auto Loader (Streaming)**

```python
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Define schema
schema = StructType([
    StructField("event_id", StringType()),
    StructField("event_name", StringType()),
    StructField("event_time", DoubleType()),
    StructField("data", MapType(StringType(), StringType()))
])

# Read streaming data from S3
streaming_df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/mnt/schema/dynamodb_changes")
    .schema(schema)
    .load(f"s3://{BUCKET_NAME}/{PREFIX}")
)

# Process the data
processed_df = (streaming_df
    .withColumn("processing_time", current_timestamp())
    .withColumn("event_datetime", from_unixtime(col("event_time")))
    # Expand the nested data structure
    .select("event_id", "event_name", "event_datetime", "data.*", "processing_time")
)

# Write to Delta Lake
(processed_df.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/mnt/checkpoints/dynamodb_stream")
    .trigger(processingTime="10 seconds")  # Adjust based on your needs
    .table("my_catalog.my_schema.dynamodb_data")
)
```

---

## Alternative: Direct Polling from Databricks (Less Efficient)

If you prefer a simpler approach without Lambda:

```python
from datetime import datetime, timedelta
import time

def incremental_load_dynamodb():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('your-table-name')
    
    # Track last processed timestamp (store in Delta table)
    last_timestamp = get_last_processed_timestamp()  # Your implementation
    
    # Query with timestamp filter
    response = table.scan(
        FilterExpression='#ts > :last_ts',
        ExpressionAttributeNames={'#ts': 'timestamp'},
        ExpressionAttributeValues={':last_ts': last_timestamp}
    )
    
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#ts > :last_ts',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={':last_ts': last_timestamp},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])
    
    if items:
        df = spark.createDataFrame(items)
        # Write to Delta Lake
        df.write.format("delta").mode("append").saveAsTable("your_delta_table")
        
        # Update checkpoint
        save_last_processed_timestamp(datetime.now())

# Run as Databricks Job every 1 minute
while True:
    incremental_load_dynamodb()
    time.sleep(60)
```

**Schedule this as a Databricks Job** with continuous run mode or 1-minute trigger.

---

## Required IAM Permissions

### **For Lambda Function Role:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME/stream/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::your-bucket/dynamodb-changes/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### **For Databricks Instance Profile:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket",
        "arn:aws:s3:::your-bucket/dynamodb-changes/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket/checkpoints/*",
        "arn:aws:s3:::your-bucket/schema/*"
      ]
    }
  ]
}
```

---

## Comparison of Approaches

| Approach | Latency | Cost | Complexity | Scalability |
|----------|---------|------|------------|-------------|
| **DynamoDB Streams + Lambda** | Seconds | Low | Medium | Excellent |
| **Direct Polling** | 1+ minutes | Higher (read capacity) | Low | Limited |
| **Kinesis Data Streams** | Seconds | Medium | High | Excellent |

## Recommendation

**Use DynamoDB Streams + Lambda + Auto Loader** for:
- True near real-time processing (seconds delay)
- Cost efficiency (only pay for changes)
- Scalability (handles burst traffic)
- Change Data Capture (CDC) capabilities

  **Yes, direct polling is the easiest to deploy**,

but it’s also the least robust at scale. If your tables are small/moderate and you just need data every few minutes, polling can be fine.   
If you expect growth, spikes, strict SLAs, or multiple tables, prefer Streams→(Lambda/Kinesis/Firehose)→S3→Databricks (Auto Loader) or DMS.

---

## “Ease of deployment” comparison (from easiest → more setup)

#### 1) Direct polling from Databricks (boto3)
   - What you do:
     - Add `boto3` to the cluster.
     - Give the cluster an AWS role with DynamoDB read perms.
     - (Recommended) Add a GSI on a change key (e.g., `updated_at`) and keep a Delta watermark table.
     - Write a simple Python job that queries “> watermark”, appends to Bronze, MERGE to Silver.
   - Time-to-first-ingest: hours.
   - Latency: job schedule (e.g., every 2–5 min).
   - Pros: minimal AWS infra; easy to iterate; works from one repo/job.
   - Cons: no built-in CDC; you own pagination/backoff/retries/RCU costs; easy to over-scan; brittle under high write rates; horizontal scaling is manual.

#### 2) DynamoDB Streams → Kinesis Firehose → S3 → Databricks Auto Loader (default for many teams)
   - What you do:
     - Enable DynamoDB Streams.
     - Create Firehose to S3 (optionally via Kinesis Data Streams for buffering/replay).
     - Create an S3 bucket/prefix; wire IAM roles/policies.
     - In Databricks, set up Auto Loader streaming job to Bronze; MERGE to Silver.
   - Time-to-first-ingest: half-day to 1–2 days (mostly IAM + plumbing).
   - Latency: minutes (Firehose buffer) + Auto Loader trigger.
   - Pros: durable S3 landing, replayability, low ops, scales well, near-real-time with exactly-once in Delta via checkpoints + MERGE.
   - Cons: more AWS setup than polling.

#### 3) AWS DMS → S3 → Auto Loader
   - What you do:
     - Create a DMS replication instance + task (Full load + CDC from DynamoDB).
     - Land to S3 (JSON/Parquet) with operation codes, then Auto Loader to Bronze; MERGE to Silver.
   - Time-to-first-ingest: 1–2 days.
   - Latency: usually minutes.
   - Pros: great for initial backfill + ongoing changes; robust retry/monitoring.
   - Cons: service cost; some DMS learning curve.

#### 4) DynamoDB Streams → Lambda → S3 → Auto Loader (DIY)
   - What you do:
     - Enable Streams; write Lambda to process records and write to S3 (optionally partitioned Parquet).
     - IAM for Lambda + S3; Auto Loader to Bronze; MERGE to Silver.
   - Time-to-first-ingest: 1–3 days (code + ops).
   - Latency: seconds to minutes.
   - Pros: very flexible transform, low latency.
   - Cons: you own code, retries, DLQs, backpressure; more ops.

---

## When direct polling is OK (and simplest)
- Low/medium write rates.
- Few tables (e.g., 1–5).
- You can add a **GSI on `updated_at`** (or another monotonic change key).
- Latency target is relaxed (2–10 minutes).
- You accept building a simple **watermark** mechanism and occasional upsert dedupe logic.

## When to avoid polling (use Streams/Firehose or DMS)
- High or bursty write rates, large tables, many tables.
- Need strong CDC semantics, replay, ordering, scalable fan-in.
- Want durable, append-only S3 landing and Auto Loader’s “just works” ingestion.
- Strict SLAs and hands-off operations.

---

## Decision cheatsheet
- “I need the fastest path today, and volumes are small” → **Direct polling**.
- “I want a stable, scalable pipeline with low ops and near-real-time” → **Streams → Firehose → S3 → Auto Loader**.
- “I also need a one-time full backfill, then keep in sync” → **PITR Export (backfill) + Streams/Firehose (incremental)** or **DMS (full + CDC)**.

---

## Minimal direct-polling checklist (if you choose it)
- Add/ensure `updated_at` (ISO8601 or epoch) on all items, updated on every write.
- Create GSI to query by `updated_at` (and, if needed, a fixed/bucketed partition key).
- Implement watermark table in Delta.
- Implement boto3 pagination + exponential backoff on throttling.
- Batch writes to Bronze and MERGE to Silver; dedupe on primary key and latest `updated_at`.
- Set conservative schedules initially (e.g., every 5 min) and watch RCUs/latency.
- Add CloudWatch alarms on throttling and Databricks job failure alerts.

If you want, I can give you:
- A ready-to-paste DynamoDB **GSI definition (CLI + Console)**.
- The **Databricks job** (Python) with watermarking, backoff, and metrics logging.
- An **Auto Loader** alternative that writes JSONL to S3 from the poller so you can pivot to streaming later with zero model changes.
 


### How to To check if a DynamoDB table has a **Global Secondary Index (GSI)

** you can use either the AWS Console, AWS CLI, or boto3:

---

### 1. AWS Console
1. Go to the **DynamoDB** service in the AWS Management Console.
2. Select your table.
3. In the left panel, click **Indexes**.
   - If you see entries under **Global secondary indexes**, then the table has GSIs.
   - If the list is empty, there are none.

---

### 2. AWS CLI
Run:
```bash
aws dynamodb describe-table --table-name YourTableName
````

Look at the `"GlobalSecondaryIndexes"` field in the JSON output:

* If it exists and has entries → GSIs are defined.
* If it is missing or `null` → no GSIs.

Example snippet from the output:

```json
"GlobalSecondaryIndexes": [
  {
    "IndexName": "updated_at_index",
    "KeySchema": [
      {"AttributeName": "dummy_hash", "KeyType": "HASH"},
      {"AttributeName": "updated_at", "KeyType": "RANGE"}
    ],
    "Projection": {"ProjectionType": "ALL"}
  }
]
```

---

### 3. boto3 (Python)

```python
import boto3

dynamodb = boto3.client("dynamodb")

resp = dynamodb.describe_table(TableName="YourTableName")
if "GlobalSecondaryIndexes" in resp["Table"]:
    print("GSIs:")
    for gsi in resp["Table"]["GlobalSecondaryIndexes"]:
        print(gsi["IndexName"])
else:
    print("No GSIs defined")
```

---

✅ If you’re planning to use **direct polling**, confirming there’s a GSI on `updated_at` (or another change key) is critical—otherwise you’ll be stuck doing expensive `Scan()` operations.

Do you want me to also show you how to **add a GSI on `updated_at`** (both Console steps and CLI command)?



## How to add a Global Secondary Index (GSI) on `updated_at`

You can add a GSI either in the **AWS Console** or via the **AWS CLI**.  
⚠️ Reminder: You must provision a new index carefully — it can take time to build if the table is large, and you’ll be billed for its capacity (or it will consume write/read capacity if the table is on provisioned mode).

---

### 1. AWS Console

1. Go to **DynamoDB** in the AWS Management Console.
2. Select your **table**.
3. In the left menu, click **Indexes**.
4. Click **Create index**.
5. Fill out:
   - **Partition key**:  
     - If you want all items in one partition (common for time-range queries), use a dummy value (e.g., an attribute called `gsi_pk` that always has value `"X"` or hash-bucketed like `"bucket_0" ... "bucket_15"`).  
     - If you already have a natural partition key that works for your use case, use that instead.
   - **Sort key**: `updated_at`
6. **Projected attributes**: choose *All* if you want the whole item in the index, or *Include* if you just need a subset.
7. **Index name**: e.g. `updated_at_index`.
8. **Provisioned capacity**:
   - If the base table uses On-Demand, the GSI will also be On-Demand.
   - If provisioned, pick read/write capacity units.
9. Click **Create index**.

You’ll see the index being created; status changes from *CREATING* → *ACTIVE* when done.

---

## 2. AWS CLI

### Command
```bash
aws dynamodb update-table \
  --table-name YourTableName \
  --attribute-definitions \
      AttributeName=gsi_pk,AttributeType=S \
      AttributeName=updated_at,AttributeType=S \
  --global-secondary-index-updates \
      "[{\"Create\":{\"IndexName\": \"updated_at_index\",
                     \"KeySchema\":[
                       {\"AttributeName\":\"gsi_pk\",\"KeyType\":\"HASH\"},
                       {\"AttributeName\":\"updated_at\",\"KeyType\":\"RANGE\"}
                     ],
                     \"Projection\":{\"ProjectionType\":\"ALL\"},
                     \"ProvisionedThroughput\": {\"ReadCapacityUnits\": 5, \"WriteCapacityUnits\": 5}
      }}]"
````

### Explanation

* `--attribute-definitions`: defines new attributes that aren’t already part of the table schema (`gsi_pk` and `updated_at` in this case).
* `--global-secondary-index-updates`: tells DynamoDB to create a new GSI.
* `KeySchema`: defines the partition (`HASH`) and sort (`RANGE`) key of the GSI.
* `ProjectionType=ALL`: copies all attributes into the index (simpler for ingestion).
* `ProvisionedThroughput`: only needed if your table is not using on-demand.

---

### 3. Usage after creation

Once the GSI is active, you can query like this in boto3:

```python
from boto3.dynamodb.conditions import Key
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("YourTableName")

resp = table.query(
    IndexName="updated_at_index",
    KeyConditionExpression=Key("gsi_pk").eq("X") & Key("updated_at").gt("2025-09-01T00:00:00Z")
)
for item in resp["Items"]:
    print(item)
```

---

👉 Question for you: Do you want me to assume a **dummy constant partition key** (`gsi_pk="X"`) in the index, or do you already have a natural partition key you’d prefer to use (like `customer_id`)? This changes how I’d tailor the CLI/Console steps.

