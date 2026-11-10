## Celery and Celery Beat  

## 1. What are Celery and Celery Beat?

Celery is a distributed task queue framework for Python. It allows applications to submit tasks for execution by separate worker processes, potentially running on different machines.

Celery Beat is a scheduler that periodically submits Celery tasks to a message broker.

The distinction is important:

- Celery worker: Executes tasks.
- Celery Beat: Decides when scheduled tasks should be submitted.
- Message broker: Stores and delivers task messages to workers.
- Result backend: Optionally stores task results and execution states.

## 2. Architecture
<img width="540" height="383" alt="image" src="https://github.com/user-attachments/assets/3d8e2977-9656-4a45-9450-50d1a509296c" />

For example, imagine a system that processes compensation Excel files:

1. A user uploads a spreadsheet to a Django application.
2. Django submits a task to Redis.
3. A Celery worker reads the message and processes the spreadsheet.
4. The worker validates records and loads them into PostgreSQL.
5. Celery Beat schedules a nightly data quality check.

The web application doesn't need to wait for the ETL job to finish.

## 3. Install Celery and Redis on your MacBook

Assuming you have Python 3 and Homebrew:

```
brew install redis
brew services start redis

redis-cli ping
```

Expected output:

```
PONG
```

Create a project:

```bash
mkdir celery_tutorial
cd celery_tutorial

python3 -m venv .venv
source .venv/bin/activate

pip install "celery[redis]"
```

Our project will contain:

```
celery_tutorial/
├── tasks.py
└── submit.py
```

## 4. Write your first Celery application

Create `tasks.py`:

```python
from celery import Celery
import time

app = Celery(
    "demo",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

@app.task
def add(x, y):
    time.sleep(3)
    return x + y
```

Important details:

`@app.task` registers the function as a Celery task.

`broker` configures the message transport.

`backend` configures where results are stored. A result backend is optional.

Start a worker in terminal 1:

```
celery -A tasks:app worker --loglevel=info
```

Create `submit.py`:

```python
from tasks import add

result = add.delay(10, 20)

print("Task ID:", result.id)
print("Submitted asynchronously")

print("Result:", result.get(timeout=10))
```

Run it in terminal 2:

```
python submit.py
```

You'll see the task submitted immediately. The call to `result.get()` then waits approximately three seconds for the result.

### What happens internally?

1\. Producer publishes a task

`add.delay(10, 20)` serializes a message containing the task name, arguments, and task ID.

2\. Redis receives the message

The broker holds the pending task until a worker consumes it.

3\. Worker executes the function

The worker imports `tasks.add`, executes it, and optionally stores its result.

4\. Client retrieves the result

`result.get()` reads the result backend and returns `30`.

A crucial distinction:

```python
add(10, 20)         # Execute locally, synchronously
add.delay(10, 20)   # Submit to broker for worker execution
add.apply_async(args=(10, 20), countdown=5)
                    # Submit with a delay of ~5 seconds
```

`countdown` is for one-off delayed execution. For recurring tasks, use Celery Beat.

# Part 2 — Celery Beat

## 5. How Celery Beat works

Celery Beat is a separate process that maintains a schedule of periodic tasks.

For example:

- Every 10 seconds: Check pending imports.
- Every 5 minutes: Check failed jobs.
- Every night at 2 AM: Validate PostgreSQL data.
- Every Monday: Generate a weekly report.

Beat does not execute these tasks. It publishes messages to the broker, and workers execute them.

## 6. Implement periodic tasks

Replace `tasks.py` with:

```python
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timezone
import time

app = Celery(
    "demo",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

app.conf.update(
    timezone="UTC",
    enable_utc=True,
)

@app.task
def add(x, y):
    time.sleep(3)
    return x + y

@app.task
def check_pending_imports():
    print("Checking pending imports at",
          datetime.now(timezone.utc).isoformat())

@app.task
def nightly_validation():
    print("Running nightly data validation")

app.conf.beat_schedule = {
    "check-imports-every-10-seconds": {
        "task": "tasks.check_pending_imports",
        "schedule": 10.0,
    },
    "nightly-validation": {
        "task": "tasks.nightly_validation",
        "schedule": crontab(hour=2, minute=0),
    },
}

```

The task names use `tasks.` because Celery imports the module as `tasks`.

### Start three processes

Terminal 1

Redis

```
redis-server
```

If Redis is already running via `brew services`, skip this command.

Terminal 2

Celery worker

```
celery -A tasks:app worker --loglevel=info
```

