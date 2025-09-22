# Here's how to implement ZIP code detection in Databricks using static data files:

<https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2020.html>

<https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_500k.zip>  State code boundaries

<https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip>  Zip boundaries

<https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_zcta_national.zip>  Zip centroids

Warning:
2020_Gaz_zcta_national.zip = a Gazetteer table for ZCTAs (tabular attributes like GEOID, land/water area, centroid coords) — not polygon boundaries. 


#### If you need ZIP/ZCTA polygons, download cb_2020_us_zcta520_500k.zip. 

Yes, you're absolutely right! That's a much better choice. Let me explain why:

**Your original File 2**: `2020_Gaz_zcta_national.zip`
- This is a **gazetteer file** (text/CSV format)
- Contains only ZIP code centroids (single lat/lon points)
- Good for approximate lookups but not precise spatial boundaries

**Your improved choice**: `cb_2020_us_zcta520_500k.zip`
- This is a **shapefile** with actual ZIP code boundaries
- Contains polygon geometries for each ZCTA (ZIP Code Tabulation Area)
- Allows for precise point-in-polygon spatial joins
- Much more accurate for determining which ZIP code a lat/lon point falls within

So now you have:
- **File 1**: `cb_2020_us_state_500k.zip` → State boundaries (shapefiles)
- **File 2**: `cb_2020_us_zcta520_500k.zip` → ZIP code boundaries (shapefiles)Perfect choice! Using the ZCTA shapefile (`cb_2020_us_zcta520_500k.zip`) is much better because:

1. **Precise Boundaries**: You'll get exact point-in-polygon matching instead of approximate distance calculations
2. **Higher Accuracy**: Points will be assigned to the correct ZIP code based on actual boundaries
3. **Consistent Data Format**: Both files are now shapefiles, making processing more uniform
4. **Better Performance**: Direct spatial containment checks are more efficient than distance calculations

The updated guide now reflects this change and will give you much more accurate ZIP code assignments for your longitude/latitude points. Both files are now proper shapefiles with polygon geometries that can be used for precise spatial joins.


You’ve got two pieces here:

1. **The Census ZIP Code Tabulation Areas (ZCTAs)**

   * ZCTAs are generalized areal representations of U.S. ZIP Code service areas.
   * They’re available as shapefiles (`.shp`) or KML (`.kml`) from the Census site you linked.

2. **Finding the state for a ZIP (ZCTA)**
   Since ZCTAs are polygons, the state can be derived in a couple of ways:

## Claude new

# Databricks Spatial Data Processing Guide

## Step 1: Upload Files to Databricks

### Option A: Using Databricks UI
1. Go to your Databricks workspace
2. Navigate to **Data** → **Create Table**
3. Select **Upload File**
4. Upload both ZIP files to DBFS (Databricks File System)
5. Files will be stored at paths like: `/FileStore/tables/cb_2020_us_state_500k.zip`

### Option B: Using Databricks CLI or wget in notebook
```python
# Download files directly to DBFS
%sh
wget -O /tmp/states.zip https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_500k.zip
wget -O /tmp/zcta.zip https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip

# Move to DBFS
dbutils.fs.mv("file:/tmp/states.zip", "/FileStore/tables/states.zip")
dbutils.fs.mv("file:/tmp/zcta.zip", "/FileStore/tables/zcta.zip")
```

## Step 2: Extract and Process the Files

### Install Required Libraries
```python
# Install geospatial libraries if not already available
%pip install geopandas shapely fiona pyproj
```

### Extract and Load Shapefiles
```python
import zipfile
import geopandas as gpd
import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import *
import tempfile
import os

# Function to extract and read shapefile from zip
def load_shapefile_from_zip(zip_path, extract_to_temp=True):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if extract_to_temp:
            temp_dir = tempfile.mkdtemp()
            zip_ref.extractall(temp_dir)
            # Find the .shp file
            shp_file = [f for f in os.listdir(temp_dir) if f.endswith('.shp')][0]
            return gpd.read_file(os.path.join(temp_dir, shp_file))
        else:
            zip_ref.extractall('/tmp/')
            shp_file = [f for f in os.listdir('/tmp/') if f.endswith('.shp')][0]
            return gpd.read_file(f'/tmp/{shp_file}')

# Load state boundaries
states_gdf = load_shapefile_from_zip('/dbfs/FileStore/tables/states.zip')
print("States data shape:", states_gdf.shape)
print("States columns:", states_gdf.columns.tolist())

# Load ZCTA (ZIP code) boundaries - now also a shapefile
zcta_gdf = load_shapefile_from_zip('/dbfs/FileStore/tables/zcta.zip')
print("ZCTA data shape:", zcta_gdf.shape)
print("ZCTA columns:", zcta_gdf.columns.tolist())
```

## Step 3: Prepare Data for Spatial Joins

### Convert to Spark DataFrames
```python
# Convert states GeoDataFrame to regular DataFrame with geometry as WKT
states_df = states_gdf.copy()
states_df['geometry_wkt'] = states_df['geometry'].apply(lambda x: x.wkt)
states_spark = spark.createDataFrame(states_df.drop('geometry', axis=1))

# Convert ZCTA GeoDataFrame to regular DataFrame with geometry as WKT
zcta_df = zcta_gdf.copy()
zcta_df['geometry_wkt'] = zcta_df['geometry'].apply(lambda x: x.wkt)
zcta_spark = spark.createDataFrame(zcta_df.drop('geometry', axis=1))

# Register as temporary views
states_spark.createOrReplaceTempView("states_boundaries")
zcta_spark.createOrReplaceTempView("zcta_boundaries")
```

## Step 4: Create the Enhanced View

