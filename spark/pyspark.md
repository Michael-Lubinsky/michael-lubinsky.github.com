## Example
```
Input: dataset containing user transactions,
Goal: is to calculate the YoY growth rate for total product spend. 
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
