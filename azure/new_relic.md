
## NewRelic Incident event REST API 
<https://docs.newrelic.com/docs/data-apis/ingest-apis/event-api/incident-event-rest-api/>

To monitor the number of records in Azure PostgreSQL Flexible Server tables and raise alerts in New Relic when the count falls below a threshold, you can follow this high-level approach using the **New Relic Incident Event REST API**:

---

### **1. Prerequisites**
- **Azure PostgreSQL Flexible Server**: Ensure you have access and the necessary permissions to query the database.
- **New Relic Account**: You need a New Relic account and an [API key](https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/) for authentication.
- **Scripting Environment**: A place to run a script (e.g., Azure Function, AWS Lambda, or a local server) that can query PostgreSQL and send events to New Relic.

---

### **2. High-Level Workflow**
1. **Query PostgreSQL**: Write a query to count the number of records in the target tables for the current and previous dates.
2. **Compare with Threshold**: Check if the count is below your defined threshold.
3. **Send Event to New Relic**: If the count is below the threshold, send an incident event to New Relic using the [Incident Event REST API](https://docs.newrelic.com/docs/data-apis/ingest-apis/event-api/incident-event-rest-api/).
4. **Create Alert Policy in New Relic**: Set up a [NRQL alert condition](https://docs.newrelic.com/docs/alerts-applied-intelligence/new-relic-alerts/alert-conditions/create-nrql-alert-condition/) to trigger when the incident event is received.

---

### **3. Example Implementation**

#### **A. PostgreSQL Query**
Write a query to get the record count for the current and previous dates. For example:
```sql
SELECT
    COUNT(*) AS record_count,
    CURRENT_DATE AS current_date
FROM your_table
WHERE date_column = CURRENT_DATE;

SELECT
    COUNT(*) AS record_count,
    CURRENT_DATE - INTERVAL '1 day' AS previous_date
FROM your_table
WHERE date_column = CURRENT_DATE - INTERVAL '1 day';
```

#### **B. Script to Query and Send Event**
Here’s a Python example using `psycopg2` for PostgreSQL and `requests` for the New Relic API:

```python
import psycopg2
import requests
import json
from datetime import datetime

# PostgreSQL connection
conn = psycopg2.connect(
    host="your-postgres-host",
    database="your-database",
    user="your-username",
    password="your-password"
)
cursor = conn.cursor()

# Query for current and previous day record counts
cursor.execute("""
    SELECT COUNT(*) FROM your_table WHERE date_column = CURRENT_DATE;
""")
current_count = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM your_table WHERE date_column = CURRENT_DATE - INTERVAL '1 day';
""")
previous_count = cursor.fetchone()[0]

# Threshold
threshold = 100

# Check if current count is below threshold
if current_count < threshold:
    # New Relic Incident Event API endpoint
    url = "https://api.newrelic.com/v2/events"
    headers = {
        "Api-Key": "your-newrelic-api-key",
        "Content-Type": "application/json"
    }
    payload = [
        {
            "eventType": "PostgresRecordCountAlert",
            "currentCount": current_count,
            "previousCount": previous_count,
            "threshold": threshold,
            "date": datetime.now().isoformat(),
            "message": f"Record count ({current_count}) is below threshold ({threshold}) for {datetime.now().date()}"
        }
    ]

    # Send event to New Relic
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print("Event sent to New Relic:", response.status_code)
```

#### **C. New Relic Alert Policy**
1. Go to **Alerts & AI** > **Alert Policies** in New Relic.
2. Create a new policy or edit an existing one.
3. Add a **NRQL alert condition**:
   - Use a query like:
     ```sql
     SELECT count(*) FROM PostgresRecordCountAlert WHERE currentCount < threshold FACET message
     ```
   - Set the threshold to `1` (since any event means the count is below the threshold).
   - Configure the notification channel (e.g., email, Slack, PagerDuty).

---

### **4. Automate the Script**
- Schedule the script to run daily (e.g., using Azure Functions, AWS Lambda, or a cron job).
- Ensure the script has the necessary permissions and environment variables for PostgreSQL and New Relic API access.

---

### **5. Testing and Validation**
- Test the script manually to ensure it queries PostgreSQL correctly and sends events to New Relic.
- Verify that the alert policy triggers as expected when the record count is below the threshold.

---

### **6. Optional Enhancements**
- **Logging**: Add logging to track script execution and API responses.
- **Error Handling**: Implement retries and error handling for robustness.
- **Dynamic Thresholds**: Fetch the threshold from a configuration file or database.

 
 

New Relic’s Incident event API ingests **custom incident trigger/resolve events** (it does not directly “create” incidents; incident creation is triggered by the event).  

You POST JSON (optionally gzipped) to the Event API endpoint with `eventType: "NrAiIncidentExternal"` and use `state: "trigger"` or `state: "resolve"`. 

Include `aggregationTag.*` fields to dedupe/aggregate updates to the same incident. :contentReference[oaicite:0]{index=0}

Key bits from the docs you’ll rely on:
- Use the Event API endpoint, License (a.k.a. ingest) key, and your account id when posting events. :contentReference[oaicite:1]{index=1}
 
- Required fields:   
  `eventType = NrAiIncidentExternal`,   
  `state` (`trigger` or `resolve`),   
   plus a `title` and `source` on trigger;   
   use `aggregationTag.*` consistently so multiple triggers/resolve updates roll up to the same incident.
  
  :contentReference[oaicite:2]{index=2}



## Architecture (simple & robust)

- **A timer job** (Azure Function on a schedule, or a containerized cron job) runs every N minutes.
- It executes SQL counts for your date windows (e.g., PT “today” and “yesterday”, or UTC).
- For each (table, date) pair, it compares `rowcount` to a threshold.
  - If `< threshold`: POST a **trigger** incident event to New Relic.
  - If `≥ threshold`: POST a **resolve** event (using the same `aggregationTag.*` you used to trigger).
- Aggregation tags should uniquely identify the “thing being checked”, e.g.:
  - `aggregationTag.check = "pg-table-rowcount"`
  - `aggregationTag.table = "<schema.table>"`
  - `aggregationTag.date = "YYYY-MM-DD"`
  - `aggregationTag.env = "dev|prod"`
  - (Any `aggregationTag.*` values are eligible for grouping; use the same set on resolve.) :contentReference[oaicite:3]{index=3}

---

## SQL: safe, timezone-explicit counts

Pick the date semantics you care about (PT vs UTC). Two common options:

```sql
-- Option A: PT calendar dates
WITH tz AS (
  SELECT (now() AT TIME ZONE 'America/Los_Angeles')::date AS today_pt
)
SELECT
  (SELECT COUNT(*) FROM your_schema.your_table WHERE source_date = (SELECT today_pt FROM tz)) AS today_count,
  (SELECT COUNT(*) FROM your_schema.your_table WHERE source_date = (SELECT today_pt - 1 FROM tz)) AS yesterday_count;
```

```sql
-- Option B: UTC calendar dates
WITH tz AS (
  SELECT (now() AT TIME ZONE 'UTC')::date AS today_utc
)
SELECT
  (SELECT COUNT(*) FROM your_schema.your_table WHERE source_date = (SELECT today_utc FROM tz)) AS today_count,
  (SELECT COUNT(*) FROM your_schema.your_table WHERE source_date = (SELECT today_utc - 1 FROM tz)) AS yesterday_count;
```

Notes:

* If your date column is `timestamptz`, compare on a date range (e.g., `ts >= date AND ts < date + 1`).
* Use the same logic consistently in code so the incident definition matches what your team expects.

---

## Ready-to-use Azure Function (Python, Timer trigger)

**Folder layout**

```
pg_rowcount_to_newrelic/
  host.json
  local.settings.json        # for local dev
  requirements.txt
  RowcountTimer/__init__.py  # function code
  RowcountTimer/function.json
```

**requirements.txt**

```ini
psycopg2-binary==2.9.9
azure-identity==1.17.1
requests==2.32.3
```

**function.json** (runs every 10 minutes; adjust as needed)

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */10 * * * *"
    }
  ]
}
```

**Environment**
Set as app settings in Azure:

```
PGHOST=yourserver.postgres.database.azure.com
PGDATABASE=weavix
# If using Azure AD (Managed Identity), PGUSER must be an AAD role mapped to your Function’s managed identity:
PGUSER=<your-managed-identity-principal-name>
# Leave PGPASSWORD empty when using token auth.

