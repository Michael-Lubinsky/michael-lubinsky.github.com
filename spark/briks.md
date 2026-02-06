### Databricks Versions 

| Version            | Spark Version | Release Date   | Support Ends                                                     |
| ------------------ | ------------- | -------------- | ---------------------------------------------------------------- |
|  16.4 LTS       | 3.5.2         | May 9, 2025    | May 9, 2028                                                      |
| 15.4 LTS           | 3.5.0         | Aug 19, 2024   | Aug 19, 2027                                                     |
| 14.3 LTS           | 3.5.0         | Feb 1, 2024    | Feb 1, 2027                                                      |
|  17.0 (Beta)     | 4.0.0         | May 20, 2025   | Nov 20, 2025                                                     |
| 16.3 / 16.2 / 16.1 | 3.5.x         | Early–mid 2025 | Mid–late 2025                                                    |

```
Catalog (top-level container)
│
├── Schema (aka Database)
│   │
│   ├── Table (dataset)
│   ├── View (saved query)
│   └── Function (UDF)
```

<https://blog.dataengineerthings.org/>

<https://smartdataconf.ru/schedule/topics/#topic-2>

<https://www.waitingforcode.com/>  Bartosz Konieczny

https://buf.build/resources/data-engineering-design-patterns

https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf

<https://sympathetic.ink/2025/12/11/Column-Storage-for-the-AI-era.html>

<https://www.uber.com/blog/from-batch-to-streaming-accelerating-data-freshness-in-ubers-data-lake/>

### Databricks CLI
```bash

pip install "databricks-sdk[sql]" databricks-cli
databricks configure --token
databricks sql warehouses list
databricks sql query run \
  --warehouse-id <your-warehouse-id> \
  --statement "SELECT * FROM catalog.schema.table LIMIT 10"

brew tap databricks/tap
brew install databricks
databricks --version
databricks --help
cat  ~/.databricks/config
databricks auth profiles
databricks warehouses list
databricks auth describe -p work

# show number of record in table
TABLE=mlubinsly_telemetry
echo $TABLE

## hardcode table inside:
databricks api post /api/2.0/sql/statements \
  --json '{
    "warehouse_id": "c39aadaef2c738fb",
    "statement": "SELECT count(*) FROM hcai_databricks_dev.chargeminder2.mlubinsky_telemetry",
    "wait_timeout": "30s"
  }' -p work

echo $TABLE


databricks api post /api/2.0/sql/statements \
  --json "{
    \"warehouse_id\": \"c39aadaef2c738fb\",
    \"statement\": \"SELECT count(*) FROM hcai_databricks_dev.chargeminder2.${TABLE}\"
  }" -p work
```

### Delta Lake
Delta Lake is an open-source storage layer that brings reliability, performance, and governance to data lakes. It is tightly integrated with Databricks and underpins much of its functionality.

✅ Key Features:
ACID Transactions: Guarantees data integrity with support for concurrent writes and reads.

Schema Enforcement & Evolution: Prevents bad data and allows schema changes over time.

Time Travel: Query historical versions of data using VERSION AS OF or TIMESTAMP AS OF.

Data Compaction (OPTIMIZE): Merges small files into larger ones to improve performance.

Streaming + Batch: Supports both in the same pipeline using the same Delta table.

[Databricks commands](Databricks_commands.pdf)

[Delta Table](DeltaTabl.pdf)

[DTL - Delta Live Tables](DeltaLiveTables-DLT.pdf)

[Delta Live Tables](Apache%20Spark%20and%20Delta%20Table%20.pdf)

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

###  Summary

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

<https://medium.com/@mariusz_kujawski/why-i-liked-delta-live-tables-in-databricks-b55b5a97c55c>

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

```python
from pyspark.sql.functions import col
from dlt import table, expect

@table(
    comment="Cleaned user events with expectations enforced",
    spark_conf={"spark.databricks.delta.schema.autoMerge.enabled": "true"}
)
@expect("valid_user_id", "user_id IS NOT NULL")
@expect("valid_event_type", "event_type IN ('click', 'view', 'purchase')")
def user_events_cleaned():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .load("/mnt/raw/user_events")
    )
```


### Explanation

#### 1. `@expect(...)` decorators:
- `valid_user_id`: Ensures rows have non-null `user_id`
- `valid_event_type`: Restricts to expected `event_type` values  
  ➤ Rows that fail are **recorded but not included** in the resulting table.

#### 2. Schema evolution:
- Enabled via:  
  ```python
  spark_conf={"spark.databricks.delta.schema.autoMerge.enabled": "true"}
  ```
