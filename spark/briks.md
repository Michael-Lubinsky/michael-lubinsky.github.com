### Databricks Versions 

| Version            | Spark Version | Release Date   | Support Ends                                                     |
| ------------------ | ------------- | -------------- | ---------------------------------------------------------------- |
|  16.4 LTS       | 3.5.2         | May 9, 2025    | May 9, 2028                                                      |
| 15.4 LTS           | 3.5.0         | Aug 19, 2024   | Aug 19, 2027                                                     |
| 14.3 LTS           | 3.5.0         | Feb 1, 2024    | Feb 1, 2027                                                      |
|  17.0 (Beta)     | 4.0.0         | May 20, 2025   | Nov 20, 2025                                                     |
| 16.3 / 16.2 / 16.1 | 3.5.x         | Early–mid 2025 | Mid–late 2025                                                    |


### Delta Lake
Delta Lake is an open-source storage layer that brings reliability, performance, and governance to data lakes. It is tightly integrated with Databricks and underpins much of its functionality.

✅ Key Features:
ACID Transactions: Guarantees data integrity with support for concurrent writes and reads.

Schema Enforcement & Evolution: Prevents bad data and allows schema changes over time.

Time Travel: Query historical versions of data using VERSION AS OF or TIMESTAMP AS OF.

Data Compaction (OPTIMIZE): Merges small files into larger ones to improve performance.

Streaming + Batch: Supports both in the same pipeline using the same Delta table.


- **Definition**: Delta Lake is the **storage layer technology** that brings **ACID transactions**, **schema enforcement**, **time travel**, and **efficient metadata handling** to **Apache Spark** and **big data platforms**.
- **Scope**: It's a **general-purpose storage format** and **engine** that can be used in **Databricks**, **Apache Spark**, **EMR**, or other platforms.
- **File Format**: Internally, it stores data as **Parquet files** plus a **transaction log** (in `_delta_log/`) that records all changes to the table.
- **Main Features**:
  - ACID transactions
  - Time travel
  - Schema evolution and enforcement
  - Scalable metadata (no need for Hive metastore)
  - Unified batch and streaming processing

---

#### **Delta Table**
- **Definition**: A **table stored in Delta Lake format**. It's a **specific instance** of data using the Delta Lake capabilities.
- **Scope**: A **Delta Table** is the **user-facing abstraction** — it’s how you **interact with data** using SQL or PySpark in Databricks.
- **Types**:
  - **Managed Delta Table**: Stored fully inside the Databricks-managed metastore and filesystem.
  - **External Delta Table**: Data is stored in external storage (e.g., S3, ADLS) but registered in the metastore.
- **Usage Examples**:
  ```sql
  CREATE TABLE my_table USING DELTA LOCATION '/mnt/data/my_table';
  SELECT * FROM my_table VERSION AS OF 5;
  ```

---

## 🧠 Summary

| Feature             | Delta Lake                               | Delta Table                               |
|---------------------|------------------------------------------|-------------------------------------------|
| What is it?         | Storage format and engine                | A table that uses Delta Lake format       |
| Scope               | System-level (enables features)          | Table-level (stores actual data)          |
| Core Feature        | ACID, schema, time travel, etc.          | Logical/physical dataset using Delta Lake |
| Usage               | Underpins table functionality            | Interacted with via SQL/DataFrame API     |

---

> **In short**:  
> **Delta Lake** is the technology, and **Delta Table** is how you use that technology to store and query data.




### Liquid clustering

Liquid Clustering in Databricks is a data layout optimization feature for Delta Lake tables,   
designed to improve query performance and simplify maintenance compared to traditional Z-Ordering.   
As of 2025, liquid clustering is not obsolete—in fact, it’s the preferred and modern method recommended by Databricks for clustering large Delta tables.

Liquid Clustering automatically maintains clustering of data files on one or more columns   
(like customer_id, event_date, etc.) without requiring static Z-Ordering.   
It uses lightweight background operations to organize data incrementally, making it suitable for large and frequently updated tables.

| Feature                                 | Description                                                          |
| --------------------------------------- | -------------------------------------------------------------------- |
| **Incremental optimization**            | Files are re-clustered automatically in the background during writes |
| **No full rewrites**                    | Unlike Z-Order, it avoids full rewrites or expensive compactions     |
| **Adaptive to changes**                 | Adjusts clustering as new data arrives                               |
| **Simpler maintenance**                 | No need for regular OPTIMIZE ZORDER BY jobs                          |
| **Better for streaming/near real-time** | Works well with continuous data ingestion scenarios                  |

