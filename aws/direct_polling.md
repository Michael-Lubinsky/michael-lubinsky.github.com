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
