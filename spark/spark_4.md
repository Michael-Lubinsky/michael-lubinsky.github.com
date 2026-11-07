## Spark Structured Streaming

<https://vutr.substack.com/p/everything-you-need-to-know-about-46d>

<https://medium.com/@lisancao/spark-structured-streaming-the-full-latency-spectrum-cc2231998763>

## Autoloader

<https://medium.com/@asindugayangana/databricks-auto-loader-best-practices-for-reliable-and-scalable-data-ingestion-30e65bf4c520>

## Handling Late Arrival

<https://medium.com/@divyanshgoyal8989/handling-late-arriving-data-in-databricks-real-world-strategies-7a7203c75725>

## SPARK 4

<https://codecut.ai/pyspark-4-0-whats-new/>


<https://luminousmen.substack.com/p/the-apache-spark-optimization-checklist>

### Apache Spark 4.1.0 
 It focuses on higher-level data engineering, lower-latency streaming, faster/easier PySpark, and a more capable SQL surface.


#### Spark Declarative Pipelines (SDP)
A new declarative framework where you define datasets and queries, and Spark handles the execution graph, dependency ordering, parallelism, checkpoints, and retries — this is the OSS foundation of what became Databricks' "Lakeflow Declarative Pipelines" (formerly DLT). 

#### Structured Streaming Real-Time Mode (RTM)**
First official support for Structured Streaming queries running in real-time mode for continuous, sub-second latency processing — for stateless tasks, latency can even drop to single-digit milliseconds. Currently scoped to Scala stateless workloads.

#### SQL Scripting — now GA, on by default**
Improved error handling and cleaner variable declarations, plus support for `CONTINUE HANDLER` and multiple variables inside a single `DECLARE`.

#### VARIANT type — now GA**
Enabled with shredding for faster reads on semi-structured data, plus support for VARIANT in CSV/XML scans and Parquet read/write with proper logical-type annotation.

#### PySpark UDFs/Data Sources**
New Arrow-native UDF and UDTF decorators for efficient PyArrow execution without Pandas conversion overhead, plus Python Data Source filter pushdown to reduce data movement.

**Spark ML on Connect — GA for the Python client**
Smarter model caching and memory management, plus general stability improvements for large workloads via zstd-compressed protobuf plans, chunked Arrow result streaming, and enhanced support for large local relations.

**Other notable additions**
- Recursive CTE support and a JDBC Driver for Spark Connect
- 77 new built-in SQL functions, including new approximate data sketches: `approx_top_k`, KLL quantile sketches, and Theta sketches
- Checksum-based shuffle stage full retry to avoid incorrect results — a stability fix for silent data corruption
- A Stored Procedures API for Catalogs
- Data Source V2: join pushdown (Oracle, Postgres, MySQL, SQL Server), MERGE INTO schema evolution, table constraints
- Streaming: stream-stream join support with virtual column families, plus a wave of RocksDB state-store reliability work (lock management revamp, snapshot lag detection, checksum verification)
- Infrastructure: minimum Python bumped to 3.10, Python 3.14 support added, Scala upgraded to 2.13.17

## Check Spark Version:
```
print(spark.version)
print(spark.sparkContext.version)

Note that spark.sparkContext may not be available on serverless compute or Spark Connect.

 -- Using SQL
Run this in a Databricks SQL notebook or SQL Warehouse:
SELECT version();

Databricks may backport selected Spark features or implement its own equivalents.
Therefore, even if your environment reports Spark 4.0.0,
some functionality introduced in upstream Spark 4.1–4.3 might already be available through Databricks-specific features.

print(
    "Databricks Runtime:",
    spark.conf.get(
        "spark.databricks.clusterUsageTags.sparkVersion",
        "Unknown"
    )
)
```

For a quick mental model: 
- **4.1.0** was the "declarative pipelines + real-time streaming + SQL/VARIANT maturity" release, while
-  **4.2.0** (which you asked about earlier) layered on geospatial types, native CDC, and further PySpark/DSv2 polish on top of that foundation.

## Apache Spark 4.3.0 — What's New?

According to the official [Apache Spark 4.3.0 release notes](https://spark.apache.org/releases/spark-release-4-3-0.html?utm_source=chatgpt.com), Spark 4.3.0 introduces several important improvements, particularly for real-time streaming, Change Data Capture (CDC), SQL, and query performance.

The release includes more than 1,100 resolved JIRA tickets and contributions from over 210 developers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spark.apache.org\&sz=32)



## 1. Spark 4.1 vs. 4.2 vs. 4.3

| Version | Main focus                         | Key capabilities                                                                                 |
| ------- | ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| 4.1.0   | Foundation                         | Declarative pipelines, real-time streaming, SQL/VARIANT improvements                             |
| 4.2.0   | Data engineering                   | Geospatial types, native CDC, PySpark and Data Source V2 improvements                            |
| 4.3.0   | Stateful streaming and performance | Stateful Real-Time Mode, SCD Type 2 Auto CDC, ASOF JOIN, JSON_TABLE, faster small-data execution |

