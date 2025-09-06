How to move data from Postgres to Snowflake?

You can’t make `\copy` write “directly to Azure Blob” by itself—the `\copy ... TO PROGRAM` runs **on the client** (where `psql` is running). On Azure Database for PostgreSQL you also don’t have superuser, so server-side `COPY … TO PROGRAM` isn’t an option.

The good news: you can **stream** the export straight to Azure without writing a local file by piping `psql` → `gzip` → **AzCopy** (which supports stdin). No disk space needed.

### How to find Tenant id

Your **tenant GUID** is the unique identifier of your Azure Active Directory (AAD) tenant. You can find it directly from the Azure Portal or via CLI:

---

#### Option 1: Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com).
2. In the search bar at the top, type **Azure Active Directory** and click it.
3. In the **Overview** page of Azure Active Directory, you’ll see:

   * **Tenant ID** (that’s the GUID you need).
   * **Primary domain**.
4. Copy the **Tenant ID** — that’s the value to use in your `azcopy login --tenant-id "<tenant-guid>"`.

---

#### Option 2: Azure CLI

If you are already logged in with `az login`:

```bash
az account show --query tenantId --output tsv
```

This will print just the tenant GUID.

Alternatively, to see all tenants you have access to:

```bash
az account list --output table
```


## One table (stream to ADLS Gen2 with AzCopy)

```bash
# Log in AzCopy with your AAD identity (or use a SAS on the URL instead)
azcopy login --tenant-id "<your-tenant-guid>"

PG_URL="host=<pg-host> dbname=<db> user=<user> password=<pwd> port=5432"
TABLE="public.customers"
DEST_URL="https://<storageacct>.dfs.core.windows.net/<filesystem>/pg_full_load/public__customers.csv.gz"

# Stream: Postgres -> CSV -> gzip -> AzCopy to ADLS (no local file)
psql "$PG_URL" -c "COPY (SELECT * FROM ${TABLE}) TO STDOUT WITH (FORMAT csv, HEADER true)" \
  | gzip -c \
  | azcopy copy "stdin:" "$DEST_URL" --from-to=PipeBlob --content-type "text/csv" --content-encoding "gzip"
```

Notes:

* Use the **DFS endpoint** (`.dfs.core.windows.net`) for ADLS Gen2.
* If you prefer a SAS instead of AAD login, append it to `DEST_URL` and skip `azcopy login`.
* `--from-to=PipeBlob` tells AzCopy to read from **STDIN** and upload as a block blob, chunking automatically (works for large files).

## Many tables (loop)

This loops over a list from Postgres and streams each table straight to ADLS. Adjust schemas and naming as you like.

```bash
#!/usr/bin/env bash
set -euo pipefail

PG_URL="host=<pg-host> dbname=<db> user=<user> password=<pwd> port=5432"
ACCOUNT="<storageacct>"
FILESYS="<filesystem>"
PREFIX="pg_full_load"

# 1) get the table list
TABLES=$(psql "$PG_URL" -At -c "
  SELECT schemaname||'.'||tablename
  FROM pg_catalog.pg_tables
  WHERE schemaname IN ('public')  -- add schemas here
  ORDER BY 1;
")

# 2) upload each table via streaming
for T in $TABLES; do
  SAFE_NAME=$(echo "$T" | tr '.' '__')
  DEST_URL="https://${ACCOUNT}.dfs.core.windows.net/${FILESYS}/${PREFIX}/${SAFE_NAME}.csv.gz"

  echo "Uploading $T -> $DEST_URL"
  psql "$PG_URL" -c "COPY (SELECT * FROM ${T}) TO STDOUT WITH (FORMAT csv, HEADER true)" \
    | gzip -c \
    | azcopy copy "stdin:" "$DEST_URL" --from-to=PipeBlob --content-type "text/csv" --content-encoding "gzip"
done
```

## GEMINI

