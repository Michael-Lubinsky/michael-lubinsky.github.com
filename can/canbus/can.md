## CAN (Controller Area Network) Bus protocol

<https://en.wikipedia.org/wiki/CAN_bus>


CAN bus data is collected inside the vehicle, uploaded in raw form, and decoded into readable signals later. Here's the chain in the order the data moves.

**1. What is on the bus**

The CAN bus is the network that connects a car's electronic control units (ECUs): engine, battery management, brakes, charger, and others. Each ECU broadcasts short messages called *frames*. A frame has:
- an **arbitration ID** (for example `0x3A2`), which identifies the message type;
- up to **8 bytes of payload** (64 bytes with CAN FD);
- a **timestamp**, which the logger adds when it receives the frame.

The payload is raw bits. One frame may pack several signals, such as state of charge in bits 0–9 and battery temperature in bits 16–23, each with its own scale and offset. Messages repeat at fixed rates, typically every 10–100 ms. A single car can produce thousands of frames per second.

**2. How it is collected**

- **Data loggers** such as Vector, CSS Electronics CANedge, or Kvaser plug into the OBD-II port or tap the bus directly. They record every frame to an SD card or SSD. Research and test fleets use these.
- **Telematics control unit (TCU)**: the car's built-in modem. It reads selected signals, usually downsampled or event-triggered, and sends them over cellular to the manufacturer's cloud. This is what connected-vehicle APIs expose, which is why cloud data is sparse compared to the raw bus.
- **OBD-II dongles** query standard diagnostic values on request (PIDs) instead of passively listening. They are cheaper but give fewer signals.

**3. Decoding**

Raw frames are meaningless without a **DBC file**, the decoding dictionary. For each message ID it lists every signal's start bit, length, byte order, scale, offset, and unit. For example: physical value = raw × 0.1 + 0, unit %. Manufacturers keep their DBCs proprietary. Research teams either get them under agreement or reverse-engineer signals. In Python, the usual tools are `cantools` or `python-can`.

**4. How it is stored**

| Stage | Format | Why |
| --- | --- | --- |
| On the logger | MF4 (ASAM MDF4), BLF (Vector), ASC, or candump `.log` | Compact binary, keeps exact timestamps |
| Raw landing in the cloud | The same files in S3 or ADLS, partitioned by vehicle and date | Immutable source you can always replay |
| Robotics equivalent | ROS bags or MCAP | Same idea: timestamped multi-channel messages |
| Decoded (silver) | Parquet or Delta, long format: `vehicle_id, ts, signal_name, value` | Handles hundreds of signals and new signals without schema changes |
| Analytics (gold) | Wide, resampled tables (for example 1 Hz or 1-minute), plus derived trips and charge sessions | Easy SQL and dashboards |

Partition decoded data by date and vehicle, and cluster or Z-order by signal name. Most queries ask for a few signals over a time range.

**5. Data-quality issues worth mentioning in an interview**

- Clock drift between the logger and GPS time.
- Dropped frames and gaps when the vehicle sleeps.
- A wrong DBC version, which produces garbage values.
- Counter rollover.
- Duplicate uploads after a retry.

Keep the raw files plus the DBC version used to decode them. Then a corrected DBC simply triggers a backfill from raw.

**Interview angle:** this maps directly to MRS. Robot teleoperation data in MCAP or ROS bags is the same problem: high-frequency raw logs in object storage, a decoding layer, and a metadata layer on top that answers "how much data, from which station, and at what quality."

I can add a short version of this to the prep doc if you'd like.
<https://cardog.app/blog/autonomous-driving-stack-technical-guide>

<https://github.com/ajouatom/canbus-tools>

<https://github.com/iDoka/awesome-canbus>

<https://youtu.be/v_y65h68z3U>  Learn How The CAN Bus Works

https://emqx.medium.com/can-bus-how-it-works-pros-and-cons-and-fast-local-processing-tutorial-a6543a8ef713

<https://www.csselectronics.com/pages/chatgpt-can-bus-data-time-series-code-interpreter>

