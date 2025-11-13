Short answer: use a one-time **full export from DynamoDB to S3** for the historical backfill, run a **Databricks backfill job** over that export using the *same* transform you already use for streaming, then let your existing **Streams → Lambda → S3 → Databricks** pipeline keep you current.

Why: DynamoDB Streams only contain **future modifications** (and for ~24h), so old rows won’t ever appear on the stream. ([AWS Documentation][1])

# Recommended plan

1. **Do a full export of the table to S3 (once).**
   Use DynamoDB “Export to S3”. It’s async, has **no impact on table RCUs**, and writes either **DynamoDB JSON** or **Amazon Ion** into S3 with a manifest. Pick a distinct prefix, e.g. `s3://bucket/dynamodb-export/2025-11-12/`. ([AWS Documentation][2])

2. **Run a Databricks backfill job** over that export prefix.
   Reuse your existing transformation function (the logic that maps the nested item into your target schema). Write the output into the same Unity Catalog Delta table, using **idempotent** semantics (e.g., `MERGE` on your business key with `updated_at` tie-breakers). Enable schema evolution:

   * `spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")`
   * `mergeSchema=true` if you’re appending.
     This ensures any new attributes present in export also materialize as new columns. ([Amazon Web Services, Inc.][3])

3. **Keep your live pipeline running** for new changes.
   The stream (Lambda → S3 → Databricks) continues to deliver fresh updates while the backfill loads historical data. If overlap is possible, let the **MERGE** resolve duplicates by key + last-write-wins. ([AWS Static][4])

# Databricks backfill: practical starter

**Reading the DynamoDB export** (DynamoDB JSON) into Spark:

```python
EXPORT_PREFIX = "s3://your-bucket/dynamodb-export/2025-11-12/"
CHECKPOINT    = "s3://your-bucket/_checkpoints/ddb_backfill"
TARGET_TABLE  = "hcai_databricks_dev.chargeminder2.events"

# If your export is a one-time batch, use read (not readStream).
raw = (spark.read
       .format("json")
       .load(EXPORT_PREFIX))

# raw rows are in DynamoDB JSON ("S","N","M","L" wrappers).
# Write or import a small UDF to unwrap these to native types,
# OR pre-convert with AWS Glue (DDB JSON -> Parquet).
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# Example placeholder: you’d replace with a robust unwrap for S/N/M/L/BOOL/NULL
@udf("string")
def unwrap_example(d): 
    # d looks like {"S":"abc"} or {"N":"123"} etc.
    # ... implement full unwrap here ...
    return d.get("S") if isinstance(d, dict) and "S" in d else None

# Apply your existing transformation function to produce df_out
# df_out must match your Delta target schema (or superset, with autoMerge)
df_out = (raw
          # .withColumn("id", unwrap_example(raw["yourKey"]))
          # ... your existing mapping logic here ...
          )

spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

# Prefer MERGE for idempotency (dedupe by key/updated_at)
from delta.tables import DeltaTable
tgt = DeltaTable.forName(spark, TARGET_TABLE)
(tgt.alias("t")
   .merge(df_out.alias("s"), "t.id = s.id")
   .whenMatchedUpdateAll()
   .whenNotMatchedInsertAll()
   .execute())
```

Notes:

* If you’d rather avoid writing an “unwrap DDB JSON” UDF, an **AWS Glue job** can convert the export to **Parquet** first; then your Databricks backfill reads cleanly typed Parquet. (This is a common path and easy to automate.) ([AWS Documentation][5])
* For massive tables, run the backfill in parallel (partition on the export folder structure) and **checkpoint** only your Databricks job state (the export itself is immutable).

# Alternative (not recommended unless you must)

* **“Self-replay” the table via writes**: do a full Scan and issue a no-op `UpdateItem` per row to force a stream record so your existing Lambda sees “historical” rows. This **consumes RCUs/WCUs**, is slow/pricey, and risks side effects (TTL, triggers). Prefer Export→S3 backfill. (Streams emit only on modifications; they won’t produce events for existing items.) ([AWS Documentation][1])

# Format & governance tips

* DynamoDB Export creates **manifests + gzipped object shards**; point Databricks at the prefix; don’t forget to recurse folders. ([AWS Documentation][6])
* Keep a **max `source_updated_at`** watermark in your Delta table so the backfill MERGE can skip newer rows if needed (or let last-write-wins).
* If your streaming Lambda writes in a different JSON shape than the export, keep two reader paths but a **single transform()** that normalizes to a common intermediate schema before writing.
* For ongoing sync use cases, AWS now documents **full export + incremental exports** patterns that complement streams. ([Amazon Web Services, Inc.][3])

