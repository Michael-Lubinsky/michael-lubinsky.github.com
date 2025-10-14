Here's a comprehensive approach to building this alert mechanism:

## Recommended Solution

### 1. **SQL Query to Check for New Records**

First, create a query that checks each table:

```sql
-- Check if records exist in last 6 hours
SELECT 
    'table_name' as table_name,
    MAX(created_at) as last_record_time,
    CASE 
        WHEN MAX(created_at) < NOW() - INTERVAL '6 hours' THEN 'ALERT'
        WHEN MAX(created_at) IS NULL THEN 'NO_DATA'
        ELSE 'OK'
    END as status
FROM your_table_name;
```

### 2. **Implementation Approaches**

#### **Option A: pg_cron (Native PostgreSQL)**
Best if you want everything inside PostgreSQL:

```sql
-- Install pg_cron extension
CREATE EXTENSION pg_cron;

-- Create a monitoring function
CREATE OR REPLACE FUNCTION check_table_freshness()
RETURNS void AS $$
DECLARE
    tables_to_check TEXT[] := ARRAY['table1', 'table2', 'table3'];
    table_name TEXT;
    last_time TIMESTAMP;
    alert_needed BOOLEAN := FALSE;
    alert_message TEXT := '';
BEGIN
    FOREACH table_name IN ARRAY tables_to_check
    LOOP
        EXECUTE format('SELECT MAX(created_at) FROM %I', table_name) INTO last_time;
        
        IF last_time IS NULL OR last_time < NOW() - INTERVAL '6 hours' THEN
            alert_needed := TRUE;
            alert_message := alert_message || format('Table %s: Last record at %s\n', 
                table_name, COALESCE(last_time::TEXT, 'NEVER'));
        END IF;
    END LOOP;
    
    IF alert_needed THEN
        -- Log to a notifications table
        INSERT INTO alert_log (alert_type, message, created_at)
        VALUES ('stale_data', alert_message, NOW());
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Schedule to run every hour
SELECT cron.schedule('check-table-freshness', '0 * * * *', 'SELECT check_table_freshness()');
```

#### **Option B: Python Script with Cron (More Flexible)**

```python
import psycopg2
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def check_tables():
    conn = psycopg2.connect("dbname=yourdb user=youruser password=yourpass")
    cur = conn.cursor()
    
    tables_to_check = ['table1', 'table2', 'table3']
    alerts = []
    
    for table in tables_to_check:
        cur.execute(f"""
            SELECT MAX(created_at) 
            FROM {table}
        """)
        last_time = cur.fetchone()[0]
        
        cutoff_time = datetime.now() - timedelta(hours=6)
        
        if last_time is None or last_time < cutoff_time:
            alerts.append(f"⚠️ {table}: Last record at {last_time or 'NEVER'}")
    
    if alerts:
        send_alert_email(alerts)
    
    cur.close()
    conn.close()

def send_alert_email(alerts):
    recipients = ['admin1@company.com', 'admin2@company.com']
    
    msg = MIMEText('\n'.join(alerts))
    msg['Subject'] = 'Database Alert: Stale Data Detected'
    msg['From'] = 'alerts@company.com'
    msg['To'] = ', '.join(recipients)
    
    with smtplib.SMTP('smtp.company.com', 587) as server:
        server.starttls()
        server.login('alerts@company.com', 'password')
        server.send_message(msg)

if __name__ == '__main__':
    check_tables()
```

Add to crontab:
```bash
0 */6 * * * /usr/bin/python3 /path/to/check_tables.py
```

#### **Option C: Monitoring Tools**
- **Prometheus + Alertmanager**: Use postgres_exporter with custom queries
- **Datadog/New Relic**: Built-in database monitoring with alerting
- **Grafana**: Visual dashboards with alert rules

### 3. **Best Practices**

1. **Add a timestamp column** to all monitored tables:
   ```sql
   ALTER TABLE your_table ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
   CREATE INDEX idx_created_at ON your_table(created_at);
   ```

2. **Create an alert log table**:
   ```sql
   CREATE TABLE alert_log (
       id SERIAL PRIMARY KEY,
       alert_type VARCHAR(50),
       message TEXT,
       created_at TIMESTAMP DEFAULT NOW(),
       resolved_at TIMESTAMP
   );
   ```

3. **Avoid alert fatigue**: Add cooldown periods so you don't get repeated emails

