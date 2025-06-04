SHOW WAREHOUSES;

### Snowflake Core Concepts & Architecture

Three-layer architecture:

- Database Storage – Optimized, compressed, columnar storage in cloud blob storage
- Compute Layer – Independent virtual warehouses (clusters)
- Cloud Services Layer – Metadata management, authentication, query optimization

### Virtual Warehouses:

Decoupled compute  
Can auto-scale (multi-cluster)  
Pausable to save costs  

In Snowflake, Virtual Warehouses are the compute layer responsible for executing queries, 
loading data, and performing transformations.
They are independent of storage and can be scaled, paused, resumed, and configured per workload.

| Size             | Credits per Hour | Typical Use                                       |
| ---------------- | ---------------- | ------------------------------------------------- |
| `X-Small`        | 1                | Small dev/test jobs, occasional queries           |
| `Small`          | 2                | Light dashboards, routine ETL                     |
| `Medium`         | 4                | Moderate ELT, daily batch                         |
| `Large`          | 8                | Large dashboards, joins                           |
| `XLarge`         | 16               | Complex ETL, concurrent workloads                 |
| Up to `6X-Large` | Up to 512        | Massive parallelism for real-time/high-throughput |

| Policy     | Behavior                                            |
| ---------- | --------------------------------------------------- |
| `STANDARD` | Spins up extra clusters *as needed* for concurrency |
| `ECONOMY`  | Delays adding clusters to save cost                 |



###  Real-World Pricing Note
1 credit ≈ $2–$4 USD, depending on:

- Cloud provider (AWS, Azure, GCP)
- Region
- Contract type (on-demand vs reserved capacity)

For example:

- X-Small → ~$2–$4/hour
- Small → ~$4–$8/hour
- Medium → ~$8–$16/hour
- Large → ~$16–$32/hour

Actual rates depend on your Snowflake subscription agreement.
Always refer to your contract or Snowflake Pricing Calculator for accurate cost estimation.




To track when your warehouse scaled:
```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE WAREHOUSE_NAME = 'BI_WH'
ORDER BY START_TIME DESC;
```

#### What is CREDIT_QUOTA?
The CREDIT_QUOTA specifies how many Snowflake credits a monitor is allowed to consume during its interval period (monthly by default).

- 1 credit = 1 hour of X-Small warehouse usage
- Larger warehouses consume more credits proportionally (e.g., Large = 8 credits/hour)


### What is cluster?

In Snowflake, a cluster refers to an independent compute engine within a virtual warehouse. It is a unit of compute that executes queries, loads data, or performs transformations.

🧱 What Is a Cluster in Snowflake?
A cluster is part of a virtual warehouse and contains:
- CPU
- Memory
- Temp disk/cache

Each cluster runs queries independently and does not share memory or CPU with others.

A multi-cluster warehouse can have multiple clusters running in parallel,   
enabling horizontal scaling for high-concurrency workloads.


### Use Case for Multi-Cluster Warehouses
Multi-cluster mode is ideal for:

- High concurrent query workloads
- BI dashboards (many short queries)
- Concurrent ELT jobs or streaming workloads
- Instead of queueing, Snowflake adds new clusters to serve more users simultaneously.


When you configure a multi-cluster warehouse, you define:

- MIN_CLUSTER_COUNT — the minimum number of clusters always running
- MAX_CLUSTER_COUNT (or SCALE_MAX) — the maximum number of clusters that can run concurrently

```sql
CREATE WAREHOUSE bi_wh
  WAREHOUSE_SIZE = 'MEDIUM'
  WAREHOUSE_TYPE = 'MULTI'
  MIN_CLUSTER_COUNT = 1
  MAX_CLUSTER_COUNT = 5
  SCALING_POLICY = 'STANDARD'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;
```


#### Scaling policy

SCALE_MIN / SCALE_MAX clusters
Controls multi-cluster warehouse behavior

