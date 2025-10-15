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


 

## Azure-Specific Solutions

Since you're on Azure PostgreSQL Flexible Server, here are the best approaches:
 
### **Option: Azure Function (Python/C#)**
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

### **Option: Azure Monitor + Action Groups**
Use Azure's native monitoring:

1. **Enable Query Performance Insights** on your Flexible Server
2. Create **Log Analytics Workspace**
3. Set up **Metric Alert** with custom log query
4. Configure **Action Group** to send emails

### **Option: pg_cron + External Service**
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

 

---

# **Solution Overview**

We'll create a monitoring system that:
1. **Tracks which tables to monitor** (configuration table)
2. **Detects missing dates** based on cadence
3. **Reports results** in a structured format
4. **Sends alerts** when issues are found

---

# **Option 1: PostgreSQL Solution (pg_cron)**

## **Step 1: Create Monitoring Configuration Table**

```sql
-- Table to configure which tables to monitor
CREATE TABLE IF NOT EXISTS data_monitoring_config (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    schema_name VARCHAR(100) DEFAULT 'public',
    date_column VARCHAR(100) NOT NULL,  -- Column that contains the date
    cadence VARCHAR(20) NOT NULL,  -- 'daily', 'weekly', 'monthly'
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(schema_name, table_name)
);

-- Table to store monitoring results
CREATE TABLE IF NOT EXISTS data_monitoring_results (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP DEFAULT NOW(),
    table_name VARCHAR(100) NOT NULL,
    schema_name VARCHAR(100) NOT NULL,
    cadence VARCHAR(20) NOT NULL,
    missing_dates JSONB,  -- Array of missing dates
    missing_count INTEGER,
    status VARCHAR(20),  -- 'OK', 'WARNING', 'CRITICAL'
    message TEXT
);

-- Index for faster queries
CREATE INDEX idx_monitoring_results_timestamp ON data_monitoring_results(check_timestamp);
CREATE INDEX idx_monitoring_results_status ON data_monitoring_results(status);
```

## **Step 2: Add Your Tables to Monitor**

```sql
-- Add tables to monitor
INSERT INTO data_monitoring_config (table_name, schema_name, date_column, cadence, description)
VALUES
    ('orders', 'public', 'created_at', 'daily', 'Daily order transactions'),
    ('sales_summary', 'public', 'report_date', 'weekly', 'Weekly sales reports'),
    ('monthly_revenue', 'public', 'month_date', 'monthly', 'Monthly revenue aggregation'),
    ('user_activity', 'public', 'activity_date', 'daily', 'Daily user activity logs'),
    ('inventory_snapshots', 'public', 'snapshot_date', 'weekly', 'Weekly inventory counts');

-- View configuration
SELECT * FROM data_monitoring_config WHERE is_active = true;
```

## **Step 3: Create Monitoring Function**

