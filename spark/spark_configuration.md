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
### Executor and Memory Tuning Strategies
```
1. Determine Executor Count and Core Allocation
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

2. Allocate Memory Effectively
Divide memory between the driver and executors based on workload requirements.

Avoid allocating all system memory to executors; leave some for the operating system.
Use the spark.executor.memoryOverhead setting if your job requires more off-heap memory.
Example:

--conf spark.executor.memory=16g 
--conf spark.executor.memoryOverhead=4g

3. Monitor Garbage Collection
Java-based systems, including Spark, rely on garbage collection (GC). Poor memory allocation can trigger frequent GC, slowing down tasks.

Use the G1GC garbage collector for large memory workloads.
Configure GC settings using spark.executor.extraJavaOptions.
Example:

--conf spark.executor.extraJavaOptions="-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35"

4. Enable Dynamic Resource Allocation
Dynamic Resource Allocation adjusts executor count based on workload demands.

--conf spark.dynamicAllocation.enabled=true

5. Use Spark UI for Performance Monitoring
The Spark UI provides valuable insights into executor memory usage, task distribution, and shuffle operations. Monitor these metrics to identify bottlenecks and adjust configurations accordingly.


Optimizing Big Data Processing in Databricks!!

_Interviewer:_ Let's say we're processing a massive dataset of 5 TB in Databricks. How would you configure the cluster to achieve optimal performance?

_Candidate:_ To process 5 TB of data efficiently, I'd recommend a cluster configuration with a mix of high-performance nodes and optimized storage. First, I'd estimate the number of partitions required to process the data in parallel.

Assuming a partition size of 256 MB, we'd need:

5 TB = 5 x 1024 GB = 5,120 GB

Number of partitions = 5,120 GB / 256 MB = 20,000 partitions

To process these partitions in parallel, we need to determine the optimal number of nodes. A common rule of thumb is to allocate 1-2 CPU cores per partition. Based on this, we can estimate the total number of CPU cores required:

20,000 partitions x 1-2 CPU cores/partition = 20,000-40,000 CPU cores

Assuming each node has 200-400 partitions/node (a reasonable number to ensure efficient processing), we can estimate the number of nodes required:

Number of nodes = Total number of partitions / Partitions per node
= 20,000 partitions / 200-400 partitions/node
= 50-100 nodes

In terms of memory, we need to ensure that each node has sufficient memory to process the partitions. A common rule of thumb is to allocate 2-4 GB of memory per CPU core. Based on this, we can estimate the total memory required:

50-100 nodes x 20-40 GB/node = 1000-4000 GB

Therefore, we'd recommend a cluster configuration with:

- 50-100 high-performance nodes (e.g., AWS c5.2xlarge or Azure D16s_v3)
- 20-40 GB of memory per node

This configuration would provide a good balance between processing power and memory capacity.

_Interviewer:_ That's a great approach! How would you decide the number of executors and executor cores required?

_Candidate:_ To decide the number of executors and executor cores, I'd consider the following factors:

- Number of partitions: 20,000 partitions
- Desired level of parallelism: 50-100 nodes
- Memory requirements: 20-40 GB per node

Assuming 5-10 executor cores per node, we'd need:

Number of executor cores = 50-100 nodes x 5-10 cores/node = 250-1000 cores

Number of executors = Number of executor cores / 5-10 cores/executor = 25-100 executors

_Interviewer:_ What about memory requirements? How would you estimate the total memory required?

_Candidate:_ To estimate the total memory required, I'd consider the following factors:

- Number of executors: 25-100 executors
- Memory per executor: 20-40 GB

Total memory required = Number of executors x Memory per executor = 500-4000 GB

Therefore, we'd need a cluster with at least 500-4000 GB of memory to process 5 TB of data efficiently.

_Interviewer:_ Finally, can you tell me how you'd handle data skew and optimize data processing performance?


To handle data skew, I'd use techniques like:

- Salting: adding a random value to the partition key to reduce skew
- Bucketing: dividing data into smaller buckets to reduce skew
```


### Spark Performance
https://blog.devgenius.io/debugging-spark-jobs-using-spark-webui-21fa7ace0eb7

https://medium.com/@mahakg290399/mastering-apache-spark-performance-a-deep-dive-into-optimization-techniques-4d3b087004a8

https://medium.com/@sksami1997/how-much-spark-do-you-need-estimating-resource-requirements-without-guesswork-a0b9e751c047

https://blog.det.life/deep-dive-into-spark-jobs-and-stages-481ecf1c9b62


### Partitioning vs bucketing
https://medium.com/@ghoshsiddharth25/partitioning-vs-bucketing-in-apache-spark-a37b342082e4

https://tech8byte.wordpress.com/2022/07/05/partitioning-vs-bucketing-in-apache-spark/
