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

 
## To have 1 Row Per Timestamp we need to **aggregate** the results. 

### Solution A: UNION ALL + GROUP BY (Recommended)

```sql
SELECT 
  common_time,
  MAX(device1_value) as device1_value,
  MAX(device2_value) as device2_value,
  MAX(device3_value) as device3_value
FROM (
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
)
GROUP BY common_time
ORDER BY common_time
```

**Output (1 row per timestamp):**
```
common_time | device1_value | device2_value | device3_value
1000        | 10.5          | 20.3          | 30.1
```

### Solution B: Using COALESCE with Self-Joins

```sql
WITH all_times AS (
  SELECT DISTINCT device1_time as common_time FROM your_table WHERE device1_time IS NOT NULL
  UNION
  SELECT DISTINCT device2_time FROM your_table WHERE device2_time IS NOT NULL
  UNION
  SELECT DISTINCT device3_time FROM your_table WHERE device3_time IS NOT NULL
)
SELECT 
  t.common_time,
  d1.device1_value,
  d2.device2_value,
  d3.device3_value
FROM all_times t
LEFT JOIN your_table d1 ON t.common_time = d1.device1_time
LEFT JOIN your_table d2 ON t.common_time = d2.device2_time
LEFT JOIN your_table d3 ON t.common_time = d3.device3_time
ORDER BY t.common_time
```

### Solution C: Arrays + FLATTEN + GROUP BY

```sql
WITH exploded AS (
  SELECT 
    explode(
      array(
        struct(device1_time as time, 'device1' as device, device1_value as value),
        struct(device2_time as time, 'device2' as device, device2_value as value),
        struct(device3_time as time, 'device3' as device, device3_value as value)
      )
    ) as data
  FROM your_table
)
SELECT 
  data.time as common_time,
  MAX(IF(data.device = 'device1', data.value, NULL)) as device1_value,
  MAX(IF(data.device = 'device2', data.value, NULL)) as device2_value,
  MAX(IF(data.device = 'device3', data.value, NULL)) as device3_value
FROM exploded
WHERE data.time IS NOT NULL
GROUP BY data.time
ORDER BY common_time
```

### Solution D: PIVOT Approach (Most Elegant for Databricks)

```sql
WITH unpivoted AS (
  SELECT 
    stack(3,
      'device1', device1_time, device1_value,
      'device2', device2_time, device2_value,
      'device3', device3_time, device3_value
    ) AS (device_name, common_time, value)
  FROM your_table
)
SELECT 
  common_time,
  MAX(IF(device_name = 'device1', value, NULL)) as device1_value,
  MAX(IF(device_name = 'device2', value, NULL)) as device2_value,
  MAX(IF(device_name = 'device3', value, NULL)) as device3_value
FROM unpivoted
WHERE common_time IS NOT NULL
GROUP BY common_time
ORDER BY common_time
```

## Comparison of Behaviors

| Approach | Same Timestamp Behavior | Output |
|----------|------------------------|--------|
| **UNION ALL (original)** | 3 separate rows | Multiple rows per timestamp |
| **UNION ALL + GROUP BY** | 1 consolidated row | One row per unique timestamp |
| **Self-joins** | 1 consolidated row | One row per unique timestamp |
| **Arrays + GROUP BY** | 1 consolidated row | One row per unique timestamp |

## Full Example with Both Approaches

```sql
-- Original data
CREATE OR REPLACE TEMP VIEW source_data AS
SELECT 1000 as device1_time, 10.5 as device1_value,
       1000 as device2_time, 20.3 as device2_value,
       1000 as device3_time, 30.1 as device3_value;

-- UNION ALL (3 rows)
SELECT 'UNION ALL - Multiple Rows' as approach, * FROM (
  SELECT device1_time as common_time, device1_value, NULL as device2_value, NULL as device3_value FROM source_data
  UNION ALL
  SELECT device2_time, NULL, device2_value, NULL FROM source_data
  UNION ALL
  SELECT device3_time, NULL, NULL, device3_value FROM source_data
);

-- UNION ALL + GROUP BY (1 row)
SELECT 'UNION ALL + GROUP BY - Single Row' as approach, * FROM (
  SELECT 
    common_time,
    MAX(device1_value) as device1_value,
    MAX(device2_value) as device2_value,
    MAX(device3_value) as device3_value
  FROM (
    SELECT device1_time as common_time, device1_value, NULL as device2_value, NULL as device3_value FROM source_data
    UNION ALL
    SELECT device2_time, NULL, device2_value, NULL FROM source_data
    UNION ALL
    SELECT device3_time, NULL, NULL, device3_value FROM source_data
  )
  GROUP BY common_time
);
```

## Recommendation

**If you want 1 row per unique timestamp:** Use **Solution A (UNION ALL + GROUP BY)** or **Solution D (PIVOT)**.

**If you want separate rows for each device reading:** Use the original **UNION ALL** without GROUP BY.

The choice depends on your use case:
- **Time series analysis**: Usually want 1 row per timestamp (use GROUP BY)
- **Event log / audit trail**: May want separate rows per device (use plain UNION ALL)


 

### Option 6 - ChatGPT
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