4. **Make it configurable**: Store table names and check intervals in a config table

### 4. **Quick Win: Simple Bash Script**

```bash
#!/bin/bash
PGPASSWORD=yourpass psql -h localhost -U youruser -d yourdb -t -c "
SELECT string_agg(table_name || ': ' || status, E'\n')
FROM (
    SELECT 'table1' as table_name, 
           CASE WHEN MAX(created_at) < NOW() - INTERVAL '6 hours' 
           THEN 'STALE' ELSE 'OK' END as status 
    FROM table1
    UNION ALL
    SELECT 'table2', CASE WHEN MAX(created_at) < NOW() - INTERVAL '6 hours' 
           THEN 'STALE' ELSE 'OK' END FROM table2
) t
WHERE status = 'STALE';
" | mail -s "Database Stale Data Alert" admin@company.com
```

**Which approach would you prefer?** I can provide more detailed implementation for any of these options based on your infrastructure and requirements.


## check “freshness” every N minutes and email if any table hasn’t received new rows within the last 6 hours.

---

Pattern A — In-database with pg_cron (+ webhook or a tiny listener)

Best when you already run pg_cron in the same Postgres.

1. Create a small config table listing what to watch.

```sql
-- schema to keep things tidy
create schema if not exists monitor;

-- which tables to watch and which column to use for freshness
create table if not exists monitor.targets (
  id               bigserial primary key,
  table_schema     text not null,
  table_name       text not null,
  ts_column        text not null,     -- name of the timestamp/timestamptz column
  max_lag_hours    integer not null default 6,
  min_new_rows     integer null,      -- optional: expect at least X rows per 6h
  enabled          boolean not null default true,
  unique(table_schema, table_name)
);

-- example rows
insert into monitor.targets (table_schema, table_name, ts_column, max_lag_hours, min_new_rows)
values
  ('events','pttreceive','created_at',6,null),
  ('events','gpsstart','created_at',6,10),
  ('events','gpsstop','created_at',6,10)
on conflict (table_schema, table_name) do nothing;
```

2. A function to compute freshness for all enabled targets.

```sql
create or replace function monitor.freshness_status(ref_now timestamptz default now())
returns table(
  table_fqn     text,
  last_seen_at  timestamptz,
  lag_hours     numeric,
  rows_6h       bigint,
  max_lag_hours integer,
  ok            boolean
)
language plpgsql as
$$
declare
  r record;
  sql_last text;
  sql_rows text;
  last_ts timestamptz;
  rows_in_window bigint;
begin
  for r in
    select * from monitor.targets where enabled
  loop
    -- last timestamp
    sql_last := format(
      'select max(%I) as last_ts from %I.%I',
      r.ts_column, r.table_schema, r.table_name
    );
    execute sql_last into last_ts;

    -- rows in the last 6h (or r.max_lag_hours)
    sql_rows := format(
      'select count(*) from %I.%I where %I >= %L::timestamptz - make_interval(hours => %s)',
      r.table_schema, r.table_name, r.ts_column, ref_now, r.max_lag_hours
    );
    execute sql_rows into rows_in_window;

    return query
      select
        format('%I.%I', r.table_schema, r.table_name) as table_fqn,
        last_ts as last_seen_at,
        extract(epoch from (ref_now - coalesce(last_ts, timestamp ''epoch'')))/3600.0 as lag_hours,
        rows_in_window as rows_6h,
        r.max_lag_hours,
        (last_ts is not null
         and ref_now - last_ts <= make_interval(hours => r.max_lag_hours)
         and (r.min_new_rows is null or rows_in_window >= r.min_new_rows)) as ok;
  end loop;
end;
$$;
```

3. A view for easy ad-hoc checks.

```sql
create or replace view monitor.v_freshness as
select *
from monitor.freshness_status();
```

4. Decide how to send an alert from inside Postgres:

Option 4a (recommended): Post to a webhook (Logic App, Function, Slack, etc.). If you can install an HTTP extension (e.g., pg_http/pg_net), use it. Example with a generic HTTP POST:

```sql
-- store the webhook once
create table if not exists monitor.settings (
  key text primary key,
  value text not null
);
insert into monitor.settings(key, value)
values ('alert_webhook_url', 'https://your-logic-app-or-function/webhook')
on conflict (key) do update set value = excluded.value;

-- function that posts one JSON payload when any table is stale
create or replace function monitor.check_and_notify()
returns void
language plpgsql as
$$
declare
  webhook text;
  payload jsonb;
  bad_rows jsonb;
begin
  select value into webhook from monitor.settings where key='alert_webhook_url';
  if webhook is null then
    raise notice 'monitor: alert_webhook_url not set';
    return;
  end if;

  select jsonb_agg(to_jsonb(s))
  into bad_rows
  from (
    select table_fqn, last_seen_at, lag_hours, rows_6h, max_lag_hours
    from monitor.freshness_status()
    where not ok
  ) s;

  if bad_rows is not null then
    payload := jsonb_build_object(
      'subject', 'Postgres freshness alert',
      'generated_at', now(),
      'stale', bad_rows
    );

    -- Example call using pg_http (adjust to your HTTP ext):
    -- select http_post(webhook, payload::text, 'application/json');

    -- If you cannot install extensions, skip this call and rely on pg_cron logs,
    -- or use LISTEN/NOTIFY as shown below.
  end if;
end;
$$;
```

Option 4b: Use LISTEN/NOTIFY and a tiny daemon that sends the email. This avoids DB extensions.

```sql
create or replace function monitor.check_and_notify_via_notify()
returns void
language plpgsql as
$$
declare
  bad_rows jsonb;
begin
  select jsonb_agg(to_jsonb(s))
  into bad_rows
  from (
    select table_fqn, last_seen_at, lag_hours, rows_6h, max_lag_hours
    from monitor.freshness_status()
    where not ok
  ) s;

  if bad_rows is not null then
    perform pg_notify('freshness_alert', bad_rows::text);
  end if;
end;
$$;
```

A minimal Python listener:

```python
import os, json, psycopg2, select, smtplib
from email.message import EmailMessage

PG_DSN = os.getenv("PG_DSN")
RECIPIENTS = [ "alice@example.com", "bob@example.com" ]
SENDER = "alerts@example.com"

def send_email(stale):
    msg = EmailMessage()
    msg["Subject"] = "Postgres freshness alert"
    msg["From"] = SENDER
    msg["To"] = ", ".join(RECIPIENTS)
    lines = ["The following tables appear stale (no new rows within SLA):", ""]
    for r in stale:
        lines.append(f"- {r['table_fqn']} | last_seen={r['last_seen_at']} | lag_hours={round(r['lag_hours'],2)} | rows_6h={r['rows_6h']}")
    msg.set_content("\n".join(lines))
    with smtplib.SMTP("your-relay.example.com", 25, timeout=30) as s:
        s.send_message(msg)

with psycopg2.connect(PG_DSN) as conn:
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("LISTEN freshness_alert;")
    while True:
        if select.select([conn], [], [], 60) == ([], [], []):
            continue
        conn.poll()
        while conn.notifies:
            n = conn.notifies.pop(0)
            stale = json.loads(n.payload)
            send_email(stale)
```

5. Schedule with pg_cron (every 15 minutes, adjust as needed).

```sql
-- every 15 minutes
select cron.schedule(
  'monitor freshness',
  '*/15 * * * *',
  $$call monitor.check_and_notify();$$
);
-- or, if using notify:
-- $$call monitor.check_and_notify_via_notify();$$
```

Notes:

* Use timestamptz for ts_column; make sure it’s indexed: create index concurrently on schema.table (ts_column desc).
* If ingestion is bursty, prefer the min_new_rows guard to avoid false positives.
* If you can’t install http/pg_net, use the LISTEN/NOTIFY + tiny daemon approach, or write to a monitor.alerts table and have an external job read and email.

---

Pattern B — External monitor (Azure Function Timer) + email (SendGrid or Microsoft Graph)

Best when you already use Azure Functions (you do), and/or don’t want DB extensions.

1. Config: either keep the same monitor.targets table as above and let the Function read it, or define a static YAML/JSON in your Function.

2. Timer-triggered Azure Function (Python). Every 15 minutes:

* Query the set of targets.
* For each: SELECT max(ts_column), COUNT(*) WHERE ts_column >= now()-interval '6 hours'.
* Collect any stale entries and send one email to a recipient list.

Skeleton (minimal, uses psycopg2 + SendGrid):

