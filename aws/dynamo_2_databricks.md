## pipeline to read data from DynamoDB and load it into Databricks,
along with real-time dashboards for monitoring and analytics.

I've created a comprehensive pipeline for ingesting data from DynamoDB into Databricks with real-time dashboards. This solution covers both streaming and batch ingestion patterns to handle different use cases.

## 🏗️ **Key Architecture Components:**

**Data Ingestion Methods:**
- **Real-time**: DynamoDB Streams → Kinesis → Databricks Streaming
- **Batch**: DynamoDB Export → S3 → Databricks Batch Processing

**Processing Layers:**
- **Bronze**: Raw DynamoDB stream data
- **Silver**: Cleaned and transformed business data  
- **Gold**: Aggregated metrics and analytics

## 📊 **Real-time Dashboard Features:**

1. **Order Monitoring Dashboard**
   - Current hour orders and revenue
   - Order status distribution
   - Hourly trends and top customers
   - Live event stream

2. **Business Intelligence Dashboard**
   - Revenue trends and customer segmentation
   - Product performance metrics
   - Order funnel analysis

3. **Operational Monitoring Dashboard**
   - Pipeline health monitoring
   - Data freshness and latency metrics
   - Error rates and anomaly detection

## ⚡ **Advanced Features:**

- **Real-time Anomaly Detection**: Statistical analysis for unusual patterns
- **Automated Alerts**: Proactive monitoring for critical conditions
- **Performance Optimization**: Delta Lake optimization and Z-ordering
- **Cost Management**: Auto-scaling clusters with spot instances

## 🚀 **Next Steps:**

Would you like me to elaborate on any specific aspect:

1. **Specific DynamoDB table schemas** - Help you adapt the transformations for your actual table structures?

2. **Advanced dashboard customization** - Create more specific visualizations for your business metrics?

3. **Alert and monitoring setup** - Configure specific thresholds and notification channels?

4. **Performance tuning** - Optimize for your specific data volume and query patterns?

5. **Security and access control** - Set up proper IAM roles and Databricks permissions?

I can also help you with the actual deployment steps,
including setting up the AWS resources, configuring Databricks workspace,
and creating the streaming jobs.


# DynamoDB to Databricks Pipeline with Real-time Dashboards

## Architecture Overview

```
DynamoDB Tables → DynamoDB Streams → Kinesis Data Streams → Databricks → Delta Tables → Real-time Dashboards
                ↘ Batch Export → S3 → Databricks (Historical Load) ↗
```

## 1. Data Ingestion Strategies

### Strategy A: Real-time Streaming (DynamoDB Streams + Kinesis)

#### DynamoDB Streams Configuration
```python
import boto3

def enable_dynamodb_streams():
    """Enable DynamoDB Streams for real-time data capture"""
    
    dynamodb = boto3.client('dynamodb')
    
    tables = ['users', 'orders', 'products', 'transactions']  # Your table names
    
    for table_name in tables:
        try:
            response = dynamodb.update_table(
                TableName=table_name,
                StreamSpecification={
                    'StreamEnabled': True,
                    'StreamViewType': 'NEW_AND_OLD_IMAGES'  # Captures before and after images
                }
            )
            print(f"Enabled streams for {table_name}")
        except Exception as e:
            print(f"Error enabling streams for {table_name}: {e}")
```

#### Kinesis Data Streams Setup
```python
def create_kinesis_streams():
    """Create Kinesis streams for DynamoDB data"""
    
    kinesis = boto3.client('kinesis')
    
    streams = {
        'dynamodb-users-stream': 2,
        'dynamodb-orders-stream': 4,
        'dynamodb-products-stream': 1,
        'dynamodb-transactions-stream': 6
    }
    
    for stream_name, shard_count in streams.items():
        try:
            kinesis.create_stream(
                StreamName=stream_name,
                ShardCount=shard_count
            )
            print(f"Created Kinesis stream: {stream_name}")
        except kinesis.exceptions.ResourceInUseException:
            print(f"Stream {stream_name} already exists")
```