If many queries queue up, Snowflake automatically spins up additional clusters to avoid queueing
```sql
CREATE WAREHOUSE my_wh
  WAREHOUSE_SIZE = 'LARGE'
  MAX_CLUSTER_COUNT = 5
  MIN_CLUSTER_COUNT = 1
  SCALING_POLICY = 'ECONOMY'; -- Or 'STANDARD'

AUTO_SUSPEND = 300  -- in seconds
AUTO_RESUME = TRUE

```
Changing Warehouse Configs  
Snowflake allows dynamic resizing and reconfiguration:
```sql
ALTER WAREHOUSE my_wh SET WAREHOUSE_SIZE = 'XLARGE';
ALTER WAREHOUSE my_wh SET AUTO_SUSPEND = 60;
```

| Scenario         | Suggested Config                                        |
| ---------------- | ------------------------------------------------------- |
| Ad-hoc dev       | `X-Small` + auto-suspend 60s                            |
| Daily ETL        | `Large`, auto-resume, auto-suspend 300s                 |
| Dashboards       | `Medium`, multi-cluster (`MAX_CLUSTER_COUNT > 1`)       |
| High concurrency | `XLarge`, `STANDARD` scaling policy, short suspend time |
| Cost control     | Always use **resource monitors** and auto-suspend       |

| Term                        | Meaning                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------ |
| **Cluster**                 | One compute engine within a virtual warehouse                                        |
| **Virtual Warehouse**       | Logical group of clusters for processing                                             |
| **Multi-Cluster Warehouse** | A warehouse with multiple clusters for concurrent execution                          |
| **Scaling**                 | Snowflake adds or removes clusters based on query demand and `MIN/MAX_CLUSTER_COUNT` |


### Micro-partitions:
Immutable 16MB–512MB blocks  
Automatically created on data ingestion  
Columnar, sorted, compressed, metadata-rich  


During peak reporting times, you might spin up a large warehouse, 
and then during off-peak hours, you can suspend it
(stopping compute charges entirely) or resize it to a smaller size.

Multi-Cluster Architecture: Snowflake's architecture allows multiple independent compute clusters
(virtual warehouses) to operate on the same data concurrently without contention.

While there's a Cloud Services layer that handles things like authentication, query optimization, and metadata management,
its usage is often free as long as it doesn't exceed 10% of your daily virtual warehouse compute credit usage.

##  End-to-End ETL / ELT Process

When would you use ELT over ETL?

ELT is preferred in Snowflake due to its compute scalability and SQL-based transformations. 
Ingestion tools: Fivetran, Stitch, Airbyte, custom scripts  
Transformations: dbt, stored procedures, or SQL views

### Typical flow:

Load raw data (via Snowpipe, COPY INTO, connectors)  
Stage it (usually raw or staging schema)  
Apply transformation logic (SQL/dbt models)  
Load into analytics layer (star schema / data mart)  

##  Monitoring and Optimization

Use Account Usage and Information Schema:

- QUERY_HISTORY, WAREHOUSE_LOAD_HISTORY, METERING_HISTORY
- Track long-running or costly queries
- Visualize with dashboards (e.g., in Power BI or Tableau)

### Resource Monitors (Cost Control)
You can bind a resource monitor to a warehouse to track/limit credit usage.

```sql
  CREATE RESOURCE MONITOR etl_monitor
  WITH CREDIT_QUOTA = 100
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE etl_wh SET RESOURCE_MONITOR = etl_monitor;
```
This means: once 80 credits are consumed → send a notification;  
when 100 credits are consumed → suspend assigned warehouses.

A resource monitor allows you to:

- Track credit usage
- Define threshold-based triggers (e.g., 80%, 100%)
- Automatically notify, suspend warehouses, or disable further usage

#### Monitoring Interval Options
By default, the interval is monthly, but you can change it to:

- DAILY
- WEEKLY
- MONTHLY
- YEARLY
- NEVER (one-time monitor)

 ```sql
CREATE RESOURCE MONITOR etl_monitor
  WITH CREDIT_QUOTA = 100
  FREQUENCY = DAILY
  TRIGGERS ON 90 PERCENT DO SUSPEND;
 ```

### Who Gets Notified by DO NOTIFY?
Notifications are sent to account administrators (users with ACCOUNTADMIN role).  
They appear in the Snowflake UI (Notifications tab) and can be queried via metadata views.  
You can also configure notification integrations with email, Slack, webhooks, or custom logging,  
but that requires external alerting tools (like PagerDuty or AWS SNS via monitoring dashboards).

