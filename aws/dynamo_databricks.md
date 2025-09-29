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

Would you like help implementing any specific part of this architecture?