Terminal 3

Celery Beat

```
celery -A tasks:app beat --loglevel=info
```

Every 10 seconds, Beat publishes `check_pending_imports` to Redis. The worker consumes the message and executes the task.

At 02:00 UTC, Beat submits `nightly_validation`.

## 7. Interval scheduling vs. cron scheduling

Celery Beat supports several scheduling methods.

| Schedule               | Configuration                                     |
| ---------------------- | ------------------------------------------------- |
| Every 30 seconds       | `30.0`                                            |
| Every 5 minutes        | `timedelta(minutes=5)`                            |
| Every hour at minute 0 | `crontab(minute=0)`                               |
| Every day at 2 AM      | `crontab(hour=2, minute=0)`                       |
| Every Monday at 9 AM   | `crontab(day_of_week="monday", hour=9, minute=0)` |

For example:

```python
from datetime import timedelta
from celery.schedules import crontab

app.conf.beat_schedule = {
    "job-a": {
        "task": "tasks.check_pending_imports",
        "schedule": timedelta(minutes=5),
    },
    "job-b": {
        "task": "tasks.nightly_validation",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

Cron schedules use the configured Celery timezone.

### Interactive scheduling example

Build a Celery Beat schedule

TaskCheck pending imports

Run frequency

Every 10 seconds

Every 5 minutes

Every day at 2 AM UTC

Generated Python configuration
```
app.conf.beat_schedule = {
    "scheduled-job": {
        "task": "tasks.check_pending_imports",
        "schedule": 10.0,
    },
}
```

# Part 3 — Celery in production

## 8. Retries and exception handling

Imagine an ETL task that calls an external API. The API occasionally times out.

Celery supports automatic retries:

```python
import requests

