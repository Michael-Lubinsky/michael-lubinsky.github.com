# Apache Airflow Interview Prep

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
