
 https://docs.databricks.com/aws/en/delta/update-schema
 https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema


There is Databricks Spark Job task triggered on File arrival 
which reads json files from S3.
JSON has deeply nested attributes.

The  dataframe need to be transformed into  into another dataframe  
which will be stored in Databcks Unity Catalog Table.


Please explain how to support the Databicks Unity Catalog Table schema evolution?
If  new attribute will appear in JSON how to automatically create add new columnd in 
Databcks Unity Catalog table?

There are 2 ways to read JSON from Spark:
1) Using explicit schema, provided by code.
2) Let Spark to infer schema

I read about  Delta Lake tables using options like .option("mergeSchema", "true") for writes, MERGE WITH SCHEMA EVOLUTION syntax for merge operations 
 or by setting spark.databricks.delta.schema.autoMerge.enabled to true.

I also read about 
cloudFiles.schemaEvolutionMode: addNewColumns or rescue

 https://docs.databricks.com/aws/en/delta/update-schema
 https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema

let say the new json file has extra attribute which did not exits before and therefore there  is no such column in Databicks Unity Catalog Table.
How to handle this case automatically?

# ChatGPT

##  Trigger File-Arrival Spark job ingests nested JSON from S3 and **automatically adds new columns** to a Unity Catalog Delta table—without manual DDL.


High-level approach (Bronze → Silver, streaming):

1. Read with Auto Loader (cloudFiles) so the **reader** evolves as files arrive.
   • Turn on schema inference + evolution.
   • Choose how to handle unexpected fields: `addNewColumns` (create columns) or `rescue` (park in `_rescued_data`). ([Databricks Documentation][1])

2. Write to a **Delta** table with evolution enabled.
   • For append: use `mergeSchema` on the writeStream.
   • For upserts (MERGE): set `spark.databricks.delta.schema.autoMerge.enabled = true`. This is required for nested/struct evolution and MERGE-based pipelines. ([Microsoft Learn][2])

3. Keep a schema registry path (`cloudFiles.schemaLocation`) so Auto Loader tracks/evolves the schema across runs. ([Medium][3])

4. (Optional) Keep/rescue unknown data in a column so you never drop it; you can promote rescued keys to real columns later. ([Databricks Documentation][1])

---

## Option A — Append-only (new columns get added automatically)

```python
from pyspark.sql import functions as F

SOURCE_PATH   = "s3://your-bucket/path/"
SCHEMA_PATH   = "s3://your-bucket/_schemas/your_stream"
CHECKPOINT    = "s3://your-bucket/_checkpoints/your_stream"
TARGET_TABLE  = "hcai_databricks_dev.yourschema.yourtable"

spark.conf.set("spark.sql.streaming.schemaInference", "true")  # safe default
# Not strictly required for append, but harmless:
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")
      .option("cloudFiles.inferColumnTypes", "true")                 # infer nested types
      .option("cloudFiles.schemaLocation", SCHEMA_PATH)              # persist schema
      .option("cloudFiles.schemaEvolutionMode", "addNewColumns")     # or "rescue"
      # Optional: keep unknown keys instead of failing/dropping them
      .option("rescuedDataColumn", "_rescued_data")
      .load(SOURCE_PATH))

# If you need to add nested fields programmatically, you can still use withField()/transform,
# but most new fields from JSON will arrive automatically with addNewColumns.

(df.writeStream
   .format("delta")
   .option("checkpointLocation", CHECKPOINT)
   .option("mergeSchema", "true")            # append-mode evolution: adds new columns
   .outputMode("append")
   .toTable(TARGET_TABLE))
```

Why this works:
• Auto Loader sees a new key in the JSON (even deep inside a struct/array-of-structs), updates the tracked schema at `schemaLocation`, and presents a DataFrame that includes the new column(s).
• `mergeSchema` on the streaming write tells Delta to **materialize** those new columns in the target table automatically. For nested additions and more complex cases, `autoMerge` helps as well. ([Databricks Documentation][1])

---

## Option B — Upsert (MERGE) with automatic schema evolution (e.g., SCD)

Use this if you dedupe, maintain keys, or do SCD logic in `foreachBatch`. The important knob is `autoMerge`.

```python
from delta.tables import DeltaTable

TARGET_TABLE  = "hcai_databricks_dev.yourschema.yourtable"
CHECKPOINT    = "s3://your-bucket/_checkpoints/your_merge_job"

spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")  # REQUIRED for MERGE evolution

def upsert_to_delta(batch_df, batch_id):
    tgt = DeltaTable.forName(spark, TARGET_TABLE)
    # Example: key = id
    (tgt.alias("t")
       .merge(batch_df.alias("s"), "t.id = s.id")
       .whenMatchedUpdateAll()
       .whenNotMatchedInsertAll()
       .execute())

(df.writeStream
   .option("checkpointLocation", CHECKPOINT)
   .foreachBatch(upsert_to_delta)
   .start())
```

With `autoMerge` on, **new columns present in `batch_df` but missing in the table are added automatically** during MERGE (including nested struct evolution). ([Microsoft Learn][2])



## Choosing between explicit schema vs. inference

• Explicit schema + `schemaHints`: best when you know most of the structure (types stay stable), but still want evolution for surprises; Auto Loader will add new columns beyond your declared schema (or rescue them, depending on mode). This reduces type flapping. ([Databricks Documentation][4])

• Inferred schema: fastest to get started; rely on `cloudFiles.inferColumnTypes` and `addNewColumns`. Keep `_rescued_data` so you never lose unexpected keys and can later promote them. ([Databricks Documentation][1])

Tip: always set and keep `cloudFiles.schemaLocation` stable for the stream; it’s the registry Auto Loader uses to track & evolve schemas across runs. ([Medium][3])

---

## Handling deeply-nested arrays/structs

• Auto Loader + `addNewColumns` can add **nested** fields when JSON evolves (e.g., a new `signals[i].body.capacity` key appears).
• To write those nested additions into the Delta table during append, keep `mergeSchema` on (and `autoMerge` on if you later MERGE). This combination is what enables nested evolution end-to-end. ([Stack Overflow][5])



### “Rescue” mode when you’re cautious

If you’re not ready to add columns automatically, use:

```python
.option("cloudFiles.schemaEvolutionMode", "rescue")
.option("rescuedDataColumn", "_rescued_data")
```

