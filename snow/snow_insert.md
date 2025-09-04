<https://www.snowflake.com/en/developers/>

<https://www.snowflake.com/en/developers/downloads/>

# Load JSONL from Azure ADLS Gen2 into Snowflake Bronze Tables

There are newline-delimited JSON (JSONL) arriving in Azure ADLS Gen2 under:

```
/root_name/YYYY/MM/DD/HH/*.jsonl
```

### Goal

* Load each JSONL file into a Snowflake table whose name matches the file name (without `.jsonl`).
* Capture the hour folder (`YYYY/MM/DD/HH`) as a column in the destination table.
* Auto-create the table if it doesn’t exist.

---

## 1. What to Install on Mac

You do **not** install `COPY` or `Snowpipe` locally—those are Snowflake features.

Install these tools:

* **SnowSQL CLI** – run SQL from your Mac
   SnowSQL  <https://developers.snowflake.com/snowsql/>
* **(Optional) Snowflake CLI** – newer multi-command tool  <https://developers.snowflake.com/cli/>
* **(Optional) SDK** for automation

  * Node.js: `snowflake-sdk`
  * Python: `snowflake-connector-python`
* **Azure CLI** – if you need to mint SAS tokens

  ```bash
  brew install azure-cli
  ```

### Azure SAS Token
```
-- Easiest path to start is a SAS token on the stage (rotate regularly).
-- URL form for Azure in Snowflake: azure://<container>@<account>.blob.core.windows.net/<optional/path>
-- Example assumes your JSON is under container “telemetry” at path root_name/
--  >>> IMPORTANT: Put only the *fixed* root here; the per-hour folders stay in the URL path or the COPY paths <<<
CREATE OR REPLACE STAGE weavix.bronze.adls_stage
  URL='azure://weavixdatalakedevsa.blob.core.windows.net/<blobstorage>'
  CREDENTIALS=(AZURE_SAS_TOKEN='<PASTE_SAS_TOKEN>')  -- or use STORAGE INTEGRATION (recommended long-term)
  FILE_FORMAT = weavix.bronze.ff_jsonl;

-- (Recommended long-term) Replace SAS with a STORAGE INTEGRATION (RBAC, no secrets on stage).
-- You can swap the CREDENTIALS clause for: STORAGE_INTEGRATION = my_azure_integration
```


Not quite 🙂 — the command you showed:

```bash
az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv
```

generates an **Azure Active Directory (AAD) access token**, not a **SAS token**.

---

## Difference

* **AAD Access Token**

  * Short-lived OAuth2 token (JWT).
  * Used for authenticating against Azure services that support Azure AD directly (e.g., Azure Database for PostgreSQL, Azure SQL, ARM APIs).
  * Works only for a few minutes (usually 1 hour).
  * Returned by `az account get-access-token`.

* **SAS Token (Shared Access Signature)**

  * A signed query string you append to a **storage URL**.
  * Grants scoped access (read/write/list/etc.) to blobs, containers, or directories in **Azure Storage** (including ADLS Gen2).
  * Lifetime and permissions are defined when you create it.
  * Generated using `az storage` commands (or the Portal).

---

## Example: Generate a SAS token for ADLS Gen2

### Container-level SAS (read + list)

```bash
az storage container generate-sas \
  --account-name weavixdatalakedevsa \
  --name telemetry \
  --permissions rl \
  --expiry 2025-09-05T00:00Z \
  --auth-mode login \
  --as-user
```

This returns just the SAS string (e.g., `sv=...&ss=...&sig=...`).
You then append it to your container URL:

```
https://weavixdatalakedevsa.blob.core.windows.net/telemetry?<SAS_TOKEN>
```

---

## When to use each

* Use **AAD access tokens** if you’re calling ARM APIs or databases with AAD auth.
* Use **SAS tokens** when you need Snowflake, Databricks, or some external app to fetch files from ADLS Gen2 without storing account keys.

---

👉 Do you want me to give you a **ready-to-use CLI command** to generate a SAS token specifically for your `/root_name/YYYY/MM/DD/HH/` folder in ADLS Gen2?


Perfect 👍 Let’s make this concrete for your case: you want a **SAS token** that Snowflake can use to read JSONL files from a **specific ADLS Gen2 folder**:

```
/root_name/YYYY-MM-DD-HH/
```

in your storage account `weavixdatalakedevsa`, container `telemetry`.

---

## 1. Generate SAS token with Azure CLI

### Command



```bash
az storage container generate-sas \
  --account-name weavixdatalakedevsa \
  --name telemetry \
  --permissions rl \
  --expiry 2025-10-30T00:00Z \
  --https-only \
  --auth-mode login \
  --as-user
```

