Given:

* Files are **small**
* They arrive only **a few times per day**
* You’re already using a **Databricks Job with File Arrival trigger**

👉 I would **recommend batch DataFrames**, not a long-running streaming query.

---

## Why batch is a better fit here

1. **File Arrival trigger is already your “streaming” layer**

   * The Job run is started *only when a new file arrives*.
   * Each run can just do a **one-shot batch** read of the new files, transform, and write output.
   * No need to manage streaming checkpoints, query lifecycle, etc.

2. **Cluster lifecycle is simpler**

   * Job starts → reads the new file(s) → writes to target table → stops.
   * With streaming you’d typically want a long-running cluster, or at least `trigger(once/availableNow)` and `awaitTermination()`. That’s extra plumbing for no real gain at your volume.

3. **Cost and complexity**

   * For “few files/day”, streaming ≈ overkill.
   * Batch is easier to reason about, debug, and re-run for a given file/date.

---

## How it usually looks with batch + file arrival

File Arrival trigger can pass the new paths into your job (e.g. via widget or param). Then in the notebook:

```python
from pyspark.sql import functions as F

# Example: widget populated by file arrival trigger with comma-separated paths
dbutils.widgets.text("input_file_paths", "")
raw_paths = dbutils.widgets.get("input_file_paths")

if not raw_paths:
    print("No input_file_paths provided, nothing to process.")
else:
    paths = [p.strip() for p in raw_paths.split(",") if p.strip()]
    print(f"Processing {len(paths)} new files:")
    for p in paths:
        print("  ", p)

    df_raw = (
        spark.read
             .format("json")
             .load(paths)
             .withColumn("source_file", F.input_file_name())
    )

    # your transformations here…
    df_transformed = ...  # build car_daily_summary cols etc.

    (
        df_transformed
        .write
        .format("delta")
        .mode("append")
        .saveAsTable("hcai_databricks_dev.chargeminder2.car_daily_summary")
    )
```

This plays perfectly with “small, infrequent files”.

---

## When I *would* recommend streaming / Auto Loader

Use `readStream().format("cloudFiles")` (Auto Loader) if:

* You have **lots of files** arriving frequently, or
* Need **schema evolution**, `_rescued_data`, and file-discovery optimizations, or
* Want a **continuous** pipeline independent of Jobs.

Even then, for job-style runs you’d typically do:

```python
df = spark.readStream.format("cloudFiles")...
query = (
    df.writeStream
      .format("delta")
      .option("checkpointLocation", CHECKPOINT_PATH)
      .trigger(availableNow=True)  # or once=True
      .start(TARGET_PATH)
)
query.awaitTermination()
```

That’s still more machinery than you need for “few files/day”.

---

### Bottom line

For your scenario (small, few-per-day, job on File Arrival):

➡️ **Batch DataFrames (`spark.read`) inside the job task are the right tool.**
Streaming/Auto Loader is great, but it shines when the *file arrival itself* is large/continuous, not when you’re already using File Arrival as the trigger.

Great question — **Databricks File Arrival triggers do *not* magically populate a widget for you**.
They provide file arrival info through a **special field in the Job run context**, which *you* must read inside your job code.

Let me explain exactly how this works.

---

# ✅ **How File Arrival Trigger passes file information**

When a Databricks Job task is triggered by a **File Arrival event**, Databricks injects a special JSON payload into the job run context.

You access it through:

```python
dbutils.jobs.taskContext().get()
```

Inside that JSON, you will find:

```
taskConfig
 └── file_arrival
        ├── files
        │     ├── path
        │     ├── event_time
        │     ├── size
        │     └── ...
        └── directory
```

---

# 📌 **Example: Read file-arrival info in PySpark**

Here’s the correct way to extract the list of files:

```python
from pyspark.sql import functions as F
import json

ctx = dbutils.jobs.taskContext().get()

# This field is only present when job is triggered by File Arrival
file_arrival_info = ctx.get("file_arrival", None)

if file_arrival_info is None:
    print("⚠️ Not triggered by file arrival event. Nothing to process.")
else:
    files = file_arrival_info.get("files", [])
    paths = [f["path"] for f in files]

    print(f"🔔 Files that triggered this job ({len(paths)}):")
    for p in paths:
        print(" -", p)

    # Read new files (batch mode)
    df_raw = (
        spark.read
             .format("json")
             .load(paths)
             .withColumn("source_file", F.input_file_name())
    )

    print(f"Read {df_raw.count()} records.")
```

---

# 🔍 **Output looks like:**

```text
file_arrival: {
  "files": [
      {
         "path": "s3://mybucket/path/file1.json",
         "size": 1024,
         "event_time": "2025-01-10T03:22:41Z"
      },
      {
         "path": "s3://mybucket/path/file2.json",
         "size": 981,
         "event_time": "2025-01-10T03:22:41Z"
      }
  ],
  "directory": "s3://mybucket/path/"
}
```

---

# 🚀 **Full recommended job pattern (Batch mode + File Arrival)**

```python
import json
from pyspark.sql import functions as F

ctx = dbutils.jobs.taskContext().get()

file_arrival_info = ctx.get("file_arrival", None)

if not file_arrival_info:
    print("No new files – job was not triggered by File Arrival.")
    dbutils.notebook.exit("NO FILES")

files = file_arrival_info["files"]
paths = [x["path"] for x in files]

print(f"Processing {len(paths)} new files")

# Batch read (recommended)
df_raw = (
    spark.read
         .format("json")
         .load(paths)
         .withColumn("source_file", F.input_file_name())
)

# Skip empty file
if not df_raw.head(1):
    print("Empty batch. Skipping.")
    dbutils.notebook.exit("EMPTY")

# Process further...
```

---

# ❗ **Important clarification**

### You do **NOT** use widgets for File Arrival trigger.

Widgets are for user-driven parameters only.

File Arrival → **Databricks automatically injects metadata into task context**.

---

# ✔ Summary

| What you want      | How it works                                                    |
| ------------------ | --------------------------------------------------------------- |
| Get file paths     | Use `dbutils.jobs.taskContext().get()["file_arrival"]["files"]` |
| Do batch ingestion | Use `spark.read` (recommended for few small files/day)          |
| Avoid streaming    | Yes — streaming not needed in your use case                     |
| Widgets?           | ❌ Not used for file arrival info                                |

---

If you want, I can generate:

* A **complete production-ready Databricks job notebook**
* Auto-create rollup logic
* Logging
* Error handling + retries
* MERGE to target table

Just say the word!


## forEachBatch Error
```
Pipeline failed: [STREAMING_CONNECT_SERIALIZATION_ERROR] Cannot serialize the function `foreachBatch`.
If you accessed the Spark session, or a DataFrame defined outside of the function, or any object that contains a Spark session,
please be aware that they are not allowed in Spark Connect.
For `foreachBatch`, please access the Spark session using `df.sparkSession`, where `df` is the first parameter in your `foreachBatch` function.

For `StreamingQueryListener`,
please access the Spark session using `self.spark`.
For details please check out the PySpark doc for `foreachBatch` and `StreamingQueryListener`.

INFO:__main__:
Spark session stopped
 You cannot use dbutils within a spark job or otherwise pickle it.
            If you need to use getArguments within a spark job, you have to get the argument before
            using it in the job. For example, if you have the following code:

              myRdd.map(lambda i: dbutils.args.getArgument("X") + str(i))

            Then you should use it this way:

              argX = dbutils.args.getArgument("X")
              myRdd.map(lambda i: argX + str(i))

```            
This exact error almost always appears when you run an Auto Loader (or any Structured Streaming) job on a **Spark Connect-based cluster** (i.e. a Serverless compute, SQL warehouse-started notebook, or a cluster started with “Enable Spark Connect” turned on) **and** you use `.foreachBatch()` in a way that tries to capture non-serializable objects (most commonly `dbutils`, global variables, or the notebook’s `spark` session).

### Why the error happens

Spark Connect runs the driver code on your browser/notebook side and the executor code remotely.  
Everything you pass inside `foreachBatch` (or UDFs, etc.) must be **serializable with pickle**.  
`dbutils` and the notebook’s `spark` object are **explicitly non-serializable** in Spark Connect → instant failure with the message you saw.

### How to fix it (100% working patterns)

#### Option 1 (Recommended) – Don’t use `foreachBatch` at all  
Just write directly to Delta with `writeStream` – this is the simplest and most reliable on Serverless/Spark Connect.

```python
# This works perfectly on Serverless / Spark Connect
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/tmp/checkpoints/my_stream")
    .load("abfss://landing@mystorage.dfs.core.windows.net/incoming/")
    .writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/tmp/checkpoints/my_stream")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)          # or leave empty for continuous
    .table("my_catalog.my_db.bronze_table")   # or .start("/path/to/table")
)
```

→ No `foreachBatch` → no serialization problem.

#### Option 2 – You really need custom logic inside `foreachBatch` (e.g. move files, call external API, etc.)

Do it like this — **never capture dbutils or the outer spark**:

```python
```python
def process_batch(df, batch_id):
    # CORRECT: use the spark session that comes with the DataFrame
    spark = df.sparkSession
    
    # Do whatever you need with normal Spark APIs
    df.write.mode("append").saveAsTable("my_catalog.my_db.bronze_table")
    
    # If you need to move/archive files, use pure Hadoop FS API (works everywhere)
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    raw_path = "abfss://landing@mystorage.dfs.core.windows.net/incoming/"
    archive_path = "abfss://landing@mystorage.dfs.core.windows.net/processed/"
    
    # List files that were just processed in this micro-batch
    files_this_batch = [row._1 for row in df.select("_metadata.file_path").distinct().collect()]
    
    for file_path in files_this_batch:
        src = spark._jvm.org.apache.hadoop.fs.Path(file_path)
        dst = spark._jvm.org.apache.hadoop.fs.Path(archive_path + src.getName())
        fs.rename(src, dst)   # moves the file

