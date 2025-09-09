 **Databricks Mosaic**  <https://databrickslabs.github.io/mosaic/>
 
 is an **open-source geospatial analytics library** built specifically for **Apache Spark** (and deeply integrated with Databricks).

It helps you do **spatial joins, geometry operations, and tiling** directly inside Spark SQL / PySpark, so you can run **large-scale geospatial processing** on billions of points (e.g. lat/long from IoT, GPS, telecom, etc.).

---

## 🔹 Key Features of Databricks Mosaic

* **Geometry support in Spark**
  Adds functions to handle geometries (`POINT`, `POLYGON`, etc.) in Spark DataFrames.

* **Point-in-polygon joins**
  Example: “Which state polygon does this GPS coordinate fall inside?”

* **H3 indexing (Uber’s hexagonal grid)**
  Convert lat/lon to H3 cells for **fast spatial bucketing and aggregations**.

* **Raster and vector data support**
  Works with shapefiles, GeoJSON, Parquet with geometry, raster imagery, etc.

* **SQL and PySpark APIs**
  You can call Mosaic functions in Spark SQL just like `ST_POINT`, `ST_WITHIN`, `ST_DISTANCE`.

* **Scales out**
  Unlike PostGIS (single-node), Mosaic leverages Spark clusters to handle **massive datasets**.

---

## 🔹 Example Use Case in Databricks

Say you have a Parquet file with **millions of GPS points**, and you want to assign each point to a **U.S. state**.

```python
import mosaic as mos

# Enable Mosaic on Spark
mos.enable_mosaic(spark, dbutils)

# Register Mosaic SQL functions
mos.enable_mosaic_sql(spark, dbutils)

# Read GPS points
df_points = spark.read.parquet("/mnt/data/gps_points")

# Read polygons (states shapefile converted to parquet/GeoJSON)
df_states = spark.read.format("geojson").load("/mnt/lookup/us_states.geojson")

# Register as temp views
df_points.createOrReplaceTempView("points")
df_states.createOrReplaceTempView("states")

# SQL: point-in-polygon join
enriched = spark.sql("""
SELECT p.id, p.lon, p.lat, s.state_name
FROM points p
JOIN states s
ON ST_Contains(s.geometry, ST_Point(p.lon, p.lat))
""")
```

Now every GPS point is enriched with its **state**.
Similarly, you can do **distance queries** to get nearest cities.

---

## 🔹 Why Use Mosaic?

* If you already use **Databricks**, it avoids needing PostGIS or separate GIS infra.
* Scales to **billions of rows**.
* Plays nicely with **Delta Lake**, **Parquet**, and **Spark SQL**.
* Production-ready for telecom, IoT, transport, energy use cases.

---

✅ **In your case (U.S. lat/lon → state + closest city)**:

* Load **TIGER state polygons** + **GeoNames cities centroids**.
* Use Mosaic `ST_Contains` for state lookup.
* Use Mosaic `ST_Distance` + window function for nearest city.

---

Here’s a **drop-in Databricks PySpark notebook** that:

1. enables Mosaic
2. reads your **point Parquet** (lon/lat)
3. reads **US state polygons** (GeoJSON)
4. reads **US cities** (GeoNames TSV)
5. enriches points with **state** (point-in-polygon) and **closest\_city** (nearest centroid)

Just set the three paths at the top and run.

