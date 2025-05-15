### Iceberg catalog

**Iceberg catalog** is a **metadata management system** used by **Apache Iceberg**, a high-performance table format designed for large-scale analytic datasets.

### What is Apache Iceberg?

Apache Iceberg is an open table format for huge analytic datasets, designed to work with engines like:

-   **Apache Spark**
    
-   **Trino**
    
-   **Presto**
    
-   **Flink**
    
-   **Hive**
    

It solves problems with traditional Hive-style tables such as:

-   Lack of ACID guarantees
    
-   Poor performance on large datasets
    
-   Difficulty managing metadata
    

* * *

### What is an Iceberg Catalog?

An **Iceberg catalog** is the **component that tracks where tables are stored and how to access them**. It maps table names to their metadata locations and allows for **table discovery, creation, and versioning**.

There are several types of Iceberg catalogs:

Catalog Type  Description

**Hadoop Catalog**  Stores metadata in HDFS or S3, often in the same directory as the data

**Hive Catalog**  Integrates with the Hive Metastore to store table metadata locations

**REST Catalog** A service-based approach where a REST API handles catalog interactions

**Nessie Catalog** Provides Git-like version control for data tables

**Glue Catalog** Uses AWS Glue Data Catalog for metadata

* * *

### Why is it important?

The catalog enables Iceberg to:

-   Manage table metadata independently from compute engines
    
-   Support schema evolution and partition evolution
    
-   Maintain full table history (time travel, rollback)
    
-   Handle concurrent writes with ACID guarantees
    

* * *

### Example Workflow

1.  You create an Iceberg table in Spark:
    
    `spark.sql("CREATE TABLE db.users (id BIGINT, name STRING) USING iceberg")`
    
2.  The catalog stores metadata about this table (schema, file locations, snapshots).
    
3.  Another engine (e.g., Trino) can read this same table using the catalog.
    

* * *

##### How Iceberg catalog is related to Databricks delta tables?

 
Apache Iceberg catalogs and **Databricks Delta tables (Delta Lake)** serve **similar purposes** in the big data ecosystem, but they are **distinct technologies** developed by different organizations and have **different underlying architectures**.

Here’s a comparison to clarify how they relate:

* * *

### 🔷 1. **Role and Purpose**

| Feature | Iceberg Catalog | Delta Lake (Databricks)
|---------|-----------------|------------------------
| **Purpose** | Manages metadata for Iceberg tables | Manages metadata and data for Delta tables
| **Catalog** | Separate system (Hive, REST, etc.) for metadata  | Built into Delta Lake / Unity Catalog on Databricks
| **Table Format** | Apache Iceberg open standard | Delta Lake table format developed by Databricks

* * *

### 🔶 2. **Integration with Engines**
 
| Feature | Iceberg | Delta Lake
|---------|---------|------------
| **Engine Compatibility**  | Spark, Trino, Flink, Presto, etc. | Primarily Spark (esp. Databricks), now Trino, Flink
| **Catalog Use** | External catalogs (Hive, REST, Glue)|  Databricks Unity Catalog or Hive metastore

* * *

### 🔸 3. **ACID & Versioning**

Both support:

-   ACID transactions
    
-   Schema evolution
    
-   Time travel (accessing old table versions)
    
-   Partition evolution
    

But **Iceberg separates the table format from the compute layer**, while **Delta Lake is more tightly integrated with Spark** (and especially Databricks).

* * *

### 🔹 4. **Catalog Example: Unity Catalog**

In Databricks, if you’re using **Unity Catalog**, it acts **similar to an Iceberg catalog**:

-   Stores table metadata centrally
    
-   Provides table discovery and access control
    
-   Enables multi-engine access (e.g., SQL, Spark, Python, etc.)
    

So, **Unity Catalog is to Delta tables what Hive/REST catalog is to Iceberg tables**.

* * *

### 🧩 Summary

| Concept |  Iceberg |  Delta Lake (Databricks) |
|---------|----------|--------------------------|
| **Open Source** | Yes |    Yes (core), but enhanced on Databricks|
|**Metadata Storage**  | External catalog (Hive, REST, etc.)  |  Built-in or Unity Catalog
| **Compute Decoupled**  |  Yes  | Mostly Spark-based (Databricks optimized)
|**Standard Format**  | Apache Iceberg  | Delta Lake format


### Databricks Delta: 
Uses a transaction log (Delta Log) stored alongside the data in the object storage.  
This log is an ordered record of every transaction (commit) made to the table.  
The log contains information about added and removed data files, schema changes, and other metadata.  Periodically, the Delta Log is compacted into Parquet checkpoint files to improve query performance and manage the log size

### Apache Iceberg: Employs a three-tiered metadata architecture:
1. Metadata Files: Store the table's schema, partitioning specification, and a pointer to the current manifest list.

2. Manifest Lists: List all the manifest files for the table.

3. Manifest Files: List the data files that make up a snapshot of the table, along with their partition
values,
file-level statistics (like row count, min/max values for columns), and column-level statistics.

 This hierarchical structure allows for efficient metadata management and faster query planning, especially for large tables. 
 Iceberg avoids reliance on a central metastore for most operations, only using it to store the pointer to the latest metadata.



 
### The choice between Iceberg and Delta Lake depends on your infrastructure, workload, and strategic goals:

For flexibility and future-proofing: Iceberg is the safer bet due to its open ecosystem, 
scalability, and broad adoption across clouds and engines. 
It’s ideal for organizations avoiding vendor lock-in or managing complex, large-scale datasets.

For Databricks-centric environments: Delta Lake is superior for Spark/Databricks users, offering seamless integration, real-time capabilities, and UniForm for Iceberg compatibility.

Proof of Concept (PoC): Test both formats with your workload, focusing on schema evolution, query performance, and integration with your stack. 
High-volume jobs will reveal practical differences (e.g., Iceberg’s metadata efficiency vs. Delta’s streaming speed).

If you’re starting fresh and prioritize openness, Iceberg’s momentum (e.g., AWS S3 Tables, Snowflake Polaris) makes it a strong contender for 2025 and beyond.
If you’re in Databricks, Delta’s optimizations and UniForm provide immediate value with future Iceberg compatibility.


Iceberg’s documentation: apache.iceberg.io
Delta Lake’s documentation: delta.io
