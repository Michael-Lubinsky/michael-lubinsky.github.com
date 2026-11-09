## Celery

# Celery and Celery Beat — Practical Python Tutorial

Since you're preparing for a Compensia interview, I'll focus on how Celery works internally, how to implement it in Python, how Celery Beat schedules tasks, and how to troubleshoot production problems.

We'll build a small ETL system that processes data and runs scheduled jobs, using Redis as the message broker.

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
                    # Submit with a delay of ~5 seconds```

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

```
from datetime import timedeltafrom celery.schedules import crontabapp.conf.beat_schedule = {    "job-a": {        "task": "tasks.check_pending_imports",        "schedule": timedelta(minutes=5),    },    "job-b": {        "task": "tasks.nightly_validation",        "schedule": crontab(hour=2, minute=0),    },}
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

&#x20;Copy

app.conf.beat_schedule = {\
&#x20;   "scheduled-job": {\
&#x20;       "task": "tasks.check_pending_imports",\
&#x20;       "schedule": 10.0,\
&#x20;   },\
}

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

After practicing this tutorial, you should be comfortable discussing Celery's broker/worker architecture, Beat's periodic scheduling, task retries, acknowledgment semantics, idempotency, worker failures, monitoring, and the differences between Celery and Airflow.

The next useful exercise is to build a realistic Celery + Celery Beat + PostgreSQL ETL project where a Python task imports CSV records into PostgreSQL, Beat schedules periodic validation, and failed tasks can be retried safely.

Build the PostgreSQL ETL project Practice Celery interview questions
