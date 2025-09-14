## The **Haversine formula** 
is a mathematical equation used to calculate the shortest distance between two points on Earth's surface, given their latitude and longitude coordinates. It's named after the haversine function.

## Why Do We Need It?

Earth is not flat—it's a sphere (approximately). When you have two GPS coordinates, you can't just use the Pythagorean theorem because:
- Longitude lines converge at the poles
- The distance between latitude/longitude degrees varies by location
- We need to account for Earth's curvature

## The Formula

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