Since you don't have enough disk space on your MacBook for a PostgreSQL dump, 
you can perform the dump and upload it to Azure Blob Storage in a single, streamed operation without saving the file locally. This method pipes the output of `pg_dump` directly to `azcopy`.

-----

### Method 1: Stream `pg_dump` to `azcopy`

This is the most efficient and direct way to dump a database to cloud storage without using any local disk space.

#### Step 1: Install `azcopy` and `pg_dump`

Make sure you have both `azcopy` and the `pg_dump` client tools installed on your MacBook.

#### Step 2: Use a Named Pipe

Create a named pipe (a special file that acts as a stream) to connect the output of `pg_dump` to the input of `azcopy`. This allows data to flow directly from one command to the other.

1.  **Create a named pipe:**

    ```bash
    mkfifo /tmp/postgres_dump_pipe
    ```

2.  **Start `azcopy` listening on the pipe:**
    In one terminal window, start the `azcopy` command, telling it to copy from the named pipe to your Azure Blob Storage container. The `azcopy` command will wait for data to be sent to the pipe.

    ```bash
    azcopy copy /tmp/postgres_dump_pipe "https://<your-storage-account>.blob.core.windows.net/<your-container-name>/<dump-file-name>?[SAS_TOKEN]"
    ```

    *`azcopy` will now be paused, waiting for input.*

3.  **Pipe `pg_dump` output to the pipe:**
    In a **separate** terminal window, run the `pg_dump` command and redirect its output to the named pipe. As soon as `pg_dump` starts generating the dump, the data will be streamed directly to `azcopy` and uploaded to Azure.

    ```bash
    pg_dump -h <your-server-name.postgres.database.azure.com> -U <your-username> -d <your-database-name> -Fp > /tmp/postgres_dump_pipe
    ```

    *Once `pg_dump` completes, `azcopy` will finish its transfer.*

#### Step 3: Clean Up

After the transfer is complete, delete the named pipe.

```bash
rm /tmp/postgres_dump_pipe
```

\<br\>

-----

### Method 2: Use an Azure Virtual Machine

If you have an Azure subscription, you can spin up a small VM (e.g., a B1s) to act as an intermediary. This offloads the entire process to the cloud, using the VM's temporary disk space.

#### Step 1: Create an Azure VM

Create a Linux VM in the same region as your PostgreSQL Flexible Server. This minimizes data transfer latency.

#### Step 2: Install PostgreSQL and `azcopy`

On the VM, install the PostgreSQL client tools and `azcopy`.

#### Step 3: Run `pg_dump` on the VM

Log in to the VM via SSH and run the `pg_dump` command to dump the database to the VM's disk.

#### Step 4: Upload from the VM

Use the `azcopy` command on the VM to upload the dump file to your Azure Blob Storage. This transfer will be extremely fast because it's happening within the Azure network.













###############


## Why not `az` CLI?

`az storage fs/blob upload` expects a **file path**; it doesn’t read from stdin. **AzCopy** is the supported way to upload from a pipe.

## Alternative: Parquet streaming (optional)

If you want Parquet for faster `COPY` in Snowflake, you’d need a local temp file or a small VM/ephemeral disk because typical Parquet writers don’t stream to stdout. The CSV+gzip+pipe method above avoids disk entirely.

## Load in Snowflake

After files land in ADLS Gen2, use an external stage and `COPY INTO`:

```sql
CREATE OR REPLACE FILE FORMAT UTIL.FF_CSV_GZ
  TYPE=CSV FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1 COMPRESSION=GZIP;

CREATE OR REPLACE STAGE UTIL.PG_STAGE
  URL='azure://<storageacct>.dfs.core.windows.net/<filesystem>/pg_full_load'
  STORAGE_INTEGRATION=AZ_INT
  FILE_FORMAT=UTIL.FF_CSV_GZ;

COPY INTO LANDING.PUBLIC.CUSTOMERS
FROM @UTIL.PG_STAGE
PATTERN='.*public__customers\.csv\.gz'
ON_ERROR='ABORT_STATEMENT';
```

