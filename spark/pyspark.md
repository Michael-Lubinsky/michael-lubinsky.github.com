```python
df.printSchema()
df.columns
df.count()
df.describe('Name').show()
df.describe('uniform', 'normal').show()
df.filter((df.Club=='FC Barcelona') &
(df.Nationality=='Spain')).orderBy('ID', ascending='False').show(5)
from pyspark.sql.functions import mean, min, max
df.select([mean('uniform'), min('uniform'), max('uniform')]).show()

df.select("name").distinct().show()

from pyspark.sql.functions import countDistinct

df.select(countDistinct("name")).show()
df.select(countDistinct("name", "department")).show()
df.groupBy("department").agg(countDistinct("name").alias("unique_employees")).show()
```

### From SQL to PySpark

```sql
SELECT name, COUNT(*)
FROM T
GROUP BY name
HAVING COUNT(*) > (SELECT AVG(val) FROM T)
```
PySpark doesn’t support subqueries directly in having() like SQL does.
```python
avg_val = df.selectExpr("avg(val) as avg_val").collect()[0]["avg_val"]
from pyspark.sql.functions import count

df_grouped = df.groupBy("name").agg(count("*").alias("cnt"))
df_result = df_grouped.filter(f"cnt > {avg_val}")

or

df_result = df_grouped.filter(df_grouped["cnt"] > avg_val)
```
### Crosstab
```
In PySpark, you can create a cross-tabulation (contingency table) using the crosstab method, which is available directly on a DataFrame or via df.stat. 
Usage
The crosstab method takes two column names as arguments: 
col1: The name of the column for the rows of the resulting table.
col2: The name of the column for the columns of the resulting table. 
The method then computes the frequency of each pair of distinct values from these two columns. The result is a new DataFrame. 
 
Both of the following syntaxes are aliases and produce the same result:
df.crosstab(col1, col2)
df.stat.crosstab(col1, col2)
```

```python


data = [
    ("A", "X"),
    ("A", "Y"),
    ("A", "X"),
    ("B", "X"),
    ("B", "Z"),
    ("C", "Y")
]

df = spark.createDataFrame(data, ["col1", "col2"])
ct = df.crosstab("col1", "col2")
ct.show()
+---------+---+---+---+
|col1_col2| X | Y | Z |
+---------+---+---+---+
|   A     | 2 | 1 | 0 |
|   B     | 1 | 0 | 1 |
|   C     | 0 | 1 | 0 |
+---------+---+---+---+

ct.printSchema()
root
 |-- col1_col2: string
 |-- X: long
 |-- Y: long
 |-- Z: long

```
##  Avoid duplicates during insert

### Implementation 1: DELETE Existing Records Before INSERT

This approach first deletes any rows in the destination table that have matching `event_id` values from the staging DataFrame, then inserts the new rows. This ensures no duplicates by replacing any conflicting rows. Note that this requires the destination table to support ACID operations (e.g., a Delta Lake table).

```python
df.createOrReplaceTempView("staging")

# Delete existing records with matching event_ids
spark.sql(f"""
    DELETE FROM {FULL_TABLE}
    WHERE event_id IN (SELECT event_id FROM staging)
""")

# Insert the new records
spark.sql(f"""
    INSERT INTO {FULL_TABLE}
    SELECT * FROM staging
""")
```

### Implementation 2: Use SQL MERGE Command

This approach uses the `MERGE` statement to perform an upsert: if a row with the same `event_id` exists, it updates (replaces) it with the new values; otherwise, it inserts the new row. This is more efficient than delete-then-insert for large datasets and also requires the destination table to support ACID operations (e.g., Delta Lake).

```python
df.createOrReplaceTempView("staging")

spark.sql(f"""
    MERGE INTO {FULL_TABLE} dest
    USING staging src
    ON dest.event_id = src.event_id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
""")
```
 
If the incoming `df` (staging DataFrame) itself contains **duplicate `event_id` values**, both previous approaches can cause issues:

- **Problem**  
- **DELETE + INSERT**: Deletes the row once, but inserts multiple duplicates → you end up with duplicates.  
- **MERGE**: Behavior is undefined or throws an error in Delta Lake if multiple source rows match the same target row (unless you use the newer `WHEN MATCHED ... THEN UPDATE` with `MERGE` enhancements in Delta 2.0+).

### Recommended robust solution (works in all cases)

```python
from pyspark.sql import functions as F

# 1. Remove duplicates in staging: keep the latest record per event_id
#    (adjust logic if you have a timestamp or ingestion order)
deduped_df = (
    df
    .withColumn("row_num", F.row_number().over(
        Window.partitionBy("event_id").orderBy(
            F.desc("_ingestion_timestamp")  # use your actual event timestamp or metadata column
            # Alternatives if no timestamp:
            # F.desc("_metadata.file_modification_time")  # for file-based sources
            # or just F.monotonically_increasing_id() as last resort
        )
    ))
    .filter("row_num = 1")
    .drop("row_num")
)

# Register clean staging view
deduped_df.createOrReplaceTempView("staging_clean")

# 2. Now safely use the most efficient and correct MERGE
spark.sql(f"""
    MERGE INTO {FULL_TABLE} AS target
    USING staging_clean AS source
    ON target.event_id = source.event_id
    WHEN MATCHED THEN 
        UPDATE SET *
    WHEN NOT MATCHED THEN 
        INSERT *
""")
```