My characterization of Spark 4.3.0 would be:

> Spark 4.3 makes real-time streaming more capable, CDC pipelines more useful for historical analytics, and SQL more expressive for complex and time-dependent data.

## 2. Most important 4.3.0 new features

#### Stateful Real-Time Streaming

Streaming aggregations, `dropDuplicates`, and `transformWithState` can now operate in Real-Time Mode, targeting end-to-end latency on the order of 100 milliseconds. This is particularly relevant to GPS and IoT telemetry processing.

#### SCD Type 2 Auto CDC

Declarative pipelines can preserve historical versions of changed records, instead of maintaining only the latest state. Supported through Python, SQL, and Spark Connect.

#### SQL ASOF JOIN

Match an event with the most appropriate earlier or contemporaneous record. Useful for time-series joins, financial market data, and telemetry enrichment. The SQL feature is disabled by default.

#### JSON_TABLE and VARIANT manipulation

Convert nested JSON into relational structures and modify semi-structured data using functions such as `variant_set`, `variant_insert`, and `variant_delete`.

#### Faster execution on small datasets

Opt-in shuffle-free single-task execution and Arrow-native caching reduce overhead for eligible queries, particularly useful for development and local Spark workloads.

These are all documented in the official 4.3.0 release notes. 

 
## 3. Additional Spark 4.3  improvements worth knowing

Several less-publicized changes are particularly useful for data engineering.

| Feature                 | Why it matters                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| `counter_diff`          | Converts cumulative counters into deltas, useful for odometer and energy consumption measurements |
| Nanosecond timestamps   | Precision up to 9 fractional digits; currently a preview feature                                  |
| Archive readers         | Opt-in reading of CSV, JSON, Parquet and other files inside TAR, ZIP and 7z archives              |
| Data Source V2          | Generated columns, runtime filtering, and additional predicate pushdown                           |
| Python UDF optimization | Experimental conversion of simple Python UDFs into Catalyst expressions                           |
| Parquet performance     | Faster vectorized decoding and type conversions                                                   |
| Spark Connect           | REST endpoints for sessions and operations, improved JDBC support                                 |

 

One important compatibility change: Spark 4.3 drops Python 3.10 support.  
Plan to use Python 3.11 or newer when upgrading.

## 4. Practical example: ASOF JOIN for vehicle telemetry

Suppose you have two datasets.

GPS telemetry

| car_id | event_time | speed |
| ------ | ---------- | ----- |
| A      | 10:00:05   | 35    |
| A      | 10:00:12   | 42    |
| A      | 10:00:20   | 38    |

Battery measurements

| car_id | measurement_time | battery_pct |
| ------ | ---------------- | ----------- |
| A      | 10:00:00         | 80          |
| A      | 10:00:10         | 79          |
| A      | 10:00:18         | 78          |

You want each GPS event enriched with the most recent battery measurement at or before its timestamp.

The result should be:

| event_time | speed | battery_pct |
| ---------- | ----- | ----------- |
| 10:00:05   | 35    | 80          |
| 10:00:12   | 42    | 79          |
| 10:00:20   | 38    | 78          |

Previously, you could implement this using window functions or more complicated joins. Spark 4.3 introduces SQL `ASOF JOIN` for this pattern, with a dedicated sort-merge execution operator.

Enable the feature:

```
spark.conf.set(    "spark.sql.join.asofJoin.enabled",    "true")
```


## 5. What I would prioritize learning

For your Spark and Databricks data engineering work, I would prioritize:

1. ASOF JOIN — extremely relevant to time-series and vehicle telemetry.
2. SCD Type 2 Auto CDC — useful for maintaining historical user and vehicle attributes. Note that the target catalog must support Data Source V2 row-level operations, such as Apache Iceberg.
3. Stateful Real-Time Mode — important for low-latency IoT and streaming applications.
4. `counter_diff` — useful for cumulative mileage and energy readings.
5. Python UDF transpilation and optimizer improvements — potentially helpful for performance tuning, though some capabilities are experimental.

One important distinction: these are features of upstream Apache Spark 4.3.0.  
Their availability in a managed Databricks runtime depends on that runtime's Spark version and Databricks-specific implementation.

Overall, Spark 4.3.0 is more than an incremental API release.   
Its most significant architectural advance is bringing stateful processing into low-latency Real-Time Mode,   
while its most immediately useful data engineering additions are SCD Type 2 Auto CDC and SQL ASOF JOIN.

<https://spark.apache.org/releases/spark-release-4-3-0.html>

## Declarative Pipeline

<https://github.com/bartoszgajda55/spark_declarative_pipelines_cheat_sheets>

<https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html>

<https://www.waitingforcode.com/apache-spark-structured-streaming/spark-declarative-pipelines-101/read>

