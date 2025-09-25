## CAN (Controller Area Network) Bus protocol

<https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial>

<https://www.cartrack.co.za/blog/what-is-canbus-and-how-does-it-work>

<https://www.cartrack.co.za/blog/can-bus-system-a-powerful-partnership-for-fleet-data-and-efficiency>


Telemetry collected from cars via CAN bus is rich and multi-layered. 

Here are the main categories of **data analysis** you can perform with it:


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



## CAN Bus Telemetry — Reference Pipeline (Raw on Amazon S3)

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

Got it — assuming you meant **CAN bus** (typo “CN”). Here’s a practical, production-ready way to **detect EV charging events** from CAN signals, including robust rules, a finite-state machine, and example implementations (PySpark on Databricks and SQL on Snowflake/DB SQL).

# 1) What signals typically indicate charging?

You may have some (not all) of these; use what you have.

* **SoC / State of Charge**: `soc` (0–100%).
  • Rises monotonically (after smoothing) when charging; may pause at plateau steps.
* **Battery current / voltage**: `pack_current` (A), `pack_voltage` (V).
  • **AC charging**: positive charge current into battery at low vehicle speed.
  • **DC fast**: high current and usually higher/steady voltage.
* **Charge power**: `charge_power_kw = pack_current * pack_voltage / 1000`.
  • Above a threshold (e.g., ≥ 1.5–2.0 kW) signals active charging.
* **Plug / inlet flags**: `plug_present`, `charging_enabled`, `charger_status`, `evse_pilot`, `ac_dc_mode`.
  • Very strong evidence if present.
* **Gear & speed**: `gear` = Park/Neutral; `speed` ≈ 0 km/h.
* **Port / door**: `charge_port_open` helpful for start/end edges.
* **Onboard charger state codes**: “charging”, “complete”, “fault”.

# 2) Core detection logic (hierarchy of evidence)

Use a hierarchical approach, falling back when richer signals don’t exist.

**Tier A — Explicit flags (best):**
Start when `plug_present=1 AND charging_enabled=1` (or `charger_status in ('charging','dc_fast')`).
End when `charging_enabled=0` or `plug_present=0`.

**Tier B — Electrical thresholds (reliable):**

* Start when `charge_power_kw >= P_ON` (e.g., `P_ON=2.0`) **AND** `speed <= 1 km/h`.
* End when `charge_power_kw <= P_OFF` (e.g., `P_OFF=0.8`) for ≥ `t_off` seconds.
* Use **hysteresis**: `P_ON > P_OFF` to prevent flapping.

**Tier C — SoC-only fallback (last resort):**

* Start when **smoothed** `soc` shows sustained increase: `ΔSoC >= 0.3%` over `T` minutes (e.g., 5–10 min), speed ≈ 0.
* End when `soc` stops rising for ≥ `t_off` or speed > threshold.
* Guard against **regen** during downhill driving by requiring near-zero speed for SoC-based starts.

# 3) State machine (recommended)

Model as a simple FSM with debouncing:

States: `IDLE → PLUGGED → CHARGING → TOPPING → COMPLETE/UNPLUGGED → IDLE`

* **IDLE → PLUGGED:** `plug_present==1` or `charge_port_open==1`
* **PLUGGED → CHARGING:** `charging_enabled==1` OR `charge_power_kw >= P_ON` (for ≥ `t_on`)
* **CHARGING → TOPPING (optional):** power drops below `P_TOP` but still enabled; SoC ~ 80–100%
* **CHARGING/TOPPING → COMPLETE:** `charging_enabled==0` OR `charge_power_kw <= P_OFF` for ≥ `t_off`, and SoC near prior peak
* **Any → UNPLUGGED:** `plug_present==0`
* **UNPLUGGED → IDLE:** stabilize for `t_idle` seconds

**Debounce windows** (typical): `t_on=60–120s`, `t_off=180–300s`, sample period 1–5s.

# 4) Event/sessionization outputs

For each charging session, emit:

* `car_id`, `charge_session_id`
* `start_ts`, `end_ts`, `duration_sec`
* **Energy added (kWh)**: integrate `max(pack_current*pack_voltage,0)/1000` over time.
* **Max/avg power (kW)**, **final SoC**, **start/end SoC**, `ΔSoC`
* `charging_mode` (“AC_L2”, “DC_Fast”, “Unknown”) heuristic by `max_power`:
  • DC fast: `max_power >= 40 kW` (tune)
  • AC L2: `2–19 kW`
* **Location**: median(lat,lon) during the session; optional reverse-geocode to station.
* **Quality flags**: missing data %, clock skew detected, gaps filled.

# 5) PySpark (Databricks) reference implementation

Assumes a tall silver table `silver.can_signals_clean`:

```
car_id STRING, sensor_name STRING, event_ts TIMESTAMP, value DOUBLE,
unit STRING, event_date DATE, speed_kmh DOUBLE?, pack_current_a DOUBLE?, pack_voltage_v DOUBLE?, soc DOUBLE?,
plug_present INT?, charging_enabled INT?, charge_port_open INT?
```

```python
from pyspark.sql import functions as F, Window as W

signals = spark.table("silver.can_signals_clean")

# Pivot minimal sensors you have (speed, current, voltage, soc, flags)
needed = (signals
  .filter(F.col("sensor_name").isin("speed","pack_current","pack_voltage","soc",
                                    "plug_present","charging_enabled","charge_port_open"))
  .groupBy("car_id","event_ts")
  .pivot("sensor_name")
  .agg(F.first("value"))
  .withColumnRenamed("pack_current","pack_current_a")
  .withColumnRenamed("pack_voltage","pack_voltage_v")
  .withColumnRenamed("speed","speed_kmh")
)

df = (needed
  .withColumn("charge_power_kw",
              (F.coalesce(F.col("pack_current_a"),F.lit(0.0)) *
               F.coalesce(F.col("pack_voltage_v"),F.lit(0.0)))/1000.0)
  .withColumn("speed_kmh", F.coalesce("speed_kmh", F.lit(0.0)))
  .withColumn("soc", F.coalesce("soc", F.lit(None).cast("double")))
  .withColumn("plug_present", F.col("plug_present").cast("int"))
  .withColumn("charging_enabled", F.col("charging_enabled").cast("int"))
  .withColumn("charge_port_open", F.col("charge_port_open").cast("int"))
)

# Parameters (tune per fleet)
P_ON  = F.lit(2.0)   # kW
P_OFF = F.lit(0.8)   # kW
V_NEAR_ZERO = F.lit(1.0) # km/h
T_ON  = 2*60         # seconds debounce
T_OFF = 3*60         # seconds debounce

# Sort by time per car
w_time = W.partitionBy("car_id").orderBy("event_ts")

# Basic “is_charging_evidence” signal (combine tiers)
df1 = (df
  .withColumn("flag_explicit",
              (F.col("charging_enabled")==1) | (F.col("plug_present")==1))
  .withColumn("flag_power",
              (F.col("charge_power_kw") >= P_ON) & (F.col("speed_kmh") <= V_NEAR_ZERO))
)

# Debounce with running durations above/below thresholds
# Convert to 1/0 and compute consecutive streak lengths
def streak(colname):
    return (F.when(F.col(colname), 1).otherwise(0)).alias(colname)

df2 = (df1
  .withColumn("evidence_on",  F.when(F.col("flag_explicit") | F.col("flag_power"), 1).otherwise(0))
  .withColumn("evidence_off", F.when((F.col("charge_power_kw") <= P_OFF) | (F.col("charging_enabled")==0) | (F.col("plug_present")==0), 1).otherwise(0))
)

# Compute time deltas to approximate streak durations
df2 = df2.withColumn("prev_ts", F.lag("event_ts").over(w_time)) \
         .withColumn("dt_sec", (F.col("event_ts").cast("long")-F.col("prev_ts").cast("long")).cast("int")) \
         .fillna({"dt_sec":0})

# Accumulate evidence_on seconds until reset by evidence_off, and vice versa
# (Simple approach: running sums with resets using stateful aggregation in a subsequent streaming job
#  or use a Python UDF state machine for batch.)

# For clarity, use a small Python state machine per car (pandas_udf):
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType, LongType
import pandas as pd

schema = StructType([
    StructField("car_id", StringType()),
    StructField("event_ts", TimestampType()),
    StructField("charge_session_id", StringType()),
    StructField("state", StringType()),
    StructField("charge_power_kw", DoubleType()),
    StructField("soc", DoubleType())
])

@F.pandas_udf(schema, F.PandasUDFType.GROUPED_MAP)
def detect_sessions(pdf: pd.DataFrame) -> pd.DataFrame:
    pdf = pdf.sort_values("event_ts")
    P_ON  = 2.0
    P_OFF = 0.8
    T_ON  = 120
    T_OFF = 180

    state = "IDLE"
    on_secs = 0
    off_secs = 0
    last_ts = None
    session_id = None
    rows = []

    for _, r in pdf.iterrows():
        ts = r["event_ts"]
        dt = 0 if last_ts is None else max(0, (ts - last_ts).total_seconds())
        last_ts = ts

        flag_explicit = bool(r.get("charging_enabled", 0) == 1 or r.get("plug_present", 0) == 1)
        flag_power = (r.get("charge_power_kw", 0.0) or 0.0) >= P_ON and (r.get("speed_kmh", 0.0) or 0.0) <= 1.0
        power_low = (r.get("charge_power_kw", 0.0) or 0.0) <= P_OFF
        unplugged = (r.get("plug_present", 1) or 1) == 0

        evidence_on = flag_explicit or flag_power
        evidence_off = power_low or unplugged or (r.get("charging_enabled", 1) or 1)==0

        if evidence_on:
            on_secs += dt
            off_secs = 0
        elif evidence_off:
            off_secs += dt
            on_secs = 0
        else:
            on_secs = max(0, on_secs - dt)  # decay
            off_secs = max(0, off_secs - dt)

        if state in ("IDLE","PLUGGED"):
            if on_secs >= T_ON:
                state = "CHARGING"
                session_id = f"{r['car_id']}_{int(ts.timestamp())}"
        if state == "CHARGING":
            if off_secs >= T_OFF:
                state = "IDLE"
                session_id = None

        rows.append([r["car_id"], ts, session_id, state, r.get("charge_power_kw", None), r.get("soc", None)])

    return pd.DataFrame(rows, columns=[c.name for c in schema.fields])

sessions = (df2.groupBy("car_id").apply(detect_sessions).cache())

# Materialize session boundaries + metrics
w_sess = W.partitionBy("car_id","charge_session_id")

charging_events = (sessions
  .filter(F.col("state")=="CHARGING")
  .groupBy("car_id","charge_session_id")
  .agg(
      F.min("event_ts").alias("start_ts"),
      F.max("event_ts").alias("end_ts"),
      (F.max("event_ts").cast("long")-F.min("event_ts").cast("long")).alias("duration_sec"),
      F.max("charge_power_kw").alias("max_power_kw"),
      F.expr("max_by(soc, event_ts)").alias("end_soc"),
      F.expr("min_by(soc, event_ts)").alias("start_soc")
  )
  .withColumn("delta_soc", F.col("end_soc") - F.col("start_soc"))
)

charging_events.createOrReplaceTempView("charging_events_tmp")

spark.sql("""
CREATE OR REPLACE TABLE gold.charging_events AS
SELECT
  car_id, charge_session_id, start_ts, end_ts, duration_sec,
  max_power_kw, start_soc, end_soc, delta_soc
FROM charging_events_tmp
WHERE duration_sec >= 120      -- prune spurious
""")
```

