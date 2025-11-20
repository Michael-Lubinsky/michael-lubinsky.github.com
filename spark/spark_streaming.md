https://towardsdatascience.com/mastering-data-streaming-in-python-a88d4b3abf8b

https://spark.apache.org/docs/latest/streaming-programming-guide.html

https://medium.com/@ashutoshkumar2048/unraveling-apache-spark-structured-streaming-ui-9915ef29562e

https://subhamkharwal.medium.com/pyspark-spark-streaming-error-and-exception-handling-cd4ac4882788

https://www.youtube.com/playlist?list=PL2IsFZBGM_IEtp2fF5xxZCS9CYBSHV2WW


# How **Auto Loader**, **read()**, and **readStream()** relate in Databricks.



**Auto Loader works only with `readStream()` (structured streaming).**
Not with plain `read()`.

You enable Auto Loader by using:

```python
spark.readStream.format("cloudFiles")
```

So:

* `read()` → batch read (no Auto Loader)
* `readStream()` → streaming read

  * If format = `"cloudFiles"` → Auto Loader is active
  * If format = anything else → normal streaming reader

---

# 🚀 **Auto Loader explained simply**

Auto Loader is a **streaming file ingestion** engine built on top of **Structured Streaming**.

It automatically:

* detects new files arriving in cloud storage (S3 / ADLS / GCS)
* infers schema (with evolution)
* tracks already-processed files
* handles retries, exactly-once semantics
* efficiently lists cloud storage paths (uses RocksDB or notification modes)

All of that is built into:

```python
spark.readStream.format("cloudFiles")
```

---

# 🧩 **Relationship to `read()`**

### ❌ Auto Loader cannot be used with `read()`

```python
spark.read.format("cloudFiles").load(...)
```

This will fail — “cloudFiles” is not supported in batch mode.

`read()` = batch DataFrame
No streaming, no checkpoints, no state, no Auto Loader.

---

# 🧩 **Relationship to `readStream()`**

### ✔ Auto Loader **is a special format** inside `readStream()`

```python
df = (
    spark.readStream
         .format("cloudFiles")       # enables Auto Loader
         .option("cloudFiles.format", "json")
         .option("cloudFiles.schemaLocation", "/mnt/schema")
         .load("/mnt/source")
)
```

This is how Auto Loader works.

---

# 🕘 **Where things fit in the Databricks ingestion architecture**

| Ingestion Type           | Uses `readStream()` | Uses Auto Loader | Schema evolution | File notifications    |
| ------------------------ | ------------------- | ---------------- | ---------------- | --------------------- |
| **Batch read**           | ❌                   | ❌                | ❌                | ❌                     |
| **Structured Streaming** | ✔                   | ❌                | Some             | ❌                     |
| **Auto Loader**          | ✔                   | ✔                | ✔ full           | ✔ cloud notifications |

---

# 🛠️ Example Comparison

### **1. Normal batch read**

```python
df = spark.read.json("/mnt/source")
```

### **2. Normal streaming read**

```python
df = spark.readStream.format("json").load("/mnt/source")
```

### **3. Auto Loader streaming read**

```python
df = (
    spark.readStream
         .format("cloudFiles")
         .option("cloudFiles.format", "json")
         .option("cloudFiles.schemaLocation", "/mnt/schema")
         .load("/mnt/source")
)
```

---

# 🔥 Key Benefits of Auto Loader (over readStream without it)

Auto Loader adds:

* **High-performance file discovery** (optimized listings or notifications)
* **Schema inference & evolution**
* **Checkpointing & exactly-once guarantees**
* **Automatic retries**
* **Ability to process millions of files efficiently**

Structured Streaming (`readStream`) **alone** does not provide these.

---

# 📌 Summary

* `read()` = batch → **Auto Loader cannot be used**
* `readStream()` = streaming →

  * If `.format("json")` → normal streaming
  * If `.format("cloudFiles")` → **Auto Loader**

---

In Databricks, **Auto Loader** is a powerful feature for efficiently and incrementally ingesting new files from cloud storage (e.g., S3, ADLS, GCS) into Delta Lake tables. It builds on Apache Spark Structured Streaming and is the recommended way to load file-based data incrementally, offering benefits like automatic schema inference/evolution, scalable file discovery (directory listing or event notifications), exactly-once guarantees via RocksDB-backed checkpoints, and better performance than vanilla file sources.

### Key Relationships Between `spark.read()`, `spark.readStream()`, and Auto Loader

