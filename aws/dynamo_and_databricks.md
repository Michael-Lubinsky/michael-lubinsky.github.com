## Read  DynamoDB table *into* your Databricks notebook 


## 1) Easiest + scalable: **Export DynamoDB → S3**, then read with Spark

**Why:** It’s serverless, doesn’t consume RCUs, and you can do **full** or **incremental** exports (PITR window). Data lands in S3 as **DynamoDB JSON** or **Amazon Ion** files; Databricks can read them directly. ([AWS Documentation][1])

**Steps (one-time / per-run):**

1. In the DynamoDB console: *Exports to S3* → choose **Full** (or **Incremental**) export, pick S3 bucket/prefix, format **DynamoDB JSON** (simplest), and run. (PITR must be enabled.) ([AWS Documentation][2])
2. In Databricks, read the S3 prefix that contains `data/` files (ignore the `manifest-files.json`):

```python
# Spark (PySpark) on Databricks
s3_path = "s3://your-bucket/prefix/<export-id>/data/"  # or .../incremental/data/
df_raw = spark.read.json(s3_path)  # reads DynamoDB JSON (typed)
df_raw.printSchema()
df_raw.show(3, truncate=False)
```

DynamoDB JSON is *typed* (e.g., `{"attr":{"S":"value"}}`). A quick normalizer to unwrap common types:

```python
from pyspark.sql import functions as F

def unwrap(col):
    # unwrap common DynamoDB JSON types; add others (BOOL, L, M, NULL, BS, NS) as needed
    return F.coalesce(col.getField("S"), col.getField("N"), col.getField("B"))

# Example: suppose items have keys "id", "updated_at", "payload"
df = df_raw.select(
    unwrap(F.col("id")).alias("id"),
    unwrap(F.col("updated_at")).cast("timestamp").alias("updated_at"),
    F.col("payload")  # if this is a map (M), handle similarly by drilling into fields
)
df.display()
```

**Pros:** No load on the live table; supports incremental refreshes you can schedule. **Cons:** Export is asynchronous; format is typed JSON/Ion you may need to unwrap. ([AWS Documentation][1])

---

## 2) Quick, small/medium tables: **AWS SDK for pandas (awswrangler)** inside Databricks

Great when you want to **scan/query now** without setting up an export. Use `wr.dynamodb.read_items` (scan) or `wr.dynamodb.read_partiql_query` (filter). Returns a pandas DataFrame; convert to Spark if needed. ([aws-sdk-pandas.readthedocs.io][3])

```python
# %pip install awswrangler
import awswrangler as wr
import boto3

session = boto3.Session(region_name="us-east-1")  # set your region

# 2a) Full read (scan) -- careful on big tables
pdf = wr.dynamodb.read_items(
    table_name="your_table",
    boto3_session=session,
)

# 2b) Filter with PartiQL (server-side)
pdf = wr.dynamodb.read_partiql_query(
    query="SELECT * FROM your_table WHERE updated_at >= ?",
    parameters=["2025-09-01T00:00:00Z"],
    boto3_session=session,
)

# Convert to Spark if you prefer Spark APIs
df = spark.createDataFrame(pdf)
df.display()
```

**Pros:** Minimal setup, flexible queries. **Cons:** Scans can be slow/pricey at scale; mind RCUs; better for small/medium pulls or targeted PartiQL. ([aws-sdk-pandas.readthedocs.io][3])

---

## 3) Advanced: **Spark ↔ DynamoDB connector (EMR DynamoDB Connector)**

You can wire the EMR DynamoDB Hadoop/Spark connector jars to Databricks and use the `DynamoDBInputFormat`. This is powerful but more involved (jars, configs, IAM, throttling). If you manage heavy reads/writes frequently, consider running this on EMR; on Databricks it’s doable but fiddly. ([GitHub][4])

**Sketch (Scala/Python pyspark style):**

```python
# After attaching the EMR DynamoDB connector JARs to the cluster:
conf = {
  "dynamodb.input.tableName": "your_table",
  "dynamodb.region": "us-east-1",
  "dynamodb.throughput.read.percent": "0.25",  # throttle to 25% RCUs
}

rdd = sc.newAPIHadoopRDD(
    "org.apache.hadoop.dynamodb.read.DynamoDBInputFormat",
    "org.apache.hadoop.io.Text",
    "org.apache.hadoop.io.MapWritable",
    conf
)

# Convert to DataFrame (you'll need a mapper to flatten MapWritable)
```

**Pros:** Parallel Spark reads direct from DynamoDB. **Cons:** Setup complexity; need to manage RCUs/backoff; less “plug-and-play” on Databricks. ([GitHub][4])

---

## 4) Very small tables / ad-hoc: **boto3 scan** then parallelize

Fine for a few thousand items; not recommended at scale.

```python
import boto3
from itertools import islice

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("your_table")

items = []
resp = table.scan()
items.extend(resp.get("Items", []))
while "LastEvaluatedKey" in resp:
    resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
    items.extend(resp.get("Items", []))

df = spark.createDataFrame(items)
df.count(), df.display()
```

---

## Credentials / IAM notes (Databricks on AWS)

* Prefer attaching an **instance profile**/IAM role to the cluster so Spark & libraries can talk to S3 and DynamoDB without embedding keys.
* For S3 reads (Option 1), make sure the cluster has `s3:GetObject` on the export bucket/prefix.
* For exports (Option 1), the exporting principal needs `dynamodb:ExportTableToPointInTime` and S3 `PutObject` on the target bucket. PITR must be enabled to export. ([AWS Documentation][2])

---

## Which should you pick?

* **Batch analytics** (your case sounds like this): **Export→S3** then read with Spark. Use **incremental export** on a schedule (e.g., every 5–15 min) to keep Databricks up to date without hammering DynamoDB. ([Amazon Web Services, Inc.][5])
* **Small/targeted pulls**: `awswrangler` with PartiQL. ([aws-sdk-pandas.readthedocs.io][6])
* **Heavy direct access**: EMR connector (or just run on EMR Serverless). ([AWS Documentation][7])

If you want, I can give you a ready-to-run Databricks notebook that:

1. starts an **incremental export** (CLI/API),
2. reads the **new files** from S3, normalizes the DynamoDB JSON, and
3. merges into a Delta table.

[1]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.HowItWorks.html?utm_source=chatgpt.com "DynamoDB data export to Amazon S3: how it works"
[2]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport_Requesting.html?utm_source=chatgpt.com "Requesting a table export in DynamoDB - AWS Documentation"
[3]: https://aws-sdk-pandas.readthedocs.io/en/3.10.1/stubs/awswrangler.dynamodb.read_items.html?utm_source=chatgpt.com "awswrangler.dynamodb.read_items - AWS SDK for pandas"
[4]: https://github.com/awslabs/emr-dynamodb-connector?utm_source=chatgpt.com "awslabs/emr-dynamodb-connector"
[5]: https://www.amazonaws.cn/en/blog-selection/introducing-incremental-export-from-amazon-dynamodb-to-amazon-s3/?nc1=h_ls&utm_source=chatgpt.com "Introducing incremental export from Amazon DynamoDB to Amazon ..."
[6]: https://aws-sdk-pandas.readthedocs.io/en/3.10.0/stubs/awswrangler.dynamodb.read_partiql_query.html?utm_source=chatgpt.com "awswrangler.dynamodb.read_partiql_query"
[7]: https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-ddb-connector.html?utm_source=chatgpt.com "Connecting to DynamoDB with Amazon EMR Serverless"