NR_ACCOUNT_ID=<your_nr_account_id>
NR_LICENSE_KEY=<your_nr_license_key>   # "Api-Key" for ingest
NR_SOURCE=azure-postgres-monitor
NR_ENV=prod
SERVICE_ID=42                           # whatever makes sense for you
TABLES=json list like: [{"table":"events.pttreceive","date_col":"source_date","threshold":1000}, {"table":"events.ltetowerchange","date_col":"source_date","threshold":50}]
DATE_TZ=PT   # or UTC
```

**RowcountTimer/**init**.py**

```python
import json
import os
import logging
import psycopg2
import requests
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential

# --- Config ---
PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE", "postgres")
PGUSER = os.getenv("PGUSER")
DATE_TZ = os.getenv("DATE_TZ", "UTC")  # "PT" or "UTC"
NR_ACCOUNT_ID = os.getenv("NR_ACCOUNT_ID")
NR_LICENSE_KEY = os.getenv("NR_LICENSE_KEY")
NR_SOURCE = os.getenv("NR_SOURCE", "azure-postgres-monitor")
NR_ENV = os.getenv("NR_ENV", "dev")
SERVICE_ID = os.getenv("SERVICE_ID", "0")

# TABLES env is a JSON array of objects:
#   { "table": "schema.table", "date_col": "source_date", "threshold": 1000 }
TABLES = json.loads(os.getenv("TABLES", "[]"))