## Troubleshooting tips

* If you see `authorization` errors, verify `azcopy login` (or SAS) has **write** access to the container/path.
* For very wide rows, add `QUOTE '"' ESCAPE '"'` to the CSV options on Postgres if needed.
* For huge tables, consider splitting by ranges (multiple concurrent pipes), each with a distinct destination blob name.

If you share your storage account + filesystem names (and whether you want AAD or SAS), I’ll tailor the loop script exactly to your environment.




# Fastest path (Azure → Snowflake)

## A) One-time / periodic bulk loads (ADLS Gen2 + COPY INTO)

Use ADLS Gen2 as landing, then `COPY INTO` in Snowflake.

1. Export Postgres tables to CSV.gz on a VM/jumpbox (or your Mac)

```bash
# list tables you want
psql "host=<pg-host> dbname=<db> user=<user> password=<pwd> port=5432" -At \
  -c "SELECT schemaname||'.'||tablename
      FROM pg_catalog.pg_tables
      WHERE schemaname IN ('public') ORDER BY 1" > tables.txt

mkdir -p export
while IFS= read -r t; do
  f="export/$(echo "$t" | tr '.' '__').csv.gz"
  echo "Exporting $t -> $f"
  psql -c "\copy (SELECT * FROM $t)
           TO PROGRAM 'gzip > $f'
           WITH (FORMAT csv, HEADER true)"
done < tables.txt
```

2. Upload files to **ADLS Gen2** (hierarchical namespace storage)

```bash
# create a filesystem (container) once
az storage fs create \
  --account-name <storageacct> --name pg_full_load

# upload recursively
az storage fs directory upload \
  --account-name <storageacct> --file-system pg_full_load \
  --source export --destination-path raw --recursive
```

3. Snowflake objects (Azure storage integration + stage + file format)

```sql
-- 3.1: Create an Azure STORAGE INTEGRATION (once, admin step)
CREATE OR REPLACE STORAGE INTEGRATION AZ_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = AZURE
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-tenant-guid>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://<storageacct>.dfs.core.windows.net/pg_full_load');

-- SHOW INTEGRATIONS LIKE 'AZ_INT';  -- copy AZURE_CONSENT_URL to grant permissions in Azure

-- 3.2: File format for CSV.gz
CREATE OR REPLACE FILE FORMAT UTIL.FF_CSV_GZ
  TYPE = CSV
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 1
  COMPRESSION = GZIP;

-- 3.3: External stage pointing to ADLS Gen2
CREATE OR REPLACE STAGE UTIL.PG_STAGE
  URL = 'azure://<storageacct>.dfs.core.windows.net/pg_full_load/raw'
  STORAGE_INTEGRATION = AZ_INT
  FILE_FORMAT = UTIL.FF_CSV_GZ;
```

4. Create target tables and load (per table)

```sql
-- example target
CREATE OR REPLACE TABLE LANDING.PUBLIC.CUSTOMERS (
  ID NUMBER, EMAIL STRING, IS_ACTIVE BOOLEAN,
  CREATED_AT TIMESTAMP_TZ, AMOUNT NUMBER(18,2)
);

-- load using filename pattern
COPY INTO LANDING.PUBLIC.CUSTOMERS
FROM @UTIL.PG_STAGE
PATTERN='.*public__customers.*\.csv\.gz'
ON_ERROR='ABORT_STATEMENT'
FORCE=FALSE;
```

Tip: Put table→pattern pairs in a driver table and generate `COPY` statements for dozens of tables in one go.

---

## B) Ongoing sync (CDC) with **Snowpipe (auto-ingest via Event Grid)**

If you need near-real-time:

1. Produce change files to ADLS (e.g., from Debezium/DMS/Azure Function).
2. Create a **pipe** with `AUTO_INGEST=TRUE`.
3. Hook ADLS container to Snowflake pipe via **Azure Event Grid** (one-time authorization).