# Now register the function
(spark.readStream
    .format("cloudFiles")
    ...
    .foreachBatch(process_batch)
    .option("checkpointLocation", checkpoint_path)
    .trigger(availableNow=True)
    .start()
)
```

#### Option 3 – You really need `dbutils` inside the batch (e.g. secrets, widgets, fs utils)

Extract everything **before** you start the stream:

```python
# Do this in notebook cells BEFORE the streaming query
archive_path = dbutils.widgets.get("archive_path")          # or hard-code
secret_value = dbutils.secrets.get("my-scope", "my-key")

def process_batch_with_dbutils(df, batch_id):
    spark = df.sparkSession
    
    df.write.mode("append").saveAsTable("bronze_table")
    
    # Use the variables that were captured BEFORE the stream started
    print("Using secret:", secret_value)
    
    # Move files with dbutils (this works because we captured the path earlier)
    files = [row.file_path for row in df.select("_metadata.file_path").collect()]
    for f in files:
        file_name = f.split("/")[-1]
        dbutils.fs.mv(f, f"{archive_path}{file_name}")

# Now start the stream
(spark.readStream
    .readStream
    .format("cloudFiles")
    ...
    .foreachBatch(process_batch_with_dbutils)
    .start()
)
```

### What does NOT work on Spark Connect / Serverless

```python
def bad_batch(df, batch_id):
    dbutils.fs.mv(...)           # ← crashes
    spark.session...            # ← also crashes
    some_global_variable        # if it contains spark or dbutils → crashes
```

### Quick checklist for your notebook

- Are you on Serverless compute or a cluster with “Spark Connect” enabled? → avoid `foreachBatch` if possible.
- Do you use `.table()` or `.start(path)` to write the stream.
- If you must use `foreachBatch`, never reference `dbutils` or the outer `spark` inside the function.
- Use `df.sparkSession` inside the function when you need Spark.

Follow Option 1 in 95 % of cases and you will never see this error again.

Here are the exact ways to detect and fix the issue on **Serverless Compute** or any cluster with **Spark Connect** enabled.

### 1. How to Check if Spark Connect is Enabled

#### Programmatically (PySpark / Python)

Run this in any notebook cell — works everywhere:

```python
# Method 1: Most reliable (works in DBR 13.3+ and all Serverless)
print(spark.conf.get("spark.databricks.clusterUsageTags.isSparkConnectCluster", "false").lower() == "true")

# Method 2: Also very reliable
print("spark.connect" in spark.conf.get("spark.sql.execution.arrow.pyspark.enabled", "") or 
      spark.conf.get("spark.databricks.isServerless", "false).lower() == "true")

# Method 3: One-liner you can paste anywhere
is_spark_connect = spark.conf.get("spark.databricks.clusterUsageTags.clusterOwnerOrgId", None) is not None and \
                   spark.conf.get("spark.databricks.isServerless", "false").lower() == "true" or \
                   spark.conf.get("spark.databricks.clusterUsageTags.isSparkConnectCluster", "false").lower() == "true"

print("Spark Connect / Serverless =", is_spark_connect)
```

If it prints **True** → you are on Serverless or a Spark Connect cluster → `foreachBatch` with `dbutils` or outer `spark` will fail.

#### Via Web UI (100% accurate)

1. Open your running cluster page.
2. Go to the Configuration tab → Spark cluster UI → Environment tab.
3. Look for any of these properties:

| Property                                         | Value that means Spark Connect is ON |
|--------------------------------------------------|--------------------------------------|
| `spark.databricks.isServerless`                  | `true`                               |
| `spark.databricks.clusterUsageTags.isSparkConnectCluster` | `true`                               |
| `spark.connect.grpc.binding.port`                | any value (e.g. 15002)               |

If you see any of the above → Spark Connect is active.

### 2. How to Modify Your Code So It Works Everywhere (Serverless + Classic Clusters)

Use this future-proof pattern — works on Serverless, Spark Connect clusters, and normal clusters:

```python
from pyspark.sql.functions import input_file_name, current_timestamp

input_path       = "abfss://landing@storage.dfs.core.windows.net/incoming/"
processed_path   = "abfss://landing@storage.dfs.core.windows.net/processed/"
checkpoint_path  = "/dbfs/tmp/checkpoints/my_autoloader"

# Extract everything that is NOT serializable BEFORE the stream
archive_path = processed_path   # or dbutils.widgets.get("archive_path") etc.
some_secret  = dbutils.secrets.get(scope="my-scope", key="my-key") if not spark.conf.get("spark.databricks.isServerless", "false") == "true" else "dummy"

def process_batch(df, batchId):
    if df.rdd.isEmpty(): 
        return   # nothing to do

    spark = df.sparkSession   # ← THIS IS THE ONLY SPARK YOU ARE ALLOWED TO USE

    # 1. Write the data (recommended way)
    (df.write
       .format("delta")
       .mode("append")
       .option("mergeSchema", "true")
       .saveAsTable("my_catalog.my_db.bronze_table"))

    # 2. Archive / move processed files (two safe options)

    # Option A: Use pure Hadoop FS (works 100% on Serverless)
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    processed_files = [row.file_path for row in df.select("_metadata.file_path").distinct().collect()]

    for src_path in processed_files:
        src = spark._jvm.org.apache.hadoop.fs.Path(src_path)
        file_name = src.getName()
        dst = spark._jvm.org.apache.hadoop.fs.Path(archive_path + file_name)
        if fs.exists(src):          # safety check
            fs.mkdirs(dst.getParent()) # ensure parent folder exists
            fs.rename(src, dst)

    # Option B: Use dbutils only if we are NOT on Serverless (safe fallback)
    try:
        is_serverless = spark.conf.get("spark.databricks.isServerless", "false").lower() == "true"
        if not is_serverless:
            for src_path in processed_files:
                file_name = src_path.split("/")[-1]
                dbutils.fs.mv(src_path, archive_path + file_name)
    except Exception as e:
        print("dbutils not available (expected on Serverless):", e)

# Final streaming query — this works everywhere
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .load(input_path)
    .withColumn("ingest_time", current_timestamp())
    .withColumn("source_file", input_file_name())
    .writeStream
    .foreachBatch(process_batch)
    .option("checkpointLocation", checkpoint_path)
    .trigger(availableNow=True)    # perfect for file-arrival jobs
    .start()
)
```

### Even Better: Avoid foreachBatch Completely (Recommended for New Code)

```python
# 100% Serverless-safe, simplest, and fastest
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .load(input_path)
    .writeStream
    .format("delta")
    .option("checkpointLocation", checkpoint_path)
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .table("my_catalog.my_db.bronze_table")   # or .start("/path/to/table")
)
```

Then move files in a separate task (or with Databricks Workflows) using `dbutils.fs.mv` — no serialization issues at all.

### Summary

| Question                              | Answer                                                                 |
|---------------------------------------|------------------------------------------------------------------------|
| How to detect Spark Connect?          | `spark.conf.get("spark.databricks.isServerless") == "true"` or check UI Environment tab |
| Will my old `foreachBatch` + `dbutils` work on Serverless? | No → serialization error |
| How to make it work everywhere?       | Never use `dbutils` or outer `spark` inside `foreachBatch`. Use `df.sparkSession` + Hadoop FS API or move archiving to a separate task |

Use the code pattern above and you will never see the `[STREAMING_CONNECT_SERIALIZATION_ERROR]` again — on any Databricks compute type.

## Databricks Job

It Streamining we use readStream() and writeStream(), checkpoint required



## 🔍 **cloudFiles.useNotifications vs cloudFiles.useManagedFileEvents**

  These are **two different approaches** to file event notifications in Databricks Auto Loader. Let me break down the key differences:

 Here’s a clear breakdown of the difference between the two options in Databricks Auto Loader: `cloudFiles.useNotifications` vs `cloudFiles.useManagedFileEvents` — when to use each, what they require, and how they behave.

---

| Option                                       | Description                                                                                                                                                                                                                                                                     | When to use                                                                                                                                  | Key requirements & caveats                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`cloudFiles.useNotifications = true`**     | Legacy file-notification mode: Auto Loader uses cloud storage events (e.g., S3 → SNS → SQS) or you supply your own queue, to detect new files rather than scanning the entire directory. ([Databricks Documentation][1])                                                        | Useful when you want more real-time detection than listing, but haven’t adopted the newer “file events” service yet.                         | • You must supply or allow creation of SNS + SQS (or provider equivalent) for your cloud storage. ([Databricks Documentation][1]) <br>• You must ensure your IAM role can create or subscribe to those resources.<br>• Some settings (e.g., backfill interval, incremental listing) still apply.<br>• You must **not** set `useManagedFileEvents = true` at the same time. ([Databricks Documentation][2])                                                                                                                                                           |
| **`cloudFiles.useManagedFileEvents = true`** | Modern (“file events”) mode: If your load path is defined as a UC external location with file-events enabled, Auto Loader uses a managed notifications service and internal queue/cache rather than requiring you to manage SNS/SQS per stream. ([Databricks Documentation][3]) | The preferred long-term mode if you’re using Unity Catalog and external locations, want simpler setup, fewer queues, and better scalability. | • Requires your workspace to support external locations + file-events (often UC enabled). ([Databricks Documentation][1]) <br>• Only available in newer runtimes (e.g., 14.3 LTS+) on AWS. ([Databricks Documentation][3]) <br>• Certain options are **not supported** when using it (e.g., `cloudFiles.useNotifications`, `cloudFiles.backfillInterval`, some path-rewrites). ([Databricks Documentation][4]) <br>• On first run it still does a full listing to establish the cache, then subsequent runs use event notifications. ([Databricks Documentation][3]) |

---

### 🔍 Key behavioral differences

* **Discovery mechanism**

  * `useNotifications = true`: Auto Loader listens to or polls a queue you manage (or created) for file‐created events, so new files show up faster.
  * `useManagedFileEvents = true`: Auto Loader uses a **managed event service** (Databricks sets up the underlying infrastructure) that watches the external location; it then uses an internal “cache” of file arrival events — directory listing is minimized. ([Databricks Documentation][3])

* **Setup & maintenance**

  * Legacy (`useNotifications`): You (or your cloud team) must configure SNS/SQS, subscriptions, IAM permissions, etc. Limits exist (e.g., number of queues per bucket). ([Databricks Documentation][1])
  * Managed (`useManagedFileEvents`): Much simpler to maintain; less cloud-resource overhead, fewer queues. Databricks handles many parts of the plumbing. ([Databricks Documentation][1])

* **Supported options**

  * If using `useManagedFileEvents`, some legacy options are disabled: e.g., `cloudFiles.useNotifications` cannot be set at the same time. ([Databricks Documentation][2])
  * If using `useNotifications`, you still may need to consider `cloudFiles.backfillInterval`, queueUrl options, etc.

* **Fallback behavior**

  * With managed file-events, even though event notifications are used, Auto Loader may fallback to directory listing in certain cases (e.g., initial run, path changed, no run in 7+ days) to ensure completeness. ([Databricks Documentation][3])
  * With legacy notifications, you still might need to schedule periodic directory listing/backfill if events are delayed or missed.

---

### 🎯 Which one should **you** pick?

Given your environment:

* You are using UC or want to move towards it — then `useManagedFileEvents=true` is **ideal**.
* If you have an external location set up with file events enabled (via storage credential + external location) and newer runtime (14.3+), pick `useManagedFileEvents`.
* If you don’t yet have the external location/file-events infra, and you already built SNS/SQS or want quicker short-term setup, `useNotifications=true` is okay — but you should plan to migrate to managed mode.

---

### 🧾 Example usage snippets

**Legacy notifications mode:**

```python
stream = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", CONFIG["schema_path"])
    .option("cloudFiles.useNotifications", "true")
    .option("cloudFiles.queueUrl", "https://sqs.us-east-1.amazonaws.com/123456789012/yourQueue")  # if you self-manage
    .schema(raw_schema)
    .load(SOURCE_PATH)
)
```

**Managed file events mode:**

```python
stream = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", CONFIG["schema_path"])
    .option("cloudFiles.useManagedFileEvents", "true")
    .schema(raw_schema)
    .load(SOURCE_PATH)
)
```

---

### ✅ Summary

* `cloudFiles.useNotifications`: legacy queue-based file event detection; you manage or configure SNS/SQS.
* `cloudFiles.useManagedFileEvents`: newer, preferred mode if using UC + external locations; less manual infra, better scalability.

---


[1]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/file-notification-mode?utm_source=chatgpt.com "Configure Auto Loader streams in file notification mode"
[2]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/options?utm_source=chatgpt.com "Auto Loader options | Databricks on AWS"
[3]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/file-events-explained?utm_source=chatgpt.com "Auto Loader with file events overview | Databricks on AWS"
[4]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/migrating-to-file-events?utm_source=chatgpt.com "Migrate to Auto Loader with file events | Databricks on AWS"


## 📊 **Quick Comparison**

| Feature | useNotifications | useManagedFileEvents |
|---------|------------------|----------------------|
| **Status** | Legacy (older) | Modern (recommended) |
| **Who manages SNS/SQS?** | You or Auto Loader | Databricks fully manages |
| **Setup complexity** | Medium-High | Low |
| **Resource cleanup** | Manual | Automatic |
| **Requires Storage Credential?** | ✅ Yes | ✅ Yes |
| **Cost tracking** | Your AWS account | Your AWS account (but tagged) |
| **Recommended?** | ⚠️ Legacy | ✅ Yes |

---

## 🏗️ **Architecture Differences**

### **useNotifications = true (Legacy Approach)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. You or Auto Loader creates:                             │
│     - SNS Topic (manual or auto)                            │
│     - SQS Queue (manual or auto)                            │
│     - S3 Event Notification (manual or auto)                │
│                                                              │
│  You must specify:                                          │
│     .option("cloudFiles.queueUrl", "your-queue-url")       │
│  or let Auto Loader create with "auto"                      │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. S3 → SNS → SQS → Databricks polls queue                │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. If you delete stream:                                   │
│     ⚠️ SNS/SQS resources remain (manual cleanup needed)    │
└─────────────────────────────────────────────────────────────┘
```

