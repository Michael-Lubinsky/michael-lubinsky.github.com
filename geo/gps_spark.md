
<https://en.wikipedia.org/wiki/Spatial_reference_system>

<https://en.wikipedia.org/wiki/Geographic_coordinate_system>

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

### GeoPy , Folium
```python
import folium
from geopy.geocoders import Nominatim
from IPython.display import display, HTML
location_name = input("Enter a location: ")
geolocator = Nominatim(user_agent="geoapi")
location = geolocator.geocode(location_name)
if location:
    # Create a map centered on the user's location
    latitude = location.latitude
    longitude = location.longitude
    clcoding = folium.Map(location=[latitude, longitude], zoom_start=12)
    marker = folium.Marker([latitude, longitude], popup=location_name)
    marker.add_to(clcoding)
    display(HTML(clcoding._repr_html_()))
else:
    print("Location not found. Please try again.")



from geopy.geocoders import ArcGIS

# Initialize ArcGIS geocoder
geolocator = ArcGIS()

# Geocode an address using ArcGIS
location = geolocator.geocode("Pune, India")

print("Latitude:", location.latitude)
print("Longitude:", location.longitude)


from geopy.distance import geodesic

# Coordinates of two locations
location1 = (18.521428, 73.8544541)  # Pune
location2 = (19.0785451, 72.878176)  # Mumbai

# Calculate distance between locations
distance = geodesic(location1, location2).kilometers

print("Distance betwen City :", distance, "km")


from geopy.geocoders import Nominatim

# Initialize Nominatim geocoder
geolocator = Nominatim(user_agent="my_geocoder")

# Reverse geocode coordinates
location = geolocator.reverse((26.4219999, 71.0840575))

print("Address:", location.address)
```


### Reverse Geocoding
<https://austinhenley.com/blog/coord2state.html>

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
{
"user_id": "u1",
"timestamp": "2024-01-01T08:00:00",
"latitude": 37.7749,
"longitude": -122.4194
}
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
```python
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


### Apache Spark and Databricks support geospatial data pipelines through a combination of:

✅ 1. Apache Spark – Native + Extended Support
Apache Spark itself has limited native support for geospatial processing. 
However, it becomes powerful when extended with open-source libraries like:

#### GeoSpark (now Apache Sedona)
Apache Sedona is the most popular open-source geospatial extension for Apache Spark.
<https://www.youtube.com/watch?v=V__Lq72ge5A>

Adds native support for spatial types: Point, Polygon, LineString, etc.

Supports spatial joins, indexing (R-Tree, QuadTree), and spatial partitioning.

Works with DataFrames, SQL, and RDDs.

✅ Example:
```python

from sedona.register import SedonaRegistrator
from sedona.sql.types import GeometryType
from pyspark.sql.functions import col

# Register geospatial functions
SedonaRegistrator.registerAll(spark)

df = spark.read.csv("h3_data.csv")
df.createOrReplaceTempView("geodata")

spark.sql("""
SELECT ST_Distance(ST_Point(1.0, 2.0), ST_Point(3.0, 4.0)) AS dist
""").show()
```

Features:
ST_Contains, ST_Intersects, ST_Within, ST_Buffer, ST_Distance, etc.

Read/write WKT, WKB, GeoJSON, Shapefile, Parquet with embedded geometries

Indexing and spatial partitioning for efficient processing

#### Databricks – Enhanced Integration & Built-in Tools
Databricks extends Apache Spark with easier integration for geospatial analytics through:

🔷 a) Built-in Support for Apache Sedona
Databricks Runtime supports Sedona through:

Databricks Labs geospatial libraries

Pre-installed or installable as a library in a cluster

Integration with SQL, Delta Lake, ML, visualizations

🔷 b) Databricks SQL and Delta Lake with Geospatial
Delta Lake can store large geospatial datasets in partitioned form

Compatible with GeoParquet, H3 indexes, and Delta Sharing

🔷 c) H3 Index Support
H3 is a hierarchical hex-based spatial index developed by Uber.

Databricks supports H3 natively (via the H3 SQL extension or Python APIs)

Use h3_cell_to_boundary, h3_point_to_cell, and h3_cell_area_km2

✅ Example:
```sql