- If new columns appear in the source (e.g., `device_type`), DLT will **automatically update** the schema of the target Delta table.

#### 3. Autoloader (`cloudFiles`):
- Automatically ingests files incrementally from the specified path.

#### Optional: Route bad records

To store failed rows, use:

```python
@dlt.expect_or_drop("valid_user_id", "user_id IS NOT NULL")
```

or  

```python
@dlt.expect_all({"valid_user_id": "user_id IS NOT NULL", ...})
```

To **store** failed rows in a separate table:

```python
@dlt.expect("valid_user_id", "user_id IS NOT NULL", on_failure="redirect")
@dlt.expect("valid_event_type", "event_type IN ('click', 'view', 'purchase')", on_failure="redirect")
```

Then the failed rows go to a **default `_expectations_failed_record` table**.


💡 Why It Matters:  
 • 🔹 Declarative + testable pipelines  
 • 🔹 Fully managed orchestration  
 • 🔹 Native support for streaming, CDC, batch  
 • 🔹 Built-in quality checks and lineage tracking  




### ✅ Example: Delta Live Tables (DLT) Pipeline in Databricks

This example defines a **DLT pipeline** with 2 stages:
1. **Raw input** from JSON files in a mounted path (Bronze)
2. **Cleaned data** with basic transformations (Silver)

### 🔸 Python Notebook Example (for DLT)

```python
import dlt
from pyspark.sql.functions import col

# Ingest raw JSON data into Bronze table
@dlt.table(
    name="raw_orders",
    comment="Raw order data ingested from JSON files"
)
def raw_orders():
    return (
        spark.read.json("/mnt/raw/orders/")
    )

# Transform and clean raw data into Silver table
@dlt.table(
    name="clean_orders",
    comment="Cleaned order data with proper schema"
)
def clean_orders():
    df = dlt.read("raw_orders")
    return (
        df
        .filter(col("order_id").isNotNull())
        .withColumnRenamed("orderAmount", "amount")
    )
```

---

### 🔸 How to Use:

1. Save the code in a Databricks **DLT notebook**.
2. Create a **Delta Live Table pipeline** in the UI:
   - Click **Workflows → Delta Live Tables → Create Pipeline**
   - Select your notebook and storage location.
   - Set mode to **Triggered** (for batch) or **Continuous** (for streaming).
3. Run the pipeline.

---

### 🧠 Notes:
- `@dlt.table` registers the function output as a managed Delta Live Table.
- You can also use `@dlt.view` for intermediate views.
- Input can be JSON, CSV, Kafka, Auto Loader, etc.

Let me know if you want an example with Kafka input or full Bronze → Silver → Gold DLT structure.



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



# Delta Table Schema Evolution in Databricks

Databricks **Delta Tables** support **schema evolution** by allowing your table’s schema to **automatically adapt to changes** in your data, such as **adding new columns**. This is particularly useful in **streaming or incremental batch pipelines** where the incoming data structure might change over time.

---

## ✅ Key Features of Delta Table Schema Evolution

| Capability                         | Supported? | Notes                                                                 |
|------------------------------------|------------|-----------------------------------------------------------------------|
| Add new columns                    | ✅         | Automatically with `mergeSchema = true`                              |
| Change column types                | ❌ (limited) | Requires manual DDL or full overwrite                                |
| Drop columns                       | ❌         | Not allowed directly via schema evolution                            |
| Nested column evolution            | ✅         | With support for complex types (Struct, Array)                       |
| Schema evolution in streaming      | ✅         | Via **Auto Loader** or structured streaming + `mergeSchema`          |
| Schema enforcement (validation)    | ✅         | Rejects writes with incompatible schema unless `mergeSchema=true`    |

---

## 🧪 Example: Schema Evolution in Batch Write

```python
df = spark.read.json("s3://bucket/new_data/")  # Assume new data has additional column 'new_col'

df.write \
  .format("delta") \
  .option("mergeSchema", "true") \
  .mode("append") \
  .save("/mnt/delta/events")
```

> Delta Lake will **merge the schema** of `df` with the existing table, adding `new_col` automatically.

---

## 🔁 Schema Evolution in Streaming with Auto Loader

```python
df = spark.readStream \
  .format("cloudFiles") \
  .option("cloudFiles.format", "json") \
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns") \
  .load("s3://incoming-json/")

df.writeStream \
  .format("delta") \
  .option("mergeSchema", "true") \
  .option("checkpointLocation", "/mnt/checkpoints/schema-evolve") \
  .start("/mnt/delta/evolving_table")
```

> ✅ New fields are **added** to the schema dynamically without breaking the stream.

---

