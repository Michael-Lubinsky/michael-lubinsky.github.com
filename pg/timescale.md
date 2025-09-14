### Timescaldb Postgres extension

CREATE EXTENSION IF NOT EXISTS timescaledb;

Version Check - Make sure it's version 2.0 or higher fo compression support:  
```sql
SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';
```

## To to see  partition intervals in hours 
To see the partition intervals in hours for a TimescaleDB hypertable in PostgreSQL,   
you can query the `timescaledb_information.hypertables` and `timescaledb_information.chunks` views.

### 1. Find the Partition Interval

 

```sql
SELECT 
     hypertable_schema,
     hypertable_name,
     time_interval  
FROM timescaledb_information.dimensions
WHERE dimension_type = 'Time';

```

 

```sql
SELECT *
FROM    timescaledb_information.hypertables

```


### 2. See Partitions for a Specific Table

To see the actual partitions (chunks) for a hypertable, you can query the `timescaledb_information.chunks` view. This view lists all the individual chunks that make up your hypertable.

```sql
SELECT
    chunk_name,
    range_start,
    range_end
FROM
    timescaledb_information.chunks
WHERE
    hypertable_name = 'your_hypertable_name'
ORDER BY
    range_start DESC;
```

This will show you each chunk's name and the start and end timestamps of its time interval. The difference between `range_end` and `range_start` should equal the `chunk_time_interval` you found earlier.

If you are using Azure Database for PostgreSQL - Flexible Server, and TimescaleDB is enabled,

### Compression support
Then compression is supported if 
- You're using TimescaleDB 2.x+  
- And you are using community edition features (not enterprise-only)

✅ Columnar compression (introduced in TimescaleDB 2.7+) is enterprise-only and not available by default on Azure unless you bring your own license.

 Azure PostgreSQL **Single Server**: TimescaleDB may be available, but:

Compression is generally not supported or is outdated, depending on the version Azure provides.


Then test this:

```sql
SELECT * FROM timescaledb_information.hypertables;
```
If you see a column named compression_enabled, you're good to go.

🛠️ Enable Compression (if supported), for example:

```sql

-- Enable compression on a hypertable
ALTER TABLE your_table SET (
  timescaledb.compress,
  timescaledb.compress_orderby = 'time DESC',
  timescaledb.compress_segmentby = 'device_id'
);

-- Add a compression policy
SELECT add_compression_policy('your_table', INTERVAL '30 days');
```

⚠️ Notes
Compression in TimescaleDB is only available on hypertables, not regular tables.

On Azure, compression is subject to Timescale license (Apache 2.0 for core features, Timescale License for some advanced ones).




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

### time_bucket() vs date_trunc() in TimescaleDB context

| Feature                   | `date_trunc()` | `time_bucket()` (✅ TimescaleDB)     |
| ------------------------- | -------------- | ----------------------------------- |
| Standard SQL              | ✅ Yes          | ❌ Extension-specific                |
| Works with TimescaleDB    | ✅ Partially    | ✅ Fully optimized                   |
| Required for CAGGs        | ❌ No           | ✅ **Yes** (must use `time_bucket`)  |
| Chunk-aware optimizations | ❌ No           | ✅ Yes                               |
| Continuous Aggregates use | ❌ Invalid      | ✅ **Required** in `GROUP BY` clause |




#### When to use time_bucket()?
- Always use time_bucket() in SELECT/aggregation queries over hypertables  
- Use it in GROUP BY for continuous aggregates — it's required  
- Use it in filtering (WHERE) only if matching bucket-aligned boundaries  

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



TimescaleDB does not use cron-like scheduling for add_continuous_aggregate_policy.   
It relies on a background job that wakes up every schedule_interval and checks whether the data range needs refreshing.

So:

⛔️ You cannot directly say "run only on the 1st of the month" in add_continuous_aggregate_policy.

✅ Practical solution (match your goal)
To approximate “once per month on the 1st”, use:

```sql

SELECT add_continuous_aggregate_policy('monthly_counts',
  start_offset => INTERVAL '2 months',
  end_offset   => INTERVAL '1 month',
  schedule_interval => INTERVAL '1 day');
```
🔍 What this does:
schedule_interval => '1 day': check once per day (low load)

start_offset => '2 months': refresh two months back

end_offset => '1 month': excludes the most recent month (assumed to be still collecting)

On the 1st day of the new month, the system will:

Recompute data for the just-completed month

Skip the current (in-progress) month

This pattern ensures monthly refresh behavior, even if it's not cron-based.






⏱ Optional: Manual control instead
If you want absolute control, disable the automatic policy and just run this manually via pg_cron:

```sql

CALL refresh_continuous_aggregate('monthly_counts',
  date_trunc('month', now() - interval '1 month'),
  date_trunc('month', now()));
```
Then schedule this in pg_cron:

```sql

SELECT cron.schedule(
  'refresh_monthly_counts',
  '0 0 1 * *',
  $$CALL refresh_continuous_aggregate('monthly_counts',
    date_trunc('month', now() - interval '1 month'),
    date_trunc('month', now()));$$
);
```
This gives you cron-like exact timing.



You should use date_trunc() in refresh_continuous_aggregate() time boundaries:

```sql

CALL refresh_continuous_aggregate('monthly_counts',
  date_trunc('month', now() - interval '1 month'),
  date_trunc('month', now()));
```
Why?
refresh_continuous_aggregate() requires exact timestamps

It defines the raw time range to refresh, not how it's grouped

time_bucket() is not appropriate here — it's for grouping inside the materialized view


| Use case                           | Recommended Function |
| ---------------------------------- | -------------------- |
| Creating continuous aggregate view | `time_bucket()` ✅    |
| Querying time-series buckets       | `time_bucket()` ✅    |
| Specifying refresh time range      | `date_trunc()` ✅     |


```sql
CREATE MATERIALIZED VIEW monthly_counts
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 month', c) AS bucket,
  COUNT(*) AS record_count
FROM A
GROUP BY bucket
WITH NO DATA; --  means it won't populate until you run REFRESH


CALL refresh_continuous_aggregate('monthly_counts', NULL, NULL);


SELECT add_continuous_aggregate_policy('monthly_counts',
  start_offset => INTERVAL '1 month', -- refreshes up to 1 month ago
  end_offset   => INTERVAL '1 day', --  skips the most recent day (in case data is still arriving)
  schedule_interval => INTERVAL '1 hour'); checks every hour
```

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

```sql
SELECT 
  to_char(date_trunc('month', c), 'YYYY-MM') AS year_month,
  COUNT(*) AS record_count
FROM A
GROUP BY date_trunc('month', c)
ORDER BY year_month;
```


```sql
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