# New Relic Event API endpoint (Incident event uses Event API endpoint)
NR_ENDPOINT = f"https://insights-collector.newrelic.com/v1/accounts/{NR_ACCOUNT_ID}/events"

def _aad_pg_connection():
    """
    Connect to Azure PostgreSQL using Azure AD token auth via Managed Identity.
    Ensure your Managed Identity is created as an AAD user/role in Postgres with proper grants.
    """
    cred = DefaultAzureCredential()
    token = cred.get_token("https://ossrdbms-aad.database.windows.net/.default").token
    conn = psycopg2.connect(
        host=PGHOST,
        dbname=PGDATABASE,
        user=PGUSER,
        password=token,
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = True
    return conn

def _dates_sql(date_col: str, tz_choice: str):
    """
    Returns WHERE fragments & a label map for today/yesterday based on PT or UTC calendar dates.
    """
    if tz_choice.upper() == "PT":
        tzsql = "(now() AT TIME ZONE 'America/Los_Angeles')::date"
    else:
        tzsql = "(now() AT TIME ZONE 'UTC')::date"

    # Safely construct the date filters. Caller should pass identifiers, not user input.
    today_where = f"{date_col} = {tzsql}"
    yday_where = f"{date_col} = {tzsql} - 1"
    return {"today": today_where, "yesterday": yday_where}

def _count_rows(cur, table: str, where_clause: str):
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_clause};")
    return cur.fetchone()[0]

def _post_incident_event(payloads):
    """
    Send one or more incident events to New Relic via the Event API.
    The docs require:
      - eventType = 'NrAiIncidentExternal'
      - state = 'trigger' or 'resolve'
      - 'aggregationTag.*' to aggregate updates to the same incident
    """
    headers = {
        "Content-Type": "application/json",
        "Api-Key": NR_LICENSE_KEY,
    }
    r = requests.post(NR_ENDPOINT, headers=headers, json=payloads, timeout=10)
    r.raise_for_status()
    return r.json()

