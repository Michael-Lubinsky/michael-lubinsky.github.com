
### Config

from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName("LargeDataProcessing") \
    .config("spark.sql.shuffle.partitions", "200") \  # Adjust based on data size
    .config("spark.driver.memory", "8g") \            # Increase if needed
    .config("spark.executor.memory", "16g") \         # Allocate more for large jobs
    .getOrCreate()

###   Reading Large Datasets

```
df = spark.read.format("parquet").load("hdfs:///data/large_dataset.parquet")
df.show(5)
```
### Partitioning & Bucketing
Partitioning splits data into directories (e.g., by date)  
Bucketing groups data within partitions for optimized joins.
```
df.write.partitionBy("date").parquet("hdfs:///data/partitioned_dataset")
df.write.bucketBy(10, "customer_id").saveAsTable("bucketed_table")
```
###   Transformations
```
df_filtered = df.filter(df["sales"] > 5000)
df_grouped = df_filtered.groupBy("category").sum("sales")
df_grouped.show()
```
### Handle Skewed Data
Check distribution:
```
df.groupBy("category").count().show()
```
Repartition to balance data:
```
df = df.repartition("category")  # Or manually: df.repartition(200)
```
### Tuning Spark Configurations
Adjust Shuffle Partitions & Memory
```
spark.conf.set("spark.sql.shuffle.partitions", "400")  # Default is 200
spark.conf.set("spark.executor.memory", "32g")         # Increase for heavy workloads
```
### Use Broadcast Joins for Small Tables
Avoid shuffling by broadcasting small DataFrames:
```
from pyspark.sql.functions import broadcast
df_large = spark.read.parquet("hdfs:///data/large_dataset.parquet")
df_small = spark.read.parquet("hdfs:///data/small_lookup.parquet")
result_df = df_large.join(broadcast(df_small), "key_column")
```
### Writing Large Data Efficiently

Use Parquet/ORC for storage efficiency.

Coalesce partitions to reduce output files:
```
df.coalesce(10).write.format("parquet").save("hdfs:///data/output")
```
Overwrite mode to avoid duplicates:
```
df.write.mode("overwrite").parquet("hdfs:///data/output")
```
###  Monitoring & Debugging Performance

Access the Spark Web UI at:

http://localhost:4040

### Analyze Query Execution Plans
Check optimization opportunities with:

df.explain(True)  # Displays physical/logical plansConclusion
 

<https://medium.com/@sgouda835/handling-large-data-volumes-100gb-1tb-in-pyspark-best-practices-optimizations-b0ce2fe73f24>


<https://medium.com/towards-data-engineering/parquet-internals-7a51d2aaf8ae>
