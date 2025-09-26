
 ## Analytical pipeline for CAN bus data on Databricks. 
 
 This pipeline follows the medallion architecture (Bronze-Silver-Gold) 
 and is designed to handle the scale and complexity of automotive telematics data from thousands of vehicles over multiple years.

## Key Highlights of the Pipeline:

**🏗️ Architecture**: 
- Uses Delta Lake for ACID transactions and time travel
- Implements streaming ingestion from S3 using Auto Loader
- Follows medallion architecture for data quality and governance

**⚡ Real-time Processing**:
- Continuous ingestion of CAN bus data
- Stream processing for immediate insights
- Real-time anomaly detection for vehicle health monitoring

**🤖 Advanced Analytics**:
- Predictive maintenance ML models
- Fleet-level performance analytics
- Vehicle health monitoring with automated alerts

**💰 Cost Optimization**:
- Auto-scaling clusters with spot instances
- Optimized Delta table storage
- Efficient partitioning strategies

**🔍 Key Features**:
- CAN message parsing and signal extraction
- Trip segmentation and feature engineering
- Data quality monitoring and validation
- Performance optimization with Z-ordering

Would you like me to elaborate on any specific component of the pipeline, such as:
- The CAN message parsing logic for your specific vehicle protocols?
- Setting up the ML models for predictive maintenance?
- Configuring the monitoring and alerting systems?
- Optimizing for your specific data volume and query patterns?

# CAN Bus Data Analytics Pipeline on Databricks

## Architecture Overview

### Data Flow Architecture
```
AWS S3 (Raw CAN Data) → Databricks Auto Loader → Bronze Layer → Silver Layer → Gold Layer → Analytics & ML
```

## 1. Data Ingestion Layer

### Auto Loader Configuration
```python
# Configure Auto Loader for continuous ingestion from S3
checkpoint_path = "/mnt/delta/checkpoints/can_bus_ingestion"
raw_data_path = "s3a://your-bucket/can-bus-data/"

df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")  # or csv, parquet based on your format
      .option("cloudFiles.schemaLocation", checkpoint_path)
      .option("cloudFiles.maxFilesPerTrigger", 1000)
      .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
      .load(raw_data_path))
```

### Schema Definition for CAN Bus Data
```python
from pyspark.sql.types import *

can_bus_schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("vehicle_id", StringType(), True),
    StructField("trip_id", StringType(), True),
    StructField("can_id", StringType(), True),
    StructField("message_data", StringType(), True),
    StructField("dlc", IntegerType(), True),  # Data Length Code
    StructField("signal_name", StringType(), True),
    StructField("signal_value", DoubleType(), True),
    StructField("unit", StringType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("ingestion_time", TimestampType(), True)
])
```

## 2. Bronze Layer (Raw Data Storage)

### Raw Data Ingestion
```python
def write_to_bronze():
    return (df.writeStream
            .format("delta")
            .option("checkpointLocation", f"{checkpoint_path}/bronze")
            .option("mergeSchema", "true")
            .partitionBy("year", "month", "day", "vehicle_id")
            .trigger(processingTime='5 minutes')
            .table("can_bus_bronze"))

bronze_stream = write_to_bronze()
```

### Data Quality Checks
```python
def bronze_data_quality_checks(df):
    """Apply data quality checks at bronze layer"""
    return (df
            .filter(col("timestamp").isNotNull())
            .filter(col("vehicle_id").isNotNull())
            .filter(col("can_id").isNotNull())
            .withColumn("data_quality_flag", 
                       when(col("signal_value").isNull(), "missing_signal_value")
                       .when(col("timestamp") < lit("2020-01-01"), "invalid_timestamp")
                       .otherwise("valid")))
```

## 3. Silver Layer (Cleaned & Enriched Data)