---

### **useManagedFileEvents = true (Modern Approach)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. Databricks automatically creates & manages:             │
│     - SNS Topic (tagged as "databricks-auto-ingest-*")     │
│     - SQS Queue (tagged as "databricks-auto-ingest-*")     │
│     - S3 Event Notification                                 │
│                                                              │
│  You specify: NOTHING! Fully automatic                      │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. S3 → SNS → SQS → Databricks polls queue                │
│     (Same flow, but managed by Databricks)                  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. If you delete stream:                                   │
│     ✅ Databricks automatically cleans up SNS/SQS          │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 **Code Examples**

### **Example 1: useNotifications (Legacy)**

```python
# Option A: You manually create SNS/SQS
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "true")
  .option("cloudFiles.queueUrl", "https://sqs.us-east-1.amazonaws.com/447759255101/my-queue")
  .load("s3://chargeminder-2/data/"))

# Option B: Let Auto Loader create (but you manage lifecycle)
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "true")
  .option("cloudFiles.queueUrl", "auto")  # Auto Loader creates queue
  .load("s3://chargeminder-2/data/"))
```

**Issues:**
- ⚠️ If stream is deleted, SNS/SQS resources remain
- ⚠️ Must manually clean up orphaned resources
- ⚠️ More configuration options to manage

---

### **Example 2: useManagedFileEvents (Modern - Recommended)**

```python
# Databricks handles EVERYTHING automatically
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useManagedFileEvents", "true")  # That's it!
  .load("s3://chargeminder-2/data/"))

# No need to specify:
# - queueUrl
# - SNS topic
# - Resource names
# All managed automatically!
```

**Benefits:**
- ✅ Automatic resource creation
- ✅ Automatic resource cleanup
- ✅ Less configuration
- ✅ Databricks handles everything

---

## 🔑 **IAM Policy Requirements**

Both approaches need similar permissions, but `useManagedFileEvents` uses specific naming conventions.

### **Your Policy Already Supports Both!**

From your `chargeminder-databricks-s3-file-events-access.json`:

```json
{
  "Action": [
    "sns:CreateTopic",
    "sns:TagResource",
    "sns:Publish",
    "sns:Subscribe",
    "sqs:CreateQueue",
    "sqs:TagQueue",
    "sqs:ReceiveMessage",
    "sqs:SendMessage",
    "sqs:DeleteMessage"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:sns:*:*:databricks-auto-ingest-*",  // ✅ For useManagedFileEvents
    "arn:aws:sqs:*:*:databricks-auto-ingest-*"   // ✅ For useManagedFileEvents
  ]
}
```

The `databricks-auto-ingest-*` prefix is what `useManagedFileEvents` uses! ✅

---

## 🎯 **Which Should You Use?**

### **Use useManagedFileEvents (Recommended):**

```python
.option("cloudFiles.useManagedFileEvents", "true")
```

**When:**
- ✅ Starting a new project
- ✅ Want simplicity and less management
- ✅ Don't need custom SNS/SQS configuration
- ✅ Want automatic cleanup

**This is Databricks' recommended approach!**

---

### **Use useNotifications (Legacy):**

```python
.option("cloudFiles.useNotifications", "true")
.option("cloudFiles.queueUrl", "your-queue-url")
```

**When:**
- ⚠️ Migrating existing infrastructure
- ⚠️ Need custom SNS/SQS setup
- ⚠️ Have specific compliance requirements for resource naming
- ⚠️ Already have existing queues you want to reuse

**Not recommended for new projects.**

---

## ⚠️ **CRITICAL: Both Still Require Storage Credential!**

Whether you use `useNotifications` or `useManagedFileEvents`, **both require a Storage Credential** in Unity Catalog.

```python
# Either of these:
.option("cloudFiles.useNotifications", "true")       # ❌ Fails without Storage Credential
.option("cloudFiles.useManagedFileEvents", "true")   # ❌ Fails without Storage Credential

# Only this works without Storage Credential:
.option("cloudFiles.useNotifications", "false")      # ✅ Works with instance profile only
```

---

## 🔄 **Migration Path**

If you have existing code with `useNotifications`:

### **Before (Legacy):**
```python
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "true")  #  OLD way
  .option("cloudFiles.queueUrl", "auto")
  .load("s3://chargeminder-2/data/"))
```

### **After (Modern):**
```python
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useManagedFileEvents", "true")  # Just change this line
  .load("s3://chargeminder-2/data/"))
```

**Cleanup old resources:**
```bash
# List and delete old queues
aws sqs list-queues --queue-name-prefix databricks
aws sqs delete-queue --queue-url <old-queue-url>

# List and delete old topics
aws sns list-topics
aws sns delete-topic --topic-arn <old-topic-arn>
```

---

## 📝 **For Your Situation**

Given your current setup and the authentication error, here's what you should know:

### **Current Problem:**
```
❌ No Storage Credential → Both useManagedFileEvents AND useNotifications fail
```

### **Solutions:**

#### **Option 1: Use Directory Listing (Works NOW)**
```python
.option("cloudFiles.useNotifications", "false")  # ✅ No Storage Credential needed
```