<https://medium.com/apache-spark/declarative-pipelining-in-apache-spark-part-1-focus-on-your-data-not-your-dags-553a1056d178>

<https://medium.com/apache-spark/apache-spark-patterns-for-agent-safe-data-pipelines-0d58d6d84fa4>

## DataSource API

<https://github.com/allisonwang-db/awesome-python-datasources>

## max_by

The Query
Find the top (ranked 1) in each category based on certain condition.

The solution was implemented with a window function to handle duplicate records (some pseudo SQL):
```sql
WITH ranked AS (
  SELECT 
    ...
    ROW_NUMBER() OVER (
      PARTITION BY col1, col2, col3, col4
      ORDER BY 
        col5 DESC, 
        col6 DESC, 
        col7 DESC
    ) AS rank
  FROM table1 t1
  JOIN table2 t2 ON (...)
)
SELECT * EXCEPT (rank)
FROM ranked 
WHERE rank = 1
```
This is a simple query. The goal of the above query is to find the top record for each combination of col1, col2, col3, col4. In Spark terms it will do

Split the into partitions based on partition keys
Sort each partition by the ORDER BY clause
Assign row numbers to every single row
Filter out everything except rank = 1


<https://blog.devgenius.io/improving-spark-jobs-runtime-b128f0c29d44>

How max_by Works Under the Hood  

max_by(col, ord) — Returns the value from the col parameter that is associated with the maximum value from the ord parameter.  

The first parameter is the column name that needs to be displayed as output, and the second parameter is the column on which we check the max condition.
```
df.groupby("course").agg(max_by("year", "earnings")).show()
# SELECT max_by(x, y) FROM VALUES ('a', 10), ('b', 50), ('c', 20) AS tab(x, y);
```

Instead of collecting and sorting all rows in each partition, max_by uses an incremental aggregation approach:

For each partition, maintain only two values:

valueWithExtremumOrdering: The current "best" record
extremumOrdering: The current maximum ordering value
For each new row, do a simple comparison:

If new_ordering > current_max_ordering, update both values
Otherwise, keep the current values
No sorting required: Just O(1) comparisons per row instead of O(n log n) sorting

This means:

Memory usage: O(1) per partition instead of O(n)  
CPU complexity: O(n) instead of O(n log n)  
Less disk spilling: The intermediate state fits more easily in memory  
So the query was rewritten to leverage the MAX_BY function:  

```sql
SELECT 
  col1, col2, col3, col4,
  MAX_BY(
    STRUCT(...),
    STRUCT(col5, col6, col7)
  )
FROM table1 t1 
INNER JOIN table2 t2 ON (...)
GROUP BY col1, col2, col3, col
```
 


### Spark 4.0 links

<https://medium.com/@cralle/what-developers-need-to-know-about-apache-spark-4-0-508d0e4a5370>

<https://habr.com/ru/companies/korus_consulting/articles/920766/>

<https://sabarevictor.medium.com/stop-learning-pandas-the-spark-4-0-features-nobodys-telling-you-about-8651b0206ee5>

<https://medium.com/@goyalarchana17/whats-next-for-apache-spark-4-0-a-comprehensive-overview-with-comparisons-to-spark-3-x-c2c1ba78aa5b?sk=81039bff1aadd3a8e65507a43f21ec12>

<https://medium.com/towards-data-engineering/how-to-migrate-to-apache-spark-4-0-in-10-steps-a-complete-guide-b25aff9454a7>

<https://medium.com/towards-data-engineering/meet-variant-apache-spark-4-0s-secret-weapon-for-semi-structured-data-c087e164c241>





◉ Apache Spark all fundamentals in one long article

<https://lnkd.in/g8bzn5Fk>

◉ Apache Spark overview: Architecture, Job, Stage, Task, RDD, the journey of the Spark application

<https://lnkd.in/gxrkaAk3>

◉ Spark resource allocation: Static vs dynamic allocation, FIFO vs Fair schedule mode

<https://lnkd.in/ga-wX-j6>

◉ Spark scheduling process: from your code to physical execution on executors

https://lnkd.in/g7VrtHv3

◉ Spark planning process: Catalyst, logical vs physical planning, Adaptive Query Execution in Spark 3

https://lnkd.in/gcCUpKev

◉ Spark's memory management: On-heap and Off-heap memory

https://lnkd.in/gPpyFK7j

◉ Databricks's Spark vs Open-sourced Spark: Spark + Photon engine to boost the query performance

https://lnkd.in/gSN7Vk33

◉ PySpark: Spark was written in Scala, so how could we use Python with it?

https://lnkd.in/gwA-BWdp

◉ Spark Structured Streaming: the micro-batch processing engine

https://lnkd.in/gQMywJsz

◉ Spark Connect: process data in Spark by making an API request instead of submitting an application

https://lnkd.in/gfXsbQ35