```sql
CREATE OR REPLACE FUNCTION check_data_freshness()
RETURNS TABLE(
    table_name VARCHAR,
    schema_name VARCHAR,
    cadence VARCHAR,
    missing_dates JSONB,
    missing_count INTEGER,
    status VARCHAR,
    message TEXT
) 
LANGUAGE plpgsql
AS $$
DECLARE
    config_record RECORD;
    missing_list JSONB;
    expected_dates DATE[];
    existing_dates DATE[];
    missing_date_list DATE[];
    check_start_date DATE;
    check_end_date DATE;
    current_date_iter DATE;
    date_exists BOOLEAN;
    result_status VARCHAR;
    result_message TEXT;
BEGIN
    -- Loop through each active configuration
    FOR config_record IN 
        SELECT * FROM data_monitoring_config WHERE is_active = true
    LOOP
        -- Determine date range based on cadence
        check_end_date := CURRENT_DATE;
        
        CASE config_record.cadence
            WHEN 'daily' THEN
                check_start_date := CURRENT_DATE - INTERVAL '7 days';
            WHEN 'weekly' THEN
                check_start_date := CURRENT_DATE - INTERVAL '1 month';
            WHEN 'monthly' THEN
                check_start_date := CURRENT_DATE - INTERVAL '3 months';
            ELSE
                check_start_date := CURRENT_DATE - INTERVAL '7 days';
        END CASE;
        
        -- Build expected dates list based on cadence
        missing_date_list := ARRAY[]::DATE[];
        
        IF config_record.cadence = 'daily' THEN
            -- Check each day
            current_date_iter := check_start_date;
            WHILE current_date_iter <= check_end_date LOOP
                -- Check if data exists for this date
                EXECUTE format(
                    'SELECT EXISTS(SELECT 1 FROM %I.%I WHERE DATE(%I) = $1)',
                    config_record.schema_name,
                    config_record.table_name,
                    config_record.date_column
                ) INTO date_exists USING current_date_iter;
                
                IF NOT date_exists THEN
                    missing_date_list := array_append(missing_date_list, current_date_iter);
                END IF;
                
                current_date_iter := current_date_iter + INTERVAL '1 day';
            END LOOP;
            
        ELSIF config_record.cadence = 'weekly' THEN
            -- Check each Monday (or first day of week)
            current_date_iter := date_trunc('week', check_start_date)::DATE;
            WHILE current_date_iter <= check_end_date LOOP
                -- Check if data exists for this week
                EXECUTE format(
                    'SELECT EXISTS(SELECT 1 FROM %I.%I WHERE DATE(%I) BETWEEN $1 AND $1 + INTERVAL ''6 days'')',
                    config_record.schema_name,
                    config_record.table_name,
                    config_record.date_column
                ) INTO date_exists USING current_date_iter;
                
                IF NOT date_exists THEN
                    missing_date_list := array_append(missing_date_list, current_date_iter);
                END IF;
                
                current_date_iter := current_date_iter + INTERVAL '1 week';
            END LOOP;
            
        ELSIF config_record.cadence = 'monthly' THEN
            -- Check each month (first day)
            current_date_iter := date_trunc('month', check_start_date)::DATE;
            WHILE current_date_iter <= check_end_date LOOP
                -- Check if data exists for this month
                EXECUTE format(
                    'SELECT EXISTS(SELECT 1 FROM %I.%I WHERE DATE_TRUNC(''month'', %I) = $1)',
                    config_record.schema_name,
                    config_record.table_name,
                    config_record.date_column
                ) INTO date_exists USING current_date_iter;
                
                IF NOT date_exists THEN
                    missing_date_list := array_append(missing_date_list, current_date_iter);
                END IF;
                
                current_date_iter := current_date_iter + INTERVAL '1 month';
            END LOOP;
        END IF;
        
        -- Convert array to JSONB
        missing_list := to_jsonb(missing_date_list);
        
        -- Determine status
        IF array_length(missing_date_list, 1) IS NULL OR array_length(missing_date_list, 1) = 0 THEN
            result_status := 'OK';
            result_message := 'All expected dates have data';
        ELSIF array_length(missing_date_list, 1) <= 2 THEN
            result_status := 'WARNING';
            result_message := format('%s missing date(s)', array_length(missing_date_list, 1));
        ELSE
            result_status := 'CRITICAL';
            result_message := format('%s missing date(s) - requires attention', array_length(missing_date_list, 1));
        END IF;
        
        -- Insert results
        INSERT INTO data_monitoring_results (
            table_name,
            schema_name,
            cadence,
            missing_dates,
            missing_count,
            status,
            message
        ) VALUES (
            config_record.table_name,
            config_record.schema_name,
            config_record.cadence,
            missing_list,
            COALESCE(array_length(missing_date_list, 1), 0),
            result_status,
            result_message
        );
        
        -- Return row
        table_name := config_record.table_name;
        schema_name := config_record.schema_name;
        cadence := config_record.cadence;
        missing_dates := missing_list;
        missing_count := COALESCE(array_length(missing_date_list, 1), 0);
        status := result_status;
        message := result_message;
        
        RETURN NEXT;
    END LOOP;
END;
$$;
```

## **Step 4: Create View for Easy Reporting**

```sql
CREATE OR REPLACE VIEW v_data_monitoring_latest AS
SELECT DISTINCT ON (table_name, schema_name)
    id,
    check_timestamp,
    table_name,
    schema_name,
    cadence,
    missing_dates,
    missing_count,
    status,
    message
FROM data_monitoring_results
ORDER BY table_name, schema_name, check_timestamp DESC;

-- View for problems only
CREATE OR REPLACE VIEW v_data_monitoring_issues AS
SELECT 
    check_timestamp,
    table_name,
    schema_name,
    cadence,
    missing_dates,
    missing_count,
    status,
    message
FROM v_data_monitoring_latest
WHERE status IN ('WARNING', 'CRITICAL')
ORDER BY 
    CASE status 
        WHEN 'CRITICAL' THEN 1
        WHEN 'WARNING' THEN 2
    END,
    missing_count DESC;
```