Use Liquid Clustering when:

You have large tables with frequent updates/inserts

Query performance suffers due to data skew or file fragmentation

You need a less maintenance-heavy alternative to Z-Ordering

```sql
ALTER TABLE my_table
SET TBLPROPERTIES (
  'delta.liquidClustered.columns' = 'event_date, user_id'
);

or

CREATE TABLE my_table (
  event_date DATE,
  user_id STRING,
  ...
)
USING DELTA
TBLPROPERTIES (
  'delta.liquidClustered.columns' = 'event_date, user_id'
);
```
Databricks is moving away from recommending Z-Ordering for many use cases.

Liquid Clustering is better aligned with streaming + batch hybrid pipelines.

| Feature     | Z-Ordering                      | Liquid Clustering              |
| ----------- | ------------------------------- | ------------------------------ |
| Maintenance | Manual `OPTIMIZE ZORDER BY`     | Automatic                      |
| Performance | High, but expensive to maintain | Comparable, and auto-adjusting |
| Best For    | Static/batch workloads          | Streaming + frequent updates   |
| Obsolete?   | No, but becoming less preferred | No, recommended for modern use |


### Clustering (Z-Ordering)
Clustering in Delta Lake is done using Z-Ordering, a technique to optimize data layout on disk for faster query performance.

✅ Key Concepts:
Z-Ordering: Reorders data files on disk to colocate related records (e.g., by customer_id or timestamp).

Improves predicate pushdown and data skipping, so queries scan fewer files.

Used with OPTIMIZE command:

```sql
OPTIMIZE table_name ZORDER BY (col1, col2);
```
🔍 When to Use:
Large tables where you frequently query by filters on certain columns (e.g., date ranges, user IDs).

Example: speeding up queries on a logs table by Z-Ordering on event_time.



### Table properties
```sql
CREATE TABLE sales_data (
    sale_id STRING,
    customer_id STRING,
    amount DOUBLE,
    sale_date DATE
)
USING DELTA
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'comment' = 'Sales transactions table',
    'source' = 'ETL_v2'
);

TBLPROPERTIES ('source' = 'ingestion_pipeline', 'pii' = 'true')


DESCRIBE TABLE EXTENDED sales_data;

SHOW TBLPROPERTIES sales_data;

```

#### Delta Lake-Specific Properties
 
| Property                                                    | Description                                                                     |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `delta.autoOptimize.optimizeWrite = true`                   | Automatically optimizes file sizes when writing data.                           |
| `delta.autoOptimize.autoCompact = true`                     | Automatically compacts small files after write operations.                      |
| `delta.logRetentionDuration = 'interval'`                   | Retain Delta transaction log files for a specific duration (e.g., `'30 days'`). |
| `delta.deletedFileRetentionDuration = 'interval'`           | Controls how long deleted files are retained (for time travel).                 |
| `delta.enableChangeDataFeed = true`                         | Enables Change Data Feed (CDF) for the table.                                   |
| `delta.columnMapping.mode = 'name'`                         | Enables column mapping by name, useful for schema evolution.                    |
| `delta.minReaderVersion = X` / `delta.minWriterVersion = Y` | Sets required Delta protocol versions.                                          |

#### Clustering and Performance

| Property                           | Description                                     |
| ---------------------------------- | ----------------------------------------------- |
| `delta.dataSkippingNumIndexedCols` | Number of columns used for data skipping.       |
| `delta.checkConstraints.<name>`    | Used to enforce a check constraint on a column. |
| `delta.zOrderCols` *(internal)*    | Metadata about columns used for Z-ordering.     |

#### Access Control

| Property  | Description                                                   |
| --------- | ------------------------------------------------------------- |
| `owner`   | Sets the owner of the table (for Unity Catalog).              |
| `comment` | Adds a description to the table. Useful for catalog browsing. |


### Databricks Delta Table

A **Databricks Delta Table** (based on **Delta Lake**) is a **storage format** and **transactional layer** built on top of data lakes (like **S3**, **ADLS**, or **DBFS**) that enables **reliable, fast, and ACID-compliant** analytics on big data.

* * *

### ✅ **Key Features of Delta Tables**

