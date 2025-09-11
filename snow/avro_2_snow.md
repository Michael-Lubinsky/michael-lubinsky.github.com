# AVRO -> Snowflake

I configured Azure EventHub Capture with serialization in Avro format on ADLS Gen2.
How to configure automate triggering Snowpipe from ADLS Gen2 on regular bases every 15 minutes?

## Claude
Snowpipe doesn't support direct triggering from ADLS Gen2 on a time-based schedule. 
Snowpipe is designed for event-driven loading when new files arrive, not scheduled batch processing. 
Here are the viable approaches:

## Option 1: Event-Driven Snowpipe (Recommended)
Set up automatic loading when new files arrive:

1. **Create Azure Event Grid subscription** on your storage account
2. **Configure blob creation events** to trigger when Avro files are written
3. **Use Azure Function or Logic App** to call Snowpipe REST API
4. **Files load automatically** as they're captured

```sql
-- Create pipe
CREATE PIPE eventhub_pipe 
AUTO_INGEST = FALSE 
AS COPY INTO events_table 
FROM @eventhub_stage 
FILE_FORMAT = (TYPE = 'AVRO');
```

## Option 2: Scheduled Tasks (Better for 15-minute intervals)
Since you want regular 15-minute intervals, use Snowflake Tasks:

### create stage
Here's how to create the `eventhub_stage` external stage in Snowflake that points to your ADLS Gen2 storage:

### Step 1: Create File Format for Avro
```sql
CREATE OR REPLACE FILE FORMAT avro_format
TYPE = 'AVRO'
COMPRESSION = 'AUTO';
```

### Step 2: Get SAS Token for Azure Storage

Generate a SAS token with read and list permissions:

```bash
az storage container generate-sas \
  --as-user \
  --auth-mode login \
  --account-name weavixdatalakedevsa \
  --name adls \
  --permissions rl \
  --expiry "$(date -u -v+30d '+%Y-%m-%dT%H:%MZ')" \
  --output tsv
```

### Step 3: Create External Stage
```sql
CREATE OR REPLACE STAGE eventhub_stage
URL = 'azure://weavixdatalakedevsa.blob.core.windows.net/adls/weavix-reporting-dev-ehns/telemetry-stream-parallel-hub/'
CREDENTIALS = (
    AZURE_SAS_TOKEN = 'your-sas-token-here'
)
FILE_FORMAT = avro_format;
```

### Step 4: Test the Stage
```sql
-- List files in the stage
LIST @eventhub_stage;

-- Test loading a single file
SELECT $1 FROM @eventhub_stage LIMIT 10;
```

### Step 5: Verify Stage Structure
Based on your previous Event Hub capture path structure:
```
adls/weavix-reporting-dev-ehns/telemetry-stream-parallel-hub/17/2025/09/09/14/34/38.avro
```

You might want to create stages for specific time periods:
```sql
-- Stage for today's data
CREATE OR REPLACE STAGE eventhub_stage_daily
URL = 'azure://weavixdatalakedevsa.blob.core.windows.net/adls/weavix-reporting-dev-ehns/telemetry-stream-parallel-hub/*/2025/09/09/'
CREDENTIALS = (AZURE_SAS_TOKEN = 'your-token')
FILE_FORMAT = avro_format;
```

## Notes:
- Replace `your-sas-token-here` with the actual SAS token
- The URL path should match your Event Hub capture directory structure
- SAS token needs read (`r`) and list (`l`) permissions
- Consider token expiration and rotation strategy

Once created, you can use this stage in your COPY commands or Snowpipe configuration.



```sql
-- Create task that runs every 15 minutes
CREATE TASK load_eventhub_data
WAREHOUSE = 'COMPUTE_WH'
SCHEDULE = 'USING CRON 0,15,30,45 * * * *'
AS
COPY INTO events_table 
FROM @eventhub_stage 
FILE_FORMAT = (TYPE = 'AVRO')
FILES = (SELECT file_name FROM directory(@eventhub_stage) 
         WHERE last_modified > current_timestamp - INTERVAL '16 minutes');

-- Start the task
ALTER TASK load_eventhub_data RESUME;
```