### Alternative versions depending on your needs

#### A. If you don’t have any timestamp but want deterministic choice (e.g., keep first seen)
```python
deduped_df = df.dropDuplicates(["event_id"])
```

#### B. If you are on Delta Lake ≥ 2.0 and want MERGE to handle source duplicates automatically (new feature!)
```python
# No deduplication needed in PySpark
df.createOrReplaceTempView("staging")

spark.sql(f"""
    MERGE INTO {FULL_TABLE} target
    USING staging source
    ON target.event_id = source.event_id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
""")

# Enable the session config to make MERGE tolerant to source duplicates
spark.conf.set("spark.databricks.delta.merge.repartitionBeforeWrite.enabled", "true")
# This makes Delta pick one source row arbitrarily when multiple match
```

#### C. Most bullet-proof version (delete + insert) – still works even on Hive tables
```python
deduped_df = df.dropDuplicates(["event_id"])
deduped_df.createOrReplaceTempView("staging_clean")

spark.sql(f"""
    DELETE FROM {FULL_TABLE}
    WHERE event_id IN (SELECT event_id FROM staging_clean)
""")

spark.sql(f"""
    INSERT INTO {FULL_TABLE}
    SELECT * FROM staging_clean
""")
```

### Summary – Recommended choice in 2025

| Scenario                              | Best approach                                      |
|---------------------------------------|-----------------------------------------------------|
| You are on **Delta Lake** (recommended) | Deduplicate staging + MERGE (cleanest & fastest) |
| You have a reliable event timestamp   | Use `row_number()` over `event_id` + timestamp     |
| No timestamp, just want one row       | `dropDuplicates(["event_id"])` + MERGE             |
| Still on Hive / non-ACID tables       | Deduplicate + DELETE + INSERT                      |

Use the first full example with `row_number()` if you have any timestamp column — it’s the safest and most commonly needed pattern in production.






### read json
```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
# Read single-line JSON
df = spark.read.json("path/to/singleline.json")
df_multiline = spark.read.option("multiLine", True).json("path/to/multiline.json") # Define custom schema for JSON
StructField("id", IntegerType(), True), StructField("name", StringType(), True), StructField("attributes", StructType([
StructField("gender", StringType(), True) ]))
])
df_custom_schema = spark.read.schema(schema).json("path/to/jsonfile.json")
```

<!-- https://mayursurani.medium.com/production-grade-pyspark-scripts-for-aws-data-engineering-bb824399c448 -->

### Read from S3
```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

spark = SparkSession.builder.appName("IngestWithSchema").getOrCreate()

schema = StructType([
    StructField("order_id", StringType(), True),
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("quantity", IntegerType(), True)
])

df = spark.read.schema(schema).json("s3a://ecommerce-bucket/orders/")
df.show(5)
```
### Splat * operator
In PySpark, the * symbol (called the "splat" operator) is Python syntax used to unpack a list (or tuple)
into individual arguments.  
It's not specific to PySpark—it's pure Python—but is commonly seen in PySpark code when you're passing multiple columns dynamically.

 Example: select(*cols)
```python
cols = ["name", "age", "salary"]
df.select(*cols)

#Is equivalent to:

df.select("name", "age", "salary")
```
 So *cols unpacks the list cols into individual column arguments for the select() method.

In PySpark, you can call methods like .groupBy() with either:

a list of columns (no splat *), or

multiple column arguments (using * to unpack a list)

✅ Both are valid — but slightly different in behavior behind the scenes.
🔸 1. With a List (no splat):
 
df.groupBy(['column1', 'column2'])  
You are passing a single list object as an argument to groupBy().  
PySpark internally handles this by flattening the list and using its elements as group keys.


🔸 2. With a Splat (unpacking):
```
columns = ['column1', 'column2']  
df.groupBy(*columns)  
```
Here, *columns unpacks the list into multiple positional arguments, equivalent to:

df.groupBy('column1', 'column2')  
 Also works — and it's more flexible if you're dynamically building the list of columns.


### Data quality check
```python
from pyspark.sql.functions import col

invalid_rows = df.filter(
    col("policy_number").isNull() | (col("premium") <= 0)
)

if invalid_rows.count() > 0:
    invalid_rows.write.mode("overwrite").json("s3a://dq-logs/errors/")
    raise ValueError("Data Quality Issues Found: Null policy numbers or non-positive premium values")
```

### Join

Use "inner", "left", "right", "outer", "left_semi", "left_anti" as the how parameter.

Spark automatically avoids duplicate join columns by keeping just one id column.
```python
df_joined = df1.join(df2, on="id", how="inner")
df_joined = df1.join(df2, on=["id", "dept"], how="inner")
df_joined.show()
```
Join using explicit conditions (df1.id == df2.id)

df_joined = df1.join(df2, df1.id == df2.id, "inner")

It lead to duplicate id columns: one from df1, one from df2.
Solution:  
```python
df_joined = df1.join(df2, df1.id == df2.id, "inner") \
               .drop(df2.id)

df_joined = df1.join(
    df2,
    (df1.emp_id == df2.id) & (df1.department == df2.dept),
    how="inner"
).drop(df2.id, df2.dept)  # optional: remove duplicate columns
```

### left_semi left_anti joins

In PySpark, left_semi and left_anti joins are special join types used to filter data from the left DataFrame based on the existence (or non-existence) of matching rows in the right DataFrame.