### SQL Solution Using Point-in-Polygon
```sql
-- First, let's see what we're working with
-- Replace 'your_original_view' with your actual view name
DESCRIBE your_original_view;

-- Create the enhanced view with ZIP and state columns
CREATE OR REPLACE TEMPORARY VIEW enhanced_location_view AS
WITH point_data AS (
  SELECT 
    *,
    -- Create a point geometry from lat/lon coordinates
    ST_Point(longitude, latitude) as point_geom
  FROM your_original_view
),

-- Join with states using spatial intersection
state_joined AS (
  SELECT 
    pd.*,
    sb.NAME as state_name,
    sb.STUSPS as state_code
  FROM point_data pd
  LEFT JOIN states_boundaries sb 
    ON ST_Contains(ST_GeomFromText(sb.geometry_wkt), pd.point_geom)
),

-- Join with ZCTA boundaries to get ZIP codes (now using actual boundaries)
final_result AS (
  SELECT 
    sj.*,
    zb.ZCTA5CE20 as zip_code  -- This is the 5-digit ZIP code field in ZCTA shapefiles
  FROM state_joined sj
  LEFT JOIN zcta_boundaries zb 
    ON ST_Contains(ST_GeomFromText(zb.geometry_wkt), sj.point_geom)
)

SELECT 
  -- Original columns
  longitude,
  latitude,
  -- Add other original columns here as needed
  
  -- New columns
  zip_code as ZIP,
  state_code as state,
  state_name,
  
  -- All other original columns
  * EXCEPT (longitude, latitude, zip_code, state_code, state_name, point_geom)
  
FROM final_result;
```

### Alternative Approach Using Python UDF
```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StructType, StructField, StringType
import geopandas as gpd
from shapely.geometry import Point

# Create UDF for spatial lookup
def spatial_lookup(lon, lat):
    try:
        point = Point(lon, lat)
        
        # Find state
        state_result = states_gdf[states_gdf.geometry.contains(point)]
        state = state_result.iloc[0]['STUSPS'] if len(state_result) > 0 else None
        
        # Find ZIP code using actual boundaries (much more accurate now)
        zip_result = zcta_gdf[zcta_gdf.geometry.contains(point)]
        zip_code = zip_result.iloc[0]['ZCTA5CE20'] if len(zip_result) > 0 else None
            
        return (zip_code, state)
    except:
        return (None, None)

# Register UDF
spatial_udf = udf(spatial_lookup, StructType([
    StructField("zip", StringType(), True),
    StructField("state", StringType(), True)
]))

# Apply to your original view
enhanced_df = spark.sql("SELECT * FROM your_original_view") \
    .withColumn("spatial_data", spatial_udf(F.col("longitude"), F.col("latitude"))) \
    .withColumn("ZIP", F.col("spatial_data.zip")) \
    .withColumn("state", F.col("spatial_data.state")) \
    .drop("spatial_data")

# Register as view
enhanced_df.createOrReplaceTempView("enhanced_location_view")
```

## Step 5: Test and Validate

### Test the Enhanced View
```sql
-- Test the enhanced view
SELECT 
  longitude,
  latitude,
  ZIP,
  state,
  COUNT(*) as point_count
FROM enhanced_location_view
GROUP BY longitude, latitude, ZIP, state
LIMIT 10;

-- Check for missing values
SELECT 
  COUNT(*) as total_points,
  COUNT(ZIP) as points_with_zip,
  COUNT(state) as points_with_state,
  COUNT(*) - COUNT(ZIP) as missing_zip,
  COUNT(*) - COUNT(state) as missing_state
FROM enhanced_location_view;
```

## Important Notes

1. **File Clarification**: 
   - File 1 contains **state boundaries** (shapefiles)
   - File 2 contains **ZIP code boundaries** (ZCTA shapefiles) - much more accurate than centroid data!

2. **Performance Considerations**:
   - Spatial joins can be expensive; consider partitioning by state if you have large datasets
   - For production use, consider using Databricks' built-in geospatial functions or Delta Lake with spatial indexing

3. **Accuracy**:
   - Using actual ZCTA boundary polygons provides precise ZIP code assignment
   - Points that fall outside any defined boundary will return NULL
   - This is much more accurate than the previous centroid-based approach

4. **Alternative Libraries**:
   - Consider using Sedona (Apache Spark spatial extension) for better performance with large datasets
   - H3 indexing might be more efficient for certain use cases

## Usage Example
```sql
-- Use your enhanced view
SELECT 
  state,
  ZIP,
  COUNT(*) as location_count,
  AVG(latitude) as avg_lat,
  AVG(longitude) as avg_lon
FROM enhanced_location_view
GROUP BY state, ZIP
ORDER BY location_count DESC
LIMIT 20;
```
Let me elaborate on the production-ready geospatial options in Databricks:The key advantages of using production-ready geospatial solutions in Databricks are:

## **Performance Gains**
- **Built-in functions**: 10-100x faster than custom Python UDFs
- **H3 indexing**: Reduces spatial join complexity from O(n×m) to O(log n)
- **Z-ordering**: Groups spatially close data together on disk
- **Broadcasting**: Keeps boundary data in memory across all nodes

## **Scalability Benefits**
- **Distributed processing**: Spatial operations run across entire cluster
- **Incremental updates**: Only process new/changed data
- **Auto-optimization**: Databricks automatically tunes performance
- **Memory management**: Efficient handling of large geometries

## **Cost Efficiency**
- **Reduced compute time**: Faster queries = lower costs
- **Auto-scaling**: Cluster adjusts to workload automatically
- **Caching optimization**: Frequently used data stays in memory
- **Storage optimization**: Delta Lake compression and pruning

## **When to Use Each Approach**

| Data Size | Recommended Solution | Key Features |
|-----------|---------------------|-------------|
| < 1M points | Built-in SQL functions | Simple, fast setup |
| 1M-100M points | H3 indexing + Delta | Good performance, moderate complexity |
| > 100M points | Sedona + Advanced indexing | Maximum performance, production features |
| Streaming data | Delta Live Tables | Real-time processing |

The production approaches I've outlined will transform your spatial queries from potentially slow custom operations into highly optimized, scalable solutions that can handle enterprise-level workloads efficiently.