```sql
CREATE OR REPLACE PIPE RAW.PUBLIC.CUSTOMERS_PIPE
  AUTO_INGEST = TRUE
  AS
  COPY INTO RAW.PUBLIC.CUSTOMERS_STG
  FROM @UTIL.PG_STAGE/customers_cdc/
  FILE_FORMAT=(FORMAT_NAME=UTIL.FF_JSON)
  ON_ERROR='CONTINUE';
```

Then complete the Event Grid subscription using the `NOTIFICATION_CHANNEL` from:

```sql
DESC PIPE RAW.PUBLIC.CUSTOMERS_PIPE;
```

(You’ll copy the channel ARN-like string into the Event Grid subscription target in Azure.)

Do nightly/hourly **MERGE** from `_STG` to your final table.

---

## C) No-code / low-code options on Azure

* **Azure Data Factory**: Copy Activity (Postgres → ADLS) + Snowflake Copy (linked service). Good for batch/full loads.
* **Fivetran / Airbyte**: Managed CDC Postgres→Snowflake. Fast to set up; recurring cost.

---

# Azure specifics & gotchas

* **Postgres on Azure (Flexible Server)**
  • For CDC, ensure **logical replication** is enabled and your DB params (`wal_level=logical`, etc.) allow Debezium/DMS.
  • For bulk reads, throttle with `work_mem` and `statement_timeout` as needed; export in chunks for very large tables.

* **ADLS Gen2 vs classic Blob**
  Use **DFS endpoint** (`*.dfs.core.windows.net`) for the Snowflake stage URL.
  Confirm hierarchical namespace is ON for Gen2.

* **Snowflake types**
  Map `timestamptz` → `TIMESTAMP_TZ`, `jsonb` → `VARIANT`, `bytea` → `BINARY`. Prefer Parquet for large loads (smaller, faster).

* **Auth**
  Prefer **STORAGE INTEGRATION** (AAD) over SAS. After `CREATE STORAGE INTEGRATION`, follow the consent URL in Azure portal to grant the service principal access to the container.

---

# Quick validation

```sql
-- Row counts
SELECT 'pg.customers' src, COUNT(*) FROM LANDING.PUBLIC.CUSTOMERS;

-- Spot date/tz
SELECT MIN(CREATED_AT), MAX(CREATED_AT) FROM LANDING.PUBLIC.CUSTOMERS;

-- JSON health (if any)
SELECT COUNT(*) FROM LANDING.PUBLIC.CUSTOMERS WHERE TRY_PARSE_JSON(NOTES) IS NULL;
```

---

# Want me to generate everything for you?

Tell me:

* your storage account name + filesystem (container) for ADLS,
* Snowflake account name/role/DB/schema,
* list of schemas/tables (or just the schema),

…and I’ll spit out:

* the `psql` export script (parallelized for big tables),
* `az` upload command tailored to your account,
* `CREATE STORAGE INTEGRATION / STAGE / FILE FORMAT`,
* per-table `CREATE TABLE` + `COPY INTO` statements,
* optional **Snowpipe** + Event Grid wiring steps.



````text
# Copy a lot of PostgreSQL tables into Snowflake — practical playbook

Below are four proven paths, from one-time bulk loads to ongoing CDC. I included ready-to-run snippets (Postgres `psql`, Bash, Snowflake SQL, and a small Python loader), plus gotchas and validation.

---

## Choose your path

1) **One-time / periodic bulk load (files + COPY INTO)**  
   Export tables from Postgres (CSV or Parquet), land in cloud storage (S3/Azure/GCS), load with Snowflake `COPY INTO`.  
   • Fast, cheap, simple.  
   • Best for initial full loads and periodic refreshes.  

2) **Managed pipeline tool (no-code/low-code)**  
   Fivetran / Airbyte / Matillion / Azure Data Factory copy Postgres→Snowflake.  
   • Quick to set up, handles schema drift & CDC (depends on tool).  
   • $$ and vendor lock-in tradeoffs.  

