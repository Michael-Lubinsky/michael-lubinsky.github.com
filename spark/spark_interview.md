# Interview Cheat Sheet: Event Scan Dedup / Attendance ETL

## 1. Talk through the pipeline shape FIRST (before code)
1. Ingest raw scans (badge/device double-scans, retries, clock skew → duplicates)
2. Deduplicate → one canonical scan per (event, attendee, time window)
3. Compute attendance metrics (checked-in %, no-shows, duration)
4. Identify unmatched activity both directions (orphan scans, orphan registrations)
5. Discuss reliability/scale: idempotency, checkpointing, partitioning, skew, cost

---

## 2. Deduplication — SQL
```sql
WITH ranked_scans AS (
  SELECT
    scan_id, event_id, attendee_id, scan_ts, device_id,
    ROW_NUMBER() OVER (
      PARTITION BY event_id, attendee_id, date_trunc('minute', scan_ts)
      ORDER BY scan_ts ASC, scan_id ASC
    ) AS rn
  FROM raw_scans
)
SELECT * EXCEPT (rn) FROM ranked_scans WHERE rn = 1;
```
**Say out loud:** exact-match dedup misses near-duplicate scans a few seconds apart →
time-bucket (`date_trunc`) trades bucket size against false-merge risk.

## 3. Deduplication — PySpark (batch)
```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

w = Window.partitionBy("event_id", "attendee_id",
                        F.date_trunc("minute", "scan_ts")) \
          .orderBy(F.col("scan_ts").asc(), F.col("scan_id").asc())

deduped = (raw_scans
    .withColumn("rn", F.row_number().over(w))
    .filter(F.col("rn") == 1)
    .drop("rn"))
```

## 4. Deduplication — PySpark (streaming)
```python
deduped_stream = (
    raw_scans_stream
    .withWatermark("scan_ts", "10 minutes")
    .dropDuplicatesWithinWatermark(["event_id", "attendee_id", "scan_minute"])
)
```
**Key point:** plain `dropDuplicates` on unbounded stream grows state forever;
watermark bounds it. Strong reliability signal.

---

## 5. Attendance metrics — SQL
```sql
SELECT
  e.event_id, e.event_name,
  COUNT(DISTINCT r.attendee_id)                                AS registered_count,
  COUNT(DISTINCT ds.attendee_id)                                AS checked_in_count,
  COUNT(*) FILTER (WHERE ds.attendee_id IS NULL)                AS no_show_count,
  ROUND(COUNT(DISTINCT ds.attendee_id) * 100.0
        / NULLIF(COUNT(DISTINCT r.attendee_id), 0), 1)          AS attendance_pct,
  AVG(ds.duration_minutes)                                      AS avg_duration_minutes
FROM events e
LEFT JOIN registrations r  ON e.event_id = r.event_id
LEFT JOIN deduped_scans ds ON r.event_id = ds.event_id
                           AND r.attendee_id = ds.attendee_id
GROUP BY e.event_id, e.event_name;
```

## 6. Unmatched activity — both directions
```sql
-- Scans with no registration (walk-ins / fraud / bad IDs)
SELECT ds.*
FROM deduped_scans ds
LEFT ANTI JOIN registrations r
  ON ds.event_id = r.event_id AND ds.attendee_id = r.attendee_id;

-- Registrations with no scan (no-shows)
SELECT r.*
FROM registrations r
LEFT ANTI JOIN deduped_scans ds
  ON r.event_id = ds.event_id AND r.attendee_id = ds.attendee_id;
```
PySpark: `registrations.join(deduped_scans, ["event_id","attendee_id"], "left_anti")`

---