-- In Databricks SQL
SELECT h3_point_to_cell(37.7749, -122.4194, 8) AS h3_cell;
```
#### Integration with External Geospatial Tools
  
Kepler.gl - 	Visualize spatial data in Databricks  
ArcGIS /  - QGIS	External tools connected to Spark/Delta  
ESRI	- Enterprise GIS integration with Spark/ML  

#### Example Geospatial Pipeline on Databricks
Scenario: Geofence alerts for delivery vehicles  
Ingest GPS data from Kafka into Delta table

Use Sedona to parse points and match with polygon geofences

Filter events with ST_Within(point, geofence_polygon)

Store alerts into Delta + push to notification system

Visualize data with Kepler.gl or Databricks dashboard

| Feature                     | Apache Spark                 | Databricks Enhancements               |
| --------------------------- | ---------------------------- | ------------------------------------- |
| Geospatial types            | With Sedona                  | Built-in via Sedona + geospatial SQL  |
| Spatial joins & indexing    | Supported via Sedona         | Fully integrated, optimized for Delta |
| Format support              | WKT, WKB, GeoJSON, Shapefile | Same + H3, Delta Lake                 |
| Visualization               | External tools               | Kepler.gl, built-in notebooks         |
| Real-time/streaming support | Spark Structured Streaming   | Full Delta Live Tables + Auto Loader  |

 
#### Databricks notebook example: Real-time Geofence Alert System using Apache Sedona & H3
```python
# Step 1: Install Sedona and H3 (in Databricks cluster)
# %pip install apache-sedona h3

from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator, KryoSerializer
from pyspark.sql.functions import col, expr
import h3

# Step 2: Initialize Sedona
spark.conf.set("spark.serializer", KryoSerializer.getName)
spark.conf.set("spark.kryo.registrator", SedonaKryoRegistrator.getName)
SedonaRegistrator.registerAll(spark)

# Step 3: Create example geofence (polygon) table
geofence_data = [
    ("Zone A", "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"),
    ("Zone B", "POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))")
]

df_geofence = spark.createDataFrame(geofence_data, ["zone_name", "wkt"])
df_geofence = df_geofence.withColumn("geom", expr("ST_GeomFromText(wkt)"))
df_geofence.createOrReplaceTempView("geofences")

# Step 4: Simulate streaming GPS data (as batch for demo)
gps_data = [
    ("veh_1", 0.5, 0.5),  # Inside Zone A
    ("veh_2", 1.5, 1.5),  # Inside Zone B
    ("veh_3", 2.5, 2.5)   # Outside any zone
]

df_gps = spark.createDataFrame(gps_data, ["vehicle_id", "lon", "lat"])
df_gps = df_gps.withColumn("point", expr("ST_Point(cast(lon as decimal(24,20)), cast(lat as decimal(24,20)))"))
df_gps.createOrReplaceTempView("gps_events")

# Step 5: Spatial join to find matching geofences
alerts = spark.sql("""
SELECT g.vehicle_id, z.zone_name
FROM gps_events g, geofences z
WHERE ST_Contains(z.geom, g.point)
""")

alerts.show()

# Step 6: Use H3 to assign spatial index to each point
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

def point_to_h3(lon, lat, res=8):
    return h3.geo_to_h3(lat, lon, res)

h3_udf = udf(point_to_h3, StringType())
df_h3 = df_gps.withColumn("h3_index", h3_udf(col("lon"), col("lat")))
df_h3.select("vehicle_id", "h3_index").show()

# This notebook can be extended with:
# - Streaming input via Auto Loader or Kafka
# - Alert outputs to Delta, notification service, or external API
# - Visualization using Kepler.gl or Databricks dashboards

```
## PostGIS

- PostGIS is an open-source extension for PostgreSQL that:
- Adds support for geometric and geographic types
- Implements hundreds of spatial functions (e.g. distance, intersection, containment)
- Supports spatial indexing with GiST and SP-GiST
- Fully compliant with OpenGIS and OGC standards

#### Example Use Case: Point-in-Polygon Query
📘 Table: geofences (with polygons)
```sql

CREATE TABLE geofences (
    id SERIAL PRIMARY KEY,
    name TEXT,
    geom GEOMETRY(POLYGON, 4326)
);
```
📘 Table: locations (with points)
```sql

CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    location GEOMETRY(POINT, 4326)
);
```
#### Query: Find users inside geofence
```sql

