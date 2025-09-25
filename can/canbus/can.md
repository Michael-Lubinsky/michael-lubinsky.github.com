# CAN Bus
https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial


Telemetry collected from cars via CAN bus is rich and multi-layered. 

Here are the main categories of **data analysis** you can perform with it:

---

## 1. **Descriptive Analytics**

* **Sensor statistics:** Compute averages, medians, standard deviations, min/max values per sensor (e.g., RPM, temperature, speed).
* **Trip summaries:** Distance traveled, duration, fuel/energy consumption, start/end locations.
* **Event counts:** Number of braking events, gear changes, charging events (for EVs), ABS activations, etc.
* **Time-of-day / day-of-week patterns:** Morning vs evening driving behavior, weekdays vs weekends.

---

## 2. **Diagnostic Analytics**

* **Outlier detection:** Spot abnormal sensor readings (e.g., speed > 500 mph, engine temperature spikes).
* **Fault analysis:** Correlate sensor anomalies with fault codes (if available).
* **Lag/gap detection:** Find missing signals or delays between trips.
* **Root cause investigation:** Compare events leading to breakdowns, accidents, or unusual performance.

---

## 3. **Predictive Analytics**

* **Predictive maintenance:** Use vibration, temperature, or pressure trends to forecast failures (e.g., tire wear, brake pad issues).
* **Fuel/energy efficiency models:** Predict expected fuel economy or battery usage under certain conditions.
* **Driver behavior scoring:** Predict accident risks or insurance categories from aggressive driving signals.
* **Trip prediction:** Estimate trip time, route choice, or likely destination.

---

## 4. **Prescriptive Analytics**

* **Optimization recommendations:** Suggest more fuel-efficient driving patterns.
* **Maintenance scheduling:** Recommend proactive servicing when approaching predicted failure thresholds.
* **Fleet management:** Recommend vehicle rotation strategies to balance wear and tear.

---

## 5. **Advanced Analytics**

* **Sensor correlations:** Cross-sensor analysis (e.g., acceleration vs fuel consumption).
* **Clustering:** Group trips or drivers into patterns (e.g., aggressive vs conservative driving styles).
* **Anomaly detection with ML:** Use models to identify sensor streams that deviate from expected patterns.
* **Geospatial analytics:** Overlay trips on maps, analyze city vs highway patterns, charging station usage, congestion.
* **Time-series analysis:** Apply rolling windows, seasonal patterns, forecasting of sensor signals.

---

## 6. **Domain-Specific Insights**

* **For ICE (internal combustion engines):** Engine load cycles, emission estimates, cold start analysis.
* **For EVs:** Charging events, battery health, state-of-charge curves, regenerative braking contribution.
* **Safety analytics:** ABS/EBS activation, traction control usage, near-collision detection from acceleration/gyroscope sensors.



# CAN Bus Telemetry — Reference Pipeline (Raw on Amazon S3)

Below is a production-ready, cloud-agnostic blueprint that keeps your current source of truth on **Amazon S3** and cleanly separates concerns into **Bronze → Silver → Gold** layers, with governance, quality checks, and ML hooks. I tailor this toward **Databricks on AWS (Delta Lake)** because that’s closest to your stack, but I also call out **Snowflake** alternatives where relevant.

---

## 0) High-level architecture

* **Storage (immutable source):** `s3://veh-telemetry/raw/` (append-only, original files; Avro/JSON/CSV/Parquet)
* **Bronze (landing/normalized):** `s3://veh-telemetry/bronze/` (Delta tables; schema-on-write, no business rules)
* **Silver (cleaned/curated):** `s3://veh-telemetry/silver/` (Delta tables; outlier handling, type casting, joins, sessionization, trip segmentation)
* **Gold (analytics/serving):** `s3://veh-telemetry/gold/` (Delta tables; aggregates, features, semantic models)
* **Catalog/Discovery:** AWS Glue Data Catalog or Unity Catalog
* **Orchestration:** MWAA (Airflow) / Step Functions / Databricks Jobs
* **Quality:** Great Expectations / Delta Live Tables expectations
* **Lineage:** Unity Catalog lineage / OpenLineage
* **Analytics/BI:** Databricks SQL, Athena, Snowflake (optional)
* **ML:** Databricks Feature Store for features (driver style, battery health, etc.)