##  Important Notes

- `mergeSchema` must be explicitly set to `true` to allow evolution.
- Schema evolution **does not allow removing columns** — you must use a table rewrite or `ALTER TABLE`.
- Changing data types (e.g., from `int` to `string`) is **not allowed** implicitly; use explicit DDL if needed.

---

## 🛠 Enforcing or Disabling Schema Changes

Delta tables support schema **enforcement** as well. You can control it via:

```sql
ALTER TABLE my_table SET TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5'
);
```

Or, to **disable automatic evolution**, omit `mergeSchema` or set:

```python
.option("mergeSchema", "false")
```

---

## 📚 Summary

| Operation                    | Supported in Delta Lake? | Requires `mergeSchema=true`? |
|-----------------------------|---------------------------|-------------------------------|
| Adding columns              | ✅                        | ✅                            |
| Changing column types       | ❌ (manually via DDL)     | N/A                           |
| Dropping columns            | ❌ (DDL only)


### Databricks SQL `MERGE`  

The **`MERGE`** command in **Databricks SQL** (also known as **`MERGE INTO`**) is used to **perform upserts**—a combination of **update**, **insert**, and **delete** operations—on a **Delta Lake table**, based on matching records from a source table or query.

---

### ✅ Syntax: Databricks SQL `MERGE INTO`

```sql
MERGE INTO target_table AS target
USING source_table AS source
ON <matching_condition>
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

You can also:
- Customize `UPDATE` with column mappings
- Add conditional logic (e.g., `WHEN MATCHED AND ...`)
- Perform `DELETE` when matched

---

## 🔹 Example: UPSERT into Delta Table

```sql
MERGE INTO customers AS target
USING updates AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN
  UPDATE SET
    target.name = source.name,
    target.email = source.email

WHEN NOT MATCHED THEN
  INSERT (customer_id, name, email)
  VALUES (source.customer_id, source.name, source.email)
```

---

## 🔧 Real-World Use Cases

| Use Case                    | How `MERGE` Helps                            |
|-----------------------------|----------------------------------------------|
| Upserting CDC (change data) | Inserts new rows, updates existing ones      |
| Slowly Changing Dimensions  | Implement SCD Type 1 / 2 transformations     |
| Deduplicating data          | Merge only when a newer version is present   |
| Merg



### How to Create and Periodically Update a Materialized View in Databricks

Databricks **does not natively support "materialized views"** like traditional databases (e.g., Postgres, Snowflake), but you can **simulate** materialized views using **Delta tables** along with **scheduled jobs** or **Delta Live Tables (DLT)**.

---

#### ✅ Option 1: Materialized View using Delta Table + Scheduled SQL Query

### Step 1: Create a Delta Table to Act as Materialized View

```sql
CREATE TABLE sales_mv
USING DELTA
AS
SELECT
  customer_id,
  SUM(amount) AS total_spent,
  COUNT(*) AS transaction_count
FROM sales
GROUP BY customer_id;
```

### Step 2: Schedule SQL Job to Refresh It Periodically

- Go to **Databricks Jobs UI**
- Create a new **SQL Job**
- Use a query like:

```sql
MERGE INTO sales_mv AS target
USING (
  SELECT
    customer_id,
    SUM(amount) AS total_spent,
    COUNT(*) AS transaction_count
  FROM sales
  GROUP BY customer_id
) AS source
ON target.customer_id = source.customer_id

WHEN MATCHED THEN UPDATE SET
  target.total_spent = source.total_spent,
  target.transaction_count = source.transaction_count

WHEN NOT MATCHED THEN
  INSERT (customer_id, total_spent, transaction_count)
  VALUES (source.customer_id, source.total_spent, source.transaction_count);
```

- Set the schedule (e.g., every hour)

---

## ✅ Option 2: Materialized View with Delta Live Tables (DLT)

DLT lets you define streaming or batch pipelines with auto-managed tables.

### Step 1: Define a DLT Pipeline

```python
import dlt
from pyspark.sql.functions import sum, count

@dlt.table(name="sales_mv_dlt")
def sales_mv():
    df = dlt.read("sales")
    return df.groupBy("customer_id").agg(
        sum("amount").alias("total_spent"),
        count("*").alias("transaction_count")
    )