New/unknown fields will be captured in `_rescued_data` (a JSON map) without failing the stream. Later, promote a rescued key to a “real” column with `ALTER TABLE ADD COLUMNS`, then parse/backfill from `_rescued_data`. ([Databricks Documentation][1])

---

Unity Catalog/Delta settings & gotchas

• Your job’s principal needs UC privileges to **ALTER** the target table and **WRITE** to the schema—schema updates are ALTER operations and conflict with concurrent writers. Plan concurrency accordingly. ([Microsoft Learn][2])

• Prefer Delta column mapping mode “name” if you expect renames later (not required just to add columns, but helpful long-term). ([Stack Overflow][6])

---

Minimal checklist (copy/paste)

1. Reader:
   `cloudFiles.format=json`, `cloudFiles.inferColumnTypes=true`,
   `cloudFiles.schemaLocation=...`,
   `cloudFiles.schemaEvolutionMode=addNewColumns` (or `rescue`),
   optionally `rescuedDataColumn=_rescued_data`. ([Databricks Documentation][4])

2. Writer (append):
   `.option("mergeSchema","true")` on `writeStream.toTable(...)`. ([Microsoft Learn][2])

3. Writer (upsert/merge):
   `spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled","true")` and MERGE in `foreachBatch`. ([Microsoft Learn][2])

That’s it—new attributes that appear in future JSON files will flow into the DataFrame and land as **new columns** in your Unity Catalog Delta table automatically, with optional guardrails via the rescued data column.

[1]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema?utm_source=chatgpt.com "Configure schema inference and evolution in Auto Loader"
[2]: https://learn.microsoft.com/en-us/azure/databricks/delta/update-schema?utm_source=chatgpt.com "Update Delta Lake table schema - Azure Databricks"
[3]: https://medium.com/%40krthiak/intro-to-auto-loader-in-databricks-day-68-of-100-days-of-data-engineering-ai-and-azure-challenge-d4e5a0261c6b?utm_source=chatgpt.com "Intro to Auto loader in Databricks – Day 68 of 100 ..."
[4]: https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/options?utm_source=chatgpt.com "Auto Loader options | Databricks on AWS"
[5]: https://stackoverflow.com/questions/66335154/spark-delta-lake-auto-schema-evolution-for-nested-columns?utm_source=chatgpt.com "Spark, delta lake auto schema evolution for nested columns"
[6]: https://stackoverflow.com/questions/73319482/how-to-deal-with-invalid-characters-in-column-names-when-using-databricks-auto?utm_source=chatgpt.com "How to deal with invalid character(s) in column names ..."

# GROK

### Overview of Schema Evolution in Databricks Unity Catalog Tables

Databricks Unity Catalog tables are backed by Delta Lake, which natively supports schema evolution. 
This means you can automatically handle changes in incoming data schemas—like new attributes in deeply nested JSON files—without manual schema updates. 
For your Spark job triggered on file arrival in S3, the key is to use **Auto Loader** (the recommended approach for incremental file ingestion) 
combined with Delta Lake's schema merging capabilities. Auto Loader handles schema inference and evolution for JSON files,   
while Delta Lake ensures the Unity Catalog table schema adapts during writes.

Schema evolution supports:
- **Adding new columns**: Automatically appends new fields (including nested ones as structs) to the table schema.
- **Limitations**: It doesn't support changing existing column types, dropping columns, or evolving arrays/maps deeply (though top-level structs work well for nested JSON). For reordering/renaming/dropping, you'd need column mapping or manual rewrites.

There are two main paths for reading JSON (explicit schema vs. inference), but for automatic evolution with new attributes,  
**let Spark infer the schema via Auto Loader** and enable evolution modes. Using an explicit schema upfront would ignore new fields, requiring manual updates. 

### Recommended Approach: Auto Loader with Schema Evolution
```
Auto Loader (`cloudFiles` source) is ideal for your file-arrival trigger. It:
- Infers schemas from JSON files (sampling up to 50 GB or 1,000 files by default; configurable).
- Evolves the schema over time by tracking versions in a `_schemas` directory at the `cloudFiles.schemaLocation`.
- Handles deeply nested JSON by inferring structs (e.g., `{"user": {"name": "Alice", "address": {"city": "NY"}}}` becomes `user.name STRING` and `user.address STRUCT<city: STRING>`).

For new attributes (e.g., a new field `extra_field` appears in a JSON file),  
 Auto Loader detects it, updates the inferred schema, and propagates it to the Delta table.
```
#### Key Configurations
1. **Schema Evolution Mode in Auto Loader** (`cloudFiles.schemaEvolutionMode`):
   - **`addNewColumns`** (default when no schema provided): Automatically adds new columns to the inferred schema. When a new field is detected:
     - The stream temporarily fails with an `UnknownFieldException`.
     - Auto Loader updates the schema at `schemaLocation` and restarts the stream (use Lakeflow Jobs for auto-restart).
     - New columns are appended to the end of the schema (preserves case).
   - **`rescue`** (alternative): Doesn't evolve the schema; instead, captures new/mismatched fields in a special `_rescued_data` column (as JSON string with file path). Use this if you want to quarantine unknowns for later review, but it won't auto-add columns to the main schema.
   - Set via `.option("cloudFiles.schemaEvolutionMode", "addNewColumns")`.

2. **Delta Lake Merge on Write** (`mergeSchema` option):
   - Enables the table to automatically incorporate the evolved schema from Auto Loader during appends.
   - Set `.option("mergeSchema", "true")` on the write stream.
   - For Unity Catalog tables, this works seamlessly—specify the table as `catalog.schema.table_name`.

