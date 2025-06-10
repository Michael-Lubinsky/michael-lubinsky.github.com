### Delta Lake
Delta Lake is an open-source storage layer that brings reliability, performance, and governance to data lakes. It is tightly integrated with Databricks and underpins much of its functionality.

✅ Key Features:
ACID Transactions: Guarantees data integrity with support for concurrent writes and reads.

Schema Enforcement & Evolution: Prevents bad data and allows schema changes over time.

Time Travel: Query historical versions of data using VERSION AS OF or TIMESTAMP AS OF.

Data Compaction (OPTIMIZE): Merges small files into larger ones to improve performance.

Streaming + Batch: Supports both in the same pipeline using the same Delta table.


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