## **Step 5: Schedule with pg_cron**

```sql
-- Enable pg_cron extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule monitoring to run daily at 6 AM
SELECT cron.schedule(
    'data-freshness-check',
    '0 6 * * *',  -- Every day at 6 AM
    $$SELECT check_data_freshness()$$
);

-- View scheduled jobs
SELECT * FROM cron.job WHERE jobname = 'data-freshness-check';

-- To run manually for testing
SELECT * FROM check_data_freshness();
```

## **Step 6: Query Results**

```sql
-- View latest results for all tables
SELECT 
    table_name,
    cadence,
    missing_dates,
    missing_count,
    status,
    message,
    check_timestamp
FROM v_data_monitoring_latest
ORDER BY status DESC, missing_count DESC;

-- View only issues
SELECT * FROM v_data_monitoring_issues;

-- View history for specific table
SELECT 
    check_timestamp,
    missing_count,
    status,
    message
FROM data_monitoring_results
WHERE table_name = 'orders'
ORDER BY check_timestamp DESC
LIMIT 10;

-- Summary by status
SELECT 
    status,
    COUNT(*) as table_count,
    SUM(missing_count) as total_missing
FROM v_data_monitoring_latest
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'CRITICAL' THEN 1
        WHEN 'WARNING' THEN 2
        WHEN 'OK' THEN 3
    END;
```

---

# **Option 2: Azure Function Solution (Python)**

## **Complete Azure Function Code**

