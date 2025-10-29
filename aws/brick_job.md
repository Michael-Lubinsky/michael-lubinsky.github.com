How to run your PySpark code every minute **outside a notebook** and manage it end-to-end.

# 1) Package your notebook logic as a Python entrypoint

Refactor your notebook into a tiny callable module plus a `main.py` runner. Put this in a Databricks Repo (recommended) or upload to DBFS.

```
repo-root/
  ingest/
    __init__.py
    job_logic.py      # your existing function(s)
    main.py           # entrypoint that calls your function
```

`job_logic.py` (sketch)

```
from pyspark.sql import SparkSession

def run_job():
    spark = SparkSession.builder.getOrCreate()

    # 1) Read from DynamoDB (however you currently do it)
    # ddb = spark.read.format("dynamodb")...  (or your connector)
    # 2) Transform
    # 3) Write to your Databricks table (on S3 / Delta)

    # example:
    # df.write.format("delta").mode("append").saveAsTable("my_catalog.my_schema.my_table")
```

`main.py`

```
from ingest.job_logic import run_job

if __name__ == "__main__":
    run_job()
```

Push this repo to Git and use **Repos** in Databricks to keep it synced.

# 2) Create a Databricks Job (non-interactive)

You have three good compute choices:

* **Serverless compute for Jobs** (best if available): fully managed, quick starts, no cluster babysitting.
* **Job cluster**: ephemeral cluster created per run (simple, but cold-start overhead every minute can be costly).
* **Existing all-purpose cluster**: fastest per-minute cadence (no cold start), but you pay for it to stay running.

For a true **every-minute** cadence, prefer **Serverless** or an **Existing cluster kept warm**. A Job cluster spinning up every minute is usually too slow/expensive.

## Create the Job (UI)

* Workflows → Jobs → Create Job
* Task type: **Python script**
* Source: **Repo** → pick your `main.py`
* Compute:

  * **Use Serverless compute** (if your workspace supports it), or
  * **Use existing cluster** (kept running; set Auto-Terminate to something long), or
  * **New job cluster** (only if you can tolerate startup time)
* Schedule: **Every 1 minute** (Scheduler uses UTC)
* Set **Timeout** (e.g., 50 seconds) and **Max concurrent runs = 1** to avoid overlaps
* Add **Retry** policy (e.g., 3 attempts, 10s backoff)
* Save

## Create the Job (JSON + CLI)

If you automate with the new `databricks` CLI:

`job.json` (example; adjust paths)

```
{
  "name": "ddb-to-delta-every-minute",
  "max_concurrent_runs": 1,
  "timeout_seconds": 50,
  "tasks": [
    {
      "task_key": "ingest-task",
      "python_wheel_task": null,
      "spark_python_task": {
        "python_file": "repos/you/your-repo/ingest/main.py"
      },
      "job_cluster_key": "job-cluster",
      "timeout_seconds": 50,
      "max_retries": 3,
      "min_retry_interval_millis": 10000,
      "retry_on_timeout": true
    }
  ],
  "job_clusters": [
    {
      "job_cluster_key": "job-cluster",
      "new_cluster": {
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "i3.xlarge",
        "num_workers": 1
      }
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 0/1 * * * ?",
    "timezone_id": "UTC",
    "pause_status": "UNPAUSED"
  }
}
```

Create/update:

```
databricks jobs create --json-file job.json
# or
databricks jobs reset --job-id <id> --json-file job.json
```

**Tip:** In the UI, selecting “Every minute” will populate a correct Quartz cron; if you’re unsure about the expression, use the UI first.

# 3) Credentials to DynamoDB/S3

Because you’re on **Serverless/Jobs**, the clean path is an **instance profile / IAM role** that grants read to DynamoDB and write to your S3/Delta location. In the job’s compute settings:

* For **Serverless compute**: attach the workspace’s **serverless access**/instance profile (your admin might need to map it).
* For **Existing or Job clusters**: set the **Instance Profile / IAM role**.
  Then your Spark code can use the default provider chain (no hardcoded keys). In Python, `boto3` (if used) will pick up the role automatically.

# 4) If you truly need “every minute,” consider streaming

A Structured Streaming job is often better than cron-style runs. You can:

* Wrap your logic as a streaming pipeline (e.g., `Trigger.ProcessingTime("1 minute")`).
* Deploy as a **continuous** job (no schedule; it runs once and keeps going).
* Use **Serverless** or an **existing cluster** to keep it alive.
  This avoids per-run startup, improves latency, and handles backpressure.

Minimal pattern:

```
(
  spark.readStream.format("...dynamodb-source...")
  .load()
  # transforms
  .writeStream
  .format("delta")
  .option("checkpointLocation", "s3://…/chk/ingest-ddb")
  .trigger(processingTime="1 minute")
  .toTable("my_catalog.my_schema.my_table")
)
```

# 5) How to stop the non-interactive job

You have several options:

* **Cancel the active run:** Workflows → Runs → select run → **Cancel**
  CLI: `databricks runs cancel --run-id <run-id>`
* **Pause the schedule:** Workflows → Job → **Pause**
  CLI: `databricks jobs pause --job-id <job-id>`
* **Delete the job:** Workflows → Job → **Delete**
  CLI: `databricks jobs delete --job-id <job-id>`
* **Stop compute:**

  * Serverless: stopping the run is enough; there’s no cluster to manage.
  * Existing cluster: **Terminate** it in Compute if you used one for the job.

# 6) Quick checklist for your case

* [ ] Move your notebook logic into `job_logic.run_job()`
* [ ] Put code in a Repo (so Jobs → Python script can point to it)
* [ ] Choose **Serverless compute for Jobs** (or an existing warm cluster)
* [ ] Schedule “Every minute” (UTC), timeout < 60s, retries, max concurrent = 1
* [ ] Ensure IAM role/instance profile grants DynamoDB read + S3 write
* [ ] (Optional but recommended) Convert to a single **streaming** job instead of per-minute batch

If you want, paste a snippet of how you’re reading DynamoDB and writing to S3/Delta, and I’ll turn it into a ready-to-run `job_logic.py` and `main.py` for you.
