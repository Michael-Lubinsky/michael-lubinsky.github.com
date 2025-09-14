# Here's how to implement ZIP code detection in Databricks using static data files:

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

## 3. Implementation Strategy## 4. Implementation Steps

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