They do not return columns from the right DataFrame.

🔹 1. left_semi Join
Returns rows from the left DataFrame that have a match in the right DataFrame.

✅ Think of it as: left_df WHERE EXISTS (SELECT ... FROM right_df WHERE join condition)

🔸 Example:
```python
df1 = spark.createDataFrame([(1, "Alice"), (2, "Bob"), (3, "Charlie")], ["id", "name"])
df2 = spark.createDataFrame([(2,), (3,)], ["id"])

df1.join(df2, on="id", how="left_semi").show()

+---+-------+
| id|  name |
+---+-------+
|  2|   Bob |
|  3|Charlie|
+---+-------+
```
🔹 2. left_anti Join
Returns rows from the left DataFrame that do NOT have a match in the right DataFrame.

✅ Think of it as: left_df WHERE NOT EXISTS (...)

🔸 Example:

df1.join(df2, on="id", how="left_anti").show()

```
+---+-----+
| id| name|
+---+-----+
|  1|Alice|
+---+-----+
```

### Full join
```python
df1.join(df2, on="id", how="full")
df1.join(df2, on="id", how="outer")
df1.join(df2, on="id", how="fullouter")

df1 = spark.createDataFrame([(1, "A"), (2, "B")], ["id", "val1"])
df2 = spark.createDataFrame([(2, "X"), (3, "Y")], ["id", "val2"])

df1.join(df2, on="id", how="fullouter").show()

+----+-----+-----+
| id | val1| val2|
+----+-----+-----+
|  1 |  A  | null|
|  2 |  B  |  X  |
|  3 |null |  Y  |
+----+-----+-----+
```

### Find and drop duplicates

dropDuplicates() in PySpark is used to remove duplicate rows from a DataFrame. 
It can operate on all columns or a subset of columns.

`df.dropDuplicates(subset=None, keep='first')`
```
subset: (Optional) A list of column names to consider when identifying duplicates. If None, all columns are considered.
keep: (Optional) Specifies which duplicate row to keep. It can be 'first' (default), 'last', or False (to drop all duplicates).
```

```python
df \
.groupby(['column1', 'column2']) \
.count() \
.where('count > 1') \
.sort('count', ascending=False) \
.show()

df.dropDuplicates(['id', 'name']).show()

# using Window: 

from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, col

windowSpec = Window.partitionBy("transaction_id").orderBy(col("timestamp").desc())

unique_df = df.withColumn("row_num", row_number().over(windowSpec)) \
             .filter(col("row_num") == 1) \
             .drop("row_num")
```

### sum(column)
```python
data = [("John Doe", "john@example.com", 50000.0),
    ("Jane Smith", "jane@example.com", 60000.0),
    ("Bob Johnson", "bob@example.com", 55000.0)]


schema="Name string,email string,salary double"
df=spark.createDataFrame(data,schema)
display(df)


from pyspark.sql.functions import col,sum
df_final=df.agg(sum(col("salary")).alias("total_salary")).first()[0]
```

### Pivoting in SQL and PySpark

```sql
SELECT
  name,
  SUM(CASE WHEN subject = 'English' THEN score END) AS English,
  SUM(CASE WHEN subject = 'Math' THEN score END) AS Math
FROM your_table
GROUP BY name;
```

In PySpark, pivot() converts rows into columns, but if more than one value exists for a given combination, Spark needs to know how to combine them.

So you must specify an aggregation function like:

sum() → to total values

avg() → to take the average

max(), min(), count(), etc.

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum

spark = SparkSession.builder.getOrCreate()

data = [
    ("Alice", "Math", 85),
    ("Alice", "English", 78),
    ("Bob", "Math", 91),
    ("Bob", "English", 84),
    ("Charlie", "Math", 65),
    ("Charlie", "English", 70)
]

df = spark.createDataFrame(data, ["name", "subject", "score"])
df.show()
+-------+--------+-----+
|  name | subject|score|
+-------+--------+-----+
| Alice |   Math |   85|
| Alice | English|   78|
| Bob   |   Math |   91|
| Bob   | English|   84|
|Charlie|   Math |   65|
|Charlie| English|   70|
+-------+--------+-----+
df_pivot = df.groupBy("name").pivot("subject").agg(sum("score"))
df_pivot.show()

+-------+--------+-----+
|  name | English| Math|
+-------+--------+-----+
| Alice |     78 |   85|
| Bob   |     84 |   91|
|Charlie|     70 |   65|
+-------+--------+-----+
```


###  Flatten Any JSON in PySpark
<https://nidhig631.medium.com/how-to-effortlessly-flatten-any-json-in-pyspark-no-more-nested-headaches-60a30bd36bb1>

Recursively flattens a DataFrame with complex nested fields (Arrays and Structs)   
by converting them into individual columns.
```python
from pyspark.sql.functions import col, explode_outer
from pyspark.sql.types import StructType, ArrayType