3. **Other Essentials**:
   - **Schema Location**: Required for evolution; stores schema versions (e.g., `s3://bucket/schema-path`).
   - **Checkpoint Location**: Tracks processed files (e.g., `s3://bucket/checkpoint-path`).
   - **Explicit Schema Hint**: Optional for deeply nested JSON—provide hints like `.option("cloudFiles.schemaHints", "user.dob DATE")` to refine types without blocking evolution.
   - **Global Config**: Avoid `spark.databricks.delta.schema.autoMerge.enabled` (it's for older merges); per-operation options are preferred.

#### Example Spark Code for Your Job
Assuming your job reads from `s3://bucket/input-json/` and writes to a Unity Catalog table `my_catalog.my_schema.events_table`. Use PySpark/Scala in your Databricks notebook or job.

```python
# Streaming read with Auto Loader for JSON files
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")  # Handles nested JSON
    .option("cloudFiles.schemaLocation", "s3://bucket/schema-location/")  # Stores evolved schemas
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")  # Auto-add new columns
    .load("s3://bucket/input-json/")  # Trigger on file arrival
)

# Write to Unity Catalog Delta table with schema merge
query = (df.writeStream
    .format("delta")
    .option("mergeSchema", "true")  # Evolves table schema on write
    .option("checkpointLocation", "s3://bucket/checkpoint-location/")
    .outputMode("append")
    .trigger(availableNow=True)  # Or .trigger(once=True) for batch-like
    .toTable("my_catalog.my_schema.events_table")  # Unity Catalog table
)

query.awaitTermination()
```

- **How It Handles New Attributes Automatically**:
  1. Initial files: Schema inferred (e.g., columns `id`, `name`, `nested.obj`).
  2. New JSON arrives with `extra_field`: Auto Loader samples it, detects the mismatch, updates the schema at `schemaLocation` (adds `extra_field STRING` at the end), and restarts.
  3. On write: `mergeSchema=true` appends `extra_field` to the Unity Catalog table schema. Existing rows get `NULL` in the new column.
  4. Nested new fields (e.g., `nested.new_subfield`) are added as `nested STRUCT<new_subfield: STRING>` if the parent is a struct.

- **Batch Mode Alternative** (if not streaming):
  ```python
  df = spark.read.format("json").load("s3://bucket/input-json/")
  df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable("my_catalog.my_schema.events_table")
  ```
  This infers schema per batch but lacks Auto Loader's evolution tracking—use for one-off jobs.

#### Using `rescue` Mode for Safer Handling
If you prefer not to auto-restart on changes:
```python
.option("cloudFiles.schemaEvolutionMode", "rescue")
.option("cloudFiles.rescuedDataColumn", "_extra_fields")  # Custom column for unknowns
```
- New fields go into `_extra_fields` as JSON (e.g., `{"extra_field": "value", "source_file": "s3://..."}`).
- Later, manually evolve: Read the rescued column, parse it, and write with `mergeSchema=true`.

### Comparison of Reading Approaches

| Approach | Pros for Evolution | Cons | When to Use |
|----------|---------------------|------|-------------|
| **Explicit Schema** (e.g., `spark.read.schema(mySchema).json(...)`) | Strict control, performance. | Ignores new fields (sets to NULL or drops); no auto-evolution. | Stable schemas; combine with `mergeSchema` for basic adds (but misses nested). |
| **Schema Inference** (default or Auto Loader) | Auto-detects/evolves nested fields. | Initial sampling overhead; temporary failures on changes. | Dynamic JSON like yours; enables full automation. |

### Additional Tips for Your Setup
- **File Arrival Trigger**: Use Databricks Workflows (Jobs) with a "File Arrival" sensor on S3 paths to trigger the notebook/cluster.
- **Performance**: For large/deep JSON, increase sampling (`spark.databricks.cloudFiles.schemaInference.sampleSize.numBytes=100GB`).
- **Unity Catalog Specifics**: Ensure your service principal/job has `USE CATALOG`, `USE SCHEMA`, and `CREATE/MODIFY` on the table. Evolution works identically to managed tables.
- **MERGE Operations**: If transforming/upserting (not just append), use `MERGE WITH SCHEMA EVOLUTION` SQL:
  ```sql
  MERGE WITH SCHEMA EVOLUTION INTO my_catalog.my_schema.events_table AS target
  USING source_df AS source
  ON source.id = target.id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *;
  ```
  This auto-adds new columns from `source_df` (Databricks Runtime 12.2+).
- **Testing**: Start with a small S3 path; monitor via `DESCRIBE HISTORY` or `DESCRIBE DETAIL` on the table.
- **Edge Cases**: If new fields cause type conflicts, use `overwriteSchema=true` (replaces entire schema—use cautiously). For very deep nesting, flatten with `spark.sql.functions.explode` or UDFs before writing.
 

# CLAUDE

Great question! You're dealing with a classic schema evolution challenge. Here's how to handle it effectively in Databricks:

## **Recommended Approach: Auto Loader with Schema Evolution**

For your file-arrival triggered workflow with evolving JSON schemas, **Auto Loader** is the best solution. Here's why and how:

### **1. Use Auto Loader with Schema Inference**

```python
# Read JSON files with Auto Loader
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/path/to/schema/location")
    
    # KEY OPTIONS for automatic schema evolution:
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")  # Or "rescue"
    .option("cloudFiles.inferColumnTypes", "true")  # Infer types, not just strings
    
    # Optional: schema hints for nested structures
    .option("cloudFiles.schemaHints", "metadata.timestamp timestamp, metadata.userId long")
    
    .load("s3://your-bucket/path/to/json/files/")
)
```

### **2. Write to Unity Catalog with Schema Evolution**

```python
# Write to Unity Catalog table with automatic schema merge
(df.writeStream
    .format("delta")
    .outputMode("append")  # or "update" for MERGE operations
    
    # Enable automatic schema evolution on write:
    .option("mergeSchema", "true")
    
    # For checkpointing
    .option("checkpointLocation", "/path/to/checkpoint")
    
    .trigger(availableNow=True)  # or Trigger.Once() for file arrival
    .toTable("catalog.schema.your_table")
)
```

---

## **Schema Evolution Modes Explained**

### **`cloudFiles.schemaEvolutionMode` Options:**

| Mode | Behavior | Best For |
|------|----------|----------|
| **`addNewColumns`** | New columns automatically added to schema and table | Most common use case - graceful evolution |
| **`rescue`** | New columns go into `_rescued_data` column as JSON | When you want to review new fields before promoting them |
| **`failOnNewColumns`** | Stream fails if new columns detected | Strict schema enforcement |
| **`none`** (default) | No evolution, new columns ignored | When schema is locked |

### **For Your Case:**

```python
.option("cloudFiles.schemaEvolutionMode", "addNewColumns")
```

This will:
- ✅ Automatically detect new JSON attributes
- ✅ Add them to the inferred schema
- ✅ Create new columns in the Delta table
- ✅ Populate existing rows with NULL for new columns

---

## **Complete Production-Ready Example**

```python
from pyspark.sql.functions import *

# 1. Define schema location (Auto Loader tracks schema evolution here)
schema_location = "s3://your-bucket/autoloader-schemas/your_table"
checkpoint_location = "s3://your-bucket/checkpoints/your_table"

# 2. Read with Auto Loader
raw_df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", schema_location)
    
    # Schema evolution settings
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("cloudFiles.inferColumnTypes", "true")
    
    # For deeply nested JSON, you might want to set max depth
    .option("cloudFiles.maxFilesPerTrigger", 1000)
    
    # Optional: rescue mode to capture malformed records
    .option("cloudFiles.rescuedDataColumn", "_rescued_data")
    
    .load("s3://your-bucket/input/json/")
)

# 3. Transform (flatten nested structures if needed)
transformed_df = (raw_df
    .withColumn("event_timestamp", col("metadata.timestamp"))
    .withColumn("user_id", col("user.id"))
    # ... your transformations
    .withColumn("ingestion_time", current_timestamp())
)

# 4. Write to Unity Catalog with schema merge
query = (transformed_df.writeStream
    .format("delta")
    .outputMode("append")
    
    # CRITICAL: Enable schema evolution on write
    .option("mergeSchema", "true")
    
    .option("checkpointLocation", checkpoint_location)
    .trigger(availableNow=True)  # File arrival trigger
    .toTable("catalog.schema.your_table")
)

query.awaitTermination()
```

---

## **Alternative: Using MERGE with Schema Evolution**

If you're using MERGE operations (for upserts/deduplication):

```python
def merge_with_schema_evolution(batch_df, batch_id):
    batch_df.createOrReplaceTempView("updates")
    
    spark.sql("""
        MERGE INTO catalog.schema.your_table target
        USING updates source
        ON target.id = source.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
        -- Enable schema evolution in MERGE
        WITH SCHEMA EVOLUTION
    """)

# Use foreachBatch for MERGE operations
query = (transformed_df.writeStream
    .foreachBatch(merge_with_schema_evolution)
    .option("checkpointLocation", checkpoint_location)
    .trigger(availableNow=True)
    .start()
)
```

---

## **Key Configuration Settings**

### **Cluster/Session Level (Optional):**

```python
# Auto-merge schemas globally (alternative to per-write option)
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

# Allow schema evolution in MERGE operations
spark.conf.set("spark.databricks.delta.merge.enableSchemaEvolution", "true")
```

---

## **Best Practices for Your Use Case**

1. **Use Auto Loader** - Don't use `spark.read.json()` for incremental loads
2. **Schema Location** - Always specify `cloudFiles.schemaLocation` to persist the inferred schema
3. **Monitor Schema Changes** - Check the schema evolution log:
   ```python
   schema_log = spark.read.json(f"{schema_location}/_schema_log")
   schema_log.display()
   ```
4. **Test New Columns** - Use `rescue` mode initially to see what's coming before promoting
5. **Schema Hints** - Provide hints for critical nested fields to ensure correct types
6. **Checkpoint Management** - Keep checkpoints separate from schema locations

---

## **Handling Your Scenario**

**When a new JSON attribute appears:**

1. **Auto Loader detects it** during the next file processing
2. **Schema is updated** in the schema location
3. **Column is added** to the Delta table automatically
4. **Existing rows** get NULL for the new column
5. **New rows** get the actual values

**No manual intervention needed!**

---

## **Comparison: Explicit Schema vs. Inferred Schema**

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Inferred (Auto Loader)** | ✅ Automatic evolution<br>✅ No code changes<br>✅ Flexible | ⚠️ Less control<br>⚠️ Type inference can be wrong | Evolving schemas, exploratory |
| **Explicit Schema** | ✅ Type safety<br>✅ Clear contract<br>✅ Performance | ❌ Manual updates needed<br>❌ Breaks on new fields | Stable, well-defined schemas |

**For your case with evolving JSON**, inferred schema with Auto Loader is the clear winner.



# **Rescue Mode Approach: Controlled Schema Evolution**

Rescue mode is the **safer, production-grade approach** where new JSON attributes are captured in a special `_rescued_data` column instead of automatically creating new columns. This gives you visibility and control before promoting fields to full schema.

---

## **How Rescue Mode Works**

1. **Known fields** → Regular columns
2. **Unknown fields** → Captured as JSON in `_rescued_data` column
3. **You review** → Decide which fields to promote
4. **Manual promotion** → Update schema and add columns
5. **Backfill (optional)** → Extract rescued data into new columns

---

## **1. Initial Setup with Rescue Mode**

```python
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Schema and checkpoint locations
schema_location = "s3://your-bucket/autoloader-schemas/telemetry_table"
checkpoint_location = "s3://your-bucket/checkpoints/telemetry_table"

# Read with Auto Loader in RESCUE mode
raw_df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", schema_location)
    
    # RESCUE MODE: Capture unknown fields
    .option("cloudFiles.schemaEvolutionMode", "rescue")
    .option("cloudFiles.inferColumnTypes", "true")
    
    # Name the rescue column (default is "_rescued_data")
    .option("cloudFiles.rescuedDataColumn", "_rescued_data")
    
    # Optional: Also capture parsing errors
    .option("columnNameOfCorruptRecord", "_corrupt_record")
    
    .load("s3://your-bucket/telemetry/json/")
)

# Add metadata for tracking
transformed_df = (raw_df
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("source_file", input_file_name())
)

# Write to Unity Catalog
query = (transformed_df.writeStream
    .format("delta")
    .outputMode("append")
    .option("mergeSchema", "true")  # Allow _rescued_data column to be added
    .option("checkpointLocation", checkpoint_location)
    .trigger(availableNow=True)
    .toTable("catalog.schema.telemetry_data")
)

query.awaitTermination()
```

---

## **2. Monitoring & Inspecting Rescued Data**

### **A. Check if There's Any Rescued Data**

```python
# Query to see if any records have rescued data
rescued_records = spark.sql("""
    SELECT 
        COUNT(*) as total_records,
        COUNT_IF(_rescued_data IS NOT NULL) as records_with_rescued_data,
        COUNT_IF(_rescued_data IS NOT NULL) * 100.0 / COUNT(*) as rescued_percentage
    FROM catalog.schema.telemetry_data
    WHERE ingestion_timestamp >= current_timestamp() - INTERVAL 7 DAYS
""")

rescued_records.display()
```

### **B. Explore What Fields Are Being Rescued**

```python
# Get sample of rescued data
rescued_samples = spark.sql("""
    SELECT 
        _rescued_data,
        ingestion_timestamp,
        source_file
    FROM catalog.schema.telemetry_data
    WHERE _rescued_data IS NOT NULL
    LIMIT 100
""")

rescued_samples.display()

# Parse rescued JSON to see structure
from pyspark.sql.functions import from_json, schema_of_json

# Infer schema from rescued data
rescued_schema_sample = spark.sql("""
    SELECT _rescued_data 
    FROM catalog.schema.telemetry_data 
    WHERE _rescued_data IS NOT NULL 
    LIMIT 1
""").collect()[0][0]

print("Rescued data sample:")
print(rescued_schema_sample)
```

### **C. Analyze Rescued Fields Systematically**

```python
# Extract all unique keys from rescued JSON
rescued_analysis = spark.sql("""
    SELECT 
        explode(map_keys(from_json(_rescued_data, 'map<string,string>'))) as rescued_field,
        COUNT(*) as occurrence_count,
        MIN(ingestion_timestamp) as first_seen,
        MAX(ingestion_timestamp) as last_seen
    FROM catalog.schema.telemetry_data
    WHERE _rescued_data IS NOT NULL
    GROUP BY rescued_field
    ORDER BY occurrence_count DESC
""")

rescued_analysis.display()
```

### **D. Deep Inspection of Specific Rescued Fields**

```python
# Look at specific rescued field values
spark.sql("""
    SELECT 
        from_json(_rescued_data, 'map<string,string>')['battery_health_score'] as battery_health_score,
        from_json(_rescued_data, 'map<string,string>')['charging_session_id'] as charging_session_id,
        COUNT(*) as count
    FROM catalog.schema.telemetry_data
    WHERE _rescued_data IS NOT NULL
    GROUP BY 1, 2
    ORDER BY count DESC
    LIMIT 20
""").display()
```

---

## **3. Promoting Rescued Fields to Full Columns**

Once you've reviewed and decided which fields to promote:

### **Option A: Add Schema Hints (Prospective)**

Update your Auto Loader to recognize the new fields going forward:

```python
# Updated Auto Loader with schema hints for new fields
raw_df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", schema_location)
    .option("cloudFiles.schemaEvolutionMode", "rescue")
    .option("cloudFiles.inferColumnTypes", "true")
    
    # Add schema hints for fields you want to promote
    .option("cloudFiles.schemaHints", 
            """
            battery_health_score double,
            charging_session_id string,
            battery.temperature_celsius double,
            diagnostics.error_codes array<string>
            """)
    
    .option("cloudFiles.rescuedDataColumn", "_rescued_data")
    .load("s3://your-bucket/telemetry/json/")
)
```

### **Option B: Switch to addNewColumns Mode**

If you're confident about the new fields, switch evolution mode:

```python
# Change to automatic evolution
raw_df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", schema_location)
    
    # Switch from rescue to addNewColumns
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("cloudFiles.inferColumnTypes", "true")
    
    .load("s3://your-bucket/telemetry/json/")
)
```

**Note:** You'll need to reset the checkpoint or use a new checkpoint location when changing evolution modes.

### **Option C: Manually Add Columns to Table**

```sql
-- Add specific columns you want from rescued data
ALTER TABLE catalog.schema.telemetry_data 
ADD COLUMNS (
    battery_health_score DOUBLE COMMENT 'Battery health score from rescued data',
    charging_session_id STRING COMMENT 'Charging session identifier'
);
```

---

## **4. Backfilling Rescued Data**

After promoting fields, extract historical data from `_rescued_data`:

```python
# Backfill: Extract rescued data into new columns
spark.sql("""
    UPDATE catalog.schema.telemetry_data
    SET 
        battery_health_score = CAST(from_json(_rescued_data, 'map<string,string>')['battery_health_score'] AS DOUBLE),
        charging_session_id = from_json(_rescued_data, 'map<string,string>')['charging_session_id']
    WHERE _rescued_data IS NOT NULL
        AND battery_health_score IS NULL  -- Only update if not already set
""")

# Verify backfill
spark.sql("""
    SELECT 
        COUNT(*) as total_backfilled,
        COUNT_IF(battery_health_score IS NOT NULL) as has_battery_health,
        COUNT_IF(charging_session_id IS NOT NULL) as has_charging_session
    FROM catalog.schema.telemetry_data
    WHERE _rescued_data IS NOT NULL
""").display()
```

---

## **5. Complete Production Workflow**

Here's a complete, opinionated production setup:

```python
from pyspark.sql.functions import *
from delta.tables import *

# Configuration
CATALOG = "catalog"
SCHEMA = "schema"
TABLE = "telemetry_data"
FULL_TABLE = f"{CATALOG}.{SCHEMA}.{TABLE}"

schema_location = f"s3://your-bucket/autoloader-schemas/{TABLE}"
checkpoint_location = f"s3://your-bucket/checkpoints/{TABLE}"

# ===== STEP 1: Ingest with Rescue Mode =====
def ingest_with_rescue():
    raw_df = (spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", schema_location)
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.rescuedDataColumn", "_rescued_data")
        .option("cloudFiles.maxFilesPerTrigger", 1000)
        .load("s3://your-bucket/telemetry/json/")
    )
    
    # Add metadata
    enriched_df = (raw_df
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_file", input_file_name())
        .withColumn("processing_date", current_date())
    )
    
    query = (enriched_df.writeStream
        .format("delta")
        .outputMode("append")
        .option("mergeSchema", "true")
        .option("checkpointLocation", checkpoint_location)
        .trigger(availableNow=True)
        .toTable(FULL_TABLE)
    )
    
    return query

# ===== STEP 2: Monitor Rescued Data =====
def analyze_rescued_data():
    """Run this periodically to see what new fields are appearing"""
    
    analysis = spark.sql(f"""
        WITH rescued_records AS (
            SELECT 
                _rescued_data,
                ingestion_timestamp
            FROM {FULL_TABLE}
            WHERE _rescued_data IS NOT NULL
                AND ingestion_timestamp >= current_timestamp() - INTERVAL 24 HOURS
        ),
        parsed_keys AS (
            SELECT 
                explode(map_keys(from_json(_rescued_data, 'map<string,string>'))) as field_name,
                from_json(_rescued_data, 'map<string,string>')[explode(map_keys(from_json(_rescued_data, 'map<string,string>')))] as field_value,
                ingestion_timestamp
            FROM rescued_records
        )
        SELECT 
            field_name,
            COUNT(*) as occurrence_count,
            COUNT(DISTINCT field_value) as unique_values,
            MIN(field_value) as sample_value,
            MIN(ingestion_timestamp) as first_seen,
            MAX(ingestion_timestamp) as last_seen
        FROM parsed_keys
        GROUP BY field_name
        ORDER BY occurrence_count DESC
    """)
    
    return analysis

# ===== STEP 3: Promote Fields =====
def promote_rescued_fields(field_definitions):
    """
    Promote rescued fields to full columns
    
    Args:
        field_definitions: dict like {'battery_health_score': 'DOUBLE', 'charging_session_id': 'STRING'}
    """
    
    # Add columns to table
    for field_name, field_type in field_definitions.items():
        spark.sql(f"""
            ALTER TABLE {FULL_TABLE}
            ADD COLUMNS ({field_name} {field_type})
        """)
        print(f"✓ Added column: {field_name} ({field_type})")
    
    # Backfill from rescued data
    set_clause = ", ".join([
        f"{field} = CAST(from_json(_rescued_data, 'map<string,string>')['{field}'] AS {dtype})"
        for field, dtype in field_definitions.items()
    ])
    
    spark.sql(f"""
        UPDATE {FULL_TABLE}
        SET {set_clause}
        WHERE _rescued_data IS NOT NULL
    """)
    print(f"✓ Backfilled {len(field_definitions)} fields from rescued data")

# ===== STEP 4: Clean Up Rescued Data (Optional) =====
def clean_rescued_data_for_promoted_fields(promoted_fields):
    """
    Remove promoted fields from _rescued_data column to reduce storage
    """
    
    spark.sql(f"""
        UPDATE {FULL_TABLE}
        SET _rescued_data = CASE
            WHEN size(map_keys(from_json(_rescued_data, 'map<string,string>'))) = {len(promoted_fields)}
            THEN NULL  -- All fields promoted, clear rescued data
            ELSE _rescued_data  -- Keep remaining unpromoted fields
        END
        WHERE _rescued_data IS NOT NULL
    """)
    print("✓ Cleaned up rescued data for promoted fields")
```

### **Using the Workflow:**

```python
# Day 1: Start ingestion with rescue mode
query = ingest_with_rescue()
query.awaitTermination()

# Day 2: Check what's being rescued
rescued_analysis = analyze_rescued_data()
rescued_analysis.display()

# Output might show:
# field_name              | occurrence_count | unique_values | sample_value | first_seen          | last_seen
# battery_health_score    | 15000           | 450          | "87.5"       | 2025-11-10 08:00:00 | 2025-11-11 10:00:00
# charging_session_id     | 15000           | 8900         | "CS-2024..." | 2025-11-10 08:00:00 | 2025-11-11 10:00:00
# experimental_metric     | 120             | 45           | "0.234"      | 2025-11-11 09:00:00 | 2025-11-11 10:00:00

# Day 3: Promote fields you want to keep
promote_rescued_fields({
    'battery_health_score': 'DOUBLE',
    'charging_session_id': 'STRING'
})

# Day 4: Clean up (optional)
clean_rescued_data_for_promoted_fields(['battery_health_score', 'charging_session_id'])

# Continue ingestion - new data will now populate the promoted columns
# while "experimental_metric" stays in _rescued_data until you decide
```

---

## **6. Rescue Mode vs. addNewColumns Comparison**

| Aspect | Rescue Mode | addNewColumns |
|--------|-------------|---------------|
| **New fields** | Go to `_rescued_data` | Auto-create columns |
| **Visibility** | ✅ Full visibility | ⚠️ Silent addition |
| **Control** | ✅ Manual promotion | ❌ Automatic |
| **Storage** | ⚠️ JSON overhead | ✅ Optimized columnar |
| **Querying** | ⚠️ Requires parsing | ✅ Direct access |
| **Testing** | ✅ Safe testing | ⚠️ Immediate impact |
| **Backfilling** | ⚠️ Manual process | ✅ Automatic |
| **Best for** | Production, governance | Development, flexibility |

---

## **7. Best Practices for Rescue Mode**

### **✅ DO:**

1. **Set up monitoring dashboards**
   ```sql
   -- Daily rescued data report
   CREATE OR REPLACE VIEW rescued_data_summary AS
   SELECT 
       processing_date,
       COUNT(*) as total_records,
       COUNT_IF(_rescued_data IS NOT NULL) as rescued_count,
       COUNT_IF(_rescued_data IS NOT NULL) * 100.0 / COUNT(*) as rescued_pct
   FROM catalog.schema.telemetry_data
   GROUP BY processing_date
   ORDER BY processing_date DESC;
   ```

2. **Schedule regular analysis**
   ```python
   # Run weekly via Databricks job
   analysis = analyze_rescued_data()
   analysis.write.mode("overwrite").saveAsTable("catalog.schema.rescued_data_analysis")
   ```

3. **Document promotion decisions**
   ```python
   # Keep a log of schema changes
   schema_changes = spark.createDataFrame([
       ("2025-11-11", "battery_health_score", "DOUBLE", "Promoted from rescued", "user@company.com")
   ], ["change_date", "field_name", "field_type", "reason", "changed_by"])
   
   schema_changes.write.mode("append").saveAsTable("catalog.schema.schema_change_log")
   ```

### **❌ DON'T:**

1. Don't let rescued data accumulate indefinitely without review
2. Don't promote fields without understanding their semantics
3. Don't forget to backfill after promotion
4. Don't ignore the storage cost of JSON in `_rescued_data`

---

## **8. Hybrid Approach: Rescue + Auto-Promotion**

For the best of both worlds:

```python
# Use rescue mode initially
# After 7 days, if field appears consistently, auto-promote

def smart_promotion_pipeline():
    # Analyze rescued data
    analysis = spark.sql(f"""
        SELECT 
            field_name,
            COUNT(*) as count,
            MAX(ingestion_timestamp) as last_seen
        FROM (
            SELECT 
                explode(map_keys(from_json(_rescued_data, 'map<string,string>'))) as field_name,
                ingestion_timestamp
            FROM {FULL_TABLE}
            WHERE _rescued_data IS NOT NULL
        )
        GROUP BY field_name
        HAVING COUNT(*) > 10000  -- Significant volume
            AND MAX(ingestion_timestamp) >= current_timestamp() - INTERVAL 7 DAYS  -- Recent
    """)
    
    # Auto-promote high-volume, consistent fields
    for row in analysis.collect():
        field_name = row['field_name']
        print(f"Auto-promoting: {field_name}")
        promote_rescued_fields({field_name: 'STRING'})  # Default to STRING, refine later
```

---

## **Summary: When to Use Rescue Mode**

**Use Rescue Mode when:**
- ✅ Production environment with governance requirements
- ✅ Schema changes need review/approval
- ✅ You want to test new fields before committing
- ✅ Multiple teams contribute data with varying quality
- ✅ You need audit trail of schema evolution

**Use addNewColumns when:**
- ✅ Development/staging environment
- ✅ Trusted data sources
- ✅ Rapid iteration needed
- ✅ Schema is expected to evolve frequently

**For ChargeMinder telemetry data**, I'd recommend **starting with rescue mode** in production, then switching to a hybrid approach once you understand the evolution patterns.


## One more opinion

### Explanation of `rescuedDataColumn` Option

The `.option("rescuedDataColumn", "_rescued_data")` line in your Auto Loader (`cloudFiles`) configuration tells Databricks to **automatically rescue (save) malformed or unparsable records** during ingestion, rather than failing the entire batch. Here's a breakdown:

#### What It Does
- **Purpose**: When Auto Loader reads JSON files (or other formats) against your explicit `raw_schema`, some rows might not conform:
  - Missing required fields.
  - Type mismatches (e.g., expected `string` but got `int`).
  - Malformed JSON (e.g., syntax errors from DynamoDB Lambda exports).
  - Without this, the job would **fail** (throwing a schema validation error), halting processing.
- **How It Works**:
  - Auto Loader parses each row against `raw_schema`.
  - If a row fails, it's **not dropped**—instead, the **raw, unparsed content** (as a JSON string) is inserted into a new column named `_rescued_data`.
  - Valid rows proceed normally.
  - The `_rescued_data` column is added to your DataFrame schema (nullable `string` type).
- **Example**:
  - Input JSON row: `{"event_id": "abc", "recorded_at": 123}` (type mismatch: `recorded_at` should be `string`).
  - Output: Row has all normal columns as `null` (or defaults), but `_rescued_data` = `'{"event_id": "abc", "recorded_at": 123}'`.
- **Benefits**:
  - **Resilience**: Job continues; no full failure.
  - **Debugging**: Query `_rescued_data` to inspect/fix issues (e.g., `df.filter(F.col("_rescued_data").isNotNull()).show()`).
  - **Downstream Handling**: In `upsert_batch`, filter out rescued rows or route to quarantine.

#### When to Use/Configure
- **Default**: No rescued column (fails on errors).
- **Your Code**: Naming it `"_rescued_data"` is conventional—keep it if you plan to query it.
- **Trade-Offs**:
  | Pro | Con |
  |-----|-----|
  | Prevents job crashes | Adds a column (slight schema bloat) |
  | Easy error triage | Rescued rows may need manual cleanup |

If unused, you can drop it later: `.drop("_rescued_data")`.

### Explanation of `schemaEvolutionMode` Option (Missing in Snippet)

The `option("schemaEvolutionMode", "rescue")` is **not present** in the code snippet you shared (it uses `"addNewColumn"` in the full code from earlier responses). This option controls how Auto Loader **adapts to schema changes** over time (e.g., new fields in DynamoDB exports). Adding it is optional but recommended for evolving data like telemetry signals.

#### What It Does
- **Purpose**: Auto Loader infers/evolves the schema at `CONFIG["schema_path"]` based on new files. Without this, it fails on mismatches. With it, it handles changes gracefully.
- **Modes** (All are "permissive"—no failures):
  | Mode | Description | Best For | Impact on Data |
  |------|-------------|----------|----------------|
  | **"addNewColumn"** (Your Current) | Adds new fields as nullable columns to the schema. Existing rows get `null` for new fields. | Non-breaking adds (e.g., new signal like "battery_temp"). | Minimal data loss; appends columns. |
  | **"rescue"** (You Asked About) | Like "addNewColumn", but **any row with schema mismatches** (new/missing fields) is routed to `rescuedDataColumn`. Valid rows evolve the schema. | Strict validation + error isolation (e.g., old files with outdated JSON). | Mismatches become raw strings in rescued column; schema still evolves. |
  | **"failOnNewColumn"** (Strict) | Fails if new fields appear. | Frozen schemas (rare). | Stops processing. |
  | **"none"** (Default) | No evolution; strict match to initial schema. | Stable data only. | Fails on changes. |

- **"rescue" Specifics**:
  - Combines evolution with rescue: New columns are added, but problematic rows (e.g., missing new required field) go to `_rescued_data` as raw JSON.
  - Example: New file has `{"event_id": "abc", "new_signal": "xyz"}`. Schema adds `new_signal`; old rows get `null`; mismatched rows (e.g., bad types) → rescued.
  - **Why "rescue" over "addNewColumn"?** Better for auditing—isolates "dirty" rows without polluting the main table.

#### Why It's Missing & How to Add It
- **In Snippet**: Omitted for brevity; full code had `"addNewColumn"`.
- **Recommendation**: Use `"rescue"` if you have `rescuedDataColumn` enabled (synergistic). Add it right after `.option("cloudFiles.validateOptions", "true")`:
  ```python
  .option("cloudFiles.schemaEvolutionMode", "rescue")  # Handles changes + rescues mismatches
  ```
- **Trade-Offs**:
  | Pro | Con |
  |-----|-----|
  | Evolves schema dynamically | More rescued rows if data varies wildly |
  | Integrates with rescuedDataColumn | Slight perf hit on validation |

#### Quick Test
In a notebook:
```python
# Simulate: Add a mismatched file, run stream, query rescued rows
df.filter(F.col("_rescued_data").isNotNull()).count()  # Should show issues
```

This keeps your pipeline robust for real-world DynamoDB variability. If adding it causes issues, fall back to `"addNewColumn"`. Let me know if you need the full updated `read_stream()`!


#  Reprocessing Archived Files in Your Databricks Streaming Job

Your code's archiving logic (`archive_processed_files()`) moves successfully processed files from the source S3 prefix (e.g., `s3://chargeminder-2/raw/dynamodb/chargeminder-mlubinsky-telemetry/`) to the archive prefix (e.g., `s3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/`) using `dbutils.fs.mv()`. This is a common pattern for data lakes to prevent re-ingestion, but it makes reprocessing intentional (e.g., for errors or schema evolution).

Reprocessing is straightforward: **Manually move files back to the source path**, then **restart the stream** to let Auto Loader detect and process them again. Auto Loader's checkpointing ensures it tracks what's been ingested, but you can override with a new checkpoint or schema tweaks. Below, I'll cover scenarios (errors vs. schema changes) and step-by-step instructions.

#### Key Concepts
- **Checkpoint Safety**: Your stream uses `checkpointLocation` (e.g., `s3://chargeminder-2/_checkpoints/mlubinsky-telemetry`). It logs processed files/metadata—moving files back won't auto-reprocess unless you clear/rename the checkpoint.
- **Schema Evolution**: Auto Loader supports adding columns (`cloudFiles.schemaEvolutionMode="addNewColumn"`) without full reprocessing.
- **No Data Loss**: Archived files remain intact; MERGE in `upsert_batch` handles upserts idempotently (via `event_id` PK).

| Scenario | Trigger | Reprocessing Impact | Best Tool |
|----------|---------|---------------------|-----------|
| **Job Error** (e.g., transform fail) | Partial batch fails; some files archived, others not. | Reprocess only failed files; no schema change. | S3 Console or AWS CLI. |
| **Schema Change** (e.g., add column) | Update `raw_schema` or DDL; run stream with evolution. | Full reprocess if needed; append-only for new cols. | Databricks SQL + Auto Loader. |

#### Step-by-Step: Reprocessing Archived Files

##### 1. **Stop the Running Job/Stream**
   - In Databricks UI: Go to **Workflows** → Your Job → **Runs** → Stop the active run.
   - Or via API: `POST /api/2.0/jobs/runs/cancel` with run ID.
   - This prevents conflicts during file moves.

##### 2. **Identify Files to Reprocess**
   - **For Errors**: Check Job logs/metrics (`METRICS_TABLE`) for batch IDs/files that failed (e.g., `status="FAILED"`, `error_message`).
     ```sql
     SELECT * FROM hcai_databricks_dev.chargeminder2.telemetry_metrics 
     WHERE status = 'FAILED' ORDER BY run_timestamp DESC;
     ```
     - From logs, note archived file paths (e.g., via `source_file` in quarantined data).
   - **For Schema Changes**: Query the archive for all files (or date range).
     ```sql
     -- List archived files (use Databricks SQL or AWS CLI)
     LIST 's3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/';
     ```
   - **Tip**: If high volume, use AWS CLI: `aws s3 ls s3://chargeminder-2/archived/... --recursive | grep jsonl`.

##### 3. **Move Files Back to Source Path**
   - **Manual (Small Scale)**: Use Databricks Notebook (attach to your cluster):
     ```python
     # In a notebook cell
     from delta.utils import DeltaFiles

     # Example: Move specific files back
     source_prefix = "s3://chargeminder-2/raw/dynamodb/chargeminder-mlubinsky-telemetry/"
     archive_prefix = "s3://chargeminder-2/archived/dynamodb/chargeminder-michael-telemetry/"
     
     # List archived files (adapt for your needs)
     archived_files = dbutils.fs.ls(archive_prefix)  # Returns list of FileInfo
     for file_info in archived_files:
         if file_info.name.endswith('.jsonl'):  # Filter JSONL
             archive_path = file_info.path
             source_path = archive_path.replace(archive_prefix, source_prefix)
             dbutils.fs.mv(archive_path, source_path, recurse=True)
             print(f"Moved back: {source_path}")
     ```
     - Run this in a one-off notebook; test with `--dryrun` if available.

   - **Bulk (AWS CLI/S3 Console)**:
     - CLI: `aws s3 mv s3://chargeminder-2/archived/.../file.jsonl s3://chargeminder-2/raw/.../file.jsonl --recursive`
     - Console: Select files in S3 → Actions → Copy/Move.
     - **Caution**: Add a timestamp suffix (e.g., `_reprocess_v2.jsonl`) to avoid name conflicts.

##### 4. **Handle Schema Changes (If Applicable)**
   - **Add Columns**: Update `raw_schema` (e.g., add `StructField("new_field", StringType(), True)`) and DDL (`create_or_update_table()`).
     - Re-run the job: Auto Loader's `"addNewColumn"` mode appends without reprocessing old data.
   - **Breaking Changes** (e.g., type changes): 
     - Set `cloudFiles.schemaEvolutionMode="rescue"` to quarantine bad rows.
     - Or full reprocess: Clear checkpoint (delete contents of `checkpoint_path`) before restart—**warning: loses ingestion history**.
   - **Test**: Run a dry-run job with `maxFilesPerTrigger=1` on a subset.

##### 5. **Restart the Stream and Monitor**
   - **Restart Job**: In UI, **Run Now** or resume schedule (now "Continuously" if using notifications).
   - **Verify Reprocessing**:
     - Watch logs for "Processing Batch X" with your files.
     - Query target table: `SELECT COUNT(*) FROM {FULL_TABLE} WHERE pipeline_ingest_ts > '2025-11-09';` (post-reprocess).
     - Check metrics: New rows in `METRICS_TABLE` with updated counts.
   - **Checkpoint Reset (If Needed)**: To force re-detection:
     ```python
     # In notebook: Clear checkpoint (one-time)
     dbutils.fs.rm(CONFIG["checkpoint_path"], recurse=True)
     ```
     - Then restart—Auto Loader rescans from scratch.

##### 6. **Prevention and Best Practices**
   - **Error Handling**: In `upsert_batch`, add try-catch around archiving—only move on full success.
     ```python
     # In upsert_batch, after MERGE
     try:
         archive_processed_files(micro_df)
     except Exception as ae:
         print(f"⚠️ Archiving failed: {ae} — Files remain in source for retry")
     ```
   - **Dry Runs**: Add a config flag (`"dry_run": True`) to skip archiving/MERGE for testing schema changes.
   - **Versioned Archives**: Append timestamps to archive paths (e.g., `/archived/YYYY/MM/DD/`) for easier rollback.
   - **Alternatives to Archiving**:
     - Use Auto Loader's **file filtering** (e.g., `cloudFiles.includeExistingFiles=true` for re-runs) instead of moving.
     - Or soft-archive: Add a `processed` tag via S3 metadata, filter in Auto Loader.
   - **Monitoring**: Set Job alerts for failures; use Delta Lake's time travel (`AS OF TIMESTAMP`) to rollback bad inserts.

This process typically takes 5-15 minutes for small batches. If reprocessing large volumes (>1TB), consider partitioning by date in your source S3 structure. Let me know your error details or schema mods for tailored tweaks!