3) **Snowpipe / Snowpipe Streaming + CDC**  
   Stream change events (Debezium or DMS) to storage or directly with Streaming API; Snowpipe auto/near-real-time ingestion.  
   • Best for ongoing synchronization with minimal lag.  
   • More moving parts, but production-grade.

4) **You roll your own code (Python/Spark)**  
   Extract with psycopg2 + PyArrow (Parquet), upload to stage, `COPY INTO`.  
   • Full control, fits custom transforms.  
   • You own reliability & ops.

---

## Option A — Bulk load via files + COPY INTO (recommended baseline)

### 0) Prereqs
- A Snowflake **warehouse** & **role** with `USAGE`/`CREATE STAGE`/`CREATE TABLE`/`INSERT` privs.
- A cloud bucket + Snowflake **external stage** (or use internal stage).
- Network/path for Postgres exports.

### 1) Export all tables from Postgres to CSV (gzip)
List tables, then `\copy` each to a compressed CSV. (Runs client-side; good for large exports.)

```bash
# 1. Get list of tables you want (adjust schemas)
PGDATABASE=mydb PGUSER=postgres PGPASSWORD=*** PGHOST=… PGPORT=5432

psql -At -c "
  SELECT schemaname||'.'||tablename
  FROM pg_catalog.pg_tables
  WHERE schemaname IN ('public')  -- add your schemas
  ORDER BY 1;
" > tables.txt

# 2. Export each table to CSV.gz with headers
mkdir -p export
while IFS= read -r t; do
  f="export/$(echo "$t" | tr '.' '__').csv.gz"
  echo "Exporting $t -> $f"
  psql -c "\copy (SELECT * FROM $t) TO PROGRAM 'gzip > $f' WITH (FORMAT csv, HEADER true)"
done < tables.txt
````

Tip: For very large tables, split by ID ranges or date partitions (parallelizable), e.g.:

```bash
# Example: export in 8 chunks by id ranges
t="public.large_table"
for i in {0..7}; do
  lo=$((i*12500000+1))
  hi=$(((i+1)*12500000))
  f="export/public__large_table_${lo}_${hi}.csv.gz"
  psql -c "\copy (SELECT * FROM $t WHERE id BETWEEN $lo AND $hi) TO PROGRAM 'gzip > $f' WITH (FORMAT csv, HEADER true)" &
done
wait
```

### 2) Upload files to your cloud storage

Pick one:

```bash
# AWS S3
aws s3 sync export/ s3://my-bucket/pg_full_load/

# Azure Blob (ADLS Gen2)
az storage fs directory upload -f myfilesystem -s export --destination-path pg_full_load --account-name mystorage --recursive

# GCS
gsutil -m rsync -r export/ gs://my-bucket/pg_full_load/
```

### 3) Create target tables in Snowflake

Generate Postgres DDL then adapt types (see mapping below). Quick start:

```sql
-- In Snowflake (run once per schema)
CREATE DATABASE IF NOT EXISTS LANDING;
CREATE SCHEMA IF NOT EXISTS LANDING.PUBLIC;

-- Example table (adjust columns/types)
CREATE OR REPLACE TABLE LANDING.PUBLIC.CUSTOMERS (
  ID            NUMBER,
  EMAIL         STRING,
  IS_ACTIVE     BOOLEAN,
  CREATED_AT    TIMESTAMP_TZ,
  AMOUNT        NUMBER(18,2),
  NOTES         STRING
);
```

**Type mapping cheatsheet (Postgres → Snowflake)**

* `integer/bigint` → `NUMBER` (consider explicit precision/scale)
* `serial/bigserial` → `NUMBER` + optional `IDENTITY` in SF
* `numeric(p,s)` → `NUMBER(p,s)`
* `text/varchar` → `STRING`
* `boolean` → `BOOLEAN`
* `timestamp with time zone` → `TIMESTAMP_TZ`
* `timestamp without time zone` → `TIMESTAMP_NTZ`
* `date` → `DATE`
* `bytea` → `BINARY`
* `json/jsonb` → `VARIANT` (then `COPY` with `STRIP_OUTER_ARRAY=TRUE` if needed)

### 4) Create stage + file format + COPY INTO

Use external stage (S3/Azure/GCS) or internal stage. Example with CSV:

```sql
-- File format for CSV.gz
CREATE OR REPLACE FILE FORMAT UTIL.FF_CSV_GZ
  TYPE = CSV
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 1
  COMPRESSION = GZIP;

