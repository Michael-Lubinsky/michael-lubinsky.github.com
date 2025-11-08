## Read a DynamoDB "Export to S3" (DynamoDB JSON) into a DataFrame

S: String
N: Number
M: Map (nested object)
L: List
BOOL: Boolean
NULL: Null
B: Binary (base64-encoded)

### File Organization

- Multiple files: The export is split into multiple files (one per DynamoDB partition, by default).
- Gzipped: Each file is compressed with GZIP (.gz extension).
- Manifest file: There’s also a manifest file (manifest-files.json) listing all the data files.
```
AWSDynamoDB/01671980323456-7abcdef0/manifest-files.json
AWSDynamoDB/01671980323456-7abcdef0/data/part-00000.gz
AWSDynamoDB/01671980323456-7abcdef0/data/part-00001.gz
```

Tip: the export will include many shard files plus a manifest-files.json. Read the data files (e.g., .../AWSDynamoDB/.../data/) and ignore manifests in your Spark job.

- Read the exported objects from S3 as text (they’re gzip’d JSON lines).

- Parse each line, take the "Item" payload, and convert DynamoDB-JSON
  (typed like {"S": "..."},"N":"42","M":{...},"L":[...])
  to plain Python types using boto3.dynamodb.types.TypeDeserializer.

- Optionally spark.read.json again on the normalized JSON to get a proper schema, or from_json with an explicit schema.

### mistral
```python
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, ArrayType, MapType
import json

# Your schema definitions (as provided)
# ... (keep your raw_schema and all nested structs as before) ...

# Initialize SparkSession with AWS config
spark = SparkSession.builder \
    .appName("ReadDynamoDBExport") \
    .config("spark.hadoop.fs.s3a.access.key", "YOUR_AWS_ACCESS_KEY") \
    .config("spark.hadoop.fs.s3a.secret.key", "YOUR_AWS_SECRET_KEY") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# Path to your DynamoDB export data files
s3_path = "s3a://your-bucket-name/AWSDynamoDB/01671980323456-7abcdef0/data/*.gz"

# Read all .gz files as text
df_text = spark.read.text(s3_path)

# UDF to convert DynamoDB JSON to standard JSON
def convert_dynamodb_json(dynamodb_json_str):
    try:
        data = json.loads(dynamodb_json_str)
        item = {}
        for k, v in data.items():
            # Handle each DynamoDB type
            for typ, val in v.items():
                if typ == "S":
                    item[k] = str(val)
                elif typ == "N":
                    try:
                        item[k] = int(val) if "." not in val else float(val)
                    except:
                        item[k] = val
                elif typ == "BOOL":
                    item[k] = bool(val)
                elif typ == "NULL":
                    item[k] = None
                elif typ == "L":
                    item[k] = [convert_dynamodb_json({"v": x})["v"] for x in val]
                elif typ == "M":
                    item[k] = convert_dynamodb_json(val)
                elif typ == "B":
                    item[k] = val  # base64-encoded binary
        return json.dumps(item)
    except Exception as e:
        print(f"Error converting JSON: {e}")
        return None

# Register UDF
convert_dynamodb_udf = F.udf(convert_dynamodb_json, StringType())

# Convert DynamoDB JSON to standard JSON
df_converted = df_text.withColumn(
    "standard_json",
    convert_dynamodb_udf(F.col("value"))
)

# Parse the standard JSON with your schema
df_parsed = df_converted.select(
    F.from_json(F.col("standard_json"), raw_schema).alias("data")
).select("data.*")

# Show the DataFrame schema and data
df_parsed.printSchema()
df_parsed.show(truncate=False)

```

### ChatGPT

