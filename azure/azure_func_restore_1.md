Here’s a ready-to-run **Azure Function (Python, HTTP trigger)** that restores a compressed daily CSV (`*.csv.gz`) from **ADLS Gen2** into a **Postgres/TimescaleDB** table.

It:

* Parses the ADLS URL and filename convention `database/schema.table.YYYY-MM-DD.csv.gz`.
* Derives `database`, `schema`, `table`, and the `date` window to (optionally) decompress/recompress the corresponding chunk.
* Streams the blob, **decompresses gzip**, buffers into a `SpooledTemporaryFile` (spills to disk past a threshold), reads the CSV header to get the column list, then `COPY ... FROM STDIN` into the destination table.
* Supports:

  * Loading **directly into the existing hypertable** (default), or
  * Loading into a **new staging table** (created `UNLOGGED LIKE target INCLUDING ALL`) and then inserting into the target.
* Uses `SET LOCAL timescaledb.restoring = on` during the load.
* Optional: **decompress/recompress** the affected chunk window (based on the date in the filename) and **refresh** specified CAGGs afterwards.

---

# Project layout

```
functions-restore-chunk/
├─ host.json
├─ local.settings.json            # for local testing (Do NOT commit secrets)
├─ requirements.txt
└─ RestoreChunk/
   ├─ __init__.py                 # Azure Function entrypoint
   └─ function.json
```

---

# `requirements.txt`

```text
azure-functions
azure-identity>=1.16.0
azure-storage-file-datalake>=12.14.1
psycopg2-binary>=2.9.9
python-dateutil>=2.9.0
```

---

# `RestoreChunk/function.json`

```json
{
  "bindings": [
    {
      "authLevel": "function",
      "direction": "in",
      "methods": [ "post" ],
      "name": "req",
      "type": "httpTrigger",
      "route": "restore"
    },
    {
      "direction": "out",
      "name": "$return",
      "type": "http"
    }
  ],
  "scriptFile": "__init__.py"
}
```

---

# `host.json`

```json
{
  "version": "2.0",
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

---

# `local.settings.json` (sample — for local only)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    // If using Managed Identity on Azure, you typically don't need these locally.
    // Provide developer creds via az login or env vars as needed.

    // Optional defaults:
    "ADLS_ACCOUNT_URL_DEFAULT": "https://<account>.dfs.core.windows.net",
    "ADLS_FILESYSTEM_DEFAULT": "<filesystem>"
  }
}
```

---

# HTTP request schema

POST `/api/restore` with JSON body:

```json
{
  "pg": {
    "host": "my-pg.postgres.database.azure.com",
    "port": 5432,
    "user": "user@domain",
    "password": "*****",                  // or use "connection_uri": "postgresql://..."
    "sslmode": "require",
    "database": null                      // optional; if null we derive from path
  },
  "adls_url": "abfss://fs@account.dfs.core.windows.net/backups/weavix/silver/schema.table.2025-01-01.csv.gz",
  "destination": {
    "mode": "direct|staging",             // default: "direct"
    "target_table": null,                 // default: derived from filename -> schema.table
    "create_staging_like": null           // when mode=staging: e.g. "schema.table" to clone
  },
  "timescaledb": {
    "decompress_window": true,            // default: true
    "recompress_window": true,            // default: true
    "refresh_caggs": [                    // optional list of CAGG names to refresh
      "schema.my_cagg"
    ]
  },
  "copy": {
    "csv_options": {                      // optional COPY CSV options
      "HEADER": true,
      "DELIMITER": ",",
      "NULL": "",
      "QUOTE": "\""
    },
    "synchronous_commit_off": true        // default: true
  }
}
```

* `adls_url` accepts `abfss://` or `https://` style URLs.
* File path must follow `.../<database>/<schema>.<table>.<YYYY-MM-DD>.csv.gz`.

---

# `RestoreChunk/__init__.py`

