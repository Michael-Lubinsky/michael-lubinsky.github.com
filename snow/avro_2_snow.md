# AVRO -> Snowflake


The timestamp "9/9/2025 2:34:38 PM" is **not** from your original Event Hub event data. This is a **system-generated timestamp** created by Azure Event Hub itself when the event was received and enqueued.

## Where This Timestamp Comes From

**EnqueuedTimeUtc** is automatically added by Azure Event Hub infrastructure when an event arrives. It represents when Event Hub received the event, not when your application created it.

Your original event data is in the `Body` field (the hex-encoded JSON), which contains:
```json
{
  "id": "c9d1f3a1-b5e4-4314-8512-956ece6689b7",
  "originalTimestamp": "Tue Sep 09 2025 14:34:39 GMT+0000 (Coordinated Universal Time)",
  "event": "ChangeStreamTransform",
  "environment": "dev",
  "properties": {...}
}
```

## Event Hub Avro Structure

Event Hub Capture wraps every event in this standard envelope:
- **SequenceNumber**: Event Hub's internal sequence number
- **Offset**: Position in the Event Hub partition
- **EnqueuedTimeUtc**: When Event Hub received it (system time)
- **Body**: Your actual event data (hex-encoded)
- **Properties**: Custom properties from sender
- **SystemProperties**: Event Hub metadata

## Why the Format Difference

The "9/9/2025 2:34:38 PM" format is Azure's default .NET DateTime string representation, which gets serialized into the Avro file. This is different from your application's timestamp format in the Body.

Your application sent the event with `originalTimestamp` in a different format, but Event Hub added its own `EnqueuedTimeUtc` in the standard Azure format.

So you're dealing with two different timestamps:
1. **EnqueuedTimeUtc**: Azure system time (needs format conversion)
2. **originalTimestamp** (in Body): Your application time (after hex decoding)

I configured Azure EventHub Capture with serialization in Avro format on ADLS Gen2.
How to configure automate triggering Snowpipe from ADLS Gen2 on regular bases every 15 minutes?


For automating periodic loads with incremental file processing, you have several options. Here's the most effective approach using Snowflake Tasks:

## Option 1: Snowflake Tasks with Incremental Loading

Create a task that runs every 15-30 minutes and only processes new files:

```sql
-- Create a table to track processed files
CREATE TABLE IF NOT EXISTS eventhub_file_log (
    file_path STRING,
    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    file_size NUMBER,
    rows_loaded NUMBER
);

-- Create the automated task
CREATE OR REPLACE TASK load_eventhub_incremental
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON */15 * * * *'  -- Every 15 minutes
AS
DECLARE
    files_processed NUMBER DEFAULT 0;
BEGIN
    -- Load only new files not in our log
    COPY INTO my_eventhub_events (sequence_number, enqueued_time, offset, event_data)
    FROM (
        SELECT 
            $1:SequenceNumber::NUMBER,
            TO_TIMESTAMP($1:EnqueuedTimeUtc::STRING, 'MM/DD/YYYY HH12:MI:SS AM'),
            $1:Offset::STRING,
            PARSE_JSON(TRY_HEX_DECODE_STRING($1:Body))
        FROM @eventhub_stage
        WHERE metadata$filename NOT IN (
            SELECT file_path FROM eventhub_file_log
        )
    )
    FILE_FORMAT = avro_format
    ON_ERROR = 'CONTINUE';
    
    -- Log processed files
    INSERT INTO eventhub_file_log (file_path, file_size, rows_loaded)
    SELECT 
        metadata$filename,
        metadata$file_size,
        COUNT(*)
    FROM @eventhub_stage
    WHERE metadata$filename NOT IN (
        SELECT file_path FROM eventhub_file_log WHERE processed_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    )
    GROUP BY metadata$filename, metadata$file_size;
    
    RETURN 'Task completed successfully';
END;

-- Start the task
ALTER TASK load_eventhub_incremental RESUME;
```

## Option 2: Time-Based Incremental Loading

