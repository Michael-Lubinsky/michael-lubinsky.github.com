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

### Project:
 Please describe how to design and implement in Snowflake the following ETL pipeline.
There are 3 input datasets as below.

Input  dataset 1:  100 millions rows daily.
Files on AWS S3  the daily clickstream.
Every row has following columns:
timestamp, action (can be START or STOP or PAUSE), user_id, movie_id, device_type, operating_system.
File format: AVRO or CSV
AWS S3 buckets are named as YYYY-MM-DD

Input dataset 2: 50,000 records
Dataset of movies stored  on S3 in JSONL format, has movie_id attribute and many other attributes per movie (movie_name, genre, date, language, artists) 


Input Dataset 3:  50 millions records
This is users dataset, it has user_id and  other users attributes, like user_name, user_location, etc 

QUESTIONS:
How to load 3 imput datasets into SnowFlake once per day?
Which Datawarehouse configuration to use?
How to cluster the tables?
How to join  datasets on columns  show_id and to calculate total time per movie per genre for given time range? 
How to join   datasets on columns user_id  to calculate total time per user? 

How to use QUERY_HISTORY, WAREHOUSE_LOAD_HISTORY, METERING_HISTORY?
How to Track long-running or costly queries?