@app.task(
    bind=True,
    autoretry_for=(requests.exceptions.Timeout,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def fetch_data(self, url):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()
```

This example retries request timeouts. Other HTTP or connection failures need their own handling policy.

`retry_backoff=True` introduces increasing delays, and `retry_jitter=True` helps prevent many workers from retrying simultaneously.

### A critical interview concept: Idempotency

A task is idempotent when executing it multiple times produces the same intended final effect as executing it once.

Consider:

```python
@app.task
def import_customer(customer_id, name):
    # Risk: retries may insert duplicates
    insert_customer(customer_id, name)```

A better design uses a unique database key and an upsert:

```sql
INSERT INTO customers (customer_id, name)
VALUES (101, 'Alice')
ON CONFLICT (customer_id)
DO UPDATE SET name = EXCLUDED.name;
```

This is important because task redelivery and retries can cause the same operation to execute more than once.

## 9. What happens when a worker crashes?

Celery has acknowledgment settings that affect task delivery.

| Setting                           | Behavior                                           |
| --------------------------------- | -------------------------------------------------- |
| `task_acks_late=False`            | Worker normally acknowledges before execution      |
| `task_acks_late=True`             | Worker normally acknowledges after execution       |
| `task_reject_on_worker_lost=True` | Can requeue a task when its worker process is lost |

Example:

```python
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
```

These settings require careful consideration. Requeuing tasks after worker loss can create repeated failures, and late acknowledgment does not by itself guarantee redelivery in every crash scenario.

Interview takeaway: Celery should generally be treated as an at-least-once execution system when designing recoverable jobs. Use idempotency, durable state, and database constraints rather than assuming exactly-once execution.

## 10. What if a periodic job takes longer than its interval?

Suppose Beat schedules a job every five minutes, but each execution takes eight minutes.

Overlapping task executions
<img width="534" height="301" alt="image" src="https://github.com/user-attachments/assets/2aa079b9-e12b-4025-9f1c-5596b1307408" />

Illustrative timeline: each job runs for 8 minutes and starts 5 minutes after the previous one.

Celery Beat does not automatically prevent these executions from overlapping.

Possible solutions include a PostgreSQL advisory lock, Redis distributed lock, or a database-backed job lease. In a PostgreSQL-based ETL system, an advisory lock can be a natural solution.

For example:

```
SELECT pg_try_advisory_lock(12345);
```

This attempts to acquire a session-level lock. If another session holds it, the function returns `false`.

Release the lock when finished:

```
SELECT pg_advisory_unlock(12345);
```

Use the same database connection for acquiring and releasing the session-level lock. Handle connection failures and transaction boundaries carefully.

## 11. Monitoring and troubleshooting

Common Celery commands:

```
# See active tasks
celery -A tasks:app inspect active

# See reserved tasks
celery -A tasks:app inspect reserved

# See registered tasks
celery -A tasks:app inspect registered

# Check worker responsiveness
celery -A tasks:app inspect ping
```

For a graphical monitoring interface, you can use Flower:

```
pip install flower

celery -A tasks:app flower --port=5555
```

Then open `http://localhost:5555`.

Flower should be protected with appropriate authentication and network access controls in production.

### Common production problems

| Symptom                                         | Possible cause                                         |
| ----------------------------------------------- | ------------------------------------------------------ |
| Tasks remain queued                             | No worker, wrong queue, broker connection issue        |
| Beat logs scheduled tasks, but nothing executes | Worker not consuming the intended queue                |
| Task executes twice                             | Retries, redelivery, duplicate scheduling              |
| Task never finishes                             | External dependency hanging, deadlock, missing timeout |
| Beat stops scheduling                           | Beat process stopped or scheduler state issue          |
| Tasks overlap                                   | Execution time exceeds schedule interval               |

Run only one Beat scheduler for a given schedule unless you've implemented coordination to avoid duplicate dispatch.

# Part 4 — Celery vs. Celery Beat vs. cron vs. Airflow

This is a particularly useful comparison for your interview.

| Feature                      | Celery            | Celery Beat             | Linux cron               | Airflow                     |
| ---------------------------- | ----------------- | ----------------------- | ------------------------ | --------------------------- |
| Execute Python tasks         | Yes               | No                      | Yes, via scripts         | Yes, via operators          |
| Periodic scheduling          | Via Beat          | Yes                     | Yes                      | Yes                         |
| Distributed workers          | Yes               | No                      | No, not natively         | Yes, with suitable executor |
| Workflow dependencies        | Canvas primitives | No                      | No                       | DAGs                        |
| Built-in workflow history UI | Limited           | No                      | No                       | Yes                         |
| Typical use                  | Background jobs   | Recurring task dispatch | Simple scheduled scripts | ETL orchestration           |

A practical distinction:

- Use Celery to process an uploaded Excel file asynchronously.
- Use Celery Beat to schedule a daily PostgreSQL validation.
- Use cron for a simple standalone maintenance script.
- Use Airflow for a multi-stage ETL workflow with dependencies, backfills, and execution history.

## Part 5 — Interview practice

Test your understanding

0 / 5 answered

1\. Does Celery Beat execute tasks itself?

Yes, in its own worker pool

No, it submits tasks to the broker

Yes, using cron

2\. What happens when a Beat task takes longer than its scheduling interval?

Beat automatically waits

Celery automatically cancels the previous run

Executions may overlap

3\. Why is idempotency important in Celery?

Tasks may be retried or redelivered

It makes Python functions faster

It eliminates the need for a broker

4\. What is the main purpose of a result backend?

To schedule tasks

To store task results and states

To route task messages

5\. Which component would you use to schedule a nightly ETL task?

Celery Beat

Celery result backend

Celery task decorator alone

Check answersReset

## What you should be able to explain in your interview

# Celery and Celery Beat

**Celery** runs Python functions ("tasks") in separate worker processes, outside your web app. **Celery Beat** is a scheduler that puts tasks on the queue at set times. Your app does the same thing when it calls `.delay()`.

## 1. Why use it

A web request should return in milliseconds. Parsing a 50-sheet Excel upload, calling the SEC API for 300 filings, or refreshing a materialized view can take minutes. Celery moves that work out of the request. The app responds right away ("upload received"), and a worker does the heavy work in the background.

## 2. The parts

```
 Django / FastAPI app ──.delay()──►  BROKER  ◄──enqueue on schedule── BEAT (1 process)
                                  (Redis or RabbitMQ)
                                        │  workers pull tasks
                                        ▼
                                  WORKER processes ──► Postgres, APIs, files
                                        │
                                        ▼
                                  RESULT BACKEND (optional: Redis/Postgres)
```

- **Broker:** the queue that holds task messages, usually Redis or RabbitMQ.
- **Worker:** a process (`celery worker`) that pulls messages and runs the functions. You can run many, on several machines.
- **Result backend:** stores return values and task state. You only need it if something reads results, such as chords.
- **Beat:** only *enqueues* tasks. It never runs them. Workers do the work.

## 3. Minimal code

```python
# tasks.py
from celery import Celery

app = Celery("compensia",
             broker="redis://localhost:6379/0",
             backend="redis://localhost:6379/1")

@app.task
def ingest_file(file_id: int) -> int:
    rows = parse_and_load(file_id)   # your ETL logic
    return rows
```

```python
# in the web app
ingest_file.delay(42)                                    # run ASAP
ingest_file.apply_async(args=[42], countdown=60,         # in 60 s
                        queue="ingest", expires=3600)    # drop if not started in 1 h
```

Run it on Linux:

```bash
celery -A tasks worker -l info -c 4 -Q ingest,default   # 4 processes, two queues
celery -A tasks beat   -l info                          # the scheduler
```

On-prem, you'd run each command as a **systemd service** (or under supervisord) so it restarts when it crashes and its logs go to journald.

## 4. Making tasks reliable (the senior-level part)

```python
@app.task(bind=True,
          autoretry_for=(ConnectionError, TimeoutError),  # transient errors only
          retry_backoff=True, retry_jitter=True,          # 1s, 2s, 4s… plus randomness
          max_retries=5,
          acks_late=True,                 # acknowledge AFTER success, not on receipt
          soft_time_limit=600, time_limit=660)
def fetch_filing(self, cik: str, accession: str):
    if already_loaded(accession):         # idempotency check
        return "skipped"
    ...
```

These are the ideas worth naming in the interview:

1. **Idempotency.** Celery guarantees *at-least-once* delivery, so a task can run twice. Write tasks so a second run is harmless: upserts (`ON CONFLICT`), "already processed?" checks, or a unique load key.
2. **Retry only transient errors.** Network timeouts and lock waits are worth retrying. Bad data will fail the same way every time, so send it to a quarantine table and alert someone.
3. **`acks_late=True`.** Without it, a worker that crashes mid-task loses the message. With it, the broker delivers the task again. That's why idempotency matters.
4. **Pass IDs, not objects.** Use `ingest_file.delay(file_id)`, not a DataFrame or a model instance. Messages stay small and JSON-serializable, and the task always reads fresh data.
5. **Time limits.** A hung API call shouldn't block a worker forever. The soft limit raises an exception you can catch. The hard limit kills the process.
6. **Long tasks:** set `worker_prefetch_multiplier=1` so one worker doesn't reserve tasks it can't start. With Redis, the `visibility_timeout` (default 1 hour) must be longer than your longest task. Otherwise Redis redelivers the task while it's still running.
7. **Never wait for another task's result inside a task.** Calling `.get()` there can deadlock the worker pool. Use workflows instead (section 5).
8. **Django gotcha:** if you enqueue inside a database transaction, the worker may run before the commit and not find the row. Use this instead:
   ```python
   transaction.on_commit(lambda: ingest_file.delay(upload.id))
   ```
   This one is a good sign of real experience. Mention it.

## 5. Workflows: chaining tasks together

```python
from celery import chain, group, chord

# Steps in order; each result is passed to the next task
chain(validate.s(file_id), load.s(), refresh_views.s()).delay()

# Run in parallel
group(fetch_filing.s(cik, acc) for cik, acc in filings).delay()

# Run in parallel, then one callback when all finish (needs a result backend)
chord([fetch_filing.s(c, a) for c, a in filings])(build_peer_report.s())
```

`.s()` creates a "signature", which is a task call packaged up to run later.

## 6. Celery Beat in detail

You define the schedule in configuration:

```python
from celery.schedules import crontab
from datetime import timedelta

app.conf.timezone = "America/Los_Angeles"
app.conf.beat_schedule = {
    "nightly-sec-sync": {
        "task": "tasks.sync_new_filings",
        "schedule": crontab(hour=2, minute=15),          # 02:15 daily
        "options": {"queue": "ingest", "expires": 3 * 3600},
    },
    "refresh-mv-every-15-min": {
        "task": "tasks.refresh_views",
        "schedule": timedelta(minutes=15),
    },
    "weekday-report": {
        "task": "tasks.weekly_report",
        "schedule": crontab(hour=7, minute=0, day_of_week="mon-fri"),
    },
}
```

What to know about Beat:

- **Run exactly one Beat process.** Two Beat processes means every job runs twice. This is the most common Beat bug. Workers can scale out, but Beat can't.
- **Beat doesn't prevent overlap.** If a 15-minute job sometimes takes 20 minutes, two copies will run at once. Guard the task with a lock. A **Postgres advisory lock** works well, and it fits their stack:
  ```python
  with conn.cursor() as cur:
      cur.execute("SELECT pg_try_advisory_lock(%s)", (JOB_ID,))
      if not cur.fetchone()[0]:
          return "previous run still active"
  ```
- **Beat only enqueues.** If all workers are down, scheduled tasks pile up in the broker and then run in a burst. Set `expires` so stale runs are dropped instead.
- **Missed runs aren't all replayed.** If Beat was down for 6 hours, an hourly job won't run 6 times when Beat comes back. If a missing time window matters, the task should work out what's missing ("load everything since the last successful run") and not assume it runs every hour.
- **Where the schedule lives:** by default it's in a local `celerybeat-schedule` file. With **django-celery-beat**, schedules are stored in Postgres and can be edited in the Django admin without a deploy. Data Hub is Django, so ask whether they use it.

## 7. Monitoring and troubleshooting

```bash
celery -A tasks inspect active       # what's running now
celery -A tasks inspect reserved     # prefetched, waiting to run
celery -A tasks inspect scheduled    # ETA/countdown tasks
celery -A tasks purge                # empty the queues (careful!)
redis-cli LLEN ingest                # queue depth for the "ingest" queue
journalctl -u celery-worker -f       # worker logs under systemd
```

- **Flower** is a web UI that shows tasks, workers, failures and runtimes.
- Alert on: failed-task count (hook the `task_failure` signal to email or Slack), growing queue depth, and "nightly job hasn't succeeded in 26 hours". That last check catches the case where Beat itself died silently.
- Record every run in a `job_runs` table: task, arguments, start, end, status, row count, error. You get an audit trail (useful for SOC 2) and a way to tell what's missing.

## 8. When to use Celery, cron or Airflow

| | cron | Celery + Beat | Airflow |
| --- | --- | --- | --- |
| Best for | Simple scripts on one box | App-triggered work plus recurring jobs, in Python | Complex DAGs with dependencies and backfills |
| Retries | Write them yourself | Built in | Built in |
| Dependencies between steps | No | chain / chord | First-class DAGs |
| Overhead | None | Broker + workers | Scheduler, webserver, metadata DB |

**Your line for the interview:** "Celery fits a small team running Python and Postgres. The web app can trigger tasks and the scheduler is in the same code base. I'd only reach for Airflow if the dependency graphs got complex or we needed backfills."

## 9. Five likely questions with short answers

1. **"A nightly Celery job sometimes fails. What do you do?"** Check the logs and `job_runs` first. Then decide whether the failure is transient or caused by data. Transient: add retry with backoff. Data: quarantine it and alert. Then make the task idempotent so a rerun is safe.
2. **"A job ran twice. Why?"** Two Beat processes, a redelivery after `acks_late` or the visibility timeout, or a manual rerun. The fix is a single Beat, idempotent writes, and a lock.
3. **"How do you know scheduled jobs are actually running?"** Check last-success times and alert if a job is overdue, not only on failure. A dead Beat process produces no errors at all.
4. **"How do you handle a task that runs for an hour?"** Split it into chunks with `group` or a chord, set time limits, `prefetch_multiplier=1`, and a Redis visibility timeout longer than the task. Make the job resumable from a checkpoint.
5. **"Where do you get stuck with Celery?"** Answer this honestly: things like the visibility timeout surprise, or enqueuing before the database commit. Each is a nice chance to show you've hit real problems.

## Practice it (about 30 minutes in hour 3)

```bash
docker run -d -p 6379:6379 redis
pip install celery redis flower
```

1. Put the `tasks.py` above in a folder. Add a task that randomly raises `ConnectionError`, and watch the retries with backoff.
2. Add a Beat entry with `timedelta(seconds=10)` and start Beat and a worker in two terminals.
3. Make the task sleep 15 seconds and watch the runs overlap. Then add the advisory lock (or a Redis lock) and watch the overlap stop.
4. Kill the worker with `kill -9` during a task with `acks_late=True`, restart it, and watch the task run again.
5. Run `celery -A tasks flower` and open http://localhost:5555.

If you do step 4 yourself, you can say in the interview that you've watched redelivery happen. That carries more weight than having read about it.

## Why not Celery?
Most teams that leave Celery aren't leaving because it's broken. They leave because it's **complex, its defaults surprise people, and it was built before asyncio and Postgres-backed queues were common**. Here are the main pain points, grouped by type.

## 1. Defaults that cause silent problems

- **Tasks are acknowledged on receipt (early ack) by default.** If a worker crashes mid-task, the task is gone. You have to opt in to `acks_late`, and then you have to make tasks idempotent.
- **Prefetching.** By default each worker process reserves several tasks ahead. With long tasks, one busy worker holds tasks hostage while other workers sit idle. Teams find this by accident and then learn about `prefetch_multiplier=1` and `-Ofair`.
- **Redis visibility timeout.** Any task running longer than the timeout (one hour by default) gets delivered a second time while the first run is still going. You end up with duplicate runs and no error.
- **Settings sprawl.** There are hundreds of settings across Celery, Kombu (messaging) and billiard (process pool). Behavior varies by broker, and some features work well on RabbitMQ and poorly on Redis (priorities, chords).

## 2. Weak operations and visibility

- **No lasting task history.** Results expire. Flower shows recent events but isn't an audit log. "Did last Tuesday's job run, and what did it process?" usually needs your own `job_runs` table.
- **Debugging is hard.** Tracebacks are split between producer logs and worker logs. Canvas workflows (chords especially) fail in confusing ways, and a failed chord member can leave the callback hanging.
- **Memory growth in long-lived workers.** Teams end up setting `worker_max_tasks_per_child` to recycle processes.
- **Testing.** `task_always_eager` runs tasks inline, which behaves differently from real workers, so bugs get through.

## 3. Beat's limits

- **It's a single point of failure with no built-in high availability.** If it dies quietly, nothing runs and nothing errors.
- **Running two Beat processes doubles every job.**
- **It doesn't prevent overlapping runs.** You add the locking yourself.
- **Schedule state is kept in a local file** unless you add django-celery-beat.

## 4. The architecture is showing its age

- **No native asyncio.** Celery tasks are synchronous. FastAPI and other async-first teams find it awkward and switch to async-native queues such as arq or Taskiq.
- **The dual-write problem.** You save to Postgres and enqueue to Redis. These are two systems, and there's no transaction across them. If the enqueue fails after the commit, the work is lost. If the worker runs before the commit, it can't find the row. `on_commit` and the outbox pattern only partly fix this.
- **An extra moving part.** Redis or RabbitMQ has to be run, monitored, persisted and secured, often only to support the task queue.
- **No durable workflows.** A 10-step process that fails at step 7 can't resume where it stopped unless you build checkpointing yourself.
- **Maintenance.** It's a large, old codebase with a small maintainer team, and some long-standing bugs have stayed open for years.

## Where teams go, and why

| Alternative | What they gain | Typical reason for switching |
| --- | --- | --- |
| **RQ** | Very simple, Redis only | "We only need fire-and-forget jobs" |
| **Dramatiq** | Safer defaults (ack after processing, retries with backoff built in), small codebase | Tired of Celery's surprising defaults |
| **Huey** | Lightweight, scheduled jobs built in, can use Redis or SQLite | Small apps that don't want Celery's weight |
| **arq / Taskiq** | Native asyncio | FastAPI or other async codebases |
| **Postgres-backed queues** (Procrastinate, PgQueuer, django-tasks-db) | No broker; enqueue *in the same transaction* as your data, using `SELECT … FOR UPDATE SKIP LOCKED` | Removes Redis and fixes the dual-write problem |
| **Temporal / Hatchet** | Durable workflows that resume after failure, with full run history | Long multi-step business processes |
| **Airflow / Dagster / Prefect** | Dependency graphs, backfills, data lineage | Scheduled data pipelines, not app tasks |

**New since late 2025:** Django now has a standard API for background tasks, but it deliberately doesn't run them. Django 6.0 includes a built-in Tasks framework for running code outside the HTTP request–response cycle, while the responsibility for running tasks continues to belong to external worker processes. Django 6.0 ships two backends, ImmediateBackend and DummyBackend, and both exist for development and testing. For real execution you add a third-party backend such as the database-backed django-tasks-db. The general view is that for complex workflows with chaining, retries, and periodic scheduling, Celery remains the established choice.

## How to use this in the Compensia interview

They run Celery today, and you're joining someone else's system, so **don't pitch a migration**. Show that you know where Celery bites and how to harden it:

> "Celery fits your stack. The places it usually hurts are early acks, prefetch with long tasks, Beat being a single point of failure, and the gap between committing to Postgres and enqueuing to Redis. I'd check those first: acks_late plus idempotent tasks, alerts when a job is overdue, a lock against overlapping runs, and on_commit for enqueues. If the queue ever became a real pain point, a Postgres-backed queue would be worth evaluating, since Postgres is already your core system and it would remove the Redis dependency. But I wouldn't change it without a concrete reason."

That answer shows depth, respect for the existing design, and judgment, which are the three things Christina is looking for.

Want me to add the Celery lesson and this comparison to your prep doc as a new section?
