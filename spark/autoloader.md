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
## Relation between Databricks Job and Databricks Workflow

Workflows and Jobs mean the same thing — Workflows is the feature/product name, and a job is the thing you build with it. So there's no separate hierarchy: "Workflows" is the umbrella orchestration product in Databricks (what you click into in the sidebar), and each individual pipeline you configure inside it is called a "job." Strip away the UI and every Databricks job is just two ingredients: tasks (units of work — a notebook, Python script/wheel, SQL query/dashboard refresh, dbt project, or a whole Delta Live Tables/Lakeflow pipeline) and a trigger (schedule, file arrival, table update, continuous, or manual) that decides when it runs. A job can contain a single task or many tasks wired into a DAG.

## Building a DAG of tasks (Airflow-style)

It's built directly in the Jobs UI (or via JSON/Databricks Asset Bundles) using **task dependencies**:

- Configuring task dependencies creates a Directed Acyclic Graph of task execution — for example, Task 1 is the root task with no dependencies, Task 2 and Task 3 both depend on Task 1 completing, and Task 4 depends on both Task 2 and Task 3 completing successfully.
- Dependencies are visually represented in the job DAG as lines between tasks, and Databricks runs upstream tasks before downstream ones, running as many as possible in parallel — this is the direct analog of Airflow's `>>` / `set_downstream` operators.
- Tasks connect to each other with `depends_on` — that's how you build the DAG (boxes and arrows with no loops). In the UI this is the "Depends on" field on each task; if you have a task selected in the DAG when you create a new task, the new one automatically gets a dependency on it.
- The "Run if dependencies" field adds control-flow logic based on upstream success/failure/completion — options include "All succeeded" (default), "At least one succeeded," "At least one failed," "None failed," and "All done" (runs regardless of upstream outcome) — this is Databricks' equivalent of Airflow's trigger rules.
- For branching and looping — the things you'd do with `BranchPythonOperator` or dynamic task mapping in Airflow — Databricks has an If/else condition task to run part of the DAG based on a boolean expression, and a For each condition task to add looping logic over an input array.
- To chain across jobs (like Airflow's `TriggerDagRunOperator`), there's a "Run Job" task type that lets one job trigger another job in the workspace.
- Data can be passed between tasks similarly to XComs: the producing task calls `dbutils.jobs.taskValues.set(key, value)` and the consuming task calls `dbutils.jobs.taskValues.get(taskKey, key)` to pass things like row counts or file paths downstream.

**Cross-job/cross-DAG dependencies** (analogous to Airflow datasets or `ExternalTaskSensor`) aren't natively built in — since jobs/bundles are independently deployable units, you'd implement this via the Workflows API polling job status, an external orchestrator like Airflow, or an event-based trigger (e.g. a webhook or message queue) fired on completion.

**Where it differs from Airflow**: a Databricks job is a DAG of tasks plus a trigger, and repair runs let you rerun only the failed tasks rather than the whole DAG — Workflows tends to be the natural choice when the pipeline lives entirely inside Databricks, while Airflow earns its keep when orchestrating across many external systems. Databricks Workflows doesn't have Airflow's broader ecosystem of provider operators/sensors for arbitrary external systems — it's purpose-built around notebooks, SQL, dbt, DLT/Lakeflow pipelines, and now table-update/model-update triggers, with cross-system orchestration typically left to something like ADF or Airflow sitting one layer above it.
