
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

let say the new json file has extra attribute which did not exits before and therefore there  is no such column in Databcks Unity Catalog Table.
How to handle this case automatically?


##  Pattern to  use so your File-Arrival Spark job ingests nested JSON from S3 and **automatically 
adds new columns** to a Unity Catalog Delta table—without manual DDL.


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

Option A — Append-only (new columns get added automatically)

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

Option B — Upsert (MERGE) with automatic schema evolution (e.g., SCD)

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

---

Choosing between explicit schema vs. inference

• Explicit schema + `schemaHints`: best when you know most of the structure (types stay stable), but still want evolution for surprises; Auto Loader will add new columns beyond your declared schema (or rescue them, depending on mode). This reduces type flapping. ([Databricks Documentation][4])

• Inferred schema: fastest to get started; rely on `cloudFiles.inferColumnTypes` and `addNewColumns`. Keep `_rescued_data` so you never lose unexpected keys and can later promote them. ([Databricks Documentation][1])

Tip: always set and keep `cloudFiles.schemaLocation` stable for the stream; it’s the registry Auto Loader uses to track & evolve schemas across runs. ([Medium][3])

---

Handling deeply-nested arrays/structs

• Auto Loader + `addNewColumns` can add **nested** fields when JSON evolves (e.g., a new `signals[i].body.capacity` key appears).
• To write those nested additions into the Delta table during append, keep `mergeSchema` on (and `autoMerge` on if you later MERGE). This combination is what enables nested evolution end-to-end. ([Stack Overflow][5])

---

“Rescue” mode when you’re cautious

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