```python
# function_app.py
import os, json, psycopg2, sendgrid
from sendgrid.helpers.mail import Mail
from datetime import timedelta, timezone, datetime
import azure.functions as func

PG_DSN = os.getenv("PG_DSN")  # e.g. "host=... dbname=... user=... password=... sslmode=require"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
ALERT_TO = os.getenv("ALERT_TO", "alice@example.com,bob@example.com").split(",")

def query_targets(conn):
    with conn.cursor() as cur:
        cur.execute("""
            select table_schema, table_name, ts_column, max_lag_hours, min_new_rows
            from monitor.targets
            where enabled
        """)
        return cur.fetchall()

def check_one(conn, schema, table, ts_col, max_lag_hours, min_new_rows):
    with conn.cursor() as cur:
        cur.execute(f"select max({ts_col}) from {schema}.{table}")
        last_ts, = cur.fetchone()
        cur.execute(f"""
            select count(*) from {schema}.{table}
            where {ts_col} >= now() - make_interval(hours => %s)
        """, (max_lag_hours,))
        rows_6h, = cur.fetchone()
    lag_hours = None
    if last_ts is not None:
        lag_hours = (datetime.now(timezone.utc) - last_ts).total_seconds()/3600.0
    ok = (last_ts is not None
          and lag_hours <= max_lag_hours
          and (min_new_rows is None or rows_6h >= min_new_rows))
    return dict(
        table_fqn=f"{schema}.{table}",
        last_seen_at=last_ts.isoformat() if last_ts else None,
        lag_hours=lag_hours,
        rows_6h=rows_6h,
        max_lag_hours=max_lag_hours,
        ok=ok
    )

def send_email(stale):
    if not stale:
        return
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    lines = ["The following tables appear stale:", ""]
    for r in stale:
        lh = "n/a" if r['lag_hours'] is None else f"{r['lag_hours']:.2f}"
        lines.append(f"- {r['table_fqn']} | last_seen={r['last_seen_at']} | lag_hours={lh} | rows_6h={r['rows_6h']}")
    content = "\n".join(lines)
    msg = Mail(
        from_email="alerts@your-domain.example",
        to_emails=ALERT_TO,
        subject="Postgres freshness alert",
        plain_text_content=content
    )
    sg.send(msg)

app = func.FunctionApp()

@app.schedule(schedule="0 */15 * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=True)
def freshness_monitor(myTimer: func.TimerRequest) -> None:
    with psycopg2.connect(PG_DSN) as conn:
        targets = query_targets(conn)
        stale = []
        for schema, table, ts_col, max_lag_hours, min_new_rows in targets:
            res = check_one(conn, schema, table, ts_col, max_lag_hours, min_new_rows)
            if not res["ok"]:
                stale.append(res)
        send_email(stale)
```

Environment variables (App Settings):

* PG_DSN
* SENDGRID_API_KEY
* ALERT_TO = “[alice@example.com](mailto:alice@example.com),[bob@example.com](mailto:bob@example.com)”

If you prefer Microsoft Graph instead of SendGrid, swap send_email() to call Graph’s /sendMail using a managed identity-enabled app registration.

3. Hardening tips:

* Index each ts_column (DESC) for fast MAX() and range counts.
* Use timestamptz everywhere; ensure your writers set UTC.
* Mitigate clock skew by comparing against now() at the DB (not the app).
* Add per-table overrides (e.g., a table that only updates daily → max_lag_hours=30).
* Debounce: record last_alert_at per table to avoid spamming. E.g., only alert again if still stale after 1 hour.
* Optional: include “top 3 newest rows” in the email for context.

---

Quick start checklist

1. Add monitor.targets rows for each table you care about and ensure an index:
   create index concurrently on your_schema.your_table (your_ts_column desc);

2. Choose your engine:

   * If you already use pg_cron and can reach a webhook: use Pattern A (check_and_notify via http).
   * If you prefer app-side control and easy email APIs: use Pattern B (Azure Function Timer + SendGrid/Graph).

3. Start at a 15-minute schedule; tune to 5–10 minutes if needed.

4. Add a “maintenance mode” switch (e.g., a monitor.settings flag) so you can pause alerts during planned outages.

If you tell me which exact tables and timestamp columns you want to watch, I’ll fill in the INSERTs and, if you like, wire either pattern end-to-end for your environment.



## Short Answer: **No**

Azure PostgreSQL Flexible Server does not support the plpython3u extension, which would be needed to send emails directly from the database. Additionally, Azure blocks outbound SMTP connections on port 25 for security reasons.

