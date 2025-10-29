```python
import boto3
boto3_session = boto3.Session(
    botocore_session=dbutils.credentials.getServiceCredentialsProvider("chargeminder-dynamodb-creds"),
    region_name="us-east-1"
)
dynamodb = boto3_session.resource('dynamodb')

response = dynamodb_client.list_tables()
table_names = response['TableNames']

print("DynamoDB ChargeMinder Tables:")
for table_name in table_names:
  if table_name.startswith('chargeminder')  :
    table = dynamodb.Table(table_name)
    print(f"TABLE  - {table_name}")
    print(f"Item count: {table.item_count}")
    print(f"Key schema: {table.key_schema}")
    print()

table = dynamodb.Table('chargeminder-car-telemetry')
# Replace with your table name
 

# Scan all items
response = table.scan()
items = response['Items']

print(f"Found {len(items)} items")
for i, item in enumerate(items):
    print("item number", i)
    print(item)
    print()
    print()
```


Below is a **complete, copy-and-paste-ready** notebook that

1. **Normalises the DynamoDB JSON** (so every field has a known type)  
2. **Creates a PySpark DataFrame** with an explicit schema (no inference)  
3. **Flattens / explodes** the nested `signals` and `triggers` arrays  
4. **Writes the result** to a Unity Catalog table.

