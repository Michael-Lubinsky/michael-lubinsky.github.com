### Config


### Key Settings:

```
--executor-memory 16G 
--executor-cores 4 
--num-executors 15 
--driver-memory 8G
```


### Spark Config Tuning:


```
spark.conf.set("spark.sql.shuffle.partitions", "400") 
spark.conf.set("spark.memory.fraction", "0.8")   # More memory for execution
```


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
###  Adjust Shuffle Partitions & Memory
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
To process **10–100 TB of data per day** with Apache Spark efficiently,
the optimal cluster configuration depends on several factors including data format, processing complexity, 
I/O throughput, and the SLAs (e.g., whether you need to finish processing in real-time, hourly, or daily).
That said, here's a **baseline recommendation** for batch workloads, assuming structured data in formats like Parquet or ORC,
 and moderate-to-complex Spark transformations.
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
```
df.explain(True)  # Displays physical/logical plansConclusion
```

<https://medium.com/@sgouda835/handling-large-data-volumes-100gb-1tb-in-pyspark-best-practices-optimizations-b0ce2fe73f24>

<https://medium.com/@abheshekh1285/how-to-master-spark-caching-myths-mistakes-and-best-practices-410a90054c45>


<https://medium.com/towards-data-engineering/parquet-internals-7a51d2aaf8ae>



### Config params
```
the number of executor instances to launch.
--conf spark.executor.instances=10

Sets the number of cores for each executor.
--conf spark.executor.cores=4

Defines the amount of memory allocated to each executor.
--conf spark.executor.memory=8g

Specifies the memory allocated to the driver program.
--conf spark.driver.memory=4g

Controls the fraction of total memory available for execution and storage
(default is 0.6).
--conf spark.memory.fraction=0.7


Defines the fraction of memory reserved for storage-related tasks (default is 0.5 of the memory fraction).
```

### EXAMPLE
```

Lets say you have a 1000 node spark cluster

Each node is of size - 16 cpu cores / 64 gb RAM

Let's say each node has 3 executors,
with each executor of size - 5 cpu cores / 21 GB RAM (Remaining goes for overheads)

Let's answer the following questions..

=> 1. What's the total capacity of cluster?

We will have 1000 * 3 = 3000 executors

Total CPU capacity: 3000 * 5 = 15000 cpu Cores

Total Memory capacity: 3000 * 21 = 63000 GB RAM (63 TB)

=> 2. How many parallel tasks can run on this cluster?

We have 15000 CPU cores, so we can run at the max 15000 parallel tasks on this cluster.

=> 3. Let's say you requested for 4 executors then how many parallel tasks can run?

so the capacity we got is (4 * 5 = 20) cpu cores

(4 * 21 = 84) GB RAM

so a total of 20 parallel tasks can run at the max.

=> 4. Let's say we have a 1 TB file stored in datalake and have to do some filtering of data, how many tasks will run.
Assume we are requesting for 50 executors (5 cores, 21 GB RAM each)

if we create a dataframe out of 1 TB file we will get 8000 partitions in our dataframe. (will cover in my next post on how many partitions are created)

so we have 8000 partitions each of size 128 mb.

so our job will run 8000 total tasks but are all of this in parallel? let's see.

we have (50 * 5 = 250) cpu cores

lets say each task takes around 10 second to process 128 mb data.

so first 250 tasks run in parallel,

once these 250 tasks are done the other 250 tasks are executed and so on...

so totally 32 cycles (in sequence), if we think the most ideal scenario.

10 sec + 10 sec + .... (32 times) = 320 seconds.

=> 5. is there a possibility of, out of memory error in the above scenario?

Each executor has 5 cpu cores and 21 gb ram.

This 21 gb RAM is divided in various parts -

300 mb reserved memory,

40% user memory to store user defined variables/data. example hashmap

60% spark memory - this is divided 50:50 between storage memory and execution memory.

so basically we are looking at execution memory and it will be around 28% roughly of the total memory allotted.

so consider around 6 GB of 21 GB memory is meant for execution memory.

per cpu core we have (6 GB / 5 cores) = 1.2 GB execution memory.

That means our task can roughly handle around 1.2 GB of data.

however, we are handling 128 mb so we are well under this range.

```