```python
# Databricks notebook (Python) — Points → State + Nearest City using Mosaic
# -------------------------------------------------------------------------
# Prereqs (one-time per cluster):
#   %pip install databricks-mosaic
#   Restart Python when prompted.

from pyspark.sql import functions as F, types as T, Window as W

# === EDIT THESE PATHS ===
POINTS_PATH  = "/mnt/data/gps_points/"              # your points parquet; must have columns: longitude, latitude (double)
STATES_GEOJSON_PATH = "/mnt/lookup/us_states.geojson"   # US states GeoJSON (e.g., Census TIGER 'tl_latest_us_state.geojson')
GEONAMES_US_CITIES  = "/mnt/lookup/geonames_US.txt"     # GeoNames US cities file (tab-delimited 'US.txt')

# --- 1) Enable Mosaic ---
import mosaic as mos
mos.enable_mosaic(spark, dbutils)
mos.enable_mosaic_sql(spark, dbutils)

# Recommended configs
spark.conf.set("spark.databricks.labs.mosaic.geometry.api", "JTS")   # robust geometry engine
spark.conf.set("spark.databricks.labs.mosaic.index.system", "H3")    # for optional indexing later

from mosaic import functions as mf  # geometry functions, e.g. ST_Point, ST_Contains, ST_Distance

# --- 2) Read GPS points and build geometry ---
points = (
    spark.read.parquet(POINTS_PATH)
    .withColumn("lon", F.col("longitude").cast("double"))
    .withColumn("lat", F.col("latitude").cast("double"))
    .dropna(subset=["lon","lat"])
)

# Ensure there's a stable id for windowing later
if "id" not in points.columns:
    points = points.withColumn("id", F.monotonically_increasing_id())

points = points.withColumn("pt", mf.st_point(F.col("lon"), F.col("lat")))

# --- 3) Read US State polygons (GeoJSON) and build geometry ---
# Expecting a FeatureCollection with: properties.NAME (state) and geometry
# If your file is line-delimited GeoJSON, this still works; Spark json reader is flexible.
raw_states = spark.read.option("multiLine", "true").json(STATES_GEOJSON_PATH)

# If the file is a standard FeatureCollection:
if "features" in raw_states.columns:
    states = (
        raw_states.select(F.explode("features").alias("f"))
        .select(
            F.col("f.properties.NAME").alias("state_name"),
            F.to_json("f.geometry").alias("geometry_json")
        )
    )
else:
    # fallback if file already contains per-feature rows
    states = raw_states.select(
        F.col("properties.NAME").alias("state_name"),
        F.to_json("geometry").alias("geometry_json")
    )

states = states.withColumn("geom", mf.st_geomfromgeojson("geometry_json")).select("state_name","geom")

# (Optional) Cache/broadcast small polygon table
states = states.cache()
# from pyspark.sql.functions import broadcast
# states = broadcast(states)

# --- 4) Read US Cities (GeoNames) and build centroid geometry ---
# GeoNames US.txt schema: https://download.geonames.org/export/dump/readme.txt
# We’ll keep a minimal schema and filter to populated places for speed/quality.
city_schema = T.StructType([
    T.StructField("geonameid", T.IntegerType(), True),           # 0
    T.StructField("name", T.StringType(), True),                 # 1
    T.StructField("asciiname", T.StringType(), True),            # 2
    T.StructField("alternatenames", T.StringType(), True),       # 3
    T.StructField("latitude", T.DoubleType(), True),             # 4
    T.StructField("longitude", T.DoubleType(), True),            # 5
    T.StructField("feature_class", T.StringType(), True),        # 6
    T.StructField("feature_code", T.StringType(), True),         # 7
    T.StructField("country_code", T.StringType(), True),         # 8
    T.StructField("cc2", T.StringType(), True),                  # 9
    T.StructField("admin1_code", T.StringType(), True),          # 10 (state FIPS-ish)
    T.StructField("admin2_code", T.StringType(), True),          # 11
    T.StructField("admin3_code", T.StringType(), True),          # 12
    T.StructField("admin4_code", T.StringType(), True),          # 13
    T.StructField("population", T.LongType(), True),             # 14
    T.StructField("elevation", T.IntegerType(), True),           # 15
    T.StructField("dem", T.IntegerType(), True),                 # 16
    T.StructField("timezone", T.StringType(), True),             # 17
    T.StructField("modification_date", T.StringType(), True),    # 18
])

cities = (
    spark.read
         .option("sep", "\t")
         .option("quote", "\u0000")
         .schema(city_schema)
         .csv(GEONAMES_US_CITIES)
         .filter(F.col("country_code") == "US")
         # Keep populated places only (PPL*) and bigger towns to reduce candidate set
         .filter(F.col("feature_class") == "P")
         .filter(F.col("population") >= 10000)
         .withColumnRenamed("name","city_name")
         .withColumn("city_lon", F.col("longitude").cast("double"))
         .withColumn("city_lat", F.col("latitude").cast("double"))
         .dropna(subset=["city_lon","city_lat"])
         .withColumn("city_pt", mf.st_point("city_lon", "city_lat"))
         .select("geonameid","city_name","admin1_code","population","city_lon","city_lat","city_pt")
         .cache()
)

# --- 5) STATE ENRICHMENT: point-in-polygon join ---
points_with_state = (
    points.alias("p")
    .join(states.alias("s"), mf.st_contains(F.col("s.geom"), F.col("p.pt")), "left")
    .select("p.*", F.col("s.state_name"))
)

# --- 6) CLOSEST CITY ENRICHMENT ---
# Strategy: Pre-filter candidate cities by a lat/lon box (fast), then compute precise distances
# via a Haversine UDF; pick the nearest with a window function.
# (This scales well; tune the 'box_delta_deg' depending on point density.)

import math

@F.udf("double")
def haversine_km(lon1, lat1, lon2, lat2):
    # robust for WGS84 coordinates in degrees
    if None in (lon1, lat1, lon2, lat2):
        return None
    R = 6371.0088  # mean Earth radius (km)
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = math.sin(dlat/2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Prefilter band: ~0.5 degree ~ up to ~55 km in latitude; we’ll also allow a bit wider for longitude.
box_delta_deg = F.lit(0.75)  # widen if you want bigger search radius

candidates = (
    points_with_state
      .select("id","lon","lat","state_name")
      .join(
          cities.select("geonameid","city_name","admin1_code","population","city_lon","city_lat"),
          on=(
              (F.col("city_lat") >= (F.col("lat") - box_delta_deg)) &
              (F.col("city_lat") <= (F.col("lat") + box_delta_deg)) &
              (F.col("city_lon") >= (F.col("lon") - box_delta_deg)) &
              (F.col("city_lon") <= (F.col("lon") + box_delta_deg))
          ),
          how="inner"
      )
      .withColumn("dist_km", haversine_km(F.col("lon"), F.col("lat"), F.col("city_lon"), F.col("city_lat")))
)

w = W.partitionBy("id").orderBy(F.col("dist_km").asc(), F.col("population").desc())
nearest_city = (
    candidates
      .withColumn("rn", F.row_number().over(w))
      .filter(F.col("rn") == 1)
      .select(
          "id",
          F.col("city_name").alias("closest_city"),
          F.col("admin1_code").alias("closest_city_admin1"),
          "dist_km"
      )
)

# --- 7) Final enriched dataset ---
enriched = (
    points_with_state.alias("p")
    .join(nearest_city.alias("c"), on="id", how="left")
    .select(
        "p.*",
        "state_name",
        "closest_city",
        "closest_city_admin1",
        F.round("dist_km", 3).alias("closest_city_distance_km")
    )
)

# Persist as Delta (or view)
enriched.write.mode("overwrite").format("delta").saveAsTable("geo.enriched_points_us")

display(enriched.limit(50))
```