-- External stage (S3 example)
CREATE OR REPLACE STAGE UTIL.STAGE_PG
  URL = 's3://my-bucket/pg_full_load/'
  STORAGE_INTEGRATION = MY_INT;  -- pre-created integration
  FILE_FORMAT = UTIL.FF_CSV_GZ;

-- Load one table (pattern selects its files)
COPY INTO LANDING.PUBLIC.CUSTOMERS
FROM @UTIL.STAGE_PG
PATTERN='.*public__customers.*\.csv\.gz'
ON_ERROR='ABORT_STATEMENT'
FORCE=FALSE;
```

**Repeat** `COPY INTO` per table (or drive it with a metadata table listing `table_name` + `pattern`). For many tables, generate the SQL:

```sql
-- Example driver table
CREATE OR REPLACE TABLE UTIL.LOAD_MAP(
  tgt_table STRING, pattern STRING
);

INSERT INTO UTIL.LOAD_MAP VALUES
  ('LANDING.PUBLIC.CUSTOMERS', '.*public__customers.*\.csv\.gz'),
  ('LANDING.PUBLIC.ORDERS',    '.*public__orders.*\.csv\.gz');

-- Run all loads (copy-paste generated statements from a SELECT or use Snowflake Scripting)
```

**Variant: Parquet** (smaller & faster loads if you can produce Parquet):

```sql
CREATE OR REPLACE FILE FORMAT UTIL.FF_PARQUET TYPE = PARQUET;

COPY INTO LANDING.PUBLIC.CUSTOMERS
FROM @UTIL.STAGE_PG
FILE_FORMAT = (FORMAT_NAME=UTIL.FF_PARQUET)
MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE
ON_ERROR='CONTINUE';
```

---

## Option B — Ongoing sync (CDC) with Snowpipe / Streaming (advanced)

* **DMS / Debezium → S3/Blob → Snowpipe**:

  1. Enable logical decoding on Postgres, stream CDC to storage as JSON.
  2. Configure **Snowpipe** with auto-ingest (events) to load new files.
  3. Use **MERGE** into target tables (staging → upsert).

* **Debezium → Kafka → Snowpipe Streaming**:
  Push change events directly using Snowflake’s Streaming Ingest SDK; lower latency, fewer files.

**Upsert pattern (table per entity)**:

```sql
MERGE INTO PROD.PUBLIC.CUSTOMERS t
USING STAGE_STAGING.CUSTOMERS_CHANGES s
ON t.ID = s.ID
WHEN MATCHED AND s.op IN ('U','D') THEN
  UPDATE SET EMAIL=s.EMAIL, IS_ACTIVE=s.IS_ACTIVE, UPDATED_AT=CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND s.op='I' THEN
  INSERT (ID, EMAIL, IS_ACTIVE, CREATED_AT) VALUES (s.ID, s.EMAIL, s.IS_ACTIVE, s.CREATED_AT);
```

---

## Option C — Use a managed tool

* **Fivetran / Airbyte / Matillion / ADF**:

  * Pick Postgres connector (enable log-based CDC if you need ongoing updates).
  * Pick Snowflake as destination (warehouse, role, database/schema, staging).
  * Map schemas, schedule or continuous, monitor via UI.
  * Pros: fast setup, schema drift handling; Cons: cost and vendor dependency.

---

## Option D — Python DIY (extract → Parquet → stage → COPY)

Minimal example for one table (extend with a table loop):

```python
# pip install psycopg2-binary pyarrow pandas snowflake-connector-python
import os, pyarrow as pa, pyarrow.parquet as pq, pandas as pd
import psycopg2
import snowflake.connector