### CAN Message Parsing and Signal Extraction
```python
# Create a comprehensive signal mapping dictionary
signal_mappings = {
    "0x100": {"name": "engine_rpm", "formula": "value * 0.25", "unit": "rpm"},
    "0x101": {"name": "vehicle_speed", "formula": "value * 0.0625", "unit": "km/h"},
    "0x102": {"name": "engine_temp", "formula": "value - 40", "unit": "celsius"},
    "0x103": {"name": "fuel_level", "formula": "value * 0.4", "unit": "liters"},
    "0x200": {"name": "throttle_position", "formula": "value * 0.4", "unit": "percent"},
    "0x201": {"name": "brake_pressure", "formula": "value * 0.1", "unit": "bar"}
}

def parse_can_signals(df):
    """Parse CAN messages and extract meaningful signals"""
    
    # Create UDF for signal parsing
    @udf(returnType=StructType([
        StructField("parsed_signals", ArrayType(StructType([
            StructField("signal_name", StringType()),
            StructField("signal_value", DoubleType()),
            StructField("unit", StringType())
        ])))
    ]))
    def parse_can_message(can_id, message_data):
        # Implementation for parsing based on DBC files or signal mappings
        parsed = []
        if can_id in signal_mappings:
            # Extract signals based on bit positions and formulas
            # This is simplified - in practice, you'd use proper CAN parsing
            raw_value = int(message_data, 16) if message_data else 0
            signal_info = signal_mappings[can_id]
            calculated_value = eval(signal_info["formula"].replace("value", str(raw_value)))
            
            parsed.append({
                "signal_name": signal_info["name"],
                "signal_value": float(calculated_value),
                "unit": signal_info["unit"]
            })
        return parsed
    
    return (df
            .withColumn("parsed_signals", parse_can_message(col("can_id"), col("message_data")))
            .withColumn("exploded_signals", explode(col("parsed_signals")))
            .select("*", 
                   col("exploded_signals.signal_name").alias("signal_name"),
                   col("exploded_signals.signal_value").alias("signal_value"),
                   col("exploded_signals.unit").alias("unit"))
            .drop("parsed_signals", "exploded_signals"))
```

### Trip Segmentation and Feature Engineering
```python
def create_trip_features(df):
    """Create trip-level features and metrics"""
    
    window_spec = Window.partitionBy("vehicle_id", "trip_id").orderBy("timestamp")
    
    return (df
            .withColumn("trip_duration_minutes", 
                       (max("timestamp").over(window_spec).cast("long") - 
                        min("timestamp").over(window_spec).cast("long")) / 60)
            .withColumn("distance_km", 
                       sum(when(col("signal_name") == "vehicle_speed", 
                               col("signal_value") * 0.0166)).over(window_spec))  # Convert to km
            .withColumn("fuel_consumed", 
                       sum(when(col("signal_name") == "fuel_consumption_rate", 
                               col("signal_value"))).over(window_spec))
            .withColumn("max_speed", 
                       max(when(col("signal_name") == "vehicle_speed", 
                              col("signal_value"))).over(window_spec))
            .withColumn("avg_rpm", 
                       avg(when(col("signal_name") == "engine_rpm", 
                              col("signal_value"))).over(window_spec)))
```

### Silver Layer Processing
```python
def process_silver_layer():
    """Process bronze data into silver layer"""
    
    bronze_df = spark.readStream.table("can_bus_bronze")
    
    silver_df = (bronze_df
                .transform(bronze_data_quality_checks)
                .filter(col("data_quality_flag") == "valid")
                .transform(parse_can_signals)
                .transform(create_trip_features)
                .withColumn("processing_time", current_timestamp()))
    
    return (silver_df.writeStream
            .format("delta")
            .option("checkpointLocation", f"{checkpoint_path}/silver")
            .partitionBy("year", "month", "signal_name")
            .trigger(processingTime='10 minutes')
            .table("can_bus_silver"))

silver_stream = process_silver_layer()
```

## 4. Gold Layer (Aggregated Business Metrics)

### Fleet-Level Analytics
```python
def create_fleet_analytics():
    """Create fleet-level aggregated metrics"""
    
    return spark.sql("""
        CREATE OR REPLACE TABLE can_bus_gold_fleet_daily AS
        SELECT 
            DATE(timestamp) as date,
            COUNT(DISTINCT vehicle_id) as active_vehicles,
            COUNT(DISTINCT trip_id) as total_trips,
            AVG(CASE WHEN signal_name = 'fuel_efficiency' THEN signal_value END) as avg_fuel_efficiency,
            AVG(CASE WHEN signal_name = 'vehicle_speed' THEN signal_value END) as avg_speed,
            MAX(CASE WHEN signal_name = 'vehicle_speed' THEN signal_value END) as max_speed_observed,
            SUM(distance_km) as total_distance_km,
            AVG(trip_duration_minutes) as avg_trip_duration
        FROM can_bus_silver
        WHERE signal_name IN ('fuel_efficiency', 'vehicle_speed')
        GROUP BY DATE(timestamp)
    """)
```