```python
import azure.functions as func
import logging
import os
import re
import io
import json
import tempfile
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

# ---------- Helpers ----------

FILENAME_RE = re.compile(
    r'(?P<schema>[^./]+)\.(?P<table>[^./]+)\.(?P<date>\d{4}-\d{2}-\d{2})\.csv\.gz$'
)

def parse_adls_url(adls_url: str):
    """
    Parse abfss://filesystem@account.dfs.core.windows.net/path/database/schema.table.YYYY-MM-DD.csv.gz
    or https://account.dfs.core.windows.net/filesystem/path/...
    Returns: (account_url, filesystem, path, database, schema, table, date_str)
    """
    u = urlparse(adls_url)
    if u.scheme not in ("abfss", "https"):
        raise ValueError(f"Unsupported URL scheme: {u.scheme}")

    if u.scheme == "abfss":
        # abfss://<filesystem>@<account>.dfs.core.windows.net/<path>
        if not u.netloc or '@' not in u.netloc:
            raise ValueError("abfss URL must be like abfss://<fs>@<account>.dfs.core.windows.net/<path>")
        filesystem, account_host = u.netloc.split("@", 1)
        account_url = f"https://{account_host}"
        # strip leading "/"
        path = u.path.lstrip("/")
    else:
        # https://<account>.dfs.core.windows.net/<filesystem>/<path>
        parts = u.path.lstrip("/").split("/", 1)
        if len(parts) < 2:
            raise ValueError("https URL must be like https://<account>.dfs.core.windows.net/<fs>/<path>")
        filesystem, path = parts
        account_url = f"{u.scheme}://{u.netloc}"

    # Expect path like: backups/<database>/<schema.table.YYYY-MM-DD.csv.gz>
    segments = path.split("/")
    if len(segments) < 2:
        raise ValueError("Path must contain at least '<database>/<schema.table.YYYY-MM-DD.csv.gz>'")

    database = segments[-2]
    filename = segments[-1]
    m = FILENAME_RE.search(filename)
    if not m:
        raise ValueError("Filename must match 'schema.table.YYYY-MM-DD.csv.gz'")

    schema = m.group("schema")
    table = m.group("table")
    date_str = m.group("date")

    return account_url, filesystem, path, database, schema, table, date_str

def build_pg_conn(pg_cfg: dict, derived_db: str):
    # Allow connection_uri shortcut
    if "connection_uri" in pg_cfg and pg_cfg["connection_uri"]:
        return psycopg2.connect(pg_cfg["connection_uri"])

    host = pg_cfg["host"]
    port = pg_cfg.get("port", 5432)
    user = pg_cfg["user"]
    password = pg_cfg.get("password")
    sslmode = pg_cfg.get("sslmode", "require")
    database = pg_cfg.get("database") or derived_db

    dsn = f"host={host} port={port} user={user} dbname={database} sslmode={sslmode}"
    if password:
        dsn += f" password={password}"
    return psycopg2.connect(dsn)

def download_gz_to_spooled_temp(file_client, spool_threshold=100*1024*1024):
    """
    Stream-download ADLS file into a SpooledTemporaryFile (in memory until threshold),
    then return handle positioned at start (decompressed text in a second step).
    """
    downloader = file_client.download_file()  # StorageStreamDownloader-like
    # We'll write the *compressed* bytes first, then wrap with gzip for a second pass.
    spooled = tempfile.SpooledTemporaryFile(max_size=spool_threshold, mode="w+b")
    for chunk in downloader.chunks():
        spooled.write(chunk)
    spooled.seek(0)
    return spooled  # compressed bytes

def gunzip_to_spooled_csv(gz_fp, spool_threshold=100*1024*1024):
    """
    Decompress gz_fp (file-like, positioned at start) into a new SpooledTemporaryFile containing CSV bytes.
    Returns (csv_fp, header_columns)
    """
    import gzip
    csv_fp = tempfile.SpooledTemporaryFile(max_size=spool_threshold, mode="w+b")
    with gzip.GzipFile(fileobj=gz_fp, mode="rb") as gzf:
        # We need to read the first line (header) to get columns, but also preserve the full stream.
        # So copy all bytes to csv_fp and also capture the first line along the way.
        header_line = None
        # Efficient copy in chunks while detecting the first line
        buf = b""
        first_chunk = True
        while True:
            chunk = gzf.read(1024 * 1024)
            if not chunk:
                break
            if first_chunk:
                # try to split header from the first chunk (or concatenated buffers)
                buf += chunk
                nl = buf.find(b"\n")
                if nl != -1:
                    header_line = buf[:nl].decode("utf-8").rstrip("\r\n")
                    # write full buffer to csv_fp (we want the whole file with header)
                    csv_fp.write(buf)
                    buf = b""
                    first_chunk = False
                # else keep accumulating until we find newline (pathological long header)
            else:
                csv_fp.write(chunk)
        if first_chunk:
            # the whole file had no newline? treat entire buf as header anyway
            header_line = buf.decode("utf-8").rstrip("\r\n")
            csv_fp.write(buf)

    if header_line is None:
        raise ValueError("Unable to read CSV header from gzip")

    # Parse CSV header into column list (simple split respecting common quotes)
    # For robustness, use Python csv.reader on the single header line
    import csv as pycsv
    cols = next(pycsv.reader([header_line]))
    cols = [c.strip() for c in cols]

    csv_fp.seek(0)
    return csv_fp, cols

def quote_ident(name: str) -> str:
    # Minimal quoting; for full safety you might use psycopg2.sql, but here we build COPY text.
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        return name
    return '"' + name.replace('"', '""') + '"'

def build_copy_sql(full_table: str, columns: list, csv_options: dict) -> str:
    collist = ", ".join(quote_ident(c) for c in columns)
    opts = {"FORMAT": "csv", "HEADER": True}
    if csv_options:
        opts.update(csv_options)

    # Normalize boolean options to lowercase true/false
    def fmt_val(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        # Quote strings if they contain special chars or spaces
        s = str(v)
        if re.search(r'[\s,()\'"]', s):
            # single-quote and escape internal single quotes
            return "'" + s.replace("'", "''") + "'"
        return s

    optlist = ", ".join(f"{k} {fmt_val(v)}" for k, v in opts.items())
    return f"COPY {full_table} ({collist}) FROM STDIN WITH ({optlist})"

def parse_destination_table(destination_cfg: dict, derived_schema: str, derived_table: str):
    mode = (destination_cfg or {}).get("mode", "direct")
    target_table = (destination_cfg or {}).get("target_table")
    if not target_table:
        target_table = f"{derived_schema}.{derived_table}"
    create_like = (destination_cfg or {}).get("create_staging_like")  # for staging mode
    return mode, target_table, create_like

def get_time_window(date_str: str):
    # interpret as date in UTC (window [date, date+1))
    day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return day, day + timedelta(days=1)

# ---------- Azure Function ----------

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    try:
        adls_url = body["adls_url"]
        pg_cfg = body["pg"]
    except KeyError as e:
        return func.HttpResponse(f"Missing required field: {e}", status_code=400)

    destination_cfg = body.get("destination", {})
    tsdb_cfg = body.get("timescaledb", {})
    copy_cfg = body.get("copy", {})

    try:
        account_url, filesystem, path, derived_db, schema, table, date_str = parse_adls_url(adls_url)
    except Exception as e:
        logging.exception("Failed to parse ADLS URL")
        return func.HttpResponse(f"Bad adls_url: {e}", status_code=400)

    mode, target_table, create_like = parse_destination_table(destination_cfg, schema, table)
    decompress_window = tsdb_cfg.get("decompress_window", True)
    recompress_window = tsdb_cfg.get("recompress_window", True)
    refresh_caggs = tsdb_cfg.get("refresh_caggs", []) or []
    sync_off = copy_cfg.get("synchronous_commit_off", True)
    csv_options = (copy_cfg.get("csv_options") or {})
    header_flag = csv_options.get("HEADER", True)
    if not header_flag:
        # We rely on reading the header to build column list; enforce HEADER
        csv_options["HEADER"] = True

    # ADLS auth (Managed Identity / developer creds)
    cred = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    dls = DataLakeServiceClient(account_url=account_url, credential=cred)
    file_system_client = dls.get_file_system_client(filesystem)
    file_client = file_system_client.get_file_client(path)

    # Download compressed, then gunzip to CSV in a spooled temp file
    try:
        gz_fp = download_gz_to_spooled_temp(file_client)
        csv_fp, columns = gunzip_to_spooled_csv(gz_fp)
    except Exception as e:
        logging.exception("Failed to download/decompress file")
        return func.HttpResponse(f"Download/decompress error: {e}", status_code=500)

    # Connect to Postgres (db may be derived from path)
    try:
        conn = build_pg_conn(pg_cfg, derived_db)
        conn.autocommit = False
    except Exception as e:
        logging.exception("Failed to connect to Postgres")
        return func.HttpResponse(f"Postgres connect error: {e}", status_code=500)

    start_ts, end_ts = get_time_window(date_str)

    try:
        with conn, conn.cursor() as cur:
            # Preparation: resolve actual destination and (optionally) staging
            if mode == "staging":
                if not create_like:
                    # default: clone target table
                    create_like = target_table
                staging_table = f"{schema}.{table}_staging_{date_str.replace('-', '')}"
                cur.execute(f'CREATE UNLOGGED TABLE {staging_table} (LIKE {create_like} INCLUDING ALL);')
                dest_table_for_copy = staging_table
            else:
                dest_table_for_copy = target_table

            # Optional: decompress target chunk window (best-effort)
            if decompress_window:
                try:
                    cur.execute(
                        """
                        SELECT decompress_chunk(c)
                        FROM show_chunks(%s, newer_than => %s, older_than => %s) c
                        """,
                        (target_table, start_ts, end_ts)
                    )
                except Exception as de:
                    logging.warning(f"decompress_chunk warning (continuing): {de}")

            # COPY from CSV stream
            copy_sql = build_copy_sql(dest_table_for_copy, columns, csv_options)
            if sync_off:
                cur.execute("SET LOCAL synchronous_commit = off;")
            # Avoid immediate invalidations/overhead during bulk load
            cur.execute("SET LOCAL timescaledb.restoring = on;")

            # psycopg2 copy_expert expects a file-like object positioned at start
            csv_fp.seek(0)
            cur.copy_expert(copy_sql, csv_fp)

            if mode == "staging":
                # Insert into target; dedupe optional — here we simple append.
                # If you have a PK/unique index, use ON CONFLICT DO NOTHING.
                cols_ql = ", ".join(quote_ident(c) for c in columns)
                cur.execute(
                    f"INSERT INTO {target_table} ({cols_ql}) SELECT {cols_ql} FROM {dest_table_for_copy} ON CONFLICT DO NOTHING;"
                )
                cur.execute(f"DROP TABLE {dest_table_for_copy};")

            # Optional: recompress target chunk window
            if recompress_window:
                try:
                    cur.execute(
                        """
                        SELECT compress_chunk(c)
                        FROM show_chunks(%s, newer_than => %s, older_than => %s) c
                        """,
                        (target_table, start_ts, end_ts)
                    )
                except Exception as ce:
                    logging.warning(f"compress_chunk warning (continuing): {ce}")

            # Optional: refresh specified CAGGs for the day window
            for cagg in refresh_caggs:
                try:
                    cur.execute(
                        "CALL refresh_continuous_aggregate(%s, %s, %s);",
                        (cagg, start_ts, end_ts)
                    )
                except Exception as re:
                    logging.warning(f"refresh CAGG {cagg} warning (continuing): {re}")

        conn.commit()

    except Exception as e:
        logging.exception("Load failed; rolling back")
        conn.rollback()
        return func.HttpResponse(f"Restore failed: {e}", status_code=500)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            csv_fp.close()
        except Exception:
            pass

    result = {
        "status": "ok",
        "database": pg_cfg.get("database") or derived_db,
        "target_table": target_table,
        "date_window": {"start": start_ts.isoformat(), "end": end_ts.isoformat()},
        "mode": mode,
        "columns_loaded": columns
    }
    return func.HttpResponse(json.dumps(result), status_code=200, mimetype="application/json")
```

