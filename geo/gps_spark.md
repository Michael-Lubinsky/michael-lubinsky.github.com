
| Type          | Range            | Description                            |
| ------------- | ---------------- | -------------------------------------- |
| **Latitude**  | `-90` to `+90`   | Measures north/south from Equator      |
| **Longitude** | `-180` to `+180` | Measures east/west from Prime Meridian |

Latitude = 0 → on the Equator  
Longitude = 0 → on the Prime Meridian (passes through Greenwich, UK)  

What is the latitude and longitude of the North Pole and South Pole?

| Pole      | Latitude | Longitude               |
| --------- | -------- | ----------------------- |
| **North** | +90      | Any value (0 is common) |
| **South** | -90      | Any value (0 is common) |

Longitude is undefined at the poles because all lines converge — but (0, 90) and (0, -90) are conventional.

What is the lat/lon of points on the Equator?  
Latitude = 0  
Longitude: anywhere from -180 to +180  


#### Where is point (0, 0) on Earth?
(lat, lon) = (0, 0) is called the Null Island.  
It lies in the Gulf of Guinea, off the coast of West Africa, where the Equator meets the Prime Meridian.  
There’s no actual island — it’s an imaginary point in the Atlantic Ocean.  

### GeoJSON 
 GeoJSON  is a widely-used format for encoding geographic data structures using JSON. 
It’s supported by many tools like Mapbox, Leaflet, PostGIS, and others.

####  Common GeoJSON Types:
"Point": A single GPS coordinate
"LineString": A path (sequence of points)
"Polygon": A region enclosed by lines
"Feature": A geometry + properties (like a labeled point)
"FeatureCollection": A list of features

####  A single GPS point
```json
{
  "type": "Point",
  "coordinates": [-122.4194, 37.7749]  // [longitude, latitude]
}
```

#### LineString path
```json
{
  "type": "LineString",
  "coordinates": [
    [-122.4194, 37.7749],
    [-122.4294, 37.8049]
  ]
}
```


### GPS Data Processing with PySpark
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

|user_id |total_distance_km|
|--------|-----------------|
|u1      |5.93             |
|u2      |2.50             |


###  Real-Time GPS Data Processing with PySpark Streaming
Input:
```json
{"user_id": "u1", "timestamp": "2024-01-01T08:00:00", "latitude": 37.7749, "longitude": -122.4194}
```
#### Stream Pipeline Steps
1. Read JSON records from socket or Kafka
2. Parse and clean data
3. Use stateful processing with watermarking (because of lag)
4. Calculate distance and speed
5. Filter noisy data
6. Aggregate per user

Code: PySpark Structured Streaming (Socket Source)
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, unix_timestamp, lag, radians, sin, cos, sqrt, atan2, window
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType
from pyspark.sql.window import Window

# Start session
spark = SparkSession.builder.appName("GPSStreaming").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Define input schema
schema = StructType() \
    .add("user_id", StringType()) \
    .add("timestamp", TimestampType()) \
    .add("latitude", DoubleType()) \
    .add("longitude", DoubleType())

# Read from socket (use 'nc -lk 9999' to simulate)
raw_stream = spark.readStream.format("socket") \
    .option("host", "localhost").option("port", 9999).load()

# Parse JSON lines
gps_df = raw_stream.select(from_json(col("value"), schema).alias("data")).select("data.*")

# Use watermark to manage late data
gps_df = gps_df.withWatermark("timestamp", "10 minutes")

# Add lagged values
window_spec = Window.partitionBy("user_id").orderBy("timestamp")

from pyspark.sql.functions import expr

# Add previous lat/lon/time
from pyspark.sql.functions import to_timestamp

gps_df = gps_df \
    .withColumn("prev_lat", lag("latitude").over(window_spec)) \
    .withColumn("prev_lon", lag("longitude").over(window_spec)) \
    .withColumn("prev_time", lag("timestamp").over(window_spec)) \
    .withColumn("time_diff_hr", (unix_timestamp("timestamp") - unix_timestamp("prev_time")) / 3600.0)

# Haversine distance
R = 6371  # Earth radius in km
gps_df = gps_df.withColumn("dlat", radians(col("latitude") - col("prev_lat"))) \
    .withColumn("dlon", radians(col("longitude") - col("prev_lon"))) \
    .withColumn("a", sin(col("dlat") / 2)**2 + 
                     cos(radians(col("prev_lat"))) * cos(radians(col("latitude"))) *
                     sin(col("dlon") / 2)**2) \
    .withColumn("c", 2 * atan2(sqrt(col("a")), sqrt(1 - col("a")))) \
    .withColumn("distance_km", R * col("c"))

# Compute speed
gps_df = gps_df.withColumn("speed_kph", col("distance_km") / col("time_diff_hr"))