Assigning Resource Monitor to a Warehouse:
 
ALTER WAREHOUSE etl_wh SET RESOURCE_MONITOR = etl_monitor;

A resource monitor can be shared across multiple warehouses.

You can check usage and trigger activity with:
```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.RESOURCE_MONITOR_HISTORY
WHERE MONITOR_NAME = 'ETL_MONITOR'
ORDER BY USAGE_DATE DESC;
```

###  Optimization Tips:
Use clustering keys on large tables with frequent range scans  
Use result caching effectively  
Use materialized views for performance  
Scale compute vertically or horizontally (multi-cluster warehouses)

### Cost Control:
Suspend warehouses when not in use
Set resource monitors to cap credit consumption
Use serverless functions (Tasks, Streams) with care (billed per second)

##  Internal Workings (Deep Dive)
How does Snowflake handle concurrent queries?  
What happens behind the scenes when you run a query?  
How does Snowflake achieve scalability?  

Each virtual warehouse handles queries independently → no contention.
Queries use metadata from the cloud services layer to find optimal micro-partitions.
Automatic query optimization based on metadata (e.g., pruning, caching).

### Data Ingestion & Loading
How do you load data into Snowflake?

What is Snowpipe and how is it different from COPY INTO?

| Method              | Use Case                                                          |
| ------------------- | ----------------------------------------------------------------- |
| `COPY INTO`         | Bulk, manual or scheduled ingestion                               |
| **Snowpipe**        | Continuous ingestion with **event triggers** (e.g., from S3, GCS) |
| **External Tables** | Read directly from cloud storage without ingestion                |
| **Streams + Tasks** | Enable **incremental processing** and change data capture (CDC)   |


## Transformations and Automation
How do you orchestrate ELT in Snowflake?  
How do you ensure data quality and freshness?  


#### dbt (Data Build Tool):

SQL-first transformation layer
Version-controlled
Supports incremental models, tests, and documentation

#### Tasks + Streams:

Automate incremental logic (e.g., insert/update only changed records)

Use SQL-based logic or call external services (e.g., via external functions)

## Data Governance, Security, and Access Control

How do you enforce data security in Snowflake?  
What is the difference between role-based access and row access policies?  

💡 Techniques:
RBAC (Role-Based Access Control)  
Row Access Policies: Dynamic filtering based on user context  
Dynamic Data Masking: Show/hide sensitive values based on role  
Object-level & Column-level permissions  
Audit logs via LOGIN_HISTORY and ACCESS_HISTORY

###  Testing & Data Quality
 
Use dbt tests: unique, not_null, relationships

Build custom test queries using EXCEPT or ROW COUNT COMPARISONS

Log exceptions in an error table and monitor regularly

###
Be cost-aware: 
Snowflake charges per-second compute and per-TB storage—mention how you optimized.

### Project:
 Please describe how to design and implement in Snowflake the following ETL pipeline.
There are 3 input datasets as below.

Input  dataset 1:  100 millions rows daily.
Files on AWS S3  the daily clickstream.
Every row has following columns:
timestamp, action (can be START or STOP or PAUSE), user_id, movie_id, device_type, operating_system.
File format: AVRO or CSV.
AWS S3 buckets are named as YYYY-MM-DD

Input dataset 2: 50,000 records
Dataset of movies stored  on S3 in JSONL format, has movie_id attribute and many other attributes per movie (movie_name, genre, date, language, artists) 


Input Dataset 3:  50 millions records
This is users dataset, it has user_id and  other users attributes, like user_name, user_location, etc 

QUESTIONS:
How to load 3 input datasets into SnowFlake once per day?
Which Datawarehouse configuration to use?
How to cluster the tables?
How to join  datasets on columns  show_id and to calculate total time per movie per genre for given time range? 
How to join   datasets on columns user_id  to calculate total time per user? 

How to use QUERY_HISTORY, WAREHOUSE_LOAD_HISTORY, METERING_HISTORY?
How to Track long-running or costly queries?


### Ingestion Method:

Use Snowpipe if you want continuous streaming (optional)  
For batch ETL: use COPY INTO command from external stage  
```sql
#--------
# clicks
#--------

CREATE STAGE clickstream_stage 
  URL = 's3://bucket/'
  FILE_FORMAT = (TYPE = 'AVRO');  -- or CSV

COPY INTO raw.clickstream
FROM @clickstream_stage/YYYY-MM-DD/
FILE_FORMAT = (TYPE = 'AVRO');

#------------------
#  movies (JSONL)
#------------------
CREATE STAGE movies_stage URL = 's3://bucket/movies/';
CREATE OR REPLACE TABLE raw.movies_json (
    movie VARIANT
);

COPY INTO raw.movies_json
FROM @movies_stage
FILE_FORMAT = (TYPE = JSON);

-- Normalize JSONL into flat columns
CREATE OR REPLACE TABLE raw.movies AS
SELECT 
  movie:value:id::STRING AS movie_id,
  movie:value:genre::STRING AS genre,
  movie:value:movie_name::STRING,
  ...
FROM raw.movies_json;

#----------
#   users
# ---------
COPY INTO raw.users
FROM @users_stage
FILE_FORMAT = (TYPE = 'CSV');
```

### Data Warehouse Configuration
❄️ Recommended Snowflake Configuration
Dedicated Virtual Warehouse: For loading and transformations
- ETL_WH: X-Large or 2X-Large (scale based on load time SLA)
- Enable auto-suspend (5 minutes) and auto-resume

###  Warehousing Strategy
Separate warehouses for:
 - ETL_WH: Loading and transforms
- BI_WH: Dashboarding or query use
- Enables concurrency and cost control

### Schema & Clustering Design

| Table         | Primary Key            | Cluster Key                      |
| ------------- | ---------------------- | -------------------------------- |
| `clickstream` | `(timestamp, user_id)` | `movie_id`, `timestamp`          |
| `movies`      | `movie_id`             | `genre`                          |
| `users`       | `user_id`              | optional (large dimension table) |


- Cluster clickstream on movie_id and timestamp for time-range and movie queries.
- Optional: Set clustering key on users(user_id) if lookups are frequent and the table is very large.
```sql
CREATE TABLE clickstream (
  timestamp TIMESTAMP,
  action STRING,
  user_id STRING,
  movie_id STRING,
  ...
)
CLUSTER BY (movie_id, timestamp);
```

### Compute Total Time per Movie per Genre

```sql
WITH sessions AS (
  SELECT
    user_id,
    movie_id,
    timestamp,
    LAG(timestamp) OVER (PARTITION BY user_id, movie_id ORDER BY timestamp) AS prev_ts,
    LAG(action) OVER (PARTITION BY user_id, movie_id ORDER BY timestamp) AS prev_action,
    action
  FROM raw.clickstream
)
SELECT
  s.movie_id,
  m.genre,
  SUM(DATEDIFF('second', s.prev_ts, s.timestamp)) AS total_watch_time_seconds
FROM sessions s
JOIN raw.movies m ON s.movie_id = m.movie_id
WHERE s.prev_action = 'START' AND s.action = 'STOP'
  AND s.timestamp BETWEEN '2025-06-01' AND '2025-06-03'
GROUP BY s.movie_id, m.genre;

```

### Compute Total Time per User
```sql
WITH sessions AS (...) -- same as above
SELECT
  s.user_id,
  u.user_location,
  SUM(DATEDIFF('second', s.prev_ts, s.timestamp)) AS total_watch_time
FROM sessions s
JOIN raw.users u ON s.user_id = u.user_id
WHERE s.prev_action = 'START' AND s.action = 'STOP'
GROUP BY s.user_id, u.user_location;
```

### Query Monitoring and Cost Management

#### QUERY_HISTORY
```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND EXECUTION_STATUS = 'SUCCESS'
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 10;


SELECT QUERY_TEXT,
       EXECUTION_STATUS,
       TOTAL_ELAPSED_TIME,
       BYTES_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME > DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 10;

```
Find slowest queries  
Look at BYTES_SCANNED, ROWS_PRODUCED, WAREHOUSE_NAME