```python
import azure.functions as func
import logging
import os
import json
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from azure.identity import DefaultAzureCredential

app = func.FunctionApp()

# Schedule: Run daily at 6 AM UTC
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=False)
def data_freshness_monitor(myTimer: func.TimerRequest) -> None:
    """Monitor data freshness across multiple tables"""
    logging.info('=' * 60)
    logging.info('Starting data freshness monitoring...')
    logging.info('=' * 60)
    
    try:
        results = check_all_tables()
        
        # Log summary
        issues = [r for r in results if r['status'] in ['WARNING', 'CRITICAL']]
        
        if issues:
            logging.warning(f'Found {len(issues)} table(s) with issues!')
            send_alert_email(issues)
        else:
            logging.info('✓ All tables have current data')
        
        # Log details
        for result in results:
            if result['status'] == 'OK':
                logging.info(f"✓ {result['table_name']} ({result['cadence']}): OK")
            else:
                logging.warning(
                    f"⚠️ {result['table_name']} ({result['cadence']}): "
                    f"{result['missing_count']} missing dates"
                )
        
    except Exception as e:
        logging.error(f'Monitoring failed: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())


# HTTP endpoint for manual testing
@app.route(route="check-data-freshness", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def check_data_freshness_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint to manually trigger data freshness check"""
    logging.info('HTTP trigger - data freshness check')
    
    try:
        results = check_all_tables()
        
        # Format response
        response = {
            "check_timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_tables": len(results),
                "ok": len([r for r in results if r['status'] == 'OK']),
                "warning": len([r for r in results if r['status'] == 'WARNING']),
                "critical": len([r for r in results if r['status'] == 'CRITICAL'])
            },
            "results": results
        }
        
        return func.HttpResponse(
            json.dumps(response, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f'Error: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def get_db_connection():
    """Get database connection using Managed Identity"""
    from azure.identity import DefaultAzureCredential
    
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    
    # Get token for PostgreSQL
    credential = DefaultAzureCredential()
    token_response = credential.get_token(
        "https://ossrdbms-aad.database.windows.net/.default"
    )
    
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=token_response.token,
        sslmode='require',
        cursor_factory=RealDictCursor
    )
    
    return conn


def get_monitoring_config():
    """Get list of tables to monitor from database or configuration"""
    
    # Option 1: From database table
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT table_name, schema_name, date_column, cadence, description
            FROM data_monitoring_config
            WHERE is_active = true
        """)
        
        config = cur.fetchall()
        cur.close()
        conn.close()
        
        return config
        
    except Exception as e:
        logging.warning(f'Could not read config from database: {e}')
        
        # Option 2: Fallback to environment variable or hardcoded config
        return get_default_config()


def get_default_config():
    """Default configuration if database config table doesn't exist"""
    
    # This can be loaded from environment variable as JSON
    config_json = os.environ.get('MONITORING_CONFIG')
    
    if config_json:
        return json.loads(config_json)
    
    # Hardcoded fallback
    return [
        {
            'table_name': 'orders',
            'schema_name': 'public',
            'date_column': 'created_at',
            'cadence': 'daily',
            'description': 'Daily order transactions'
        },
        {
            'table_name': 'sales_summary',
            'schema_name': 'public',
            'date_column': 'report_date',
            'cadence': 'weekly',
            'description': 'Weekly sales reports'
        },
        {
            'table_name': 'monthly_revenue',
            'schema_name': 'public',
            'date_column': 'month_date',
            'cadence': 'monthly',
            'description': 'Monthly revenue'
        }
    ]


def check_all_tables():
    """Check all configured tables for missing data"""
    
    config = get_monitoring_config()
    results = []
    
    for table_config in config:
        try:
            result = check_single_table(table_config)
            results.append(result)
        except Exception as e:
            logging.error(f"Error checking {table_config['table_name']}: {e}")
            results.append({
                'table_name': table_config['table_name'],
                'schema_name': table_config.get('schema_name', 'public'),
                'cadence': table_config['cadence'],
                'missing_dates': [],
                'missing_count': 0,
                'status': 'ERROR',
                'message': f'Error: {str(e)}'
            })
    
    return results


def check_single_table(config):
    """Check a single table for missing data"""
    
    table_name = config['table_name']
    schema_name = config.get('schema_name', 'public')
    date_column = config['date_column']
    cadence = config['cadence']
    
    logging.info(f"Checking {schema_name}.{table_name} ({cadence})...")
    
    # Get expected date range
    end_date = date.today()
    
    if cadence == 'daily':
        start_date = end_date - timedelta(days=7)
        expected_dates = generate_daily_dates(start_date, end_date)
    elif cadence == 'weekly':
        start_date = end_date - relativedelta(months=1)
        expected_dates = generate_weekly_dates(start_date, end_date)
    elif cadence == 'monthly':
        start_date = end_date - relativedelta(months=3)
        expected_dates = generate_monthly_dates(start_date, end_date)
    else:
        raise ValueError(f"Unknown cadence: {cadence}")
    
    # Query database for existing dates
    conn = get_db_connection()
    cur = conn.cursor()
    
    if cadence == 'daily':
        query = f"""
            SELECT DISTINCT DATE({date_column}) as date_value
            FROM {schema_name}.{table_name}
            WHERE {date_column} >= %s AND {date_column} <= %s
            ORDER BY date_value
        """
    elif cadence == 'weekly':
        query = f"""
            SELECT DISTINCT DATE_TRUNC('week', {date_column})::DATE as date_value
            FROM {schema_name}.{table_name}
            WHERE {date_column} >= %s AND {date_column} <= %s
            ORDER BY date_value
        """
    else:  # monthly
        query = f"""
            SELECT DISTINCT DATE_TRUNC('month', {date_column})::DATE as date_value
            FROM {schema_name}.{table_name}
            WHERE {date_column} >= %s AND {date_column} <= %s
            ORDER BY date_value
        """
    
    cur.execute(query, (start_date, end_date))
    existing_dates = {row['date_value'] for row in cur.fetchall()}
    
    cur.close()
    conn.close()
    
    # Find missing dates
    missing_dates = [d for d in expected_dates if d not in existing_dates]
    
    # Determine status
    missing_count = len(missing_dates)
    
    if missing_count == 0:
        status = 'OK'
        message = 'All expected dates have data'
    elif missing_count <= 2:
        status = 'WARNING'
        message = f'{missing_count} missing date(s)'
    else:
        status = 'CRITICAL'
        message = f'{missing_count} missing date(s) - requires attention'
    
    return {
        'table_name': table_name,
        'schema_name': schema_name,
        'cadence': cadence,
        'missing_dates': [d.isoformat() for d in missing_dates],
        'missing_count': missing_count,
        'status': status,
        'message': message
    }


def generate_daily_dates(start_date, end_date):
    """Generate list of daily dates"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def generate_weekly_dates(start_date, end_date):
    """Generate list of weekly dates (Mondays)"""
    dates = []
    # Start from the Monday of the start week
    current = start_date - timedelta(days=start_date.weekday())
    while current <= end_date:
        dates.append(current)
        current += timedelta(weeks=1)
    return dates


def generate_monthly_dates(start_date, end_date):
    """Generate list of monthly dates (first day of month)"""
    dates = []
    # Start from first day of start month
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        dates.append(current)
        # Move to first day of next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return dates


def send_alert_email(issues):
    """Send email alert for issues found"""
    
    try:
        from azure.communication.email import EmailClient
        
        connection_string = os.environ.get('COMMUNICATION_SERVICES_CONNECTION_STRING')
        sender_address = os.environ.get('SENDER_EMAIL')
        recipient_address = os.environ.get('ALERT_EMAIL')
        
        if not all([connection_string, sender_address, recipient_address]):
            logging.warning('Email not configured, skipping alert')
            return
        
        # Build email content
        email_body = "Data Freshness Issues Detected\n"
        email_body += "=" * 60 + "\n\n"
        
        for issue in issues:
            email_body += f"Table: {issue['table_name']}\n"
            email_body += f"Cadence: {issue['cadence']}\n"
            email_body += f"Status: {issue['status']}\n"
            email_body += f"Missing Count: {issue['missing_count']}\n"
            email_body += f"Missing Dates: {', '.join(issue['missing_dates'][:10])}"
            if len(issue['missing_dates']) > 10:
                email_body += f" ... and {len(issue['missing_dates']) - 10} more"
            email_body += "\n\n" + "-" * 60 + "\n\n"
        
        email_body += f"\nCheck timestamp: {datetime.utcnow()} UTC\n"
        
        # Send email
        email_client = EmailClient.from_connection_string(connection_string)
        
        message = {
            "senderAddress": sender_address,
            "recipients": {
                "to": [{"address": recipient_address}]
            },
            "content": {
                "subject": f"⚠️ Data Freshness Alert: {len(issues)} Table(s) Missing Data",
                "plainText": email_body
            }
        }
        
        poller = email_client.begin_send(message)
        result = poller.result()
        
        logging.info(f'✓ Alert email sent. Message ID: {result["id"]}')
        
    except Exception as e:
        logging.error(f'Failed to send alert email: {e}')
```

