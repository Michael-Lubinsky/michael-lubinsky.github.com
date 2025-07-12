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
| TimescaleDB    | ⚠️        |