def flatten_json(df):

    def get_complex_fields(df):
        # Returns a dictionary of complex (Array or Struct) fields in the DataFrame schema.
        return {field.name: field.dataType for field in df.schema.fields if isinstance(field.dataType, (ArrayType, StructType))}

    #Retrieves all Structs & Arrays in the DataFrame.
    #If no complex fields exist, the function simply returns the original DataFrame.
    complex_fields = get_complex_fields(df) 

    while complex_fields:
        col_name, col_type = next(iter(complex_fields.items()))  # Get first complex column
        print(f"Processing: {col_name}, Type: {type(col_type)}")

        if isinstance(col_type, StructType):
            # Expand Struct fields into separate columns
            expanded_cols = [col(f"{col_name}.{sub_field.name}").alias(f"{col_name}_{sub_field.name}") 
                             for sub_field in col_type]
            df = df.select("*", *expanded_cols).drop(col_name)

        elif isinstance(col_type, ArrayType):
            # Explode Array fields into separate rows
            df = df.withColumn(col_name, explode_outer(col_name))

        # Recompute remaining complex fields
        complex_fields = get_complex_fields(df)

    return df
    ```

### Calculate the monthly average balance for banking customers.
```python
from pyspark.sql.functions import avg, month
from pyspark.sql.window import Window

windowSpec = Window.partitionBy("customer_id", month("date"))

df = df.withColumn("monthly_avg_balance", avg("balance").over(windowSpec))
```

### collect_list, collect_set
```python
data=[(1,'Watson',34),(1,'Watson',40),(1,'Watson',34),(2,'Alex',45),(2,'Alex',50)]
schema="ID int,Name string,Marks int"
df=spark.createDataFrame(data,schema)
display(df)

from pyspark.sql.functions import collect_list,collect_set,col

df_final=df.groupBy(col("ID"),col("Name")).agg(collect_list(col('Marks')))
display(df_final)
```

### UDTF

https://habr.com/ru/companies/otus/articles/942148/
```python
from pyspark.sql.functions import udtf
from pyspark.sql.types import Row

@udtf(returnType="id: int")
class FilterUDTF:
    def eval(self, row: Row):
        # Если значение столбца "id" больше 5, возвращаем эту строку
        if row["id"] > 5:
            yield (row["id"],)

```
```sql
SELECT * FROM filter_udtf(
    TABLE(SELECT * FROM range(10) AS t(id))
);
```

### Explicit broadcast to avoid shuffle joins
```python
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", -1)

optimized_df = large_df.join(
    small_df.hint("broadcast"), on="product_id", how="inner"
)
```

### Write to Partitioned Parquet with Overwrite Mode
```python
output_path = "s3a://reports-bucket/daily/"

report_df.write.partitionBy("region", "report_date") \
    .mode("overwrite") \
    .parquet(output_path)
```
### Partitioning + Bucketing in PySpark 
```python
orders_df.write \
 .partitionBy("year") \
 .bucketBy(4, "customer_id") \
 .sortBy("customer_id") \
 .saveAsTable("orders_partitioned_bucketed") 

Here:
.partitionBy("year") → Create a folder for each year
.bucketBy(4, "customer_id") → Create 4 groups inside each partition
.sortBy("customer_id") → Optional: Helps optimize even further!
```
### rlike - regulal expression 
```python
from pyspark.sql.types import *
schema = StructType([
  StructField("ProductCode", StringType(), True),
  StructField("Quantity", StringType(), True),
  StructField("UnitPrice", StringType(), True),
  StructField("CustomerID", StringType(), True),
])
 

data = [
  ("Q001", 5, 20.0, "C001"),
  ("Q002", 3, 15.5, "C002"),
  ("Q003", 10, 5.99, "C003"),
  ("Q004", 2, 50.0, "C001"),
  ("Q005", "nein", 12.75, "C002"),
]
 
df = spark.createDataFrame(data, schema=schema)
df.show()

from pyspark.sql.functions import col
df_final=df.filter(col("Quantity").rlike('^[a-zA-Z]*$'))
df_final.show()
```

### explode, explode_outer

explode_outer() - preserves rows where the input column is null or an empty array.

Produces a row with null as the result for null or [].

```python
data=[('Paris','Polo, Tennis'),('Matt','Golf, Hockey'),('Sam',None)]
schema="Person string,Games string"
df=spark.createDataFrame(data,schema)
display(df)

from pyspark.sql.functions import col,explode,explode_outer, split
df_final=df.withColumn("Games",split(col("Games"),','))
display(df_final)
df_final.select("Person",explode(col("Games")).alias("Games")).display()
```


### year, start_week_date, end_week_date, week_num
```python
from pyspark.sql.types import *
data=[(2025,1,'2025-01-01'),
      (2025,1,'2025-01-02'),
      (2025,1,'2025-01-03'),
      (2025,1,'2025-01-04'),
      (2025,1,'2025-01-05'),
      (2025,1,'2025-01-06'),
      (2025,1,'2025-01-07'),
      (2025,2,'2025-01-08'),
      (2025,2,'2025-01-09'),
      (2025,2,'2025-01-10'),
      (2025,2,'2025-01-11'),
      (2025,2,'2025-01-12'),
      (2025,2,'2025-01-13'),
      (2025,2,'2025-01-14')]

schema=StructType([
  StructField('year',IntegerType(),True),
  StructField('week_num',IntegerType(),True),
  StructField('dates',StringType(),True)])

df=spark.createDataFrame(data,schema)
df.display()

from pyspark.sql.functions import col,min,max,to_date
df=df.withColumn("dates",to_date(col("dates")))
df.groupBy(col("year"),col("week_num")).agg(min(col("dates")).alias("start_day_week"),
   max(col("dates")).alias("end_day_week")).display()