### Notes & tips

* **Inputs**

  * `POINTS_PATH` must contain columns `longitude` and `latitude` (double).
  * `STATES_GEOJSON_PATH` can be the Census TIGER/Line states GeoJSON.
  * `GEONAMES_US_CITIES` is the GeoNames “US.txt” (tab-delimited). We filter to **populated places** with **population ≥ 10k** to keep nearest-city fast and meaningful; adjust as you like.

* **Performance**

  * The **state join** uses true **point-in-polygon** via `ST_Contains` (accurate).
  * The **nearest city** step does a **bounding-box prefilter** then exact **Haversine** distance. For very large datasets, consider:

    * increasing/decreasing `box_delta_deg` (trade recall vs speed),
    * or using **H3** bucketing with a k-ring join when you want strict locality indexing.

* **Outputs**

  * `state_name`: US state resolved by polygon containment.
  * `closest_city`, `closest_city_admin1`, `closest_city_distance_km`: nearest GeoNames city centroid and distance in km.

Awesome — here are two **drop-in helper cells** you can paste at the *top* of your Databricks notebook to **download & stage** both datasets into DBFS and leave you with the exact paths your main pipeline expects.

---

# 0) Download raw files into DBFS (states + cities)

```
%sh
set -euo pipefail

# Where to put the downloaded/source files (inside DBFS)
RAW_DIR=/dbfs/tmp/lookup_raw
mkdir -p "$RAW_DIR"

echo "→ Downloading Census cartographic boundary STATES (shapefile zip)…"
# 2023 cartographic boundary file (states, 1:500k)
# Directory listing (for reference): https://www2.census.gov/geo/tiger/GENZ2023/shp/
curl -L -o "$RAW_DIR/cb_2023_us_state_500k.zip" "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_500k.zip"

echo "→ Unzipping shapefile…"
unzip -o "$RAW_DIR/cb_2023_us_state_500k.zip" -d "$RAW_DIR/cb_2023_us_state_500k"

echo "→ Downloading GeoNames cities (population ≥ 15k)…"
# We’ll use the compact cities15k dump and filter to US later in Spark
# Directory index: https://download.geonames.org/export/dump/
curl -L -o "$RAW_DIR/cities15000.zip" "https://download.geonames.org/export/dump/cities15000.zip"

echo "→ Unzipping GeoNames cities…"
unzip -o "$RAW_DIR/cities15000.zip" -d "$RAW_DIR"

echo "✔ Done. Raw files are in $RAW_DIR"
ls -lh "$RAW_DIR" || true
```