| Feature | Description |
|--------|-------------|
| **ACID Transactions**  | Supports atomic writes, rollback, and concurrent reads/writes
| **Schema Enforcement** | Automatically validates schema consistency during data writes
| **Schema Evolution** | Allows you to change table schemas without manual data migration
| **Time Travel** | Lets you query previous versions of the data (e.g., `VERSION AS OF 10`)
| **Data Compaction** | Optimizes small files into larger ones (`OPTIMIZE` command)
| **Audit History** | Tracks table changes over time (`DESCRIBE HISTORY`)
| **Streaming + Batch** | Supports both real-time streaming and batch processing

* * *

### 🔄 **How It Works**

Under the hood, a Delta table:

-   Stores **data in Parquet files**
    
-   Maintains a **transaction log (`_delta_log`)** that tracks all operations (adds, deletes, schema changes, etc.)
    

This log makes it possible to achieve ACID guarantees on top of object stores, which don’t provide native transactional capabilities.

* * *

### 🧱 **Delta Table in Databricks**

In a Databricks workspace, you typically create and use Delta tables like this:

```sql
CREATE TABLE sales (   id INT,   amount DOUBLE ) USING DELTA;
INSERT INTO sales VALUES (1, 100.0);
-- Querying a previous version
SELECT * FROM sales VERSION AS OF 3;`
```
Or using PySpark:

`df.write.format("delta").save("/mnt/datalake/sales")`

* * *

### 📚 Delta Table Types in Databricks

| Table Type | Description |
|----|-----|
| **Managed** | Databricks manages the data and metadata location
| **External** | You manage the storage location; metadata stored in the metastore
| **Unity Catalog Table** | Fully governed table under Unity Catalog with access control & lineage

* * *

### 📌 Summary

A **Databricks Delta Table** is:

-   A **reliable and high-performance** table format for data lakes
    
-   Built on **Parquet** + **transaction logs**
    
-   Enables **analytics with ACID guarantees** in **streaming or batch**


##### How to access Databrick delta table via databricks Unity catalog?

To access a **Databricks Delta Table via Unity Catalog**, you need to reference the table using **three-level namespace syntax** and ensure the workspace is set up with Unity Catalog enabled. Here's how:

* * *

### ✅ Prerequisites

1.  **Unity Catalog is enabled** in your Databricks workspace.
    
2.  You have:
    
    -   A **Metastore** registered to your workspace.
        
    -   Access to a **catalog**, **schema (database)**, and **table**.
        
    -   Assigned appropriate **permissions** (like `USE CATALOG`, `SELECT`).
        

* * *

### 🧭 Unity Catalog Structure

 

`catalog_name.schema_name.table_name`

For example:
 

`main.sales.transactions`

* * *

### 🛠 How to Access a Delta Table via SQL

Use the full name:
 

`SELECT * FROM main.sales.transactions;`

Or if you set the context:

 

`USE CATALOG main; USE SCHEMA sales;  SELECT * FROM transactions;`

* * *

### 🐍 Access via PySpark / Python

 

`df = spark.table("main.sales.transactions") df.show()`

Or using SQL directly:

 

`spark.sql("SELECT * FROM main.sales.transactions").show()`

* * *

### 🔐 Managing Permissions (SQL)

 

``GRANT SELECT ON TABLE main.sales.transactions TO `data_analyst_group`;``

* * *

### 💡 Best Practices

-   Always use the **3-level identifier** to avoid ambiguity, especially in multi-catalog environments.
    
-   Use **Unity Catalog's fine-grained access controls** for secure data governance.


### Autoloader

Autoloader is a utility in Databricks optimized for incrementally ingesting new files from cloud storage into Delta Lake.

Efficiently detects new files using file listings or notification services.

Scales well with millions of files.

Supports schema inference and evolution.

```python
df = (spark.readStream
         .format("cloudFiles")
         .option("cloudFiles.format", "json")
         .load("/mnt/raw_data/"))
