## Kafka Streams

https://habr.com/ru/articles/913652/

https://github.com/quixio/quix-streams Kafta Stream  + Python

https://blog.picnic.nl/using-change-data-capture-for-warehouse-analytics-a1b23c074781 CDC change dta capture


https://medium.com/@seanfalconer/a-data-scientists-guide-to-data-streaming-2b2b78dd8486 

Master ETL Pipelines with PySpark: 8 Real-World Challenges Solved
https://medium.com/@mayursurani/master-etl-pipelines-with-pyspark-8-real-world-challenges-solved-507711d0c26f

## Flink

https://habr.com/ru/articles/914836/

https://www.unskewdata.com/blog/stream-flink-4

https://habr.com/ru/articles/908220/

https://www.onehouse.ai/blog/apache-spark-structured-streaming-vs-apache-flink-vs-apache-kafka-streams-comparing-stream-processing-engines 



https://testdriven.io/blog/flask-svelte/ Real Time Dashboard

https://testdriven.io/blog/fastapi-svelte/ FastAPI real time dashoard 



Apache Pinot vs Apache Flink
============================

Apache Pinot and Apache Flink are both open-source distributed systems, but they serve very different purposes within a data processing architecture.

High-Level Purpose
------------------

- **Apache Pinot**: Real-time OLAP datastore optimized for low-latency analytical queries on immutable event data.
- **Apache Flink**: Real-time stream processing framework for building event-driven applications and pipelines.

Primary Use Case
----------------

- **Pinot**: Real-time analytics dashboards (e.g., user behavior metrics, A/B testing analytics).
- **Flink**: Real-time transformations, windowed aggregations, and complex event processing on streaming data.

Data Input
----------

- **Pinot**: 
  - Ingests data from Kafka, batch sources (e.g., HDFS, S3), or APIs.
  - Optimized for append-only immutable data.
- **Flink**: 
  - Consumes data from streaming sources like Kafka, Pulsar, files, JDBC, etc.
  - Supports both stream and batch processing.

Data Output
-----------

- **Pinot**: Serves SQL-based analytical queries via REST/Presto/Broker.
- **Flink**: Emits transformed streams to sinks like Kafka, databases, filesystems, or can trigger actions.

Latency
-------

- **Pinot**: Sub-second query latency for high-dimensional aggregations and filters.
- **Flink**: Low-latency processing (millisecond-scale), but not designed for serving ad hoc queries.

Query Model
-----------

- **Pinot**: SQL-based OLAP queries with filtering, aggregations, group by, time-range, etc.
- **Flink**: Continuous streaming SQL or programmatic API (Java, Scala, Python) for event transformations.

State Management
----------------

- **Pinot**: Stateless for ingestion; stateful for indexing and query acceleration.
- **Flink**: Built-in distributed state management and exactly-once guarantees for stream operations.

Deployment
----------

- **Pinot**: Components include Controller, Broker, Server, Minion; typically used with Zookeeper.
- **Flink**: Deployed as JobManager and TaskManagers; supports standalone, YARN, Kubernetes, etc.

Integration
-----------

- **Pinot**:
  - Kafka, Hadoop, S3, Presto, Superset, Tableau, Looker
- **Flink**:
  - Kafka, Pulsar, JDBC, S3, Hive, Elasticsearch, Iceberg, Delta Lake, etc.

Typical Use Together
--------------------

Flink and Pinot are **complementary**:
- Flink processes/aggregates events from Kafka → writes results to Pinot → Pinot serves the results for analytics dashboards or APIs.

Summary Table
-------------

| Feature              | Apache Pinot                        | Apache Flink                        |
|----------------------|--------------------------------------|-------------------------------------|
| Type                 | OLAP datastore                      | Stream processing engine            |
| Query Language       | SQL (OLAP-style)                    | SQL (streaming), Java, Scala, Python|
| Latency              | Sub-second for queries              | Sub-second for event processing     |
| Input Sources        | Kafka, S3, HDFS, APIs               | Kafka, Pulsar, JDBC, Files, etc.    |
| Output               | Query results (dashboards, APIs)   | Streams to sinks (Kafka, DB, S3)    |
| Use Case             | Real-time user-facing analytics     | Real-time ETL, stream transformations|
| Common Together      | Pinot ← Flink → Kafka               | Pinot serves; Flink transforms      |

