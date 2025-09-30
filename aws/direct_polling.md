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


# DynamoDB Direct Polling Setup Guide

## Overview
This guide walks through setting up direct polling from DynamoDB to Databricks with 1-minute intervals.

## Prerequisites
- DynamoDB table with a timestamp column (e.g., `created_at`)
- Databricks workspace on AWS
- AWS credentials with appropriate permissions

---

## Step 1: Configure AWS IAM

### 1.1 Create IAM Role

```bash
# Create trust policy file
cat > trust-policy.json << EOF
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
EOF

# Create the role
aws iam create-role \
  --role-name databricks-dynamodb-role \
  --assume-role-policy-document file://trust-policy.json
```

### 1.2 Attach Permissions

```bash
# Create permission policy file
cat > permission-policy.json << EOF
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
EOF

# Attach policy to role
aws iam put-role-policy \
  --role-name databricks-dynamodb-role \
  --policy-name DynamoDBAccess \
  --policy-document file://permission-policy.json
```

### 1.3 Create Instance Profile

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

---

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

---

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


"""
DynamoDB Direct Polling to Databricks Delta Lake
Polls DynamoDB table every 1 minute and ingests new records into Delta Lake
"""
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