incorrect usage: --expiry should be within 7 days from now

## Explanation  
* --permissions rl → read and list (enough for Snowflake COPY INTO).

* --expiry → set when the token should expire. Here it’s valid until Sept 5, 2025 (UTC). Adjust as needed.

* --https-only → ensures token works only over HTTPS.

*  --auth-mode login → uses your logged-in Azure CLI identity.
* `--auth-mode login` → use your signed-in Azure AD identity (instead of storage account key).
* `--as-user` → tells Azure to issue a **user delegation SAS**, which works with ADLS Gen2.
* Without `--as-user`, the CLI expects you to provide an **account key** or **connection string** instead.

---

## Alternative (if you don’t want `--as-user`)

You can also generate a SAS with the **account key**:

```bash
az storage container generate-sas \
  --account-name weavixdatalakedevsa \
  --name telemetry \
  --permissions rl \
  --expiry 2025-10-30T00:00Z \
  --https-only \
  --account-key "$(az storage account keys list --account-name weavixdatalakedevsa --query '[0].value' -o tsv)"
```

This version uses the storage account key, so you don’t need `--auth-mode login` or `--as-user`. But in general, **user delegation SAS** (`--as-user`) is more secure if you’re on RBAC.

---

👉 Do you want me to show you how to **scope the SAS token to a specific subfolder** (like `/root_name/2025/09/03/13/`) so it doesn’t expose the whole container?

This returns just the **SAS query string**, e.g.:

```
sv=2022-11-02&ss=b&srt=sco&sp=rl&se=2025-09-05T00:00Z&st=2025-09-03T00:00Z&spr=https&sig=abc123...
```

---

## 2. Construct full SAS URL for Snowflake

Combine your container URL with the SAS string:

```
https://weavixdatalakedevsa.blob.core.windows.net/telemetry/root_name/YYYY-MM-DD-HH?<SAS_TOKEN>
```

Example:

```
https://weavixdatalakedevsa.blob.core.windows.net/telemetry/root_name/2025-09-03-13?sv=2022-11-02&ss=b...&sig=abc123
```

---

## 3. Use in Snowflake stage

```sql
CREATE OR REPLACE STAGE weavix.events.adls_stage_hour
  URL='azure://weavixdatalakedevsa.blob.core.windows.net/telemetry'
  CREDENTIALS=(AZURE_SAS_TOKEN='sv=2022-11-02&ss=b...&sig=abc123')
  FILE_FORMAT = weavix.bronze.ff_jsonl;
```

Now Snowflake can `LIST` and `COPY INTO` from that folder.

---

⚠️ Notes:

* If you want the SAS to cover **all hour folders**, generate it at the container or `/root_name/` level instead of `/root_name/YYYY/MM/DD/HH/`.
* SAS tokens are **secrets**: don’t commit them to GitHub or share publicly.
* For production, a **Storage Integration** (Snowflake ↔ Azure AD RBAC) is more secure than SAS.

---

 


## 2. One-time Snowflake Setup

```sql
-- Database and schema
CREATE DATABASE IF NOT EXISTS weavix;
CREATE SCHEMA IF NOT EXISTS weavix.events;

-- JSONL file format
CREATE OR REPLACE FILE FORMAT weavix.events.ff_jsonl
  TYPE = JSON
  STRIP_OUTER_ARRAY = FALSE
  IGNORE_UTF8_ERRORS = TRUE
  COMPRESSION = AUTO;

-- External stage pointing to ADLS Gen2
CREATE OR REPLACE STAGE weavix.events.telemetry_stage
  URL='azure://weavixdatalakedevsa.blob.core.windows.net/telemetry'
  CREDENTIALS=(AZURE_SAS_TOKEN='<PASTE_SAS_TOKEN>')
  FILE_FORMAT = weavix.events.ff_jsonl;

-- Sanity check
LIST @weavix.bronze.telemetry_stage/2025/09/03/13/;

LIST @weavix.bronze.telemetry_stage/2025/09/03/17/;

LIST @weavix.bronze.telemetry_stage/2025/09/03/17/ PATTERN='.*\.jsonl';

LIST @weavix.bronze.telemetry_stage;
```
--------------
--- CLAUDE
-------------

## Key Features:

1. **Dynamic Path Handling**: Takes a path parameter in 'YYYY/MM/DD/HH' format and lists all `.jsonl` files in that directory.

2. **Automatic Table Creation**: For each JSONL file found, it creates a table with the same name (minus the `.jsonl` extension) if it doesn't exist.

