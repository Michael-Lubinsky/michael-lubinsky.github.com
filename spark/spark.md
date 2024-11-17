
 Avoid using count() Action
```
df = sqlContext.read().json(...);
if not len(df.take(1)):   # <-- use this  instead of: if not df.count():
```

### Bucketing:

without bucketing:
```
# Without Bucketing 
df1 = spark.table('table1')
df2 = spark.table('table2')

# Print the Physical plan of this join and join strategy by Spark
df1.join(df2, 'joining_key').explain()

Above code will shuffle i.e exchange the data as it is not bucketed.
SortMergeJoin is the default Spark join,
but now let’s avoid the data exchanges that happened by using bucketing

df.write\
    .bucketBy(32, 'joining_key') \
    .sortBy('date_created') \
    .saveAsTable('bucketed', format='parquet')

bucketBy() distributes data into a predetermined number of partitions,
providing a scalable solution when the cardinality of unique values is high.

However, for datasets with a limited number of distinct values,
partitioning is often a more efficient approach.
```



https://blog.devgenius.io/behind-the-scenes-what-happens-after-you-spark-submit-31439651f6df

https://towardsdatascience.com/feature-engineering-for-time-series-using-pyspark-on-databricks-02b97d62a287

https://medium.com/@kaviprakash.2007/spark-performance-optimization-in-databricks-a-complete-guide-ab57280a8260

### Spark performance

https://www.youtube.com/watch?v=O4MlLUYkjN8

https://rahultiwari876.medium.com/big-data-spark-optimization-techniques-part-1-d485c99ec66f

https://rahultiwari876.medium.com/big-data-spark-optimization-techniques-part-2-da866d6f8243


```
🔹🔹Broadcast Join🔹🔹
Best For: When one DataFrame is small enough to fit in memory.
How It Works: The smaller DataFrame is broadcasted to all nodes in the cluster, allowing the join to be performed locally on each partition.
✅Pros: Reduces network shuffling, leading to faster execution times.
❌Cons: Limited by the size of the smaller DataFrame; memory-intensive if not managed properly.

🔹🔹Sort-Merge Join🔹🔹
Best For: Large datasets that are already sorted or can be efficiently sorted by the join key.
How It Works: Spark sorts the data in each partition by the join key and then merges the partitions.
✅Pros: Efficient for large datasets and multi-column joins.
❌Cons: Requires sorting, which can be computationally expensive; may require more memory.

🔹🔹Shuffle Hash Join🔹🔹
Best For: General-purpose join when neither broadcast nor sort-merge is feasible.
How It Works: Data is shuffled across nodes based on the join key, and a hash table is used to perform the join.
✅Pros: Works well with large, unsorted datasets.
❌Cons: High network I/O due to shuffling; slower than the other join strategies.


🔹🔹Which One Should You Use?🔹🔹
Small DataFrame? Go for Broadcast Join.
Large, Pre-Sorted DataFrames? Sort-Merge Join is your friend.
Unsorted, Massive Data? Use Shuffle Hash Join, but be mindful of its performance impact.
```
####  Broadcast small DataFrames

 Example of a broadcast join
``` 
from pyspark.sql.functions import broadcast

small_df = spark.read.csv(“small_data.csv”)
large_df = spark.read.csv(“large_data.csv”)

joined_df = large_df.join(broadcast(small_df), “key”)
```
#### ReduceByKey over GroupByKey: 
Use reduceByKey instead of groupByKey to minimize the amount of data shuffled.


#### Spark Config

spark.executor.memory  
spark.executor.cores    
spark.sql.files.maxPartitionBytes: This parameter controls the size of each partition.

spark.conf.set(“spark.sql.adaptive.enabled”, “true”)  Enable AQE
spark.conf.set(“spark.sql.adaptive.enabled”, “true”)      Skew Join Optimization
spark.conf.set(“spark.sql.adaptive.skewJoin.enabled”, “true”) Skew Join Optimization

### Caching