## **Environment Variables for Azure Function**

Add to Function App configuration:

```
DB_HOST = your-server.postgres.database.azure.com
DB_NAME = your_database
DB_USER = dataplatform
DB_TABLE = (not needed for this function)

COMMUNICATION_SERVICES_CONNECTION_STRING = endpoint=https://...
SENDER_EMAIL = DoNotReply@....azurecomm.net
ALERT_EMAIL = admin@company.com

# Optional: JSON configuration if not using database table
MONITORING_CONFIG = [{"table_name":"orders","schema_name":"public","date_column":"created_at","cadence":"daily"}]
```

## **requirements.txt for Azure Function**

```txt
azure-functions
psycopg2-binary
azure-identity
azure-communication-email
python-dateutil
```

---

# **Comparison: pg_cron vs Azure Function**

| Feature | pg_cron | Azure Function |
|---------|---------|----------------|
| **Setup Complexity** | Medium | Medium |
| **Maintenance** | Low | Low |
| **Alerting** | Need additional setup | Built-in email |
| **Flexibility** | SQL only | Python - very flexible |
| **Cost** | Free | Free tier available |
| **Monitoring** | PostgreSQL logs | Azure Monitor |
| **Best For** | Database-centric | Cloud-native, integrations |

---

# **My Recommendation**

**Start with PostgreSQL (pg_cron)** for:
- ✅ Simpler setup if you're comfortable with SQL
- ✅ Everything in one place (database)
- ✅ No external dependencies
- ✅ Direct access to data

**Use Azure Function** for:
- ✅ Better integration with Azure services
- ✅ Easier email alerting
- ✅ More flexible logic (Python)
- ✅ Better monitoring and logs

---

# **Quick Start Guide**

## **For pg_cron approach:**

1. Run Step 1 SQL (create tables)
2. Run Step 2 SQL (add your tables to monitor)
3. Run Step 3 SQL (create function)
4. Run Step 4 SQL (create views)
5. Run Step 5 SQL (schedule with pg_cron)
6. Test: `SELECT * FROM check_data_freshness();`

## **For Azure Function approach:**

1. Create new Azure Function or add to existing
2. Copy the Python code
3. Update requirements.txt
4. Add environment variables
5. Deploy
6. Test via HTTP endpoint