### Strategy B: Batch Export via S3

#### DynamoDB Export to S3
```python
def export_dynamodb_to_s3():
    """Export DynamoDB tables to S3 for historical load"""
    
    dynamodb = boto3.client('dynamodb')
    
    export_config = {
        'S3Bucket': 'your-ddb-export-bucket',
        'S3Prefix': 'dynamodb-exports/',
        'ExportFormat': 'DYNAMODB_JSON',  # or ION
        'ExportType': 'FULL_EXPORT'
    }
    
    tables = ['users', 'orders', 'products', 'transactions']
    
    for table_name in tables:
        response = dynamodb.export_table_to_point_in_time(
            TableArn=f"arn:aws:dynamodb:us-east-1:123456789:table/{table_name}",
            S3Bucket=export_config['S3Bucket'],
            S3Prefix=f"{export_config['S3Prefix']}{table_name}/",
            ExportFormat=export_config['ExportFormat'],
            ExportType=export_config['ExportType']
        )
        print(f"Export initiated for {table_name}: {response['ExportDescription']['ExportArn']}")
```

## 2. Databricks Data Ingestion

### Real-time Streaming Ingestion

#### Kinesis to Databricks Streaming
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json

# Initialize Spark session with required configurations
spark = SparkSession.builder \
    .appName("DynamoDB-Kinesis-Streaming") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

def setup_kinesis_streaming():
    """Setup Kinesis streaming ingestion"""
    
    # Kinesis stream configuration
    kinesis_config = {
        "streamName": "dynamodb-orders-stream",
        "region": "us-east-1",
        "initialPosition": "TRIM_HORIZON",
        "awsAccessKeyId": dbutils.secrets.get("aws", "access-key-id"),
        "awsSecretKey": dbutils.secrets.get("aws", "secret-access-key")
    }
    
    # Read from Kinesis stream
    kinesis_stream = (spark
                     .readStream
                     .format("kinesis")
                     .option("streamName", kinesis_config["streamName"])
                     .option("region", kinesis_config["region"])
                     .option("initialPosition", kinesis_config["initialPosition"])
                     .option("awsAccessKeyId", kinesis_config["awsAccessKeyId"])
                     .option("awsSecretKey", kinesis_config["awsSecretKey"])
                     .load())
    
    return kinesis_stream

def parse_dynamodb_stream_record(df):
    """Parse DynamoDB stream records from Kinesis"""
    
    # Define schema for DynamoDB stream record
    dynamodb_schema = StructType([
        StructField("eventName", StringType(), True),  # INSERT, MODIFY, REMOVE
        StructField("eventSource", StringType(), True),
        StructField("awsRegion", StringType(), True),
        StructField("dynamodb", StructType([
            StructField("ApproximateCreationDateTime", TimestampType(), True),
            StructField("Keys", MapType(StringType(), MapType(StringType(), StringType())), True),
            StructField("NewImage", MapType(StringType(), MapType(StringType(), StringType())), True),
            StructField("OldImage", MapType(StringType(), MapType(StringType(), StringType())), True),
            StructField("SequenceNumber", StringType(), True),
            StructField("SizeBytes", LongType(), True),
            StructField("StreamViewType", StringType(), True)
        ]), True)
    ])
    
    # Parse JSON data from Kinesis
    parsed_df = (df
                .select(from_json(col("data").cast("string"), dynamodb_schema).alias("record"))
                .select("record.*")
                .withColumn("processing_timestamp", current_timestamp()))
    
    return parsed_df