#### **Option 2: Get Storage Credential, Use Modern Approach (Best Long-Term)**
```python
# After admin creates Storage Credential:
.option("cloudFiles.useManagedFileEvents", "true")  # ✅ Recommended modern approach
```

#### **Option 3: Get Storage Credential, Use Legacy (Not Recommended)**
```python
# After admin creates Storage Credential:
.option("cloudFiles.useNotifications", "true")
.option("cloudFiles.queueUrl", "auto")
```

---

## 🎯 **Recommendation for Your ChargeMinder Project**

1. **Immediate (Today):**
   ```python
   .option("cloudFiles.useNotifications", "false")  # Works without Storage Credential
   ```

2. **Long-term (After Storage Credential Created):**
   ```python
   .option("cloudFiles.useManagedFileEvents", "true")  # Modern, recommended approach
   ```

   Skip `useNotifications` - go straight to the modern approach!

---

## 📚 **Summary**

```
cloudFiles.useNotifications = true:
- Legacy approach
- More manual control
- Manual cleanup needed
- Still requires Storage Credential

cloudFiles.useManagedFileEvents = true:
- Modern approach (RECOMMENDED)
- Fully automated
- Automatic cleanup
- Still requires Storage Credential
- This is what Databricks recommends

cloudFiles.useNotifications = false:
- Directory listing
- No Storage Credential needed
- Works with instance profile only
- Slower, but simple
```

---

**Bottom line:** Once your admin creates the Storage Credential, use **`useManagedFileEvents = true`** - it's the modern, recommended approach that Databricks prefers!



Yes – that policy is *exactly* why you’re getting the `SNS:CreateTopic` error.

The key mismatch is here 👇

Your **policy** allows `sns:CreateTopic` only on:

```json
"Resource": [
  "arn:aws:sns:*:*:databricks-auto-ingest-*",
  "arn:aws:sqs:*:*:databricks-auto-ingest-*"
]
```

But the **actual topic** Databricks is trying to create (from the error) is:

```text
arn:aws:sns:us-east-1:447759255101:csms-topic-by-path-d3822b22...
```

The name starts with `csms-topic-by-path-…`, **not** `databricks-auto-ingest-…`, so your `sns:CreateTopic` permission does **not** apply → 403 on `SNS:CreateTopic`.

That “databricks-auto-ingest-*” pattern is from **older / different Auto Loader examples**. Managed file events use the `csms-*` naming convention.

---

### What to change

You can fix it by changing the **Resource** on the SNS/SQS statement to include `csms-*` instead of (or in addition to) `databricks-auto-ingest-*`.

For example, replace this block:

```json
{
  "Action": [
    "sns:CreateTopic",
    "sns:TagResource",
    "sns:Publish",
    "sns:Subscribe",
    "sns:ListSubscriptionsByTopic",
    "sns:GetTopicAttributes",
    "sns:SetTopicAttributes",
    "sqs:CreateQueue",
    "sqs:TagQueue",
    "sqs:GetQueueUrl",
    "sqs:GetQueueAttributes",
    "sqs:SetQueueAttributes",
    "sqs:ReceiveMessage",
    "sqs:SendMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:sns:*:*:databricks-auto-ingest-*",
    "arn:aws:sqs:*:*:databricks-auto-ingest-*"
  ],
  "Sid": "ManagedFileEventsSetupStatement"
}
```

with something like:

```json
{
  "Sid": "ManagedFileEventsSetupStatement",
  "Effect": "Allow",
  "Action": [
    "sns:CreateTopic",
    "sns:TagResource",
    "sns:Publish",
    "sns:Subscribe",
    "sns:ListSubscriptionsByTopic",
    "sns:GetTopicAttributes",
    "sns:SetTopicAttributes",
    "sqs:CreateQueue",
    "sqs:TagQueue",
    "sqs:GetQueueUrl",
    "sqs:GetQueueAttributes",
    "sqs:SetQueueAttributes",
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility"
  ],
  "Resource": [
    "arn:aws:sns:us-east-1:447759255101:csms-*",
    "arn:aws:sqs:us-east-1:447759255101:csms-*"
  ]
}
```

If your security team wants to be *extra* strict, they can narrow the SNS ARN to just:

```json
"arn:aws:sns:us-east-1:447759255101:csms-topic-by-path-*"
```

but `csms-*` is usually fine.

The rest of your policy looks OK for managed file events:

* `S3DataAccess` → bucket + object read/write ✅
* `S3NotificationSetup` → `GetBucketNotification` / `PutBucketNotification` ✅
* `ManagedFileEventsListStatement` / `TeardownStatement` → listing topics/queues and delete/unsubscribe ✅

Right now, the **only** thing blocking managed file events is that `CreateTopic` Resource pattern doesn’t match the actual `csms-topic-by-path-*` name.

---

### After updating

Once that policy is updated on the role used by your Databricks **storage credential**:

1. Make sure the external location for `s3://chargeminder-2/raw/dynamodb/chargeminder-mlubinsky-telemetry` still has **File events enabled (Automatic)**.
2. Re-run your job with:

   ```python
   .option("cloudFiles.useManagedFileEvents", "true")
   .trigger(availableNow=True)
   ```

The `SNS:CreateTopic` error should disappear.

If you’d like, I can rewrite the *entire* final policy JSON (S3 + SNS + SQS) in one clean block with your bucket/account baked in so you can just paste it into IAM.


## 🎯 **Found It! IAM Policy Mismatch**

The error is clear - Databricks is trying to create an SNS topic but your IAM policy is **too restrictive**.

### **The Problem:**

**What Databricks is trying to create:**
```
arn:aws:sns:us-east-1:447759255101:csms-topic-by-path-d3822b227e3d150b5235f321e95e8bd9203a300dca7cf806457fdeb2c168606a
```
Topic prefix: `csms-topic-by-path-*`

**What your IAM policy allows:**
```json
"Resource": [
  "arn:aws:sns:*:*:databricks-auto-ingest-*",  // ❌ Wrong prefix!
  "arn:aws:sqs:*:*:databricks-auto-ingest-*"
]
```
Only allows: `databricks-auto-ingest-*`

---

## ✅ **Solution: Update IAM Policy**

Unity Catalog's `useManagedFileEvents` uses **different naming conventions** than the legacy Auto Loader.

### **Update File: `policies/chargeminder-databricks-s3-file-events-access.json`**

**Change from:**
```json
{
  "Action": [
    "sns:CreateTopic",
    "sns:TagResource",
    "sns:Publish",
    "sns:Subscribe",
    "sns:ListSubscriptionsByTopic",
    "sns:GetTopicAttributes",
    "sns:SetTopicAttributes",
    "sqs:CreateQueue",
    "sqs:TagQueue",
    "sqs:GetQueueUrl",
    "sqs:GetQueueAttributes",
    "sqs:SetQueueAttributes",
    "sqs:ReceiveMessage",
    "sqs:SendMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:sns:*:*:databricks-auto-ingest-*",
    "arn:aws:sqs:*:*:databricks-auto-ingest-*"
  ],
  "Sid": "ManagedFileEventsSetupStatement"
}
```

**To:**
```json
{
  "Action": [
    "sns:CreateTopic",
    "sns:TagResource",
    "sns:Publish",
    "sns:Subscribe",
    "sns:ListSubscriptionsByTopic",
    "sns:GetTopicAttributes",
    "sns:SetTopicAttributes",
    "sqs:CreateQueue",
    "sqs:TagQueue",
    "sqs:GetQueueUrl",
    "sqs:GetQueueAttributes",
    "sqs:SetQueueAttributes",
    "sqs:ReceiveMessage",
    "sqs:SendMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility"
  ],
  "Effect": "Allow",
  "Resource": [
    "arn:aws:sns:*:447759255101:databricks-auto-ingest-*",
    "arn:aws:sqs:*:447759255101:databricks-auto-ingest-*",
    "arn:aws:sns:*:447759255101:csms-topic-by-path-*",
    "arn:aws:sqs:*:447759255101:csms-queue-by-path-*"
  ],
  "Sid": "ManagedFileEventsSetupStatement"
}
```

---

## 🔧 **Complete Updated Policy**

Here's the full updated `chargeminder-databricks-s3-file-events-access.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "S3NotificationSetup",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketNotification",
        "s3:PutBucketNotification"
      ],
      "Resource": "arn:aws:s3:::chargeminder-2"
    },
    {
      "Sid": "ManagedFileEventsSetupStatement",
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:TagResource",
        "sns:Publish",
        "sns:Subscribe",
        "sns:ListSubscriptionsByTopic",
        "sns:GetTopicAttributes",
        "sns:SetTopicAttributes",
        "sqs:CreateQueue",
        "sqs:TagQueue",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes",
        "sqs:SetQueueAttributes",
        "sqs:ReceiveMessage",
        "sqs:SendMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": [
        "arn:aws:sns:*:447759255101:databricks-auto-ingest-*",
        "arn:aws:sqs:*:447759255101:databricks-auto-ingest-*",
        "arn:aws:sns:*:447759255101:csms-topic-by-path-*",
        "arn:aws:sqs:*:447759255101:csms-queue-by-path-*"
      ]
    },
    {
      "Sid": "ManagedFileEventsListStatement",
      "Effect": "Allow",
      "Action": [
        "sqs:ListQueues",
        "sqs:ListQueueTags",
        "sns:ListTopics"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ManagedFileEventsTeardownStatement",
      "Effect": "Allow",
      "Action": [
        "sns:Unsubscribe",
        "sns:DeleteTopic",
        "sqs:DeleteQueue"
      ],
      "Resource": [
        "arn:aws:sqs:*:447759255101:databricks-auto-ingest-*",
        "arn:aws:sns:*:447759255101:databricks-auto-ingest-*",
        "arn:aws:sqs:*:447759255101:csms-queue-by-path-*",
        "arn:aws:sns:*:447759255101:csms-topic-by-path-*"
      ]
    }
  ]
}
```

---

## 📝 **What Changed**

### **Added Resources for Unity Catalog Managed File Events:**

```json
"arn:aws:sns:*:447759255101:csms-topic-by-path-*",   // ✅ NEW
"arn:aws:sqs:*:447759255101:csms-queue-by-path-*"    // ✅ NEW
```

**CSMS** = Cloud Storage Metadata Service (Unity Catalog's file event service)

---

## 🚀 **Deployment Steps**

### **Step 1: Update the Policy File**
Edit `policies/chargeminder-databricks-s3-file-events-access.json` with the updated content above.

### **Step 2: Deploy the IAM Changes**
```bash
# Apply your IAM changes (using your deployment tool)
terraform apply
# or
cdktf deploy
# or whatever tool you use
```

### **Step 3: Verify Policy Update**
```bash
# Check that the policy is updated
aws iam get-role-policy \
  --role-name chargeminder-databricks-s3-access-prod \
  --policy-name chargeminder-databricks-s3-file-events-access