* Source for state boundaries (official Census cartographic boundary files): ([Census][1], [Data.gov][2])
* Source for GeoNames cities dumps: ([GeoNames][3])

---

# 1) Convert the state shapefile → GeoJSON in DBFS

Databricks can read GeoJSON easily; we’ll convert the shapefile once and store the result where the main code expects it.

```
# Databricks Python cell
# One-time install (lightweight) for vector I/O:
%pip install -q geopandas pyogrio shapely

dbutils.library.restartPython()
```

```
# Databricks Python cell
import os
import geopandas as gpd

RAW_DIR = "/dbfs/tmp/lookup_raw"
SRC_SHAPE_DIR = f"{RAW_DIR}/cb_2023_us_state_500k"  # folder created by unzip
OUT_GEOJSON_DBFS = "/dbfs/mnt/lookup/us_states.geojson"  # final target your pipeline will use
os.makedirs("/dbfs/mnt/lookup", exist_ok=True)

# Read the shapefile (pyogrio backend handles it efficiently)
# File inside the folder is typically named cb_2023_us_state_500k.shp
shp_path = [p for p in os.listdir(SRC_SHAPE_DIR) if p.endswith(".shp")][0]
gdf = gpd.read_file(os.path.join(SRC_SHAPE_DIR, shp_path))

# Keep the human-friendly state name column; Census often uses NAME
keep_cols = [c for c in gdf.columns if c.upper() in ("NAME", "STUSPS", "GEOID")]
gdf = gdf[keep_cols + ["geometry"]]

# Standardize property names the main notebook expects:
rename_map = {}
if "NAME" in gdf.columns: rename_map["NAME"] = "state_name"
if "STUSPS" in gdf.columns: rename_map["STUSPS"] = "state_abbr"
if "GEOID" in gdf.columns: rename_map["GEOID"] = "state_geoid"
gdf = gdf.rename(columns=rename_map)

# Write GeoJSON (newline-delimited not required here)
gdf.to_file(OUT_GEOJSON_DBFS, driver="GeoJSON")
print(f"✔ Wrote GeoJSON → {OUT_GEOJSON_DBFS}")
```

---

# 2) Set the paths your main pipeline will use

Now you can set the same three variables you used earlier to point at what we just staged:

```
# Databricks Python cell
POINTS_PATH = "/mnt/data/gps_points/"                     # (your existing points parquet)
STATES_GEOJSON_PATH = "/mnt/lookup/us_states.geojson"     # produced above
GEONAMES_US_CITIES  = "/tmp/lookup_raw/cities15000.txt"   # unzipped text file

# Note: /dbfs/... paths are visible to the driver; Spark APIs should use /mnt, /tmp (no /dbfs prefix).
# We'll copy/alias if you prefer clean mount-style paths:
dbutils.fs.mkdirs("dbfs:/mnt/lookup")
dbutils.fs.cp("dbfs:/mnt/lookup/us_states.geojson", "dbfs:/mnt/lookup/us_states.geojson", True)  # no-op keeps it in place

# For the cities file, we can reference it via /dbfs to Spark by using file:// in pandas or
# directly in Spark CSV reader with the absolute path shown next cell in your main pipeline.
print("POINTS_PATH =", POINTS_PATH)
print("STATES_GEOJSON_PATH =", STATES_GEOJSON_PATH)
print("GEONAMES_US_CITIES =", "/dbfs/tmp/lookup_raw/cities15000.txt")
```

In your **main enrichment notebook**, set:

* `STATES_GEOJSON_PATH = "/mnt/lookup/us_states.geojson"`
* `GEONAMES_US_CITIES = "/dbfs/tmp/lookup_raw/cities15000.txt"` (the Spark CSV reader accepts this absolute path).

That’s it — after running these cells once, your earlier Mosaic pipeline should run end-to-end without leaving Databricks.

[1]: https://www2.census.gov/geo/tiger/GENZ2023/shp/?utm_source=chatgpt.com "Index of /geo/tiger/GENZ2023/shp"
[2]: https://catalog.data.gov/dataset/2023-cartographic-boundary-file-shp-state-and-equivalent-entities-for-united-states-1-500000/resource/38adbbf9-658a-4e0f-911c-ed1c0db0c940?utm_source=chatgpt.com "cb_2023_us_state_500k.zip - Dataset - Catalog"
[3]: https://download.geonames.org/export/dump/ "GeoNames"
