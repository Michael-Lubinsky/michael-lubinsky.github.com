## Databricks File arrival trigger
```
This is the job-scheduling feature) this is a Databricks Workflows feature, not part of open-source Apache Spark at all.   
It lets a Databricks *job* (not a streaming query) kick off a run when new files land in a Unity Catalog volume or external location on S3/ADLS/GCS.
It's useful when a scheduled job's efficiency is compromised by irregular new data arrivals, and makes a best-effort check for new files every minute, 
with no extra cost beyond cloud-provider listing costs. 
This has nothing to do with Spark Structured Streaming's execution model — 
the File trigger doesn't belong to stream processing; 
it's more adapted to starting workloads where files are delivered non-deterministically, 
whereas streaming is for continuous 24/7 processing. 
It went GA about a year after its February 2023 initial release, 
and for best performance the external location should be enabled for file events, 
where Databricks uses an internal service that processes cloud-provider change notifications instead of pure directory listing.
```


## Databricks Lakeflow Jobs offer these trigger types 
(all Databricks-only, part of the Workflows/Jobs orchestration layer, not Spark itself):

- **Scheduled** — triggers a job run based on a time-based schedule (cron-style)
- **File arrival** — triggers a job run when new files arrive in a monitored Unity Catalog storage location, as discussed above
- **Table update** — runs the job automatically as soon as one or more specified Unity Catalog tables are updated, so you don't have to guess a schedule or run a continuous cluster. It works for updates, merges, and deletes, and can fire when one monitored table updates, or only after all monitored tables update. This recently went GA. It shares the same tuning knobs as file arrival — a minimum time between triggers (to avoid firing too often on bursty tables) and a "wait after last change" delay (to let data finish landing before the job starts)
- **Model update** — appeared in the GCP/Azure docs list alongside Table update as a newer trigger type (run manually, on a time-based schedule, on source-table updates, on file arrival, model update, or continuously) — fires when a registered model is updated
- **Continuous** — keeps the job always running by starting a new run whenever the previous run completes or fails — this is what you'd use to host an actual Structured Streaming query as a long-running job
- **None (manual)** — runs are triggered manually via "Run now" or programmatically through external orchestration tools (Airflow, REST API, etc.)

None of these have an OSS Spark equivalent — they're all Databricks Workflows/Jobs-service

## Databricks Auto Loader (`cloudFiles` streaming source)
```
 Databricks-only , not in OSS Spark. 
This is what you'd actually use *inside* a Structured Streaming job to incrementally pick up new files, 
e.g. `spark.readStream.format("cloudFiles")...`, 
optionally combined with `trigger(availableNow=True)` 
to process what's currently available and then stop.
```
## What open-source Apache Spark has natively?
```
just the plain file-based streaming source   
(`spark.readStream.format("csv"/"json"/"parquet"/...).load(path)`), 
which does directory listing on each micro-batch trigger interval — 
no file-notification/event-driven mode, no Auto Loader, no job-level file-arrival trigger. 
If you want push-based, event-driven file detection in vanilla Spark, 
you'd have to build it yourself 
(e.g., via cloud notification queues feeding into `foreachBatch`/custom sources) — 
Databricks just ships that as a managed feature.

So: if you're on OSS Spark (EMR, self-managed, etc.), you don't get either of these — you're stuck with directory-listing based streaming or building your own event-driven glue.
```
