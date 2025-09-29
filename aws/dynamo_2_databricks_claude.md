# Streaming data from Databricks to S3 with low latency and immediate visibility

## Architecture Overview

**Databricks → S3 → Databricks** with ~1 minute end-to-end latency

## Implementation Approach

### 1. **Stream Data to S3 Using Structured Streaming**

Use Databricks Structured Streaming to continuously write data to S3:

```python
# Read from your source tables as a stream
df_stream = spark.readStream \
    .format("delta")  # or your table format
    .table("your_database.your_table")

# Write to S3 with trigger interval
df_stream.writeStream \
    .format("parquet")  # or delta
    .outputMode("append") \
    .option("checkpointLocation", "s3://your-bucket/checkpoints/table_name") \
    .option("path", "s3://your-bucket/data/table_name") \
    .trigger(processingTime="30 seconds")  # Adjust based on your latency needs
    .start()
```

### 2. **Make S3 Data Immediately Visible in Databricks**

You have several options:

#### **Option A: Delta Lake with Auto Loader (Recommended)**

Write to S3 as Delta format and use Auto Loader to read it back:

**Write side:**
```python
df_stream.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "s3://your-bucket/checkpoints/write") \
    .option("path", "s3://your-bucket/delta/table_name") \
    .trigger(processingTime="30 seconds") \
    .start()
```

**Read side (create external table):**
```sql
CREATE TABLE IF NOT EXISTS s3_synced_table
USING DELTA
LOCATION 's3://your-bucket/delta/table_name';

-- Query with automatic metadata refresh
SELECT * FROM s3_synced_table;
```

Delta Lake automatically handles metadata, making new data visible immediately.

#### **Option B: Hive Metastore with MSCK REPAIR**

If using Parquet/ORC, automate partition discovery:

```python
# After writing, repair table (can be scheduled)
spark.sql("MSCK REPAIR TABLE s3_synced_table")

# Or use Auto Loader with cloudFiles
df = spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.format", "parquet") \
    .option("cloudFiles.schemaLocation", "s3://your-bucket/schema") \
    .load("s3://your-bucket/data/table_name")
```

#### **Option C: External Table with Auto Refresh**

```sql
CREATE TABLE s3_synced_table
USING parquet
LOCATION 's3://your-bucket/data/table_name'
TBLPROPERTIES (
    'spark.sql.streaming.schemaInference' = 'true'
);

-- Enable auto refresh (Databricks SQL specific)
ALTER TABLE s3_synced_table 
SET TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true');
```

## Complete End-to-End Example

```python
# 1. Stream from Databricks tables to S3
def stream_to_s3(source_table, s3_path):
    df = spark.readStream \
        .format("delta") \
        .table(source_table)
    
    query = df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", f"{s3_path}/_checkpoints") \
        .option("path", f"{s3_path}/data") \
        .trigger(processingTime="30 seconds") \
        .start()
    
    return query

# 2. Create external Delta table pointing to S3
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS s3_synced_table
    USING DELTA
    LOCATION 's3://your-bucket/delta/table_name/data'
""")

# 3. Query the data (automatically sees new files)
spark.sql("SELECT * FROM s3_synced_table WHERE timestamp > current_timestamp() - INTERVAL 1 MINUTE")
```

## Key Considerations

1. **Latency Optimization:**
   - Set `trigger(processingTime="30 seconds")` or `trigger(once=True)` for batch
   - Use smaller file sizes for faster writes
   - Consider partitioning by time (e.g., hour) for better performance

2. **S3 Credentials:**
   - Configure IAM roles or instance profiles
   - Or set credentials in Spark config:
   ```python
   spark.conf.set("fs.s3a.access.key", "YOUR_ACCESS_KEY")
   spark.conf.set("fs.s3a.secret.key", "YOUR_SECRET_KEY")
   ```

3. **Cost Optimization:**
   - Use Delta Lake's `optimizeWrite` to reduce small files
   - Implement periodic `OPTIMIZE` and `VACUUM` operations

4. **Monitoring:**
   - Track streaming query metrics
   - Set up alerts for checkpoint failures

This approach gives you ~1 minute latency (30s write trigger + processing time) with immediate visibility through Delta Lake's transactional guarantees.

Would you like me to elaborate on any specific part of this solution?
