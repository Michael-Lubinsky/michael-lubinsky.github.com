### Timescaldb Postgres extension

CREATE EXTENSION IF NOT EXISTS timescaledb;

Version Check:  
```sql
SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';
```



```sql


CREATE TABLE sensor_data (
  time        TIMESTAMPTZ       NOT NULL,
  sensor_id   INTEGER           NOT NULL,
  temperature DOUBLE PRECISION  NULL
);

SELECT create_hypertable('sensor_data', 'time');

SELECT time_bucket('1 hour', time) AS hour, avg(temperature)
FROM sensor_data
GROUP BY hour
ORDER BY hour;


SELECT 
  to_char(time_bucket('1 month', c), 'YYYY-MM') AS year_month,
  COUNT(*) AS record_count
FROM A
WHERE c >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY time_bucket('1 month', c)
ORDER BY year_month;

```


###  Continuous Aggregate in TimescaleDB 
A Continuous Aggregate (CAGG) in TimescaleDB is a materialized view   
that is automatically and incrementally refreshed as new data is added to the underlying hypertable.

It’s designed for efficient aggregation of time-series data, like:

- per-day, per-month counts
- rolling averages
- time-bucketed stats

| Feature                     | Regular Aggregates | Continuous Aggregates ✅ |
| --------------------------- | ------------------ | ----------------------- |
| Precomputed aggregation     | ❌ Every time       | ✅ Stored and reused     |
| Fast for large data volumes | ❌ Slow             | ✅ Very fast             |
| Incremental refresh         | ❌ Recalculate all  | ✅ Recompute only recent |
| Use `time_bucket()`         | Optional           | ✅ Required              |



### Enable compression


```sql
ALTER TABLE sensor_data SET (timescaledb.compress);
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

### How to Check if a Hypertable is Compressed
To determine if a hypertable is compressed in TimescaleDB, you can query the timescaledb_information.compression_settings view, which provides details about compression configuration for hypertables.



```sql

SELECT 
    ht.schema_name,
    ht.table_name,
    cs.compression_enabled,
    cs.segmentby,
    cs.orderby
FROM timescaledb_information.hypertables ht
LEFT JOIN timescaledb_information.compression_settings cs
    ON ht.schema_name = cs.schema_name 
    AND ht.table_name = cs.table_name
WHERE ht.table_name = 'your_hypertable_name';
```
Explanation:
timescaledb_information.hypertables: Lists all hypertables.
timescaledb_information.compression_settings: Contains compression settings for hypertables.
compression_enabled: Indicates if compression is enabled (true or false).  
If compression_enabled is true, the hypertable has compression enabled.   
If false or NULL, compression is not enabled.

Alternative: To check if any data is actually compressed,   
query the timescaledb_information.compressed_chunk_stats view:

```sql

SELECT 
    chunk_schema,
    chunk_name,
    compression_status,
    uncompressed_total_bytes,
    compressed_total_bytes
FROM timescaledb_information.compressed_chunk_stats
WHERE hypertable_name = 'your_hypertable_name';
```
Explanation:
compression_status: Shows whether the chunk is compressed (Compressed) or not.  
compressed_total_bytes: Indicates the size of compressed data, confirming compression is active.  
If no rows are returned or compression_status is not Compressed, no chunks are compressed.


Notes:


Compression must be explicitly enabled using 
```sql
ALTER TABLE your_hypertable_name SET (timescaledb.compress = true)
```
It allow chunks of this hypertable to be compressed manually or by policy.

This does not compress any chunks yet — it only enables compression.

You must still:

- Define which columns to segment and order by (optional but recommended)

- Manually compress chunks with SELECT compress_chunk(...)
  or
- Schedule auto compression with:

```sql

SELECT add_compression_policy('your_hypertable_name', INTERVAL '7 days');
```

✅ Example full setup:
```sql

-- Enable compression on the hypertable
ALTER TABLE sensor_data SET (timescaledb.compress = true);