---

## 1) S3 layout & partitioning

```
s3://veh-telemetry/
  raw/{topic}/ingest_date=YYYY-MM-DD/HH=HH/*.json.gz|.parquet
  bronze/
    can_frames/         (partitioned by event_date=YYYY-MM-DD, car_id)
    events/             (...)
    trips/              (derived)
  silver/
    can_signals/        (wide or tall; normalized units; deduped)
    trips/              (sessionized trips)
    signals_by_trip/    (first/last per sensor per trip; diffs)
    charging_events/    (EV-specific)
  gold/
    car_day_stats/      (per-car per-day)
    car_week_stats/     (per-car per-ISO-week)
    sensor_health/      (missingness, drift)
    driver_style/       (clusters / scores)
    features/           (feature store tables)
```

**Partitioning rules**

* Time-dominant fact tables: `event_date=YYYY-MM-DD` (or by hour if high TPS).
* Add `car_id` as **secondary** partitioning *column* (not a path) to keep directories manageable; rely on Z-order / clustering by `car_id`, `trip_id`, `sensor_name`.

---

## 2) Canonical schemas

### 2.1 Raw frame (Bronze)

Tall format (one row per CAN frame):

```
car_id STRING,
car_type STRING,
car_model STRING,
trip_id STRING NULL,
sensor_name STRING,
sensor_value STRING  -- raw, may be bytes/hex/encoded
unit STRING NULL,
event_ts TIMESTAMP,        -- ingestion/source time (UTC)
ingest_ts TIMESTAMP,       -- landing time
src_file STRING,           -- lineage
lat DOUBLE NULL,
lon DOUBLE NULL,
meta MAP<STRING, STRING>   -- VIN, firmware, etc.
```

### 2.2 Clean signal (Silver)

```
car_id STRING,
trip_id STRING,
sensor_name STRING,
value DOUBLE,              -- parsed to numeric; units standardized
unit STRING,
event_ts TIMESTAMP,
event_date DATE,
lat DOUBLE, lon DOUBLE,
quality STRING,            -- "ok" | "outlier" | "imputed" | "missing"
```

### 2.3 Trips (Silver)

```
trip_id STRING,
car_id STRING,
start_ts TIMESTAMP,
end_ts TIMESTAMP,
start_lat DOUBLE, start_lon DOUBLE,
end_lat DOUBLE, end_lon DOUBLE,
duration_sec BIGINT,
distance_km DOUBLE,        -- inferred (optional; haversine)
```

---

## 3) Bronze: ingestion & normalization

**Goal:** Land all files as Delta with minimal transformations (schema alignment, timestamps, basic parsing). Keep it idempotent.

**Databricks PySpark sketch**

```python
from pyspark.sql import functions as F, types as T

raw_path = "s3://veh-telemetry/raw/can/"
bronze_path = "s3://veh-telemetry/bronze/can_frames"

df_raw = (spark.read
  .option("recursiveFileLookup", "true")
  .json(raw_path))  # or .parquet(...)

# Normalize timestamps & minimal columns
df_bronze = (df_raw
  .withColumn("event_ts", F.to_timestamp("timestamp_utc"))  # adapt
  .withColumn("ingest_ts", F.current_timestamp())
  .withColumn("event_date", F.to_date("event_ts"))
  .withColumn("src_file", F.input_file_name())
  .withColumn("sensor_value", F.col("value").cast("string"))
  .select("car_id","car_type","car_model","trip_id","sensor_name","sensor_value",
          "unit","event_ts","event_date","lat","lon","ingest_ts","src_file","meta"))

(df_bronze
  .write.format("delta")
  .mode("append")
  .partitionBy("event_date")
  .save(bronze_path))
```

**Idempotency tip:** Use Auto Loader or file-based checkpoints; if not, dedupe later using `(car_id, sensor_name, event_ts, src_file)`.

---

## 4) Silver: cleaning, type casting, outliers, sessionization

### 4.1 Type casting & units

* Map each `sensor_name` to unit & parser (hex → int, scaling factors).
* Standardize units (e.g., °C, m/s², kW, % SoC).

