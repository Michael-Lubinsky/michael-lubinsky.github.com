<https://www.snowflake.com/en/developers/>

<https://www.snowflake.com/en/developers/downloads/>

# Load JSONL from Azure ADLS Gen2 into Snowflake Bronze Tables

There are newline-delimited JSON (JSONL) arriving in Azure ADLS Gen2 under:

```
/root_name/YYYY-MM-DD-HH/*.jsonl
```

### Goal

* Load each JSONL file into a Snowflake table whose name matches the file name (without `.jsonl`).
* Capture the hour folder (`YYYY-MM-DD-HH`) as a column in the destination table.
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

### Azure Token
```
-- Easiest path to start is a SAS token on the stage (rotate regularly).
-- URL form for Azure in Snowflake: azure://<container>@<account>.blob.core.windows.net/<optional/path>
-- Example assumes your JSON is under container “telemetry” at path root_name/
--  >>> IMPORTANT: Put only the *fixed* root here; the per-hour folders stay in the URL path or the COPY paths <<<
CREATE OR REPLACE STAGE weavix.bronze.adls_stage
  URL='azure://telemetry@weavixdatalakedevsa.blob.core.windows.net/root_name'
  CREDENTIALS=(AZURE_SAS_TOKEN='<PASTE_SAS_TOKEN>')  -- or use STORAGE INTEGRATION (recommended long-term)
  FILE_FORMAT = weavix.bronze.ff_jsonl;

-- (Recommended long-term) Replace SAS with a STORAGE INTEGRATION (RBAC, no secrets on stage).
-- You can swap the CREDENTIALS clause for: STORAGE_INTEGRATION = my_azure_integration
```

## 2. One-time Snowflake Setup

```sql
-- Database and schema
CREATE DATABASE IF NOT EXISTS weavix;
CREATE SCHEMA IF NOT EXISTS weavix.bronze;

-- JSONL file format
CREATE OR REPLACE FILE FORMAT weavix.bronze.ff_jsonl
  TYPE = JSON
  STRIP_OUTER_ARRAY = FALSE
  IGNORE_UTF8_ERRORS = TRUE
  COMPRESSION = AUTO;

-- External stage pointing to ADLS Gen2
CREATE OR REPLACE STAGE weavix.bronze.adls_stage
  URL='azure://telemetry@weavixdatalakedevsa.blob.core.windows.net/root_name'
  CREDENTIALS=(AZURE_SAS_TOKEN='<PASTE_SAS_TOKEN>')
  FILE_FORMAT = weavix.bronze.ff_jsonl;

-- Sanity check
LIST @weavix.bronze.adls_stage/2025-09-03-13/;
```

---

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
          REGEXP_SUBSTR(METADATA$FILENAME, ''([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2})''),
          METADATA$FILENAME,
          METADATA$FILE_ROW_NUMBER,
          CURRENT_TIMESTAMP()
        FROM @weavix.bronze.adls_stage (FILE_FORMAT => weavix.bronze.ff_jsonl)
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
CALL weavix.bronze.load_hour_folder('2025-09-03-13');
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
