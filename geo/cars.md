There is  csv file in databriks.
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