```python
sensor_ref = spark.createDataFrame([
  ("speed",        "km/h",  1.0,  0.0),
  ("rpm",          "rpm",   1.0,  0.0),
  ("coolant_temp", "°C",    0.1, -40.0),  # example decode
], ["sensor_name","unit","scale","offset"])

bronze = spark.read.format("delta").load(bronze_path)

silver = (bronze.alias("b")
  .join(sensor_ref.alias("r"), "sensor_name", "left")
  .withColumn("value_raw", F.col("sensor_value").cast("double"))
  .withColumn("value", F.col("value_raw")*F.col("r.scale") + F.col("r.offset"))
  .withColumn("unit_std", F.coalesce("r.unit","unit"))
  .withColumn("quality", F.lit("ok"))
  .select("b.car_id","b.trip_id","b.sensor_name","value","unit_std","event_ts","event_date","lat","lon","quality"))

silver.write.format("delta").mode("append").partitionBy("event_date").save("s3://veh-telemetry/silver/can_signals")
```

### 4.2 Robust outlier handling (MAD-based z-score + Winsorization)

* For each `(car_id, sensor_name, event_date)` window:

  * Compute **median** and **MAD**; flag `|z| > 6` as outliers.
  * Optionally **winsorize** aggregated metrics to p01/p99 when insight > precision.

```python
w = (Window.partitionBy("car_id","sensor_name","event_date"))
signals = spark.read.format("delta").load("s3://veh-telemetry/silver/can_signals")

median = F.expr("percentile_approx(value, 0.5)")
p50 = signals.withColumn("med", median.over(w))
mad = signals.withColumn("abs_dev", F.abs(F.col("value")-F.col("med"))) \
             .withColumn("mad", F.expr("percentile_approx(abs_dev, 0.5)").over(w))

clean = (p50.join(mad.select("car_id","sensor_name","event_date","mad").distinct(),
                  ["car_id","sensor_name","event_date"], "left")
  .withColumn("robust_z", (F.col("value")-F.col("med"))/(F.col("mad")+F.lit(1e-9)))
  .withColumn("quality", F.when(F.abs("robust_z")>6, "outlier").otherwise("ok")))

clean.write.format("delta").mode("overwrite").option("overwriteSchema","true").saveAsTable("silver.can_signals_clean")
```

### 4.3 Trip sessionization

* Define session gap (e.g., **≥ 20 minutes** inactivity starts a new trip).
* Or use ignition on/off if available.

```python
wtime = Window.partitionBy("car_id").orderBy("event_ts")
frames = spark.read.table("silver.can_signals_clean") \
            .filter("sensor_name='speed'") \
            .select("car_id","event_ts","lat","lon")

with_lag = frames.withColumn("prev_ts", F.lag("event_ts").over(wtime))
gapped = with_lag.withColumn("gap_min", F.when(F.col("prev_ts").isNull(), 9999)
                                       .otherwise(F.col("event_ts").cast("long")-F.col("prev_ts").cast("long"))/60.0)
trips = gapped.withColumn("new_trip", F.when(F.col("gap_min")>=20,1).otherwise(0))
trips = trips.withColumn("trip_num", F.sum("new_trip").over(wtime))
trips = trips.withColumn("trip_id", F.concat_ws("_","car_id",F.col("trip_num").cast("string")))

trips.write.format("delta").mode("overwrite").saveAsTable("silver.trips")
```

### 4.4 First/last & deltas per sensor per trip

```sql
-- first/last & difference per sensor within a trip
CREATE OR REPLACE VIEW silver.signals_by_trip AS
SELECT
  car_id, trip_id, sensor_name,
  FIRST_VALUE(value)  OVER (PARTITION BY car_id,trip_id,sensor_name ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_value,
  LAST_VALUE(value)   OVER (PARTITION BY car_id,trip_id,sensor_name ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)  AS last_value,
  (LAST_VALUE(value) OVER (PARTITION BY car_id,trip_id,sensor_name ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
   - FIRST_VALUE(value) OVER (PARTITION BY car_id,trip_id,sensor_name ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)) AS delta_value
FROM silver.can_signals_clean;
```

### 4.5 EV charging events

* Heuristics: SoC rising; plug-in flag; power_kW > threshold at low speed; location at known charger.