# Or if it's an attached policy:
aws iam get-policy-version \
  --policy-arn <policy-arn> \
  --version-id <version-id>
```

### **Step 4: Re-run Your Databricks Job**
The SNS:CreateTopic error should be resolved! ✅

---

## 🔍 **Why This Happened**

**Legacy Auto Loader** naming:
```
databricks-auto-ingest-*
```

**Unity Catalog Managed File Events** naming:
```
csms-topic-by-path-*
csms-queue-by-path-*
```

Your policy was written for the legacy naming convention, but Unity Catalog uses the new CSMS naming.

---

## 📊 **Resource Naming Patterns**

| Feature | SNS Topic Pattern | SQS Queue Pattern |
|---------|------------------|-------------------|
| **Legacy Auto Loader** | `databricks-auto-ingest-*` | `databricks-auto-ingest-*` |
| **Unity Catalog (CSMS)** | `csms-topic-by-path-*` | `csms-queue-by-path-*` |

Your policy now supports **both** for maximum compatibility.

---

## ⚠️ **Important Note on Account ID**

I changed the wildcard `*:*:` to your specific account ID `*:447759255101:` for better security:

```json
// Before (too permissive):
"arn:aws:sns:*:*:databricks-auto-ingest-*"

// After (scoped to your account):
"arn:aws:sns:*:447759255101:databricks-auto-ingest-*"
```

This ensures the policy only works in your AWS account.

---

## 🧪 **Testing After Deployment**

Once deployed, your Databricks job should:
1. ✅ Create SNS topic: `csms-topic-by-path-...`
2. ✅ Create SQS queue: `csms-queue-by-path-...`
3. ✅ Set up S3 event notifications
4. ✅ Start processing files with file arrival trigger

---

## 📋 **Checklist**

- [ ] Update `chargeminder-databricks-s3-file-events-access.json` with new resource patterns
- [ ] Deploy IAM policy changes
- [ ] Wait 1-2 minutes for IAM propagation
- [ ] Re-run Databricks job
- [ ] Verify SNS/SQS resources created in AWS Console
- [ ] Confirm file arrival trigger works

---

**Update that policy file and deploy it - your file arrival trigger should work after that!** Let me know if you hit any other errors.
 

#  Trigger Type: File Arrival

S3 (event) → SNS topic → SQS queue → Databricks Auto Loader
```
1. Lambda writes file → s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/file.json                   ↓
2. S3 Event Notification → SQS Queue                       ↓
3. Databricks File Arrival Trigger monitors SQS → Detects new file                       ↓
4. Starts your Databricks Job (streaming query)                      ↓
5. Auto Loader reads from SQS notification → Processes new file(s)                      ↓
6. Checkpoint tracks processed files → No duplicates                     ↓
7. Query completes (if using availableNow) → Cluster stops
```

### Code modification
```
# Change this line from:
.option("cloudFiles.useNotifications", "false")  # ❌ Current

# To this:
.option("cloudFiles.useNotifications", "true")   # ✅ For File Arrival
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

```
writer = (
            flat_stream.writeStream
                .option("checkpointLocation", CONFIG["checkpoint_path"])
                .foreachBatch(upsert_batch)
                .option("mergeSchema", "true")
                .trigger(processingTime="30 seconds") # continuousl watch  for new files
                .trigger(availableNow=True)    #  Good for reprocessing current dta and stop File-Arrival job DOES NOT WAIT FOR NEW FILES
        )
```

If trigger is not speccified to writeStream default is   
.trigger(processingTime="100ms")  
which is 100 times per second






## IAM Requirements: GROK

### 1. Give Databricks permission to create SNS/SQS for you
```
aws iam create-policy --policy-name DatabricksAutoLoaderNotifications \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["sns:CreateTopic","sns:Subscribe"],"Resource":"*"},
      {"Effect":"Allow","Action":["sqs:*"],"Resource":"*"}
    ]
  }'
```
### Attach the policy to the role
that your Databricks workspace uses for S3 access  
Databricks will now auto-provision an SNS topic + SQS queue 
the first time you start the stream with useNotifications=true.


## 🔐 AWS IAM Permissions (Claude)

### IAM Policy for Databricks

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SQSAccessForAutoLoader",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:*:*:databricks-auto-ingest-*"
    },
    {
      "Sid": "SQSListQueues",
      "Effect": "Allow",
      "Action": "sqs:ListQueues",
      "Resource": "*"
    }
  ]
}
```

### S3 Event Notification to SQS

```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksAutoLoaderNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```

### SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/databricks-instance-role"
      },
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder"
    }
  ]
}
```

## 🎯 Two Modes of Operation

### Mode 1: Continuous Streaming (Your Current Code)
```python
if CONFIG["trigger_mode"] == "availableNow":
    writer = writer.trigger(availableNow=True)  # ✅ Process files then stop
else:
    writer = writer.trigger(processingTime=CONFIG["processing_time"])  # Continuous
```

**For File Arrival Trigger, use:**
```python
CONFIG = {
    "trigger_mode": "availableNow",  # ✅ Recommended for cost efficiency
    # When file arrives → job starts → processes all files → stops
}
```

### Mode 2: Always-On Streaming
```python
CONFIG = {
    "trigger_mode": "processingTime",
    "processing_time": "1 minute",
    # Cluster stays running, checks every minute
}
```

## 📊 Comparison: Batch vs Streaming with File Arrival

| Approach | Trigger | Processing | Checkpoints | Duplicates | Cost |
|----------|---------|------------|-------------|------------|------|
| **Batch (read + merge)** | Manual/Orchestrated | Each file separately | No | Possible | Lower if infrequent |
| **Streaming + File Arrival** ✅ | Automatic on file | Incremental with checkpoints | Yes | Prevented | Optimal with availableNow |
| **Continuous Streaming** | Always running | Continuous micro-batches | Yes | Prevented | Higher (always on) |

## ✅ Your Code is Already Correct!

The only actual modifications needed:

### 1. Change One Option (Critical)
```python
.option("cloudFiles.useNotifications", "true")  # Changed from "false"
```

### 2. Optionally Add Queue Name (For Multiple Jobs)
```python
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")  # Optional but recommended
```

### 3. Recommended: Use availableNow Trigger
```python
CONFIG = {
    "trigger_mode": "availableNow",  # Process files and stop (cost-efficient)
    # ... rest of config unchanged
}
```

## 🚀 Setup Steps

### 1. Create SQS Queue
```bash
aws sqs create-queue \
  --queue-name databricks-auto-ingest-chargeminder \
  --attributes MessageRetentionPeriod=86400
```

### 2. Configure S3 Event Notifications
```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://s3-notification.json
```

### 3. Update Your Code
```python
# In read_stream() function:
.option("cloudFiles.useNotifications", "true")
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

### 4. Create Databricks Job
- **No File Arrival Trigger needed in Databricks UI!**
- Just create a regular scheduled job or run it manually first
- Auto Loader will automatically poll the SQS queue
- When files arrive → Auto Loader processes them automatically

## 🎓 Key Takeaways

1. ✅ **File Arrival = Streaming, not batch**
2. ✅ **Auto Loader with useNotifications=true handles everything**
3. ✅ **checkpointLocation is required**
4. ✅ **schemaLocation is required**
5. ✅ **Your original code is correct**, just change one option
6. ✅ **availableNow trigger is recommended** for cost efficiency

 
## Another opinion on IAM permisiions for File arrive Trigger


🔐 AWS IAM Permissions Required
Option A: Using S3 Event Notifications + SQS (Recommended)
This is the standard approach for File Arrival triggers.

1. IAM Policy for Databricks Instance Profile/Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "S3WriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2/archived/*",
        "arn:aws:s3:::chargeminder-2/quarantine/*"
      ]
    },
    {
      "Sid": "SQSAccess",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue"
    }
  ]
}
```
2. S3 Bucket Notification Configuration
   
```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksFileArrivalNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```
3. SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    }
  ]
}
```

## Option B: Using S3 Event Notifications + SNS
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SNSAccess",
      "Effect": "Allow",
      "Action": [
        "sns:Subscribe",
        "sns:Unsubscribe",
        "sns:GetTopicAttributes"
      ],
      "Resource": "arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-topic"
    }
  ]
}
```

📋 Setup Steps for File Arrival Trigger
### Option B: Step 1: Create SQS Queue

```bash
aws sqs create-queue \
  --queue-name databricks-file-arrival-queue \
  --attributes '{
    "MessageRetentionPeriod": "86400",
    "VisibilityTimeout": "300"
  }'

```

### Option B: Step 2: Configure S3 Event Notifications

```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://notification-config.json
```

###   Option B: Step 3: Create Databricks Job with File Arrival Trigger