-- Define how data is organized inside compressed chunks
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
SELECT set_chunk_compression('sensor_data', 'sensor_id', 'time');
```



Manually compress a specific chunk of a hypertable:
```sql
SELECT compress_chunk(chunk_name).
```

###  TimescaleDB-Specific SQL Functions to Filter Columns by Timestamp
TimescaleDB provides several functions to efficiently filter or manipulate timestamp-based data in hypertables. These functions are optimized for time-series data and work well with timestamp columns. 
Below are the key TimescaleDB-specific SQL functions for filtering by timestamp:  

#### time_bucket(bucket_width, ts_column):

Groups timestamps into fixed-size buckets (e.g., 1 hour, 1 day).  
Useful for aggregating data over time intervals.
Example:

```sql

SELECT 
  to_char(time_bucket('1 month', c), 'YYYY-MM') AS year_month,
  COUNT(*) AS record_count
FROM A
GROUP BY time_bucket('1 month', c)
ORDER BY year_month;

```
The SQL above has standard SQL equivalent, which runs slow:

```
SELECT 
  to_char(date_trunc('month', c), 'YYYY-MM') AS year_month,
  COUNT(*) AS record_count
FROM A
GROUP BY date_trunc('month', c)
ORDER BY year_month;
```


```

SELECT time_bucket('1 hour', time_column) AS bucket, COUNT(*)
FROM your_hypertable_name
WHERE time_column >= '2025-01-01' AND time_column < '2025-01-02'
GROUP BY bucket;
```
Filters rows by time_column and groups them into hourly buckets.


#### time_bucket_gapfill(bucket_width, ts_column, start, end):

Similar to time_bucket, but fills in missing buckets with NULL or interpolated values within the specified start and end timestamp range.

```sql

SELECT time_bucket_gapfill('1 day', time_column, '2025-01-01', '2025-01-07') AS bucket, 
       COALESCE(AVG(value), 0) AS avg_value
FROM your_hypertable_name
WHERE time_column >= '2025-01-01' AND time_column < '2025-01-07'
GROUP BY bucket;
```


Filters rows and ensures all daily buckets are returned, even if no data exists.



### first(value_column, ts_column) and last(value_column, ts_column):
Retrieves the first or last value of a column within a time range, ordered by the timestamp column.


```sql
SELECT first(value_column, time_column) AS first_value
FROM your_hypertable_name
WHERE time_column BETWEEN '2025-01-01' AND '2025-01-02';
```


Filters rows by time_column and returns the earliest value_column in the range.  

#### histogram(ts_column, min_value, max_value, num_bins):  
Creates a histogram of values within a timestamp range (though typically used for numeric columns,  
can be paired with timestamp filtering).

```sql

SELECT time_bucket('1 hour', time_column) AS bucket, 
       histogram(value_column, 0, 100, 10)
FROM your_hypertable_name
WHERE time_column >= '2025-01-01' AND time_column < '2025-01-02'
GROUP BY bucket;
```

Filters by timestamp and generates histograms for each time bucket.

#### locf(value_column):
Last Observation Carried Forward: Fills missing values with the last non-null value, often used with timestamp filtering.

```sql

SELECT time_bucket_gapfill('1 hour', time_column) AS bucket, 
       locf(AVG(value_column)) AS filled_value
FROM your_hypertable_name
WHERE time_column >= '2025-01-01' AND time_column < '2025-01-02'
GROUP BY bucket;
```

Filters by timestamp and fills gaps in data.  
Standard SQL with Hypertable Optimization:  
TimescaleDB optimizes standard PostgreSQL WHERE clauses on timestamp columns  
(e.g., WHERE time_column BETWEEN '2025-01-01' AND '2025-01-02').

Hypertables use chunk-based partitioning, so timestamp filters leverage this for efficient query execution.
Notes:

Replace time_column with your hypertable’s timestamp column and your_hypertable_name with your table name.
These functions are most effective when used with hypertables, as TimescaleDB optimizes them for time-series data.
Always ensure the timestamp column is indexed (automatically done for the time dimension in hypertables).

### Additional Notes
Compression and Filtering: If your hypertable is compressed, you can still use these functions. 
TimescaleDB transparently decompresses chunks as needed for queries.  

Performance: For large datasets, ensure your timestamp column is used in WHERE clauses to leverage chunk exclusion, and consider adding secondary indexes if filtering on other columns.

<https://medium.com/timescale/handling-billions-of-rows-in-postgresql-80d3bd24dabb>