```python
# PySpark: Read a DynamoDB "Export to S3" (DynamoDB JSON) into a DataFrame
# - Works with the console/UI export ("DynamoDB JSON" format; files are gzip'd JSON lines)
# - Point `ddb_export_s3_uri` at the *export folder*, Spark will read the /data/ shards
# - Result: a clean Spark DataFrame with native types (strings, numbers, arrays, structs)

from pyspark.sql import functions as F
from pyspark.sql import types as T
import json
from decimal import Decimal

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# CONFIG: change this to your export location (keep the trailing '/data/' or we'll add it)
ddb_export_s3_uri = "s3a://YOUR-BUCKET/AWSDynamoDB/016-YYYYMMDDThhmmZ-abcdef/export-abcdef/data/"
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# If the user passes the root export folder, normalize to its /data/ subfolder
if not ddb_export_s3_uri.rstrip("/").endswith("/data"):
    ddb_export_s3_uri = ddb_export_s3_uri.rstrip("/") + "/data/"

# -------- DynamoDB JSON -> native Python types (recursive) --------
def _to_number(n: str):
    # Convert DynamoDB N (always a string) to int if possible, else float.
    # Adjust if you want Decimal precision instead.
    try:
        if "." in n or "e" in n or "E" in n:
            return float(n)
        return int(n)
    except Exception:
        # fallback to Decimal, Spark will coerce later when reading JSON
        return float(Decimal(n))

def ddbjson_to_python(obj):
    """
    Convert a DynamoDB-JSON value (S, N, BOOL, NULL, M, L, SS, NS, BS, B) to native Python.
    """
    if isinstance(obj, dict) and len(obj) == 1:
        k, v = next(iter(obj.items()))
        if k == "S":   return v
        if k == "N":   return _to_number(v)
        if k == "BOOL": return bool(v)
        if k == "NULL": return None
        if k == "M":   return {kk: ddbjson_to_python(vv) for kk, vv in v.items()}
        if k == "L":   return [ddbjson_to_python(x) for x in v]
        if k == "SS":  return list(v)
        if k == "NS":  return [_to_number(x) for x in v]
        if k == "BS":  return list(v)  # base64-encoded strings; keep as-is or decode if needed
        if k == "B":   return v        # base64-encoded string
    # If it's already a plain type or not a typed DDB-JSON dict, return as-is
    if isinstance(obj, list):
        return [ddbjson_to_python(x) for x in obj]
    if isinstance(obj, dict):
        return {k: ddbjson_to_python(v) for k, v in obj.items()}
    return obj

# -------- Read raw export lines (Spark auto-decompresses .gz) --------
# Each line is a JSON object; the item payload is in the "Item" field.
raw_lines = spark.read.text(ddb_export_s3_uri).select("value").rdd.map(lambda r: r[0])

def extract_clean_json(line):
    if not line:
        return None
    try:
        rec = json.loads(line)
        # DynamoDB export lines typically contain {"Item": {...}, ...}
        item = rec.get("Item")
        if item is None:
            # Fallback: some exports may store data under a different key; ignore non-item lines
            return None
        clean = ddbjson_to_python(item)
        # Convert to a compact JSON string; Spark will infer schema when reading JSON
        return json.dumps(clean, separators=(",", ":"))
    except Exception:
        # Malformed line or unexpected shape; skip
        return None

clean_json_rdd = raw_lines.map(extract_clean_json).filter(lambda s: s is not None)

# -------- Create a DataFrame --------
# Using read.json on an RDD of JSON strings gives robust schema inference for nested structures.
df = spark.read.json(clean_json_rdd)

# Example: inspect results
df.printSchema()
df.show(20, truncate=False)

# -------- (Optional) Enforce a known schema --------
# If you already know the target schema, you can apply it for stronger typing:
# target_schema = T.StructType([
#     T.StructField("id", T.StringType(), True),
#     T.StructField("ts", T.LongType(), True),
#     T.StructField("value", T.DoubleType(), True),
#     T.StructField("tags", T.ArrayType(T.StringType()), True),
#     T.StructField("meta", T.StructType([
#         T.StructField("source", T.StringType(), True),
#         T.StructField("oemUpdatedAt", T.LongType(), True),
#     ]), True),
# ])
# df = spark.read.schema(target_schema).json(clean_json_rdd)

# -- (Optional) Write once to Parquet/Delta for faster downstream use ---
# df.write.mode("overwrite").parquet("s3a://YOUR-BUCKET/curated/your_table/")
# df.write.format("delta").mode("overwrite").save("s3a://YOUR-BUCKET/delta/your_table/")
```

Notes:

* Point `ddb_export_s3_uri` at the **/data/** folder inside your DynamoDB export. The code auto-adjusts if you give the root.
* Numbers (`"N"`) are parsed to `int` or `float`. If you need exact decimal precision, swap `_to_number` to return `Decimal` and provide an explicit Spark schema with `DecimalType`.
* Binary types (`B`, `BS`) are left as base64 strings; decode if you need raw bytes.



## Mistral
Here’s a **PySpark code snippet** to read DynamoDB JSON export files (GZIP-compressed, DynamoDB-typed JSON) from S3 into a DataFrame, with type conversion to a flat schema:


### **1. Setup and Dependencies**
Make sure your Spark session has the `hadoop-aws` library and AWS credentials configured.

### **2. PySpark Code**

```python
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, MapType, IntegerType, DoubleType, BooleanType, ArrayType
import gzip
import json

# Initialize SparkSession with AWS config
spark = SparkSession.builder \
    .appName("ReadDynamoDBExport") \
    .config("spark.hadoop.fs.s3a.access.key", "YOUR_AWS_ACCESS_KEY") \
    .config("spark.hadoop.fs.s3a.secret.key", "YOUR_AWS_SECRET_KEY") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# Path to your DynamoDB export data files (use wildcard to match all .gz files)
s3_path = "s3a://your-bucket-name/AWSDynamoDB/01671980323456-7abcdef0/data/*.gz"

# Read all .gz files as text
df_text = spark.read.text(s3_path)

# UDF to parse DynamoDB JSON and flatten types
def parse_dynamodb_json(json_str):
    try:
        data = json.loads(json_str)
        item = {}
        for k, v in data.items():
            # Handle each DynamoDB type
            for typ, val in v.items():
                if typ == "S":
                    item[k] = str(val)
                elif typ == "N":
                    try:
                        item[k] = int(val) if "." not in val else float(val)
                    except:
                        item[k] = val
                elif typ == "BOOL":
                    item[k] = bool(val)
                elif typ == "NULL":
                    item[k] = None
                elif typ == "L":
                    item[k] = [parse_dynamodb_json({"v": x})["v"] for x in val]
                elif typ == "M":
                    item[k] = parse_dynamodb_json(val)
                elif typ == "B":
                    item[k] = val  # base64-encoded binary
        return item
    except:
        return None

# Register UDF
parse_dynamodb_udf = F.udf(parse_dynamodb_json, MapType(StringType(), StringType()))

# Parse each line
df_parsed = df_text.select(
    parse_dynamodb_udf("value").alias("data")
).select("data.*")

# Show the DataFrame
df_parsed.show(truncate=False)
```

### **3. Key Points**
- **GZIP Handling:** Spark’s `.text()` method automatically decompresses `.gz` files.
- **Type Conversion:** The UDF flattens DynamoDB-typed JSON into a map of native Python types.
- **Schema Inference:** The resulting DataFrame will have columns for each top-level attribute in your DynamoDB items.


### **4. Customization**
- **Schema:** If you know your schema, replace the `MapType` with a `StructType` for better type safety.
- **Nested Fields:** The UDF handles nested maps and lists, but you may want to flatten them further.

```
   
body_struct = StructType([
    StructField("value", StringType(), True),
    StructField("unit",  StringType(), True),
    StructField("capacity",  StringType(), True),
    StructField("locationType",  StringType(), True),
    StructField("heading",  StringType(), True),
    StructField("latitude",  StringType(), True),
    StructField("longitude", StringType(), True),
    StructField("direction",  StringType(), True),

])

signal_struct = StructType([
    StructField("name",   StringType(), True),
    StructField("code",   StringType(), True),
    StructField("group",  StringType(), True),
    StructField("status", StructType([
        StructField("value", StringType(), True),
        StructField("error", StructType([
            StructField("type", StringType(), True),
            StructField("code", StringType(), True),
        ]), True),
    ]), True),
    StructField("body", body_struct, True),
    StructField("meta", StructType([
        StructField("retrievedAt", LongType(), True),
        StructField("oemUpdatedAt", LongType(), True),
    ]), True),
])

trigger_struct = StructType([
    StructField("type", StringType(), True),
    StructField("signal", StructType([
        StructField("name", StringType(), True),
        StructField("code", StringType(), True),
        StructField("group", StringType(), True),
    ]), True),
])

raw_schema = StructType([
    StructField("event_id",         StringType(), True),
    StructField("record_type",      StringType(), True),
    StructField("recorded_at",      StringType(), True),
    StructField("car_timezone",     StringType(), True),
    StructField("smartcar_user_id", StringType(), True),

    StructField("vehicle", StructType([
        StructField("id",    StringType(), True),
        StructField("make",  StringType(), True),
        StructField("model", StringType(), True),
        StructField("year",  IntegerType(), True),
    ]), True),

    StructField("user", StructType([
        StructField("id", StringType(), True),
    ]), True),

    StructField("meta", StructType([
        StructField("mode",        StringType(), True),
        StructField("deliveryId",  StringType(), True),
        StructField("webhookId",   StringType(), True),
        StructField("signalCount", IntegerType(), True),
        StructField("webhookName", StringType(), True),
        StructField("version",     StringType(), True),
        StructField("deliveredAt", StringType(), True),
    ]), True),

    StructField("signals",  ArrayType(signal_struct), True),
    StructField("triggers", ArrayType(trigger_struct), True),

    StructField("_processing_metadata", StructType([
        StructField("processed_at", StringType(), True),
        StructField("event_id", StringType(), True),
        StructField("event_name", StringType(), True),
        StructField("lambda_version", StringType(), True),
    ]), True),
])
```