PG_CONN = psycopg2.connect("dbname=mydb user=postgres password=*** host=... port=5432")
SF_CONN = snowflake.connector.connect(
    user="ME", password="***", account="xy12345", warehouse="XSMALL", database="LANDING", schema="PUBLIC", role="SYSADMIN"
)

table = "public.customers"
df = pd.read_sql(f"SELECT * FROM {table}", PG_CONN)

# Write Parquet
pq_path = "/tmp/public__customers.parquet"
pq.write_table(pa.Table.from_pandas(df), pq_path)

# Upload to internal stage and COPY (internal stage example)
with SF_CONN.cursor() as cur:
    cur.execute("CREATE OR REPLACE STAGE UTIL_INT_STAGE")
    cur.execute(f"PUT file://{pq_path} @UTIL_INT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
    cur.execute("""
      CREATE OR REPLACE FILE FORMAT UTIL.FF_PARQUET TYPE=PARQUET;
    """)
    cur.execute("""
      COPY INTO LANDING.PUBLIC.CUSTOMERS
      FROM @UTIL_INT_STAGE
      FILE_FORMAT = (FORMAT_NAME=UTIL.FF_PARQUET)
      MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE
      ON_ERROR='CONTINUE';
    """)

SF_CONN.close(); PG_CONN.close()
```

Scale it by looping through a `tables` list, chunked `SELECT`s, and multiprocessing.

---

## Data correctness & validation (do this!)

* **Row counts** (expect minor differences if NULL filtering/trailing newlines):
  Postgres: `SELECT COUNT(*) FROM schema.table;`
  Snowflake: `SELECT COUNT(*) FROM schema.table;`

* **Checksums** (sampled):
  Postgres: `SELECT md5(string_agg(id::text, ',' ORDER BY id)) FROM schema.table WHERE id % 1000 = 0;`
  Snowflake: `SELECT md5(string_agg(TO_VARCHAR(id), ',' ORDER BY id)) FROM schema.table WHERE MOD(id,1000)=0;`

* **Spot check dates/timezones**: ensure `timestamptz` → `TIMESTAMP_TZ` and not silently cast to NTZ.

* **JSON fields**: prefer loading into `VARIANT`, not `STRING`, if you plan to query it.

---

## Common gotchas

* **Identifier case**: Snowflake uppercases unquoted identifiers; either stick to lowercase w/o quotes in both systems, or always quote.
* **NULL vs empty strings**: CSV loads may turn empty into NULL (desired?), configure `EMPTY_FIELD_AS_NULL`.
* **Encoding**: ensure UTF-8 exports; set `ENCODING='UTF8'` on Postgres side if needed.
* **Constraints & indexes**: migrate only what you need; Snowflake doesn’t enforce PK/FK for performance (they’re metadata only).
* **Sequences / serials**: switch to Snowflake `IDENTITY` or keep sequence logic in ETL.
* **Large tables**: parallelize exports; prefer Parquet; increase `WAREHOUSE` size for faster `COPY`.
* **Network egress**: exporting from managed Postgres (cloud) may need VPC peering or dump workers close to DB.

---

## Suggested minimal plan (safe + fast)

1. **Full load** all required tables via CSV.gz (Option A).
2. **Create incremental** pipeline for the top 3 change-heavy tables using Snowpipe or your favorite tool.
3. **Backfill** historical & heavy tables as Parquet (Option D) for speed.
4. Add **validation queries** and a **retryable load script** (idempotent).
5. Schedule loads (cron/Airflow/ADF) and monitor.

If you want, tell me your cloud (AWS/Azure/GCP), approx table list/size, and whether you want CDC. I’ll generate a tailored script set (exports + stage + `COPY` + validation) you can drop in and run.

```
```