# TL;DR

1. One-time **Export to S3** → Databricks **backfill job** (MERGE, auto-evolve schema).
2. Keep **Streams→Lambda→S3→Databricks** for new changes.
   This cleanly covers “historical + real-time” with minimal risk and strong performance. ([AWS Documentation][2])

[1]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html?utm_source=chatgpt.com "Change data capture for DynamoDB Streams"
[2]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.HowItWorks.html?utm_source=chatgpt.com "DynamoDB data export to Amazon S3: how it works"
[3]: https://aws.amazon.com/solutions/guidance/incremental-data-exports-from-amazon-dynamodb-to-amazon-s3/?utm_source=chatgpt.com "Guidance for Incremental Data Exports from Amazon ..."
[4]: https://d1.awsstatic.com/solutions/guidance/architecture-diagrams/incremental-data-exports-on-aws.pdf?utm_source=chatgpt.com "Guidance for Incremental Data Exports on AWS - awsstatic.com"
[5]: https://docs.aws.amazon.com/prescriptive-guidance/latest/dynamodb-full-table-copy-options/amazon-s3.html?utm_source=chatgpt.com "Using DynamoDB with Amazon S3 to export and import ..."
[6]: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport.Output.html?utm_source=chatgpt.com "DynamoDB table export output format"


### Backfilling Historical DynamoDB Data into Your Streaming Pipeline

Your existing pipeline (DynamoDB Streams → Lambda → S3 → Databricks Job) is designed for **incremental** processing of new/modified records via streams, which capture only changes made *after* the stream is enabled (with a 24-hour retention limit). Historical records (pre-pipeline data) won't trigger the stream automatically, so you need a **one-time backfill** process to export them to the same S3 location in a compatible format. This ensures the Databricks job can process them seamlessly, populating your Unity Catalog table with full historical data before ongoing streams take over.

The recommended approach uses DynamoDB's native **Export to S3** feature, which is serverless, doesn't consume read capacity units (RCUs), and exports data asynchronously without impacting table performance. It supports Point-in-Time Recovery (PITR) for consistent snapshots from up to 35 days ago (or full table if PITR is enabled). Exports land in S3 as DynamoDB JSON files (or Amazon Ion), which your Lambda likely parses—ensure the backfill format matches (e.g., via Lambda transformation if needed).

