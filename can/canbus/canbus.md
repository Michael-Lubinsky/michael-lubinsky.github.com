# Trip identification from CANBUS data, 
you'll want to detect when there are gaps in the data that indicate the vehicle was turned off or parked. Here's how to approach this:

## Recommended Approach

Since **TBDC-Correlationid** represents a 1-minute message window, you can use it along with timestamps to identify trip boundaries. Here's a step-by-step solution:

### Method 1: Using Time Gaps (Most Reliable)

```python
from pyspark.sql import Window
from pyspark.sql.functions import col, lag, when, sum as _sum, unix_timestamp

# Define trip gap threshold (e.g., 10 minutes = 600 seconds)
TRIP_GAP_THRESHOLD = 600  # adjust based on your use case

# Sort by VIN and timestamp
window_spec = Window.partitionBy("MASKED-VIN").orderBy("dateTime")

df_with_trips = df \
    .withColumn("prev_timestamp", lag("dateTime").over(window_spec)) \
    .withColumn("time_diff_seconds", 
                unix_timestamp("dateTime") - unix_timestamp("prev_timestamp")) \
    .withColumn("is_new_trip", 
                when((col("time_diff_seconds") > TRIP_GAP_THRESHOLD) | 
                     col("prev_timestamp").isNull(), 1).otherwise(0)) \
    .withColumn("trip_number", 
                _sum("is_new_trip").over(window_spec.rowsBetween(Window.unboundedPreceding, 0))) \
    .drop("prev_timestamp", "time_diff_seconds", "is_new_trip")
```

### Method 2: Using TBDC-Correlationid Changes

```python
from pyspark.sql import Window
from pyspark.sql.functions import col, lag, when, sum as _sum

window_spec = Window.partitionBy("MASKED-VIN").orderBy("dateTime")

df_with_trips = df \
    .withColumn("prev_correlation_id", lag("TBDC-Correlationid").over(window_spec)) \
    .withColumn("prev_timestamp", lag("dateTime").over(window_spec)) \
    .withColumn("time_diff_seconds", 
                unix_timestamp("dateTime") - unix_timestamp("prev_timestamp")) \
    .withColumn("is_new_trip", 
                when(col("prev_correlation_id").isNull() | 
                     (col("time_diff_seconds") > 600), 1).otherwise(0)) \
    .withColumn("trip_number", 
                _sum("is_new_trip").over(window_spec.rowsBetween(Window.unboundedPreceding, 0)))
```

### Method 3: Hybrid Approach (Recommended)

Combine both correlation ID and time gaps for more robust trip detection:

```python
from pyspark.sql import Window
from pyspark.sql.functions import *

TRIP_GAP_THRESHOLD = 600  # 10 minutes

window_spec = Window.partitionBy("MASKED-VIN").orderBy("dateTime")

df_with_trips = (df
    .withColumn("prev_correlation_id", lag("TBDC-Correlationid").over(window_spec))
    .withColumn("prev_datetime", lag("dateTime").over(window_spec))
    .withColumn("time_gap_seconds", 
                unix_timestamp("dateTime") - unix_timestamp("prev_datetime"))
    
    # New trip conditions:
    # 1. First record for this VIN
    # 2. Time gap exceeds threshold
    # 3. Significant correlation ID jump (indicating missing messages)
    .withColumn("is_new_trip",
                when(col("prev_datetime").isNull(), 1)
                .when(col("time_gap_seconds") > TRIP_GAP_THRESHOLD, 1)
                .otherwise(0))
    
    .withColumn("trip_number",
                _sum("is_new_trip").over(window_spec.rowsBetween(Window.unboundedPreceding, 0)))
    
    .drop("prev_correlation_id", "prev_datetime", "time_gap_seconds", "is_new_trip")
)
```

## Key Considerations

1. **Trip Gap Threshold**: Adjust based on your use case:
   - 5-10 minutes: Typical for distinguishing trips
   - 2-3 minutes: More sensitive, might split trips at traffic lights
   - 15-30 minutes: Less sensitive, might merge short errands

