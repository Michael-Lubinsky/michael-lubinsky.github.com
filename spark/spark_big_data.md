### Config
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .appName("LargeDataProcessing") \
    .config("spark.sql.shuffle.partitions", "200") \  # Adjust based on data size
    .config("spark.driver.memory", "8g") \            # Increase if needed
    .config("spark.executor.memory", "16g") \         # Allocate more for large jobs
    .getOrCreate()
```
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
```python
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

Access the Spark Web UI at:  <http://localhost:4040>


### Configure Spark to process 10–100 TB of data
```
To process **10–100 TB of data per day** with Apache Spark efficiently, the optimal cluster configuration depends on several factors including data format, processing complexity, 
I/O throughput, and the SLAs (e.g., whether you need to finish processing in real-time, hourly, or daily). 
That said, here's a **baseline recommendation** for batch workloads, assuming structured data in formats like Parquet or ORC, and moderate-to-complex Spark transformations.
```
* * *

### 🔧 **Cluster Configuration (Baseline for 50 TB/day)**

#### **1\. Number of Nodes**

-   **Total nodes**: 50–200 worker nodes (adjust based on throughput needs and data volume).
    
-   **Node type**: 16–32 cores, 128–256 GB RAM, SSD-backed disks or networked storage (like EBS or HDFS).
    
-   For 100 TB/day, scale to 300–400 nodes if needed.
```
Volume	Nodes	Cores/Node	RAM/Node	Total Cores	Daily Throughput Target
10 TB	~50	16	128 GB	800	~417 MB/sec
50 TB	~150	32	256 GB	4800	~2.4 GB/sec
100 TB	~300	32	256 GB	9600	~4.8 GB/sec
```    

### ⚙️ **Spark JVM Configuration**

Tweak these based on executor size and garbage collection overhead:

```bash
--executor-memory 20G
--driver-memory 20G
--executor-cores 5
--num-executors 500  # or use dynamic allocation
--conf spark.executor.memoryOverhead=4G
--conf spark.serializer=org.apache.spark.serializer.KryoSerializer
--conf spark.sql.shuffle.partitions=2000  # tune based on input size
--conf spark.sql.adaptive.enabled=true
--conf spark.network.timeout=800s
--conf spark.rpc.askTimeout=600s
--conf spark.storage.memoryFraction=0.3
--conf spark.shuffle.service.enabled=true
--conf spark.dynamicAllocation.enabled=true
```

* * *

### 🔄 **Jobs per Node / Job Concurrency**

-   **Jobs per node**: 2–4 concurrent Spark jobs per node if they are not CPU-bound.
    
-   For streaming or real-time batch ingestion, use **separate clusters** or **YARN/Mesos pools** to isolate workloads.
    

* * *

### 🧠 **Tuning Recommendations**

-   Use **columnar formats** like Parquet with predicate pushdown.
    
-   Ensure data is **evenly partitioned** (~128–512 MB per partition).
    
-   Avoid **data skews** in joins or aggregations.
    
-   Consider **caching** reference datasets (`broadcast` joins for small tables).
    
-   Enable **adaptive query execution (AQE)** for dynamic optimizations.
    

* * *

### ☁️ Cloud-specific Notes

If using EMR, Databricks, or GCP Dataproc:

-   Use **auto-scaling** with spot/preemptible nodes for cost savings.
    
-   Leverage **autoscaling clusters** to handle variance between 10–100 TB loads.




### Analyze Query Execution Plans
Check optimization opportunities with:

df.explain(True)  # Displays physical/logical plansConclusion
 

<https://medium.com/@sgouda835/handling-large-data-volumes-100gb-1tb-in-pyspark-best-practices-optimizations-b0ce2fe73f24>

<https://medium.com/@abheshekh1285/how-to-master-spark-caching-myths-mistakes-and-best-practices-410a90054c45>


<https://medium.com/towards-data-engineering/parquet-internals-7a51d2aaf8ae>