In Databricks UI:
```
1. **Create Job**
2. **Add Task:**
   - Task name: `process_telemetry`
   - Type: `Python script` or `Notebook`
   - Source: Your modified script
   - Cluster: Select appropriate cluster

3. **Configure Trigger:**
   - Click **Add trigger**
   - Select **File arrival**
   - Configure:


File notification service: SQS (or SNS)
Queue/Topic URL:
https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
#### Advanced Options:
```
Wait for all tasks: ✓
Max concurrent runs: 1 (or higher for parallel processing)
Timeout: 60 minutes
```


###  Test the Setup - Upload a test file to S3
 
```bash
aws s3 cp test-file.json s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/
```
### Check SQS queue for message
```
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
### Monitor Databricks job runs
  The job should trigger automatically within a few seconds





#### Limitations
| Aspect | Details |
|--------|---------|
| **Polling Frequency** | Every ~1 minute (affected by storage perf; faster with "file events" enabled on Unity Catalog external locations). |
| **File Detection** | Triggers on *any* new/updated file in the path (no native filtering). Multiple files in one minute → single trigger. |
| **Path Scope** | Root or subpath only; no regex/wildcards in UI. |
| **Max Triggers** | Up to 1,000 per workspace (with file events enabled). |
| **Cost** | Free (beyond S3 listing costs); no extra DBUs for polling. |

If files arrive irregularly (e.g., Lambda dumps), it may delay ~1 minute—use **file events** (enable on external locations) for <10s latency.

#  How to Filter Input Files Effectively
Since the trigger fires on *any* file, implement filtering **in your PySpark job code** (e.g., using Auto Loader options).  
This is the recommended pattern—no UI changes needed.

 ## 1. **Filter in Auto Loader (cloudFiles Options)**
   Use `.option("cloudFiles.includeExistingFiles", "false")` + pattern matching to ignore non-target files.

   ```python
   # In your read_stream() function
   return (
       spark.readStream
           .format("cloudFiles")
           .option("cloudFiles.format", "json")
           .option("cloudFiles.schemaLocation", CONFIG["schema_path"])
           .option("cloudFiles.useNotifications", "true")  # For low-latency events
           .option("cloudFiles.maxFilesPerTrigger", "1000")
           # ----- FILE PATTERN FILTERING -----
           .option("cloudFiles.fileNamePattern", ".*\\.jsonl$")  # <--------    Only *.jsonl files
           # Or more complex: .option("cloudFiles.filterFunction", "lambda path: 'telemetry' in path")
           .option("cloudFiles.schemaEvolutionMode", "rescue")
           .option("rescuedDataColumn", "_rescued_data")
           .schema(raw_schema)
           .load(SOURCE_PATH)
           .withColumn("source_file", F.col("_metadata.file_path"))
   )
   ```

   - **Patterns Supported**: Regex (e.g., `.*telemetry-.*\\.jsonl$`) or custom functions.
   - **Behavior**: Auto Loader scans and filters *before* processing—ignores mismatches without triggering MERGE.

## 2. **Filter in Your Batch Function (upsert_batch)**
   If patterns vary, filter post-read:

   ```python
   # In upsert_batch(micro_df, batch_id)
   # Filter to only process *.jsonl
   filtered_df = micro_df.filter(F.regexp_extract(F.col("source_file"), r"([^/]+)$", 1).like("%jsonl"))
   
   if filtered_df.count() == 0:
       print(f"No matching files in batch {batch_id} — skipping")
       return
   
   # Then validate/dedup/MERGE on filtered_df
   valid_df, invalid_df, _ = validate_batch(filtered_df)
   # ... rest of MERGE
   ```

 ## 3. **Use Subpaths for "Patterns"**
   - Structure your S3 like: `s3://bucket/raw/telemetry/jsonl/` (only JSONL here).
   - Trigger monitors the subpath—no code changes.

 ## 4. **Advanced: Custom SNS Filtering (If Using Events)**
   - In AWS SNS: Add a **filter policy** on S3 events (e.g., `{"object.key[0]": [{"prefix": "telemetry-"}]}`).
   - This prevents the trigger from firing on non-matches.

 ## Testing & Best Practices