#### WAREHOUSE_LOAD_HISTORY
```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD(day, -1, CURRENT_TIMESTAMP());
```
Shows how loaded the warehouses are  
Key for tuning size and concurrency scaling

#### METERING_HISTORY

```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP());
```
Monitor credit usage per warehouse

Identify underutilized or costly compute resources


| Area               | Best Practice                                                           |
| ------------------ | ----------------------------------------------------------------------- |
| **Loading**        | Use `COPY INTO` with external stages; Snowpipe for streaming            |
| **Partitioning**   | Use clustering on large fact tables (`movie_id`, `timestamp`)           |
| **Query Tuning**   | Use pruning, materialized views, avoid `SELECT *`                       |
| **Monitoring**     | Query/warehouse/metering history; set resource monitors                 |
| **Cost Control**   | Enable auto-suspend, separate compute workloads, use `COST_USAGE` views |
| **Transformation** | Prefer ELT using SQL/dbt; optimize joins and use CTEs where appropriate |


### Tips for Efficient Use of CLUSTER BY

| Tip                                             | Explanation                                                                |
| ----------------------------------------------- | -------------------------------------------------------------------------- |
| **Use only when table is large**                | Recommended for tables **>100M rows** or growing fast.                     |
| **Cluster only on frequently filtered columns** | Use `CLUSTER BY (event_time)` only if queries consistently filter on it.   |
| **Avoid over-clustering**                       | Don't include too many columns; it may increase costs due to reclustering. |
| **Monitor clustering effectiveness**            | Use `SYSTEM$CLUSTERING_INFORMATION('table_name')`                          |
| **Avoid frequent inserts in random order**      | Clustered tables work best with **bulk inserts ordered by cluster key**.   |


#### Check Clustering Effectiveness

SELECT SYSTEM$CLUSTERING_INFORMATION('clickstream');

This returns a JSON object with:
- cluster_by_keys
- total_partition_count
- average_overlaps (lower is better)
- average_depth

You can use this to decide whether to manually recluster or optimize insert strategy.

In Snowflake, reclustering is the background process that reorganizes a table's micro-partitions to better align with the defined CLUSTER BY key(s).   
This improves query performance by maximizing partition pruning and minimizing the amount of data scanned.

very table in Snowflake is internally divided into immutable micro-partitions (16MB–512MB each).

Each micro-partition stores metadata about the min/max values of columns, which Snowflake uses for partition pruning.

Over time, due to inserts, deletes, and updates, the ordering of clustering keys across micro-partitions becomes less optimal.

What Reclustering Does
Reclustering is Snowflake's way of:

Rewriting micro-partitions so that values of the CLUSTER BY column(s) are more contiguously distributed

Reducing the overlap in clustering key values across micro-partitions

Enabling better query pruning → faster performance and lower cost

🔄 Types of Reclustering in Snowflake
✅ 1. Automatic Reclustering (Default)
Snowflake automatically reclusters large tables that use CLUSTER BY, as a background maintenance operation.

It's asynchronous, does not lock the table, and is incremental (operates on a small subset of data).

Triggered based on heuristics like:

Overlap of clustering key values

Number of stale micro-partitions

You don't need to manage it manually in most cases.

🧰 2. Manual Reclustering (Optional)
If you want to force reclustering (e.g., after a large unordered bulk insert), you can use:


ALTER TABLE my_table RECLUSTER;

🔸 This triggers a one-time reclustering process. It still runs asynchronously, but gives you more control.

Monitor Clustering Quality

SELECT SYSTEM$CLUSTERING_INFORMATION('my_table');
it returns JSON with

| Field                   | Description                                |
| ----------------------- | ------------------------------------------ |
| `cluster_by_keys`       | List of clustering columns                 |
| `total_partition_count` | Number of micro-partitions                 |
| `average_overlaps`      | **Lower is better** (measures key overlap) |
| `average_depth`         | Depth of partition tree; lower is better   |
| `bytes_scanned`         | Useful for tuning queries                  |


When to Recluster