```sql
CREATE OR REPLACE VIEW silver.charging_events AS
WITH e AS (
  SELECT car_id, event_ts, value AS soc
  FROM silver.can_signals_clean
  WHERE sensor_name='soc'
),
d AS (
  SELECT car_id, event_ts, soc,
         soc - LAG(soc) OVER (PARTITION BY car_id ORDER BY event_ts) AS dsoc
  FROM e
)
SELECT *
FROM d
WHERE dsoc >= 1.0  -- rising SoC indicates charging
QUALIFY SUM(CASE WHEN dsoc >= 1.0 THEN 1 ELSE 0 END)
        OVER (PARTITION BY car_id ORDER BY event_ts
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) >= 1;
```

---

## 5) Gold: curated analytics & features

### 5.1 Daily/weekly car stats (winsorized)

```sql
CREATE OR REPLACE TABLE gold.car_day_stats AS
SELECT
  car_id,
  DATE(event_ts) AS day,
  COUNT_IF(quality='ok') AS ok_points,
  APPROX_PERCENTILE(value, 0.5) FILTER (WHERE quality='ok') AS median_value,
  PERCENTILE(value, 0.01) FILTER (WHERE quality='ok') AS p01,
  PERCENTILE(value, 0.99) FILTER (WHERE quality='ok') AS p99,
  AVG(CASE WHEN value < p01 THEN p01 WHEN value > p99 THEN p99 ELSE value END) AS mean_winsor
FROM silver.can_signals_clean
GROUP BY car_id, DATE(event_ts);
```

### 5.2 Driver style scoring (example)

* Compute features: harsh brakes/accels per 100 km, mean/var of speed, idle ratio.
* Cluster (KMeans) into styles; persist `gold.driver_style`.

### 5.3 Sensor health / completeness

* Missingness by `(car_id, sensor_name, day)`.
* Drift tests (KS/AD vs trailing window).
* Output to `gold.sensor_health`.

### 5.4 Feature Store (for ML)

* Keyed by `(car_id, day)`; versioned.
* Examples: `avg_speed`, `std_speed`, `brake_events`, `soc_drop_max`, `energy_kwh_per_100km`.

---

## 6) Orchestration & SLAs

**Recommended cadence**

* **Bronze**: micro-batch every 5–15 minutes (Auto Loader) or hourly.
* **Silver**: hourly + daily consolidation jobs.
* **Gold**: daily at T+1 for heavy aggregations; some hourly (e.g., near-real-time).

**Airflow (MWAA) DAG outline**

1. `land_bronze`: discover new S3 objects → append to Delta Bronze
2. `build_silver`: clean, outliers, sessionization, trips
3. `build_gold`: rollups, health, features
4. `publish`: refresh Databricks SQL dashboards / notify

Include **checkpointing**, **idempotent writes** (MERGE on natural keys), and **backfills** (date range parameter).

---

## 7) Data quality & governance

* **Contracts**: maintain a schema registry per `sensor_name` (range, unit, decode).
* **Expectations** (Great Expectations / DLT):

  * `value` within allowed range (per sensor)
  * `event_ts` monotonicity (allow clock skew)
  * Missing rate thresholds (alert when exceeded)
* **Lineage**: enable Unity Catalog lineage to trace from Gold back to raw file.
* **Access**: table ACLs by layer; PII scrubbing if VIN considered sensitive.
* **SCD/slowly changing**: if car metadata (firmware, model year) changes, store in a `silver.car_dim` with `valid_from/valid_to` and join using `event_ts`.

---

## 8) Performance & cost controls

* **File sizes:** target 128–512 MB parquet files; use `OPTIMIZE ZORDER BY (car_id, trip_id, sensor_name, event_ts)`.
* **Partition pruning:** filter by `event_date` always; use `event_ts BETWEEN` for pushdown.
* **Caching:** cache small dimensions (sensor decode maps).
* **Skew handling:** detect hot keys (e.g., fleet test cars); salt if necessary.
* **Compaction:** weekly optimize + vacuum (retain ≥7 days).
* **Autoscaling clusters** with spot instances where appropriate.

---

## 9) BI & serving patterns

