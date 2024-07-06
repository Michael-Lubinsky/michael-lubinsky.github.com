### Spark performance

https://www.youtube.com/watch?v=O4MlLUYkjN8


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


#### Config

spark.executor.memory  
spark.executor.cores    


### Caching

Caching can improve performance when the same data is accessed multiple times.

```
• Choose the right storage level: Use appropriate storage levels (e.g., MEMORY_ONLY, MEMORY_AND_DISK) based on your application’s needs.

# Example of caching a DataFrame
df = spark.read.csv(“data.csv”)
df.cache()
```


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

### Links
https://medium.com/towards-data-engineering/the-most-discussed-spark-questions-in-2024-8aeb5bcb82be

Partitioning: https://medium.com/@ashwin_kumar_/spark-partitioning-partition-understanding-2c1705c3b0a0

Databricks Photon Spark engine
https://blog.det.life/why-did-databricks-build-the-photon-engine-90546429a31c