| When                                                  | Why                                      |
| ----------------------------------------------------- | ---------------------------------------- |
| After large unordered inserts                         | To re-establish good clustering          |
| If `SYSTEM$CLUSTERING_INFORMATION` shows high overlap | Indicates degraded pruning efficiency    |
| When queries scan more data than expected             | Bad clustering = more partitions scanned |


| Concept          | Explanation                                                   |
| ---------------- | ------------------------------------------------------------- |
| **Reclustering** | Reorders micro-partitions to improve clustering key alignment |
| **Automatic**    | Background Snowflake process for large tables                 |
| **Manual**       | Use `ALTER TABLE ... RECLUSTER` as needed                     |
| **Monitoring**   | Use `SYSTEM$CLUSTERING_INFORMATION()`                         |
| **Goal**         | Better **partition pruning**, faster queries, lower cost      |


### SYSTEM$ functions

SYSTEM — it refers to a special class of Snowflake system-defined functions,   
also known as system functions or metadata functions.

SYSTEM$ functions are built-in functions provided by Snowflake.

They are used to query internal metadata, diagnose performance, and inspect system state.  
They behave like scalar functions, returning results like strings, JSON objects, or numeric values.

| Function                                    | Purpose                                                                          |
| ------------------------------------------- | -------------------------------------------------------------------------------- |
| `SYSTEM$CLUSTERING_INFORMATION('table')`    | Returns JSON with clustering stats for a clustered table                         |
| `SYSTEM$WAIT(condition)`                    | Used in scripts to wait for a condition (rare use)                               |
| `SYSTEM$PIPE_STATUS('pipe_name')`           | Returns the status of a Snowpipe                                                 |
| `SYSTEM$STREAM_HAS_DATA('stream_name')`     | Checks if a stream has new data to process                                       |
| `SYSTEM$WH_REFRESH_HISTORY('warehouse')`    | Lists warehouse resume/suspend history                                           |
| `SYSTEM$TYPEOF(expression)`                 | Returns the data type of the expression                                          |
| `SYSTEM$ESTIMATE_QUERY_ACCELERATION(query)` | Predicts how much faster a query could run with Query Acceleration Service (QAS) |



Most SYSTEM$ functions are scalar and return a JSON string or value.

You can use PARSE_JSON(...) if you want to extract fields:


```sql
SELECT PARSE_JSON(SYSTEM$CLUSTERING_INFORMATION('clickstream')):average_overlaps;


-- 1. Clustering Quality for Target Table
SELECT
  'Clustering Info' AS section,
  table_name,
  clustering_key,
  clustering_info:"average_overlaps"::FLOAT AS avg_overlap,
  clustering_info:"average_depth"::FLOAT AS avg_depth,
  clustering_info:"total_partition_count"::INT AS partitions
FROM (
  SELECT 
    'your_schema.your_table' AS table_name,
    'event_time' AS clustering_key,
    PARSE_JSON(SYSTEM$CLUSTERING_INFORMATION('your_schema.your_table')) AS clustering_info
);

-- 2. Warehouse Resume/Suspend History (last 24 hours)
SELECT
  'Warehouse Activity' AS section,
  warehouse_name,
  event_name,
  event_timestamp,
  initiator
FROM TABLE(SYSTEM$WH_REFRESH_HISTORY('your_warehouse'))
WHERE event_timestamp >= DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
ORDER BY event_timestamp DESC;

-- 3. Credit Usage by Day for Past 7 Days
SELECT
  'Credit Usage' AS section,
  usage_date,
  warehouse_name,
  credits_used
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE usage_date >= DATEADD(DAY, -7, CURRENT_DATE())
ORDER BY usage_date, warehouse_name;

-- 4. Top 5 Longest Queries in Last 24 Hours
SELECT
  'Long Queries' AS section,
  user_name,
  warehouse_name,
  query_text,
  total_elapsed_time / 1000 AS duration_seconds,
  start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
ORDER BY total_elapsed_time DESC
LIMIT 5;

```

Replace:

- 'your_schema.your_table' with your clustered table
- 'event_time' with your clustering column
- 'your_warehouse' with your active Snowflake virtual warehouse name


### Stored procedures