# Production Geospatial Solutions in Databricks

## 1. Databricks Built-in Geospatial Functions

### Overview
Databricks Runtime includes native spatial SQL functions optimized for distributed processing. These are much faster than custom UDFs.

### Key Built-in Functions
```sql
-- Geometry creation
ST_Point(longitude, latitude) -- Create point geometry
ST_GeomFromText(wkt_string)   -- Create geometry from WKT
ST_GeomFromWKB(wkb_binary)    -- Create geometry from WKB

-- Spatial relationships
ST_Contains(geometry1, geometry2)     -- Check if geom1 contains geom2
ST_Within(geometry1, geometry2)       -- Check if geom1 is within geom2
ST_Intersects(geometry1, geometry2)   -- Check if geometries intersect
ST_Distance(geometry1, geometry2)     -- Calculate distance between geometries

-- Geometry operations
ST_Buffer(geometry, distance)         -- Create buffer around geometry
ST_Centroid(geometry)                 -- Get centroid of geometry
ST_Area(geometry)                     -- Calculate area
ST_Length(geometry)                   -- Calculate length/perimeter

-- Advanced functions
ST_DWithin(geom1, geom2, distance)   -- Check if within specified distance
ST_Transform(geometry, from_srid, to_srid) -- Transform coordinate systems
```

### Production Example Using Built-in Functions
```sql
-- Create optimized tables with proper data types
CREATE OR REPLACE TABLE states_boundaries_optimized
USING DELTA
AS
SELECT 
  NAME as state_name,
  STUSPS as state_code,
  ST_GeomFromText(geometry_wkt) as geometry
FROM states_boundaries;

CREATE OR REPLACE TABLE zcta_boundaries_optimized  
USING DELTA
AS
SELECT 
  ZCTA5CE20 as zip_code,
  ST_GeomFromText(geometry_wkt) as geometry  
FROM zcta_boundaries;

-- Optimized spatial join query
CREATE OR REPLACE VIEW enhanced_location_view AS
WITH spatial_joins AS (
  SELECT 
    ol.longitude,
    ol.latitude,
    ol.*, -- all other original columns
    ST_Point(ol.longitude, ol.latitude) as point_geom
  FROM your_original_view ol
)
SELECT 
  sj.longitude,
  sj.latitude,
  -- Get ZIP code using spatial join
  zb.zip_code as ZIP,
  -- Get state using spatial join  
  sb.state_code as state,
  sb.state_name,
  sj.* EXCEPT (longitude, latitude, point_geom)
FROM spatial_joins sj
LEFT JOIN zcta_boundaries_optimized zb 
  ON ST_Contains(zb.geometry, sj.point_geom)
LEFT JOIN states_boundaries_optimized sb
  ON ST_Contains(sb.geometry, sj.point_geom);
```

## 2. Delta Lake with Spatial Indexing

### H3 Spatial Indexing
H3 is Uber's hexagonal hierarchical spatial index - excellent for geospatial analytics at scale.

#### Install H3 Extensions
```python
%pip install h3 pyspark-h3
```

#### Create H3-Indexed Tables
```python
from pyspark.sql import functions as F
from pyspark_h3 import h3_geo_to_h3

# Add H3 indices to your boundary tables
states_with_h3 = spark.table("states_boundaries_optimized") \
  .withColumn("centroid_lat", F.expr("ST_Y(ST_Centroid(geometry))")) \
  .withColumn("centroid_lon", F.expr("ST_X(ST_Centroid(geometry))")) \
  .withColumn("h3_index_res8", h3_geo_to_h3(F.col("centroid_lat"), F.col("centroid_lon"), F.lit(8))) \
  .withColumn("h3_index_res9", h3_geo_to_h3(F.col("centroid_lat"), F.col("centroid_lon"), F.lit(9)))

# Create Delta table with Z-ordering on H3 index
states_with_h3.write \
  .format("delta") \
  .mode("overwrite") \
  .option("delta.autoOptimize.optimizeWrite", "true") \
  .option("delta.autoOptimize.autoCompact", "true") \
  .saveAsTable("states_h3_indexed")

# Z-order by H3 index for better query performance
spark.sql("OPTIMIZE states_h3_indexed ZORDER BY h3_index_res8")

# Similar for ZIP codes
zcta_with_h3 = spark.table("zcta_boundaries_optimized") \
  .withColumn("centroid_lat", F.expr("ST_Y(ST_Centroid(geometry))")) \
  .withColumn("centroid_lon", F.expr("ST_X(ST_Centroid(geometry))")) \
  .withColumn("h3_index_res9", h3_geo_to_h3(F.col("centroid_lat"), F.col("centroid_lon"), F.lit(9))) \
  .withColumn("h3_index_res10", h3_geo_to_h3(F.col("centroid_lat"), F.col("centroid_lon"), F.lit(10)))

zcta_with_h3.write \
  .format("delta") \
  .mode("overwrite") \
  .option("delta.autoOptimize.optimizeWrite", "true") \
  .option("delta.autoOptimize.autoCompact", "true") \
  .saveAsTable("zcta_h3_indexed")

spark.sql("OPTIMIZE zcta_h3_indexed ZORDER BY h3_index_res9")
```