https://blog.devgenius.io/spark-cache-persist-checkpoint-write-to-hdfs-0ea63ab4cb07

https://www.youtube.com/watch?v=p6_0qdd6X08

https://www.youtube.com/watch?v=KRAS7R2GWgc

Caching can improve performance when the same data is accessed multiple times.

```
• Choose the right storage level: Use appropriate storage levels (e.g., MEMORY_ONLY, MEMORY_AND_DISK) based on your application’s needs.

# Example of caching a DataFrame
df = spark.read.csv(“data.csv”)
df.cache()
```

### Query execution plan

https://www.youtube.com/watch?v=dCvxE2WSOsE

https://www.databricks.com/blog/2016/05/23/apache-spark-as-a-compiler-joining-a-billion-rows-per-second-on-a-laptop.html

https://premvishnoi.medium.com/exploring-apache-sparks-catalyst-optimizer-and-tungsten-execution-engine-57c51927cf1a

https://towardsdatascience.com/mastering-query-plans-in-spark-3-0-f4c334663aa4

https://medium.com/@deepa.account/spark-logical-and-physical-plan-generation-d0e7d7851d89

https://www.youtube.com/watch?v=UZt_tqx4sII - How to Read Spark Query Plans | Rock the JVM

https://www.youtube.com/watch?v=_Ne27JcLnEc - From Query Plan to Performance: Supercharging your Apache Spark Queries using the Spark UI SQL Tab

https://www.youtube.com/watch?v=rNpzrkB5KQQ  - Understanding the Spark UI

https://www.youtube.com/watch?v=lHJc0rEqjoU Spark UI

#### Explain plan

Official documentation:
https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.explain.html#pyspark.sql.DataFrame.explain

```
Spark provides an EXPLAIN() API to look at the Spark execution plan.
You can use this API with different modes like “simple,” “extended,” “codegen,” “cost,” or “formatted” 
to view the optimized logical plan and related statistics.

explain(extended = false  - Displays the physical plan.
explain(extended = true   -  Displays the physical as well as all the logical
explain(mode = "simple") — Displays the physical plan.
explain(mode = "extended") — Displays the physical and logical plans.
explain(mode = "codegen") — Displays the Java code generated for executing the query.
explain(mode = "cost") — Displays the optimized logical plan and related statistics.
explain(mode = "formatted") — Displays the simple physical plan and formatted input/output for the operators involved in details.


Example:
---------
explain codegen
select
    id,
    (id > 1 and id > 2) and (id < 1000 or (id + id) = 12) as test  
from
    range(0, 10000, 1, 32)


|== Physical Plan ==
* Project (2)
+- * Range (1)


(1) Range [codegen id : 1]
Output [1]: [id#36167L]
Arguments: Range (0, 10000, step=1, splits=Some(32))

(2) Project [codegen id : 1]
Output [2]: [id#36167L, (((id#36167L > 1) AND (id#36167L > 2)) AND ((id#36167L < 1000) OR ((id#36167L + id#36167L) = 12))) AS test#36161]
Input [1]: [id#36167L]



Example:
----------
  import contextlib
  import io

  with contextlib.redirect_stdout(io.StringIO()) as stdout:
      df.explain(mode="cost")

  logical_plan = stdout.getvalue().split("\n")
```

https://semyonsinchenko.github.io/ssinchenko/post/estimation-spark-df-size/

https://selectfrom.dev/apache-spark-query-plans-lets-explain-1dbb31989315

https://blog.gbrueckl.at/2024/04/visualizing-spark-execution-plans/

