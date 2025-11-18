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



Here are several SQL approaches to create a `common_time` column that contains the union of all device times:

## Option 1: Using UNION ALL (Simple & Clear)

```sql
-- Unpivot device times into common_time column
SELECT 
  device1_time as common_time,
  device1_value,
  NULL as device2_value,
  NULL as device3_value
FROM your_table
WHERE device1_time IS NOT NULL

UNION ALL

SELECT 
  device2_time as common_time,
  NULL as device1_value,
  device2_value,
  NULL as device3_value
FROM your_table
WHERE device2_time IS NOT NULL

UNION ALL

SELECT 
  device3_time as common_time,
  NULL as device1_value,
  NULL as device2_value,
  device3_value
FROM your_table
WHERE device3_time IS NOT NULL

ORDER BY common_time
```

## Option 2: Using STACK (Databricks/Spark SQL Native)

```sql
-- Use stack() to unpivot in a single statement
SELECT 
  common_time,
  device1_value,
  device2_value,
  device3_value
FROM your_table
LATERAL VIEW stack(3,
  device1_time, device1_value, NULL, NULL,
  device2_time, NULL, device2_value, NULL,
  device3_time, NULL, NULL, device3_value
) s AS common_time, device1_value, device2_value, device3_value
WHERE common_time IS NOT NULL
ORDER BY common_time
```

## Option 3: Using EXPLODE with Arrays (More Flexible)

```sql
-- Create array of structs then explode
SELECT 
  device.time as common_time,
  device.value1 as device1_value,
  device.value2 as device2_value,
  device.value3 as device3_value
FROM your_table
LATERAL VIEW explode(
  array(
    struct(device1_time as time, device1_value as value1, CAST(NULL AS DOUBLE) as value2, CAST(NULL AS DOUBLE) as value3),
    struct(device2_time as time, CAST(NULL AS DOUBLE) as value1, device2_value as value2, CAST(NULL AS DOUBLE) as value3),
    struct(device3_time as time, CAST(NULL AS DOUBLE) as value1, CAST(NULL AS DOUBLE) as value2, device3_value as value3)
  )
) t AS device
WHERE device.time IS NOT NULL
ORDER BY common_time
```

## Option 4: If You Want to Keep Other Columns

```sql
-- Preserve other columns from original table
SELECT 
  id,  -- your other columns
  other_column,
  common_time,
  device1_value,
  device2_value,
  device3_value
FROM (
  SELECT 
    id,
    other_column,
    device1_time as common_time,
    device1_value,
    NULL as device2_value,
    NULL as device3_value
  FROM your_table
  WHERE device1_time IS NOT NULL
  
  UNION ALL
  
  SELECT 
    id,
    other_column,
    device2_time as common_time,
    NULL as device1_value,
    device2_value,
    NULL as device3_value
  FROM your_table
  WHERE device2_time IS NOT NULL
  
  UNION ALL
  
  SELECT 
    id,
    other_column,
    device3_time as common_time,
    NULL as device1_value,
    NULL as device2_value,
    device3_value
  FROM your_table
  WHERE device3_time IS NOT NULL
)
ORDER BY common_time
```

## Option 5: Create as a View or Table

```sql
-- Create a view for reusability
CREATE OR REPLACE VIEW device_unpivoted AS
SELECT 
  device1_time as common_time,
  device1_value,
  NULL as device2_value,
  NULL as device3_value
FROM your_table
WHERE device1_time IS NOT NULL

UNION ALL

SELECT 
  device2_time as common_time,
  NULL as device1_value,
  device2_value,
  NULL as device3_value
FROM your_table
WHERE device2_time IS NOT NULL

UNION ALL

SELECT 
  device3_time as common_time,
  NULL as device1_value,
  NULL as device2_value,
  device3_value
FROM your_table
WHERE device3_time IS NOT NULL;

-- Query the view
SELECT * FROM device_unpivoted ORDER BY common_time;
```

## Example Output

**Original Table:**
```
device1_time | device1_value | device2_time | device2_value | device3_time | device3_value
1000         | 10.5          | 1000         | 20.3          | 2000         | 30.1
1500         | 11.2          | 2500         | 21.5          | 3000         | 31.8
```

**After Transformation:**
```
common_time | device1_value | device2_value | device3_value
1000        | 10.5          | NULL          | NULL
1000        | NULL          | 20.3          | NULL
1500        | 11.2          | NULL          | NULL
2000        | NULL          | NULL          | 30.1
2500        | NULL          | 21.5          | NULL
3000        | NULL          | NULL          | 31.8
```

## Convert Milliseconds to Timestamp (Bonus)

```sql
SELECT 
  common_time,
  TIMESTAMP_MILLIS(common_time) as common_timestamp,
  device1_value,
  device2_value,
  device3_value
FROM (
  -- Use any of the above queries here
)
ORDER BY common_time
```

## Recommendation

**For simplicity and readability:** Use **Option 1** (UNION ALL)  
**For Databricks/Spark efficiency:** Use **Option 2** (STACK)  
**For flexibility with many devices:** Use **Option 3** (EXPLODE)

Choose based on:
- **UNION ALL**: Easy to understand, works everywhere
- **STACK**: Most concise for Databricks, best performance
- **EXPLODE**: Most flexible if you need to add more devices later



### Option 6
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