## 7. Scalable write pattern — Delta MERGE
```python
from delta.tables import DeltaTable

target = DeltaTable.forName(spark, "catalog.schema.attendance_facts")

(target.alias("t")
 .merge(deduped.alias("s"),
        "t.event_id = s.event_id AND t.attendee_id = s.attendee_id AND t.scan_minute = s.scan_minute")
 .whenMatchedUpdateAll()
 .whenNotMatchedInsertAll()
 .execute())
```
**Gotcha to mention:** `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` —
if the SOURCE side still has duplicate keys, MERGE throws even with correct target
logic. Dedup must happen before the merge, not rely on merge to fix it.

---

## 8. Reliability & efficiency talking points

| Concern | What to say |
|---|---|
| Idempotency | Composite/natural key + MERGE upsert so batch reprocessing doesn't double-count |
| Partitioning | Partition Delta tables by `event_date`/`event_id`; run `OPTIMIZE`/auto-compaction to avoid small files |
| Skew | Popular event dominates a partition → salt the key or enable AQE (`spark.sql.adaptive.enabled`) |
| Schema evolution / bad records | Quarantine table pattern instead of failing whole batch |
| Streaming reliability | Checkpoint location + `foreachBatch` for exactly-once sink writes |
| Cost | Autoscaling clusters, cache only reused DataFrames, `F.broadcast()` the smaller side to avoid wide shuffles |
| Monitoring | Row-count assertions pre/post dedup; alert if unmatched-activity ratio spikes (signals scanner malfunction) |

---

## 9. One-liner summary if asked to wrap up
"Dedup with a deterministic window function before any MERGE, compute metrics with
outer joins plus FILTER-based conditional counts, surface unmatched activity with
anti-joins in both directions, and make the whole thing idempotent and
watermark-bounded so it's safe to replay and cheap to scale."


Given your Databricks/Delta Lake background, this maps closely to patterns you already use (ROW_NUMBER dedup, MERGE upserts, quarantine tables). Here's a structured way to attack this interview.

## 1. Problem framing (say this out loud first)

State the pipeline shape before coding — interviewers weight this heavily:

1. **Ingest** raw scan events (possibly duplicated — same badge/device double-scanning, retried API calls, clock skew).
2. **Deduplicate** scans to one canonical record per (event, attendee, scan-window).
3. **Compute attendance metrics** (checked-in, duration, no-shows).
4. **Identify unmatched activity** (scans with no registration record, or registrations with no scan — orphans on both sides).
5. **Discuss reliability/scale**: idempotency, schema evolution, backpressure, checkpointing, partitioning, cost.

## 2. Deduplication — SQL

The classic pattern you already use in ChargeMinder:

```sql
WITH ranked_scans AS (
  SELECT
    scan_id,
    event_id,
    attendee_id,
    scan_ts,
    device_id,
    ROW_NUMBER() OVER (
      PARTITION BY event_id, attendee_id, 
                   date_trunc('minute', scan_ts)  -- collapse near-duplicate scans
      ORDER BY scan_ts ASC, scan_id ASC            -- deterministic tie-break
    ) AS rn
  FROM raw_scans
)
SELECT * EXCEPT (rn)
FROM ranked_scans
WHERE rn = 1;
```

Talking point: `ROW_NUMBER()` over exact match misses "duplicate but 3 seconds apart" scans — mention a **time-bucketed window** (`date_trunc` or a rounding function) as the fix, and note the tradeoff (bucket size vs. false-merge risk).

## 3. Deduplication — PySpark

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

w = Window.partitionBy("event_id", "attendee_id",
                        F.date_trunc("minute", "scan_ts")) \
          .orderBy(F.col("scan_ts").asc(), F.col("scan_id").asc())