def transform_orders_stream(df):
    """Transform orders stream data"""
    
    return (df
            .filter(col("eventSource") == "aws:dynamodb")
            .withColumn("order_id", col("dynamodb.Keys.order_id.S"))
            .withColumn("customer_id", col("dynamodb.NewImage.customer_id.S"))
            .withColumn("product_id", col("dynamodb.NewImage.product_id.S"))
            .withColumn("order_amount", col("dynamodb.NewImage.amount.N").cast("decimal(10,2)"))
            .withColumn("order_status", col("dynamodb.NewImage.status.S"))
            .withColumn("created_at", col("dynamodb.NewImage.created_at.S").cast("timestamp"))
            .withColumn("event_type", col("eventName"))
            .withColumn("event_timestamp", col("dynamodb.ApproximateCreationDateTime"))
            .select("order_id", "customer_id", "product_id", "order_amount", 
                   "order_status", "created_at", "event_type", "event_timestamp", "processing_timestamp"))
```

#### Write Streaming Data to Delta Tables
```python
def write_to_delta_bronze():
    """Write raw streaming data to bronze Delta table"""
    
    kinesis_stream = setup_kinesis_streaming()
    parsed_stream = parse_dynamodb_stream_record(kinesis_stream)
    
    query = (parsed_stream
             .writeStream
             .format("delta")
             .outputMode("append")
             .option("checkpointLocation", "/mnt/delta/checkpoints/dynamodb_bronze")
             .partitionBy("eventSource")
             .trigger(processingTime='30 seconds')
             .table("dynamodb_bronze"))
    
    return query

def write_to_delta_silver():
    """Write transformed data to silver Delta table"""
    
    bronze_stream = spark.readStream.table("dynamodb_bronze")
    transformed_stream = transform_orders_stream(bronze_stream)
    
    query = (transformed_stream
             .writeStream
             .format("delta")
             .outputMode("append")
             .option("checkpointLocation", "/mnt/delta/checkpoints/orders_silver")
             .partitionBy("event_type")
             .trigger(processingTime='1 minute')
             .table("orders_silver"))
    
    return query
```

### Batch Ingestion from S3 Exports

#### Historical Data Load
```python
def load_historical_dynamodb_data():
    """Load historical DynamoDB data from S3 exports"""
    
    # Read DynamoDB JSON export from S3
    s3_path = "s3a://your-ddb-export-bucket/dynamodb-exports/"
    
    tables_config = {
        "users": {
            "path": f"{s3_path}users/",
            "target_table": "users_historical"
        },
        "orders": {
            "path": f"{s3_path}orders/", 
            "target_table": "orders_historical"
        },
        "products": {
            "path": f"{s3_path}products/",
            "target_table": "products_historical"
        },
        "transactions": {
            "path": f"{s3_path}transactions/",
            "target_table": "transactions_historical"
        }
    }
    
    for table_name, config in tables_config.items():
        df = (spark.read
              .format("json")
              .option("multiline", "true")
              .load(config["path"]))
        
        # Transform DynamoDB JSON format to standard format
        transformed_df = transform_dynamodb_json(df, table_name)
        
        # Write to Delta table
        (transformed_df
         .write
         .format("delta")
         .mode("overwrite")
         .option("mergeSchema", "true")
         .table(config["target_table"]))
        
        print(f"Loaded {table_name} historical data to {config['target_table']}")

def transform_dynamodb_json(df, table_name):
    """Transform DynamoDB JSON format to standard columnar format"""
    
    if table_name == "users":
        return (df
                .select(
                    col("Item.user_id.S").alias("user_id"),
                    col("Item.email.S").alias("email"),
                    col("Item.first_name.S").alias("first_name"),
                    col("Item.last_name.S").alias("last_name"),
                    col("Item.created_at.S").cast("timestamp").alias("created_at"),
                    col("Item.status.S").alias("status")
                ))
    elif table_name == "orders":
        return (df
                .select(
                    col("Item.order_id.S").alias("order_id"),
                    col("Item.customer_id.S").alias("customer_id"),
                    col("Item.product_id.S").alias("product_id"),
                    col("Item.amount.N").cast("decimal(10,2)").alias("amount"),
                    col("Item.status.S").alias("status"),
                    col("Item.created_at.S").cast("timestamp").alias("created_at")
                ))
    # Add more table transformations as needed
    else:
        return df
