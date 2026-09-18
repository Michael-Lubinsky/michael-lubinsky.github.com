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
