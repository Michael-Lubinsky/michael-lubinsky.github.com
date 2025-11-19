# Claude Databricks daily job to populate  rollup table:

## 1. Create Target Rollup Table

```sql
CREATE TABLE IF NOT EXISTS hcai_databricks_dev.chargeminder2.daily_vehicle_summary (
  car_id STRING,
  date DATE,
  miles_driven DOUBLE,
  fuel_consumed_gallons DOUBLE,
  has_charge BOOLEAN,
  
  -- Additional helpful metrics
  start_odometer DOUBLE,
  end_odometer DOUBLE,
  start_fuel DOUBLE,
  end_fuel DOUBLE,
  fuel_added_gallons DOUBLE,  -- From refueling events
  readings_count INT,
  
  -- Metadata
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
USING DELTA
PARTITIONED BY (date)
TBLPROPERTIES (
  delta.enableChangeDataFeed = true,
  delta.autoOptimize.optimizeWrite = true,
  delta.autoOptimize.autoCompact = true
)
COMMENT 'Daily rollup of vehicle metrics in PST timezone';
```

## 2. Databricks Python Job Code

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Daily Vehicle Summary Rollup Job (PST)
# MAGIC Runs daily to aggregate vehicle metrics by date in Pacific timezone

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import datetime, timedelta
from delta.tables import DeltaTable
import pytz

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "catalog": "hcai_databricks_dev",
    "schema": "chargeminder2",
    "source_table": "telemetry",
    "target_table": "daily_vehicle_summary",
    "timezone": "America/Los_Angeles",  # PST/PDT
    "lookback_days": 3,  # Process last N days (handles late-arriving data)
}

SOURCE_TABLE = f"{CONFIG['catalog']}.{CONFIG['schema']}.{CONFIG['source_table']}"
TARGET_TABLE = f"{CONFIG['catalog']}.{CONFIG['schema']}.{CONFIG['target_table']}"

print(f"""
{'='*80}
Daily Vehicle Summary Rollup Job
{'='*80}
Source: {SOURCE_TABLE}
Target: {TARGET_TABLE}
Timezone: {CONFIG['timezone']}
Processing: Last {CONFIG['lookback_days']} days
{'='*80}
""")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_processing_date_range():
    """Get date range to process (last N days in PST)."""
    pst = pytz.timezone(CONFIG['timezone'])
    now_pst = datetime.now(pst)
    
    # End date: yesterday (don't process today until it's complete)
    end_date = (now_pst - timedelta(days=1)).date()
    
    # Start date: N days back
    start_date = (now_pst - timedelta(days=CONFIG['lookback_days'])).date()
    
    print(f"Processing date range: {start_date} to {end_date} (PST)")
    return start_date, end_date


def convert_millis_to_pst_date(ts_col):
    """Convert Unix milliseconds to PST date."""
    return F.to_date(
        F.from_utc_timestamp(
            F.timestamp_millis(ts_col),
            CONFIG['timezone']
        )
    )

# ============================================================================
# DATA PROCESSING
# ============================================================================

