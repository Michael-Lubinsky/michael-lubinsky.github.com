https://lancedb.github.io/lance/  Lance format

https://www.vladsiv.com/big-data-file-formats/

https://towardsdatascience.com/demystifying-the-parquet-file-format-13adb0206705

https://davidgomes.com/understanding-parquet-iceberg-and-data-lakehouses-at-broad/

Book: Advanced analytics with PySpark
https://www.oreilly.com/library/view/advanced-analytics-with/9781098103644/


### Parquet Vs Delta File Format:

🧾 1. Parquet File Format:
Type: columnar storage format.
Optimized For: Efficient read performance, especially for analytics.

Key Features:
1. Column-wise compression → reduced file size.
2. Splittable files → parallel processing.
3. Works well with Hive, Spark, Presto, BigQuery, etc.

Limitations: No built-in support for ACID transactions, versioning, or schema enforcement.

🔼 2. Delta File Format (Delta Lake)
Built On: Parquet format + transactional layer (_delta_log).
Optimized For: Reliable, scalable data lakes with ACID transactions.

Key Features:
1. ACID transactions (safe concurrent reads/writes).
2. Schema enforcement and evolution.
3. Time travel (query past versions).
4. Supports MERGE, UPDATE, and DELETE operations.
5. Ideal for streaming + batch (unified) data workflows.

Use With: Apache Spark, Databricks, Azure Synapse, Delta-RS (for Presto/Trino support).