deduped = (
    raw_scans
    .withColumn("rn", F.row_number().over(w))
    .filter(F.col("rn") == 1)
    .drop("rn")
)
```

For **streaming** dedup (mention this proactively — shows production maturity):

```python
deduped_stream = (
    raw_scans_stream
    .withWatermark("scan_ts", "10 minutes")
    .dropDuplicatesWithinWatermark(["event_id", "attendee_id", "scan_minute"])
)
```

`dropDuplicates` alone on an unbounded stream grows state forever — watermarking bounds it. This is a strong signal in a reliability discussion.

## 4. Attendance metrics

```sql
SELECT
  e.event_id,
  e.event_name,
  COUNT(DISTINCT r.attendee_id)                                   AS registered_count,
  COUNT(DISTINCT ds.attendee_id)                                  AS checked_in_count,
  COUNT(*) FILTER (WHERE ds.attendee_id IS NULL)                  AS no_show_count,   -- pattern you already use
  ROUND(COUNT(DISTINCT ds.attendee_id) * 100.0 
        / NULLIF(COUNT(DISTINCT r.attendee_id), 0), 1)            AS attendance_pct,
  AVG(ds.duration_minutes)                                        AS avg_duration_minutes
FROM events e
LEFT JOIN registrations r  ON e.event_id = r.event_id
LEFT JOIN deduped_scans ds ON r.event_id = ds.event_id 
                           AND r.attendee_id = ds.attendee_id
GROUP BY e.event_id, e.event_name;
```

## 5. Unmatched activity (both directions — this is the part people forget)

```sql
-- Scans with no matching registration (walk-ins / fraud / bad IDs)
SELECT ds.*
FROM deduped_scans ds
LEFT ANTI JOIN registrations r
  ON ds.event_id = r.event_id AND ds.attendee_id = r.attendee_id;

-- Registrations with no scan (no-shows)
SELECT r.*
FROM registrations r
LEFT ANTI JOIN deduped_scans ds
  ON r.event_id = ds.event_id AND r.attendee_id = ds.attendee_id;
```

In PySpark: `registrations.join(deduped_scans, ["event_id","attendee_id"], "left_anti")`.

## 6. Scalable pipeline / Delta pattern

```python
from delta.tables import DeltaTable

target = DeltaTable.forName(spark, "catalog.schema.attendance_facts")

(target.alias("t")
 .merge(deduped.alias("s"),
        "t.event_id = s.event_id AND t.attendee_id = s.attendee_id AND t.scan_minute = s.scan_minute")
 .whenMatchedUpdateAll()
 .whenNotMatchedInsertAll()
 .execute())
```

Mention: this is exactly the `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` failure mode — if the *source* side of a MERGE still has duplicate keys, the merge throws even with correct target logic. Dedup must happen **before** the merge, not rely on the merge to fix it.

## 7. Reliability & efficiency talking points (this is likely a big chunk of grading)

- **Idempotency**: use natural/composite keys + MERGE so reprocessing a batch doesn't double-count. Design scan_id or a hash of (event_id, attendee_id, scan_ts) as a dedup key upstream.
- **Partitioning**: partition Delta tables by `event_date` or `event_id` to prune scans; avoid small-file problems with `OPTIMIZE` / auto-compaction.
- **Skew**: a popular event can dominate a partition — salt the key or use adaptive query execution (`spark.sql.adaptive.enabled`).
- **Schema evolution / bad records**: quarantine table pattern for malformed scan payloads instead of failing the whole batch — you've built this before (bandit analytics ingestion).
- **Checkpointing**: for streaming ingestion, checkpoint location + `foreachBatch` for exactly-once sink writes.
- **Cost**: cluster autoscaling, cache only the reused DataFrame (registrations, if joined repeatedly), avoid wide shuffles by broadcasting the smaller side (`F.broadcast(registrations)`) if it fits.
- **Monitoring**: row-count assertions pre/post dedup, alert if unmatched-activity ratio spikes (signals upstream scanner malfunction).

## Flat nested json  - EXPLODE for arrays

 <img width="495" height="515" alt="image" src="https://github.com/user-attachments/assets/274948fb-f24d-4e21-bfe7-98f1679af091" />

<img width="680" height="415" alt="image" src="https://github.com/user-attachments/assets/619ff1ab-c1b7-4fe1-81a3-001a91e668be" />