3. **Flexible Schema**: Each created table has:
   - `load_timestamp`: Automatic timestamp when data was loaded
   - `load_path`: The folder path being processed (for audit/tracking)
   - `raw_data`: VARIANT column to store the JSON data

4. **Error Handling**: Uses `ON_ERROR = 'CONTINUE'` to skip malformed records rather than failing the entire load.

5. **Return Results**: Returns a table showing the number of records inserted per table.

## Usage Example:

```sql
-- Load data from the specified hour
CALL weavix.events.load_hour('2025/09/03/17');

-- This will process all .jsonl files in:
-- @weavix.events.telemetry_stage/2025/09/03/17/
```

## Table Structure:

For each JSONL file (e.g., `user_events.jsonl`), a table `weavix.events.user_events` will be created with:
- Metadata columns for tracking when and from where data was loaded
- Raw JSON data stored in a VARIANT column for flexible querying

## Notes:

1. **Fixed Stage Reference**: I noticed your `LIST` command has a typo (`weavix.event.telemetry_stage` instead of `weavix.events.telemetry_stage`). The procedure uses the correct reference.

2. **JSON Querying**: Once loaded, you can query the JSON data using Snowflake's JSON functions:
   ```sql
   SELECT raw_data:user_id, raw_data:event_type, load_path
   FROM weavix.events.user_events
   WHERE load_path = '2025/09/03/17';
   ```

3. **Scalability**: The procedure processes files one by one, which is good for error isolation but may be slower for very large numbers of files.

The procedure will return a result set showing how many records were loaded into each table, making it easy to verify the load results.

-----------------------------------
```sql
CREATE OR REPLACE PROCEDURE weavix.events.load_hour(path STRING)
RETURNS TABLE (table_name STRING, records_inserted NUMBER)
LANGUAGE SQL
AS
$$
DECLARE
    file_cursor CURSOR FOR 
        SELECT DISTINCT REGEXP_SUBSTR("name", '[^/]+(?=\\.jsonl$)') AS table_name,
               "name" AS file_path
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
        WHERE "name" LIKE '%.jsonl';
    
    table_name_var STRING;
    file_path_var STRING;
    create_table_sql STRING;
    copy_sql STRING;
    records_count NUMBER;
    results TABLE (table_name STRING, records_inserted NUMBER);
    stage_path STRING;
BEGIN
    -- Initialize results table
    results := TABLE(SELECT '' AS table_name, 0 AS records_inserted WHERE FALSE);
    
    -- Construct the full stage path
    stage_path := '@weavix.events.telemetry_stage/' || path || '/';
    
    -- List files in the specified path
    EXECUTE IMMEDIATE 'LIST ' || stage_path || ' PATTERN=''.*\\.jsonl''';
    
    -- Open cursor to iterate through files
    OPEN file_cursor;
    
    FOR record IN file_cursor DO
        table_name_var := record.table_name;
        file_path_var := record.file_path;
        
        -- Skip if table name is null (shouldn't happen with our regex, but safety check)
        IF (table_name_var IS NULL OR table_name_var = '') THEN
            CONTINUE;
        END IF;
        
        -- Create table if it doesn't exist
        -- Using a flexible schema that can handle any JSON structure
        create_table_sql := 'CREATE TABLE IF NOT EXISTS weavix.events.' || table_name_var || ' ('
                         || 'load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), '
                         || 'load_path STRING, '
                         || 'raw_data VARIANT'
                         || ')';
        
        EXECUTE IMMEDIATE create_table_sql;
        
        -- Copy data from the specific file
        copy_sql := 'COPY INTO weavix.events.' || table_name_var || ' (load_path, raw_data) '
                 || 'FROM ('
                 || '  SELECT ''' || path || ''', $1 '
                 || '  FROM @weavix.events.telemetry_stage/' || file_path_var
                 || ') '
                 || 'FILE_FORMAT = weavix.events.ff_jsonl '
                 || 'ON_ERROR = ''CONTINUE''';
        
        EXECUTE IMMEDIATE copy_sql;
        
        -- Get the number of records inserted from the last COPY command
        SELECT "rows_loaded" INTO records_count 
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) 
        WHERE "rows_loaded" IS NOT NULL 
        LIMIT 1;
        
        -- Add result to our results table
        results := results UNION ALL 
                  SELECT table_name_var, NVL(records_count, 0);
        
    END FOR;
    
    CLOSE file_cursor;
    
    -- Return the results
    RETURN TABLE(results);
    
EXCEPTION
    WHEN OTHER THEN
        -- Close cursor if still open
        IF (file_cursor%ISOPEN) THEN
            CLOSE file_cursor;
        END IF;
        
        -- Re-raise the exception with context
        RAISE;
END;
$$;








```
---------------------------------