| Use Case                            | Description                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------ |
| **ETL/ELT orchestration**           | Control multi-step transformations with SQL logic                                    |
| **Dynamic SQL execution**           | Build and execute queries programmatically (e.g., pivot, loop, build SQL at runtime) |
| **Looping and branching logic**     | Use conditional statements and loops for iterative operations                        |
| **Metadata-driven transformations** | Read from config tables and apply transformations dynamically                        |
| **Trigger downstream workflows**    | Use with tasks to run multi-step jobs (e.g., `CALL my_daily_etl();`)                 |
| **Error handling**                  | Capture exceptions and send alerts/logs using `TRY/CATCH` blocks                     |

```sql
CREATE OR REPLACE PROCEDURE daily_etl()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
  INSERT INTO staging.cleaned_data
  SELECT * FROM raw.source_data WHERE is_valid = TRUE;

  CALL update_summary_table();
  RETURN 'ETL Complete';
END;
$$;
```

### Materialized views

| Use Case                                  | Description                                                 |
| ----------------------------------------- | ----------------------------------------------------------- |
| **Accelerate slow, repeated queries**     | Precompute expensive joins, aggregations, or filters        |
| **Optimize BI dashboards**                | Improve query speed for Power BI, Tableau, Looker           |
| **Reduce compute cost**                   | Avoid re-running the same transformation logic repeatedly   |
| **Query performance over large datasets** | Speed up filtered and grouped queries on partitioned tables |
| **Use with stream processing**            | Combine with **Streams** to track changes efficiently       |

```sql
CREATE MATERIALIZED VIEW mv_daily_views AS
SELECT
  movie_id,
  DATE_TRUNC('DAY', event_time) AS day,
  COUNT(*) AS views
FROM clickstream
WHERE action = 'START'
GROUP BY movie_id, day;


```

### Snowflake Task

A Snowflake Task is a built-in scheduling and orchestration feature that lets you automate the execution of SQL statements 
(or entire stored procedures) at regular intervals or in response to upstream events.

Think of a Task as a lightweight alternative to Airflow or cron for running scheduled ELT jobs inside Snowflake.

| Feature                             | Description                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| **Native Scheduler**                | Runs SQL code or stored procedures on a fixed interval (e.g., every 5 minutes) |
| **Serverless**                      | No need to manage compute—Snowflake handles it                                 |
| **Dependency Graph**                | Tasks can be chained into DAGs (Directed Acyclic Graphs)                       |
| **Uses Snowflake compute**          | Billing is per-second based on actual compute used                             |
| **Can resume suspended warehouses** | Tasks auto-resume compute if needed                                            |

```sql
CREATE OR REPLACE TASK daily_summary_task
  WAREHOUSE = my_wh
  SCHEDULE = 'USING CRON 0 6 * * * UTC'  -- every day at 6:00 AM UTC
AS
  INSERT INTO analytics.daily_summary
  SELECT DATE_TRUNC('DAY', event_time) AS event_date, COUNT(*) AS views
  FROM raw.clickstream
  WHERE event_time >= DATEADD(DAY, -1, CURRENT_DATE());
```

### Chaining tasks

```sql
-- Parent task
CREATE OR REPLACE TASK load_raw_data
  WAREHOUSE = my_wh
  SCHEDULE = '1 HOUR'
AS
  CALL load_s3_data();

-- Child task that runs after load_raw_data
CREATE OR REPLACE TASK transform_data
  WAREHOUSE = my_wh
  AFTER load_raw_data
AS
  CALL run_dbt_transform();
```

| Action       | Command                                               |
| ------------ | ----------------------------------------------------- |
| Start a task | `ALTER TASK my_task RESUME;`                          |
| Stop a task  | `ALTER TASK my_task SUSPEND;`                         |
| View status  | `SHOW TASKS;`                                         |
| View history | `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY;` |

Snowflake supports creating DAGs (Directed Acyclic Graphs) using its built-in Tasks   
and the AFTER keyword — enabling you to define task dependencies within Snowflake itself.

However, Snowflake Tasks are simpler and more limited than full-featured orchestrators like Apache Airflow.