```
### Slow changing dimentions type 2 
```
from pyspark.sql.functions import lit, current_date

source_df = source_df.withColumn("start_date", current_date())
source_df = source_df.withColumn("end_date", lit(None).cast("date"))

# Assume `customer_id` is the business key
changes_df = source_df.join(target_df, ["customer_id"], "left_anti")

final_df = target_df.unionByName(changes_df)
```

### ROWS BETWEEN and RANGE BETWEEN

In PySpark, the equivalents of SQL's ROWS BETWEEN and RANGE BETWEEN are handled using the Window specification API, specifically with:

rowsBetween(...) → equivalent of SQL's ROWS BETWEEN

rangeBetween(...) → equivalent of SQL's RANGE BETWEEN

✅ 1. PySpark Equivalent of ROWS BETWEEN

```sql

SUM(salary) OVER (
  ORDER BY salary
  ROWS BETWEEN 2 PRECEDING AND 1 FOLLOWING
)
```


```python

from pyspark.sql.window import Window
from pyspark.sql.functions import sum

window_spec = Window.orderBy("salary").rowsBetween(-2, 1)

df.withColumn("running_sum", sum("salary").over(window_spec))
```
✅ 2. PySpark Equivalent of RANGE BETWEEN
rangeBetween is value-based, not row-position-based (like rowsBetween)


```sql