**Energy added (kWh):** integrate within each session; for batch, join samples back to sessions and sum `power * dt`.

```python
samples = df2.select("car_id","event_ts","charge_power_kw")
evt = charging_events.select("car_id","charge_session_id","start_ts","end_ts")

joined = (samples.join(evt, ["car_id"])
  .where((samples.event_ts >= evt.start_ts) & (samples.event_ts <= evt.end_ts))
  .withColumn("prev_ts", F.lag("event_ts").over(W.partitionBy("car_id","charge_session_id").orderBy("event_ts")))
  .withColumn("dt_h", (F.col("event_ts").cast("long")-F.col("prev_ts").cast("long"))/3600.0)
  .fillna({"dt_h":0.0})
  .withColumn("energy_kwh", F.greatest(F.col("charge_power_kw"),F.lit(0.0))*F.col("dt_h"))
  .groupBy("car_id","charge_session_id")
  .agg(F.sum("energy_kwh").alias("energy_kwh"))
)

final = charging_events.join(joined, ["car_id","charge_session_id"], "left") \
                       .withColumn("mode",
                         F.when(F.col("max_power_kw") >= 40, "DC_Fast")
                          .when(F.col("max_power_kw") >= 2, "AC_L2")
                          .otherwise("Unknown"))

final.write.mode("overwrite").saveAsTable("gold.charging_events_enriched")
```