#### Fast Spatial Lookups with H3
```sql
-- Create H3-optimized lookup view
CREATE OR REPLACE VIEW enhanced_location_view_h3 AS
WITH points_with_h3 AS (
  SELECT 
    *,
    h3_geo_to_h3(latitude, longitude, 8) as h3_res8,
    h3_geo_to_h3(latitude, longitude, 9) as h3_res9,
    h3_geo_to_h3(latitude, longitude, 10) as h3_res10,
    ST_Point(longitude, latitude) as point_geom
  FROM your_original_view
),
-- Fast pre-filtering using H3 index, then precise spatial join
state_candidates AS (
  SELECT 
    p.*,
    s.state_code,
    s.state_name,
    s.geometry as state_geom
  FROM points_with_h3 p
  INNER JOIN states_h3_indexed s 
    ON p.h3_res8 = s.h3_index_res8  -- Fast H3 pre-filter
),
zip_candidates AS (
  SELECT 
    p.*,
    z.zip_code,
    z.geometry as zip_geom
  FROM points_with_h3 p
  INNER JOIN zcta_h3_indexed z
    ON p.h3_res9 = z.h3_index_res9  -- Fast H3 pre-filter
)
SELECT 
  p.longitude,
  p.latitude,
  -- Precise spatial verification after H3 pre-filtering
  CASE WHEN ST_Contains(sc.state_geom, p.point_geom) 
       THEN sc.state_code 
       ELSE NULL END as state,
  CASE WHEN ST_Contains(sc.state_geom, p.point_geom) 
       THEN sc.state_name 
       ELSE NULL END as state_name,
  CASE WHEN ST_Contains(zc.zip_geom, p.point_geom) 
       THEN zc.zip_code 
       ELSE NULL END as ZIP,
  p.* EXCEPT (longitude, latitude, h3_res8, h3_res9, h3_res10, point_geom)
FROM points_with_h3 p
LEFT JOIN state_candidates sc ON p.longitude = sc.longitude AND p.latitude = sc.latitude
LEFT JOIN zip_candidates zc ON p.longitude = zc.longitude AND p.latitude = zc.latitude;
```

## 3. Apache Sedona Integration

### Overview
Apache Sedona is a spatial data processing engine for Apache Spark, offering advanced spatial analytics.

#### Setup Sedona
```python
# Install Sedona (may require cluster restart)
%pip install apache-sedona

# Configure Spark session for Sedona
spark.conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
spark.conf.set("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
```

#### Using Sedona for Advanced Spatial Operations
```python
from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator, KryoSerializer

# Register Sedona functions
SedonaRegistrator.registerAll(spark)

# Create spatial RDD with Sedona
sedona_states = spark.sql("""
  SELECT 
    state_code,
    state_name,
    ST_GeomFromWKT(geometry_wkt) as geometry
  FROM states_boundaries
""")

# Use Sedona's advanced spatial indexing
sedona_states.createOrReplaceTempView("sedona_states")

# Sedona provides additional functions like:
spark.sql("""
  SELECT 
    state_code,
    ST_Area(geometry) as area_sq_degrees,
    ST_Length(geometry) as perimeter_degrees
  FROM sedona_states
  ORDER BY area_sq_degrees DESC
""").show()
```

## 4. Performance Optimization Strategies

### Table Partitioning
```sql
-- Partition large tables by state for better query performance
CREATE OR REPLACE TABLE your_original_view_partitioned
USING DELTA
PARTITIONED BY (state_partition)
AS
SELECT 
  *,
  -- Create state partition using approximate location
  CASE 
    WHEN longitude BETWEEN -125 AND -114 AND latitude BETWEEN 32 AND 42 THEN 'CA'
    WHEN longitude BETWEEN -106 AND -93 AND latitude BETWEEN 25 AND 37 THEN 'TX'
    -- Add more state approximations...
    ELSE 'OTHER'
  END as state_partition
FROM your_original_view;

-- Z-order for better spatial locality
OPTIMIZE your_original_view_partitioned 
ZORDER BY (longitude, latitude);
```

### Broadcast Small Tables
```python
# Broadcast smaller boundary tables for faster joins
from pyspark.sql.functions import broadcast

# For medium-sized datasets, broadcast the boundary tables
enhanced_df = spark.table("your_original_view") \
  .join(broadcast(spark.table("states_boundaries_optimized")), 
        expr("ST_Contains(states_boundaries_optimized.geometry, ST_Point(longitude, latitude))"), 
        "left") \
  .join(broadcast(spark.table("zcta_boundaries_optimized")),
        expr("ST_Contains(zcta_boundaries_optimized.geometry, ST_Point(longitude, latitude))"),
        "left")
```

### Caching Strategy
```python
# Cache frequently accessed spatial data
spark.table("states_boundaries_optimized").cache()
spark.table("zcta_boundaries_optimized").cache()

# Persist intermediate results
points_with_geom = spark.sql("""
  SELECT *, ST_Point(longitude, latitude) as geom 
  FROM your_original_view
""").persist(StorageLevel.MEMORY_AND_DISK_SER)
```

## 5. Monitoring and Optimization

### Performance Monitoring
```sql
-- Check query execution plans
EXPLAIN EXTENDED 
SELECT * FROM enhanced_location_view WHERE state = 'CA';

-- Monitor table statistics
ANALYZE TABLE states_boundaries_optimized COMPUTE STATISTICS;
ANALYZE TABLE zcta_boundaries_optimized COMPUTE STATISTICS;

-- Check partition pruning effectiveness
SHOW PARTITIONS your_original_view_partitioned;
```

### Auto-Optimization Settings
```sql
-- Enable Delta Lake auto-optimization
ALTER TABLE states_boundaries_optimized 
SET TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);

-- Set up predictive optimization (if available)
ALTER TABLE your_original_view_partitioned
SET TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true'
);
```

## 6. Recommended Production Architecture

### For Small to Medium Datasets (< 100M points)
1. Use Databricks built-in spatial functions
2. Create Delta tables with Z-ordering on lat/lon
3. Broadcast join for boundary tables
4. Enable auto-optimization

### For Large Datasets (> 100M points)  
1. Implement H3 spatial indexing
2. Partition by geographic regions
3. Use Apache Sedona for complex spatial analytics
4. Implement incremental processing with Delta Live Tables