def calculate_daily_metrics(start_date, end_date):
    """
    Calculate daily metrics per car:
    - Miles driven
    - Fuel consumed (accounting for refueling)
    - Charging activity
    """
    
    print("Reading source data...")
    
    # Read telemetry data for date range
    df = spark.sql(f"""
        SELECT 
            car_id,
            odometer_miles,
            odometer_miles_updated_at_ms,
            fuel_remaining_gallons,
            fuel_remaining_gallons_retrieved_at_ms,
            is_charging,
            is_charging_updated_at_ms
        FROM {SOURCE_TABLE}
        WHERE odometer_miles IS NOT NULL
          AND odometer_miles_updated_at_ms IS NOT NULL
    """)
    
    # Convert timestamps to PST dates
    df = df.withColumn(
        "odo_date",
        convert_millis_to_pst_date(F.col("odometer_miles_updated_at_ms"))
    ).withColumn(
        "fuel_date", 
        convert_millis_to_pst_date(F.col("fuel_remaining_gallons_retrieved_at_ms"))
    ).withColumn(
        "charging_date",
        convert_millis_to_pst_date(F.col("is_charging_updated_at_ms"))
    )
    
    # Filter to date range
    df = df.filter(
        (F.col("odo_date") >= F.lit(start_date)) &
        (F.col("odo_date") <= F.lit(end_date))
    )
    
    record_count = df.count()
    print(f"Processing {record_count:,} records...")
    
    if record_count == 0:
        print("No data to process.")
        return None
    
    # ========================================================================
    # Calculate Daily Odometer Metrics
    # ========================================================================
    
    print("Calculating odometer metrics...")
    
    # Get first and last odometer reading per car per day
    odo_window = Window.partitionBy("car_id", "odo_date").orderBy("odometer_miles_updated_at_ms")
    
    df_odo = df.filter(F.col("odometer_miles").isNotNull()) \
        .withColumn("odo_rank", F.row_number().over(odo_window)) \
        .withColumn("odo_rank_desc", 
                    F.row_number().over(
                        Window.partitionBy("car_id", "odo_date")
                              .orderBy(F.desc("odometer_miles_updated_at_ms"))
                    ))
    
    # First reading of the day
    df_odo_start = df_odo.filter(F.col("odo_rank") == 1) \
        .select(
            F.col("car_id"),
            F.col("odo_date").alias("date"),
            F.col("odometer_miles").alias("start_odometer"),
            F.col("odometer_miles_updated_at_ms").alias("start_odo_time")
        )
    
    # Last reading of the day
    df_odo_end = df_odo.filter(F.col("odo_rank_desc") == 1) \
        .select(
            F.col("car_id"),
            F.col("odo_date").alias("date"),
            F.col("odometer_miles").alias("end_odometer"),
            F.col("odometer_miles_updated_at_ms").alias("end_odo_time")
        )
    
    # Join and calculate miles driven
    df_odo_daily = df_odo_start.join(
        df_odo_end,
        on=["car_id", "date"],
        how="inner"
    ).withColumn(
        "miles_driven",
        F.when(
            F.col("end_odometer") >= F.col("start_odometer"),
            F.col("end_odometer") - F.col("start_odometer")
        ).otherwise(0.0)  # Handle odometer resets/errors
    ).withColumn(
        "odo_readings_count",
        F.count("*").over(Window.partitionBy("car_id", "date"))
    )
    
    # ========================================================================
    # Calculate Daily Fuel Metrics
    # ========================================================================
    
    print("Calculating fuel metrics...")
    
    fuel_window = Window.partitionBy("car_id", "fuel_date").orderBy("fuel_remaining_gallons_retrieved_at_ms")
    
    df_fuel = df.filter(F.col("fuel_remaining_gallons").isNotNull()) \
        .withColumn("fuel_rank", F.row_number().over(fuel_window)) \
        .withColumn("fuel_rank_desc",
                    F.row_number().over(
                        Window.partitionBy("car_id", "fuel_date")
                              .orderBy(F.desc("fuel_remaining_gallons_retrieved_at_ms"))
                    ))
    
    # First fuel reading of the day
    df_fuel_start = df_fuel.filter(F.col("fuel_rank") == 1) \
        .select(
            F.col("car_id"),
            F.col("fuel_date").alias("date"),
            F.col("fuel_remaining_gallons").alias("start_fuel")
        )
    
    # Last fuel reading of the day
    df_fuel_end = df_fuel.filter(F.col("fuel_rank_desc") == 1) \
        .select(
            F.col("car_id"),
            F.col("fuel_date").alias("date"),
            F.col("fuel_remaining_gallons").alias("end_fuel")
        )
    
    # Detect refueling events (fuel increased)
    df_fuel_events = df_fuel.withColumn(
        "prev_fuel",
        F.lag("fuel_remaining_gallons").over(
            Window.partitionBy("car_id", "fuel_date")
                  .orderBy("fuel_remaining_gallons_retrieved_at_ms")
        )
    ).withColumn(
        "fuel_added",
        F.when(
            (F.col("fuel_remaining_gallons") - F.col("prev_fuel")) > 1.0,  # Threshold: 1 gallon
            F.col("fuel_remaining_gallons") - F.col("prev_fuel")
        ).otherwise(0.0)
    )
    
    # Sum refueling events per day
    df_fuel_added = df_fuel_events.groupBy("car_id", "fuel_date") \
        .agg(F.sum("fuel_added").alias("fuel_added_gallons"))
    
    # Join fuel metrics
    df_fuel_daily = df_fuel_start.join(
        df_fuel_end,
        on=["car_id", "date"],
        how="inner"
    ).join(
        df_fuel_added.withColumnRenamed("fuel_date", "date"),
        on=["car_id", "date"],
        how="left"
    ).withColumn(
        "fuel_added_gallons",
        F.coalesce(F.col("fuel_added_gallons"), F.lit(0.0))
    )
    
    # Calculate fuel consumed
    # Formula: start_fuel - end_fuel + fuel_added = fuel_consumed
    df_fuel_daily = df_fuel_daily.withColumn(
        "fuel_consumed_gallons",
        F.when(
            F.col("start_fuel") >= F.col("end_fuel"),
            F.col("start_fuel") - F.col("end_fuel")
        ).otherwise(
            # Refueling detected: account for added fuel
            F.col("start_fuel") + F.col("fuel_added_gallons") - F.col("end_fuel")
        )
    ).withColumn(
        "fuel_consumed_gallons",
        F.when(F.col("fuel_consumed_gallons") < 0, 0.0)
         .otherwise(F.col("fuel_consumed_gallons"))  # No negative consumption
    )
    
    # ========================================================================
    # Calculate Charging Activity
    # ========================================================================
    
    print("Calculating charging activity...")
    
    df_charging = df.filter(F.col("is_charging").isNotNull()) \
        .groupBy("car_id", "charging_date") \
        .agg(
            F.max(F.col("is_charging").cast("int")).alias("has_charge_int")
        ) \
        .withColumnRenamed("charging_date", "date") \
        .withColumn("has_charge", F.col("has_charge_int").cast("boolean")) \
        .drop("has_charge_int")
    
    # ========================================================================
    # Combine All Metrics
    # ========================================================================
    
    print("Combining metrics...")
    
    # Start with odometer data (most comprehensive)
    df_daily = df_odo_daily.select(
        "car_id", "date", "miles_driven", 
        "start_odometer", "end_odometer"
    )
    
    # Add fuel metrics
    df_daily = df_daily.join(
        df_fuel_daily.select(
            "car_id", "date", "fuel_consumed_gallons",
            "start_fuel", "end_fuel", "fuel_added_gallons"
        ),
        on=["car_id", "date"],
        how="left"
    )
    
    # Add charging activity
    df_daily = df_daily.join(
        df_charging,
        on=["car_id", "date"],
        how="left"
    ).withColumn(
        "has_charge",
        F.coalesce(F.col("has_charge"), F.lit(False))
    )
    
    # Count total readings per car per day
    df_daily = df_daily.join(
        df.groupBy("car_id", "odo_date")
          .agg(F.count("*").alias("readings_count"))
          .withColumnRenamed("odo_date", "date"),
        on=["car_id", "date"],
        how="left"
    )
    
    # Add metadata
    df_daily = df_daily.withColumn("created_at", F.current_timestamp()) \
                       .withColumn("updated_at", F.current_timestamp())
    
    # Fill nulls with defaults
    df_daily = df_daily.fillna({
        "miles_driven": 0.0,
        "fuel_consumed_gallons": 0.0,
        "fuel_added_gallons": 0.0,
        "has_charge": False,
        "readings_count": 0
    })
    
    # Final column selection
    df_final = df_daily.select(
        "car_id",
        "date",
        "miles_driven",
        "fuel_consumed_gallons",
        "has_charge",
        "start_odometer",
        "end_odometer",
        "start_fuel",
        "end_fuel",
        "fuel_added_gallons",
        "readings_count",
        "created_at",
        "updated_at"
    )
    
    return df_final


