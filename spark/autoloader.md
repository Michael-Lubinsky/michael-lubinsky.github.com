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

<https://medium.com/@asindugayangana/databricks-auto-loader-best-practices-for-reliable-and-scalable-data-ingestion-30e65bf4c520>

### Handling Late Arrival

<https://medium.com/@divyanshgoyal8989/handling-late-arriving-data-in-databricks-real-world-strategies-7a7203c75725>
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



## Spark Declarative Pipelines (SDP) vs Databricks Jobs

Two different orchestration paradigms, nested inside each other

The relationship is: **Spark Declarative Pipelines (SDP) is a declarative engine for orchestrating dataset dependencies *inside* a pipeline, while a Databricks Job is a procedural engine for orchestrating arbitrary tasks — and one of those task types is "run a pipeline."** They sit at different levels of granularity, and a Job's task DAG can *contain* an SDP pipeline as a single node.

Lakeflow Jobs provides a procedural approach to defining relationships between tasks. Lakeflow pipelines provide a declarative approach to defining relationships between datasets and transformations. That's the key distinction:

## Declarative Pipelines (SDP / Lakeflow Declarative Pipelines, née DLT)

- You **declare datasets** (tables, views, streaming tables) and the queries that produce them — you don't write explicit "step 1, step 2, step 3" control flow.
- Automatic orchestration: pipelines run processing steps (called "flows") in the correct order with maximum parallelism, and retry transient failures progressively — from the Spark task, to the flow, to the entire pipeline.
- Spark itself figures out the dependency graph from your table/view references (table B reads from table A → B automatically runs after A) and parallelizes independent branches — for example, if Table A and Table B don't depend on each other, SDP automatically triggers them in parallel to save time, without you writing any parallel code.
- This is the OSS "Spark Declarative Pipelines" you asked about from Spark 4.1.0 — a declarative framework for building batch and streaming data pipelines in SQL and Python, with common use cases including data ingestion and incremental batch/streaming transformations. Databricks' "Lakeflow Declarative Pipelines" (formerly DLT) extends Apache Spark Declarative Pipelines with Databricks-specific features (AUTO CDC/SCD handling, data-quality expectations, Unity Catalog integration, enhanced autoscaling).
- Inside one pipeline, you don't build a task DAG by hand — the DAG is *derived* from the SQL/Python dataset definitions.

## Databricks Jobs (Lakeflow Jobs / Workflows)

- You **declare tasks** (a notebook, a SQL query, a dbt project, a Python script — or a whole pipeline) and explicitly wire `depends_on` relationships between them, as we covered earlier.
- The DAG here is task-level, not dataset-level — you're orchestrating heterogeneous units of work, potentially across completely different technologies, not just SQL/Python transformations against tables.

## How they connect: Pipeline as a Task type

You schedule a pipeline to run as a task in a job, using the Jobs UI, the Lakeflow pipelines UI, or SQL. So a single Job — the thing you build multi-task DAGs in — can have one task that is "Task type: Pipeline," pointing at an entire SDP/Lakeflow pipeline. That pipeline task then behaves as one atomic node in the Job's DAG: it can have upstream dependencies (e.g., "wait for the ingestion notebook to finish first") and downstream dependents (e.g., "after the pipeline update completes, run a dashboard-refresh task"), even though internally the pipeline is running its own separate declarative sub-DAG of flows.

Execution mode is inherited from the Job's trigger, not the pipeline's own setting: in a triggered or scheduled job, the pipeline task starts a single update and stops when it completes; in a continuous job, the pipeline task runs the pipeline continuously — the job's schedule determines execution mode, so the pipeline runs continuously even if its own Pipeline mode setting is "triggered." Databricks actually recommends running continuous pipelines via a continuous job rather than the pipeline's own built-in continuous setting, because the job-wrapped version can use serverless performance modes the pipeline's native continuous mode doesn't support — and to avoid unexpected behavior, you should set the pipeline's own mode to triggered when wrapping it in a continuous job.

## Mental model

Think of it as two nested DAGs at different abstraction levels:

```
Databricks Job (procedural DAG — you wire depends_on)
├── Task 1: Ingest raw files (notebook)
├── Task 2: Run SDP Pipeline  ← this ENTIRE box is one task node
│     └── (internally: declarative DAG of tables/flows,
│           auto-derived from SQL/Python dataset definitions,
│           auto-parallelized, auto-retried)
├── Task 3: Refresh dashboard (depends on Task 2)
└── Task 4: Send Slack notification (depends on Task 3)
```

**When to use which layer for dependencies:**
- Dependencies *between tables within a transformation pipeline* → let SDP infer them declaratively; don't try to model table-level lineage as Job tasks.
- Dependencies *between heterogeneous work* (ingest → transform-pipeline → BI refresh → notify, possibly spanning dbt, notebooks, SQL, and DLT/SDP) → model these as a Job task DAG with explicit `depends_on`, with the SDP pipeline as one task in that chain.

That's also why the earlier "trigger types" discussion connects here — the same trigger options (scheduled, file arrival, table update, continuous) apply to the *Job* that wraps a pipeline task, giving you event-driven orchestration one layer above SDP's own dataset-level automatic scheduling.