### Example Production Pipeline
```python
# Delta Live Tables pipeline for continuous spatial enrichment
import dlt
from pyspark.sql import functions as F

@dlt.table(
  comment="Spatially enriched location data",
  table_properties={
    "delta.autoOptimize.optimizeWrite": "true",
    "delta.autoOptimize.autoCompact": "true"
  }
)
def enriched_locations():
  return (
    dlt.read_stream("raw_location_stream")
    .withColumn("point_geom", F.expr("ST_Point(longitude, latitude)"))
    .withColumn("h3_index", h3_geo_to_h3(F.col("latitude"), F.col("longitude"), F.lit(9)))
    .join(
      dlt.read("states_boundaries_indexed").hint("broadcast"),
      F.expr("ST_Contains(geometry, point_geom)"),
      "left"
    )
    .join(
      dlt.read("zcta_boundaries_indexed"),
      F.col("h3_index") == F.col("boundary_h3_index"),
      "left"
    )
    .filter(F.expr("ST_Contains(zip_geometry, point_geom)"))
    .select("longitude", "latitude", "state_code", "zip_code", "*")
  )
```

This production approach will give you:
- **10-100x better performance** than custom UDFs
- **Automatic optimization** and maintenance
- **Scalability** to billions of points
- **Real-time streaming** capabilities
- **Cost efficiency** through better resource utilization
# ChatGPT

 

* `cb_2020_us_state_500k.zip` = **US state boundaries** (generalized “cartographic boundary” polygons intended for mapping). ([Census.gov][1])
* `2020_Gaz_zcta_national.zip` = a **Gazetteer table for ZCTAs** (tabular attributes like GEOID, land/water area, centroid coords) — not polygon boundaries. If you need *ZIP/ZCTA polygons*, download `cb_2020_us_zcta520_500k.zip`. ([Census.gov][2])

Below is a Databricks-ready path that (1) uploads the files, (2) builds state + ZIP (ZCTA) lookup using polygons, and (3) creates a new view that enriches your point view (lon/lat) with `state` and `zip`.

---

# 0) Prereqs (Databricks Runtime & libs)

This solution uses \[Databricks Mosaic] for fast point-in-polygon. Install once per cluster (or put in an init script):

```python
# In a Python notebook cell
%pip install databricks-mosaic==0.4.0 shapely pyshp
```

Enable Mosaic in your session:

```python
from mosaic import enable_mosaic
enable_mosaic(spark, dbutils)
spark.sql("SET spark.databricks.labs.mosaic.enable=true")
```

Mosaic docs (point-in-polygon, geometry functions): ([Databricks][3])

---

# 1) Upload & unzip the Census files to DBFS

Use a notebook `%sh` cell (easiest) to fetch the **state** polygons and the **ZCTA** polygons:

```bash
# create folders
mkdir -p /dbfs/FileStore/geo/states
mkdir -p /dbfs/FileStore/geo/zcta

# download states (polygons)
wget -O /dbfs/FileStore/geo/states/cb_2020_us_state_500k.zip \
  https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_500k.zip

# download ZCTA polygons (not the Gazetteer)
wget -O /dbfs/FileStore/geo/zcta/cb_2020_us_zcta520_500k.zip \
  https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip

# unzip
unzip -o /dbfs/FileStore/geo/states/cb_2020_us_state_500k.zip -d /dbfs/FileStore/geo/states
unzip -o /dbfs/FileStore/geo/zcta/cb_2020_us_zcta520_500k.zip -d /dbfs/FileStore/geo/zcta
```

Why these files: cartographic boundary shapefiles are the Census’ generalized mapping layers (good for joins & maps). ZCTA shapefile contains the ZIP-like polygons; Gazetteer is tabular (no polygon geometry). ([Census.gov][4])

---

# 2) Read shapefiles (pure-Python) and register Delta tables

Databricks clusters typically don’t ship with GDAL/Fiona; we’ll read shapefiles via `pyshp` (pure Python), convert to WKT, then let Mosaic handle geometry.

```python
import shapefile  # pyshp
from shapely.geometry import shape as shapely_shape
from pyspark.sql import Row
from pyspark.sql import functions as F

def shp_to_wkt_rows(shp_folder, id_fields):
    """
    Read a shapefile folder (containing .shp/.dbf/.shx) and yield Rows with:
      - wkt: POLYGON/MULTIPOLYGON WKT in EPSG:4326
      - attributes in id_fields (subset of .fields)
    """
    # find the .shp file in folder
    import os
    shp_path = [os.path.join(shp_folder, f) for f in os.listdir(shp_folder) if f.endswith(".shp")][0]
    r = shapefile.Reader(shp_path)
    field_names = [f[0] for f in r.fields[1:]]  # skip DeletionFlag

    for sr in r.iterShapeRecords():
        geom = shapely_shape(sr.shape.__geo_interface__)
        wkt = geom.wkt
        rec = dict(zip(field_names, sr.record))
        yield Row(wkt=wkt, **{k: rec.get(k) for k in id_fields})

# Read STATES
state_rows = list(shp_to_wkt_rows(
    "/dbfs/FileStore/geo/states",
    id_fields=["STATEFP","STUSPS","NAME"]
))
df_states = spark.createDataFrame(state_rows)

# Read ZCTAs
zcta_rows = list(shp_to_wkt_rows(
    "/dbfs/FileStore/geo/zcta",
    id_fields=["ZCTA5CE20"]
))
df_zcta = spark.createDataFrame(zcta_rows)
```

Turn WKT into Mosaic geometries and save as Delta for repeated use:

```python
from mosaic import st_geomfromwkt

states_geo = df_states.withColumn("geom", st_geomfromwkt("wkt"))
zcta_geo   = df_zcta.withColumn("geom", st_geomfromwkt("wkt"))

states_geo.select("STATEFP","STUSPS","NAME","geom").write.mode("overwrite").saveAsTable("geo.states_2020_cb500k")
zcta_geo.select("ZCTA5CE20","geom").write.mode("overwrite").saveAsTable("geo.zcta_2020_cb500k")
```

---

# 3) Enrich your points view with `state` and `zip`

Assume your existing SQL view is named `points_view` with columns `longitude` and `latitude` (WGS84). We’ll build a new view that adds `state` and `zip` using point-in-polygon joins.