```

<https://fernandodenitto.medium.com/dont-confuse-autoloader-with-spark-structured-streaming-37186b88311e>

| Feature                  | **Autoloader**                                    | **Delta Live Tables (DLT)**                                     |
| ------------------------ | ------------------------------------------------- | --------------------------------------------------------------- |
| **Purpose**              | Ingest streaming or batch data from cloud storage | Define end-to-end declarative data pipelines                    |
| **Core Use Case**        | File ingestion at scale with schema evolution     | Managed, reliable ETL pipelines with quality and lineage        |
| **Input Sources**        | Cloud storage (e.g., S3, ADLS, GCS)               | Can use Autoloader, existing tables, or streaming sources       |
| **Output Format**        | Delta Lake tables                                 | Delta Lake tables (managed by DLT)                              |
| **Processing Type**      | Micro-batch or continuous streaming               | Batch or streaming                                              |
| **Transformations**      | You write PySpark/SQL code manually               | SQL or Python with declarative semantics                        |
| **Schema Evolution**     | Supported                                         | Supported with `expectations` and automated data quality checks |
| **Data Quality Rules**   | Not built-in                                      | Yes (`expect`, `drop`, `fail` rows on conditions)               |
| **Lineage & Monitoring** | Manual                                            | Built-in lineage, DAG visualization, alerts, and versioning     |
| **Deployment**           | You manage jobs                                   | Managed by DLT (simple configuration)                           |



| Scenario                                   | Recommendation                       |
| ------------------------------------------ | ------------------------------------ |
| Ingesting raw files from S3/GCS/ADLS       | Use **Autoloader**                   |
| Building a production ETL pipeline         | Use **DLT** (can include Autoloader) |
| Need streaming ingestion + transformations | **Autoloader inside DLT**            |
| Need data quality checks or auditing       | Use **DLT**                          |


You can use Autoloader inside DLT to get best of both:

```python
@dlt.table
def raw_events():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .load("/mnt/raw_data/")
    )

```

### DLT - Delta Live Tables

<https://medium.com/towards-data-engineering/migrating-a-real-time-aws-system-to-delta-live-tables-on-databricks-299ea44d6c18>

DLT is a declarative ETL framework built into Databricks that:
 • Automates task orchestration 
 • Manages clusters and errors 
 • Integrates data quality checks 
 • Supports streaming + batch workloads 


📊 Types of Datasets in DLT 

DLT supports three main dataset types, each designed for specific pipeline needs:  
 • 🔄 Streaming Table:  
Processes data in real-time (append-only). Ideal for low-latency ingestion and continuous data flow.  
 • 💾 Materialized View:  
Stores precomputed results in a Delta table. Great for aggregations, CDC, or frequently accessed data.  
 • 👓 View:  
Logical, on-demand computation used for intermediate transformations and data quality validation.

🔁 Simplified CDC with APPLY CHANGES

DLT removes the pain of handling Change Data Capture:  
 • Automatically handles late-arriving records  
 • Eliminates complex merge/update logic  
 • Ensures accuracy and consistency in target tables  


📥 Streamlined Data Ingestion

DLT supports ingestion from:  
 • Cloud storage (S3, ADLS, GCS)  
 • Kafka/message queues  
 • Databases like PostgreSQL  

💡 Pro Tip: Use Auto Loader + Streaming Tables for optimized performance!

✅ Built-in Data Quality with Expectations

Define rules to validate data as it flows:  
 • EXPECT <condition> – log and continue  
 • EXPECT ... ON VIOLATION DROP – discard bad records  
 • EXPECT ... ON VIOLATION FAIL – halt pipeline on error  

These expectations give you robust data governance with real-time metrics.


💡 Why It Matters:  
 • 🔹 Declarative + testable pipelines  
 • 🔹 Fully managed orchestration  
 • 🔹 Native support for streaming, CDC, batch  
 • 🔹 Built-in quality checks and lineage tracking  



### Unity Catalog
Unity Catalog is Databricks’ unified governance layer for data, ML models, and notebooks across all workspaces and cloud providers.

✅ Key Features:
Centralized Metadata Management: One place to manage schemas, tables, and permissions.

Fine-Grained Access Control:

Table-, row-, and column-level security using RBAC.

Supports attribute-based access control (ABAC) with dynamic views.

Data Lineage Tracking:

Automatically captures full lineage for tables, views, and notebooks.

Governance Across Workspaces:

Share assets across multiple Databricks workspaces securely.

🛡️ Example Benefits:
Regulatory compliance (e.g., GDPR, HIPAA).

Centralized control of who can see and edit specific data.

Secure data sharing across teams or business units.

<https://mayursurani.medium.com/end-to-end-etl-pipeline-for-insurance-domain-a-complete-guide-with-aws-pyspark-and-databricks-8bcea86e55fd>