```sql
CREATE OR REPLACE TASK load_eventhub_timeboxed
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON */20 * * * *'
AS
BEGIN
    -- Load files from last 25 minutes to handle overlap
    COPY INTO my_eventhub_events (sequence_number, enqueued_time, offset, event_data)
    FROM (
        SELECT 
            $1:SequenceNumber::NUMBER,
            TO_TIMESTAMP($1:EnqueuedTimeUtc::STRING, 'MM/DD/YYYY HH12:MI:SS AM'),
            $1:Offset::STRING,
            PARSE_JSON(TRY_HEX_DECODE_STRING($1:Body))
        FROM @eventhub_stage
        WHERE metadata$file_last_modified > CURRENT_TIMESTAMP - INTERVAL '25 minutes'
    )
    FILE_FORMAT = avro_format
    ON_ERROR = 'CONTINUE';
END;

ALTER TASK load_eventhub_timeboxed RESUME;
```

## Option 3: Dynamic Path-Based Loading

Since your files are organized by date/time, you can target specific time periods:

```sql
CREATE OR REPLACE TASK load_eventhub_hourly
    WAREHOUSE = 'COMPUTE_WH'
    SCHEDULE = 'USING CRON 5 * * * *'  -- 5 minutes past each hour
AS
DECLARE
    current_hour STRING;
    prev_hour STRING;
    pattern_current STRING;
    pattern_prev STRING;
BEGIN
    -- Build patterns for current and previous hour
    SET current_hour = DATE_PART('hour', CURRENT_TIMESTAMP)::STRING;
    SET prev_hour = (DATE_PART('hour', CURRENT_TIMESTAMP) - 1)::STRING;
    
    -- Load from previous hour (should be complete)
    SET pattern_prev = '.*/' || YEAR(CURRENT_TIMESTAMP) || '/' || 
                       LPAD(MONTH(CURRENT_TIMESTAMP), 2, '0') || '/' ||
                       LPAD(DAY(CURRENT_TIMESTAMP), 2, '0') || '/' ||
                       LPAD(prev_hour, 2, '0') || '/.*\\.avro';
    
    COPY INTO my_eventhub_events (sequence_number, enqueued_time, offset, event_data)
    FROM (
        SELECT 
            $1:SequenceNumber::NUMBER,
            TO_TIMESTAMP($1:EnqueuedTimeUtc::STRING, 'MM/DD/YYYY HH12:MI:SS AM'),
            $1:Offset::STRING,
            PARSE_JSON(TRY_HEX_DECODE_STRING($1:Body))
        FROM @eventhub_stage
    )
    FILE_FORMAT = avro_format
    PATTERN = $pattern_prev
    ON_ERROR = 'CONTINUE';
END;

ALTER TASK load_eventhub_hourly RESUME;
```

## Monitoring and Troubleshooting

```sql
-- Check task history
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY()) 
WHERE NAME = 'LOAD_EVENTHUB_INCREMENTAL' 
ORDER BY SCHEDULED_TIME DESC;

-- Check what files have been processed
SELECT * FROM eventhub_file_log ORDER BY processed_timestamp DESC;

-- Manual run for testing
EXECUTE TASK load_eventhub_incremental;
```

I recommend **Option 1** for production use since it tracks processed files and prevents duplicates while handling the hierarchical folder structure automatically.




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
  --expiry "$(date -u -v+7d '+%Y-%m-%dT%H:%MZ')" \
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

### Storage integration

Good question 👍 — a **STORAGE INTEGRATION** in Snowflake is the secure object that holds the trust relationship between Snowflake and your Azure ADLS Gen2 account. It lets Snowflake read/write to ADLS without embedding secrets.

Here’s the step-by-step:

---

## 1. In Snowflake: Create the storage integration

```sql
CREATE OR REPLACE STORAGE INTEGRATION my_adls_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = AZURE
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-guid>'
  STORAGE_ALLOWED_LOCATIONS = (
    'azure://<storage-account-name>.dfs.core.windows.net/<container-name>'
  );
```

**Notes:**

* `AZURE_TENANT_ID`: your Azure AD tenant GUID (you can get it from Azure portal under **Azure Active Directory → Properties → Tenant ID**).
* `STORAGE_ALLOWED_LOCATIONS`: one or more ADLS Gen2 paths that Snowflake can access. Restrict to only what you need for security.