```sql
-- Create a temp view with a POINT geometry from lon/lat
CREATE OR REPLACE TEMP VIEW points_with_geom AS
SELECT
  *,
  mosaic.st_point(CAST(longitude AS DOUBLE), CAST(latitude AS DOUBLE)) AS geom
FROM points_view;

-- Enrich with STATE
CREATE OR REPLACE TEMP VIEW points_plus_state AS
SELECT
  p.*,
  s.STUSPS AS state,
  s.NAME   AS state_name
FROM points_with_geom p
LEFT JOIN geo.states_2020_cb500k s
  ON mosaic.st_contains(s.geom, p.geom);

-- Enrich with ZCTA (ZIP)
CREATE OR REPLACE VIEW points_plus_state_zip AS
SELECT
  ps.*,
  z.ZCTA5CE20 AS zip
FROM points_plus_state ps
LEFT JOIN geo.zcta_2020_cb500k z
  ON mosaic.st_contains(z.geom, ps.geom);
```

The resulting view `points_plus_state_zip` adds `state` (2-letter), `state_name`, and `zip` (ZCTA5CE20). Mosaic’s `st_contains`/`st_point` are designed for this pattern. ([Databricks Labs][5])

---

# 4) Notes, accuracy & performance

* **CRS**: Census cartographic boundary shapefiles are in geographic coordinates (WGS84). The above uses lon/lat directly (EPSG:4326), which is correct for these layers. ([Census.gov][4])
* **ZIP vs ZCTA**: The result is **ZCTA** (a Census ZIP-like area), not USPS ZIP routes. For analytics and mapping, ZCTAs are standard; for USPS mailing, use USPS data. ([Census.gov][6])
* **Ambiguity edges**: For a tiny number of points near borders, `st_contains` vs `st_intersects` can differ. If you want “on the border counts,” replace `st_contains` with `st_intersects`.
* **Speed**: If volume is big, pre-index with Mosaic’s H3 helpers (cover polygons → join on H3). See Mosaic quickstart for point-in-polygon via H3. ([Databricks Labs][7])

---

# 5) If you really want to use the Gazetteer ZCTA file

The Gazetteer is a **table**, not polygons. You could do an *approximate* ZIP lookup by nearest ZCTA **centroid** (fast, but less accurate than polygon PIP). 
Most folks prefer polygon PIP as shown above. Gazetteer record layout reference: ([Census.gov][2])

---


[1]: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html?utm_source=chatgpt.com "Cartographic Boundary Files"
[2]: https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.html?utm_source=chatgpt.com "Gazetteer File Record Layouts"
[3]: https://www.databricks.com/blog/2022/05/02/high-scale-geospatial-processing-with-mosaic.html?utm_source=chatgpt.com "High Scale Geospatial Processing Mosaic"
[4]: https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html?utm_source=chatgpt.com "Cartographic Boundary Files - Shapefile"
[5]: https://databrickslabs.github.io/mosaic/api/spatial-functions.html?utm_source=chatgpt.com "Spatial functions — Mosaic - GitHub Pages"
[6]: https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html?utm_source=chatgpt.com "ZIP Code Tabulation Areas (ZCTAs)"
[7]: https://databrickslabs.github.io/mosaic/usage/quickstart.html?utm_source=chatgpt.com "Quickstart notebook — Mosaic - GitHub Pages"




### Option A: Use Census TIGER/Cartographic files directly

* Download both:

  * **ZCTA shapefile** (`cb_2020_us_zcta520_500k.zip`)
  * **State shapefile** (`cb_2020_us_state_500k.zip`)
* Load them into a GIS tool or Python (e.g., `geopandas`).
* Perform a **spatial join**: for each ZCTA polygon, check which state polygon contains its centroid.
* Example (Python `geopandas`):

```python
import geopandas as gpd

# Load shapefiles
zcta = gpd.read_file("cb_2020_us_zcta520_500k.shp")
states = gpd.read_file("cb_2020_us_state_500k.shp")

# Ensure coordinate reference systems match
zcta = zcta.to_crs(states.crs)

# Use centroid of ZIP polygon
zcta['centroid'] = zcta.geometry.centroid

# Spatial join (point-in-polygon)
zcta_with_state = gpd.sjoin(
    gpd.GeoDataFrame(zcta, geometry=zcta['centroid']),
    states,
    how="left",
    op="within"
)

# Now you have ZIP → STATE mapping
print(zcta_with_state[['ZCTA5CE20', 'STATEFP', 'STUSPS', 'NAME']].head())
```

This gives you a clean table of ZIP (ZCTA5CE20) to state code (STUSPS).

---

### Option B: Use existing reference tables

If you don’t want to process shapefiles yourself:

* Census publishes **relationship files** (ZCTA-to-county, county-to-state).

  * `zcta_county_rel_10.txt` → maps each ZCTA to one or more counties.
  * Each county has a `STATEFP` (state FIPS code).
  * Join those and you get ZIP → State.

These are easier if you only need tabular lookups, not spatial work.

---

### Option C: Use APIs (simpler but not offline)

