# Streaming data from DynamoDB to S3 with low latency and immediate visibility in Databricks:

## Architecture Overview

**DynamoDB → S3 → Databricks** with ~1 minute end-to-end latency

## Implementation Approach

### 1. **Capture DynamoDB Changes Using DynamoDB Streams**

Enable DynamoDB Streams to capture all table changes in near real-time.

**Enable streams on your tables:**
```python
import boto3

dynamodb = boto3.client('dynamodb')

# Enable stream on table
dynamodb.update_table(
    TableName='your-table',
    StreamSpecification={
        'StreamEnabled': True,
        'StreamViewType': 'NEW_AND_OLD_IMAGES'  # or 'NEW_IMAGE' for inserts only
    }
)
```

### 2. **Stream Data to S3 - Three Options**

#### **Option A: Kinesis Data Firehose (Recommended - Simplest)**

This is the easiest managed solution with minimal code.

**Setup:**
1. **Connect DynamoDB Streams to Kinesis Data Streams** (via AWS Console or CDK/Terraform)
2. **Create Kinesis Firehose delivery stream** from Kinesis to S3

```python
import boto3

firehose = boto3.client('firehose')

# Create Firehose delivery stream
firehose.create_delivery_stream(
    DeliveryStreamName='dynamodb-to-s3',
    DeliveryStreamType='KinesisStreamAsSource',
    KinesisStreamSourceConfiguration={
        'KinesisStreamARN': 'arn:aws:kinesis:region:account:stream/dynamodb-stream',
        'RoleARN': 'arn:aws:iam::account:role/firehose-role'
    },
    ExtendedS3DestinationConfiguration={
        'BucketARN': 'arn:aws:s3:::your-bucket',
        'Prefix': 'dynamodb-data/table_name/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/',
        'BufferingHints': {
            'SizeInMBs': 64,
            'IntervalInSeconds': 60  # 1 minute batching
        },
        'CompressionFormat': 'GZIP',
        'DataFormatConversionConfiguration': {
            'Enabled': True,
            'OutputFormatConfiguration': {
                'Serializer': {
                    'ParquetSerDe': {}
                }
            }
        },
        'RoleARN': 'arn:aws:iam::account:role/firehose-role'
    }
)
```

#### **Option B: Lambda Function (More Control)**

Process DynamoDB Stream events with Lambda and write to S3:

```python
import json
import boto3
from datetime import datetime
import gzip

s3 = boto3.client('s3')
BUCKET_NAME = 'your-bucket'

def lambda_handler(event, context):
    """
    Lambda triggered by DynamoDB Stream
    Batches records and writes to S3 every invocation
    """
    records = []
    
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            # Extract new image
            new_image = record['dynamodb'].get('NewImage', {})
            
            # Convert DynamoDB format to standard JSON
            item = deserialize_dynamodb_item(new_image)
            item['_event_type'] = record['eventName']
            item['_event_time'] = record['dynamodb']['ApproximateCreationDateTime']
            
            records.append(item)
    
    if records:
        # Write batch to S3
        timestamp = datetime.utcnow()
        key = f"dynamodb-data/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{timestamp.hour:02d}/{timestamp.strftime('%Y%m%d%H%M%S')}-{context.request_id}.json.gz"
        
        # Compress and upload
        compressed_data = gzip.compress(
            '\n'.join([json.dumps(r) for r in records]).encode('utf-8')
        )
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=compressed_data,
            ContentType='application/json',
            ContentEncoding='gzip'
        )
    
    return {'statusCode': 200, 'body': f'Processed {len(records)} records'}

def deserialize_dynamodb_item(item):
    """Convert DynamoDB JSON format to normal JSON"""
    def deserialize_value(value):
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            return float(value['N']) if '.' in value['N'] else int(value['N'])
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'NULL' in value:
            return None
        elif 'M' in value:
            return {k: deserialize_value(v) for k, v in value['M'].items()}
        elif 'L' in value:
            return [deserialize_value(v) for v in value['L']]
        return value
    
    return {k: deserialize_value(v) for k, v in item.items()}
```

**Lambda Configuration:**
- Batch size: 100-1000 records
- Batch window: 60 seconds (for ~1 min latency)
- Memory: 512-1024 MB
- Timeout: 5 minutes

#### **Option C: AWS Glue Streaming Job**

For complex transformations:

```python
from awsglue.context import GlueContext
from pyspark.context import SparkContext
from awsglue.utils import getResolvedOptions

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Read from DynamoDB Stream via Kinesis
kinesis_options = {
    "streamARN": "arn:aws:kinesis:region:account:stream/dynamodb-stream",
    "startingPosition": "TRIM_HORIZON",
    "inferSchema": "true",
    "classification": "json"
}

df = glueContext.create_data_frame.from_options(
    connection_type="kinesis",
    connection_options=kinesis_options
)

# Write to S3
query = df.writeStream \
    .format("parquet") \
    .option("path", "s3://your-bucket/dynamodb-data/") \
    .option("checkpointLocation", "s3://your-bucket/checkpoints/") \
    .trigger(processingTime="60 seconds") \
    .start()

query.awaitTermination()
```

### 3. **Make S3 Data Visible in Databricks Immediately**