```
scala> sql("select v,count(*) from test_agg group by v").explain
== Physical Plan ==
*(2) HashAggregate(keys=[v#1], functions=[count(1)])
+- Exchange hashpartitioning(v#1, 200), true, [id=#41]
   +- *(1) HashAggregate(keys=[v#1], functions=[partial_count(1)])
      +- *(1) LocalTableScan [v#1]


scala> sql("select v,count(*) from test_agg group by v").explain(true)
== Parsed Logical Plan ==
'Aggregate ['v], ['v, unresolvedalias('count(1), None)]
+- 'UnresolvedRelation [test_agg]

== Analyzed Logical Plan ==
v: boolean, count(1): bigint
Aggregate [v#1], [v#1, count(1) AS count(1)#35L]
+- SubqueryAlias test_agg
   +- Project [k#0, v#1]
      +- SubqueryAlias test_agg
         +- LocalRelation [k#0, v#1]

== Optimized Logical Plan ==
Aggregate [v#1], [v#1, count(1) AS count(1)#35L]
+- LocalRelation [v#1]

== Physical Plan ==
*(2) HashAggregate(keys=[v#1], functions=[count(1)], output=[v#1, count(1)#35L])
+- Exchange hashpartitioning(v#1, 200), true, [id=#58]
   +- *(1) HashAggregate(keys=[v#1], functions=[partial_count(1)], output=[v#1, count#39L])
      +- *(1) LocalTableScan [v#1]


To read this plan, you should go bottom up. Spark reads the input dataset, which is a LocalTableScan in this scenario.
 Next, Spark used a HashAggregate for the aggregate function computation.
The aggregate function is count and the group by key is v. So in the first HashAggregate,
Spark will compute the partial count, denoted by partial_count. For each partition,
Spark will do a partial count operation and then merge the results in the final count.
There is an exchange, a shuffle operation. Spark is doing a hash partitioning for the exchange, and it used 200 as the shuffle partition.
The (1) and (2) are for the wholestage codegen stages. Everything with the same index number is in one stage.
So stage boundaries can be recognized by exchange operations that involve a shuffle.
```

### Explain extended
```
Below is another way to get the execution plan using the explain command, which will give the physical plan information.
If you use explain extended, it will give you the parsed logical plan, analyzed logical plan, optimized logical plan,
and the physical plan information as well.

scala> sql("explain select v,count(*) from test_agg group by v").show(false)
+-------------------
|plan                                                                                                                                                                                                                                    |
+------------------
|== Physical Plan ==
*(2) HashAggregate(keys=[v#1], functions=[count(1)])
+- Exchange hashpartitioning(v#1, 200), true, [id=#121]
   +- *(1) HashAggregate(keys=[v#1], functions=[partial_count(1)])
      +- *(1) LocalTableScan [v#1]

+---------------
 
If you have wholeStage disabled, you will not see the wholeStage codegen stage indexes in the plan.

scala> spark.conf.set("spark.sql.codegen.wholeStage", false)

scala> sql("select v,count(*) from test_agg group by v").explain(true)
== Parsed Logical Plan ==
'Aggregate ['v], ['v, unresolvedalias('count(1), None)]
+- 'UnresolvedRelation [test_agg]

== Analyzed Logical Plan ==
v: boolean, count(1): bigint
Aggregate [v#1], [v#1, count(1) AS count(1)#78L]
+- SubqueryAlias test_agg
   +- Project [k#0, v#1]
      +- SubqueryAlias test_agg
         +- LocalRelation [k#0, v#1]

== Optimized Logical Plan ==
Aggregate [v#1], [v#1, count(1) AS count(1)#78L]
+- LocalRelation [v#1]

== Physical Plan ==
HashAggregate(keys=[v#1], functions=[count(1)], output=[v#1, count(1)#78L])
+- Exchange hashpartitioning(v#1, 200), true, [id=#138]
   +- HashAggregate(keys=[v#1], functions=[partial_count(1)], output=[v#1, count#82L])
      +- LocalTableScan [v#1]
```
https://developer.ibm.com/blogs/how-to-understanddebug-your-spark-application-using-explain/

https://medium.com/@ashwin_kumar_/spark-internal-execution-plan-0d4ad067288a

https://medium.com/@deepa.account/spark-logical-and-physical-plan-generation-d0e7d7851d89

