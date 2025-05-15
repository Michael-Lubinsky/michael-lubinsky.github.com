### Databricks Delta Table*

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


##### How to access databrick delta table via databricks Unity catalog?

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