<https://www.autopi.io/blog/how-to-read-can-bus-data/>

<https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial>

<https://blog.prosig.com/2023/05/19/understanding-can-bus-the-nervous-system-of-a-modern-vehicle/>

<https://www.cartrack.co.za/blog/what-is-canbus-and-how-does-it-work>

<https://www.cartrack.co.za/blog/can-bus-system-a-powerful-partnership-for-fleet-data-and-efficiency>

 
https://ruptela.com/decode-can-bus-messages-guide/


<https://www.picotech.com/library/knowledge-bases/oscilloscopes/can-bus-serial-protocol-decoding>

## Data analysis
<https://www2.eecs.berkeley.edu/Pubs/TechRpts/2022/EECS-2022-151.pdf>

<https://www.researchgate.net/publication/228936619_Analysis_and_Classification_of_Driver_Behavior_Using_in-Vehicle_CAN-BUS_Information>

<https://deepblue.lib.umich.edu/bitstream/handle/2027.42/171757/Han_Thesis_Final.pdf?sequence=1>

<https://www.csselectronics.com/pages/chatgpt-can-bus-data-time-series-code-interpreter>

Driving Behavior Analysis through CAN Bus
Data

<https://senseable.mit.edu/papers/pdf/20181105_Fugiglando-etal_DrivingBehavior_IEEE-TITS.pdf>

Traffic anomaly detection algorithm for CAN bus using similarity analysis
(PDF)

https://www.sciencedirect.com/science/article/pii/S2667295224000102


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

# How to Present Your Samsung GPS and IMU Data Project in the Meta Robotics Interview

Your Samsung project collecting GPS and IMU (Inertial Measurement Unit) data from mobile phones could be one of your strongest examples for the Meta Robotics Studio interview.

It is particularly relevant because mobile phones and robots share important data-engineering challenges:

- Multiple sensors producing timestamped measurements at different frequencies.
- Large volumes of time-series data.
- Missing, delayed, duplicated, and out-of-order records.
- Sensor synchronization and data quality validation.
- Raw data storage, structured analytics, and reporting.
- Historical reprocessing when processing logic changes.

The key is to present your Samsung work as a sensor data collection and operational analytics platform, rather than simply another ETL project.

I would structure your explanation into six parts: business objective, architecture, file formats, data quality, backfills, and reporting.

One important qualification: your resume confirms Samsung data engineering experience, but does not specify the implementation details of this particular GPS/IMU project. I'll distinguish recommended technical explanations from details you should only claim if they match your actual implementation.

## 1. Start with a two-minute project explanation

At Samsung, I worked on a data engineering project involving GPS and IMU sensor data collected from mobile phones.

The main technical challenge was transforming raw sensor measurements into reliable, structured time-series datasets that could support analysis and reporting.

GPS provided location, speed, and movement information, while IMU sensors, such as accelerometers and gyroscopes, captured device acceleration and angular velocity.

These sensors produce data at different sampling rates, and their measurements may contain missing records, irregular timestamps, noisy values, and gaps caused by device or application behavior.

My data engineering focus was on processing this data at scale, validating its quality, organizing it into efficient analytical tables, and making the results available for downstream analytics.

The project is especially relevant to Meta Robotics because robot data collection involves similar challenges: managing heterogeneous sensor streams, ensuring data completeness and synchronization, tracking collection quality, and building reliable reporting on top of raw sensor data.

If you were also responsible for ingestion, infrastructure, dashboards, or the complete architecture, state that explicitly. The interviewer will want to understand which components you personally designed and owned.

## 2. Data flow: Explain the end-to-end architecture

Here is an illustrative architecture using technologies from your Samsung experience.

Samsung mobile phones

GPS, accelerometer, gyroscope, device/session metadata

Mobile data collection and upload

Timestamped sensor events, local buffering, batch upload

Raw object storage — AWS S3

Original files preserved for replay and auditing

Airflow orchestration

Spark / PySpark processing

Parsing, schema validation, timestamp normalization, deduplication

Curated time-series tables

Parquet / analytical warehouse tables