### Vehicle Health Monitoring
```python
def create_vehicle_health_metrics():
    """Create vehicle health monitoring table"""
    
    return spark.sql("""
        CREATE OR REPLACE TABLE can_bus_gold_vehicle_health AS
        SELECT 
            vehicle_id,
            DATE(timestamp) as date,
            -- Engine health indicators
            AVG(CASE WHEN signal_name = 'engine_temp' THEN signal_value END) as avg_engine_temp,
            MAX(CASE WHEN signal_name = 'engine_temp' THEN signal_value END) as max_engine_temp,
            AVG(CASE WHEN signal_name = 'engine_rpm' THEN signal_value END) as avg_engine_rpm,
            
            -- Operational metrics
            COUNT(CASE WHEN signal_name = 'engine_temp' AND signal_value > 100 THEN 1 END) as overheating_events,
            COUNT(CASE WHEN signal_name = 'engine_rpm' AND signal_value > 6000 THEN 1 END) as high_rpm_events,
            
            -- Usage patterns
            SUM(distance_km) as daily_distance,
            COUNT(DISTINCT trip_id) as daily_trips,
            AVG(trip_duration_minutes) as avg_trip_duration
            
        FROM can_bus_silver
        GROUP BY vehicle_id, DATE(timestamp)
    """)
```

## 5. Advanced Analytics & Machine Learning

### Predictive Maintenance Model
```python
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator

def build_predictive_maintenance_model():
    """Build ML model for predictive maintenance"""
    
    # Feature engineering for ML
    feature_df = spark.sql("""
        SELECT 
            vehicle_id,
            avg_engine_temp,
            max_engine_temp,
            avg_engine_rpm,
            overheating_events,
            high_rpm_events,
            daily_distance,
            daily_trips,
            -- Target variable (days until next maintenance)
            LEAD(maintenance_date) OVER (PARTITION BY vehicle_id ORDER BY date) - date as days_to_maintenance
        FROM can_bus_gold_vehicle_health v
        LEFT JOIN vehicle_maintenance_log m ON v.vehicle_id = m.vehicle_id
        WHERE days_to_maintenance IS NOT NULL
    """)
    
    # ML Pipeline
    feature_cols = ['avg_engine_temp', 'max_engine_temp', 'avg_engine_rpm', 
                   'overheating_events', 'high_rpm_events', 'daily_distance', 'daily_trips']
    
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
    scaler = StandardScaler(inputCol="features", outputCol="scaled_features")
    rf = RandomForestRegressor(featuresCol="scaled_features", labelCol="days_to_maintenance")
    
    pipeline = Pipeline(stages=[assembler, scaler, rf])
    
    # Train model
    train_df, test_df = feature_df.randomSplit([0.8, 0.2])
    model = pipeline.fit(train_df)
    
    # Evaluate model
    predictions = model.transform(test_df)
    evaluator = RegressionEvaluator(labelCol="days_to_maintenance", metricName="rmse")
    rmse = evaluator.evaluate(predictions)
    
    print(f"Model RMSE: {rmse}")
    
    return model
```

### Real-time Anomaly Detection
```python
def setup_anomaly_detection():
    """Set up real-time anomaly detection"""
    
    # Statistical anomaly detection using z-score
    anomaly_query = spark.sql("""
        WITH signal_stats AS (
            SELECT 
                signal_name,
                AVG(signal_value) as mean_value,
                STDDEV(signal_value) as std_value
            FROM can_bus_silver
            WHERE timestamp >= current_timestamp() - INTERVAL 30 DAYS
            GROUP BY signal_name
        ),
        current_signals AS (
            SELECT 
                s.*,
                st.mean_value,
                st.std_value,
                ABS(s.signal_value - st.mean_value) / st.std_value as z_score
            FROM can_bus_silver s
            JOIN signal_stats st ON s.signal_name = st.signal_name
            WHERE s.timestamp >= current_timestamp() - INTERVAL 1 HOUR
        )
        SELECT 
            vehicle_id,
            timestamp,
            signal_name,
            signal_value,
            z_score,
            CASE 
                WHEN z_score > 3 THEN 'HIGH_ANOMALY'
                WHEN z_score > 2 THEN 'MEDIUM_ANOMALY'
                ELSE 'NORMAL'
            END as anomaly_level
        FROM current_signals
        WHERE z_score > 2
    """)
    
    return anomaly_query
```

## 6. Monitoring and Alerting