```
Spark 3.0 introduced the new feature of Adaptive Query Execution that enables changes in the Physical plan at runtime of the query on the cluster.
Based on the real-time query execution statistics, a much better plan can be incorporated at runtime.

spark.conf.set("spark.sql.adaptive.enabled", "true")

The feature is disabled by default and can be enabled using the above configuration.
The final effect of the feature can be only seen on Spark UI.
But in the plans generated, it does show that the feature is enabled with final Plan as False AdaptiveSparkPlan isFinalPlan=false
```

### Spark SQL with Parameterized Statements
https://github.com/deepavasanthkumar/spark_tips/blob/main/Spark_SQL_Paremeterized_Demo.ipynb
```
With Spark 3.4 onwards, we can directly query from a pyspark dataframe.
Till then, we have been creating a temporary view to provide SQL.

spark.sql("SELECT max(meantemp) FROM {table}",table=df).show()
spark.sql("SELECT date FROM {table} where meantemp = {maxmeantemp}",table=df, maxmeantemp=38.714285714285715).show()
```


### Partitioning and Bucketing

https://blog.det.life/apache-spark-partitioning-and-bucketing-1790586e8917

https://medium.com/@ashwin_kumar_/spark-partitioning-partition-understanding-2c1705c3b0a0

https://blog.devgenius.io/optimizing-pyspark-data-partitioning-vs-bucketing-45ab380e851a

https://medium.com/@ashwin_kumar_/spark-partitioning-vs-bucketing-partitionby-vs-bucketby-09c98c5b40eb

spark.sql.shuffle.partitions. By default, this parameter is set to 200 partitions.


following code to know the data distribution across partitions within a DataFrame or RDD.
```
rdd_partitions = departments.rdd.glom().collect()
for partition_id in range(len(rdd_partitions)):
  print ("partition_id :",partition_id,
         "departments_present :",set(row.departmentName
               for row in rdd_partitions[partition_id]),"partition_dist_cnt :",len(rdd_partitions[partition_id]))
```

#### Repartitioning by specifying only the Partition Column : 
```
In this case, data distribution across partitions will occur using the Hash partitioning method. 
Data will be distributed across partitions based on the hash values of the 'value' column. 
The number of partitions created will be determined by the configuration parameter:

spark.sql.shuffle.partitions. By default, this parameter is set to 200 partitions.

If AQE is enabled, Spark may not create 200 partitions
(AQE Internally uses Coalesce function to merge the smaller partitions), as this can lead to the generation of many empty partitions,
which is not an optimal scenario.
To follow this the code and its underlying principles,
you can disable AQE during the learning process and enable it again once its done.

# To Turn off AQE
spark.conf.set("spark.sql.adaptive.enabled", "False")

# To Turn on AQE
spark.conf.set("spark.sql.adaptive.enabled", "True")
```
#### Repartitioning using both Number of Partitions and Partition Column :
```
In this scenario, we will utilize both the number of partitions and the partition column to perform data repartitioning.
Once again, the method employed for distribution is hash partitioning,
but the number of partitions will align with the specified input parameter.
 Example:
departments = departments.repartition(4, "departmentName")
```
#### Repartitioning using range and Partition Column :
```
In this case, instead of specifying the number of partitions,
we will define a range of values based on the partition column.
This approach leverages Range partitioning to distribute the data across partitions.
 Example:
departments = departments.repartitionByRange(5,"departmentName")
```

```
// Increase the number of partitions
val repartitionedDF = largeDF.repartition(100, col(“key”))

// Decrease the number of partitions
val coalescedDF = largeDF.coalesce(10)
```
### Spark Joins
```
Broadcast Hash Join
Shuffle Hash Join
Sort Merge Join
Cartesian Join
Broadcast Nested Loop Join
```

https://www.linkedin.com/pulse/spark-join-strategies-mastering-joins-apache-venkatesh-nandikolla-mk4qc/

### Links
https://medium.com/towards-data-engineering/the-most-discussed-spark-questions-in-2024-8aeb5bcb82be


Databricks Photon Spark engine
https://blog.det.life/why-did-databricks-build-the-photon-engine-90546429a31c
