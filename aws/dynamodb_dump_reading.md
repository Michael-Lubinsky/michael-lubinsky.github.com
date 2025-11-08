### Read a DynamoDB "Export to S3" (DynamoDB JSON) into a DataFrame

S: String
N: Number
M: Map (nested object)
L: List
BOOL: Boolean
NULL: Null
B: Binary (base64-encoded)

 File Organization

- Multiple files: The export is split into multiple files (one per DynamoDB partition, by default).
- Gzipped: Each file is compressed with GZIP (.gz extension).
- Manifest file: There’s also a manifest file (manifest-files.json) listing all the data files.



Tip: the export will include many shard files plus a manifest-files.json. Read the data files (e.g., .../AWSDynamoDB/.../data/) and ignore manifests in your Spark job.

- Read the exported objects from S3 as text (they’re gzip’d JSON lines).

- Parse each line, take the "Item" payload, and convert DynamoDB-JSON
  (typed like {"S": "..."},"N":"42","M":{...},"L":[...])
  to plain Python types using boto3.dynamodb.types.TypeDeserializer.

- Optionally spark.read.json again on the normalized JSON to get a proper schema, or from_json with an explicit schema.


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
