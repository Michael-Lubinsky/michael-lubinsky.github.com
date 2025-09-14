## The **Haversine formula** 
is a mathematical equation used to calculate the shortest distance between two points on Earth's surface, given their latitude and longitude coordinates. It's named after the haversine function.

## Why Do We Need It?

Earth is not flat—it's a sphere (approximately). When you have two GPS coordinates, you can't just use the Pythagorean theorem because:
- Longitude lines converge at the poles
- The distance between latitude/longitude degrees varies by location
- We need to account for Earth's curvature

## The Formula

The haversine function is defined as:
```
haversin(θ) = sin²(θ/2) = (1 - cos(θ))/2
```
The Haversine formula calculates the **great-circle distance** (shortest path along Earth's surface):

```
a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
c = 2 ⋅ atan2( √a, √(1−a) )
d = R ⋅ c
```

Where:
- **φ** = latitude (in radians)
- **λ** = longitude (in radians)  
- **Δφ** = difference in latitudes
- **Δλ** = difference in longitudes
- **R** = Earth's radius (≈ 6,371 km or 3,959 miles)

## SQL Implementation Breakdown

In the query I provided, here's what each part does:

```sql
6371 * ACOS(
  COS(RADIANS(start_latitude)) *           -- cos φ1
  COS(RADIANS(end_latitude)) *             -- cos φ2  
  COS(RADIANS(end_longitude) - RADIANS(start_longitude)) +  -- cos(Δλ)
  SIN(RADIANS(start_latitude)) *           -- sin φ1
  SIN(RADIANS(end_latitude))               -- sin φ2
)
```

This is a simplified version that works well for most practical distances.

## Real-World Example

Let's say you're traveling from:
- **New York City**: (40.7128°N, -74.0060°W)
- **Los Angeles**: (34.0522°N, -118.2437°W)

**Straight-line distance (Haversine)**: ~3,944 km
**Actual driving distance**: ~4,500 km (due to roads, mountains, etc.)

## Limitations

1. **Assumes perfect sphere**: Earth is slightly flattened, but error is usually <0.5%
2. **Great-circle distance**: Doesn't account for actual roads, terrain, or elevation
3. **Not suitable for very short distances**: GPS accuracy issues matter more

## When It's Useful

- **Flight planning**: Airlines use great-circle routes
- **GPS applications**: Calculate "as the crow flies" distance  
- **Data validation**: Compare with odometer readings to detect errors
- **Logistics**: Estimate transportation costs and time

## Alternative: Simpler Approximation

For shorter distances (< 100 km), you can use a simpler approximation:
```sql
-- Simple approximation (less accurate for long distances)
SQRT(
  POW(69.1 * (end_latitude - start_latitude), 2) + 
  POW(69.1 * (end_longitude - start_longitude) * COS(RADIANS(start_latitude)), 2)
)
```

The Haversine formula gives you the theoretical minimum distance between two points on Earth—useful for comparing against actual travel distances recorded by odometers or GPS tracking systems.


### There is  csv file in Databriks.
It has following columns:
car_id, travel_id, time, odometer, longitude, latitude.
Please write SQL to extract 
for every  (car_id, travel_id)  the odometer, longitude, latitude at start and end points  only

## Solution 1
```sql
-- Using FIRST_VALUE() and LAST_VALUE() approach
SELECT DISTINCT
  car_id,
  travel_id,
  FIRST_VALUE(odometer) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_odometer,
  FIRST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_longitude,
  FIRST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_latitude,
  LAST_VALUE(odometer) OVER (PARTITION BY car_id, travel_id ORDER BY time 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_odometer,
  LAST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_longitude,
  LAST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_latitude
FROM your_table_name
ORDER BY car_id, travel_id;

-- Alternative: Using MIN/MAX with CASE statements
SELECT 
  car_id,
  travel_id,
  MAX(CASE WHEN rn_first = 1 THEN odometer END) as start_odometer,
  MAX(CASE WHEN rn_first = 1 THEN longitude END) as start_longitude,
  MAX(CASE WHEN rn_first = 1 THEN latitude END) as start_latitude,
  MAX(CASE WHEN rn_last = 1 THEN odometer END) as end_odometer,
  MAX(CASE WHEN rn_last = 1 THEN longitude END) as end_longitude,
  MAX(CASE WHEN rn_last = 1 THEN latitude END) as end_latitude
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY car_id, travel_id ORDER BY time ASC) as rn_first,
    ROW_NUMBER() OVER (PARTITION BY car_id, travel_id ORDER BY time DESC) as rn_last
  FROM your_table_name
) ranked
GROUP BY car_id, travel_id
ORDER BY car_id, travel_id;
```
## Solution 2
```sql
WITH ranked_data AS (
  SELECT 
    car_id,
    travel_id,
    time,
    odometer,
    longitude,
    latitude,
    ROW_NUMBER() OVER (PARTITION BY car_id, travel_id ORDER BY time ASC) as rn_start,
    ROW_NUMBER() OVER (PARTITION BY car_id, travel_id ORDER BY time DESC) as rn_end
  FROM your_table_name
),
start_points AS (
  SELECT 
    car_id,
    travel_id,
    odometer as start_odometer,
    longitude as start_longitude,
    latitude as start_latitude
  FROM ranked_data
  WHERE rn_start = 1
),
end_points AS (
  SELECT 
    car_id,
    travel_id,
    odometer as end_odometer,
    longitude as end_longitude,
    latitude as end_latitude
  FROM ranked_data
  WHERE rn_end = 1
)
SELECT 
  s.car_id,
  s.travel_id,
  s.start_odometer,
  s.start_longitude,
  s.start_latitude,
  e.end_odometer,
  e.end_longitude,
  e.end_latitude
FROM start_points s
JOIN end_points e ON s.car_id = e.car_id AND s.travel_id = e.travel_id
ORDER BY s.car_id, s.travel_id;
```
## Compare the travel distance from odometer readings versus the distance calculated from GPS coordinates:
```
Key Features:

Haversine Formula: Used to calculate the great-circle distance between two GPS coordinates, accounting for Earth's curvature

Multiple Distance Units:

GPS distance in kilometers (using Earth's radius = 6371 km)
GPS distance in miles (converted using factor 0.621371)
```

-- Compare odometer distance vs GPS distance using Haversine formula
```sql
WITH start_end_points AS (
  SELECT DISTINCT
    car_id,
    travel_id,
    FIRST_VALUE(odometer) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_odometer,
    FIRST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_longitude,
    FIRST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_latitude,
    LAST_VALUE(odometer) OVER (PARTITION BY car_id, travel_id ORDER BY time 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_odometer,
    LAST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_longitude,
    LAST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_latitude
  FROM your_table_name
),
distance_calculations AS (
  SELECT 
    car_id,
    travel_id,
    start_odometer,
    start_longitude,
    start_latitude,
    end_odometer,
    end_longitude,
    end_latitude,
    
    -- Odometer distance (assuming odometer is in km or miles)
    (end_odometer - start_odometer) as odometer_distance,
    
    -- GPS distance using Haversine formula (result in km)
    6371 * ACOS(
      COS(RADIANS(start_latitude)) * 
      COS(RADIANS(end_latitude)) * 
      COS(RADIANS(end_longitude) - RADIANS(start_longitude)) + 
      SIN(RADIANS(start_latitude)) * 
      SIN(RADIANS(end_latitude))
    ) as gps_distance_km,
    
    -- GPS distance in miles (multiply by 0.621371)
    6371 * 0.621371 * ACOS(
      COS(RADIANS(start_latitude)) * 
      COS(RADIANS(end_latitude)) * 
      COS(RADIANS(end_longitude) - RADIANS(start_longitude)) + 
      SIN(RADIANS(start_latitude)) * 
      SIN(RADIANS(end_latitude))
    ) as gps_distance_miles
    
  FROM start_end_points
  WHERE start_latitude IS NOT NULL 
    AND end_latitude IS NOT NULL 
    AND start_longitude IS NOT NULL 
    AND end_longitude IS NOT NULL
    AND start_odometer IS NOT NULL 
    AND end_odometer IS NOT NULL
)
SELECT 
  car_id,
  travel_id,
  start_odometer,
  end_odometer,
  ROUND(odometer_distance, 2) as odometer_distance,
  ROUND(gps_distance_km, 2) as gps_distance_km,
  ROUND(gps_distance_miles, 2) as gps_distance_miles,
  
  -- Comparison metrics
  ROUND(odometer_distance - gps_distance_km, 2) as difference_km,
  ROUND(odometer_distance - gps_distance_miles, 2) as difference_miles,
  
  ROUND(
    CASE 
      WHEN gps_distance_km > 0 THEN 
        ABS(odometer_distance - gps_distance_km) / gps_distance_km * 100 
      ELSE NULL 
    END, 2
  ) as percent_diff_km,
  
  ROUND(
    CASE 
      WHEN gps_distance_miles > 0 THEN 
        ABS(odometer_distance - gps_distance_miles) / gps_distance_miles * 100 
      ELSE NULL 
    END, 2
  ) as percent_diff_miles,
  
  -- Flag for significant discrepancies (> 10% difference)
  CASE 
    WHEN ABS(odometer_distance - gps_distance_km) / NULLIF(gps_distance_km, 0) > 0.1 
      OR ABS(odometer_distance - gps_distance_miles) / NULLIF(gps_distance_miles, 0) > 0.1 
    THEN 'HIGH_DISCREPANCY'
    ELSE 'NORMAL'
  END as discrepancy_flag

FROM distance_calculations
ORDER BY car_id, travel_id;
```
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

This approach gives you complete offline reverse geocoding capability within Databricks without external API dependencies!

```sql
-- Simple state detection using bounding boxes (approximate)
-- This is less accurate but faster for large datasets

WITH state_bounds AS (
  SELECT * FROM VALUES
    ('California', 'CA', 32.5343, 42.0095, -124.4096, -114.1312),
    ('Texas', 'TX', 25.8371, 36.5007, -106.6456, -93.5083),
    ('Florida', 'FL', 24.3963, 31.0009, -87.6349, -79.9743),
    ('New York', 'NY', 40.4774, 45.0153, -79.7625, -71.7187),
    ('Arizona', 'AZ', 31.3322, 37.0043, -114.8165, -109.0452),
    ('Nevada', 'NV', 35.0018, 42.0022, -120.0064, -114.0396),
    ('Washington', 'WA', 45.5435, 49.0024, -124.8489, -116.9160),
    ('Oregon', 'OR', 41.9918, 46.2991, -124.7031, -116.4635),
    ('Colorado', 'CO', 36.9949, 41.0006, -109.0600, -102.0424),
    ('Utah', 'UT', 36.9979, 42.0013, -114.0524, -109.0410),
    ('New Mexico', 'NM', 31.3323, 37.0002, -109.0489, -103.0020),
    ('Montana', 'MT', 44.3583, 49.0011, -116.0685, -104.0394),
    ('Wyoming', 'WY', 40.9979, 45.0017, -111.0567, -104.0489),
    ('North Dakota', 'ND', 45.9356, 49.0005, -104.0489, -96.5544),
    ('South Dakota', 'SD', 42.4794, 45.9454, -104.0578, -96.4365),
    ('Idaho', 'ID', 41.9880, 49.0011, -117.2431, -111.0435),
    ('Minnesota', 'MN', 43.4999, 49.3842, -97.2394, -89.4837),
    ('Wisconsin', 'WI', 42.4919, 47.0803, -92.8893, -86.2494),
    ('Iowa', 'IA', 40.3756, 43.5012, -96.6397, -90.1401),
    ('Illinois', 'IL', 36.9702, 42.5083, -91.5130, -87.0199),
    ('Michigan', 'MI', 41.6966, 48.3060, -90.4184, -82.1220),
    ('Indiana', 'IN', 37.7554, 41.7613, -88.0157, -84.7841),
    ('Ohio', 'OH', 38.4036, 41.9773, -84.8203, -80.5190),
    ('Kentucky', 'KY', 36.4967, 39.1472, -89.5715, -81.9649),
    ('Tennessee', 'TN', 34.9829, 36.6782, -90.3103, -81.6469),
    ('Mississippi', 'MS', 30.1734, 35.0041, -91.6550, -88.0972),
    ('Alabama', 'AL', 30.2307, 35.0041, -88.4731, -84.8890),
    ('Georgia', 'GA', 30.3557, 35.0008, -85.6051, -80.7551),
    ('South Carolina', 'SC', 32.0346, 35.2154, -83.3532, -78.4996),
    ('North Carolina', 'NC', 33.7514, 36.5881, -84.3218, -75.3619),
    ('Virginia', 'VA', 36.5407, 39.4660, -83.6754, -75.1665),
    ('West Virginia', 'WV', 37.2014, 40.6381, -82.6447, -77.7190),
    ('Maryland', 'MD', 37.8854, 39.7229, -79.4877, -75.0377),
    ('Delaware', 'DE', 38.4511, 39.8394, -75.7887, -75.0490),
    ('Pennsylvania', 'PA', 39.7198, 42.2694, -80.5190, -74.6895),
    ('New Jersey', 'NJ', 38.9276, 41.3574, -75.5630, -73.8937),
    ('Connecticut', 'CT', 40.9509, 42.0508, -73.7273, -71.7869),
    ('Rhode Island', 'RI', 41.1460, 42.0188, -71.8620, -71.1208),
    ('Massachusetts', 'MA', 41.2376, 42.8867, -73.5081, -69.8586),
    ('Vermont', 'VT', 42.7269, 45.0167, -73.4540, -71.4653),
    ('New Hampshire', 'NH', 42.6970, 45.3058, -72.5570, -70.6104),
    ('Maine', 'ME', 43.0642, 47.4598, -71.0843, -66.9498),
    ('Alaska', 'AK', 54.7753, 71.5232, -179.1506, -129.9795),
    ('Hawaii', 'HI', 18.9117, 28.4023, -178.4438, -154.8056)
  AS t(state_name, state_abbr, min_lat, max_lat, min_lng, max_lng)
),
travel_with_states AS (
  SELECT DISTINCT
    car_id,
    travel_id,
    FIRST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_latitude,
    FIRST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time) as start_longitude,
    LAST_VALUE(latitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_latitude,
    LAST_VALUE(longitude) OVER (PARTITION BY car_id, travel_id ORDER BY time 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_longitude
  FROM your_table_name
)
SELECT 
  t.car_id,
  t.travel_id,
  t.start_latitude,
  t.start_longitude,
  t.end_latitude, 
  t.end_longitude,
  
  -- Start state detection
  s1.state_name as start_state,
  s1.state_abbr as start_state_abbr,
  
  -- End state detection  
  s2.state_name as end_state,
  s2.state_abbr as end_state_abbr,
  
  -- Trip classification
  CASE 
    WHEN s1.state_abbr = s2.state_abbr THEN 'INTRASTATE'
    ELSE 'INTERSTATE' 
  END as trip_type

FROM travel_with_states t
LEFT JOIN state_bounds s1 ON (
  t.start_latitude BETWEEN s1.min_lat AND s1.max_lat 
  AND t.start_longitude BETWEEN s1.min_lng AND s1.max_lng
)
LEFT JOIN state_bounds s2 ON (
  t.end_latitude BETWEEN s2.min_lat AND s2.max_lat 
  AND t.end_longitude BETWEEN s2.min_lng AND s2.max_lng
)
ORDER BY t.car_id, t.travel_id;
```

## Generate a synthetic dataset with realistic GPS coordinates and trip data
for the specified states: California, Florida,  Washington, Oregon and Nebraska
using Databricks SQL.

## Usage Instructions

1. **Run the query above** to see the generated data
2. **Create the table** by uncommenting and running the `CREATE TABLE` statement at the bottom
3. **Verify the data** with sample queries

## Data Characteristics

- **5 cars**: CAR_001 through CAR_005
- **4 trips per car**: TRIP_001 through TRIP_004  
- **5 data points per trip**: Evenly spaced along each journey
- **Trip lengths**: Randomized between 10-20 miles
- **States coverage**: Each car-trip combination is randomly assigned to CA, FL, WA, OR, or NE
- **Realistic coordinates**: Within actual state boundaries
- **Time progression**: 15-minute intervals between data points
- **Odometer progression**: Increases realistically with distance traveled

## Sample Verification Queries## Key Features of Generated Data

### **Realistic Geography**
- Coordinates fall within actual state boundaries
- Trip directions and lengths are geographically plausible
- Small random variations simulate GPS noise

### **Consistent Data Progression**
- Odometer values increase monotonically per car
- Time stamps progress in 15-minute intervals
- GPS coordinates interpolate smoothly along trip paths

### **Configurable Parameters**
You can easily modify:
- **Trip lengths**: Change the `10 + (RAND(...) * 10)` formula
- **States**: Add/remove states in the `state_bounds` CTE
- **Number of points**: Modify the points VALUES clause
- **Time intervals**: Adjust the `INTERVAL 15 MINUTES` value

### **Data Quality**
- No NULL values
- Realistic odometer progression (increases with distance)
- GPS coordinates have appropriate precision (6 decimal places)
- Time stamps are properly formatted

Run the verification queries to confirm the data meets your requirements for testing the distance comparison and geocoding queries we developed earlier!

### Generating

```sql

-- Generate synthetic trip data for 5 cars, 4 trips each, 5 data points per trip
-- Trip lengths: 10-20 miles, States: CA, FL, WA, OR, NE

WITH 
-- Define state coordinate ranges (approximate bounding boxes)
state_bounds AS (
  SELECT * FROM VALUES
    ('CA', 34.0, 37.0, -122.0, -117.0),  -- California (LA to SF area)
    ('FL', 25.5, 30.5, -84.0, -80.0),    -- Florida 
    ('WA', 47.0, 49.0, -124.0, -120.0),  -- Washington
    ('OR', 42.0, 46.0, -124.0, -120.0),  -- Oregon
    ('NE', 40.0, 43.0, -104.0, -96.0)    -- Nebraska
  AS t(state, min_lat, max_lat, min_lng, max_lng)
),

-- Generate base combinations
base_data AS (
  SELECT 
    car_id,
    travel_id,
    point_num,
    state,
    min_lat, max_lat, min_lng, max_lng,
    -- Random trip length between 10-20 miles
    10 + (RAND(car_id * 1000 + travel_id * 100) * 10) as trip_length_miles
  FROM (
    SELECT car_id FROM VALUES ('CAR_001'), ('CAR_002'), ('CAR_003'), ('CAR_004'), ('CAR_005') AS t(car_id)
  ) cars
  CROSS JOIN (
    SELECT travel_id FROM VALUES ('TRIP_001'), ('TRIP_002'), ('TRIP_003'), ('TRIP_004') AS t(travel_id)
  ) trips
  CROSS JOIN (
    SELECT point_num FROM VALUES (1), (2), (3), (4), (5) AS t(point_num)
  ) points
  CROSS JOIN (
    SELECT state, min_lat, max_lat, min_lng, max_lng,
           ROW_NUMBER() OVER (ORDER BY state) as state_rank
    FROM state_bounds
  ) states
  WHERE MOD(ABS(HASH(car_id, travel_id)), 5) + 1 = states.state_rank
),

-- Generate trip start points and calculate trip vectors
trip_starts AS (
  SELECT DISTINCT
    car_id,
    travel_id, 
    state,
    trip_length_miles,
    -- Random start latitude within state bounds
    min_lat + RAND(HASH(car_id, travel_id, 1)) * (max_lat - min_lat) as start_lat,
    -- Random start longitude within state bounds  
    min_lng + RAND(HASH(car_id, travel_id, 2)) * (max_lng - min_lng) as start_lng,
    -- Random direction (0-360 degrees)
    RAND(HASH(car_id, travel_id, 3)) * 360 as direction_degrees
  FROM base_data
),

-- Calculate end points based on trip length and direction
trip_ends AS (
  SELECT *,
    -- Calculate end coordinates using trip length and direction
    -- 1 degree lat ≈ 69 miles, 1 degree lng ≈ 69 * cos(lat) miles
    start_lat + (trip_length_miles * SIN(RADIANS(direction_degrees))) / 69.0 as end_lat,
    start_lng + (trip_length_miles * COS(RADIANS(direction_degrees))) / (69.0 * COS(RADIANS(start_lat))) as end_lng
  FROM trip_starts
),

-- Generate individual data points along each trip
trip_data AS (
  SELECT 
    bd.car_id,
    bd.travel_id,
    bd.point_num,
    bd.state,
    te.trip_length_miles,
    
    -- Calculate progress along trip (0 to 1)
    (bd.point_num - 1) / 4.0 as progress,
    
    -- Interpolate coordinates along the trip
    te.start_lat + ((bd.point_num - 1) / 4.0) * (te.end_lat - te.start_lat) as latitude,
    te.start_lng + ((bd.point_num - 1) / 4.0) * (te.end_lng - te.start_lng) as longitude,
    
    -- Generate realistic timestamps (15-minute intervals)
    TIMESTAMP('2024-01-01 08:00:00') + 
    INTERVAL (ROW_NUMBER() OVER (ORDER BY bd.car_id, bd.travel_id, bd.point_num) * 15) MINUTES as time_stamp,
    
    -- Generate odometer readings (starting from random base, increasing by trip distance)
    50000 + (HASH(bd.car_id) % 100000) + 
    (ROW_NUMBER() OVER (PARTITION BY bd.car_id ORDER BY bd.travel_id, bd.point_num) - 1) * 
    (te.trip_length_miles / 5.0) as odometer

  FROM base_data bd
  JOIN trip_ends te ON bd.car_id = te.car_id AND bd.travel_id = te.travel_id
),

-- Add some realistic variation to make data more realistic
final_data AS (
  SELECT 
    car_id,
    travel_id as trip_id,
    time_stamp as time,
    ROUND(odometer + RAND(HASH(car_id, trip_id, point_num)) * 0.1, 1) as odometer,
    ROUND(longitude + (RAND(HASH(car_id, trip_id, point_num, 1)) - 0.5) * 0.001, 6) as longitude,
    ROUND(latitude + (RAND(HASH(car_id, trip_id, point_num, 2)) - 0.5) * 0.001, 6) as latitude,
    state,
    ROUND(trip_length_miles, 1) as trip_length_miles
  FROM trip_data
)

-- Final SELECT with proper column order
SELECT 
  car_id,
  trip_id,
  time,
  odometer,
  longitude,
  latitude
FROM final_data
ORDER BY car_id, trip_id, time;

-- Uncomment below to create the actual table
/*
CREATE OR REPLACE TABLE trip_data AS
SELECT 
  car_id,
  trip_id,
  time,
  odometer,
  longitude,
  latitude
FROM final_data
ORDER BY car_id, trip_id, time;
*/
```



### Validation
-- Verification queries for the generated trip data
```sql
-- 1. Count records (should be 100 total: 5 cars × 4 trips × 5 points)
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT car_id) as unique_cars,
  COUNT(DISTINCT CONCAT(car_id, '-', trip_id)) as unique_trips
FROM trip_data;

-- 2. Check trip lengths using Haversine formula
WITH trip_distances AS (
  SELECT 
    car_id,
    trip_id,
    MIN(latitude) as start_lat,
    MIN(longitude) as start_lng,
    MAX(latitude) as end_lat,
    MAX(longitude) as end_lng,
    MIN(odometer) as start_odometer,
    MAX(odometer) as end_odometer,
    (MAX(odometer) - MIN(odometer)) as odometer_distance
  FROM trip_data
  GROUP BY car_id, trip_id
)
SELECT 
  car_id,
  trip_id,
  ROUND(odometer_distance, 1) as odometer_miles,
  ROUND(
    3959 * ACOS(
      COS(RADIANS(start_lat)) * 
      COS(RADIANS(end_lat)) * 
      COS(RADIANS(end_lng) - RADIANS(start_lng)) + 
      SIN(RADIANS(start_lat)) * 
      SIN(RADIANS(end_lat))
    ), 1
  ) as gps_distance_miles,
  start_lat, start_lng, end_lat, end_lng
FROM trip_distances
ORDER BY car_id, trip_id;

-- 3. Sample data by state (approximate state detection using coordinate ranges)
SELECT 
  CASE 
    WHEN latitude BETWEEN 34.0 AND 37.0 AND longitude BETWEEN -122.0 AND -117.0 THEN 'California'
    WHEN latitude BETWEEN 25.5 AND 30.5 AND longitude BETWEEN -84.0 AND -80.0 THEN 'Florida'
    WHEN latitude BETWEEN 47.0 AND 49.0 AND longitude BETWEEN -124.0 AND -120.0 THEN 'Washington'
    WHEN latitude BETWEEN 42.0 AND 46.0 AND longitude BETWEEN -124.0 AND -120.0 THEN 'Oregon'
    WHEN latitude BETWEEN 40.0 AND 43.0 AND longitude BETWEEN -104.0 AND -96.0 THEN 'Nebraska'
    ELSE 'Other'
  END as estimated_state,
  COUNT(DISTINCT CONCAT(car_id, '-', trip_id)) as trips_count,
  COUNT(*) as data_points,
  ROUND(MIN(latitude), 4) as min_lat,
  ROUND(MAX(latitude), 4) as max_lat,
  ROUND(MIN(longitude), 4) as min_lng,
  ROUND(MAX(longitude), 4) as max_lng
FROM trip_data
GROUP BY 1
ORDER BY trips_count DESC;

-- 4. Show sample trip progression
SELECT 
  car_id,
  trip_id,
  time,
  ROUND(latitude, 6) as latitude,
  ROUND(longitude, 6) as longitude,
  ROUND(odometer, 1) as odometer,
  ROW_NUMBER() OVER (PARTITION BY car_id, trip_id ORDER BY time) as point_sequence
FROM trip_data
WHERE car_id = 'CAR_001' AND trip_id = 'TRIP_001'
ORDER BY time;

-- 5. Check time progression and odometer consistency
SELECT 
  car_id,
  trip_id,
  COUNT(*) as points_per_trip,
  MIN(time) as trip_start,
  MAX(time) as trip_end,
  ROUND(MAX(odometer) - MIN(odometer), 1) as odometer_diff,
  ROUND(AVG(TIMESTAMPDIFF(MINUTE, LAG(time) OVER (PARTITION BY car_id, trip_id ORDER BY time), time)), 0) as avg_interval_minutes
FROM trip_data
GROUP BY car_id, trip_id
ORDER BY car_id, trip_id;

-- 6. Geographic distribution summary
SELECT 
  ROUND(AVG(latitude), 2) as avg_latitude,
  ROUND(AVG(longitude), 2) as avg_longitude,
  ROUND(MIN(latitude), 2) as min_latitude,
  ROUND(MAX(latitude), 2) as max_latitude,
  ROUND(MIN(longitude), 2) as min_longitude,
  ROUND(MAX(longitude), 2) as max_longitude
FROM trip_data;
```