Conclusion
----------

- Use **Flink** when you need complex event processing or real-time data pipeli


### Apache Pinot
Apache Pinot is a real-time distributed OLAP datastore optimized for low-latency analytics on large-scale, streaming data. 
Its main competitors typically fall into the same category of **real-time analytics databases** or **OLAP engines**.

Here are the main competitors of Apache Pinot, with brief comparisons:


### 🔹 ClickHouse
- **Strengths**: Extremely fast for analytical queries, efficient columnar storage, mature ecosystem.
- **Use Case**: Real-time and batch analytics, logs, time-series.
- **Comparison**: ClickHouse excels at high-performance queries, but lacks native integration with streaming sources like Kafka the way Pinot does.

---

### 🔹 Druid (Apache Druid)
- **Strengths**: Optimized for real-time ingestion, supports approximate aggregations, time-based partitioning.
- **Use Case**: Event data analytics, dashboards, time-series analytics.
- **Comparison**: Druid and Pinot are very close; Pinot focuses more on **exact aggregations**, **SQL support**, and **low-latency queries**, while Druid has stronger built-in roll-ups and tiered storage.

---

### 🔹 TimescaleDB
- **Strengths**: PostgreSQL extension for time-series data, strong SQL support.
- **Use Case**: Time-series workloads with traditional relational semantics.
- **Comparison**: TimescaleDB is better for developers familiar with Postgres; less performant for large-scale ad hoc analytics than Pinot.

---

### 🔹 Rockset
- **Strengths**: Real-time analytics on semi-structured data; converged indexing, cloud-native.
- **Use Case**: Fast search and analytics on structured/semi-structured data.
- **Comparison**: Rockset offers strong performance and schema-flexibility, but it's a managed SaaS offering (not open source like Pinot).

---

### 🔹 Materialize
- **Strengths**: SQL-based streaming materialized views, strong support for incremental computation.
- **Use Case**: Real-time streaming SQL workloads.
- **Comparison**: Focuses more on **incremental view updates from streaming data**, not optimized for large-scale ad hoc analytics like Pinot.

---

### 🔹 QuestDB
- **Strengths**: High-performance time-series database, SQL-like language.
- **Use Case**: High-frequency trading, telemetry data.
- **Comparison**: More time-series-focused; Pinot is more general-purpose for analytical queries.

---

### 🔹 BigQuery / Snowflake / Redshift (Cloud Data Warehouses)
- **Strengths**: Scalability, ecosystem, SQL support, integration with BI tools.
- **Use Case**: Batch analytics, ad hoc querying, dashboarding.
- **Comparison**: Pinot is real-time and purpose-built for **sub-second latency**, while these are optimized for **batch analytics**.

---

### Summary Table

| Competitor     | Real-time | Streaming Ingest | Exact Aggregations | SQL Support | Use Case                              |
|----------------|-----------|------------------|---------------------|-------------|----------------------------------------|
| ClickHouse     | ⚠️ Limited | ❌ Indirect       | ✅                  | ✅          | High-performance batch analytics       |
| Apache Druid   | ✅        | ✅               | ⚠️ Approximate       | ⚠️ Partial   | Real-time + time-series analytics      |
| Rockset        | ✅        | ✅               | ✅                  | ✅          | SaaS search and analytics              |
| TimescaleDB    | ⚠️        | ⚠️               | ✅                  | ✅          | Time-series with relational schema     |
| Materialize    | ✅        | ✅               | ✅                  | ✅          | Streaming materialized views           |
| Pinot          | ✅        | ✅               | ✅                  | ✅          | Real-time OLAP on fresh data           |