# ============================================================================
# UPSERT TO TARGET TABLE
# ============================================================================

def upsert_daily_summary(df_daily):
    """Upsert daily summary to target table."""
    
    if df_daily is None or df_daily.count() == 0:
        print("No data to upsert.")
        return
    
    print(f"Upserting {df_daily.count():,} records to {TARGET_TABLE}...")
    
    # Show sample
    print("\nSample data:")
    df_daily.select("car_id", "date", "miles_driven", "fuel_consumed_gallons", "has_charge") \
            .show(10, truncate=False)
    
    # Check if table exists
    if not spark.catalog.tableExists(TARGET_TABLE):
        print(f"Creating table {TARGET_TABLE}...")
        df_daily.write.format("delta") \
               .mode("overwrite") \
               .partitionBy("date") \
               .saveAsTable(TARGET_TABLE)
        print("✅ Table created and data written")
        return
    
    # Merge into existing table
    delta_table = DeltaTable.forName(spark, TARGET_TABLE)
    
    delta_table.alias("target") \
        .merge(
            df_daily.alias("source"),
            "target.car_id = source.car_id AND target.date = source.date"
        ) \
        .whenMatchedUpdate(set={
            "miles_driven": "source.miles_driven",
            "fuel_consumed_gallons": "source.fuel_consumed_gallons",
            "has_charge": "source.has_charge",
            "start_odometer": "source.start_odometer",
            "end_odometer": "source.end_odometer",
            "start_fuel": "source.start_fuel",
            "end_fuel": "source.end_fuel",
            "fuel_added_gallons": "source.fuel_added_gallons",
            "readings_count": "source.readings_count",
            "updated_at": "source.updated_at"
        }) \
        .whenNotMatchedInsertAll() \
        .execute()
    
    print("✅ Merge complete")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main job execution."""
    try:
        start_time = datetime.now()
        
        # Get date range to process
        start_date, end_date = get_processing_date_range()
        
        # Calculate metrics
        df_daily = calculate_daily_metrics(start_date, end_date)
        
        # Upsert to target
        upsert_daily_summary(df_daily)
        
        # Summary statistics
        if df_daily is not None:
            print("\n" + "="*80)
            print("Summary Statistics:")
            print("="*80)
            
            df_daily.agg(
                F.count("*").alias("total_records"),
                F.countDistinct("car_id").alias("unique_cars"),
                F.sum("miles_driven").alias("total_miles"),
                F.sum("fuel_consumed_gallons").alias("total_fuel_gallons"),
                F.sum(F.col("has_charge").cast("int")).alias("days_with_charging")
            ).show(truncate=False)
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Job completed in {duration:.1f} seconds")
        
    except Exception as e:
        print(f"\n❌ Job failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
```

## 3. Job Configuration (JSON)

Create the job in Databricks UI or via API:

```json
{
  "name": "Daily Vehicle Summary Rollup (PST)",
  "email_notifications": {
    "on_failure": ["your-email@company.com"]
  },
  "timeout_seconds": 7200,
  "max_concurrent_runs": 1,
  "tasks": [
    {
      "task_key": "daily_rollup",
      "description": "Calculate and upsert daily vehicle metrics",
      "notebook_task": {
        "notebook_path": "/path/to/daily_vehicle_summary_job",
        "source": "WORKSPACE"
      },
      "job_cluster_key": "daily_rollup_cluster",
      "timeout_seconds": 3600,
      "email_notifications": {}
    }
  ],
  "job_clusters": [
    {
      "job_cluster_key": "daily_rollup_cluster",
      "new_cluster": {
        "spark_version": "14.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 2,
        "spark_conf": {
          "spark.sql.adaptive.enabled": "true",
          "spark.databricks.delta.optimizeWrite.enabled": "true"
        },
        "aws_attributes": {
          "availability": "SPOT_WITH_FALLBACK"
        }
      }
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 0 2 * * ?",
    "timezone_id": "America/Los_Angeles",
    "pause_status": "UNPAUSED"
  },
  "format": "MULTI_TASK"
}
```

**Schedule explained:**
- `0 0 2 * * ?` = Every day at 2:00 AM PST
- Runs after midnight to ensure previous day's data is complete

## 4. Alternative: SQL-Only Approach

If you prefer pure SQL, create a SQL notebook:

```sql
-- Databricks SQL Notebook: Daily Vehicle Summary Rollup

-- ============================================================================
-- Set Configuration
-- ============================================================================
SET TIME ZONE 'America/Los_Angeles';

DECLARE OR REPLACE VARIABLE processing_date DATE DEFAULT CURRENT_DATE - INTERVAL 1 DAY;
DECLARE OR REPLACE VARIABLE lookback_days INT DEFAULT 3;

-- ============================================================================
-- Calculate Daily Metrics
-- ============================================================================

MERGE INTO hcai_databricks_dev.chargeminder2.daily_vehicle_summary AS target
USING (
  WITH 
  -- Convert timestamps to PST dates
  telemetry_with_dates AS (
    SELECT 
      car_id,
      odometer_miles,
      odometer_miles_updated_at_ms,
      DATE(FROM_UTC_TIMESTAMP(TIMESTAMP_MILLIS(odometer_miles_updated_at_ms), 'America/Los_Angeles')) as odo_date,
      
      fuel_remaining_gallons,
      fuel_remaining_gallons_retrieved_at_ms,
      DATE(FROM_UTC_TIMESTAMP(TIMESTAMP_MILLIS(fuel_remaining_gallons_retrieved_at_ms), 'America/Los_Angeles')) as fuel_date,
      
      is_charging,
      is_charging_updated_at_ms,
      DATE(FROM_UTC_TIMESTAMP(TIMESTAMP_MILLIS(is_charging_updated_at_ms), 'America/Los_Angeles')) as charging_date
    FROM hcai_databricks_dev.chargeminder2.telemetry
    WHERE DATE(FROM_UTC_TIMESTAMP(TIMESTAMP_MILLIS(odometer_miles_updated_at_ms), 'America/Los_Angeles')) 
          BETWEEN CURRENT_DATE - INTERVAL 3 DAY AND CURRENT_DATE - INTERVAL 1 DAY
  ),
  
  -- Daily odometer metrics
  daily_odometer AS (
    SELECT 
      car_id,
      odo_date as date,
      FIRST_VALUE(odometer_miles) OVER (PARTITION BY car_id, odo_date ORDER BY odometer_miles_updated_at_ms) as start_odometer,
      LAST_VALUE(odometer_miles) OVER (PARTITION BY car_id, odo_date ORDER BY odometer_miles_updated_at_ms 
                                       ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_odometer,
      COUNT(*) OVER (PARTITION BY car_id, odo_date) as readings_count
    FROM telemetry_with_dates
    WHERE odometer_miles IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY car_id, odo_date ORDER BY odometer_miles_updated_at_ms DESC) = 1
  ),
  
  -- Daily fuel metrics with refueling detection
  daily_fuel AS (
    SELECT 
      car_id,
      fuel_date as date,
      FIRST_VALUE(fuel_remaining_gallons) OVER (PARTITION BY car_id, fuel_date ORDER BY fuel_remaining_gallons_retrieved_at_ms) as start_fuel,
      LAST_VALUE(fuel_remaining_gallons) OVER (PARTITION BY car_id, fuel_date ORDER BY fuel_remaining_gallons_retrieved_at_ms
                                               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_fuel,
      SUM(CASE 
            WHEN fuel_remaining_gallons - LAG(fuel_remaining_gallons) OVER (PARTITION BY car_id, fuel_date ORDER BY fuel_remaining_gallons_retrieved_at_ms) > 1.0
            THEN fuel_remaining_gallons - LAG(fuel_remaining_gallons) OVER (PARTITION BY car_id, fuel_date ORDER BY fuel_remaining_gallons_retrieved_at_ms)
            ELSE 0
          END) OVER (PARTITION BY car_id, fuel_date) as fuel_added_gallons
    FROM telemetry_with_dates
    WHERE fuel_remaining_gallons IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY car_id, fuel_date ORDER BY fuel_remaining_gallons_retrieved_at_ms DESC) = 1
  ),
  
  -- Daily charging activity
  daily_charging AS (
    SELECT 
      car_id,
      charging_date as date,
      MAX(CAST(is_charging AS INT)) > 0 as has_charge
    FROM telemetry_with_dates
    WHERE is_charging IS NOT NULL
    GROUP BY car_id, charging_date
  )
  
  -- Combine all metrics
  SELECT 
    COALESCE(o.car_id, f.car_id, c.car_id) as car_id,
    COALESCE(o.date, f.date, c.date) as date,
    
    -- Miles driven
    COALESCE(GREATEST(o.end_odometer - o.start_odometer, 0), 0.0) as miles_driven,
    
    -- Fuel consumed (accounting for refueling)
    COALESCE(GREATEST(
      CASE 
        WHEN f.start_fuel >= f.end_fuel THEN f.start_fuel - f.end_fuel
        ELSE f.start_fuel + f.fuel_added_gallons - f.end_fuel
      END, 
    0), 0.0) as fuel_consumed_gallons,
    
    -- Charging activity
    COALESCE(c.has_charge, FALSE) as has_charge,
    
    -- Additional metrics
    o.start_odometer,
    o.end_odometer,
    f.start_fuel,
    f.end_fuel,
    COALESCE(f.fuel_added_gallons, 0.0) as fuel_added_gallons,
    COALESCE(o.readings_count, 0) as readings_count,
    
    -- Metadata
    CURRENT_TIMESTAMP() as created_at,
    CURRENT_TIMESTAMP() as updated_at
    
  FROM daily_odometer o
  FULL OUTER JOIN daily_fuel f ON o.car_id = f.car_id AND o.date = f.date
  FULL OUTER JOIN daily_charging c ON COALESCE(o.car_id, f.car_id) = c.car_id 
                                   AND COALESCE(o.date, f.date) = c.date
  WHERE COALESCE(o.date, f.date, c.date) IS NOT NULL
  
) AS source
ON target.car_id = source.car_id AND target.date = source.date
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- ============================================================================
-- Show Summary
-- ============================================================================
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT car_id) as unique_cars,
  SUM(miles_driven) as total_miles_driven,
  ROUND(SUM(fuel_consumed_gallons), 2) as total_fuel_consumed,
  SUM(CAST(has_charge AS INT)) as days_with_charging
FROM hcai_databricks_dev.chargeminder2.daily_vehicle_summary
WHERE date >= CURRENT_DATE - INTERVAL 3 DAY;
```

## 5. Query Examples on Rollup Table

```sql
-- Daily summary for a specific car
SELECT * 
FROM hcai_databricks_dev.chargeminder2.daily_vehicle_summary
WHERE car_id = '65e203ed-88ed-4d38-a5b3-e11a709ffd01'
  AND date >= '2024-01-01'
ORDER BY date DESC;

-- Monthly aggregates
SELECT 
  car_id,
  DATE_TRUNC('month', date) as month,
  SUM(miles_driven) as monthly_miles,
  SUM(fuel_consumed_gallons) as monthly_fuel,
  AVG(miles_driven / NULLIF(fuel_consumed_gallons, 0)) as avg_mpg,
  SUM(CAST(has_charge AS INT)) as days_charged
FROM hcai_databricks_dev.chargeminder2.daily_vehicle_summary
GROUP BY car_id, DATE_TRUNC('month', date)
ORDER BY car_id, month DESC;

-- Fleet-wide daily totals
SELECT 
  date,
  COUNT(DISTINCT car_id) as active_vehicles,
  SUM(miles_driven) as fleet_miles,
  SUM(fuel_consumed_gallons) as fleet_fuel,
  SUM(CAST(has_charge AS INT)) as vehicles_charged
FROM hcai_databricks_dev.chargeminder2.daily_vehicle_summary
WHERE date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY date
ORDER BY date DESC;
```

## 6. Monitoring & Alerts

Add this to your job for monitoring:

```python
# Add to end of main() function

# Create metrics table entry
metrics_data = {
    "job_name": "daily_vehicle_summary",
    "run_date": datetime.now(),
    "processing_start_date": str(start_date),
    "processing_end_date": str(end_date),
    "records_processed": df_daily.count() if df_daily else 0,
    "cars_processed": df_daily.select("car_id").distinct().count() if df_daily else 0,
    "duration_seconds": duration,
    "status": "SUCCESS"
}

spark.createDataFrame([metrics_data]).write.mode("append") \
    .saveAsTable(f"{CONFIG['catalog']}.{CONFIG['schema']}.job_metrics")
```

## Summary

This job:
- ✅ Runs daily at 2 AM PST
- ✅ Processes last 3 days (handles late data)
- ✅ Converts Unix timestamps to PST dates
- ✅ Calculates miles driven (start to end odometer)
- ✅ Calculates fuel consumed (accounts for refueling)
- ✅ Detects charging activity
- ✅ Uses MERGE for idempotent upserts
- ✅ Handles edge cases (missing data, odometer resets, etc.)
- ✅ Partitioned by date for query performance

Here’s one way to design this so you get a **daily PST rollup Delta table** populated by a **scheduled Databricks job**.

# ChatGPT

* Source table: `hcai_databricks_dev.chargeminder2.car_telemetry_raw`
* Target rollup table: `hcai_databricks_dev.chargeminder2.car_daily_rollup`

You can rename to whatever you like.

---

## 1. Create the daily rollup table (Unity Catalog)

```sql
USE CATALOG hcai_databricks_dev;
USE SCHEMA chargeminder2;

CREATE TABLE IF NOT EXISTS car_daily_rollup (
  car_id STRING,
  date DATE,                         -- PST calendar day
  miles_driven DOUBLE,
  fuel_consumed_gallons DOUBLE,
  has_charge BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
USING DELTA
PARTITIONED BY (date);
```

---

## 2. Daily aggregation SQL (for a given PST date)

Key ideas:

* Convert each *_ms column to a **PST local date** using `from_utc_timestamp(..., 'America/Los_Angeles')`.
* `miles_driven` = `max(odometer_miles) - min(odometer_miles)` per `car_id + PST date` (clamped at 0).
* `fuel_consumed_gallons` = `max( fuel_start - fuel_end, 0 )`, where `fuel_start` is the first fuel value of the day, `fuel_end` is the last.
* `has_charge` = `TRUE` if `is_charging` was ever true that PST day.

This query is **idempotent**: it recomputes and MERGEs a single date partition.

```sql
USE CATALOG hcai_databricks_dev;
USE SCHEMA chargeminder2;

-- Pick "yesterday" in PST as the process date
DECLARE process_date DATE;
SET process_date = date_sub(
  date(from_utc_timestamp(current_timestamp(), 'America/Los_Angeles')),
  1
);

-- 1) Miles driven from odometer
WITH odo AS (
  SELECT
    car_id,
    date(
      from_utc_timestamp(
        to_timestamp(odometer_miles_updated_at_ms / 1000.0),
        'America/Los_Angeles'
      )
    ) AS date_pst,
    MIN(odometer_miles) AS odo_min,
    MAX(odometer_miles) AS odo_max
  FROM hcai_databricks_dev.chargeminder2.car_telemetry_raw
  WHERE odometer_miles IS NOT NULL
    AND odometer_miles_updated_at_ms IS NOT NULL
  GROUP BY car_id, date_pst
),

-- 2) Fuel consumption from fuel_remaining
fuel AS (
  SELECT
    car_id,
    date(
      from_utc_timestamp(
        to_timestamp(fuel_remaining_gallons_retrieved_at_ms / 1000.0),
        'America/Los_Angeles'
      )
    ) AS date_pst,
    MIN_BY(
      fuel_remaining_gallons,
      fuel_remaining_gallons_retrieved_at_ms
    ) AS fuel_start,
    MAX_BY(
      fuel_remaining_gallons,
      fuel_remaining_gallons_retrieved_at_ms
    ) AS fuel_end
  FROM hcai_databricks_dev.chargeminder2.car_telemetry_raw
  WHERE fuel_remaining_gallons IS NOT NULL
    AND fuel_remaining_gallons_retrieved_at_ms IS NOT NULL
  GROUP BY car_id, date_pst
),

-- 3) Charging flag
charge AS (
  SELECT
    car_id,
    date(
      from_utc_timestamp(
        to_timestamp(is_charging_updated_at_ms / 1000.0),
        'America/Los_Angeles'
      )
    ) AS date_pst,
    MAX(CASE WHEN is_charging THEN 1 ELSE 0 END) AS has_charge_int
  FROM hcai_databricks_dev.chargeminder2.car_telemetry_raw
  WHERE is_charging_updated_at_ms IS NOT NULL
  GROUP BY car_id, date_pst
),

-- 4) Combine daily metrics
daily AS (
  SELECT
    COALESCE(o.car_id, f.car_id, c.car_id) AS car_id,
    COALESCE(o.date_pst, f.date_pst, c.date_pst) AS date,
    -- miles driven
    COALESCE(
      GREATEST(o.odo_max - o.odo_min, 0.0),
      0.0
    ) AS miles_driven,
    -- fuel consumed
    COALESCE(
      GREATEST(f.fuel_start - f.fuel_end, 0.0),
      0.0
    ) AS fuel_consumed_gallons,
    -- has_charge
    (COALESCE(c.has_charge_int, 0) = 1) AS has_charge
  FROM odo o
  FULL OUTER JOIN fuel f
    ON o.car_id = f.car_id
   AND o.date_pst = f.date_pst
  FULL OUTER JOIN charge c
    ON COALESCE(o.car_id, f.car_id) = c.car_id
   AND COALESCE(o.date_pst, f.date_pst) = c.date_pst
  WHERE COALESCE(o.date_pst, f.date_pst, c.date_pst) = process_date
)

-- 5) Upsert into rollup table
MERGE INTO hcai_databricks_dev.chargeminder2.car_daily_rollup AS t
USING (
  SELECT
    car_id,
    date,
    miles_driven,
    fuel_consumed_gallons,
    has_charge,
    current_timestamp() AS ts
  FROM daily
) AS s
ON t.car_id = s.car_id AND t.date = s.date
WHEN MATCHED THEN UPDATE SET
  t.miles_driven           = s.miles_driven,
  t.fuel_consumed_gallons  = s.fuel_consumed_gallons,
  t.has_charge             = s.has_charge,
  t.updated_at             = s.ts
WHEN NOT MATCHED THEN INSERT (
  car_id,
  date,
  miles_driven,
  fuel_consumed_gallons,
  has_charge,
  created_at,
  updated_at
) VALUES (
  s.car_id,
  s.date,
  s.miles_driven,
  s.fuel_consumed_gallons,
  s.has_charge,
  s.ts,
  s.ts
);
```

You can also replace the `DECLARE/SET process_date` with a job parameter if you want to backfill arbitrary days.

---

## 3. Create the daily Databricks Job (UI)

In Databricks Workflows:

1. Go to **Workflows → Jobs → Create job**.
2. **Task type**:

   * Choose **SQL** (or **SQL query**),
   * Point it at your **SQL Warehouse**.
3. **SQL**: paste the full script above.
4. **Schedule**:

   * Click **Add schedule**.
   * Set **Frequency: Daily**.
   * Set **Time zone: America/Los_Angeles**.
   * Pick a time like **03:00** (3am PST) so all previous-day data is present.
5. Save.

That’s it: each day at ~3am PST the job will:

* Compute `process_date = yesterday in PST`
* Recalculate that day’s metrics
* `MERGE` them into `car_daily_rollup`.

---

If you want, I can next:

* Adjust to your exact source table name, or
* Add **backfill** SQL to run the same logic over a whole date range.