SELECT l.user_id, g.name
FROM locations l
JOIN geofences g
  ON ST_Contains(g.geom, l.location);
```  
📦 Indexing for Performance
```sql

CREATE INDEX ON geofences USING GIST (geom);
CREATE INDEX ON locations USING GIST (location);
This dramatically improves performance for large datasets.
```

| Feature                      | Description                                             |
| ---------------------------- | ------------------------------------------------------- |
| `geometry`, `geography`      | Spatial data types (2D, 3D, etc.)                       |
| Spatial functions            | `ST_Distance()`, `ST_Intersects()`, `ST_Within()`, etc. |
| Spatial indexing             | GiST index for fast querying                            |
| Coordinate reference systems | Full support for **EPSG:4326**, **UTM**, etc.           |
| Raster + vector support      | Store satellite data, maps, and vector shapes           |
| GeoJSON support              | Read/write GeoJSON directly                             |


| Function          | Purpose                         |
| ----------------- | ------------------------------- |
| `ST_Distance()`   | Measure distance between shapes |
| `ST_Intersects()` | Do shapes overlap?              |
| `ST_Within()`     | Is point inside polygon?        |
| `ST_Buffer()`     | Create radius around a point    |
| `ST_MakePoint()`  | Construct a point from lon/lat  |


| Format        | Command Example                                |           |
| ------------- | ---------------------------------------------- | --------- |
| **Shapefile** | \`shp2pgsql -I input.shp table\_name           | psql db\` |
| **GeoJSON**   | `ST_AsGeoJSON(geom)` or `ST_GeomFromGeoJSON()` |           |
| **WKT/WKB**   | `ST_AsText(geom)` or `ST_GeomFromText()`       |           |

### Sedona vs PostGIS

| Feature           | Sedona                               | PostGIS                                       |
| ----------------- | ------------------------------------ | --------------------------------------------- |
| Geometry Types    | Point, LineString, Polygon, etc.     | Full OGC-compliant geometry types             |
| Spatial Functions | `ST_Contains`, `ST_Intersects`, etc. | Extensive – over 500+ spatial functions       |
| Distance Measures | Euclidean, Great Circle              | Euclidean, spherical, 3D, raster support      |
| Indexing          | R-tree, QuadTree                     | GiST, SP-GiST                                 |
| CRS Support       | EPSG codes supported                 | Full CRS support + transformation             |
| Raster Support    | ❌ Not yet                            | ✅ Yes (rasters, elevation, satellite imagery) |
| GeoJSON/WKT/WKB   | ✅ Supported                          | ✅ Supported                                   |

 Integration & Tools

| Feature           | Sedona                                 | PostGIS                                 |
| ----------------- | -------------------------------------- | --------------------------------------- |
| External Tools    | Kepler.gl, Databricks, Spark notebooks | QGIS, ArcGIS, pgAdmin, Geoserver        |
| Web Mapping       | With Spark + APIs                      | Direct integration with GeoServer, QGIS |
| Visualization     | Requires external tools                | Built-in via pgAdmin + QGIS integration |
| Streaming Support | ✅ (via Spark Structured Streaming)     | ❌ (only with external pipeline tools)   |

| Use Case              | Sedona                                      | PostGIS                               |
| --------------------- | ------------------------------------------- | ------------------------------------- |
| Billions of points    | ✅ Scalable (distributed memory/computation) | ❌ Slower or may require partitioning  |
| Complex spatial joins | Optimized with spatial partitioning         | Efficient but slower on large data    |
| Ad hoc queries        | ❌ Higher latency (Spark startup)            | ✅ Very fast for small/medium datasets |

<https://freegisdata.rtwilson.com/> freely available geographic datasets
<https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/> GIS with DuckDB  
<https://scottsexton.co/post/overthinking_gis/> 
<https://kepler.gl/>  geospatial analysis tool for large-scale data sets.  
<https://deck.gl/>   GPU-powered framework for visual exploratory data analysis of large datasets.  
<https://habr.com/ru/companies/ruvds/articles/917898/> GPS accuracy in city (urban canyon)  
MongoDB for GIS
<https://www.mongodb.com/docs/manual/geospatial-queries/#:~:text=MongoDB%20supports%20query%20operations%20on%20geospatial%20data.>