## Option 3: External Orchestration
Use Azure Data Factory or Logic Apps:

1. **Create Logic App** with 15-minute recurrence
2. **Call Snowflake REST API** to execute COPY commands
3. **Handle file tracking** to avoid duplicates

## Recommended Architecture

For your 15-minute requirement, **Option 2 (Snowflake Tasks)** is most appropriate because:
- Native Snowflake scheduling
- Efficient incremental loading
- Built-in error handling and monitoring
- No external dependencies

Event-driven Snowpipe is better for near real-time loading but adds complexity for your scheduled use case.

## ChatGPT

Here’s how you can wire up **Azure Event Hub Capture → ADLS Gen2 (Avro) → Snowflake (Snowpipe)** with a 15-minute refresh cycle:

---

## 1. Understand the flow

* **EventHub Capture** is already dropping Avro files into ADLS Gen2 in folders like:

  ```
  {eventhub_namespace}/{eventhub_name}/{partition_id}/YYYY/MM/DD/HH/mm/
  ```
* Snowpipe has two trigger modes:

  * **Auto-ingest (event notifications):** requires Azure Event Grid integration. This is near real-time but involves more setup.
  * **Scheduled load:** done by a **Snowflake Task** that runs `COPY INTO …` at fixed intervals. This is simpler if you just want *every 15 minutes*.

Since you asked for *regular 15-minute triggers*, I’ll show you the **Task approach**.

---

## 2. Set up the Snowflake external stage (pointing to ADLS Gen2)

```sql
CREATE STAGE my_adls_stage
  URL='azure://<storage-account-name>.dfs.core.windows.net/<container-name>/<eventhub-path>'
  STORAGE_INTEGRATION = my_adls_integration
  FILE_FORMAT = (TYPE = AVRO);
```

* `STORAGE_INTEGRATION` is a Snowflake object that holds the OAuth/AAD credentials to ADLS Gen2.
* `FILE_FORMAT = AVRO` tells Snowflake how to parse your files.

---

## 3. Create the target table (example)

```sql
CREATE OR REPLACE TABLE raw_events (
  data VARIANT
);
```

* With Avro, you often load into a VARIANT column first, then normalize with `SELECT …:field`.

---

## 4. Define the Snowpipe

```sql
CREATE OR REPLACE PIPE my_eventhub_pipe
  AUTO_INGEST = FALSE
  AS
  COPY INTO raw_events
  FROM @my_adls_stage
  FILE_FORMAT = (TYPE = AVRO);
```

* Here `AUTO_INGEST = FALSE` because we’re going to schedule it.
* Pipe tracks what files are already loaded, so you won’t double-load.

---

## 5. Schedule it with a Snowflake Task

```sql
CREATE OR REPLACE TASK run_eventhub_pipe_15min
  WAREHOUSE = my_wh
  SCHEDULE = '15 MINUTE'
AS
  ALTER PIPE my_eventhub_pipe REFRESH;
```

* The task executes every 15 minutes and tells Snowpipe to ingest new files.
* `ALTER PIPE … REFRESH` checks ADLS for new files and ingests them.

---

## 6. Enable the task

```sql
ALTER TASK run_eventhub_pipe_15min RESUME;
```

---

## 7. (Optional) Event-driven auto-ingest

If you want **near real-time ingestion instead of 15-minute batching**, you can integrate **Azure Event Grid** with Snowflake. That requires configuring **event subscriptions** from ADLS to Snowpipe, and Snowflake listens for blob-created events. But that’s more complex than a fixed 15-minute Task.

---

✅ **Summary:**
To automate ingestion every 15 minutes:

1. Create external stage → Pipe → Task.
2. Task runs `ALTER PIPE … REFRESH;` every 15 minutes.
3. Snowpipe ingests any new EventHub Avro files from ADLS.

---

Do you want me to also show you an **end-to-end example with Avro column extraction** (how to flatten `VARIANT` into structured Snowflake columns)? That way your pipeline isn’t just landing raw Avro, but also producing query-ready tables.