```

## 3. Data Processing and Transformation

### Create Gold Layer Aggregations
```python
def create_gold_layer_tables():
    """Create gold layer tables for analytics"""
    
    # Daily order metrics
    spark.sql("""
        CREATE OR REPLACE TABLE orders_daily_metrics AS
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total_orders,
            COUNT(DISTINCT customer_id) as unique_customers,
            SUM(order_amount) as total_revenue,
            AVG(order_amount) as avg_order_value,
            COUNT(CASE WHEN order_status = 'completed' THEN 1 END) as completed_orders,
            COUNT(CASE WHEN order_status = 'pending' THEN 1 END) as pending_orders,
            COUNT(CASE WHEN order_status = 'cancelled' THEN 1 END) as cancelled_orders
        FROM orders_silver
        GROUP BY DATE(created_at)
    """)
    
    # Hourly real-time metrics
    spark.sql("""
        CREATE OR REPLACE TABLE orders_hourly_realtime AS
        SELECT 
            DATE_TRUNC('HOUR', event_timestamp) as hour,
            event_type,
            COUNT(*) as event_count,
            SUM(CASE WHEN event_type = 'INSERT' THEN order_amount ELSE 0 END) as new_revenue,
            COUNT(DISTINCT customer_id) as active_customers
        FROM orders_silver
        WHERE event_timestamp >= current_timestamp() - INTERVAL 24 HOURS
        GROUP BY DATE_TRUNC('HOUR', event_timestamp), event_type
    """)
    
    # Customer analytics
    spark.sql("""
        CREATE OR REPLACE TABLE customer_analytics AS
        SELECT 
            customer_id,
            COUNT(*) as total_orders,
            SUM(order_amount) as lifetime_value,
            AVG(order_amount) as avg_order_value,
            MIN(created_at) as first_order_date,
            MAX(created_at) as last_order_date,
            DATEDIFF(MAX(created_at), MIN(created_at)) as customer_tenure_days
        FROM orders_silver
        WHERE event_type = 'INSERT'
        GROUP BY customer_id
    """)
```

### Real-time Stream Processing Jobs
```python
def setup_realtime_aggregations():
    """Setup real-time aggregation streams"""
    
    # Real-time order metrics
    orders_stream = spark.readStream.table("orders_silver")
    
    # Windowed aggregations
    windowed_metrics = (orders_stream
                       .withWatermark("event_timestamp", "10 minutes")
                       .groupBy(
                           window(col("event_timestamp"), "5 minutes"),
                           col("event_type")
                       )
                       .agg(
                           count("*").alias("event_count"),
                           sum("order_amount").alias("total_amount"),
                           countDistinct("customer_id").alias("unique_customers"),
                           avg("order_amount").alias("avg_order_value")
                       )
                       .select(
                           col("window.start").alias("window_start"),
                           col("window.end").alias("window_end"),
                           col("event_type"),
                           col("event_count"),
                           col("total_amount"),
                           col("unique_customers"),
                           col("avg_order_value")
                       ))
    
    # Write windowed metrics to Delta table
    windowed_query = (windowed_metrics
                     .writeStream
                     .format("delta")
                     .outputMode("append")
                     .option("checkpointLocation", "/mnt/delta/checkpoints/windowed_metrics")
                     .trigger(processingTime='1 minute')
                     .table("orders_windowed_metrics"))
    
    return windowed_query
```

## 4. Real-time Dashboards in Databricks

### Dashboard 1: Real-time Order Monitoring

#### SQL Queries for Dashboard Widgets
```sql
-- Widget 1: Current Hour Orders
SELECT 
    COUNT(*) as current_hour_orders,
    SUM(order_amount) as current_hour_revenue
FROM orders_silver
WHERE event_timestamp >= date_trunc('hour', current_timestamp())
  AND event_type = 'INSERT'