1. **Test Setup**: Upload a non-matching file (e.g., `.txt`) → Trigger should fire, but your code filters it out (check logs).
2. **Monitor**: Use Job runs/logs; query `_rescued_data` for mismatches.
3. **Docs Links**:
   - [File Arrival Triggers](https://docs.databricks.com/aws/en/jobs/file-arrival-triggers.html) (confirms no pattern UI).
   - [Auto Loader Patterns](https://docs.databricks.com/en/ingestion/cloud-object-storage/auto-loader/patterns.html) (for code filtering).
4. **Community Workaround**: Users on forums (e.g., Reddit, Databricks Community) confirm UI limitation—code-based filtering is standard.



# You cannot use dbutils inside foreachBatch (or any Spark job) when running in File Arrival / Streaming mode — it is not serializable and will throw the error

 You cannot use `dbutils` inside `foreachBatch` (or any Spark job) when running in **File Arrival / Streaming mode** —  
 it is **not serializable** and will throw the exact error you saw.**  

**Fix:**  
1. **Never call `dbutils.fs.mv()` inside `upsert_batch`.**  
2. **Use pure PySpark (`spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem`) or AWS SDK (`boto3`) to move files.**  
3. **Or: Do the move *outside* the stream (e.g., in a separate scheduled job).**

---

## Why `dbutils` Fails in `foreachBatch`

| Feature | `dbutils` | Spark Job (`foreachBatch`) |
|--------|-----------|----------------------------|
| **Serializable?** | No | **Must be** |
| **Runs on** | Driver (Databricks-specific) | Driver **via Spark Connect** |
| **Pickling** | Contains live JVM objects | **Cannot be pickled** |
| **Error** | `You cannot use dbutils within a spark job or otherwise pickle it` | Exactly what you got |

> `dbutils` is a **Databricks-specific utility** that wraps the notebook/driver context.  
> Spark **cannot send it to executors** or **serialize it** for `foreachBatch`.

---

## Correct Way to Move Files in Streaming Job

### Option 1: **Pure PySpark (Hadoop FS) – Recommended**

```python
def move_file_hadoop(src_path: str, dst_path: str, spark):
    """Move file using Hadoop FileSystem (no dbutils)."""
    fs = spark._jsc.hadoopConfiguration()
    path_src = spark._jvm.org.apache.hadoop.fs.Path(src_path)
    path_dst = spark._jvm.org.apache.hadoop.fs.Path(dst_path)
    file_system = spark._jvm.org.apache.hadoop.fs.FileSystem.get(fs)
    
    if file_system.exists(path_src):
        file_system.rename(path_src, path_dst)
        print(f"Moved: {src_path} → {dst_path}")
    else:
        print(f"File not found: {src_path}")
```

Use it in `upsert_batch`:

```python
# Inside upsert_batch (after MERGE)
spark = micro_df.sparkSession
for file_path in micro_df.select("source_file").distinct().collect():
    src = file_path["source_file"]
    dst = src.replace("/raw/", "/archived/")
    move_file_hadoop(src, dst, spark)
```

---

### Option 2: **Use `boto3` (AWS SDK)**

```python
import boto3

s3 = boto3.client('s3')

def move_file_boto3(src_bucket, src_key, dst_bucket, dst_key):
    # Copy
    s3.copy_object(
        Bucket=dst_bucket,
        Key=dst_key,
        CopySource={'Bucket': src_bucket, 'Key': src_key}
    )
    # Delete original
    s3.delete_object(Bucket=src_bucket, Key=src_key)
    print(f"Moved: s3://{src_bucket}/{src_key} → s3://{dst_bucket}/{dst_key}")
```

Call it:

```python
bucket = "chargeminder-2"
for row in micro_df.select("source_file").distinct().collect():
    src_key = row["source_file"].replace(f"s3://{bucket}/", "")
    dst_key = src_key.replace("raw/", "archived/")
    move_file_boto3(bucket, src_key, bucket, dst_key)
```

**Note:** Requires IAM role with `s3:CopyObject`, `s3:DeleteObject`.

---

### Option 3: **Move Files Outside the Stream (Best Practice)**

Run a **separate scheduled job** (e.g., every 5 min) that:
1. Queries the **metrics table** or **Delta `_commit` logs** to find processed files.
2. Uses `dbutils.fs.mv()` safely (since it's not in a Spark job).

```python
# Separate job: archive_processed.py
processed_files = spark.sql("""
    SELECT DISTINCT source_file 
    FROM telemetry_metrics 
    WHERE status = 'SUCCESS' AND run_timestamp > date_sub(current_date(), 1)
""")

for row in processed_files.collect():
    src = row.source_file
    dst = src.replace("/raw/", "/archived/")
    dbutils.fs.mv(src, dst)
```

**Pros:**  
- `dbutils` is safe  
- No serialization issues  
- Cleaner separation

---

## Updated `archive_processed_files` (Safe for Streaming)

```python
def archive_processed_files(micro_df: DataFrame, spark):
    """Move processed files using Hadoop FS (no dbutils)."""
    bucket = CONFIG["s3_bucket"]
    archive_prefix = CONFIG["archive_prefix"]

    files = [row["source_file"] for row in micro_df.select("source_file").distinct().collect()]
    fs = spark._jsc.hadoopConfiguration()
    hdfs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(fs)

    for src_path in files:
        if not src_path.startswith("s3://"):
            continue
        src_key = src_path.replace(f"s3://{bucket}/", "")
        dst_key = src_key.replace(CONFIG["s3_prefix"].rstrip("/"), archive_prefix.rstrip("/"))
        dst_path = f"s3://{bucket}/{dst_key}"

        src = spark._jvm.org.apache.hadoop.fs.Path(src_path)
        dst = spark._jvm.org.apache.hadoop.fs.Path(dst_path)
        if hdfs.exists(src):
            hdfs.rename(src, dst)
            print(f"Archived: {src_path} → {dst_path}")
```

Call from `upsert_batch`:

```python
archive_processed_files(micro_df, spark)
```

---

## Final `upsert_batch` Snippet (No `dbutils`)

```python
def upsert_batch(micro_df: DataFrame, batch_id: int):
    spark = micro_df.sparkSession  # Fresh session

    # ... validation, MERGE ...

    # Archive using Hadoop FS
    archive_processed_files(micro_df, spark)
```

---

## Summary

| Method | Can use in `foreachBatch`? | Needs IAM? | Recommended? |
|-------|----------------------------|-----------|--------------|
| `dbutils.fs.mv()` | No | No | No |
| Hadoop FS (`FileSystem`) | Yes | No | Yes |
| `boto3` | Yes | Yes (`CopyObject`, `DeleteObject`) | Yes |
| Separate job | Yes (outside stream) | Yes | Yes (cleanest) |

---

## Summary

> **No, you cannot use `dbutils` to move files inside `foreachBatch` in File Arrival mode.**  
> **Use Hadoop FS (`spark._jvm.org.apache.hadoop.fs.FileSystem`) or `boto3` instead.**  
> **Or move files in a separate scheduled job using `dbutils` safely.**

# How to avoid  providing  S3 input folder in 2 places: Task File Arrival trigger and Python task code


Problem statement:  The S3 location with input files should be hardcoded in 2 places :

1) Databricks task trigger on file arrival
2) PySpark code which is invoked by this trigger
 

Below is a **complete, production-ready pattern** that lets you **declare the S3 location only once** and have it flow automatically into:

1. **Databricks file-arrival trigger** (the *Job* that wakes up when a new file lands)  
2. **Your PySpark script** (the code that actually reads the files)

---

## 1. Declare the location **once** – in a **Databricks Job parameter**

| UI | CLI | API |
|----|-----|-----|
| **Jobs → Edit → Parameters** | `databricks jobs configure --job-id <id> --json '{ "parameters": { "s3_source": "s3://my-bucket/raw/telemetry" } }'` | `POST /api/2.1/jobs/update` with `settings.parameters` |

> **Only one place to change** when the bucket/prefix moves.

---

## 2. Trigger the job **on file arrival** using **S3 Event → SNS → Databricks Job**

### Step-by-step (one-time)

| Step | What you do |
|------|-------------|
| **a.** Create an **SNS topic** (Databricks can do it for you – see below) |
| **b.** Configure **S3 bucket** → **Event Notification** → **SNS topic** on `*.jsonl` (or `*.gz`) |
| **c.** Give Databricks permission to **subscribe** to that topic and **run the job** |

```bash
# 1. Create SNS policy (run once)
aws sns create-topic --name databricks-file-arrival

# 2. S3 bucket event (via console or CLI)
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:123456789012:databricks-file-arrival",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": { "Key": { "FilterRules": [{ "Name": "suffix", "Value": ".jsonl" }]}}
    }]
  }'
```

> **Databricks will auto-subscribe** the first time you run the job with `cloudFiles.useNotifications=true`.

---

## 3. PySpark script – **read the parameter** (no hard-coded path)

```python
# -------------------------------------------------
#  databricks_file_arrival_job.py
# -------------------------------------------------
import sys
from pyspark.sql import functions as F

# ---------- 1. Get the S3 path from job parameter ----------
# Databricks injects parameters into sys.argv when you use "Parameters" in the UI
if len(sys.argv) < 2:
    raise ValueError("Missing required parameter: s3_source")
S3_SOURCE = sys.argv[1]                     # <-- ONLY ONE PLACE

# Optional: fallback for local testing
# S3_SOURCE = S3_SOURCE or "s3://my-bucket/raw/telemetry"

print(f"Job started for path: {S3_SOURCE}")

# ---------- 2. Auto Loader (file-notification mode) ----------
df = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{S3_SOURCE}/_schema")
        .option("cloudFiles.useNotifications", "true")   # <-- reacts to SNS
        .option("cloudFiles.maxFilesPerTrigger", "500")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(raw_schema)
        .load(S3_SOURCE)
        .withColumn("source_file", F.col("_metadata.file_path"))
)

# ---------- 3. Rest of your pipeline (transform → MERGE) ----------
# ... (same as before) ...

# ---------- 4. Start the stream ----------
query = (
    df.writeStream
      .option("checkpointLocation", f"{S3_SOURCE}/_checkpoint")
      .trigger(processingTime="30 seconds")
      .foreachBatch(upsert_batch)
      .start()
)

query.awaitTermination()
```

---

## 4. Databricks **Job configuration** (UI)

| Field | Value |
|-------|-------|
| **Task type** | Python script |
| **Python file** | `dbfs:/FileStore/jobs/databricks_file_arrival_job.py` |
| **Parameters** | `{{s3_source}}`  *(you will fill this in the job definition)* |
| **Cluster** | All-Purpose (auto-terminate = 10 min) |
| **Schedule** | **None** – the job is **triggered by SNS**, not cron |

### How to set the parameter in the job definition

```json
{
  "name": "Telemetry File-Arrival Ingestion",
  "tasks": [
    {
      "task_key": "ingest",
      "python_wheel_task": { ... },
      "spark_python_task": {
        "python_file": "dbfs:/FileStore/jobs/databricks_file_arrival_job.py",
        "parameters": ["s3://my-bucket/raw/telemetry"]
      }
    }
  ],
  "triggers": {
    "file_arrival": {
      "file_patterns": ["*.jsonl"],
      "folder": "s3://my-bucket/raw/telemetry"
    }
  }
}
```

> **Databricks 13.3+ supports native `file_arrival` trigger** – you **don’t even need SNS** if you enable it in the UI.

---

## 5. Alternative: **Native Databricks File-Arrival Trigger** (no AWS SNS)

Databricks now offers **built-in file-arrival triggers** (DBR 13.3+):

1. **Jobs → Create Job → Trigger type → File arrival**  
2. **Folder**: `s3://my-bucket/raw/telemetry`  
 

The job **starts automatically** when a matching file appears.

**Your script still reads the path from `sys.argv[1]`** – **no duplication**.

---

## 6. Summary – **Zero duplication**

| Where the path lives | How it’s used |
|----------------------|---------------|
| **Job definition** (UI / JSON / CLI) | `parameters: ["s3://..."]` |
| **Python script** | `S3_SOURCE = sys.argv[1]` |
| **Auto Loader** | `.load(S3_SOURCE)` |
| **Checkpoint / Schema** | derived from `S3_SOURCE` |

> **Change the bucket/prefix?** → Edit **one line** in the job definition. Everything else updates automatically.

---

### TL;DR

1. **Put the S3 path in a Databricks Job parameter** (`sys.argv[1]`).  
2. **Use native `file_arrival` trigger** **or** **S3 → SNS → Databricks**.  
3. **Never hard-code the path in the script** – read it from the parameter. 



## How to specify S3 location for Trigger and PySpark code in single place only?

Below is a **complete, production-ready pattern** that lets you **declare the S3 location only once** and have it flow automatically into:

1. **Databricks file-arrival trigger** (the *Job* that wakes up when a new file lands)  
2. **Your PySpark script** (the code that actually reads the files)

---




> **Databricks 13.3+ supports native `file_arrival` trigger** – you **don’t even need SNS** if you enable it in the UI.

---

## 5. Alternative: **Native Databricks File-Arrival Trigger** (no AWS SNS)

Databricks now offers **built-in file-arrival triggers** (DBR 13.3+):

1. **Jobs → Create Job → Trigger type → File arrival**  
2. **Folder**: `s3://my-bucket/raw/telemetry`  


The job **starts automatically** when a matching file appears.

**Your script still reads the path from `sys.argv[1]`** – **no duplication**.

---

## 6. Summary – **Zero duplication**

| Where the path lives | How it’s used |
|----------------------|---------------|
| **Job definition** (UI / JSON / CLI) | `parameters: ["s3://..."]` |
| **Python script** | `S3_SOURCE = sys.argv[1]` |
| **Auto Loader** | `.load(S3_SOURCE)` |
| **Checkpoint / Schema** | derived from `S3_SOURCE` |

> **Change the bucket/prefix?** → Edit **one line** in the job definition. Everything else updates automatically.

---

### TL;DR

1. **Put the S3 path in a Databricks Job parameter** (`sys.argv[1]`).  
2. **Use native `file_arrival` trigger** **or** **S3 → SNS → Databricks**.  
3. **Never hard-code the path in the script** – read it from the parameter.  

You now have **one source of truth** and **zero duplication**.



## 1. Declare the location **once** – in a **Databricks Job parameter**

| UI | CLI | API |
|----|-----|-----|
| **Jobs → Edit → Parameters** | `databricks jobs configure --job-id <id> --json '{ "parameters": { "s3_source": "s3://my-bucket/raw/telemetry" } }'` | `POST /api/2.1/jobs/update` with `settings.parameters` |

> **Only one place to change** when the bucket/prefix moves.

---

## 2. Trigger the job **on file arrival** using **S3 Event → SNS → Databricks Job**

### Step-by-step (one-time)

| Step | What you do |
|------|-------------|
| **a.** Create an **SNS topic** (Databricks can do it for you – see below) |
| **b.** Configure **S3 bucket** → **Event Notification** → **SNS topic** on `*.jsonl` (or `*.gz`) |
| **c.** Give Databricks permission to **subscribe** to that topic and **run the job** |

```bash
# 1. Create SNS policy (run once)
aws sns create-topic --name databricks-file-arrival

# 2. S3 bucket event (via console or CLI)
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:123456789012:databricks-file-arrival",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": { "Key": { "FilterRules": [{ "Name": "suffix", "Value": ".jsonl" }]}}
    }]
  }'
```

> **Databricks will auto-subscribe** the first time you run the job with `cloudFiles.useNotifications=true`.

---



## 3. PySpark script – **read the parameter** (no hard-coded path)

```python
# -------------------------------------------------
#  databricks_file_arrival_job.py
# -------------------------------------------------
import sys
from pyspark.sql import functions as F

# ---------- 1. Get the S3 path from job parameter ----------
# Databricks injects parameters into sys.argv when you use "Parameters" in the UI
if len(sys.argv) < 2:
    raise ValueError("Missing required parameter: s3_source")
S3_SOURCE = sys.argv[1]                     # <-- ONLY ONE PLACE

# Optional: fallback for local testing
# S3_SOURCE = S3_SOURCE or "s3://my-bucket/raw/telemetry"

print(f"Job started for path: {S3_SOURCE}")

# ---------- 2. Auto Loader (file-notification mode) ----------
df = (
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{S3_SOURCE}/_schema")
        .option("cloudFiles.useNotifications", "true")   # <-- reacts to SNS
        .option("cloudFiles.maxFilesPerTrigger", "500")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(raw_schema)
        .load(S3_SOURCE)
        .withColumn("source_file", F.col("_metadata.file_path"))
)

# ---------- 3. Rest of your pipeline (transform → MERGE) ----------
# ... (same as before) ...

# ---------- 4. Start the stream ----------
query = (
    df.writeStream
      .option("checkpointLocation", f"{S3_SOURCE}/_checkpoint")
      .trigger(processingTime="30 seconds")
      .foreachBatch(upsert_batch)
      .start()
)

query.awaitTermination()
```

---

## 4. Databricks **Job configuration** (UI)

| Field | Value |
|-------|-------|
| **Task type** | Python script |
| **Python file** | `dbfs:/FileStore/jobs/databricks_file_arrival_job.py` |
| **Parameters** | `{{s3_source}}`  *(you will fill this in the job definition)* |
| **Cluster** | All-Purpose (auto-terminate = 10 min) |
| **Schedule** | **None** – the job is **triggered by SNS**, not cron |

### How to set the parameter in the job definition

```json
{
  "name": "Telemetry File-Arrival Ingestion",
  "tasks": [
    {
      "task_key": "ingest",
      "python_wheel_task": { ... },
      "spark_python_task": {
        "python_file": "dbfs:/FileStore/jobs/databricks_file_arrival_job.py",
        "parameters": ["s3://my-bucket/raw/telemetry"]
      }
    }
  ],
  "triggers": {
    "file_arrival": {
      "file_patterns": ["*.jsonl"],
      "folder": "s3://my-bucket/raw/telemetry"
    }
  }
}
```

## 🔍 **cloudFiles.useNotifications: True vs False**

This option controls **how Databricks Auto Loader discovers new files** in your S3 bucket.

---

## 📊 **Architecture Comparison**

### **useNotifications = true (Event-Driven)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. File arrives in S3                                      │
│     s3://chargeminder-2/data/file001.json                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. S3 sends event notification                             │
│     S3 Event → SNS Topic → SQS Queue                        │
│     (Auto Loader sets these up automatically)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Databricks polls SQS queue                              │
│     Gets instant notification: "file001.json arrived!"      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Databricks processes the file immediately               │
│     Latency: Seconds                                        │
└─────────────────────────────────────────────────────────────┘
```

**Requirements:**
- ✅ Storage Credential in Unity Catalog
- ✅ Permissions to create SNS/SQS resources
- ✅ S3 bucket permissions for notifications

---

### **useNotifications = false (Directory Listing)**

```
┌─────────────────────────────────────────────────────────────┐
│  1. File arrives in S3                                      │
│     s3://chargeminder-2/data/file001.json                   │
└─────────────────────────────────────────────────────────────┘
                     
                     (File just sits there, no notification)
                     
┌─────────────────────────────────────────────────────────────┐
│  2. Databricks periodically lists S3 directory              │
│     s3.listObjectsV2("s3://chargeminder-2/data/")          │
│     Interval: Every few seconds to minutes                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Compares file list to previous scan                     │
│     New file detected: "file001.json"                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Databricks processes the file                           │
│     Latency: Seconds to minutes (depends on polling)        │
└─────────────────────────────────────────────────────────────┘
```

**Requirements:**
- ✅ Instance Profile with S3 ListBucket permission
- ✅ No Unity Catalog Storage Credential needed
- ✅ No SNS/SQS setup required

---

## ⚡ **Performance Comparison**

| Metric | useNotifications = **true** | useNotifications = **false** |
|--------|---------------------------|------------------------------|
| **Latency** | 1-5 seconds | 10 seconds - 5 minutes |
| **How it discovers files** | Event-driven (push) | Polling (pull) |
| **S3 API calls** | Minimal (only reads) | Frequent LIST operations |
| **S3 costs** | Lower | Higher (more LIST calls) |
| **Setup complexity** | High (needs Unity Catalog) | Low (just IAM role) |
| **Scalability** | Excellent (instant notification) | Good (but polls all paths) |
| **Works with** | Unity Catalog required | Instance profile only |

---

## 💰 **Cost Implications**

### **With Notifications (true):**
```
S3 Event Notifications: Free
SNS: ~$0.50 per million notifications
SQS: ~$0.40 per million requests
S3 LIST calls: Minimal

Example: 10,000 files/day
- SNS: $0.005/day
- SQS: $0.004/day
- Total: ~$0.01/day
```

### **Without Notifications (false):**
```
S3 LIST calls: $0.005 per 1,000 requests

Example: Polling every 30 seconds
- 2,880 LIST calls/day
- Cost: ~$0.014/day

With 100 subdirectories:
- 288,000 LIST calls/day
- Cost: ~$1.44/day
```

**For high-volume or many directories:** Notifications are cheaper ✅

---

## 🎯 **When to Use Each**

### **Use `useNotifications = true` when:**
- ✅ You need **low latency** (real-time processing)
- ✅ High file volume (thousands+ per day)
- ✅ Many subdirectories to monitor
- ✅ You have Unity Catalog configured
- ✅ Cost optimization matters

**Example use cases:**
- Real-time dashboards
- Streaming analytics
- IoT data ingestion
- Transaction processing

---

### **Use `useNotifications = false` when:**
- ✅ You **don't have Unity Catalog** Storage Credential
- ✅ Low to medium file volume (< 1,000/day)
- ✅ Latency of minutes is acceptable
- ✅ Simple setup preferred
- ✅ Few directories to monitor

**Example use cases:**
- Daily batch jobs
- Hourly data loads
- Development/testing
- Quick prototypes

---

## 🔧 **Code Examples**

### **Example 1: High-Performance Real-Time (Notifications)**

```python
# Real-time vehicle telemetry processing
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "true")  # Event-driven
  .option("cloudFiles.region", "us-east-1")
  .option("cloudFiles.queueUrl", "auto")  # Auto-creates SQS queue
  .load("s3://chargeminder-2/telemetry/"))

