# Apache Airflow Interview Prep

**1. Correct these points in your notes first**

| Topic in your notes | Interview-ready correction |
|---|---|
| TaskFlow passes data without XCom | TaskFlow automates XCom communication. Passing a task’s output produces an `XComArg`, rather than immediately running the function. |
| Returning `TriggerDagRunOperator` from a task | This does not schedule the operator. Instantiate it as part of the DAG definition and set its dependencies. |
| Variables configured in `[variables]` in `airflow.cfg` | Use the UI, CLI, environment variables such as `AIRFLOW_VAR_KEY`, or a secrets backend. |
| SubDAGs | Prefer TaskGroups for organization. SubDAG support was removed in Airflow 3. |
| SequentialExecutor and DebugExecutor | These are historical choices, removed in Airflow 3. |
| Older imports and `schedule_interval` | Recognize older examples, but use APIs appropriate to the installed version. Airflow 3 provides `airflow.sdk` for DAG authoring. |
| Custom `SkipMixin` example | For simply skipping the current task, raising `AirflowSkipException` is clearer. |
| Legacy SLA example | Distinguish legacy SLA monitoring from execution timeouts; Airflow 3 removed the old SLA feature. |

Sources: [XCom](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html), [Variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html), [Airflow 3 removed features](https://airflow.apache.org/docs/apache-airflow/3.0.6/release_notes.html).

**2.  “What is Apache Airflow?”**

> Apache Airflow is a platform for defining, scheduling, and monitoring workflows as Python code. A workflow is represented as a DAG, where tasks have explicit dependencies. Airflow manages scheduling, retries, execution state, and observability. In a data pipeline, I use it to coordinate services such as Cloud Storage, BigQuery, and Spark.

Add this distinction:

> Airflow coordinates the work. Large transformations usually execute in the appropriate processing system.

Airflow can run Python processing itself, but its workers should not become an accidental replacement for a distributed analytics engine. [Airflow overview](https://airflow.apache.org/docs/apache-airflow/)

**3. Know the core objects precisely**

| Concept | Meaning |
|---|---|
| DAG | Workflow definition: tasks, dependencies, schedule, and configuration |
| DAG run | One execution of that workflow |
| Task | A unit of work defined in the DAG |
| Task instance | A task associated with a particular run; mapped instances also have a map index |
| Operator | A reusable implementation of a kind of task |
| Hook | An interface to an external service |
| Sensor | A task that waits for a condition |
| Executor | The mechanism used to dispatch task execution |
| Connection | External-system connection information |
| XCom | Small values communicated between task instances |

**“What happens after I deploy a DAG?”**

> The DAG processor imports the Python file and discovers the DAG. The scheduler determines eligible runs and tasks from scheduling rules and dependencies. The executor dispatches runnable tasks. Task execution updates state and produces logs, which operators inspect through the UI and APIs.

For **Airflow 3**, mention the standalone DAG processor and API server. Task code communicates through the Task Execution API rather than accessing the metadata database directly. [Architecture](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html), [Airflow 3 architecture changes](https://airflow.apache.org/docs/apache-airflow/stable/installation/upgrading_to_airflow3.html).

**4. Master scheduling—the common interview trap**

**“What is the difference between logical date and execution time?”**

> Logical date identifies the run according to its timetable. Execution time is when the task actually runs. For interval-based processing, I use the explicit data interval to select input data.

For an explicitly configured **daily data-interval timetable**:

```text
Data interval:  November 10 00:00 → November 11 00:00
Run eligible:   After November 11 00:00
Actual start:   Could be later because of queues or capacity
```

**Do not say every `@daily` DAG always processes yesterday.** Timetable behavior and configuration matter, particularly across Airflow versions. Trigger timetables and data-interval timetables have different semantics. [DAG runs and data intervals](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)

**“Catchup versus backfill?”**

> Catchup lets the scheduler create missed scheduled runs. Backfill explicitly requests historical processing over a chosen range. Both require tasks that read and write the correct historical data rather than using the current date.

**“Why avoid `datetime.now()` for partition selection?”**

> A retry or backfill could process a different partition. I derive the partition from the run’s intended interval or a validated explicit parameter.

**5. Explain reliability with a concrete failure**

**“What does idempotent mean?”**

> Repeating the same operation for the same input produces the same intended final result.

Suppose a task loads November 10 orders into BigQuery. BigQuery finishes successfully, but the worker crashes before Airflow records success.

A retry that blindly appends the file can create duplicates.

A strong answer:

> I make the load retry-safe using an appropriate combination of stable external job identity, staging tables, partition replacement, or a deduplicating `MERGE`. I also keep the input file set stable for that run.

**“Does Airflow guarantee exactly-once processing?”**

> No. A task can perform an external side effect and then fail before recording success. I design for repeated attempts and enforce deduplication or idempotency in the destination system.

**“When should a task retry?”**

> Retry transient failures such as temporary network errors or service throttling, with bounded attempts and backoff. Invalid schemas or malformed SQL usually need correction rather than repeated retries.

**“What happens when you clear a task?”**

> It becomes eligible for re-execution under Airflow’s scheduling rules. Clearing its state does not undo external writes.

These answers reflect Airflow’s guidance to make tasks transaction-like, partition-specific, and safe to rerun. [Best practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

**6. Understand task communication and runtime mapping**

**“XCom versus Variables versus Params?”**

| Mechanism | Appropriate use |
|---|---|
| XCom | Run-specific outputs: object URI, row count, external job ID |
| Variables | Shared application configuration |
| Params | Parameterized runs, with validation where configured |
| Connections / secrets backend | Credentials and connection configuration |

**“Can I pass a large DataFrame through XCom?”**

> I normally store the data in shared storage and pass its URI. XCom is intended for small values; an object-storage backend changes storage behavior but does not make huge task-to-task payloads a good default.

**“What happens in this code?”**

```python
files = discover_files()
load_file.expand(uri=files)
```

> During DAG parsing, these calls define tasks and their relationships. During execution, `discover_files` returns a list through XCom, and Airflow creates mapped task instances to process its elements.

A Python loop creates tasks at **parse time**. Dynamic task mapping can determine their number from **runtime output**. `partial()` supplies fixed arguments; `expand()` supplies mapped arguments. [XCom](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html), [Dynamic task mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html)

**7. Be ready for branching questions**

Given:

```text
          ┌── full_load ─────────┐
choose ───┤                     ├── validate
          └── incremental_load ─┘
```

**“Why might `validate` be skipped?”**

> Its default trigger rule is `all_success`, but the unselected branch is skipped. For a normal branch join, I would often use `none_failed_min_one_success`.

| Trigger rule | Meaning |
|---|---|
| `all_success` | All direct upstream tasks succeeded |
| `none_failed_min_one_success` | No upstream failures and at least one success |
| `all_done` | All upstream tasks reached terminal states |
| `one_success` | At least one upstream task succeeded; it can proceed before all finish |

**“Is `all_done` appropriate for validation?”**

> Usually not if validation requires successful upstream processing. It is more appropriate for unconditional cleanup.

A successful `all_done` leaf task can also cause a DAG run to appear successful despite an earlier failure. Know how your terminal tasks preserve failure visibility. [Trigger rules](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html#trigger-rules), [DAG run status](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)

**8. Explain efficient waiting**

**“A sensor waits six hours for a file. What mode would you choose?”**

| Approach | Resource behavior |
|---|---|
| `poke` | Holds a worker slot between checks |
| `reschedule` | Releases the worker between scheduled checks |
| Deferrable operator | Releases the worker while a trigger handles waiting |

A good answer:

> For long waits, I prefer a supported deferrable sensor with a running triggerer. Reschedule mode is another option. I also configure a timeout and define what missing data means operationally.

Deferral does not mean polling necessarily disappears: the trigger may poll asynchronously. Deferred tasks do not consume pool slots by default, although pools can be configured to include them. [Deferrable operators](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html)

**9. Know concurrency controls**

**“How do you stop Airflow overwhelming a database?”**

> Put all tasks accessing that constrained resource in a shared pool. Set pool capacity according to the database’s safe concurrency and use multiple pool slots for heavier tasks where appropriate.

Distinguish these controls:

- **Pools:** Protect shared resources across workflows.
- **`max_active_runs`:** Limit concurrent runs of one DAG.
- **`max_active_tasks`:** Limit active tasks across runs of one DAG.
- **Executor and worker capacity:** Limit actual execution capacity.
- **Priority weights:** Influence which eligible tasks are selected under contention.

A pool limits concurrent work; it is not a precise requests-per-second rate limiter.

**“Which executor would you choose?”**

| Executor | Typical tradeoff |
|---|---|
| LocalExecutor | Simpler deployment; limited to one machine’s resources |
| CeleryExecutor | Distributed workers; requires broker and worker operations |
| KubernetesExecutor | Per-task pods and isolation; pod startup and Kubernetes overhead |

Also distinguish **KubernetesExecutor** from **KubernetesPodOperator**: the former dispatches Airflow tasks; the latter is a task that launches a pod.

**10. Practice this system-design answer**

**Question: “Design a daily GCS-to-BigQuery pipeline.”**

Start by clarifying file completeness, data volume, latency, duplicate handling, late arrivals, and historical reprocessing.

Then propose:

```text
Wait for completion marker
          ↓
Read and validate manifest
          ↓
Load files into staging
          ↓
Run data-quality checks
          ↓
Publish with MERGE or partition replacement
          ↓
Notify downstream consumers
```

A strong spoken answer:

> I would process an explicit business-date partition. A completion marker and manifest identify the intended input files, so listing a partially uploaded prefix cannot trigger an incomplete load.
>
> Airflow would submit BigQuery load jobs using an explicit schema. I would load into staging, validate counts, required fields, and business keys, then publish with a retry-safe operation.
>
> I would pass object URIs and job IDs through XCom, use Connections or a secrets backend for authentication, and limit concurrent submissions with pools.
>
> For backfills, I would reuse the same pipeline with historical inputs and controlled concurrency. I would monitor data freshness and completeness as well as task success.

Important follow-ups:

- **Thousands of files?** Batch compatible files into load jobs rather than automatically creating one task per tiny file.
- **Late file?** Define a correction window and reprocess or merge the affected partition.
- **Schema change?** Apply an explicit compatibility policy; fail or quarantine unexpected changes.
- **External job still running after task failure?** Reconcile its status before submitting another job.
- **Data-quality failure?** Keep unvalidated data out of the published table.

**11. Prepare a structured troubleshooting answer**

**“My task is stuck. What do you check?”**

First identify the state:

| State | First investigation |
|---|---|
| Not scheduled | Dependencies, trigger rule, schedule, paused DAG, concurrency limits |
| Scheduled | Pools and scheduler/executor capacity |
| Queued | Worker availability, Celery routing, Kubernetes pod scheduling |
| Running | Logs, heartbeat, external job status, resource exhaustion |
| Deferred | Triggerer health and trigger progress |
| Upstream failed | Find and diagnose the original upstream failure |

**“The DAG does not appear in the UI.”**

> Check import errors, DAG discovery, unique DAG IDs, required packages, DAG processor health, and deployment synchronization.

**“Scheduling becomes slow after adding DAGs.”**

> Check parsing duration and top-level code. Network calls, database queries, heavy imports, and expensive computations should generally happen during task execution, not repeatedly during DAG parsing. Then examine scheduler and metadata database health.

**12. Know how you would test and monitor**

For testing, explain four layers:

1. Unit-test transformation logic independently of Airflow.
2. Check DAG imports, task IDs, and dependencies.
3. Test templates and runtime parameters.
4. Run integration scenarios covering retries, branching, missing files, and backfills.

Do not assume local DAG tests are free of external side effects.

For monitoring, mention:

- Failures, retries, queue time, and execution duration.
- Scheduler, DAG processor, worker, and triggerer health.
- Pool saturation and available execution capacity.
- External job IDs and remote logs.
- **Business freshness and completeness**—a green DAG can still publish wrong data.

**13. A five-session preparation plan**

| Session | Focus | Practice |
|---|---|---|
| 1 | Architecture and terminology | Explain deployment-to-execution in two minutes |
| 2 | Scheduling | Work through intervals, catchup, and backfill |
| 3 | Task authoring | Build TaskFlow, mapping, and branching examples |
| 4 | Reliability | Diagnose duplicate loads and worker crashes |
| 5 | System design | Present the GCS-to-BigQuery design and defend tradeoffs |

For each interview answer, use: **definition → example → failure case → tradeoff**.

Your first mock-interview question:

**A task successfully loads data into BigQuery, but its worker crashes before Airflow records success. Airflow retries the task. How would you prevent duplicate data?**


## 1. What Airflow Is (30-second answer)

Apache Airflow is an **open-source workflow orchestration platform** — you define pipelines as **DAGs (Directed Acyclic Graphs)** in Python, and Airflow schedules, executes, retries, and monitors the tasks in them. It doesn't move or process data itself (unlike Spark)
— it orchestrates *other* systems that do (Glue jobs, Databricks jobs, Lambda, dbt, SQL scripts, etc.).

Given your stack (Databricks, Glue, Step Functions, Lambda), the cleanest framing in an interview:
> "Step Functions is AWS-native orchestration; Airflow is the cloud-agnostic, Python-native equivalent — more flexible, more code-heavy, and the de facto standard outside pure-AWS shops."

---

## 2. Core Concepts You Must Know Cold

| Concept | What to say |
|---|---|
| **DAG** | A Python file defining tasks and their dependencies. Must be acyclic — no circular dependencies. |
| **Task / Operator** | A task is a unit of work; an Operator is the template defining *what kind* of work (PythonOperator, BashOperator, KubernetesPodOperator, etc.) |
| **Task Instance** | A specific run of a task for a specific `execution_date`/`logical_date` |
| **Scheduler** | Parses DAGs, decides what should run and when, based on `schedule_interval`/`schedule` and dependencies |
| **Executor** | Determines *how* tasks actually run: SequentialExecutor (debug only), LocalExecutor, CeleryExecutor, KubernetesExecutor, CeleryKubernetesExecutor |
| **Worker** | The process that actually executes a task (relevant for Celery/K8s executors) |
| **Webserver** | The UI — DAG views, Gantt charts, logs, manual triggers |
| **Metadata DB** | Postgres/MySQL backing store — DAG runs, task state, connections, variables, XComs |
| **XCom** | Small pieces of data passed *between* tasks (metadata DB-backed, so keep it small — not for large datasets) |
| **Hooks** | Reusable interfaces to external systems (S3Hook, PostgresHook, DatabricksHook) — Operators are usually built on top of Hooks |
| **Sensors** | Wait for a condition (file exists, partition landed, external DAG finished) before proceeding — can run in `poke` mode (blocks a worker slot) or `reschedule` mode (frees the slot between checks) |
| **Pools** | Limit concurrency on a shared resource (e.g., max 5 tasks hitting a rate-limited API at once) |
| **Task Groups** | Visual/logical grouping of tasks in the UI (replaced the older, clunkier SubDAGs) |
| **Trigger Rules** | Control when a task runs relative to upstream state: `all_success` (default), `all_failed`, `one_success`, `none_failed`, `all_done`, etc. |

---

## 3. The #1 Concept Interviewers Probe: `execution_date` / Idempotency

This trips people up constantly — know it well:

- Airflow schedules are **interval-based**, not "run now" based. A DAG scheduled `@daily` and triggered on Jan 2 actually runs for the **Jan 1 interval** (the `logical_date`/`execution_date` is the *start* of the period being processed, not the run time).
- This design exists so pipelines are **idempotent and backfillable** — you can rerun any historical interval and get the same, correct result, because each task run knows exactly which date's data it's responsible for.
- Newer Airflow (2.2+) calls this `logical_date` instead of `execution_date` to reduce confusion, but the concept is identical.

**Good interview answer:** "Airflow tasks should be idempotent — re-running a task instance for the same interval should produce the same output, whether it's the first run or a backfill. I design tasks to key off `logical_date`/`data_interval_start` rather than `datetime.now()`, and prefer overwrite/upsert semantics over blind appends."

---

## 4. Common Interview Questions + Strong Answers

**Q: How do you handle task failures and retries?**
> Set `retries` and `retry_delay` on the task (or DAG default_args), optionally with `retry_exponential_backoff=True`. For alerting, use `on_failure_callback` (e.g., post to Slack/PagerDuty) or the built-in SLA/email alerting. For truly critical paths, I'd wrap failure handling in a dedicated task with `trigger_rule='one_failed'` to run cleanup/notification logic.

**Q: PythonOperator vs. TaskFlow API (`@task` decorator)?**
> TaskFlow API (Airflow 2.0+) is the modern approach — write plain Python functions decorated with `@task`, and Airflow handles XCom passing automatically via return values, instead of manually calling `ti.xcom_push`/`xcom_pull`. Much cleaner for DAGs with heavy data passing between tasks. I'd default to TaskFlow for new DAGs and reserve traditional Operators for cases needing a specific pre-built integration (e.g., `DatabricksSubmitRunOperator`).

**Q: How do you avoid Airflow becoming a data processing engine itself?**
> Airflow orchestrates, it doesn't transform. Heavy lifting belongs in Spark/Databricks/Glue — Airflow just triggers those jobs and waits for completion (e.g., `DatabricksRunNowOperator`, `GlueJobOperator`) rather than pulling data into the worker process itself. Workers are meant to be lightweight.

**Q: SubDAGs vs. TaskGroups vs. dynamic task mapping?**
> SubDAGs are deprecated in practice — they caused scheduler deadlocks and serialization issues. TaskGroups replaced them for visual/logical grouping with no separate scheduling overhead. For truly dynamic fan-out (e.g., one task per file discovered at runtime), use **Dynamic Task Mapping** (`.expand()`), introduced in Airflow 2.3.

**Q: How would you design a DAG that processes each partition of a Delta table daily?**
> Schedule the DAG `@daily`, key it off `data_interval_start`/`data_interval_end` to determine which partition to process, use a Sensor (or Databricks job trigger) to confirm upstream data has landed, then trigger the Databricks/Glue job for just that partition. I'd make the downstream write idempotent (MERGE/overwrite by partition) so reruns and backfills are safe.

**Q: How do you handle secrets/connections?**
> Use Airflow **Connections** (stored in the metadata DB, encrypted via Fernet key) for credentials, or better, back them with a **Secrets Backend** (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault) so secrets aren't sitting in Airflow's own DB. Given you already work with Azure Key Vault / AWS Secrets Manager, that's a strong point to bring up.

**Q: Difference between `schedule_interval` and data intervals; catchup behavior?**
> `catchup=True` (the default) means Airflow will backfill every missed interval between `start_date` and now the first time a DAG is turned on — this surprises people and can hammer downstream systems. I always set `catchup=False` explicitly unless backfilling historical data is actually intended, and handle backfills deliberately via `airflow dags backfill`.

**Q: How do you scale Airflow / what's your executor choice and why?**
> LocalExecutor is fine for small/single-node setups. For production at scale, CeleryExecutor (worker pool, needs Redis/RabbitMQ as broker) or KubernetesExecutor (each task run gets its own pod — better isolation, scales to zero) are the real choices. KubernetesExecutor is increasingly the default recommendation for cloud-native, bursty workloads since you don't pay for idle workers.

**Q: How do you monitor and alert on Airflow pipelines?**
> DAG-level and task-level `on_failure_callback`/`on_success_callback`, SLA misses (`sla` parameter + `sla_miss_callback`), and exporting metrics via StatsD → Prometheus/Grafana. In an AWS/Azure shop I'd also wire failures into CloudWatch Alarms or Azure Monitor, consistent with how you already alert on Step Functions/Glue failures.

---

## 5. Things Senior Candidates Are Expected to Discuss

- **Idempotency and backfill safety** (see #3) — this is the single most common senior-level probe.
- **DAG design hygiene**: keep DAG files light (no heavy computation at parse time — the scheduler re-parses DAG files repeatedly), avoid top-level code that hits external APIs/DBs.
- **Testing DAGs**: unit-test individual task callables, use `dag.test()` (2.5+) or the `airflow tasks test` CLI for local runs without needing the full scheduler.
- **Versioning/CI-CD for DAGs**: DAGs synced via git-sync, S3, or baked into the Docker image; blue/green or canary DAG deploys.
- **Cost/resource awareness**: pool limits, worker autoscaling, avoiding sensor "poke" mode holding worker slots for long waits (prefer `reschedule` mode or deferrable operators/triggers, which use the async **Triggerer** component instead of blocking a worker at all).
- **Deferrable operators / Triggerer** (Airflow 2.2+): async waits (e.g., waiting hours for an external job) without occupying a worker slot — big cost/efficiency win over classic sensors.

---

## 6. How to Frame Your Own Experience

Since your background is Databricks/PySpark + AWS (Glue, Lambda, Step Functions, DynamoDB) + Azure (Event Hubs, Functions), a natural narrative:

> "I've built pipelines using AWS-native orchestration (Step Functions triggering Glue/Lambda), which taught me the orchestration patterns Airflow generalizes — DAG-based dependencies, retries, idempotent reruns. Airflow's advantage is being cloud-agnostic and code-first, so the same pipeline logic isn't locked into one cloud's state-machine JSON."

This positions you as someone who understands orchestration *concepts* deeply, even if your hands-on Airflow reps are lighter than your AWS Step Functions/Glue reps — which is a very defensible, honest position in an interview.

---

## 7. Quick Reference: Airflow vs. What You Already Know

| Airflow | AWS equivalent | Azure equivalent |
|---|---|---|
| DAG | State Machine (Step Functions) | Pipeline (Data Factory) |
| Operator/Task | State (Task, Choice, Map...) | Activity |
| Scheduler | EventBridge Scheduler | Trigger (scheduled) |
| Sensor | Wait state + polling Lambda | Wait/Until activity |
| Connections/Secrets Backend | Secrets Manager | Key Vault |
| XCom | Step Functions state input/output | Pipeline parameters/output |
| Executor (Celery/K8s) | Lambda concurrency / ECS/EKS | Function App scale / AKS |


## AWS Step Functions vs Apache Airflow — both are **orchestrators**,  

## Core Difference

| | **AWS Step Functions** | **Apache Airflow** |
|---|---|---|
| **What it is** | AWS-native, serverless state machine orchestrator | Open-source, cloud-agnostic workflow orchestrator |
| **Authoring** | JSON/YAML (Amazon States Language) or CDK/Workflow Studio (visual) | Python (DAGs as code) |
| **Infra** | Fully serverless — zero infra to manage | Requires running scheduler/webserver/workers, or a managed service (MWAA, Astronomer, Cloud Composer) |
| **Scope** | AWS services only (Lambda, Glue, ECS, DynamoDB, SNS/SQS, etc.) — can call HTTP endpoints too via API destinations, but it's built AWS-first | Anything — AWS, GCP, Azure, on-prem, SaaS APIs, dbt, Spark, arbitrary Python |

## Side-by-Side

| | Step Functions | Airflow |
|---|---|---|
| **Execution model** | Standard (durable, up to 1 yr, exactly-once) or Express (short, high-volume, at-least-once) | Scheduler-driven DAG runs; no built-in distinction like Standard/Express — scaling is via executor choice (Celery/K8s) |
| **State/dependency tracking** | Built-in, managed by AWS — no metadata DB to maintain | Relies on its own metadata DB (Postgres/MySQL) that you (or MWAA) must run and maintain |
| **Retries/error handling** | Declarative, built into ASL (`Retry`/`Catch` blocks per state) | Declarative via `retries`, `retry_delay`, `on_failure_callback`, trigger rules |
| **Scheduling** | Basic — EventBridge Scheduler triggers executions; no native concept of "data interval" | Rich — cron-like schedules, **data-interval-aware** (`logical_date`), first-class backfill support |
| **Visual debugging** | Built-in execution graph in console showing exact state/branch — very good out of the box | DAG graph + Gantt view in the Airflow UI — comparable, but you're running/hosting it |
| **Dynamic/programmatic DAGs** | Static state machine defined ahead of time (though Map state allows dynamic iteration) | Fully dynamic — DAGs are Python, so you can generate tasks/DAGs programmatically at parse time |
| **Ecosystem/integrations** | Deep, first-party AWS service integrations (200+ services) via direct SDK integrations, no glue code needed | Huge community-maintained **provider** ecosystem (AWS, GCP, Azure, Snowflake, Databricks, dbt, Slack, etc.) — but often via Hooks/Operators someone wrote, not always as tightly integrated as native AWS calls |
| **Cost model** | Pay per state transition (Standard) or per request+duration (Express) — no idle cost | Pay for infra/managed service uptime regardless of workflow volume (though MWAA scales somewhat) |
| **Local dev/testing** | Harder to test locally; mostly console/CLI driven against real AWS | Easier to iterate locally — `airflow dags test`, Docker Compose setups, unit-testable Python |
| **Vendor lock-in** | High — ASL and AWS service integrations don't port elsewhere | Low — portable across clouds, just needs Python + wherever it's hosted |

## When You'd Reach for Each

- **Step Functions** — you're all-in on AWS, want zero infrastructure ops, need rock-solid built-in retry/error semantics, and your workflow is primarily coordinating AWS services (Lambda → Glue → DynamoDB → SNS). Great fit for microservice orchestration and shorter, event-triggered workflows.
- **Airflow** — you have complex, long-running, data-interval-driven pipelines (daily/hourly batch ETL), need backfill semantics, span multiple clouds/tools (Databricks + Snowflake + dbt + Slack), or your team wants pipelines as version-controlled Python rather than JSON state machines.

## The Practical Nuance (good interview point)

They're both real orchestrators, but they come from different worlds:
- Step Functions grew out of **microservice/application orchestration** — sagas, approval workflows, order processing.
- Airflow grew out of **data engineering/batch ETL** — the whole "idempotent, backfillable, data-interval-aware" design (see the earlier prep doc) is baked into its DNA in a way Step Functions doesn't really have.

That's usually the sharpest way to draw the line if asked "why not just use Step Functions instead of Airflow?" — Step Functions doesn't have a native concept of "reprocess Tuesday's data," while that's Airflow's bread and butter.

## AWS Glue vs Apache Airflow

They actually solve **different problems** and are often used *together* rather than as alternatives — but here's the comparison, since interviewers sometimes ask this to test whether you understand the distinction.

## Core Difference

| | **AWS Glue** | **Apache Airflow** |
|---|---|---|
| **What it is** | A serverless **ETL/data processing engine** | A workflow **orchestrator** |
| **Job** | Actually transforms data (runs Spark jobs) | Schedules and sequences *other* systems' jobs |
| **Analogy** | The worker doing the task | The manager deciding when/what/in-what-order tasks run |

**The key point to make in an interview:** Glue *does* work (Spark-based transformation); Airflow *coordinates* work. It's common — and often the right design — to have Airflow trigger a Glue job as one step in a larger DAG (e.g., Airflow → trigger Glue crawler → trigger Glue ETL job → trigger Lambda validation → load to Redshift).

## Side-by-Side

| | AWS Glue | Apache Airflow |
|---|---|---|
| **Category** | Managed ETL service | Workflow orchestration platform |
| **Cloud scope** | AWS-only | Cloud-agnostic (self-hosted or managed via MWAA, Astronomer, Cloud Composer) |
| **Underlying engine** | Managed Apache Spark | None — it's Python + a scheduler; delegates actual compute elsewhere |
| **Infra management** | Fully serverless, zero infra | Requires running scheduler/webserver/workers (or a managed service like MWAA) |
| **Authoring** | Visual (Glue Studio) or PySpark/Scala scripts | Python DAGs (code-first) |
| **Metadata** | Built-in Data Catalog (Hive Metastore-compatible) | No catalog — relies on its own metadata DB for run state, not data schemas |
| **Scheduling** | Basic triggers/workflows | Rich DAG scheduling — cron, data-interval based, sensors, backfills |
| **Billing** | Pay per DPU-hour while job runs | Pay for infra (or managed service) regardless of what it's orchestrating |
| **Typical role in a pipeline** | The step that transforms data | The thing deciding when that step runs, what runs before/after it, and how failures/retries are handled |

## When You'd Reach for Each

- **Use Glue when:** you need to actually transform/move data (schema inference, format conversion, joins, dedup) and want serverless Spark without cluster management — especially if you're populating the Data Catalog for Athena/Redshift Spectrum queries.
- **Use Airflow when:** you have a multi-step pipeline spanning several systems (Glue + Databricks + Lambda + a dbt run + a Slack notification) and need centralized scheduling, dependency management, retries, and observability across all of them — especially if some of those systems aren't AWS-native.
- **Use both together:** very common pattern — Airflow as the conductor, Glue (and/or Databricks) as one of the instruments it's directing.

**One nuance worth mentioning if asked:** AWS Step Functions is actually the more natural *AWS-native* alternative to Airflow (both are orchestrators) — Glue isn't really Airflow's competitor at all, it's more like Databricks' competitor (both run Spark-based transforms). If an interviewer frames it as "Glue vs. Airflow," it's worth gently noting that distinction — it shows you understand orchestration vs. execution as separate concerns, not just two AWS tools that sound similar.