## Azure-Specific Solutions

Since you're on Azure PostgreSQL Flexible Server, here are the best approaches:

### **Option 1: Azure Logic Apps (Recommended)**
Perfect for managed Azure environments - no code needed:

```
PostgreSQL → Logic App → Email
```

**Setup:**
1. Create a Logic App with **Recurrence trigger** (every 6 hours)
2. Add **PostgreSQL connector** action to query your tables:
```sql
SELECT 
    table_name,
    MAX(created_at) as last_record,
    CASE 
        WHEN MAX(created_at) < DATEADD(hour, -6, GETDATE()) THEN 'STALE'
        ELSE 'OK'
    END as status
FROM (
    SELECT 'table1' as table_name, created_at FROM table1
    UNION ALL
    SELECT 'table2', created_at FROM table2
) t
GROUP BY table_name
HAVING MAX(created_at) < DATEADD(hour, -6, GETDATE())
```
3. Add **Condition** to check if any rows returned
4. Add **Office 365 Outlook** or **SendGrid** action to send email

**Pros:** No infrastructure, visual designer, built-in monitoring, easy to modify

### **Option 2: Azure Function (Python/C#)**
More flexible, serverless approach:

```python
import logging
import psycopg2
import os
from azure.communication.email import EmailClient
import azure.functions as func

def main(mytimer: func.TimerTrigger) -> None:
    conn_string = os.environ['POSTGRESQL_CONNECTION_STRING']
    email_connection_string = os.environ['COMMUNICATION_SERVICES_CONNECTION_STRING']
    
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    tables_to_check = ['table1', 'table2', 'table3']
    alerts = []
    
    for table in tables_to_check:
        cur.execute(f"""
            SELECT MAX(created_at) 
            FROM {table}
            WHERE created_at > NOW() - INTERVAL '6 hours'
        """)
        result = cur.fetchone()
        
        if result[0] is None:
            alerts.append(f"⚠️ {table}: No new records in last 6 hours")
    
    if alerts:
        email_client = EmailClient.from_connection_string(email_connection_string)
        
        message = {
            "senderAddress": "alerts@yourdomain.com",
            "recipients": {
                "to": [
                    {"address": "admin1@company.com"},
                    {"address": "admin2@company.com"}
                ]
            },
            "content": {
                "subject": "Database Alert: Stale Data Detected",
                "plainText": "\n".join(alerts)
            }
        }
        
        email_client.begin_send(message)
    
    cur.close()
    conn.close()
```

**function.json** (Timer trigger - runs every 6 hours):
```json
{
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */6 * * *"
    }
  ]
}
```

### **Option 3: Azure Monitor + Action Groups**
Use Azure's native monitoring:

1. **Enable Query Performance Insights** on your Flexible Server
2. Create **Log Analytics Workspace**
3. Set up **Metric Alert** with custom log query
4. Configure **Action Group** to send emails

### **Option 4: pg_cron + External Service**
Use pg_cron (which IS supported) to write to a log table, then have external service check it:

```sql
-- Enable pg_cron
CREATE EXTENSION pg_cron;

-- Create alert table
CREATE TABLE data_freshness_alerts (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    last_record_time TIMESTAMP,
    check_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20)
);

-- Function to log stale data
CREATE OR REPLACE FUNCTION check_data_freshness()
RETURNS void AS $$
BEGIN
    INSERT INTO data_freshness_alerts (table_name, last_record_time, status)
    SELECT 'table1', MAX(created_at), 
           CASE WHEN MAX(created_at) < NOW() - INTERVAL '6 hours' 
           THEN 'STALE' ELSE 'OK' END
    FROM table1;
    
    -- Repeat for other tables
END;
$$ LANGUAGE plpgsql;

-- Schedule every hour
SELECT cron.schedule('freshness-check', '0 * * * *', 'SELECT check_data_freshness()');
```

Then have a simple Azure Function query this table and send alerts.

### **Recommended Approach**
For Azure PostgreSQL Flexible Server, I'd recommend **Azure Logic Apps** because:
- ✅ Fully managed, no infrastructure
- ✅ Native PostgreSQL connector
- ✅ Built-in email actions (Office 365, SendGrid, Gmail)
- ✅ Easy to configure and modify
- ✅ Built-in monitoring and logging
- ✅ Low cost for periodic checks

