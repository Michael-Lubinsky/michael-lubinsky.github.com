There is  csv file in databriks.
It has following columns:
car_id, travel_id, time, odometer, longitude, latitude.
Please write SQL to extract 
for every  (car_id, travel_id)  the odometer, longitude, latitude at start and end points  only
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