2. **Validation**: Check your results:
```python
# See trip statistics per vehicle
df_with_trips.groupBy("MASKED-VIN", "trip_number") \
    .agg(
        min("dateTime").alias("trip_start"),
        max("dateTime").alias("trip_end"),
        count("*").alias("record_count")
    ).orderBy("MASKED-VIN", "trip_number").show()
```

3. **Performance**: For large datasets, consider partitioning:
```python
df_with_trips = df_with_trips.repartition("MASKED-VIN")
```

Which approach would work best depends on your data characteristics. I'd recommend starting with **Method 3** as it's the most robust!

# Derive a **trip_number** per vehicle using `TBDC-Correlationid`, 
because each unique correlation ID represents a distinct one-minute CAN message “session.” To group those into contiguous *trips* (continuous driving segments), you’ll want to detect **gaps in correlation or time** for each VIN.

Here’s the reasoning and a ready-to-run PySpark (Databricks) implementation.

---

### 🚗 Logic

1. **Partition by vehicle (`MASKED-VIN`)** and **order by timestamp (`dateTime`)**.
2. **Detect start of new trip** when:

   * The time gap between consecutive rows exceeds a threshold (e.g. > 5 minutes), **or**
   * The `TBDC-Correlationid` changes discontinuously (missing sequence or large jump).
3. **Use a cumulative sum** of these “new trip” flags to assign a `trip_number`.

---

### ⏱️ Choosing the gap threshold

Typical CANBus data arrives every 100 ms, and `TBDC-Correlationid` groups signals over 1 minute.
So if you see a gap > 5 minutes between correlation IDs (or timestamps), it likely marks engine off / ignition off → new trip.

---

### 🧭 PySpark implementation (Databricks cell)

```python
from pyspark.sql import functions as F, Window

# assume df is your CANBUS dataframe

# Window per VIN, ordered by timestamp
w = Window.partitionBy("MASKED-VIN").orderBy("dateTime")

# Calculate time difference (seconds) between consecutive rows
df = df.withColumn(
    "prev_time",
    F.lag("dateTime").over(w)
).withColumn(
    "time_diff_sec",
    F.unix_timestamp("dateTime") - F.unix_timestamp("prev_time")
)

# Detect when correlation id changes
df = df.withColumn(
    "prev_corr",
    F.lag("TBDC-Correlationid").over(w)
).withColumn(
    "new_trip_flag",
    F.when(
        (F.col("time_diff_sec") > 300) |  # gap > 5 minutes
        (F.col("TBDC-Correlationid") != F.col("prev_corr")),
        1
    ).otherwise(0)
)

# Cumulative sum of trip boundaries per VIN
df = df.withColumn(
    "trip_number",
    F.sum("new_trip_flag").over(w.rowsBetween(Window.unboundedPreceding, 0)) + F.lit(1)
)

# Optional cleanup
result_df = df.drop("prev_time", "prev_corr", "time_diff_sec", "new_trip_flag")

display(result_df.select("MASKED-VIN", "dateTime", "TBDC-Correlationid", "trip_number"))
```

---

### 🧩 Notes & tuning

* Adjust `> 300` seconds threshold depending on real vehicle behavior.
* You can also collapse data to one row per `TBDC-Correlationid` first (since each ID covers 1 minute), then apply the same logic for better performance:

  ```python
  df_min = df.groupBy("MASKED-VIN", "TBDC-Correlationid").agg(F.min("dateTime").alias("minute_ts"))
  ```
* To ensure trip numbers restart per day, you can add `.partitionBy("MASKED-VIN", "source_date")` instead.

---

Would you like me to modify this so that each trip’s **start and end timestamps** (and duration) are also output per VIN?

## Syntetic dataset
 Databricks / PySpark: generate ~10k synthetic CANBUS rows for 2 VINs
 