# Filter noisy data
filtered_df = gps_df.filter(
    (col("time_diff_hr") > 0) &
    (col("distance_km") >= 0.05) &
    (col("speed_kph") >= 1) & (col("speed_kph") <= 200)
)

# Aggregate over sliding window or by user
agg_df = filtered_df.groupBy("user_id").sum("distance_km") \
    .withColumnRenamed("sum(distance_km)", "total_distance_km")

# Output to console
query = agg_df.writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", False) \
    .start()

query.awaitTermination()
```

Simulate Data Input via Terminal:
nc -lk 9999
Paste JSON lines:
```
{"user_id":"u1","timestamp":"2024-01-01T08:00:00","latitude":37.7749,"longitude":-122.4194}
{"user_id":"u1","timestamp":"2024-01-01T08:10:00","latitude":37.8049,"longitude":-122.4294}
```

For production, replace .format("socket") with .format("kafka").  
You can write agg_df to Kafka, Delta Lake, PostgreSQL, or GCS.  
Consider using mapWithState or flatMapGroupsWithState for full control over session-based tracking.


### Kafka Example:
```
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, lag, radians, sin, cos, sqrt, atan2, unix_timestamp, to_json, struct
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType
from pyspark.sql.window import Window

# Start Spark session
spark = SparkSession.builder \
    .appName("GPS Kafka Streaming") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Define schema
schema = StructType() \
    .add("user_id", StringType()) \
    .add("timestamp", TimestampType()) \
    .add("latitude", DoubleType()) \
    .add("longitude", DoubleType())

# Read GPS data from Kafka topic
gps_kafka_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "gps_input") \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON value
gps_df = gps_kafka_raw.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*") \
    .withWatermark("timestamp", "10 minutes")

# Create window spec
window_spec = Window.partitionBy("user_id").orderBy("timestamp")

# Add lagged values
gps_df = gps_df \
    .withColumn("prev_lat", lag("latitude").over(window_spec)) \
    .withColumn("prev_lon", lag("longitude").over(window_spec)) \
    .withColumn("prev_time", lag("timestamp").over(window_spec)) \
    .withColumn("time_diff_hr", (unix_timestamp("timestamp") - unix_timestamp("prev_time")) / 3600.0)

# Compute Haversine distance
R = 6371.0  # Earth radius in km
gps_df = gps_df \
    .withColumn("dlat", radians(col("latitude") - col("prev_lat"))) \
    .withColumn("dlon", radians(col("longitude") - col("prev_lon"))) \
    .withColumn("a", sin(col("dlat") / 2)**2 +
                     cos(radians(col("prev_lat"))) * cos(radians(col("latitude"))) *
                     sin(col("dlon") / 2)**2) \
    .withColumn("c", 2 * atan2(sqrt(col("a")), sqrt(1 - col("a")))) \
    .withColumn("distance_km", R * col("c")) \
    .withColumn("speed_kph", col("distance_km") / col("time_diff_hr"))

# Filter out invalid rows
filtered_df = gps_df.filter(
    (col("time_diff_hr") > 0) &
    (col("distance_km") >= 0.05) &
    (col("speed_kph") >= 1) & (col("speed_kph") <= 200)
)

# Aggregate total distance per user
agg_df = filtered_df.groupBy("user_id").sum("distance_km") \
    .withColumnRenamed("sum(distance_km)", "total_distance_km")

# Format result as JSON
output_df = agg_df.selectExpr("user_id", "ROUND(total_distance_km, 3) as total_distance_km") \
    .withColumn("value", to_json(struct("user_id", "total_distance_km"))) \
    .selectExpr("CAST(user_id AS STRING) as key", "CAST(value AS STRING)")

# Write result to Kafka topic
query = output_df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "gps_aggregates") \
    .option("checkpointLocation", "/tmp/gps_kafka_checkpoints") \
    .outputMode("complete") \
    .start()

query.awaitTermination()
```


#### Kafka topics
```bash
# Create input topic
kafka-topics.sh --create --bootstrap-server localhost:9092 --topic gps_input --partitions 1 --replication-factor 1

# Create output topic
kafka-topics.sh --create --bootstrap-server localhost:9092 --topic gps_aggregates --partitions 1 --replication-factor 1

# Send Test Events to gps_input
kafka-console-producer.sh --broker-list localhost:9092 --topic gps_input

```

```json
{"user_id":"u1","timestamp":"2024-01-01T08:00:00","latitude":37.7749,"longitude":-122.4194}
{"user_id":"u1","timestamp":"2024-01-01T08:10:00","latitude":37.8049,"longitude":-122.4294}
```

### Kafka consumer
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic gps_aggregates --from-beginning
```