```

### Step 2: Configure Pipeline Settings

- Set **trigger interval** (e.g., every 15 minutes)
- Define pipeline in Databricks DLT UI
- Optionally enable **auto-refresh** and **schema evolution**

---

## 🛠 Notes and Best Practices

- Use **Delta** format for fast reads/writes
- Use **Z-Ordering** on `customer_id` if queries are filter-heavy
- For slowly changing data, consider **MERGE** logic or **SCD** patterns
- Store metadata (e.g., last refresh timestamp) in a helper table if needed

---

## 🧪 Summary Table

| Technique                     | Refresh Method         | Native Support |
|------------------------------|------------------------|----------------|
| Delta table + SQL Job        | Via Databricks Jobs UI | ✅ (manual)     |
| Delta Live Table (DLT)       | Auto-managed refresh   | ✅ (recommended)|
| Traditional materialized view| Not supported          | ❌              |

###  Read from **Kafka** in Databricks (Structured Streaming)

Databricks provides native support for **Apache Kafka** using `spark.readStream` with the Kafka source.

### 🔸 Kafka Configuration Example:
```python
df_kafka = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "your_kafka_broker:9092")
    .option("subscribe", "your_topic_name")
    .option("startingOffsets", "earliest")  # or "latest"
    .load()
)

# Optional: Convert value (binary) to string
df_kafka_parsed = df_kafka.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
```

### 🔸 Kafka Notes:
- You may need a **cluster-scoped init script** or install the **Kafka connector** from the **Maven coordinate**:  
  Example:
  ```python
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1
  ```

---

## ✅ 2. Read from **PostgreSQL** in Databricks

Use **JDBC** to connect to PostgreSQL using `spark.read.format("jdbc")`.

### 🔸 PostgreSQL Read Example:
```python
jdbc_url = "jdbc:postgresql://<host>:<port>/<database>"
connection_props = {
    "user": "your_username",
    "password": "your_password",
    "driver": "org.postgresql.Driver"
}

df_postgres = spark.read.format("jdbc") \
    .option("url", jdbc_url) \
    .option("dbtable", "your_table_name") \
    .options(**connection_props) \
    .load()
```

### 🔸 You may need to install the JDBC driver:
- Maven coordinate:  
  `org.postgresql:postgresql:42.6.0`

---

## 🧠 Recommendations:
- Use **Auto Loader** or **Delta Live Tables** if your sources are ingested to a landing zone (e.g., Kafka -> Bronze → Silver).
- For **CDC** or **incremental load** from Postgres, use a `WHERE` clause with a timestamp column and/or use **Z-Ordering** for performance.

#### Real-Time Grafana Dashboard for HSL Transport Data

<https://datatribe.substack.com/p/building-a-real-time-transport-lakehouse>

<https://www.youtube.com/watch?v=lOgl7OtgE1o>

<https://github.com/oiivantsov/transport-streaming-lakehouse>



## Histogram Visualization in Databricks

Here are several ways to create a histogram with 10 buckets based on column distance in table:

## Method 1: SQL with WIDTH_BUCKET (Easiest)

```sql
SELECT 
  WIDTH_BUCKET(distance, 
    (SELECT MIN(distance) FROM your_table), 
    (SELECT MAX(distance) FROM your_table), 
    10
  ) AS distance_bucket,
  COUNT(*) AS trip_count
FROM your_table
GROUP BY distance_bucket
ORDER BY distance_bucket
```

Then click the **Bar Chart** icon and configure:
- **X axis**: `distance_bucket`
- **Y axis**: `trip_count` (Sum)

---

## Method 2: SQL with Named Buckets (More Readable)

First, find your min/max distance to determine bucket ranges:

```sql
SELECT MIN(distance) AS min_dist, MAX(distance) AS max_dist
FROM your_table
```

Then create buckets (assuming distance ranges from 0 to 100):

```sql
SELECT 
  CASE 
    WHEN distance >= 0 AND distance < 10 THEN '0-10'
    WHEN distance >= 10 AND distance < 20 THEN '10-20'
    WHEN distance >= 20 AND distance < 30 THEN '20-30'
    WHEN distance >= 30 AND distance < 40 THEN '30-40'
    WHEN distance >= 40 AND distance < 50 THEN '40-50'
    WHEN distance >= 50 AND distance < 60 THEN '50-60'
    WHEN distance >= 60 AND distance < 70 THEN '60-70'
    WHEN distance >= 70 AND distance < 80 THEN '70-80'
    WHEN distance >= 80 AND distance < 90 THEN '80-90'
    WHEN distance >= 90 THEN '90+'
  END AS distance_range,
  COUNT(*) AS trip_count
