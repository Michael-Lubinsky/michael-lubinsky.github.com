### Snowflake Core Concepts & Architecture

Three-layer architecture:

- Database Storage – Optimized, compressed, columnar storage in cloud blob storage
- Compute Layer – Independent virtual warehouses (clusters)
- Cloud Services Layer – Metadata management, authentication, query optimization

### Virtual Warehouses:

Decoupled compute  
Can auto-scale (multi-cluster)  
Pausable to save costs  

### Micro-partitions:
Immutable 16MB–512MB blocks  
Automatically created on data ingestion  
Columnar, sorted, compressed, metadata-rich  

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

 