Daily aggregates and quality metrics

Collection duration, gaps, sensor availability, device health

Tableau / Grafana dashboards

Collection monitoring, data quality, historical trends

Reference architecture for discussing the project. Confirm which components and storage systems were actually used at Samsung.

### How to explain this architecture

I would emphasize three engineering decisions.

First, preserve the raw sensor data. GPS and IMU processing algorithms may change, and raw files allow historical reprocessing without collecting data again.

Second, separate ingestion from analytical processing. The system that receives mobile uploads should not depend on downstream Spark transformations completing successfully.

Third, maintain a structured metadata layer. Every recording should be traceable to a device, collection session, sensor type, time interval, processing version, and quality status.

This third point is particularly relevant to Meta because the organization needs to understand not just how much sensor data was collected, but how much of it is usable for training.

## 3. File formats: What was stored and why?

An interviewer may ask why you used a particular storage format, especially when GPS and IMU have different data characteristics.

### Raw GPS record

An illustrative JSON event might look like this:

```
{
  "device_id": "phone_1024",
  "session_id": "session_501",
  "timestamp_ms": 1793714400000,
  "sensor_type": "gps",
  "latitude": 37.3875,
  "longitude": -121.9636,
  "accuracy_m": 4.2,
  "speed_mps": 8.5
}
```

### Raw IMU record

```
{
  "device_id": "phone_1024",
  "session_id": "session_501",
  "timestamp_ms": 1793714400010,
  "sensor_type": "gyroscope",
  "x": 0.012,
  "y": -0.034,
  "z": 0.005,
  "unit": "rad/s"
}
```

The gyroscope measures angular velocity. Accelerometer events would contain acceleration components, normally measured in m/s².

These are illustrative schemas, not confirmed Samsung file layouts.

### How to compare file formats

| Format       | Strengths                                            | Typical role                     |
| ------------ | ---------------------------------------------------- | -------------------------------- |
| JSON / JSONL | Flexible, readable, easy to ingest                   | Raw events and metadata          |
| Avro         | Compact, schema-aware, supports schema evolution     | Event transport and ingestion    |
| Parquet      | Columnar, compressed, efficient for analytical scans | Curated sensor tables            |
| Delta Lake   | ACID transactions, MERGE, versioning, Parquet-based  | Incremental tables and backfills |
| MCAP         | Timestamped heterogeneous sensor messages            | Raw robotics recordings          |

I would emphasize that Parquet or Delta tables are excellent for analytical queries, whereas raw event formats preserve source fidelity.

For example, an analyst calculating average GPS accuracy over 30 days should not need to read every raw JSON file.

A partitioned analytical table can be much more efficient.

## 4. Data quality: The most important technical discussion

This is where you can demonstrate significant engineering depth.

Meta's job description repeatedly emphasizes correctness, data validation, anomaly detection, and reliable metrics.

I would explain GPS/IMU data quality in terms of five concrete problems.

Problem 1: Different sampling frequencies and timestamp synchronization

GPS might produce one measurement per second, while an IMU may produce 50–200 measurements per second.

Never join them using exact timestamp equality. Use event-time alignment, nearest-neighbor matching with a tolerance, or windowed aggregation. Preserve original timestamps and track clock offsets when devices use different clock domains.

Problem 2: Missing sensor readings and collection gaps

Phones may stop collecting due to application background restrictions, power management, permission changes, or signal loss.

Detect gaps using differences between consecutive event timestamps, with thresholds specific to each sensor. Report completeness against the expected sampling schedule, and distinguish genuine missing data from intentional changes in sampling rate.

Problem 3: Invalid GPS coordinates and noisy locations

GPS can jump unexpectedly, especially indoors or in urban environments.

Validate latitude and longitude ranges, GPS accuracy, and implied movement speed. Use Haversine distance between consecutive points to detect implausible jumps, taking reported location accuracy into account.

Problem 4: Duplicate and out-of-order events

Mobile clients may retry uploads, causing duplicate records. Network interruptions can cause events to arrive out of order.