#### Prerequisites
- **Enable PITR** on your DynamoDB table (if not already): This is required for exports and allows point-in-time snapshots. In the AWS Console: DynamoDB → Tables → Your Table → Backups → Edit → Enable Point-in-Time Recovery (PITR). It's free for the first 35 days of retention.
- **S3 Bucket Permissions**: Grant the DynamoDB service principal (`dynamodb.amazonaws.com`) `PutObject` access to your target S3 bucket/prefix (the same one your Lambda uses). Use an IAM policy like:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "dynamodb.amazonaws.com" },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::your-bucket/your-prefix/*"
      }
    ]
  }
  ```
- **IAM Role for DynamoDB Export**: Attach `AmazonDynamoDBFullAccess` (or scoped to `dynamodb:ExportTableToPointInTime`) to your IAM user/role.
- **Databricks Access**: Ensure your Databricks workspace has S3 read access (via instance profile or access keys) to ingest the exported files.

#### Step-by-Step: Export Historical Data to S3
1. **Via AWS Console (Simplest for One-Off)**:
   - Go to DynamoDB Console → Tables → Your Table → Exports to S3 tab.
   - Click **Export to S3**.
   - **S3 Bucket and Prefix**: Enter your existing S3 location (e.g., `s3://your-bucket/streaming-prefix/historical/` to avoid overwriting live files—use a sub-prefix and merge in Databricks if needed).
   - **Point-in-Time**: Select "Full export" for all historical data, or specify a timestamp (e.g., pipeline start time) for a snapshot.
   - **Format**: Choose DynamoDB JSON (matches stream events; convert to standard JSON if your Lambda expects it).
   - Click **Export**. Monitor progress in the Exports tab (typically minutes to hours, based on table size; up to 100 TB supported).
   - Files appear in S3 as compressed JSON manifests (e.g., `data/*.json.gz`), partitioned by hash/range keys for efficiency.

2. **Via AWS CLI (For Automation/Scripting)**:
   ```bash
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:region:account:table/your-table \
     --s3-bucket your-bucket \
     --s3-s3-prefix streaming-prefix/historical/ \
     --export-format DynamoDBJson
   ```
   - Track with `aws dynamodb describe-export --export-arn <export-arn>`.
   - Costs: $0.10/GB exported (full export based on table size at export time).

3. **Handling Large Tables**:
   - Exports are parallelized across shards; no RCU impact.
   - If >100 TB or cross-region/account: Exports support it natively (grant cross-account S3 perms).
   - Incremental exports (for changes since last export) are possible but not needed for one-time backfill.

#### Integrate with Your Pipeline: Process in Databricks
Once exported to S3, trigger your Databricks job manually (or via a File Arrival sensor on the historical prefix) to read and ingest the files—just like streaming data. This populates the Unity Catalog table with historical records.

- **Databricks Job/Task Code Example** (PySpark; assumes Delta table for schema evolution):
  ```python
  # Read historical JSON from S3 (matches Lambda output format)
  df = (spark.read
      .format("json")  # Or "cloudFiles" for Auto Loader if using incremental mode
      .option("multiline", "true")  # For nested JSON
      .load("s3://your-bucket/streaming-prefix/historical/")  # Your export path
  )

  # Optional: Flatten/transform if needed (e.g., extract from stream event wrapper)
  from pyspark.sql.functions import col
  df = df.select("dynamodb.NewImage.*")  # Adjust based on stream format (OldImage/NewImage)

  # Write to Unity Catalog table (append with schema evolution)
  df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable("my_catalog.my_schema.your_table")
  ```
  - **Schema Evolution**: As discussed previously, `mergeSchema=true` auto-adds columns for any schema drift between historical and streaming data.
  - **DynamoDB JSON Handling**: Exports use DynamoDB's binary JSON (with types like `N` for numbers). Use `from_dynamodb_json` UDF if needed:
    ```python
    from pyspark.sql.functions import udf
    from pyspark.sql.types import StringType
    import json
    def parse_ddb_json(col):
        return json.loads(col)  # Or use boto3.dynamodb.types.TypeDeserializer
    parse_udf = udf(parse_ddb_json, StringType())
    df = df.withColumn("parsed_data", parse_udf(col("data")))
    ```
  - Run the job: In Databricks Workflows, trigger manually or schedule once.

- **Verify Ingestion**:
  - Query the Delta table: `SELECT COUNT(*) FROM my_catalog.my_schema.your_table;`
  - Check for duplicates: Add a watermark or processed flag in your Lambda/Databricks to dedupe (e.g., based on DynamoDB sequence number).

#### Ongoing Streaming: Seamless Handoff
- After backfill, your Lambda continues writing new stream events to the same S3 prefix (e.g., without `/historical/`).
- To merge: Configure Databricks to read from the root prefix, or use Auto Loader (`cloudFiles`) for unified incremental + historical processing:
  ```python
  df = (spark.readStream
      .format("cloudFiles")
      .option("cloudFiles.format", "json")
      .load("s3://your-bucket/streaming-prefix/")  # Includes historical + new
  )
  # Write stream as before
  ```
- **Idempotency**: Ensure your Databricks transform handles `INSERT`/`MODIFY`/`REMOVE` stream records (e.g., via MERGE for upserts).

#### Alternatives If Export Doesn't Fit
| Method | Pros | Cons | When to Use |
|--------|------|------|-------------|
| **DynamoDB Export to S3** (Recommended) | Serverless, no RCU cost, scalable to TBs, PITR snapshots. | Requires PITR; format conversion if mismatched. | Large tables; one-time full backfill. |
| **Scan via Lambda/EC2 Script** | Customizable; direct to S3. | Consumes RCUs; Lambda timeout (15 min); manual scaling. | Small tables (<1 GB); if no PITR. Example: Loop `scan()` API, batch-write to S3. |
| **Update Existing Items to Trigger Stream** | Reuses exact pipeline. | High cost (write RCUs); risk of duplicates/outages. | Very small tables; testing only. Add/remove a flag field via script. |
| **AWS Glue/EMR** | Handles transforms; ETL jobs. | Extra cost (~$0.44/hour per DPU); setup overhead. | Complex schema changes during backfill. |

#### Costs and Best Practices
- **Export Cost**: $0.10/GB (e.g., 100 GB table = $10 one-time).
- **S3 Storage**: ~$0.023/GB/month; use lifecycle policies to archive/delete historical files post-ingestion.
- **Monitoring**: Track export status via CloudWatch (`DynamoDBExport*` metrics); Databricks job logs for ingestion errors.
- **Testing**: Export a small PITR window first; validate row counts match `scan` estimates.
- **Edge Cases**: If data >35 days old (no PITR history), use full export. For cross-account S3, add bucket policies.

This backfill keeps your pipeline unchanged while ensuring complete data in Databricks. If your Lambda outputs a specific format (e.g., Parquet), add a post-export Glue job to transform. Share more details (e.g., table size, Lambda code snippet) for tweaks!