# 6) Pure SQL approach (Snowflake / Databricks SQL)

If you’ve already computed `charge_power_kw`, `speed_kmh`, and flags into a tall table `signals_pivoted`:

```sql
-- 1) Evidence flags with hysteresis bands
CREATE OR REPLACE VIEW silver.charge_evidence AS
SELECT
  car_id, event_ts, charge_power_kw, speed_kmh, soc,
  plug_present, charging_enabled,
  (charging_enabled = 1 OR plug_present = 1) AS flag_explicit,
  (charge_power_kw >= 2.0 AND speed_kmh <= 1.0) AS flag_power,
  (charge_power_kw <= 0.8 OR NVL(charging_enabled,0)=0 OR NVL(plug_present,1)=0) AS flag_off
FROM silver.signals_pivoted;

-- 2) Sessionization (simplified): mark starts/ends
WITH evidence AS (
  SELECT *,
         CASE WHEN (flag_explicit OR flag_power) THEN 1 ELSE 0 END AS e_on,
         CASE WHEN flag_off THEN 1 ELSE 0 END AS e_off
  FROM silver.charge_evidence
),
marks AS (
  SELECT *,
         CASE WHEN e_on = 1 AND LAG(e_on) OVER (PARTITION BY car_id ORDER BY event_ts) = 0 THEN 1 ELSE 0 END AS start_mark,
         CASE WHEN e_off = 1 AND LAG(e_off) OVER (PARTITION BY car_id ORDER BY event_ts) = 0 THEN 1 ELSE 0 END AS off_mark
  FROM evidence
),
groups AS (
  SELECT *,
         SUM(CASE WHEN start_mark=1 THEN 1 ELSE 0 END)
         OVER (PARTITION BY car_id ORDER BY event_ts
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS grp
  FROM marks
)
SELECT car_id,
       CONCAT(car_id,'_',MIN(TO_CHAR(event_ts,'YYYYMMDDHH24MISS'))) AS charge_session_id,
       MIN(event_ts) AS start_ts,
       MAX(event_ts) AS end_ts
FROM groups
WHERE e_on = 1
GROUP BY car_id, grp
HAVING DATEDIFF('second', MIN(event_ts), MAX(event_ts)) >= 120;
```

(For strict hysteresis/debouncing in pure SQL, add rolling window counts on `e_on/e_off` ≥ N samples before confirming start/end.)

# 7) Edge cases & hardening

* **Regen braking**: rises in SoC while moving → require low speed for SoC-based start.
* **Clock skew / drops**: fill small gaps; cap `dt` between samples to avoid energy spikes.
* **Partial sessions**: if data starts mid-charge, mark `start_type='partial'`.
* **Tapering**: long “top-off” at low power near 100% SoC; keep it inside session using `t_off` debounce.
* **Home vs public**: cluster location by station centroid; label from POI lookup if available.
* **AC vs DC**: decide based on `max_power_kw`, `ac_dc_mode`, or voltage/current signature.

# 8) Minimal tests (sanity checks)

* A: Synthetic trace: `plug_present=1`, `power=7kW` for 45 min, speed 0 → **one** session; `ΔSoC` ≈ expected.
* B: Add 2-minute power dip to 0.5 kW → session **continues** (debounce).
* C: SoC increases 1% while speed 60 km/h → **no** session (regen).
* D: DC fast profile at 120 kW for 15 min → mode “DC_Fast”.

---

If you share what exact signals you have (names/units), I can plug them into the templates above and hand you a drop-in notebook (bronze→silver transforms + charging detector + gold event table).