# Process and write
(df.writeStream
  .format("delta")
  .option("checkpointLocation", "/checkpoints/telemetry")
  .table("vehicle_telemetry"))
```

**Requirements:** Storage Credential must exist

---

### **Example 2: Simple Batch Processing (Directory Listing)**

```python
# Hourly batch processing - latency OK
df = (spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.format", "json")
  .option("cloudFiles.useNotifications", "false")  # Directory listing
  .option("cloudFiles.maxFilesPerTrigger", 1000)  # Throttle processing
  .load("s3://chargeminder-2/telemetry/"))

# Process and write
(df.writeStream
  .trigger(processingTime="10 minutes")  # Batch every 10 min
  .format("delta")
  .option("checkpointLocation", "/checkpoints/telemetry")
  .table("vehicle_telemetry"))
```

**Requirements:** Only instance profile needed

---

## 🐛 **Why Your Job Failed**

### **What Happened:**

```python
# Your file arrival trigger used this:
.option("cloudFiles.useNotifications", "true")
```

**Execution flow:**
1. ✅ File arrival trigger fires
2. ❌ Auto Loader tries to set up SNS/SQS
3. ❌ **Needs Storage Credential** to authenticate with AWS
4. ❌ Storage Credential doesn't exist
5. ❌ **Error: Unable to load AWS credentials**

### **With Scheduled Trigger:**

Your scheduled trigger likely either:
- Used `useNotifications = false` (directory listing)
- Or didn't use Auto Loader at all (regular `spark.read`)

That's why it worked - it only needed the instance profile, not a Storage Credential.

---

## 🎯 **Your Decision Matrix**

For your ChargeMinder use case:

| Scenario | Recommendation |
|----------|----------------|
| **Need it working TODAY** | `useNotifications = false` |
| **Processing < 1,000 files/day** | `useNotifications = false` |
| **Can wait for admin to create Storage Credential** | `useNotifications = true` |
| **Processing > 10,000 files/day** | `useNotifications = true` (get admin help) |
| **Need sub-second latency** | `useNotifications = true` (get admin help) |
| **Cost-sensitive, high volume** | `useNotifications = true` (get admin help) |

---

## 📝 **Summary**

```
useNotifications = true:
✅ Fast (seconds)
✅ Event-driven
✅ Cost-efficient at scale
❌ Requires Storage Credential (you don't have)
❌ Complex setup

useNotifications = false:
✅ Simple setup
✅ Works with instance profile only
✅ No Unity Catalog needed
⚠️ Slower (polling)
⚠️ More expensive at high scale
```

---

**For your immediate needs:** Use `false` to unblock yourself today, then work with your admin to set up Storage Credential for `true` later if you need better performance.

Does this help clarify the difference?
