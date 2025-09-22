# Here's how to implement ZIP code detection in Databricks using static data files:

<https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2020.html>

<https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_500k.zip>  State code boundaries

<https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_zcta_national.zip>  Zip boundaries

You’ve got two pieces here:

1. **The Census ZIP Code Tabulation Areas (ZCTAs)**

   * ZCTAs are generalized areal representations of U.S. ZIP Code service areas.
   * They’re available as shapefiles (`.shp`) or KML (`.kml`) from the Census site you linked.

2. **Finding the state for a ZIP (ZCTA)**
   Since ZCTAs are polygons, the state can be derived in a couple of ways:


## Claude
I can help you work with these shapefiles and create a view in Databricks. However, I need to clarify something about your files first:

Looking at the URLs you provided:
- **File 1** (`cb_2020_us_state_500k.zip`) is actually **state boundaries**, not ZIP code boundaries (as indicated by "us_state" in the filename)
- **File 2** (`2020_Gaz_zcta_national.zip`) is **ZIP Code Tabulation Area (ZCTA) data**, which is ZIP code-related data, not state boundaries

Now, let me walk you through the process of uploading these files to Databricks and creating the enhanced view:The guide above provides a comprehensive approach to solving your problem. Here are the key points:


2. **Upload Methods**: You can either upload via the Databricks UI or download directly in a notebook using wget.

3. **Processing Approach**: The solution uses spatial joins to match longitude/latitude points with both state boundaries and ZIP code areas.

4. **Two Implementation Options**:
   - **SQL-based**: Uses Databricks' spatial functions (recommended for performance)
   - **Python UDF**: More flexible but potentially slower

The enhanced view will add two new columns (`ZIP` and `state`) to your original view based on the spatial location of each longitude/latitude pair.


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
wget -O /tmp/zcta.zip https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_zcta_national.zip

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

# Load ZCTA (ZIP code) data - this is a text file, not shapefile
import pandas as pd
zcta_df = pd.read_csv('/dbfs/FileStore/tables/zcta.zip', sep='\t', compression='zip')
print("ZCTA data shape:", zcta_df.shape)
print("ZCTA columns:", zcta_df.columns.tolist())
```

## Step 3: Prepare Data for Spatial Joins

### Convert to Spark DataFrames
```python
# Convert states GeoDataFrame to regular DataFrame with geometry as WKT
states_df = states_gdf.copy()
states_df['geometry_wkt'] = states_df['geometry'].apply(lambda x: x.wkt)
states_spark = spark.createDataFrame(states_df.drop('geometry', axis=1))

# Convert ZCTA to Spark DataFrame
zcta_spark = spark.createDataFrame(zcta_df)

# Register as temporary views
states_spark.createOrReplaceTempView("states_boundaries")
zcta_spark.createOrReplaceTempView("zcta_data")
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

-- Join with ZCTA data to get ZIP codes
-- Note: ZCTA provides approximate ZIP code areas
final_result AS (
  SELECT 
    sj.*,
    zd.GEOID as zip_code,
    -- Calculate distance to find nearest ZIP if point is not within any ZCTA
    ST_Distance(
      ST_Point(sj.longitude, sj.latitude),
      ST_Point(zd.INTPTLON, zd.INTPTLAT)
    ) as zip_distance
  FROM state_joined sj
  LEFT JOIN zcta_data zd 
    ON ST_DWithin(
      ST_Point(sj.longitude, sj.latitude),
      ST_Point(zd.INTPTLON, zd.INTPTLAT),
      0.1  -- Within ~0.1 degree radius (approximately 11km)
    )
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
  * EXCEPT (longitude, latitude, zip_code, state_code, state_name, point_geom, zip_distance)
  
FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY longitude, latitude 
      ORDER BY zip_distance ASC
    ) as rn
  FROM final_result
) ranked
WHERE rn = 1;  -- Keep only the closest ZIP code for each point
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
        
        # Find nearest ZIP (using ZCTA centroids)
        if not zcta_df.empty:
            distances = ((zcta_df['INTPTLON'] - lon)**2 + (zcta_df['INTPTLAT'] - lat)**2)**0.5
            nearest_idx = distances.idxmin()
            zip_code = zcta_df.loc[nearest_idx, 'GEOID']
        else:
            zip_code = None
            
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
   - File 1 contains **state boundaries**, not ZIP codes
   - File 2 contains **ZCTA (ZIP Code Tabulation Areas)** data with centroids

2. **Performance Considerations**:
   - Spatial joins can be expensive; consider partitioning by state if you have large datasets
   - For production use, consider using Databricks' built-in geospatial functions or Delta Lake with spatial indexing

3. **Accuracy**:
   - ZCTA boundaries are approximations of ZIP code areas
   - Some points may fall outside defined boundaries (ocean, remote areas)
   - The nearest ZIP approach provides a reasonable fallback

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


# ChatGPT

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