SUM(salary) OVER (
  ORDER BY salary
  RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```
 
```python
window_spec = Window.orderBy("salary").rangeBetween(Window.unboundedPreceding, Window.currentRow)

df.withColumn("cumulative_sum", sum("salary").over(window_spec))
```

| Feature             | `rowsBetween`                   | `rangeBetween`                     |
| ------------------- | ------------------------------- | ---------------------------------- |
| Based on            | Row **position**                | Row **values** in `ORDER BY`       |
| Includes duplicates | No special treatment            | Includes all rows with equal value |
| Most common usage   | Running totals, sliding windows | Cumulative values by key           |


### Logging and Exception Handling in PySpark Jobs
```python
import logging

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger("DataPipelineLogger")

try:
    df = spark.read.parquet("s3a://input-bucket/data/")
    logger.info("Data ingestion successful")
except Exception as e:
    logger.error(f"Error occurred: {e}")
    raise
```

### Example

Given: dataset containing Twitter tweets.  
Goal: create a histogram of tweets posted per user in 2022. 

The output should show:  

- The number of tweets per user (tweet count per user = bucket)  
- The number of users in each bucket

SQL solution:
```sql
WITH CTE AS (
    SELECT USER_ID, COUNT(TWEET_ID) AS tweet_count_per_user
    FROM tweets
    WHERE EXTRACT(YEAR FROM TWEET_DATE) = 2022
    GROUP BY USER_ID
)

SELECT tweet_count_per_user AS tweet_bucket, COUNT(USER_ID) AS users_num
FROM CTE 
GROUP BY tweet_count_per_user
ORDER BY tweet_count_per_user;

+-------------------+-------------+
|tweet_count_per_user | users_num |
+-------------------+-------------+
|                 1 |           3 |
|                 2 |           1 |
|                 3 |           1 |
+-------------------+-------------+
```

PySpark solution:
```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, TimestampType
from datetime import datetime

spark = SparkSession.builder.appName("TwitterAnalysis").getOrCreate()

schema = StructType([
    StructField("tweet_id", IntegerType(), True),
    StructField("user_id", IntegerType(), True),
    StructField("msg", StringType(), True),
    StructField("tweet_date", TimestampType(), True)
])

data = [
    (214252, 111, "Am considering taking Tesla private at $420. Funding secured.", datetime(2021, 12, 30, 0, 0, 0)),
    (739252, 111, "Despite the constant negative press covfefe", datetime(2022, 1, 1, 0, 0, 0)),
    (846402, 111, "Following @NickSinghTech on Twitter changed my life!", datetime(2022, 2, 14, 0, 0, 0)),
    (241425, 254, "If the salary is so competitive why won’t you tell me what it is?", datetime(2022, 3, 1, 0, 0, 0)),
    (231574, 148, "I no longer have a manager. I can't be managed", datetime(2022, 3, 23, 0, 0, 0)),
    (987654, 333, "Data Science is amazing!", datetime(2022, 5, 10, 0, 0, 0)),
    (876543, 333, "SQL is an essential skill for Data Engineers.", datetime(2022, 6, 15, 0, 0, 0)),
    (765432, 333, "Mastering PySpark for big data processing.", datetime(2022, 7, 20, 0, 0, 0)),
    (654321, 444, "Love writing SQL queries!", datetime(2022, 8, 25, 0, 0, 0)),
    (543210, 555, "Machine Learning is the future!", datetime(2022, 9, 30, 0, 0, 0))
]

tweets_df = spark.createDataFrame(data, schema=schema)

tweets_2022 = (tweets_df
    .filter(year(col("tweet_date")) == 2022)
    .groupBy("user_id")
    .agg(count("tweet_id").alias("tweet_count_per_user"))
)

# Count users in each tweet bucket
histogram_df = (tweets_2022
    .groupBy("tweet_count_per_user")
    .agg(count("user_id").alias("users_num"))
    .orderBy("tweet_count_per_user")
)

# Show result
histogram_df.show()
```

### Example

For each FAANG stock, we need to:

- Find the highest opening price and its corresponding month-year (Mon-YYYY).  
- Find the lowest opening price and its corresponding month-year.  
- Sort the results by ticker symbol.

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_format, rank
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("FAANG Stock Analysis").getOrCreate()

# Sample dataset with 3-4 records per unique ticker
data = [
    ("2023-01-31", "AAPL", 142.28, 144.34, 142.70, 144.29),
    ("2023-02-28", "AAPL", 146.83, 149.08, 147.05, 147.41),
    ("2023-03-31", "AAPL", 161.91, 165.00, 162.44, 164.90),
    ("2023-04-30", "AAPL", 167.88, 169.85, 168.49, 169.68),
    ("2023-01-31", "AMZN", 98.32, 101.26, 98.90, 100.55),
    ("2023-02-28", "AMZN", 102.50, 105.62, 103.12, 104.45),
    ("2023-03-31", "AMZN", 109.12, 112.50, 110.32, 111.85),
    ("2023-01-31", "NFLX", 320.45, 325.50, 321.90, 324.60),
    ("2023-02-28", "NFLX", 328.20, 332.45, 329.10, 331.25),
    ("2023-03-31", "NFLX", 335.90, 340.80, 337.40, 339.75),
    ("2023-01-31", "GOOGL", 88.56, 91.22, 89.34, 90.75),
    ("2023-02-28", "GOOGL", 92.78, 95.43, 93.45, 94.80),
    ("2023-03-31", "GOOGL", 97.34, 100.12, 98.23, 99.75)
]

columns = ["date", "ticker", "open", "high", "low", "close"]
stock_prices = spark.createDataFrame(data, columns)

# Convert date column to timestamp
stock_prices = stock_prices.withColumn("date", col("date").cast("timestamp"))

# Extract month-year column
stock_prices = stock_prices.withColumn("month_year", date_format(col("date"), "MMM-yyyy"))

# Define window partitioned by ticker and ordered by open price
window_high = Window.partitionBy("ticker").orderBy(col("open").desc())
window_low = Window.partitionBy("ticker").orderBy(col("open"))

# Rank highest and lowest open prices
stock_ranked = stock_prices \
    .withColumn("rank_high", rank().over(window_high)) \
    .withColumn("rank_low", rank().over(window_low))

# Get highest and lowest open price records
highest_open_df = stock_ranked.filter(col("rank_high") == 1).select("ticker", "month_year", col("open").alias("highest_open"))
lowest_open_df = stock_ranked.filter(col("rank_low") == 1).select("ticker", "month_year", col("open").alias("lowest_open"))

# Rename columns for joining
highest_open_df = highest_open_df.withColumnRenamed("month_year", "highest_mth")
lowest_open_df = lowest_open_df.withColumnRenamed("month_year", "lowest_mth")

# Join both DataFrames on ticker
result_df = highest_open_df.join(lowest_open_df, "ticker").orderBy("ticker")

result_df.show()

+------+-----------+------------+-----------+------------+
|ticker|highest_mth|highest_open|lowest_mth|lowest_open  |
+------+-----------+------------+-----------+------------+
| AAPL | Apr-2023  | 167.88     | Jan-2023  | 142.28     |
| AMZN | Mar-2023  | 109.12     | Jan-2023  | 98.32      |
| GOOGL| Mar-2023  | 97.34      | Jan-2023  | 88.56      |
| NFLX | Mar-2023  | 335.90     | Jan-2023  | 320.45     |
+------+-----------+------------+-----------+------------+
```  


### Example
```
Input: dataset containing user transactions,
Goal: to calculate the YoY growth rate for total product spend. 
The output should include:

- Year (sorted in ascending order)
- Product ID
- Current year’s total spend
- Previous year’s total spend
- Year-on-Year (YoY) growth percentage (rounded to 2 decimal places)
```  

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import year, sum, lag, round
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("YoY_Growth_Calculation").getOrCreate()

data = [
    (1341, 123424, 1500.60, "2019-12-31 12:00:00"),
    (1423, 123424, 1000.20, "2020-12-31 12:00:00"),
    (1623, 123424, 1246.44, "2021-12-31 12:00:00"),
    (1322, 123424, 2145.32, "2022-12-31 12:00:00"),
    (1456, 567890, 800.50, "2018-12-31 12:00:00"),
    (1534, 567890, 950.75, "2019-12-31 12:00:00"),
    (1678, 567890, 1100.90, "2020-12-31 12:00:00"),
    (1789, 567890, 1205.40, "2021-12-31 12:00:00"),
    (1890, 567890, 1400.65, "2022-12-31 12:00:00"),
    (1991, 567890, 1600.80, "2023-12-31 12:00:00")
]

from pyspark.sql.types import StructType, StructField, IntegerType, DecimalType, TimestampType

schema = StructType([
    StructField("transaction_id", IntegerType(), True),
    StructField("product_id", IntegerType(), True),
    StructField("spend", DecimalType(10,2), True),
    StructField("transaction_date", TimestampType(), True)
])

df = spark.createDataFrame(data, schema=schema)

# Extract Year from transaction_date
df = df.withColumn("year", year(df["transaction_date"]))

# Aggregate Spend per Year and Product
df_grouped = df.groupBy("year", "product_id").agg(sum("spend").alias("curr_year_spend"))

# Define Window Specification for Lag Function
window_spec = Window.partitionBy("product_id").orderBy("year")

# Compute Previous Year Spend using LAG
df_final = df_grouped.withColumn("prev_year_spend", lag("curr_year_spend").over(window_spec))

# Calculate Year-on-Year Growth Rate
df_final = df_final.withColumn(
    "yoy_rate",
    round(((df_final.curr_year_spend - df_final.prev_year_spend) / df_final.prev_year_spend) * 100, 2)
)

df_final.orderBy("product_id", "year").show()
```

### .createOrReplaceTempView() retired
Still using .createOrReplaceTempView() just to run SQL on your DataFrames?
Cleaner, safer, and more modular approach in PySpark and Fabric Notebooks. 🧼⚙️

💡 𝐐𝐮𝐢𝐜𝐤 𝐁𝐫𝐞𝐚𝐤𝐝𝐨𝐰𝐧:
🔹 𝟏. 𝐓𝐡𝐞 𝐎𝐥𝐝 𝐖𝐚𝐲 (❌ Temp Views)
```sql
df_customers.createOrReplaceTempView("customers_view")
spark.sql("SELECT * FROM customers_view")
```
⚠️ Pollutes session with global views
 ⚠️ Easy to overwrite accidentally
 ⚠️ Not notebook-friendly

🔹 𝟐. 𝐓𝐡𝐞 𝐁𝐞𝐭𝐭𝐞𝐫 𝐖𝐚𝐲 (✅ SQL Variable Binding)
```sql
spark.sql(
 "SELECT * FROM {customers}",
 customers=df_customers
)
```
 ✅ No need to register views
 ✅ Keeps code modular & testable
 ✅ Direct reference to DataFrames in SQL


```python
parametrized_query = """SELECT * FROM {item_price}
WHERE transaction_date > {transaction_date}
"""

spark.sql(
    parametrized_query, item_price=item_price, transaction_date=transaction_date_str
).show()


query_with_markers = """SELECT * FROM {item_price}
WHERE transaction_date > :transaction_date
"""

transaction_date = date(2025, 2, 15)

spark.sql(
    query_with_markers,
    item_price=item_price,
    args={"transaction_date": transaction_date},
).show()


def filter_by_price_threshold(df, amount):
    return spark.sql(
        "SELECT * from {df} where price > :amount", df=df, args={"amount": amount}
    )

#Execute query with parameters
assert filter_by_price_threshold(df, 10).count() == 1
assert filter_by_price_threshold(df, 8).count() == 2
```


`element_at()` is a **built-in PySpark SQL function** used to safely access elements inside:

* **Maps** (`MapType`)
* **Arrays** (`ArrayType`)

It pairs extremely well with SQL **`try(...)`** because together they allow **safe lookups** without throwing runtime errors.

Below is the full explanation with examples.

---

# ✅ 1. What `element_at()` does

## **For MAPS**

Extracts the value for a given key:

```python
from pyspark.sql import functions as F

df.withColumn("v", F.element_at(F.col("my_map"), F.lit("key1")))
```

Equivalent to:

```
my_map["key1"]
```

If the key does *not* exist:

* Spark **returns NULL**
* No exception is thrown

---

## **For ARRAYS**

Extracts an element by **1-based index**:

```python
F.element_at(F.col("arr"), 1)  # arr[0]
F.element_at(F.col("arr"), 2)  # arr[1]
```

If index is out of range:

* Spark returns **NULL**
* No exception (unlike Python `IndexError`)

---

# 🔥 2. How `element_at()` works together with `try(...)`

`try()` is a Spark SQL expression that **catches errors** and returns NULL instead of failing the query.

So combining them:

```python
F.expr("try(element_at(my_map, 'missing_key'))")
```

This gives you three levels of safety:

* No exception if the **map key doesn't exist**
* No exception if **my_map is NULL**
* No exception if **my_map is not even a map** (e.g. malformed data)

---

# 🟢 3. Practical examples

## ✅ **3.1 Safe lookup inside map column**

```python
df = df.withColumn(
    "location",
    F.expr("try(element_at(signals_map, 'location'))")
)
```

If:

* `signals_map` is NULL → result NULL
* Key `"location"` doesn’t exist → result NULL
* The column isn't even a map → NULL instead of error
* JSON corrupted → NULL instead of job failure

---

## ✅ **3.2 Safe extraction from deeply nested JSON**

Consider JSON:

```json
{
  "signals": [
    {"code": "internalcombustionengine-amountremaining", "body": {"value": 49.41}}
  ]
}
```

You want `"body.value"` only when `code` matches.

Common pattern:

```python
df = df.withColumn(
    "fuel_value",
    F.expr("""
      try(
          element_at(
              filter(signals, x -> x.code = 'internalcombustionengine-amountremaining'),
              1
          ).body.value
      )
    """)
)
```

Without `try(...)`, this can throw errors if:

* `signals` is NULL
* Filter result is empty
* `body` is missing
* Fields are malformed

With `try`, errors turn into **NULL**, pipeline continues.

---

## ✅ **3.3 Safe array element lookup**

```python
df = df.withColumn(
    "first_value",
    F.expr("try(element_at(values_array, 1))")
)
```

Indexes outside range → NULL.
Array is NULL → NULL.
Array is wrong type → NULL.

---

# 🎯 Why use `element_at()` instead of direct dot-access?

Compare these:

### ❌ dot-access (unsafe)

```python
df["signals"][0]["body"]["value"]
```

This will break if:

* array empty
* `body` missing
* type mismatch
* wrong index

### ✔ With element_at and try

```python
F.expr("try(element_at(signals, 1).body.value)")
```

This **never throws**, always returns NULL on failure.

---

# ⭐ Summary

| Function       | Purpose                     | Behavior on missing key/value |
| -------------- | --------------------------- | ----------------------------- |
| `element_at()` | Safe lookup in MAP or ARRAY | Returns **NULL**, no error    |
| `try(...)`     | Exception guard             | Converts errors → **NULL**    |

Together they give you **robust, production-grade JSON and nested-structure handling**, especially critical when ingesting messy IoT/telemetry data.

---

If you want, I can give you:

* The best **pattern** to safely extract `signals.body.value`
* A reusable function to parse ANY nested JSON safely
* A complete set of examples for arrays/maps and try() combos

 ## try

* DataFrame expressions run **on the Spark cluster**, not in the Python driver
* Python exceptions do not propagate into the distributed execution engine

Instead, PySpark provides **SQL-style try/catch equivalents inside expressions**, such as:

* `try_cast()`
* `element_at()` default behavior
* `F.when(...).otherwise(...)`
* `F.coalesce()`
* `F.try_add()`, `F.try_divide()`, `F.try_multiply()`, etc. (Spark 3.4+)
* `F.expr("try(...)")` for SQL `try(...)` blocks

Below are real examples you can use.

---

## ✔ 1. Using `try_cast()` (recommended)

```python
from pyspark.sql import functions as F

df = df.withColumn(
    "value_int",
    F.try_cast(F.col("value"), "int")
)
```

**If cast fails**, result becomes **NULL** instead of throwing an error.
This is the closest to a “try/catch” in PySpark expressions.

---

## ✔ 2. Using `when / otherwise` (safe fallback)

```python
from pyspark.sql import functions as F

df = df.withColumn(
    "safe_int",
    F.when(F.col("value").rlike("^[0-9]+$"), F.col("value").cast("int"))
     .otherwise(F.lit(None))
)
```

Equivalent to:

```
try:
   int(value)
except:
   None
```

---

## ✔ 3. Using SQL `try(...)` expression via F.expr()

Spark SQL has a `try()` function that catches runtime errors.

```python
df = df.withColumn(
    "safe_divide",
    F.expr("try( 100 / value )")
)
```

If `value = 0` → result = NULL instead of exception.

---

## ✔ 4. Using PySpark *try_* functions (Spark 3.4+)

```python
df = df.withColumn(
    "safe_divide",
    F.try_divide(F.lit(100), F.col("value"))
)
```

This is exactly like:

```
try:
    result = 100 / value
except:
    result = null
```

Available functions include:

* `try_add`
* `try_subtract`
* `try_multiply`
* `try_divide`
* `try_sum`
* `try_avg`
* `try_cast`

---

## ✔ 5. Example of full safe parsing expression

```python
from pyspark.sql import functions as F

df = df.withColumn(
    "parsed_date",
    F.to_date(
        F.expr("try(to_timestamp(raw_date, 'yyyy-MM-dd'))")
    )
)
```

If parsing fails → `parsed_date = NULL`.

 


https://mayursurani.medium.com/comprehensive-guide-to-building-an-enterprise-etl-pipeline-with-pyspark-and-airflow-e9286bb609a8

  https://mayursurani.medium.com/production-grade-pyspark-scripts-for-aws-data-engineering-bb824399c448 

https://medium.com/@krthiak/pyspark-sql-and-python-hands-on-interview-questions-day-92-of-100-days-of-data-engineering-ai-ef14419c98a6

<https://medium.com/@shubham.shardul2019/chapter-4-pyspark-advanced-aggregations-pivoting-conditional-logic-and-joins-924ef5d7b82a>

https://medium.com/@krthiak/pyspark-sql-and-python-hands-on-interview-questions-day-92-of-100-days-of-data-engineering-ai-ef14419c98a6  
https://medium.com/@krthiak/15-pyspark-interview-questions-day-95-of-100-days-of-data-engineering-ai-and-azure-challenge-93eda757088b  
https://medium.com/@krthiak/pysparks-interview-questions-on-friday-day-80-of-100-days-of-data-engineering-ai-and-azure-a4c920bf8ab0  

https://medium.com/towards-data-engineering/discover-how-spark-functions-like-collect-set-concat-ws-collect-list-explode-and-array-union-e506a63bd571

https://medium.com/towards-data-engineering/cracking-pyspark-json-handling-from-json-to-json-and-interview-ready-insights-6f5bacbce4dd

https://medium.com/@rames1000/50-pyspark-problems-solutions-part-1-c40c19c3416e

https://medium.com/meanlifestudies/pyspark-data-engineer-interview-questions-part-iv-5e091d14b31f

https://medium.com/@rames1000/50-pyspark-problems-solutions-part-2-1dbdbf892e1e
https://medium.com/@rames1000/50-pyspark-problems-solutions-part-3-4b8472b068fb

https://medium.com/@rames1000/pyspark-transformation-solutions-part-1-7a879d5dcec7
https://medium.com/@rames1000/pyspark-transformation-solutions-part-2-200d2bf82398

https://codecut.ai/pyspark-sql-enhancing-reusability-with-parameterized-queries/
 