| Method                  | Type          | Primary Use Case                                                                 | Relation to Auto Loader                                                                                          |
|-------------------------|---------------|----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `spark.read.format(...).load(path)` | Batch (static DataFrame) | Read **all** files in a directory at once (or a single file) in one shot. No incremental processing. | Often used to **infer or provide the schema** upfront for Auto Loader (especially for formats like Avro/Parquet that don't support easy inference). Not the core of Auto Loader itself. |
| `spark.readStream.format("cloudFiles").options(...).load(path)` | Streaming DataFrame | Incremental, fault-tolerant processing of **new files** as they arrive in a directory. | This is **how you invoke Auto Loader** in PySpark. The special source `"cloudFiles"` (with `cloudFiles.*` options) turns Structured Streaming into Auto Loader. |
| Vanilla `spark.readStream.format("json/csv/parquet/etc").load(path)` | Streaming DataFrame | Basic file-based streaming (possible but not recommended). | Works, but lacks Auto Loader's optimizations → slower file discovery, no schema evolution, harder to scale with millions of files. Databricks strongly recommends `"cloudFiles"` instead. |

**Summary of the flow**:
- Auto Loader = Structured Streaming + the `"cloudFiles"` source.
- `readStream()` is required for the incremental/"auto-loading" behavior.
- `read()` is only a helper (e.g., to grab a schema from existing files).

### PySpark Examples

#### 1. Recommended Auto Loader pattern (streaming + schema inference/evolution)

```python
from pyspark.sql.functions import current_timestamp, input_file_name

input_path     = "abfss://raw@storageaccount.dfs.core.windows.net/sales/"   # or s3://, gs://, /dbfs/...
checkpoint_path = "/tmp/auto_loader_checkpoints/sales_raw"

# Auto Loader with schema inference (works great for JSON, CSV, Avro, XML, etc.)
streaming_df = (spark
    .readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")                # or json, parquet, avro, etc.
    .option("cloudFiles.schemaLocation", checkpoint_path)   # Required for inference & evolution
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")  # Optional: auto-add new columns
    .option("header", "true")                     # CSV-specific options
    .option("delimiter", ",") 
    .load(input_path)
    .withColumn("source_file", input_file_name())
    .withColumn("ingest_time", current_timestamp())
)

# Write as a streaming Delta table (continuous or triggered mode)
(streaming_df
    .writeStream
    .format("delta")
    .option("checkpointLocation", checkpoint_path)
    .option("mergeSchema", "true")          # Allow schema evolution on the target table
    .trigger(processingTime="5 minutes")    # or .trigger(availableNow=True) for batch-like
    .table("sales_bronze")                  # or .start("/path/to/delta/table")
)
```

#### 2. When you need to provide a fixed schema (common for Parquet/Avro)

```python
# First, infer the schema from existing files using batch read()
sample_schema = spark.read.format("parquet").load(input_path).schema

# Then use it in Auto Loader streaming read
streaming_df = (spark
    .readStream
    .format("cloudFiles")
    .schema(sample_schema)                         # Provide the schema explicitly
    .option("cloudFiles.format", "parquet")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .load(input_path)
)
```

#### 3. Running Auto Loader as an incremental batch job (cost-effective, no always-on cluster)

```python
(streaming_df
    .writeStream
    .format("delta")
    .trigger(availableNow=True)        # Processes only new files then stops
    .option("checkpointLocation", checkpoint_path)
    .table("sales_bronze")
)
```

This pattern is very popular in Databricks Jobs — the job starts, processes whatever new files arrived since the last run, then terminates.

### Why choose Auto Loader (`cloudFiles`) over plain file streaming?

| Feature                          | Plain `readStream.format("csv")` | Auto Loader (`cloudFiles`) |
|----------------------------------|------------------------------------|----------------------------|
| File discovery performance        | Slow with deep/nested dirs         | Very fast (directory listing or event grid notifications) |
| Schema inference & evolution     | No                                 | Yes (automatic)           |
| Rescued data (_rescued_data column) | No                                 | Yes (bad records)          |
| Backfill of existing files        | Manual                             | Built-in options           |
| Exactly-once guarantees          | Yes (with checkpoint)              | Yes + RocksDB optimization|
| Recommended by Databricks        | No                                 | Yes (for all file ingestion) |

Use `spark.readStream.format("cloudFiles")` whenever you want Auto Loader behavior.   
Use `spark.read()` only as a helper to inspect or infer schemas when needed.   
This combination gives you the most robust, performant, and low-maintenance file ingestion pipeline in Databricks.


### Understanding Backfill in Databricks Auto Loader

**Backfill** in Auto Loader refers to the process of discovering and ingesting **historical/existing files** (files that were already present in the input directory before the stream started or files that might have been missed during normal incremental processing).

By default, when you start a new Auto Loader stream:
- It performs an **initial directory listing** to discover **all existing files** in the input path.
- Those files are added to the processing queue (backlog) and ingested incrementally in streaming batches.
- This initial load acts as an automatic one-time backfill of everything that exists at stream startup.
- After that, the stream switches to incremental mode: only **new files arriving after startup** are processed (via directory listing or file notifications).

This makes Auto Loader perfect for migrations or initial loads of massive historical datasets (billions of files) without writing custom backfill logic.

#### Built-in Options and Mechanisms for Controlling Backfill

| Scenario | Option / Mechanism | Description | Example Usage & Notes |
|----------|---------------------|-------------|-----------------------|
| **Initial backfill of all existing files when starting a brand-new stream** | No special option needed (default behavior) | On first startup, Auto Loader automatically lists the directory and queues **all** discovered files for processing. | Just start the stream — it will backfill everything once, then go incremental forever after. No duplicates thanks to checkpointing. |
| **Periodic/reconciliation backfill to catch missed files** | `cloudFiles.backfillInterval` | Triggers an **asynchronous directory listing** every N time period to find any files that were missed (e.g., due to rare notification losses in file-notification mode or race conditions). <br><br>Recommended for production when you need strict data-completeness SLAs. <br><br>Values like `"1 day"`, `"1 week"` are common. The backfill runs in the background and does **not** block normal processing. | ```python
| **Default automatic reconciliation in directory-listing mode** | Built-in (no option) | In pure directory-listing mode (or "auto" incremental listing), Auto Loader automatically triggers a full directory list after every **7 consecutive incremental lists** to guarantee eventual completeness. | You can override/replace this default with `cloudFiles.backfillInterval`. |
| **Limit backfill to files modified after a certain timestamp** (e.g., partial historical load) | `modifiedAfter` (or `cloudFiles.modifiedAfter`) | Ignores files older than the given timestamp during discovery. Useful if you only want to backfill recent history and skip very old data. | ```python<br>.option("modifiedAfter", "2024-01-01T00:00:00Z")<br>``` |
| **Limit backfill to files modified before a certain timestamp** | `modifiedBefore` (or `cloudFiles.modifiedBefore`) | Ignores files newer than the timestamp. Often combined with `modifiedAfter` for a time window backfill. | ```python<br>.option("modifiedBefore", "2025-01-01T00:00:00Z")<br>``` |
| **One-time full backfill without leaving a continuous stream running** | Use `.trigger(availableNow=True)` | Processes **all** currently existing (and any arriving during the run) files exactly once, then the query stops. Perfect for scheduled jobs that backfill historical data incrementally over time. | See example below. |

#### PySpark Examples

1. **Full initial backfill + continuous incremental ingestion** (most common production pattern)

```python
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .option("cloudFiles.backfillInterval", "1 day")   # Optional: daily reconciliation
    .load(input_path)
    .writeStream
    .format("delta")
    .option("checkpointLocation", checkpoint_path)
    .table("bronze_table")
)
```

→ First run = backfills everything. Subsequent runs = only new files + daily reconciliation.

2. **One-time backfill of all historical data** (run as a Databricks Job with `availableNow`)

```python
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "parquet")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .load(input_path)
    .writeStream
    .format("delta")
    .trigger(availableNow=True)          # Process everything once, then stop
    .option("checkpointLocation", checkpoint_path)
    .table("bronze_historical")
)
```

3. **Partial backfill – only files from the last 6 months**

```python
from datetime import datetime, timedelta

six_months_ago = (datetime.now() - timedelta(days=180)).isoformat() + "Z"

(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", checkpoint_path)
    .option("modifiedAfter", six_months_ago)   # Only backfill recent files
    .load(input_path)
    .writeStream
    .trigger(availableNow=True)
    .option("checkpointLocation", checkpoint_path)
    .table("bronze_partial_backfill")
)
```

In summary, Auto Loader’s backfill capabilities are **built-in and automatic** for the initial load**, with `cloudFiles.backfillInterval` providing the main knob for ongoing reconciliation in production. This combination gives you both easy historical migration and strong guarantees that no file is permanently missed — all without manual scripting or duplicate risk.
