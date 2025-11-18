There is Databrics Unity catalog table with columns: 
```
device1_time (number, unix time number in miliiseconds),
device1_value(number),
device2_time (number, unix time number in miliiseconds),
device2_value(number), 
device3_time (number, unix time number in miliiseconds), 
device3_value(number) 
```

  SQL to have new column common_time which is union of device1_time, device2_time, device3_time and keep other colums ,
like device1_value, device2_value, device3_value, etc in place


```sql
WITH t AS (
  SELECT device1_time, device1_value,
         device2_time, device2_value,
         device3_time, device3_value
  FROM your_table
),

-- Normalize each device to (time, value) rows
d1 AS (
  SELECT device1_time AS common_time,
         device1_value AS device1_value,
         NULL AS device2_value,
         NULL AS device3_value
  FROM t
),
d2 AS (
  SELECT device2_time AS common_time,
         NULL AS device1_value,
         device2_value AS device2_value,
         NULL AS device3_value
  FROM t
),
d3 AS (
  SELECT device3_time AS common_time,
         NULL AS device1_value,
         NULL AS device2_value,
         device3_value AS device3_value
  FROM t
),

-- Union all timestamps
all_times AS (
  SELECT * FROM d1
  UNION ALL
  SELECT * FROM d2
  UNION ALL
  SELECT * FROM d3
)

-- Group by time and combine values
SELECT
    common_time,
    MAX(device1_value) AS device1_value,
    MAX(device2_value) AS device2_value,
    MAX(device3_value) AS device3_value
FROM all_times
GROUP BY common_time
ORDER BY common_time;


```
