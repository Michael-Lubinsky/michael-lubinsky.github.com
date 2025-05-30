
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, radians, sin, cos, sqrt, atan2, unix_timestamp
from pyspark.sql.window import Window

# Initialize Spark session
spark = SparkSession.builder.appName("EnhancedGPSProcessing").getOrCreate()

# Load data
df = spark.read.option("header", True).csv("gps_data.csv")
df = df.withColumn("latitude", col("latitude").cast("double")) \
       .withColumn("longitude", col("longitude").cast("double"))

# Window spec for previous row
window_spec = Window.partitionBy("user_id").orderBy("timestamp")

# Add previous lat/lon and timestamp
df = df.withColumn("prev_lat", lag("latitude").over(window_spec)) \
       .withColumn("prev_lon", lag("longitude").over(window_spec)) \
       .withColumn("prev_ts", lag("timestamp").over(window_spec))

# Time difference in hours
df = df.withColumn("ts", unix_timestamp("timestamp")) \
       .withColumn("prev_ts_unix", unix_timestamp("prev_ts")) \
       .withColumn("time_diff_hr", (col("ts") - col("prev_ts_unix")) / 3600.0)

# Haversine formula
R = 6371  # Earth radius in kilometers

df = df.withColumn("dlat", radians(col("latitude") - col("prev_lat"))) \
       .withColumn("dlon", radians(col("longitude") - col("prev_lon"))) \
       .withColumn("a", sin(col("dlat") / 2)**2 + 
                        cos(radians(col("prev_lat"))) * cos(radians(col("latitude"))) * 
                        sin(col("dlon") / 2)**2) \
       .withColumn("c", 2 * atan2(sqrt(col("a")), sqrt(1 - col("a")))) \
       .withColumn("distance_km", R * col("c"))

# Compute speed (km/h)
df = df.withColumn("speed_kph", col("distance_km") / col("time_diff_hr"))

# Filter out invalid rows:
#  - time_diff_hr > 0
#  - distance >= 0.05 km
#  - speed between 1 and 200 km/h
df_clean = df.filter(
    (col("time_diff_hr") > 0) &
    (col("distance_km") >= 0.05) &
    (col("speed_kph") >= 1) & (col("speed_kph") <= 200)
)

# Total distance per user
result = df_clean.groupBy("user_id").sum("distance_km") \
                 .withColumnRenamed("sum(distance_km)", "total_distance_km")

result.show(truncate=False)
```
Example output
|--------|-----------------|
|user_id |total_distance_km|
|--------|-----------------+
|u1      |5.93             |
|u2      |2.50             |