### Data Quality Monitoring
```python
def setup_data_quality_monitoring():
    """Set up comprehensive data quality monitoring"""
    
    # Create data quality metrics table
    spark.sql("""
        CREATE OR REPLACE TABLE data_quality_metrics AS
        SELECT 
            DATE(processing_time) as date,
            COUNT(*) as total_records,
            COUNT(CASE WHEN data_quality_flag = 'valid' THEN 1 END) as valid_records,
            COUNT(CASE WHEN data_quality_flag != 'valid' THEN 1 END) as invalid_records,
            COUNT(DISTINCT vehicle_id) as unique_vehicles,
            COUNT(DISTINCT trip_id) as unique_trips,
            AVG(UNIX_TIMESTAMP(processing_time) - UNIX_TIMESTAMP(timestamp)) as avg_processing_delay_seconds
        FROM can_bus_bronze
        GROUP BY DATE(processing_time)
    """)
    
    # Set up alerts for data quality issues
    quality_alerts = spark.sql("""
        SELECT *,
            CASE 
                WHEN invalid_records / total_records > 0.1 THEN 'CRITICAL'
                WHEN avg_processing_delay_seconds > 300 THEN 'WARNING'
                WHEN unique_vehicles = 0 THEN 'CRITICAL'
                ELSE 'OK'
            END as alert_level
        FROM data_quality_metrics
        WHERE date = CURRENT_DATE()
    """)
    
    return quality_alerts
```

## 7. Optimization Strategies

### Performance Optimization
```python
# Optimize Delta tables
def optimize_tables():
    """Run optimization on Delta tables"""
    
    tables = ["can_bus_bronze", "can_bus_silver", "can_bus_gold_fleet_daily", "can_bus_gold_vehicle_health"]
    
    for table in tables:
        # Optimize file sizes
        spark.sql(f"OPTIMIZE {table}")
        
        # Z-order for better query performance
        if table == "can_bus_silver":
            spark.sql(f"OPTIMIZE {table} ZORDER BY (vehicle_id, timestamp, signal_name)")
        elif table == "can_bus_bronze":
            spark.sql(f"OPTIMIZE {table} ZORDER BY (vehicle_id, timestamp)")

# Auto-compaction settings
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
```

### Cost Optimization
```python
# Configure cluster auto-scaling and spot instances
cluster_config = {
    "cluster_name": "can-bus-analytics",
    "spark_version": "11.3.x-scala2.12",
    "node_type_id": "i3.xlarge",  # Memory-optimized for large datasets
    "driver_node_type_id": "i3.xlarge",
    "num_workers": 2,
    "autoscale": {
        "min_workers": 2,
        "max_workers": 20
    },
    "aws_attributes": {
        "first_on_demand": 1,
        "availability": "SPOT_WITH_FALLBACK",
        "spot_bid_price_percent": 50
    }
}
```

## 8. Deployment and Scheduling

### Job Scheduling
```python
# Create jobs for different processing stages
jobs_config = {
    "bronze_ingestion": {
        "schedule": "continuous",
        "cluster": "can-bus-analytics",
        "notebook": "/path/to/bronze_processing"
    },
    "silver_processing": {
        "schedule": "0 */15 * * * ?",  # Every 15 minutes
        "cluster": "can-bus-analytics", 
        "notebook": "/path/to/silver_processing"
    },
    "gold_aggregation": {
        "schedule": "0 0 * * * ?",  # Hourly
        "cluster": "can-bus-analytics",
        "notebook": "/path/to/gold_processing"
    },
    "ml_training": {
        "schedule": "0 0 2 * * ?",  # Daily at 2 AM
        "cluster": "ml-cluster",
        "notebook": "/path/to/ml_training"
    }
}
```

## Key Benefits of This Pipeline

1. **Scalability**: Handles thousands of vehicles and years of data
2. **Real-time Processing**: Continuous ingestion and near real-time analytics
3. **Data Quality**: Comprehensive validation and monitoring
4. **Cost Optimization**: Auto-scaling, spot instances, and optimized storage
5. **Advanced Analytics**: ML-powered predictive maintenance and anomaly detection
6. **Modularity**: Clear separation of concerns across bronze/silver/gold layers

## Next Steps

1. Set up the Databricks workspace and configure S3 connectivity
2. Create the initial schemas and tables
3. Implement the bronze layer ingestion
4. Build and test the signal parsing logic
5. Deploy the streaming jobs
6. Set up monitoring dashboards
7. Train and deploy ML models
8. Configure alerting and notifications

This pipeline provides a robust foundation for analyzing CAN bus data at scale while maintaining data quality and enabling advanced analytics capabilities.