---

## 2. Get the generated **App ID** from Snowflake

After creating, run:

```sql
DESC STORAGE INTEGRATION my_adls_integration;
```

This shows:

* **AZURE\_CONSENT\_URL** → a URL you (an Azure admin) must visit once to grant Snowflake’s service principal access.
* **AZURE\_MULTI\_TENANT\_APP\_NAME** → the Snowflake-managed app you’ll see registered in Azure.

---

## 3. In Azure: Grant Snowflake access

1. An Azure AD admin opens the `AZURE_CONSENT_URL` in a browser and accepts permissions.
2. In your ADLS Gen2 storage account:

   * Go to **Access control (IAM)**.
   * Assign **Storage Blob Data Contributor** role (minimum) to Snowflake’s service principal (the app name from the DESC output).

---

## 4. Back in Snowflake: Create the stage that uses the integration

```sql
CREATE OR REPLACE STAGE my_adls_stage
  URL = 'azure://<storage-account-name>.dfs.core.windows.net/<container-name>/<path>'
  STORAGE_INTEGRATION = my_adls_integration
  FILE_FORMAT = (TYPE = AVRO);
```

Now Snowflake can securely read files from that ADLS path.

---

✅ **Summary**

* Define the `STORAGE_INTEGRATION` in Snowflake (ties to your tenant + allowed containers).
* Approve Snowflake’s service principal in Azure (via consent URL + IAM role assignment).
* Reference the integration when you create stages/pipes.

---

Do you want me to also give you the **Azure CLI commands** to grant Snowflake’s service principal access  
to your ADLS Gen2 container (instead of only showing the portal steps)?

Good question 👍 — a **STORAGE INTEGRATION** in Snowflake is the secure object that holds the trust relationship between Snowflake and your Azure ADLS Gen2 account. It lets Snowflake read/write to ADLS without embedding secrets.

Here’s the step-by-step:

---

## 1. In Snowflake: Create the storage integration

```sql
CREATE OR REPLACE STORAGE INTEGRATION my_adls_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = AZURE
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-guid>'
  STORAGE_ALLOWED_LOCATIONS = (
    'azure://<storage-account-name>.dfs.core.windows.net/<container-name>'
  );
```

**Notes:**

* `AZURE_TENANT_ID`: your Azure AD tenant GUID (you can get it from Azure portal under **Azure Active Directory → Properties → Tenant ID**).
* `STORAGE_ALLOWED_LOCATIONS`: one or more ADLS Gen2 paths that Snowflake can access. Restrict to only what you need for security.

---

## 2. Get the generated **App ID** from Snowflake

After creating, run:

```sql
DESC STORAGE INTEGRATION my_adls_integration;
```

This shows:

* **AZURE\_CONSENT\_URL** → a URL you (an Azure admin) must visit once to grant Snowflake’s service principal access.
* **AZURE\_MULTI\_TENANT\_APP\_NAME** → the Snowflake-managed app you’ll see registered in Azure.

---

## 3. In Azure: Grant Snowflake access

1. An Azure AD admin opens the `AZURE_CONSENT_URL` in a browser and accepts permissions.
2. In your ADLS Gen2 storage account:

   * Go to **Access control (IAM)**.
   * Assign **Storage Blob Data Contributor** role (minimum) to Snowflake’s service principal (the app name from the DESC output).

---

## 4. Back in Snowflake: Create the stage that uses the integration

```sql
CREATE OR REPLACE STAGE my_adls_stage
  URL = 'azure://<storage-account-name>.dfs.core.windows.net/<container-name>/<path>'
  STORAGE_INTEGRATION = my_adls_integration
  FILE_FORMAT = (TYPE = AVRO);
```

Now Snowflake can securely read files from that ADLS path.

---

✅ **Summary**

* Define the `STORAGE_INTEGRATION` in Snowflake (ties to your tenant + allowed containers).
* Approve Snowflake’s service principal in Azure (via consent URL + IAM role assignment).
* Reference the integration when you create stages/pipes.



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