def _make_payload(state: str, *, table: str, date_str: str, count_val: int, threshold: int):
    title = f"{table} rowcount for {date_str} below threshold ({count_val} < {threshold})" if state == "trigger" \
            else f"{table} rowcount healthy {date_str} ({count_val} ≥ {threshold})"

    return {
        "eventType": "NrAiIncidentExternal",
        "state": state,               # 'trigger' or 'resolve'
        "title": title if state == "trigger" else None,  # title required on trigger
        "source": NR_SOURCE if state == "trigger" else None,  # source required on trigger
        "description": f"Rowcount={count_val}, threshold={threshold}, table={table}, date={date_str}",
        "entityName": table,
        # Aggregation tags: MUST be identical between trigger and resolve for the same incident
        "aggregationTag.check": "pg-table-rowcount",
        "aggregationTag.table": table,
        "aggregationTag.date": date_str,
        "aggregationTag.env": NR_ENV,
        "aggregationTag.serviceId": int(SERVICE_ID),
        "version": 1
    }

def main(myTimer):
    logging.info("Rowcount to New Relic: start")
    now_iso = datetime.now(timezone.utc).isoformat()

    if not (NR_ACCOUNT_ID and NR_LICENSE_KEY):
        logging.error("Missing NR_ACCOUNT_ID or NR_LICENSE_KEY")
        return

    if not TABLES:
        logging.warning("No TABLES configured; nothing to check.")
        return

    try:
        with _aad_pg_connection() as conn, conn.cursor() as cur:
            for item in TABLES:
                table = item["table"]
                date_col = item["date_col"]
                threshold = int(item["threshold"])

                where_map = _dates_sql(date_col, DATE_TZ)
                for label, where_clause in where_map.items():
                    cnt = _count_rows(cur, table, where_clause)
                    # Compute the concrete date string we just evaluated to include in aggregation tag
                    if DATE_TZ.upper() == "PT":
                        # Evaluate date in SQL to avoid drift
                        cur.execute("SELECT (now() AT TIME ZONE 'America/Los_Angeles')::date;")
                    else:
                        cur.execute("SELECT (now() AT TIME ZONE 'UTC')::date;")
                    base_date = cur.fetchone()[0]
                    date_str = (base_date if label == "today" else (base_date.replace()) )  # will assign below
                    if label == "yesterday":
                        cur.execute("SELECT ((now() AT TIME ZONE %s)::date - 1)::text;", 
                                    ('America/Los_Angeles' if DATE_TZ.upper() == 'PT' else 'UTC',))
                        date_str = cur.fetchone()[0]
                    else:
                        cur.execute("SELECT ((now() AT TIME ZONE %s)::date)::text;",
                                    ('America/Los_Angeles' if DATE_TZ.upper() == 'PT' else 'UTC',))
                        date_str = cur.fetchone()[0]

                    state = "trigger" if cnt < threshold else "resolve"
                    payload = _make_payload(state, table=table, date_str=date_str, count_val=cnt, threshold=threshold)

                    # Remove None keys (title/source omitted on resolve)
                    clean_payload = {k: v for k, v in payload.items() if v is not None}
                    try:
                        resp = _post_incident_event([clean_payload])
                        logging.info("Posted %s for %s %s: %s", state, table, date_str, resp)
                    except Exception as e:
                        logging.exception("Failed posting incident event for %s %s: %s", table, date_str, e)

    except Exception as e:
        logging.exception("Top-level failure: %s", e)

    logging.info("Rowcount to New Relic: done at %s", now_iso)