### Executor and Memory Tuning Strategies

#### 1. Determine Executor Count and Core Allocation
```

To calculate the optimal number of executors and cores:

Identify the total number of worker nodes and available cores per node.
Divide the total cores by the number of executors per node.
Example Calculation:

Assume 5 worker nodes, each with 16 cores and 64 GB memory.
Allocate 4 cores per executor and 16 GB memory per executor.
You can launch (16 cores / 4 cores per executor) = 4 executors per node.
Across 5 nodes, that’s 5 nodes * 4 executors = 20 executors.
Configuration:

--conf spark.executor.instances=20 
--conf spark.executor.cores=4 
--conf spark.executor.memory=16g
```
#### 2. Allocate Memory Effectively
```
Divide memory between the driver and executors based on workload requirements.

Avoid allocating all system memory to executors; leave some for the operating system.
Use the spark.executor.memoryOverhead setting if your job requires more off-heap memory.
Example:

--conf spark.executor.memory=16g 
--conf spark.executor.memoryOverhead=4g
```
#### 3. Monitor Garbage Collection
   ```
Java-based systems, including Spark, rely on garbage collection (GC). Poor memory allocation can trigger frequent GC, slowing down tasks.

Use the G1GC garbage collector for large memory workloads.
Configure GC settings using spark.executor.extraJavaOptions.
Example:

--conf spark.executor.extraJavaOptions="-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35"
```
#### 4. Enable Dynamic Resource Allocation
```
Dynamic Resource Allocation adjusts executor count based on workload demands.

--conf spark.dynamicAllocation.enabled=true
```
#### 5. Use Spark UI for Performance Monitoring
```
The Spark UI provides valuable insights into executor memory usage, task distribution,
and shuffle operations.
Monitor these metrics to identify bottlenecks and adjust configurations accordingly.
```


### How to configure Spark to process  5 TB in Databricks?

```
To process 5 TB of data efficiently, I'd recommend a cluster configuration 
with a mix of high-performance nodes and optimized storage.
First, I'd estimate the number of partitions required to process the data in parallel.

Assuming a partition size of 256 MB, we'd need:

5 TB = 5 x 1024 GB = 5,120 GB

Number of partitions = 5,120 GB / 256 MB = 20,000 partitions

To process these partitions in parallel, we need to determine the optimal number of nodes.
A common rule of thumb is to allocate 1-2 CPU cores per partition.
 Based on this, we can estimate the total number of CPU cores required:

20,000 partitions x 1-2 CPU cores/partition = 20,000-40,000 CPU cores

Assuming each node has 200-400 partitions/node (a reasonable number to ensure efficient processing),
we can estimate the number of nodes required:

Number of nodes = Total number of partitions / Partitions per node
= 20,000 partitions / 200-400 partitions/node
= 50-100 nodes

In terms of memory, we need to ensure that each node has sufficient memory to process the partitions.
 A common rule of thumb is to allocate 2-4 GB of memory per CPU core.
Based on this, we can estimate the total memory required:

50-100 nodes x 20-40 GB/node = 1000-4000 GB

Therefore, we'd recommend a cluster configuration with:

- 50-100 high-performance nodes (e.g., AWS c5.2xlarge or Azure D16s_v3)
- 20-40 GB of memory per node

This configuration would provide a good balance between processing power and memory capacity.
```

###   How to decide the number of executors and executor cores required?

To decide the number of executors and executor cores, I'd consider the following factors:

- Number of partitions: 20,000 partitions
- Desired level of parallelism: 50-100 nodes
- Memory requirements: 20-40 GB per node

Assuming 5-10 executor cores per node, we'd need:

Number of executor cores = 50-100 nodes x 5-10 cores/node = 250-1000 cores

Number of executors = Number of executor cores / 5-10 cores/executor = 25-100 executors

### Memory requirements:  how  estimate the total memory required?

To estimate the total memory required, I'd consider the following factors:

- Number of executors: 25-100 executors
- Memory per executor: 20-40 GB

Total memory required = Number of executors x Memory per executor = 500-4000 GB