* [Census Geocoding API](https://geocoding.geo.census.gov/) → pass a ZIP, get the state.
* Many third-party services (e.g., USPS, Google Maps API) also return state for a ZIP.

---

✅ **Recommendation:**
If you’re already downloading the Census shapefiles, the cleanest approach is **Option B (relationship files)** if you want a flat lookup table, or **Option A (spatial join)** if you’re already doing GIS analysis.

Do you want me to put together a ready-to-use **lookup table ZIP → State (CSV)** from the Census relationship file, so you can skip GIS completely?


## **Option 1: Using Census Gazetteer CSV (RECOMMENDED)**

First, let's download and use the official Census Bureau ZIP code centroids data:

```sql
-- Step 1: Download the Census Gazetteer file
-- Go to: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
-- Download "ZIP Code Tabulation Areas" file (latest is 2020)
-- Upload the file to Databricks DBFS or your data lake

-- Step 2: Create ZIP codes reference table from the Census data
-- The Gazetteer file has columns: GEOID, ALAND, AWATER, ALAND_SQMI, AWATER_SQMI, INTPTLAT, INTPTLONG

CREATE OR REPLACE TABLE zip_code_centroids AS
SELECT 
  GEOID as zip_code,
  CAST(INTPTLAT AS DOUBLE) as latitude,
  CAST(INTPTLONG AS DOUBLE) as longitude,
  CAST(ALAND_SQMI AS DOUBLE) as land_area_sqmi
FROM read_files(
  'dbfs:/path/to/your/2020_Gaz_zcta_national.txt',
  format => 'csv',
  header => true,
  sep => '\t'  -- Census files are tab-separated
);

-- Step 3: Create function to find ZIP code for given coordinates
CREATE OR REPLACE FUNCTION find_zip_code(input_lat DOUBLE, input_lng DOUBLE)
RETURNS STRING
LANGUAGE SQL
AS $$
  SELECT zip_code
  FROM (
    SELECT 
      zip_code,
      -- Haversine distance formula (in miles)
      3959 * ACOS(
        GREATEST(-1, LEAST(1,
          COS(RADIANS(latitude)) * COS(RADIANS(input_lat)) * 
          COS(RADIANS(input_lng) - RADIANS(longitude)) + 
          SIN(RADIANS(latitude)) * SIN(RADIANS(input_lat))
        ))
      ) as distance_miles
    FROM zip_code_centroids
    ORDER BY distance_miles
    LIMIT 1
  )
$$;

-- Step 4: Add ZIP code detection to your existing trip data
CREATE OR REPLACE VIEW trip_data_with_zip AS
SELECT 
  td.*,
  find_zip_code(td.latitude, td.longitude) as zip_code
FROM trip_data td;

-- Step 5: Test the function with your sample coordinates
SELECT 
  latitude,
  longitude,
  find_zip_code(latitude, longitude) as detected_zip_code
FROM VALUES 
  (41.883758, -103.047944),
  (41.954183, -103.231843)
AS t(latitude, longitude);

-- Step 6: Enhanced version with distance threshold and multiple candidates
CREATE OR REPLACE VIEW trip_zip_analysis AS
WITH zip_distances AS (
  SELECT 
    td.car_id,
    td.trip_id,
    td.time,
    td.latitude,
    td.longitude,
    zc.zip_code,
    -- Calculate distance to each ZIP centroid
    3959 * ACOS(
      GREATEST(-1, LEAST(1,
        COS(RADIANS(zc.latitude)) * COS(RADIANS(td.latitude)) * 
        COS(RADIANS(td.longitude) - RADIANS(zc.longitude)) + 
        SIN(RADIANS(zc.latitude)) * SIN(RADIANS(td.latitude))
      ))
    ) as distance_miles,
    ROW_NUMBER() OVER (PARTITION BY td.car_id, td.trip_id, td.time ORDER BY 
      3959 * ACOS(
        GREATEST(-1, LEAST(1,
          COS(RADIANS(zc.latitude)) * COS(RADIANS(td.latitude)) * 
          COS(RADIANS(td.longitude) - RADIANS(zc.longitude)) + 
          SIN(RADIANS(zc.latitude)) * SIN(RADIANS(td.latitude))
        ))
      )
    ) as rank
  FROM trip_data td
  CROSS JOIN zip_code_centroids zc
)
SELECT 
  car_id,
  trip_id,
  time,
  latitude,
  longitude,
  zip_code,
  ROUND(distance_miles, 2) as distance_to_zip_miles,
  CASE 
    WHEN distance_miles <= 5 THEN 'HIGH_CONFIDENCE'
    WHEN distance_miles <= 15 THEN 'MEDIUM_CONFIDENCE'
    ELSE 'LOW_CONFIDENCE'
  END as confidence_level
FROM zip_distances
WHERE rank = 1;

-- Step 7: Aggregate trip analysis by ZIP code
SELECT 
  zip_code,
  COUNT(DISTINCT car_id) as unique_vehicles,
  COUNT(DISTINCT trip_id) as total_trips,
  COUNT(*) as total_gps_points,
  AVG(distance_to_zip_miles) as avg_distance_to_centroid,
  confidence_level
FROM trip_zip_analysis
GROUP BY zip_code, confidence_level
ORDER BY total_gps_points DESC;

```

## ** Option 2: Using Pre-built ZIP Code Table**

If you prefer to use existing data in Databricks
```sql
-- Option 2: Create a sample ZIP codes table with major US cities
-- This is a smaller dataset for testing/prototyping

CREATE OR REPLACE TABLE sample_zip_codes AS
SELECT * FROM VALUES
  ('10001', 40.7505, -73.9934, 'New York', 'NY'),
  ('90210', 34.0901, -118.4065, 'Beverly Hills', 'CA'), 
  ('60601', 41.8827, -87.6233, 'Chicago', 'IL'),
  ('77001', 29.7347, -95.3897, 'Houston', 'TX'),
  ('33101', 25.7839, -80.2102, 'Miami', 'FL'),
  ('02101', 42.3584, -71.0598, 'Boston', 'MA'),
  ('98101', 47.6089, -122.3356, 'Seattle', 'WA'),
  ('69101', 41.2565, -95.9345, 'Omaha', 'NE'),  -- Nebraska ZIP for your test data
  ('69001', 41.8781, -103.6647, 'Scottsbluff', 'NE'), -- Closer to your coordinates
  ('30301', 33.7907, -84.3733, 'Atlanta', 'GA')
AS t(zip_code, latitude, longitude, city, state);

-- Simple function for ZIP detection using sample data
CREATE OR REPLACE FUNCTION detect_zip_simple(input_lat DOUBLE, input_lng DOUBLE)
RETURNS STRUCT<zip_code: STRING, distance_miles: DOUBLE, city: STRING, state: STRING>
LANGUAGE SQL
AS $$
  SELECT STRUCT(
    zip_code,
    distance_miles,
    city,
    state
  )
  FROM (
    SELECT 
      zip_code,
      city,
      state,
      3959 * ACOS(
        GREATEST(-1, LEAST(1,
          COS(RADIANS(latitude)) * COS(RADIANS(input_lat)) * 
          COS(RADIANS(input_lng) - RADIANS(longitude)) + 
          SIN(RADIANS(latitude)) * SIN(RADIANS(input_lat))
        ))
      ) as distance_miles
    FROM sample_zip_codes
    ORDER BY distance_miles
    LIMIT 1
  )
$$;

-- Test with your coordinates
SELECT 
  latitude,
  longitude,
  detect_zip_simple(latitude, longitude).zip_code as zip_code,
  detect_zip_simple(latitude, longitude).distance_miles as distance_miles,
  detect_zip_simple(latitude, longitude).city as city,
  detect_zip_simple(latitude, longitude).state as state
FROM VALUES 
  (41.883758, -103.047944),
  (41.954183, -103.231843)
AS t(latitude, longitude);

-- Apply to your trip data
SELECT 
  car_id,
  trip_id,
  time,
  latitude,
  longitude,
  detect_zip_simple(latitude, longitude).zip_code as zip_code,
  detect_zip_simple(latitude, longitude).city as city,
  detect_zip_simple(latitude, longitude).state as state
FROM trip_data
LIMIT 10;
```

## **Step-by-Step Implementation Guide:**

### **1. Download Census Data**
```bash
# Download the latest ZIP Code Tabulation Areas file
wget https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_zcta_national.zip
```

### **2. Upload to Databricks**
```python
# Upload file to DBFS using Databricks File System
dbutils.fs.cp("file:/databricks/driver/2020_Gaz_zcta_national.txt", "dbfs:/data/zip_codes/")
```

### **3. Create the Tables**
Run the SQL from Option 1 above to create your ZIP code reference table.

### **4. Performance Optimization**
```sql
-- Create indexes for better performance
CREATE INDEX idx_zip_lat_lng ON zip_code_centroids (latitude, longitude);

-- Use Delta Lake for better performance
CREATE OR REPLACE TABLE zip_code_centroids
USING DELTA
AS SELECT * FROM your_imported_data;

-- Optimize table
OPTIMIZE zip_code_centroids;
```

## **Key Benefits:**

✅ **No external API calls** - All data stored locally  
✅ **Fast performance** - Simple distance calculations  
✅ **Authoritative data** - US Census Bureau official data  
✅ **Scalable** - Works with millions of coordinates  
✅ **Customizable** - Adjust distance thresholds and confidence levels  

## **Usage Examples:**

```sql
-- Add ZIP codes to your existing trip analysis
SELECT 
  car_id,
  COUNT(DISTINCT find_zip_code(latitude, longitude)) as zip_codes_visited,
  COLLECT_SET(find_zip_code(latitude, longitude)) as zip_list
FROM trip_data
GROUP BY car_id;
```

The Census Gazetteer approach gives you ~33,000 ZIP codes with official coordinates. For production use, I recommend Option 1 with the full Census dataset!





# **Reverse geocoding** with static datasets.

<https://austinhenley.com/blog/coord2state.html>

Here are the best approaches for detecting states and cities from lat/lon coordinates without external APIs:

## 1. State Detection - Recommended Datasets

### Option A: Natural Earth Data (Recommended)
**Dataset**: US States boundaries in GeoJSON/Shapefile format
- **Source**: https://www.naturalearthdata.com/downloads/50m-cultural-vectors/
- **File**: `ne_50m_admin_1_states_provinces_lakes.zip`
- **Format**: Shapefile or GeoJSON with state polygons
- **Size**: ~2MB
- **Accuracy**: Very high, official boundaries

### Option B: US Census Bureau TIGER/Line
**Dataset**: State boundary files
- **Source**: https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
- **File**: State boundaries (cb_2023_us_state_20m.zip)
- **Format**: Shapefile
- **Size**: ~5MB
- **Accuracy**: Official US government data

## 2. City Detection - Recommended Datasets

### Option A: SimpleMaps US Cities Database
**Dataset**: US Cities with lat/lon coordinates
- **Source**: https://simplemaps.com/data/us-cities (Free basic version available)
- **Format**: CSV with columns: city, state, lat, lng, population
- **Size**: ~1MB for 30K+ cities
- **Coverage**: All US cities with population data

### Option B: GeoNames US Cities
**Dataset**: Free geographical database
- **Source**: https://download.geonames.org/export/dump/ (US.zip)
- **Format**: Tab-delimited text file
- **Size**: ~50MB (includes all US geographic features)
- **Coverage**: Comprehensive, includes cities, towns, villages


## 4. Implementation Steps

### Step 1: Download and Upload Datasets

1. **Download US Cities CSV** from SimpleMaps:
   - Go to https://simplemaps.com/data/us-cities
   - Download the free version (uscities.csv)

2. **Upload to Databricks**:
   ```python
   # In Databricks notebook
   dbutils.fs.cp("file:/FileStore/shared_uploads/uscities.csv", "/FileStore/tables/us_cities.csv")
   ```

### Step 2: Alternative - Create Simple State Bounds Table

If you want a lightweight approach for states only:## 5. Performance Optimization Tips

1. **Index your reference tables**:
   ```sql
   CREATE INDEX idx_cities_lat_lng ON us_cities (city_lat, city_lng);
   ```

2. **Use bounding box filters** to reduce computation:
   - Filter cities within ±2 degrees lat/lng before calculating distance
   - This dramatically reduces the search space

3. **Consider data partitioning**:
   - Partition reference tables by region/state for faster lookups

## 6. Accuracy Considerations

- **State detection**: Bounding boxes are ~95% accurate (issues near state borders)
- **City detection**: Depends on dataset completeness and distance threshold
- **Border cases**: Points near state/city boundaries may be misclassified