* **Databricks SQL**: semantic views for dashboards (trips, charging, daily/weekly stats).
* **Athena**: external tables on Delta/Iceberg for lightweight querying.
* **Snowflake option**:

  * Create external stage to S3 Bronze/Silver; define **external tables** or COPY INTO internal tables for Gold.
  * Use **Dynamic Tables** to maintain Gold rollups with incremental refresh.

---

## 10) Security & compliance

* **S3 bucket policy**: VPC endpoints; block public access.
* **KMS**: SSE-KMS encryption for buckets.
* **Secrets**: AWS Secrets Manager / Databricks Secrets; never hard-code.
* **Audit**: CloudTrail + table-level logs.

---

## 11) Minimal end-to-end job set (Databricks Jobs)

1. **`bronze_load_can_frames`**
   Input: `s3://veh-telemetry/raw/...`
   Output: `delta:bronze.can_frames` (partitioned by `event_date`)
   Idempotent: yes (file lists/checkpoints)

2. **`silver_build_signals_trips`**

* Parse & standardize units
* Robust outliers (`|z|>6` MAD) + label quality
* Sessionize trips
  Outputs: `silver.can_signals_clean`, `silver.trips`, `silver.signals_by_trip`, `silver.charging_events`

3. **`gold_rollups`**

* Daily/weekly per car; weekday vs weekend; morning vs evening comparisons
* Sensor health & completeness
* Driver style clustering (optional nightly ML)
  Outputs: `gold.car_day_stats`, `gold.car_week_stats`, `gold.sensor_health`, `gold.driver_style`, `gold.features_*`

---

## 12) Example: Weekday vs weekend, morning vs evening

```sql
CREATE OR REPLACE VIEW gold.speed_time_slices AS
WITH base AS (
  SELECT
    car_id,
    event_ts,
    value AS speed_kmh,
    CASE WHEN date_format(event_ts, 'E') IN ('Sat','Sun') THEN 'weekend' ELSE 'weekday' END AS day_type,
    CASE
      WHEN hour(event_ts) BETWEEN 5 AND 10  THEN 'morning'
      WHEN hour(event_ts) BETWEEN 17 AND 21 THEN 'evening'
      ELSE 'other' END AS day_part
  FROM silver.can_signals_clean
  WHERE sensor_name='speed' AND quality='ok'
)
SELECT car_id, day_type, day_part,
       AVG(speed_kmh) AS avg_speed,
       APPROX_PERCENTILE(speed_kmh,0.5) AS median_speed,
       STDDEV(speed_kmh) AS std_speed,
       COUNT(*) AS n_samples
FROM base
GROUP BY car_id, day_type, day_part;
```

---

## 13) How to extend to ML (predictive maintenance & energy)

* **Labels**: use repair logs/fault codes to label positive failure windows.
* **Features**: rolling stats (mean, std, spikes), utilization, thermal cycles, voltage ripple, vibration bands.
* **Pipelines**: AutoML baseline → custom models (XGBoost, LSTM).
* **Monitoring**: drift in `gold.sensor_health`, prediction stability, A/B of thresholds.

---

## 14) Snowflake quick notes (if you want both)

* Create an **external stage** to S3 and **external tables** over your **Silver** Delta/Iceberg.
* Materialize **Gold** in Snowflake with **Dynamic Tables** (incremental by `event_date`).
* Use **Streams & Tasks** for change capture from Silver → Gold.

---

## 15) Operational runbook (essentials)

* **Backfill**: parameterize by `event_date` range; rerun Bronze→Gold safely (MERGE keys).
* **Hotfix**: patch Decode Map → reprocess Silver for affected sensors/dates only; ripple recalculation in Gold.
* **Alerts**:

  * Data delay (no Bronze arrivals in 60 min)
  * Missingness > threshold in `sensor_health`
  * Outlier rate spike for any `(sensor_name, car_type)`
* **Cost guardrails**: enforce cluster max size, enable photon/DBIO, schedule OPTIMIZE weekly.

---

If you want, I can generate:

* Databricks **Jobs JSON** (Bronze/Silver/Gold) with parameters,
* A ready-to-run **Airflow DAG** calling Databricks runs,
* **Great Expectations** suites for key tables,
* A **Snowflake** variant (stages + dynamic tables) side-by-side.
