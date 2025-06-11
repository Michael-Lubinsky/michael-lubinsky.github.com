### Databricks Versions 
| Version            | Spark Version | Release Date   | Support Ends                                                     |
| ------------------ | ------------- | -------------- | ---------------------------------------------------------------- |
| **16.4 LTS**       | 3.5.2         | May 9, 2025    | May 9, 2028                                                      |
| 15.4 LTS           | 3.5.0         | Aug 19, 2024   | Aug 19, 2027                                                     |
| 14.3 LTS           | 3.5.0         | Feb 1, 2024    | Feb 1, 2027                                                      |
| … Other LTS        | Older Sparks  | Various        | See release notes ([docs.databricks.com][1], [docs.azure.cn][2]) |
| **17.0 (Beta)**    | 4.0.0         | May 20, 2025   | Nov 20, 2025                                                     |
| 16.3 / 16.2 / 16.1 | 3.5.x         | Early–mid 2025 | Mid–late 2025                                                    |


### Delta Lake
Delta Lake is an open-source storage layer that brings reliability, performance, and governance to data lakes. It is tightly integrated with Databricks and underpins much of its functionality.

✅ Key Features:
ACID Transactions: Guarantees data integrity with support for concurrent writes and reads.

Schema Enforcement & Evolution: Prevents bad data and allows schema changes over time.

Time Travel: Query historical versions of data using VERSION AS OF or TIMESTAMP AS OF.

Data Compaction (OPTIMIZE): Merges small files into larger ones to improve performance.

Streaming + Batch: Supports both in the same pipeline using the same Delta table.

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




### DLT Delta Live Tables

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

