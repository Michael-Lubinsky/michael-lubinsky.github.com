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

```


### Spark Performance
https://blog.devgenius.io/debugging-spark-jobs-using-spark-webui-21fa7ace0eb7

https://medium.com/@mahakg290399/mastering-apache-spark-performance-a-deep-dive-into-optimization-techniques-4d3b087004a8

https://medium.com/@sksami1997/how-much-spark-do-you-need-estimating-resource-requirements-without-guesswork-a0b9e751c047

https://blog.det.life/deep-dive-into-spark-jobs-and-stages-481ecf1c9b62


### Partitioning vs bucketing
https://medium.com/@ghoshsiddharth25/partitioning-vs-bucketing-in-apache-spark-a37b342082e4

https://tech8byte.wordpress.com/2022/07/05/partitioning-vs-bucketing-in-apache-spark/