## 3. Auto-Creating Tables and Loading

Each table will have this structure:

```sql
payload          VARIANT,
hour_folder      STRING,
file_name        STRING,
file_row_number  NUMBER,
loaded_at        TIMESTAMP_NTZ
```

Procedure:

```sql
CREATE OR REPLACE PROCEDURE weavix.bronze.load_hour_folder(hour_str STRING)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_prefix STRING DEFAULT hour_str || '/';
  v_tab    STRING;
  v_stmt   STRING;
BEGIN
  CREATE OR REPLACE TEMP TABLE t_files AS
  SELECT REGEXP_SUBSTR(name, '[^/]+$') AS base_name, name AS full_name
  FROM TABLE(LIST(@weavix.bronze.adls_stage/:v_prefix));

  FOR rec IN (SELECT base_name, full_name FROM t_files WHERE base_name ILIKE '%.jsonl') DO
    v_tab := LOWER(REGEXP_REPLACE(REGEXP_REPLACE(rec.base_name, '\\.jsonl$', ''), '[-\\.]', '_'));

    v_stmt := '
      CREATE TABLE IF NOT EXISTS weavix.bronze.' || IDENTIFIER(v_tab) || ' (
        payload VARIANT,
        hour_folder STRING,
        file_name STRING,
        file_row_number NUMBER,
        loaded_at TIMESTAMP_NTZ
      )';
    EXECUTE IMMEDIATE v_stmt;

    v_stmt := '
      COPY INTO weavix.bronze.' || IDENTIFIER(v_tab) || ' (payload, hour_folder, file_name, file_row_number, loaded_at)
      FROM (
        SELECT
          $1,
          REGEXP_SUBSTR(METADATA$FILENAME, ''([0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9]{2})''),
          METADATA$FILENAME,
          METADATA$FILE_ROW_NUMBER,
          CURRENT_TIMESTAMP()
        FROM @weavix.bronze.telemetry_stage (FILE_FORMAT => weavix.bronze.ff_jsonl)
        WHERE METADATA$FILENAME ILIKE ''%' || :v_prefix || rec.base_name || '''
      )
      ON_ERROR = ''ABORT_STATEMENT''
      FORCE = FALSE';
    EXECUTE IMMEDIATE v_stmt;
  END FOR;

  RETURN 'Loaded hour folder ' || hour_str;
END;
$$;
```

Run it:

```sql
CALL weavix.bronze.load_hour_folder('2025/09/03/13');
```

---

## 4. Automate Hourly with Tasks

```sql
CREATE OR REPLACE PROCEDURE weavix.bronze.run_prev_hour()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE v_hour STRING;
BEGIN
  SELECT TO_VARCHAR(DATEADD(hour, -1, DATE_TRUNC(hour, CURRENT_TIMESTAMP())), 'YYYY-MM-DD-HH')
  INTO :v_hour;
  RETURN weavix.bronze.load_hour_folder(:v_hour);
END;
$$;

CREATE OR REPLACE TASK weavix.bronze.t_load_jsonl_hourly
  WAREHOUSE = <YOUR_WAREHOUSE>
  SCHEDULE = 'USING CRON 10 * * * * UTC'
AS
CALL weavix.bronze.run_prev_hour();

ALTER TASK weavix.bronze.t_load_jsonl_hourly RESUME;
```

---

## 5. When to Use Snowpipe

* **Good for:** auto-ingesting into a **single fixed table**.
* **Not good for:** dynamically creating one table per file.
* If you’re okay with one target table per topic/collection, Snowpipe is ideal.

---

## 6. Quick Run from SnowSQL

```bash
snowsql -a <ACCOUNT> -u <USER> -w <WAREHOUSE> -q "
  USE DATABASE weavix;
  USE SCHEMA bronze;
  CALL weavix.bronze.load_hour_folder('2025-09-03-13');
"
```

---

## 7. Tips

* `LIST @stage/hour/` to verify Snowflake sees files.
* Keep JSON as `VARIANT` until you know the schema.
* Use `(file_name, file_row_number)` as unique keys if needed.

---

✅ With this setup, you can ingest JSONL from ADLS Gen2 into Snowflake Bronze tables, auto-creating per-file tables, capturing the folder hour, and running it all directly from your MacBook.

---

Do you want me to also show you the **Snowpipe version** (single target table) so you can compare trade-offs?