Therefore, we'd need a cluster with at least 500-4000 GB of memory to process 5 TB of data efficiently.

### How to  handle data skew and optimize data processing performance?


- Salting: adding a random value to the partition key to reduce skew
- Bucketing: dividing data into smaller buckets to reduce skew
 



## RDD vs DataFrame

In Apache Spark, **RDD** (Resilient Distributed Dataset) and **DataFrame** 
are two core abstractions for working with distributed data, but they differ in several key ways:

* * *

### 🔹 1. **Definition**

| Feature       | RDD                               | DataFrame                                    |
| ------------- | --------------------------------- | -------------------------------------------- |
| **Type**      | Low-level API                     | High-level API                               |
| **Structure** | Distributed collection of objects | Distributed collection of rows with a schema |
| **Schema**    | No schema (unstructured)          | Has a schema (structured)                    |


* * *

### 🔹 2. **Ease of Use**

| RDD | DataFrame |
|-----|------------|
| Requires more code for operations | Easier to use due to SQL-like syntax
| Based on functional programming (map, reduce, etc.) | Can use SQL queries or dataframe-style syntax

* * *

### 🔹 3. **Performance**

| RDD  | DataFrame |
|-----|------------|
| Slower due to lack of optimization | Faster due to Catalyst optimizer and Tungsten execution engine
| No automatic optimization | Optimized logical and physical execution plans

* * *

### 🔹 4. **Type Safety**

| RDD | DataFrame |
|-----|------------|
| Type-safe (compile-time checks) | Not type-safe (runtime errors possible) in Python/Scala
| Strong typing in Scala/Java | Columns accessed by name (less compile-time checking)

* * *

### 🔹 5. **Use Cases**

| RDD                                            | DataFrame                                                       |
| ---------------------------------------------- | --------------------------------------------------------------- |
| When low-level transformations are needed      | When you need performance and SQL-like queries                  |
| When working with unstructured data            | Ideal for structured/semi-structured data (e.g., JSON, Parquet) |
| When needing full control over data processing | When productivity and performance are priorities                |


* * *

### 🔹 6. **Interoperability**

You can convert between RDD and DataFrame:


```python
# From RDD to DataFrame (Python)
df = rdd.toDF(schema) 
# From DataFrame to 
RDD rdd = df.rdd
```

* * *

### ✅ Summary

| Feature           | RDD                            | DataFrame                        |
| ----------------- | ------------------------------ | -------------------------------- |
| Abstraction level | Low                            | High                             |
| Performance       | Slower                         | Faster                           |
| Type safety       | Yes (Scala/Java)               | No (Python/Scala)                |
| Optimization      | Manual                         | Automatic                        |
| Use case          | Custom processing, legacy code | Analytics, ETL, SQL-like queries |




#####   What is data skew in Spark and how to fix it?


**Data skew** in Apache Spark refers to a situation where **data is unevenly distributed across partitions**, causing some tasks to process significantly more data than others. This leads to performance bottlenecks because Spark tasks are executed in parallel, and the slowest task (usually the skewed one) holds up the entire job.

* * *

### 🔍 **Why Data Skew Happens**

-   Certain keys appear **much more frequently** than others in your dataset.
    
-   Joins or aggregations are performed on **highly skewed keys**.
    
-   Hash partitioning or shuffle operations place a disproportionate amount of data on a few partitions.
    

* * *

### 🧨 **Problems Caused by Data Skew**

-   Long-running tasks (stragglers)
    
-   OOM (Out of Memory) errors
    
-   Inefficient CPU usage
    
-   Long job execution time
    

* * *

### 🛠️ **How to Fix Data Skew in Spark**

#### 1\. **Salting the Key (Key Salting)**

Add a random prefix or suffix to the skewed key to artificially distribute the load across partitions.

```python
# Before salting
skewed_df = df.filter(df["key"] == "hot_key")

# After salting (example in PySpark)
import random
df = df.withColumn("salted_key", concat(df["key"], lit("_"), lit(random.randint(0, 10))))
```

Then, join using `salted_key` instead of `key`.

* * *

#### 2\. **Skewed Join Optimization**

If only a few keys are skewed, treat them differently:

-   Separate skewed keys.
    
-   Process skewed and non-skewed parts separately.
    
-   Combine results afterward.
    

```python
# Pseudo-strategy
skewed = df.filter("key = 'skewed_value'")
normal = df.filter("key != 'skewed_value'")

# Handle them separately and then union
```

* * *

#### 3\. **Broadcast Join**

If one side of the join is small, broadcast it to all worker nodes to avoid shuffle altogether.

 

`from pyspark.sql.functions import broadcast df_large.join(broadcast(df_small), "key")`

* * *

#### 4\. **Repartitioning**

Manually repartition the data to try to balance it better.



`df.repartition("key")  # Caution: might worsen performance if skew still exists`

* * *

#### 5\. **Increase Parallelism**

Increase the number of shuffle partitions:


`spark.conf.set("spark.sql.shuffle.partitions", "200")  # default is 200, increase if needed`

* * *

#### 6\. **Custom Partitioning**

Use a custom partitioner to better distribute skewed keys, especially in RDD-based code.

* * *

### 📊 Detecting Data Skew

-   Use the **Spark UI > Stages > Tasks** tab to check for straggling tasks.
    
-   Look for **partitions** that process **significantly more data** than others.
    
-   Log or analyze key distributions manually (`groupBy("key").count()`).
    

* * *

### ✅ Summary Table

| Fix                  | When to Use                 | Pros              | Cons                           |
| -------------------- | --------------------------- | ----------------- | ------------------------------ |
| Salting              | Small number of skewed keys | Simple, effective | Needs custom logic             |
| Broadcast Join       | One table is small          | No shuffle        | Doesn't scale for large tables |
| Repartitioning       | Moderate skew               | Easy to try       | Not always effective           |
| Skewed Join Handling | Known skewed keys           | Very efficient    | Complex to manage              |
| Custom Partitioner   | Using RDDs                  | Full control      | Needs careful tuning           |






### Spark Performance
https://blog.devgenius.io/debugging-spark-jobs-using-spark-webui-21fa7ace0eb7

https://medium.com/@mahakg290399/mastering-apache-spark-performance-a-deep-dive-into-optimization-techniques-4d3b087004a8

https://medium.com/@sksami1997/how-much-spark-do-you-need-estimating-resource-requirements-without-guesswork-a0b9e751c047

https://blog.det.life/deep-dive-into-spark-jobs-and-stages-481ecf1c9b62


### Partitioning vs bucketing
https://medium.com/@ghoshsiddharth25/partitioning-vs-bucketing-in-apache-spark-a37b342082e4

https://tech8byte.wordpress.com/2022/07/05/partitioning-vs-bucketing-in-apache-spark/


* * *

### 🔥 1. **Out of Memory Errors (OOM)**

**Symptoms**:

-   `java.lang.OutOfMemoryError: Java heap space`
    
-   `GC overhead limit exceeded`
    

**Causes**:

-   Too many intermediate objects in memory
    
-   Large shuffles or joins
    
-   Skewed data distribution
    

**Solutions**:

-   **Increase executor memory**:
    
    `--executor-memory 4g`
    
-   **Use `persist()` or `cache()`** wisely (avoid caching everything)
    
-   **Broadcast small datasets** when joining:
    
    `broadcast(small_df)`
    
-   **Optimize partitioning**: Increase partitions using `repartition()` or `coalesce()` wisely
    
-   **Enable spill to disk** for shuffle-heavy operations
    

* * *

### ⚙️ 2. **Shuffle Issues**

**Symptoms**:

-   Slow stage execution
    
-   Errors related to shuffle file reads
    

**Causes**:

-   Too many partitions
    
-   Large amount of data shuffled
    
-   Skewed partitions (some tasks taking much longer)
    

**Solutions**:

-   Increase `spark.sql.shuffle.partitions` (default is 200)
    
-   Use **salting** or **bucketing** to handle skew
    
-   Use **map-side aggregation** before shuffling
    

* * *

### 🐌 3. **Skewed Data**

**Symptoms**:

-   Some tasks take much longer than others
    
-   One executor doing most of the work
    

**Causes**:

-   Uneven key distribution in joins or aggregations
    