Define stable event identities, deduplicate deterministically, preserve both event time and ingestion time, and use event-time processing with explicit late-data policies.

Problem 5: IMU calibration, orientation, and outliers

IMU readings can contain sensor bias, noise, saturation, and changes in device orientation.

Validate units and physical ranges, monitor device-specific distributions, distinguish raw acceleration from gravity-compensated acceleration, and preserve calibration and coordinate-frame metadata.

### Show that you understand sampling-rate differences

Illustrative GPS versus IMU samples over one second

GPS: 1 Hz

IMU: 25 Hz (illustrative)

An excellent technical point is that resampling is not simply dropping IMU measurements.

For example, you might calculate mean acceleration, variance, peak angular velocity, and sample completeness within a one-second window. Those features can be aligned with GPS observations while retaining the original high-frequency IMU data for detailed analysis.

### Data quality metrics for dashboards

You can suggest metrics such as:

| Metric                  | Example calculation                                     |
| ----------------------- | ------------------------------------------------------- |
| GPS completeness        | Observed valid samples / expected samples               |
| IMU completeness        | Observed samples / expected samples                     |
| GPS accuracy            | Median reported horizontal accuracy                     |
| Gap rate                | Number of excessive timestamp gaps per collection hour  |
| Duplicate rate          | Duplicate events / received events                      |
| Processing freshness    | Current time − latest successfully processed event time |
| Session acceptance rate | Accepted sessions / evaluated sessions                  |

For completeness metrics, expected counts must account for device configuration and periods when collection was intentionally paused.

I would explicitly mention that invalid records should not necessarily be deleted. Often they should be retained with a quality flag, because they may be useful for debugging sensor or collection problems.

## 5. Backfill: How to explain historical reprocessing

Meta explicitly requires someone who can own backfills and metric restatements. This is a critical interview topic.

I recommend explaining backfill through a realistic sensor-data incident.

### Example scenario

Suppose you discover that GPS coordinates were processed incorrectly for certain mobile devices because a source application changed its timestamp format.

Three weeks of historical data may be affected.

You need to correct the data without losing new incoming measurements.

### Recommended backfill process

1\. Identify affected devices, sessions, and dates

2\. Retrieve original sensor files from raw storage

3\. Reprocess with corrected, version-controlled PySpark logic

4\. Validate corrected data against raw sources and expectations

5\. Atomically replace affected data or MERGE corrected records

6\. Recompute daily metrics and refresh dashboards

### Technical points to emphasize

Idempotency: Running the same backfill twice must not double-count sensor measurements.

Partition-aware processing: Reprocess only affected dates, devices, or sessions when practical. But account for neighboring intervals if calculations depend on preceding or following samples.

Concurrent ingestion: Prevent live ingestion and backfill from overwriting each other's results.

Reconciliation: Compare source record counts, unique events, session coverage, and aggregate metrics before and after correction.

Lineage: Track source files, processing version, execution ID, and the date of the correction.

For example, with Delta Lake you could use a `MERGE` operation keyed by a stable event identifier or perform controlled partition replacement. With Snowflake, a similar approach can use staging tables and `MERGE`.

### How to present it verbally

For sensor data pipelines, I consider backfill an essential part of the architecture, not an exceptional maintenance operation.

My preferred approach is to preserve immutable raw data so that if a parsing rule, timestamp conversion, or data quality definition changes, we can reprocess the affected historical period.

I design transformations to be deterministic and idempotent, so rerunning the same input does not introduce duplicate records.

After a backfill, I validate record counts, sensor coverage, and aggregated metrics. I also identify which reporting tables and dashboards need to be recomputed.

An important part of the process is communicating changes to stakeholders, especially when historical metrics have been restated.

This is a strong description of your engineering approach. For an actual Samsung project story, replace the hypothetical scenario with a correction you personally handled.

## 6. Reporting and dashboards: Your Grafana experience is especially valuable

Your Samsung experience includes GPS time-series pipelines and Grafana dashboards using Azure Data Explorer, PostgreSQL, and Prometheus.

This is particularly useful for Meta because it demonstrates reporting across different types of data systems.