#### **Option A: Auto Loader with Delta Lake (Recommended)**

```python
# In Databricks notebook - Read from S3 using Auto Loader
from pyspark.sql.functions import col, from_json

# Auto Loader automatically detects new files
df = spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.useNotifications", "true")  # Uses S3 events for instant detection
    .option("cloudFiles.region", "us-east-1") \
    .option("cloudFiles.includeExistingFiles", "true") \
    .schema("your_schema_here") \
    .load("s3://your-bucket/dynamodb-data/")

# Write to Delta table for instant querying
df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/mnt/delta/checkpoints/dynamodb_table") \
    .table("dynamodb_synced_table")
```

#### **Option B: S3 Event Notifications + Auto Loader**

Set up S3 to send notifications when new files arrive:

**1. Configure S3 Event Notification (via AWS Console or Boto3):**
```python
import boto3

s3 = boto3.client('s3')

# Configure bucket notification
s3.put_bucket_notification_configuration(
    Bucket='your-bucket',
    NotificationConfiguration={
        'QueueConfigurations': [
            {
                'QueueArn': 'arn:aws:sqs:region:account:dynamodb-s3-events',
                'Events': ['s3:ObjectCreated:*'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {'Name': 'prefix', 'Value': 'dynamodb-data/'}
                        ]
                    }
                }
            }
        ]
    }
)
```

**2. Use Auto Loader with notifications in Databricks:**
```python
df = spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.useNotifications", "true") \
    .option("cloudFiles.region", "us-east-1") \
    .option("cloudFiles.queueUrl", "https://sqs.us-east-1.amazonaws.com/account/dynamodb-s3-events") \
    .schema(schema) \
    .load("s3://your-bucket/dynamodb-data/")

# Create Delta table
df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/mnt/delta/checkpoints/") \
    .trigger(processingTime="10 seconds")  # Check frequently
    .table("live_dynamodb_data")
```

## Complete End-to-End Solution

### **Terraform/CDK Infrastructure Setup**

```python
# Example using AWS CDK (Python)
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_kinesis as kinesis,
    aws_kinesisfirehose as firehose,
    aws_s3 as s3,
    aws_iam as iam,
    Stack
)

class DynamoDBToS3Stack(Stack):
    def __init__(self, scope, id):
        super().__init__(scope, id)
        
        # S3 bucket
        bucket = s3.Bucket(self, "DataBucket",
            bucket_name="your-dynamodb-data-bucket"
        )
        
        # Kinesis Stream (connects to DynamoDB Stream)
        stream = kinesis.Stream(self, "DynamoDBStream",
            stream_name="dynamodb-changes-stream"
        )
        
        # Firehose to S3
        firehose_role = iam.Role(self, "FirehoseRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com")
        )
        
        bucket.grant_write(firehose_role)
        stream.grant_read(firehose_role)
        
        # Note: Use L1 construct for full Firehose configuration
        # as shown in Option A above
```

### **Databricks Configuration**

```python
# Mount S3 bucket in Databricks (one-time setup)
aws_access_key = dbutils.secrets.get(scope="aws", key="access-key")
aws_secret_key = dbutils.secrets.get(scope="aws", key="secret-key")

dbutils.fs.mount(
    source=f"s3a://your-bucket/dynamodb-data",
    mount_point="/mnt/dynamodb-data",
    extra_configs={
        f"fs.s3a.access.key": aws_access_key,
        f"fs.s3a.secret.key": aws_secret_key
    }
)

# Set up streaming ingestion
from pyspark.sql.types import *

schema = StructType([
    StructField("id", StringType()),
    StructField("timestamp", LongType()),
    StructField("data", StringType()),
    StructField("_event_type", StringType()),
    StructField("_event_time", TimestampType())
])

# Read with Auto Loader
df = spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.schemaLocation", "/mnt/schemas/dynamodb") \
    .option("cloudFiles.useNotifications", "true") \
    .schema(schema) \
    .load("/mnt/dynamodb-data/")

# Write to Delta Lake
df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/mnt/delta/checkpoints/dynamodb") \
    .trigger(processingTime="10 seconds") \
    .table("production.dynamodb_live_data")

# Query the data (sees new data within seconds)
display(spark.sql("""
    SELECT * 
    FROM production.dynamodb_live_data 
    WHERE _event_time > current_timestamp() - INTERVAL 2 MINUTES
    ORDER BY _event_time DESC
"""))
```

## Latency Breakdown

- **DynamoDB Stream capture**: < 1 second
- **Kinesis/Lambda processing**: 10-60 seconds (configurable)
- **S3 write**: Near-instant
- **Databricks Auto Loader detection**: 5-30 seconds (with S3 notifications: < 5 seconds)
- **Total end-to-end**: ~1-2 minutes

## Best Practices

1. **Partition your S3 data** by date/hour for better Databricks performance
2. **Use Parquet format** in Firehose for efficient columnar storage
3. **Enable S3 event notifications** for fastest Auto Loader detection
4. **Monitor DynamoDB Stream shard limits** (1000 records/sec per shard)
5. **Set up CloudWatch alarms** for Lambda/Firehose failures
6. **Use Delta Lake's OPTIMIZE** periodically to compact small files

 