-- Widget 2: Orders by Status (Last 24 Hours)
SELECT 
    order_status,
    COUNT(*) as order_count,
    SUM(order_amount) as revenue
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 24 HOURS
  AND event_type = 'INSERT'
GROUP BY order_status
ORDER BY order_count DESC

-- Widget 3: Hourly Order Trend (Last 24 Hours)
SELECT 
    DATE_TRUNC('HOUR', event_timestamp) as hour,
    COUNT(*) as orders,
    SUM(order_amount) as revenue
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 24 HOURS
  AND event_type = 'INSERT'
GROUP BY DATE_TRUNC('HOUR', event_timestamp)
ORDER BY hour

-- Widget 4: Top Customers (Last 7 Days)
SELECT 
    customer_id,
    COUNT(*) as order_count,
    SUM(order_amount) as total_spent
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 7 DAYS
  AND event_type = 'INSERT'
GROUP BY customer_id
ORDER BY total_spent DESC
LIMIT 10

-- Widget 5: Real-time Event Stream (Last 10 minutes)
SELECT 
    event_timestamp,
    event_type,
    order_id,
    customer_id,
    order_amount,
    order_status
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 10 MINUTES
ORDER BY event_timestamp DESC
LIMIT 20
```

### Dashboard 2: Business Intelligence Dashboard

```sql
-- Widget 1: Daily Revenue Trend (Last 30 Days)
SELECT 
    date,
    total_revenue,
    total_orders,
    avg_order_value
FROM orders_daily_metrics
WHERE date >= current_date() - INTERVAL 30 DAYS
ORDER BY date

-- Widget 2: Customer Segmentation
SELECT 
    CASE 
        WHEN lifetime_value >= 1000 THEN 'High Value'
        WHEN lifetime_value >= 500 THEN 'Medium Value'
        ELSE 'Low Value'
    END as customer_segment,
    COUNT(*) as customer_count,
    AVG(lifetime_value) as avg_lifetime_value
FROM customer_analytics
GROUP BY 1

-- Widget 3: Product Performance
SELECT 
    product_id,
    COUNT(*) as order_count,
    SUM(order_amount) as total_revenue,
    AVG(order_amount) as avg_price
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 30 DAYS
  AND event_type = 'INSERT'
GROUP BY product_id
ORDER BY total_revenue DESC
LIMIT 15

-- Widget 4: Order Status Funnel
WITH status_counts AS (
    SELECT 
        order_status,
        COUNT(*) as count
    FROM orders_silver
    WHERE event_timestamp >= current_timestamp() - INTERVAL 7 DAYS
    GROUP BY order_status
),
total_orders AS (
    SELECT SUM(count) as total FROM status_counts
)
SELECT 
    sc.order_status,
    sc.count,
    ROUND(sc.count * 100.0 / to.total, 2) as percentage
FROM status_counts sc
CROSS JOIN total_orders to
ORDER BY sc.count DESC
```

### Dashboard 3: Operational Monitoring

```sql
-- Widget 1: Data Pipeline Health
SELECT 
    'DynamoDB Streaming' as pipeline,
    CASE 
        WHEN MAX(processing_timestamp) >= current_timestamp() - INTERVAL 5 MINUTES THEN 'Healthy'
        WHEN MAX(processing_timestamp) >= current_timestamp() - INTERVAL 15 MINUTES THEN 'Warning'
        ELSE 'Critical'
    END as status,
    MAX(processing_timestamp) as last_processed,
    COUNT(*) as records_last_hour
FROM orders_silver
WHERE processing_timestamp >= current_timestamp() - INTERVAL 1 HOUR

-- Widget 2: Event Type Distribution (Last Hour)
SELECT 
    event_type,
    COUNT(*) as event_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 1 HOUR
GROUP BY event_type