**Solutions**:

-   Add a **salting key** to reduce skew
    
-   Use `salting` + `groupBy` + `agg`
    
-   Use **adaptive query execution (AQE)**:
  
    
    `spark.conf.set("spark.sql.adaptive.enabled", "true")`
    

* * *

### 🔄 4. **Job Stuck or Takes Too Long**

**Symptoms**:

-   Jobs hang or run forever
    
-   UI shows no progress
    

**Causes**:

-   Complex DAGs
    
-   Inefficient transformations
    
-   Bad joins (e.g., Cartesian join)
    

**Solutions**:

-   Break the job into stages and `checkpoint()` intermediate results
    
-   Avoid wide transformations like `groupByKey`, prefer `reduceByKey`
    
-   Check physical plan with `.explain(extended=True)`
    
-   Repartition large datasets before join
    

* * *

### 🧮 5. **Driver Memory Issues**

**Symptoms**:

-   Driver crashes
    
-   `OutOfMemoryError` in driver logs
    

**Causes**:

-   Collecting too much data to the driver (`collect()`, `toPandas()`)
    

**Solutions**:

-   Avoid `.collect()` unless absolutely necessary
    
-   Use `.show(n)` or `.take(n)` instead
    
-   Increase driver memory:
    
    `--driver-memory 4g`
    

* * *

### 🔌 6. **Resource Misconfiguration**

**Symptoms**:

-   Executors idle or underutilized
    
-   Not enough parallelism
    

**Causes**:

-   Incorrect number of cores or memory per executor
    

**Solutions**:

-   Tune `--executor-cores` and `--num-executors`
    
-   Use dynamic allocation if supported:
    
    
    `spark.conf.set("spark.dynamicAllocation.enabled", "true")`
    

* * *

### 🛠️ 7. **Serialization Issues**

**Symptoms**:

-   Slow performance
    
-   Errors related to serialization
    

**Solutions**:

-   Use **Kryo serialization** for better performance:
  
    
    `spark.conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")`
    

* * *



##  Let's look at **example configurations and tuning tips** for three common Spark workloads:

* * *

## ✅ 1. **ETL Workload (Extract, Transform, Load)**

### Common Features:

-   Reading/writing from data sources (CSV, Parquet, DBs)
    
-   Lots of filtering, column transformations
    
-   Moderate joins
    

### Key Settings:

`--executor-memory 4G --executor-cores 2 --num-executors 10 --driver-memory 4G`

### Spark Config Tuning:


```
spark.conf.set("spark.sql.shuffle.partitions", "200")  # Adjust based on cluster size
spark.conf.set("spark.sql.adaptive.enabled", "true")   # Enable AQE
spark.conf.set("spark.sql.files.maxPartitionBytes", "134217728")  # 128 MB
spark.conf.set("spark.sql.broadcastTimeout", "300")    # Increase if needed
```

### Tips:

-   Use **Parquet** or **ORC** instead of CSV
    
-   Push filters early with `.filter()` before wide transformations
    
-   Repartition by join key if large shuffle expected:
  
    
    `df.repartition("customer_id")`
    

* * *

## ✅ 2. **Join-Heavy Analytics Workload**

### Common Features:

-   Joining big tables (e.g., user activity + metadata)
    
-   Aggregations and groupBy on joined results
    

### Key Settings:


`--executor-memory 8G --executor-cores 4 --num-executors 20`

### Spark Config Tuning:


```
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "50MB")  # Or larger if memory allows spark.conf.set("spark.sql.adaptive.enabled", "true")            # Adaptive join selection spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")   # Handle data skew
```

### Tips:

-   Use **broadcast joins** for small tables:
    
    
    `from pyspark.sql.functions import broadcast df1.join(broadcast(df2), "id")`
    
-   Avoid **Cartesian joins**
    
-   Use `.hint("shuffle_hash")` or `.hint("broadcast")` if AQE isn't enough
    

* * *

## ✅ 3. **Machine Learning Workload**

### Common Features:

-   Feature engineering (vectorization, scaling)
    
-   Model training (e.g., MLlib)
    
-   Cache-heavy pipelines
    


### Tips:

-   Cache intermediate feature engineering steps:
    
    
    `features_df.persist()`
    
-   Avoid `.collect()` on large predictions
    
-   Use **pipeline API** to structure transformations cleanly
    



## 🧰 Example Setup (AWS EMR)

### ⚙️ Cluster Spec

-   **Instance type**: `m5.xlarge` (4 vCPU, 16 GB RAM per node)
    
-   **Nodes**: 1 master + 5 core nodes
    
-   **Spark workload**: Batch ETL (daily jobs), ~500 GB of Parquet data in S3
    

* * *

## ✅ Spark Tuning Strategy

### 1\. **Executor Configuration**

`--executor-cores 2 --executor-memory 6G --num-executors 10`

Each `m5.xlarge` has:

-   4 vCPUs → 2 executors with 2 cores each per node
    
-   16 GB RAM → ~12 GB usable → 2 × 6 GB executors
    

Multiply by 5 worker nodes: 10 executors total.

> 🧠 Tip: Reserve ~1 GB per node for YARN and OS overhead.

* * *

### 2\. **Spark Submit Example**


```
spark-submit \
--deploy-mode cluster \
--master yarn \
--executor-cores 2 \
--executor-memory 6G \
--num-executors 10 \
 --driver-memory 4G \
--conf spark.sql.shuffle.partitions=200 \
--conf spark.sql.adaptive.enabled=true \
--conf spark.sql.broadcastTimeout=300 \
your_script.py
```

* * *

### 3\. **Common Config Tweaks for AWS EMR**

```
spark.conf.set("spark.sql.shuffle.partitions", "200")        # Match number of total cores
spark.conf.set("spark.sql.adaptive.enabled", "true")         # Adaptive execution
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.dynamicAllocation.enabled", "false")   # Fixed executors preferred unless you’re using a large autoscaling cluster
```
* * *

### 4\. **S3 Optimization Tips**

-   Prefer **Parquet** or **ORC** over CSV
    
-   Partition your data on relevant keys (`date`, `region`, etc.)
    
-   Avoid small files — combine them during write (e.g., using `coalesce()`)
    


`df.coalesce(50).write.mode("overwrite").parquet("s3://your-bucket/output/")`

* * *

### 5\. **Monitoring & Debugging**

-   Use **EMR Spark UI** (port 18080)
    
-   Review **stage DAGs** to identify wide transformations or skew
    
-   Use `.explain("extended")` to review physical plans
    

* * *



### What is a checkpoint in Apache Spark?


A **checkpoint** in Apache Spark is a mechanism to **persist the state of an RDD or DataFrame 
to reliable storage (like HDFS or S3)**, 
breaking the lineage and providing fault-tolerance and performance improvements for complex jobs.

* * *

### ✅ **Why Use Checkpointing?**

1.  **Avoid Long Lineages**  
    Spark builds a _lineage graph_ of transformations. With many steps, failures can be expensive to recover. Checkpointing saves the result to stable storage and cuts off the lineage.
    
2.  **Improve Fault Tolerance**  
    Especially in iterative algorithms (like ML training), checkpointing ensures Spark can recover without recomputing from the start.
    
3.  **Avoid StackOverflow**  
    Very long chains of narrow transformations may trigger stack overflow or performance issues.
    

* * *

### 🔧 How to Use It

1.  **Set the checkpoint directory** (should be on fault-tolerant storage like HDFS):
    
    `spark.sparkContext.setCheckpointDir("hdfs:///tmp/spark-checkpoints")`
    
2.  **Checkpoint an RDD or DataFrame**:
    
    `df.checkpoint()`
    
    or for an RDD:
    
    `rdd.checkpoint()`
    
3.  **Force materialization** (optional but recommended):
    
    `df = df.checkpoint() df.count()  # triggers the computation and writes checkpoint`
    

* * *

### 📌 Notes:

-   Checkpointing is **expensive**: it involves writing to disk and recomputing lineage up to that point.
    
-   Use **`.persist()` or `.cache()`** for performance boost if failure recovery isn’t critical.
    
-   For streaming applications (Structured Streaming), **checkpointing is required** for maintaining state between micro-batches.