| Feature                     | Supported? | Notes                                                                    |
| --------------------------- | ---------- | ------------------------------------------------------------------------ |
| **Chaining / Dependencies** | ✅          | Use `AFTER` to define DAGs                                               |
| **Schedules**               | ✅          | Use `SCHEDULE = 'CRON'` or `AFTER` (not both)                            |
| **Parallel branches**       | ✅          | Multiple tasks can depend on the same parent                             |
| **Retry on failure**        | ❌          | No built-in retries; must handle via logic or monitoring                 |
| **Conditional branching**   | ❌          | Not natively supported                                                   |
| **Dynamic task generation** | ❌          | Static DAG only — no runtime DAG logic                                   |
| **Monitoring UI**           | 🟡         | `SHOW TASKS` and `TASK_HISTORY`; limited visibility                      |
| **External integration**    | 🟡         | Possible via Snowflake + external functions (e.g., call webhooks, Slack) |


### Snowflake Tasks vs Apache Airflow

| Capability                     | Snowflake Tasks | Apache Airflow                              |
| ------------------------------ | --------------- | ------------------------------------------- |
| **Native SQL/ELT automation**  | ✅               | ✅                                           |
| **Python tasks**               | ❌               | ✅                                           |
| **Branching (IF/ELSE logic)**  | ❌               | ✅                                           |
| **Dynamic DAGs**               | ❌               | ✅                                           |
| **Retries and error handling** | ❌               | ✅ (fine-grained control)                    |
| **Rich UI & visualization**    | ❌ (basic only)  | ✅                                           |
| **Cross-system orchestration** | ❌               | ✅ (e.g., S3 → Snowflake → BigQuery → Slack) |
| **REST API & plugins**         | ❌               | ✅ (rich ecosystem)                          |


### Qualify keyword

Normally, when you use window functions (like ROW_NUMBER(), RANK(), LAG()), you can't directly use them in the WHERE clause because WHERE is processed before window functions.

QUALIFY allows you to filter based on window function results, similar to how HAVING filters aggregates.

```sql
SELECT *
FROM sales
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY sale_date DESC) = 1;
```
the same without qualify:
```sql
SELECT *
FROM (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY sale_date DESC) AS rn
  FROM sales
) t
WHERE rn = 1;
```

### JSON

Load JSON into VARIANT columns (semi-structured type) 
Use dot notation or colon : notation to extract fields 
Can use FLATTEN() to explode arrays 

Query JSON

```sql
SELECT
  data:movie_id::STRING AS movie_id,
  data:genre::STRING AS genre,
  data:attributes:director::STRING AS director
FROM raw_json_table;
```

Load JSON or JSONL
```sql
CREATE OR REPLACE TABLE raw_movies (data VARIANT);

COPY INTO raw_movies
FROM @my_stage/movies/
FILE_FORMAT = (TYPE = 'JSON');
```

Extracting arrays with flatten()
```sql
{
  "movie_id": "abc123",
  "actors": ["Tom Hanks", "Meg Ryan"]
}

SELECT
  data:movie_id::STRING AS movie_id,
  actor.value::STRING AS actor_name
FROM raw_movies,
LATERAL FLATTEN(input => data:actors) AS actor;

```

JSON query helpers
```sql
| Function                    | Description                                          |
| --------------------------- | ---------------------------------------------------- |
| `:field`                    | Extract value from JSON (`data:genre`)               |
| `::TYPE`                    | Cast JSON value to SQL type (`::STRING`, `::NUMBER`) |
| `FLATTEN()`                 | Explode arrays in JSON                               |
| `OBJECT_KEYS()`             | Get keys of JSON object                              |
| `IS_OBJECT()`, `IS_ARRAY()` | Check JSON structure                                 |


```

### Pivot SQL
- You must specify the values in the IN (...) clause (no dynamic pivoting).
- Aggregation function (e.g. SUM, AVG) is required.
```sql
SELECT *
FROM (
  SELECT department, gender, salary
  FROM employees
)
PIVOT(
  SUM(salary) FOR gender IN ('M', 'F')
);
```
| department | 'M' (salary) | 'F' (salary) |
| ---------- | ------------ | ------------ |
| HR         | 100000       | 90000        |
| IT         | 150000       | 130000       |