```

**What this does**

* Connects to Azure Postgres using Managed Identity (AAD) and token (ensure your Function’s managed identity has a Postgres role mapped and SELECT access).
* For each configured table, checks row counts for “today” and “yesterday” in either **PT** or **UTC** calendar terms (controlled by `DATE_TZ`).
* Posts **trigger** events to New Relic when `count < threshold`; posts **resolve** events when `count ≥ threshold`.
* Uses `aggregationTag.*` so that all updates for the same (table, date, env) aggregate to one incident thread. ([New Relic][1])

---

## Example TABLES setting

```json
[
  {"table":"events.pttreceive",       "date_col":"source_date", "threshold": 100000},
  {"table":"events.ltetowerchange",   "date_col":"source_date", "threshold": 1000 },
  {"table":"events.pttjitter",        "date_col":"source_date", "threshold": 2500 }
]
```

---

## Verifying in New Relic

* You can query ingested incident events:

  ```
  FROM NrAiIncidentExternal
  SELECT * 
  WHERE aggregationTag.check = 'pg-table-rowcount'
  SINCE 2 days ago
  ```
* If you also want notifications for ingestion errors, New Relic suggests setting up **NRQL alert conditions** around the data you’re sending. ([New Relic][1])

---

## Curl example (manual test)

Once you have a JSON payload (minimally containing `eventType`, `state`, `title` + `source` for trigger, and your `aggregationTag.*`), you can test with curl to the Event API endpoint:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Api-Key: $NR_LICENSE_KEY" \
  "https://insights-collector.newrelic.com/v1/accounts/$NR_ACCOUNT_ID/events" \
  -d '[
    {
      "eventType":"NrAiIncidentExternal",
      "state":"trigger",
      "title":"Test low rowcount",
      "source":"azure-postgres-monitor",
      "description":"Rowcount=42, threshold=100, table=events.pttreceive, date=2025-10-22",
      "aggregationTag.check":"pg-table-rowcount",
      "aggregationTag.table":"events.pttreceive",
      "aggregationTag.date":"2025-10-22",
      "aggregationTag.env":"prod",
      "aggregationTag.serviceId":42,
      "version":1
    }
  ]'
```

The same endpoint and headers are shown in the New Relic docs; they also show how to gzip the body if you prefer compressed ingest. ([New Relic][1])

---

## Operational notes & tips

* **Idempotency/duplication:** If your job runs frequently, posting multiple `trigger` events with the same `aggregationTag.*` will aggregate into one incident; posting `resolve` with the same tags will close it. ([New Relic][1])
* **Credentials:** Prefer Managed Identity → AAD token for Postgres (as shown). Ensure the MI principal has `CONNECT` + `USAGE` and `SELECT` on target schemas/tables.
* **Timeouts:** Keep your Postgres query fast (indexes on the date column help). If your date column is `timestamptz`, filter with a **range** (`ts >= date AND ts < date + 1`) and index on that column (or create a functional index on `ts::date` if appropriate).
* **Severity:** You can set `priority` in the payload (`low|medium|high|critical`) if you want to drive different workflows. ([New Relic][1])
* **Runbook link:** Consider adding a `runbookUrl` to help on-call. ([New Relic][1])

---

## Variations

* **Pure-DB scheduling:** Use `pg_cron` to call a small HTTP relay (e.g., Azure Function HTTP trigger) after computing counts in SQL. But keeping the scheduler in Azure Functions (Timer) avoids network egress from the DB and keeps secrets out of SQL.
* **One event per table/day vs batch:** The code sends one event per table/day. You can batch multiple events in a single POST by passing an array (shown) to reduce overhead. ([New Relic][1])

If you want, tell me your exact tables, date columns, thresholds, timezone rule (PT vs UTC), and your NR account id/env naming—and I’ll tailor the `TABLES` config and the SQL predicates precisely for your schema.

```
::contentReference[oaicite:11]{index=11}
```

[1]: https://docs.newrelic.com/docs/data-apis/ingest-apis/event-api/incident-event-rest-api/ "Incident event REST API | New Relic Documentation"