---

## Example request

```bash
curl -X POST "http://localhost:7071/api/restore" \
  -H "Content-Type: application/json" \
  -d '{
    "pg": {
      "host": "weavix-dev-pg.postgres.database.azure.com",
      "port": 5432,
      "user": "mlubinsky@weavix.com",
      "password": "*****",
      "sslmode": "require"
    },
    "adls_url": "abfss://telemetry@weavixdatalake.dfs.core.windows.net/backups/weavix/silver/pttreceive2.2025-01-01.csv.gz",
    "destination": {
      "mode": "direct"
    },
    "timescaledb": {
      "decompress_window": true,
      "recompress_window": true,
      "refresh_caggs": ["weavix.silver_ptt_daily_cagg"]
    },
    "copy": {
      "csv_options": { "HEADER": true, "DELIMITER": ",", "NULL": "", "QUOTE": "\"" },
      "synchronous_commit_off": true
    }
  }'
```

> Note: In your naming convention, the path must be like:
> `.../<database>/<schema>.<table>.<YYYY-MM-DD>.csv.gz`
> If your path uses an extra directory (e.g., `.../<tenant>/<database>/<schema.table.date>.csv.gz`), the parser still derives the database from the **penultimate** segment.

---

## Operational notes

* **Authentication to ADLS**: In Azure, grant the Function’s **Managed Identity** `Storage Blob Data Reader` on the filesystem. Locally, `az login` or environment creds will be used by `DefaultAzureCredential`.
* **Memory vs disk**: `SpooledTemporaryFile` buffers in memory up to 100 MB, then spills to a temp file. Tweak thresholds if your day-files are large.
* **CSV columns**: The loader **reads the header** and builds an explicit column list for `COPY`. If your table changed since the export, use `destination.mode = "staging"` and map/transform before inserting into the target (you can customize that section).
* **Constraints & triggers**: They will fire during `COPY`/`INSERT`. For complex logic, keep the default `staging` path and do controlled transformations.
* **Chunk compression**: The function tries to `decompress_chunk` before loading and `compress_chunk` afterwards (best-effort; warnings are logged but non-fatal).
* **CAGGs**: Provide names (fully qualified) in `timescaledb.refresh_caggs` to recalc just the day window.

---

## Common tweaks

* **Headerless CSVs**: This implementation requires a header. If you have headerless exports, add a mapping of columns in the request (e.g., `copy.columns`) and skip header parsing.
* **Azure SQL/AAD auth**: If you connect with AAD tokens to Postgres, supply a `connection_uri` with the appropriate parameters (or extend the function to fetch a token and pass it as the password).
* **Very large files**: For hundreds of MB/GB per day, you may implement a true streaming COPY by building a small adapter that decompresses on the fly and exposes a `.read(size)` API to `copy_expert`. The `SpooledTemporaryFile` approach is simpler and robust for typical day-sized chunks.

---

If you want, I can also add a **Timer trigger** wrapper (e.g., restore yesterday’s file automatically) or a **queue-trigger** version that restores as soon as a new archive lands in a designated ADLS path.