```python

from pyspark.sql import functions as F, types as T

# ---------- knobs ----------
minutes_per_vin = 9                 # 9 minutes @ 100ms → 9*60*10 = 5400 rows per VIN
rows_per_minute = 60 * 10           # 600 rows per minute at 100ms
seed = 42                           # reproducible randoms
start_ts = F.to_timestamp(F.lit("2025-01-01 08:00:00"))  # base start for VIN A
start_ts_b = F.to_timestamp(F.lit("2025-01-01 09:30:00"))# base start for VIN B

vin_a = "VINXXXXXXXXXXXXXA"
vin_b = "VINXXXXXXXXXXXXXB"

# vehicle metadata to make things a bit realistic
vehicleA = {
  "vehicleName": "Falcon X",
  "DispatchModelType": "DM-1234",
  "NaviModel": "7",
  "ModelYear": "2022",
}
vehicleB = {
  "vehicleName": "Ranger Pro",
  "DispatchModelType": "DM-8877",
  "NaviModel": "8",
  "ModelYear": "2023",
}

# Labels & units (array is 1-indexed in Spark for element_at)
labels = F.array(
    F.lit("speed"),
    F.lit("rpm"),
    F.lit("throttle"),
    F.lit("coolant_temp"),
    F.lit("fuel_rate")
)
def unit_for(label_col):
    return (F.when(label_col=="speed",        F.lit("km/h"))
             .when(label_col=="rpm",          F.lit("rpm"))
             .when(label_col=="throttle",     F.lit("%"))
             .when(label_col=="coolant_temp", F.lit("°C"))
             .when(label_col=="fuel_rate",    F.lit("L/h"))
             .otherwise(F.lit("")))

def value_for(label_col, r):
    # simple synthetic ranges; tweak as needed
    return (F.when(label_col=="speed",        120.0*r)                                  # 0..120
             .when(label_col=="rpm",          600.0 + r*3400.0)                         # 600..4000
             .when(label_col=="throttle",     r*100.0)                                  # 0..100
             .when(label_col=="coolant_temp", 70.0 + r*40.0)                            # 70..110
             .when(label_col=="fuel_rate",    r*25.0)                                   # 0..25
             .otherwise(r*10.0))

def build_vin_df(vin, meta, base_ts):
    total_rows = minutes_per_vin * rows_per_minute
    base = spark.range(0, total_rows).withColumnRenamed("id", "row_id")

    # 100ms ticks
    df = base.withColumn("dateTime", base_ts + F.expr("INTERVAL 100 milliseconds") * F.col("row_id"))

    # one-minute correlation grouping (unique per minute per VIN)
    minute_ts = F.date_trunc("minute", F.col("dateTime"))
    df = df.withColumn("minute_ts", minute_ts)
    df = df.withColumn(
        "TBDC-Correlationid",
        F.concat_ws("-", F.lit("corr"), F.lit(vin), F.date_format(F.col("minute_ts"), "yyyyMMddHHmm"))
    )

    # per-row label chosen cyclically
    label = F.element_at(labels, (F.col("row_id") % F.size(labels)) + F.lit(1))
    df = df.withColumn("label", label)

    # deterministic random by minute + row_id
    rnd = F.rand(seed) * 0.7 + F.rand(seed+7) * 0.3  # mix for variety
    df = df.withColumn("value", value_for(F.col("label"), rnd).cast("double"))
    df = df.withColumn("unit", unit_for(F.col("label")))

    # date parts
    df = df.withColumn("year",  F.date_format("dateTime", "yyyy")) \
           .withColumn("month", F.month("dateTime")) \
           .withColumn("day",   F.dayofmonth("dateTime")) \
           .withColumn("hour",  F.hour("dateTime"))

    # static / metadata columns
    df = (df
        .withColumn("vehicleName",        F.lit(meta["vehicleName"]))
        .withColumn("DispatchModelType",  F.lit(meta["DispatchModelType"]))
        .withColumn("MASKED-VIN",         F.lit(vin))
        .withColumn("NaviModel",          F.lit(meta["NaviModel"]))
        .withColumn("ModelYear",          F.lit(meta["ModelYear"]))
        .withColumn("insert_date_time",   F.current_timestamp())
        .withColumn("record_version",     F.lit(1).cast("int"))
        .withColumn("schema_version",     F.lit("1.1"))
        .withColumn("original_table",     F.lit("bronze.canbus"))
        .withColumn("source_date",        F.to_date("dateTime"))
        .withColumn("original_table",     F.lit("bronze.canbus"))
        .withColumn("TBDC-Correlationid", F.col("TBDC-Correlationid").cast("string"))
    )

    # reorder/select to exactly match requested schema & names
    cols = [
        "vehicleName",                # string
        "DispatchModelType",          # string
        "year",                       # string
        "month",                      # int
        "day",                        # int
        "hour",                       # int
        "MASKED-VIN",                 # string
        "TBDC-Correlationid",         # string
        "NaviModel",                  # string
        "ModelYear",                  # string
        "dateTime",                   # timestamp
        "label",                      # string
        "value",                      # float/double
        "unit",                       # string
        "insert_date_time",           # timestamp
        "record_version",             # int
        "schema_version",             # string
        "original_table",             # string
        "source_date"                 # date
    ]
    return df.select(*cols)

df_a = build_vin_df(vin_a, vehicleA, start_ts)
df_b = build_vin_df(vin_b, vehicleB, start_ts_b)

synthetic_df = df_a.unionByName(df_b)

synthetic_df = synthetic_df.cache()

print("Rows per VIN:")
display(synthetic_df.groupBy("MASKED-VIN").count().orderBy("MASKED-VIN"))

print("Total rows (should be ~10,800):", synthetic_df.count())

# Peek
display(synthetic_df.orderBy("MASKED-VIN", "dateTime").limit(20))
```

