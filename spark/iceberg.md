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

Would you like a diagram showing how catalogs fit into the Iceberg architecture?

4o

##### How Iceberg catalog is related to Databricks delta tables?

 

Apache Iceberg catalogs and **Databricks Delta tables (Delta Lake)** serve **similar purposes** in the big data ecosystem, but they are **distinct technologies** developed by different organizations and have **different underlying architectures**.

Here’s a comparison to clarify how they relate:

* * *

### 🔷 1. **Role and Purpose**

| Feature | Iceberg Catalog | Delta Lake (Databricks)
|---------|-----------------|------------------------
**Purpose** Manages metadata for Iceberg tables  Manages metadata and data for Delta tables

**Catalog** Separate system (Hive, REST, etc.) for metadata  Built into Delta Lake / Unity Catalog on Databricks

**Table Format** Apache Iceberg open standard Delta Lake table format developed by Databricks

* * *

### 🔶 2. **Integration with Engines**
---------------------------------
| Feature | Iceberg | Delta Lake
|---------|---------|------------
**Engine Compatibility**  Spark, Trino, Flink, Presto, etc. Primarily Spark (esp. Databricks), now Trino, Flink

**Catalog Use** External catalogs (Hive, REST, Glue) Databricks Unity Catalog or Hive metastore

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

Concept  Iceberg   Delta Lake (Databricks)

**Open Source** Yes    Yes (core), but enhanced on Databricks

**Metadata Storage**  External catalog (Hive, REST, etc.)   Built-in or Unity Catalog

**Compute Decoupled**  Yes  Mostly Spark-based (Databricks optimized)

**Standard Format**  Apache Iceberg  Delta Lake format