FROM your_table
GROUP BY distance_range
ORDER BY distance_range
```

---

## Method 3: SQL with Dynamic Buckets

Calculate bucket width automatically:

```sql
WITH stats AS (
  SELECT 
    MIN(distance) AS min_dist,
    MAX(distance) AS max_dist,
    (MAX(distance) - MIN(distance)) / 10.0 AS bucket_width
  FROM your_table
)
SELECT 
  FLOOR((distance - stats.min_dist) / stats.bucket_width) AS bucket_number,
  CONCAT(
    CAST(ROUND(stats.min_dist + FLOOR((distance - stats.min_dist) / stats.bucket_width) * stats.bucket_width, 1) AS STRING),
    ' - ',
    CAST(ROUND(stats.min_dist + (FLOOR((distance - stats.min_dist) / stats.bucket_width) + 1) * stats.bucket_width, 1) AS STRING)
  ) AS distance_range,
  COUNT(*) AS trip_count
FROM your_table
CROSS JOIN stats
GROUP BY bucket_number, distance_range, stats.min_dist, stats.max_dist, stats.bucket_width
ORDER BY bucket_number
```

---

## Method 4: Python with Matplotlib (Most Control)

```python
import matplotlib.pyplot as plt

# Get data
df = spark.sql("""
  SELECT distance 
  FROM your_table
  WHERE distance IS NOT NULL
""").toPandas()

# Create histogram
plt.figure(figsize=(10, 6))
plt.hist(df['distance'], bins=10, color='steelblue', edgecolor='black')
plt.xlabel('Distance')
plt.ylabel('Number of Trips')
plt.title('Trip Distribution by Distance')
plt.grid(axis='y', alpha=0.3)

# Display
display(plt.gcf())
```

---

## Method 5: Python with Databricks display()

```python
# Calculate buckets in SQL
buckets_df = spark.sql("""
  SELECT 
    WIDTH_BUCKET(distance, 
      (SELECT MIN(distance) FROM your_table), 
      (SELECT MAX(distance) FROM your_table), 
      10
    ) AS bucket,
    COUNT(*) AS count
  FROM your_table
  GROUP BY bucket
  ORDER BY bucket
""")

# Display with built-in visualization
display(buckets_df)
```

Then use the bar chart visualization.

---

## Recommended Approach

**Start with Method 1 (WIDTH_BUCKET)** - it's the simplest and automatically handles the bucket ranges for you. Here's the complete workflow:

```sql
-- Step 1: Create the histogram data
CREATE OR REPLACE TEMP VIEW distance_histogram AS
SELECT 
  WIDTH_BUCKET(distance, 
    (SELECT MIN(distance) FROM your_table), 
    (SELECT MAX(distance) FROM your_table), 
    10
  ) AS bucket,
  COUNT(*) AS trip_count,
  ROUND(MIN(distance), 1) AS bucket_min,
  ROUND(MAX(distance), 1) AS bucket_max
FROM your_table
GROUP BY bucket
ORDER BY bucket;

-- Step 2: View results
SELECT * FROM distance_histogram;
```

Then click the **Bar Chart** icon below the results!

Which method would you prefer?

### Databricks Links

<https://www.youtube.com/@easewithdata/playlists>

<https://www.youtube.com/playlist?list=PL2IsFZBGM_IGiAvVZWAEKX8gg1ItnxEEb>  
<https://blog.devgenius.io/databricks-platform-basics-de00317bbf2c>

<https://medium.com/dev-genius/databricks-platform-advanced-18c2dcfe31a5>

 <https://medium.com/towards-data-engineering/building-the-right-data-for-ai-deep-dive-into-databricks-job-etl-pipeline-and-ingestion-pipeline-351532b569df>

<https://medium.com/towards-data-engineering/when-dbfs-is-not-an-option-how-databricks-volumes-saved-the-day-for-file-based-learning-on-free-a0e0e92579ce>

<https://medium.com/towards-data-engineering/databricks-declarative-pipelines-how-databricks-dlt-saved-my-day-d95cc72db2b5>

<https://medium.com/towards-data-engineering/databricks-apps-builder-ecosystem-9d825a9666f8>

<https://mayursurani.medium.com/end-to-end-etl-pipeline-for-insurance-domain-a-complete-guide-with-aws-pyspark-and-databricks-8bcea86e55fd>

<https://medium.com/towards-data-engineering/real-world-retail-data-pipeline-using-databricks-declarative-pipelines-8b80ea7bc34c>


Databricks X PySpark INTERVIEW QUESTIONS (2026 Guide) | PySpark Real-Time Scenarios
https://www.youtube.com/watch?v=__9tqYjEJhE

### Apache Iceberg

<https://www.youtube.com/watch?v=XluBSLT60h8&list=PLGVZCDnMOq0qi19dNwAO6KxWmMqXppGpz&index=47&pp=iAQB>

https://habr.com/ru/companies/ru_mts/articles/926618/