```python
# --------------------------------------------------------------
# 1. Imports & helper to convert DynamoDB types → Python types
# --------------------------------------------------------------
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, from_unixtime, lit
from pyspark.sql.types import *
from decimal import Decimal
from datetime import datetime
import json

spark = SparkSession.builder.getOrCreate()


def _dynamodb_to_python(item: dict) -> dict:
    """
    Recursively walk a DynamoDB JSON dict and convert:
        Decimal → float (or int if whole number)
        list / dict → keep as-is (will become Array/Struct later)
    """
    if isinstance(item, dict):
        # DynamoDB typed format (e.g. {'S': 'abc'}) is NOT used here,
        # we assume the scan already returned plain Python types.
        return {k: _dynamodb_to_python(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [_dynamodb_to_python(v) for v in item]
    elif isinstance(item, Decimal):
        # Keep precision for timestamps, otherwise cast to float
        if item % 1 == 0:
            return int(item)
        return float(item)
    else:
        return item


# --------------------------------------------------------------
# 2. Normalise the raw items
# --------------------------------------------------------------
raw_items = response["Items"]                     # <-- your list of dicts
items = [_dynamodb_to_python(it) for it in raw_items]

# --------------------------------------------------------------
# 3. Explicit schema (no inference!)
# --------------------------------------------------------------
schema = StructType([
    # top-level scalar fields
    StructField("event_id", StringType(), True),
    StructField("recorded_at", StringType(), True),          # keep as string for now
    StructField("record_type", StringType(), True),
    StructField("smartcar_user_id", StringType(), True),

    # meta
    StructField("meta", StructType([
        StructField("mode", StringType(), True),
        StructField("deliveryId", StringType(), True),
        StructField("webhookId", StringType(), True),
        StructField("signalCount", LongType(), True),
        StructField("webhookName", StringType(), True),
        StructField("version", StringType(), True),
        StructField("deliveredAt", LongType(), True),        # ms epoch
    ]), True),

    # user
    StructField("user", StructType([
        StructField("id", StringType(), True),
    ]), True),

    # vehicle
    StructField("vehicle", StructType([
        StructField("model", StringType(), True),
        StructField("id", StringType(), True),
        StructField("make", StringType(), True),
        StructField("year", IntegerType(), True),
    ]), True),

    # signals array
    StructField("signals", ArrayType(StructType([
        StructField("name", StringType(), True),
        StructField("code", StringType(), True),
        StructField("group", StringType(), True),

        StructField("status", StructType([
            StructField("value", StringType(), True),
            StructField("error", StructType([
                StructField("type", StringType(), True),
                StructField("code", StringType(), True),
            ]), True),
        ]), True),

        StructField("body", StructType([
            StructField("value", DoubleType(), True),
            StructField("unit", StringType(), True),
        ]), True),

        StructField("meta", StructType([
            StructField("retrievedAt", LongType(), True),
            StructField("oemUpdatedAt", LongType(), True),
        ]), True),
    ])), True),

    # triggers array
    StructField("triggers", ArrayType(StructType([
        StructField("type", StringType(), True),
        StructField("signal", StructType([
            StructField("name", StringType(), True),
            StructField("code", StringType(), True),
            StructField("group", StringType(), True),
        ]), True),
    ])), True),
])

# --------------------------------------------------------------
# 4. Create DataFrame with the explicit schema
# --------------------------------------------------------------
df = spark.createDataFrame(items, schema=schema)

# --------------------------------------------------------------
# 5. Flatten top-level structs
# --------------------------------------------------------------
df_flat = df.select(
    col("event_id"),
    col("recorded_at"),
    col("record_type"),
    col("smartcar_user_id"),
    col("meta.mode").alias("meta_mode"),
    col("meta.deliveryId").alias("meta_deliveryId"),
    col("meta.webhookId").alias("meta_webhookId"),
    col("meta.signalCount").alias("meta_signalCount"),
    col("meta.webhookName").alias("meta_webhookName"),
    col("meta.version").alias("meta_version"),
    col("meta.deliveredAt").alias("meta_deliveredAt"),
    col("user.id").alias("user_id"),
    col("vehicle.model").alias("vehicle_model"),
    col("vehicle.id").alias("vehicle_id"),
    col("vehicle.make").alias("vehicle_make"),
    col("vehicle.year").alias("vehicle_year"),
    col("signals"),
    col("triggers")
)

# --------------------------------------------------------------
# 6. Explode signals → one row per signal
# --------------------------------------------------------------
df_sig = df_flat.withColumn("signal", explode(col("signals")))

df_sig_flat = df_sig.select(
    "*" ,  # keep all previous columns
    col("signal.name").alias("signal_name"),
    col("signal.code").alias("signal_code"),
    col("signal.group").alias("signal_group"),
    col("signal.status.value").alias("signal_status_value"),
    col("signal.status.error.type").alias("signal_status_error_type"),
    col("signal.status.error.code").alias("signal_status_error_code"),
    col("signal.body.value").alias("signal_body_value"),
    col("signal.body.unit").alias("signal_body_unit"),
    col("signal.meta.retrievedAt").alias("signal_meta_retrievedAt"),
    col("signal.meta.oemUpdatedAt").alias("signal_meta_oemUpdatedAt")
).drop("signal", "signals")

# --------------------------------------------------------------
# 7. (Optional) Explode triggers → one row per trigger per signal
# --------------------------------------------------------------
df_trig = df_sig_flat.withColumn("trigger", explode(col("triggers")))

df_final = df_trig.select(
    "*",
    col("trigger.type").alias("trigger_type"),
    col("trigger.signal.name").alias("trigger_signal_name"),
    col("trigger.signal.code").alias("trigger_signal_code"),
    col("trigger.signal.group").alias("trigger_signal_group")
).drop("trigger", "triggers")

# --------------------------------------------------------------
# 8. Convert epoch ms → timestamp (optional but nice)
# --------------------------------------------------------------
df_final = df_final \
    .withColumn("meta_deliveredAt_ts",
                from_unixtime(col("meta_deliveredAt") / 1000).cast(TimestampType())) \
    .withColumn("signal_meta_retrievedAt_ts",
                from_unixtime(col("signal_meta_retrievedAt") / 1000).cast(TimestampType())) \
    .withColumn("signal_meta_oemUpdatedAt_ts",
                from_unixtime(col("signal_meta_oemUpdatedAt") / 1000).cast(TimestampType()))

# --------------------------------------------------------------
# 9. Persist to Unity Catalog
# --------------------------------------------------------------
catalog   = "your_catalog"      # <-- replace
schema_nm = "your_schema"       # <-- replace
table_nm  = "vehicle_signals"   # <-- replace

full_name = f"`{catalog}`.`{schema_nm}`.`{table_nm}`"

df_final.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(full_name)

print(f"Table {full_name} created/overwritten with {df_final.count()} rows.")
df_final.show(5, truncate=False)
```

---

### Why the original `spark.createDataFrame(items)` failed

* **`Decimal` values** inside `signals.body.value`, `meta.retrievedAt`, … are **not natively supported** by Spark’s schema inference.  
* Mixed types inside the same field (some signals have `body.unit`, others don’t) confuse the inferrer.

**Solution:**  
* Convert every `Decimal` → `float`/`int` **before** creating the DataFrame.  
* Supply an **explicit schema** that tells Spark exactly what each column/array/struct contains.

---

### Quick checklist

| Step | What you did | Why it matters |
|------|--------------|----------------|
| Normalise DynamoDB JSON | `_dynamodb_to_python` | Removes `Decimal` → Python native |
| Explicit schema | `StructType([...])` | No inference → no “Unable to infer …” |
| `explode` signals | `withColumn("signal", explode(...))` | One row per signal |
| `explode` triggers (optional) | same pattern | One row per trigger |
| Timestamp conversion | `from_unixtime(.../1000)` | Human-readable dates |
| `saveAsTable` | Unity Catalog full name | Table lands in the catalog you own |

Copy the whole block into a **Databricks notebook**, replace the three placeholder names (`your_catalog`, `your_schema`, `vehicle_signals`) and you’re done.
  