Organize your dashboard discussion around three audiences:

### A. Operational dashboard

## Mobile Sensor Collection Operations


Operational users would want to know whether collection is running, how much data is arriving, and which devices are experiencing problems.

### B. Data engineering dashboard

This dashboard monitors pipeline reliability rather than sensor behavior.

Useful metrics include ingestion lag, Spark job failures, rejected record counts, schema changes, missing partitions, and freshness SLA violations.

Your experience with Grafana and Prometheus is particularly relevant here.

### C. Data quality dashboard

This dashboard helps engineers and scientists identify data that may be unsuitable for downstream analysis.

Examples include GPS accuracy distributions, IMU sampling gaps, devices with excessive missing measurements, and sensor outlier rates.

###   Grafana experience

 

One important aspect was integrating information from different backends, including Azure Data Explorer, PostgreSQL, and Prometheus.

The dashboards supported time-range filtering, drill-down analysis, and operational monitoring. I also worked on SQL and time-series query optimization to make reporting more efficient.

For Meta Robotics, I see a similar need: a dashboard should not only display collection volume, but also help operators and engineers understand why collection is below target — whether because of equipment availability, missing sensor data, processing delays, or data quality problems.

The final sentence is particularly valuable because it connects your previous work directly to Meta's operational needs.

## 7. The architectural decisions that demonstrate senior-level experience

 

| Design decision            | What to explain                                                                                               |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Batch versus streaming     | How quickly do operators need data? Is hourly reporting sufficient, or is near-real-time monitoring required? |
| Raw versus curated storage | Preserve original measurements while providing efficient analytical datasets                                  |
| Partitioning strategy      | Partition by date, with device/session filtering and suitable clustering or file layout                       |
| Sensor synchronization     | Use event timestamps, clock metadata, and bounded alignment windows                                           |
| Data validation            | Separate malformed, suspicious, and acceptable records                                                        |
| Backfill                   | Support deterministic reprocessing without duplicate counting                                                 |
| Reporting                  | Separate operational metrics from data pipeline health metrics                                                |

  do not partition high-volume sensor tables by device ID and date automatically. If thousands of devices produce small files, this can cause severe partition fragmentation.

Often, partitioning by collection date and using clustering or optimized file layout for device/session queries is preferable.

## 8. How to connect Samsung directly to Meta Robotics

 

| Samsung mobile sensors         | Meta robotics equivalent         |
| ------------------------------ | -------------------------------- |
| Mobile device                  | Robot or wearable device         |
| GPS / IMU recording session    | Robot teleoperation session      |
| Sensor sample count            | Collected sensor samples         |
| Sensor completeness            | Training data completeness       |
| Mobile device availability     | Robot equipment uptime           |
| Collection interruption        | Robot session interruption       |
| Sensor quality flags           | Training data quality evaluation |
| Daily collection statistics    | Daily robot collection targets   |
| Grafana operational monitoring | Robot fleet-status dashboards    |

I would use the following statement near the end of your Samsung project explanation:

> "The main similarity between my Samsung project and Meta Robotics is that both involve large-scale sensor data collection from physical devices. The challenge is not simply storing the data. It is ensuring that the data is complete, correctly timestamped, traceable to the original collection session, and reliable enough to support operational decisions."

## 9. Prepare to answer these technical follow-up questions

1\. How did you synchronize GPS and IMU data?

Explain the actual timestamp sources and clock domains. Describe event-time alignment, sampling-frequency differences, and the tolerance used for matching or aggregation.

2\. How did you detect GPS outliers?

3\. What happened when mobile phones lost connectivity?

4\. How did you backfill a failed day?

5\. How did you guarantee data quality?

6\. How did you optimize reporting queries?

## 10. The real production incident.

 
For example, a sensor collection gap, an unexpected GPS anomaly, an ingestion failure, a historical correction, or a discrepancy in a Grafana dashboard.

Describe what happened, how you diagnosed it, the Python/SQL/Spark changes you made, and how you verified the result.

That will be more convincing than describing an ideal architecture alone.

 
 