# Syntetic dataset apprach 2
```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, TimestampType, DateType
from datetime import datetime, timedelta
import random
import uuid

# Initialize Spark session
spark = SparkSession.builder.appName("CANBUS_Synthetic_Data").getOrCreate()

# Define schema
 
schema = StructType([
    StructField("vehicleName", StringType(), True),
    StructField("DispatchModelType", StringType(), True),
    StructField("year", StringType(), True),
    StructField("month", IntegerType(), True),
    StructField("day", IntegerType(), True),
    StructField("hour", IntegerType(), True),
    StructField("MASKED-VIN", StringType(), True),
    StructField("TBDC-Correlationid", StringType(), True),
    StructField("NaviModel", StringType(), True),
    StructField("ModelYear", StringType(), True),
    StructField("dateTime", TimestampType(), True),
    StructField("label", StringType(), True),
    StructField("value", FloatType(), True),
    StructField("unit", StringType(), True),
    StructField("insert_date_time", TimestampType(), True),
    StructField("record_version", IntegerType(), True),
    StructField("schema_version", StringType(), True),
    StructField("original_table", StringType(), True),
    StructField("source_date", DateType(), True)
])

# Configuration
NUM_RECORDS = 10000
VINS = ["VIN123XXXXX456789", "VIN987XXXXX654321"]
VEHICLE_CONFIGS = {
    "VIN123XXXXX456789": {
        "vehicleName": "Camry",
        "DispatchModelType": "AXVH70",
        "NaviModel": "7",
        "ModelYear": "2024"
    },
    "VIN987XXXXX654321": {
        "vehicleName": "RAV4",
        "DispatchModelType": "AXAH54",
        "NaviModel": "9",
        "ModelYear": "2023"
    }
}

# Sensor labels with typical ranges
LABELS = {
    "VehicleSpeed": {"range": (0, 120), "unit": "km/h"},
    "EngineRPM": {"range": (600, 6000), "unit": "rpm"},
    "FuelLevel": {"range": (10, 100), "unit": "%"},
    "EngineTemp": {"range": (80, 105), "unit": "C"},
    "ThrottlePosition": {"range": (0, 100), "unit": "%"},
    "BatteryVoltage": {"range": (12.0, 14.5), "unit": "V"},
    "OdometerReading": {"range": (10000, 50000), "unit": "km"},
    "AmbientTemp": {"range": (15, 35), "unit": "C"}
}

def generate_trip_data(vin, start_time, duration_minutes, records_per_vin):
    """Generate data for a single trip"""
    data = []
    current_time = start_time
    correlation_id = None
    last_correlation_time = None
    
    # Trip characteristics
    vehicle_config = VEHICLE_CONFIGS[vin]
    num_labels = len(LABELS)
    records_per_timestamp = num_labels  # One record per label per timestamp
    
    # Calculate number of timestamps needed
    num_timestamps = records_per_vin // records_per_timestamp
    interval_ms = (duration_minutes * 60 * 1000) / num_timestamps  # milliseconds between readings
    
    for i in range(num_timestamps):
        # Update correlation ID every minute (60000ms)
        if last_correlation_time is None or (current_time - last_correlation_time).total_seconds() >= 60:
            correlation_id = str(uuid.uuid4())
            last_correlation_time = current_time
        
        # Generate one record for each label at this timestamp
        for label_name, label_config in LABELS.items():
            min_val, max_val = label_config["range"]
            
            # Add some realistic variation based on label
            if label_name == "VehicleSpeed":
                # Speed varies more during trip
                value = random.uniform(20, 80) if i > 10 and i < num_timestamps - 10 else random.uniform(0, 30)
            elif label_name == "EngineRPM":
                # RPM correlates with speed
                value = random.uniform(1500, 3500) if i > 10 else random.uniform(800, 1200)
            elif label_name == "FuelLevel":
                # Fuel decreases slowly over trip
                value = max_val - (i / num_timestamps) * 10
            elif label_name == "OdometerReading":
                # Odometer increases
                value = min_val + (i / num_timestamps) * 50
            else:
                value = random.uniform(min_val, max_val)
            
            row = (
                vehicle_config["vehicleName"],
                vehicle_config["DispatchModelType"],
                str(current_time.year),
                current_time.month,
                current_time.day,
                current_time.hour,
                vin,
                correlation_id,
                vehicle_config["NaviModel"],
                vehicle_config["ModelYear"],
                current_time,
                label_name,
                round(value, 2),
                label_config["unit"],
                datetime.now(),  # insert_date_time
                1,  # record_version
                "1.1",  # schema_version
                "canbus.telemetry.signals",  # original_table
                current_time.date()  # source_date
            )
            data.append(row)
        
        # Increment time by interval
        current_time += timedelta(milliseconds=interval_ms)
    
    return data

# Generate data for both VINs with multiple trips
all_data = []
records_per_vin = NUM_RECORDS // 2

# VIN 1: 3 trips
vin1 = VINS[0]
base_date = datetime(2025, 10, 15, 8, 0, 0)

# Trip 1: Morning commute
trip1_data = generate_trip_data(vin1, base_date, 25, records_per_vin // 3)
all_data.extend(trip1_data)

# Gap of 8 hours (at work)
# Trip 2: Evening commute
trip2_start = base_date + timedelta(hours=8, minutes=30)
trip2_data = generate_trip_data(vin1, trip2_start, 30, records_per_vin // 3)
all_data.extend(trip2_data)

# Gap of 12 hours (overnight)
# Trip 3: Next day morning
trip3_start = base_date + timedelta(days=1, hours=7, minutes=45)
trip3_data = generate_trip_data(vin1, trip3_start, 20, records_per_vin // 3)
all_data.extend(trip3_data)

# VIN 2: 2 trips
vin2 = VINS[1]
base_date2 = datetime(2025, 10, 15, 9, 15, 0)

# Trip 1: Mid-morning drive
trip4_data = generate_trip_data(vin2, base_date2, 35, records_per_vin // 2)
all_data.extend(trip4_data)

# Gap of 5 hours
# Trip 2: Afternoon drive
trip5_start = base_date2 + timedelta(hours=5, minutes=20)
trip5_data = generate_trip_data(vin2, trip5_start, 40, records_per_vin // 2)
all_data.extend(trip5_data)

# Create DataFrame
df = spark.createDataFrame(all_data, schema=schema)

# Show summary
print(f"Total records generated: {df.count()}")
print(f"\nRecords per VIN:")
df.groupBy("MASKED-VIN").count().show()

print(f"\nSample data:")
df.orderBy("MASKED-VIN", "dateTime").show(20, truncate=False)

print(f"\nUnique correlation IDs per VIN:")
df.groupBy("MASKED-VIN").agg({"TBDC-Correlationid": "approx_count_distinct"}).show()

print(f"\nTime range per VIN:")
df.groupBy("MASKED-VIN").agg(
    {"dateTime": "min", "dateTime": "max"}
).show(truncate=False)

print(f"\nLabel distribution:")
df.groupBy("label").count().orderBy("label").show()

# Display schema
print("\nDataFrame Schema:")
df.printSchema()
```