-- Widget 3: Data Freshness
SELECT 
    'Orders' as table_name,
    MAX(event_timestamp) as latest_event,
    MAX(processing_timestamp) as latest_processing,
    ROUND(AVG(UNIX_TIMESTAMP(processing_timestamp) - UNIX_TIMESTAMP(event_timestamp)), 2) as avg_latency_seconds
FROM orders_silver
WHERE event_timestamp >= current_timestamp() - INTERVAL 1 HOUR

-- Widget 4: Error Monitoring
SELECT 
    DATE_TRUNC('HOUR', processing_timestamp) as hour,
    SUM(CASE WHEN event_type IS NULL OR order_id IS NULL THEN 1 ELSE 0 END) as error_count,
    COUNT(*) as total_records,
    ROUND(SUM(CASE WHEN event_type IS NULL OR order_id IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as error_rate
FROM orders_silver
WHERE processing_timestamp >= current_timestamp() - INTERVAL 24 HOURS
GROUP BY DATE_TRUNC('HOUR', processing_timestamp)
ORDER BY hour DESC
```

## 5. Advanced Analytics and Alerts

### Real-time Anomaly Detection
```python
def setup_anomaly_detection():
    """Setup real-time anomaly detection for business metrics"""
    
    # Anomaly detection using statistical methods
    anomaly_query = spark.sql("""
        WITH hourly_stats AS (
            SELECT 
                DATE_TRUNC('HOUR', event_timestamp) as hour,
                COUNT(*) as order_count,
                SUM(order_amount) as revenue
            FROM orders_silver
            WHERE event_timestamp >= current_timestamp() - INTERVAL 7 DAYS
              AND event_type = 'INSERT'
            GROUP BY DATE_TRUNC('HOUR', event_timestamp)
        ),
        stats_with_moving_avg AS (
            SELECT *,
                AVG(order_count) OVER (ORDER BY hour ROWS BETWEEN 23 PRECEDING AND 1 PRECEDING) as avg_orders_24h,
                STDDEV(order_count) OVER (ORDER BY hour ROWS BETWEEN 23 PRECEDING AND 1 PRECEDING) as stddev_orders_24h,
                AVG(revenue) OVER (ORDER BY hour ROWS BETWEEN 23 PRECEDING AND 1 PRECEDING) as avg_revenue_24h,
                STDDEV(revenue) OVER (ORDER BY hour ROWS BETWEEN 23 PRECEDING AND 1 PRECEDING) as stddev_revenue_24h
            FROM hourly_stats
        )
        SELECT *,
            CASE 
                WHEN ABS(order_count - avg_orders_24h) > 2 * stddev_orders_24h THEN 'ANOMALY'
                WHEN ABS(order_count - avg_orders_24h) > 1.5 * stddev_orders_24h THEN 'WARNING'
                ELSE 'NORMAL'
            END as order_anomaly_status,
            CASE 
                WHEN ABS(revenue - avg_revenue_24h) > 2 * stddev_revenue_24h THEN 'ANOMALY'
                WHEN ABS(revenue - avg_revenue_24h) > 1.5 * stddev_revenue_24h THEN 'WARNING'
                ELSE 'NORMAL'
            END as revenue_anomaly_status
        FROM stats_with_moving_avg
        WHERE hour >= current_timestamp() - INTERVAL 24 HOURS
        ORDER BY hour DESC
    """)
    
    return anomaly_query

# Alert configuration
def setup_alerts():
    """Setup automated alerts for critical conditions"""
    
    alert_queries = {
        "low_order_volume": """
            SELECT COUNT(*) as current_hour_orders
            FROM orders_silver
            WHERE event_timestamp >= date_trunc('hour', current_timestamp())
              AND event_type = 'INSERT'
            HAVING COUNT(*) < 10  -- Alert if less than 10 orders in current hour
        """,
        
        "high_cancellation_rate": """
            SELECT 
                COUNT(CASE WHEN order_status = 'cancelled' THEN 1 END) * 100.0 / COUNT(*) as cancellation_rate
            FROM orders_silver
            WHERE event_timestamp >= current_timestamp() - INTERVAL 1 HOUR
              AND event_type = 'INSERT'
            HAVING cancellation_rate > 15  -- Alert if cancellation rate > 15%
        """,
        
        "pipeline_lag": """
            SELECT 
                AVG(UNIX_TIMESTAMP(processing_timestamp) - UNIX_TIMESTAMP(event_timestamp)) as avg_lag_seconds
            FROM orders_silver
            WHERE event_timestamp >= current_timestamp() - INTERVAL 15 MINUTES
            HAVING avg_lag_seconds > 300  -- Alert if processing lag > 5 minutes
        """
    }
    
    return alert_queries
```

## 6. Performance Optimization

### Delta Table Optimization
```python
def optimize_performance():
    """Optimize Delta tables for better query performance"""
    
    # Optimize tables
    tables_to_optimize = [
        "orders_silver",
        "orders_daily_metrics", 
        "orders_windowed_metrics",
        "customer_analytics"
    ]
    
    for table in tables_to_optimize:
        # Optimize file sizes
        spark.sql(f"OPTIMIZE {table}")
        
        # Z-order for better query performance
        if table == "orders_silver":
            spark.sql(f"OPTIMIZE {table} ZORDER BY (customer_id, event_timestamp)")
        elif table == "orders_daily_metrics":
            spark.sql(f"OPTIMIZE {table} ZORDER BY (date)")
            
    # Enable auto-optimization
    spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
    spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
```

## 7. Deployment Configuration

### Job Scheduling and Cluster Configuration
```python
# Cluster configuration for streaming jobs
streaming_cluster_config = {
    "cluster_name": "dynamodb-streaming-cluster",
    "spark_version": "11.3.x-scala2.12",
    "node_type_id": "i3.large",
    "driver_node_type_id": "i3.large", 
    "num_workers": 3,
    "autoscale": {
        "min_workers": 2,
        "max_workers": 8
    },
    "aws_attributes": {
        "first_on_demand": 1,
        "availability": "SPOT_WITH_FALLBACK"
    },
    "spark_conf": {
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.databricks.delta.autoCompact.enabled": "true"
    }
}

# Job configuration
jobs_config = {
    "dynamodb_streaming_ingestion": {
        "schedule": "continuous",
        "cluster": "dynamodb-streaming-cluster",
        "libraries": [
            {"pypi": {"package": "boto3"}},
            {"maven": {"coordinates": "org.apache.spark:spark-sql-kinesis_2.12:3.3.0"}}
        ]
    },
    "gold_layer_batch_processing": {
        "schedule": "0 */5 * * * ?",  # Every 5 minutes
        "cluster": "dynamodb-streaming-cluster"
    },
    "historical_data_load": {
        "schedule": "manual",  # Run on-demand
        "cluster": "batch-processing-cluster"
    }
}
```

## Key Benefits

1. **Real-time Processing**: Near real-time ingestion and processing of DynamoDB changes
2. **Scalable Architecture**: Handles high-volume DynamoDB tables with auto-scaling
3. **Data Quality**: Built-in validation and monitoring
4. **Interactive Dashboards**: Real-time business intelligence and operational monitoring
5. **Cost Effective**: Uses spot instances and optimized storage
6. **Flexible**: Supports both streaming and batch processing patterns

## Implementation Steps

1. **Setup Infrastructure**: Configure DynamoDB streams and Kinesis
2. **Deploy Databricks Jobs**: Set up streaming ingestion jobs
3. **Create Delta Tables**: Implement bronze, silver, and gold layers  
4. **Build Dashboards**: Create real-time monitoring dashboards
5. **Setup Alerts**: Configure anomaly detection and alerting
6. **Optimize Performance**: Implement table optimization and caching
7. **Monitor and Scale**: Set up operational monitoring and auto-scaling

This pipeline provides a robust, scalable solution for real-time analytics on DynamoDB data with comprehensive monitoring and business intelligence capabilities.
