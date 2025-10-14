Use  **token-based authentication with Managed Identity** is much more secure. 
 

---

## **Step 1: Enable Managed Identity**

Remember that **Identity** setting we discussed earlier? Now we need to turn it **ON**.

1. In your Function App, go to **Settings** → **Identity**
2. Under **System assigned** tab
3. Set **Status** to **On**
4. Click **Save**
5. Click **Yes** to confirm
6. **Copy the Object (principal) ID** that appears (you'll need it)

---

## **Step 2: Configure PostgreSQL for Azure AD Authentication**

1. Go to your **PostgreSQL Flexible Server** in Azure Portal
2. Go to **Settings** → **Authentication**
3. **Authentication method**: Select **Azure Active Directory authentication only** (or **PostgreSQL and Azure Active Directory authentication**)
4. Click **Add Azure AD admin** and add yourself as admin
5. Click **Save**

---

## **Step 3: Grant Function App Access to PostgreSQL**

Now we need to create a database user for your Function App's Managed Identity.

### **Option A: Using Azure Portal (if available)**

Some PostgreSQL servers have this option:
1. In PostgreSQL server, go to **Settings** → **Authentication**  
2. Look for **"Azure AD users"** or **"Add user"**
3. Add your Function App name

### **Option B: Using SQL (More reliable)**

1. Connect to your PostgreSQL using Azure Cloud Shell or any SQL client
2. Run these commands:

```sql
-- Connect as Azure AD admin first

-- Create role for your Function App
-- Replace "dataplatform" with your Function App name
CREATE ROLE "dataplatform" WITH LOGIN;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE your_database_name TO "dataplatform";
GRANT USAGE ON SCHEMA public TO "dataplatform";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "dataplatform";
GRANT SELECT ON your_table_name TO "dataplatform";

-- If you need to grant to future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "dataplatform";
```

**Important:** The role name must **exactly match** your Function App name: `dataplatform`

---

## **Step 4: Update Function Code for Token Authentication**

Now update your function code to use Managed Identity instead of passwords:

```python
import azure.functions as func
import logging
import os
import sys
import subprocess

def install_if_missing(package, import_name=None):
    """Install package on first run if not available"""
    if import_name is None:
        import_name = package.replace('-', '_')
    try:
        __import__(import_name)
        return True
    except ImportError:
        logging.info(f'Installing {package}...')
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
            return True
        except Exception as e:
            logging.error(f'Failed to install {package}: {e}')
            return False

app = func.FunctionApp()

# Timer trigger - runs every 6 hours
@app.schedule(schedule="0 0 */6 * * *", arg_name="myTimer", run_on_startup=False)
def check_database_records(myTimer: func.TimerRequest) -> None:
    logging.info('=' * 50)
    logging.info('Starting database check with Managed Identity...')
    logging.info('=' * 50)
    
    # Install required packages
    if not install_if_missing('psycopg2-binary', 'psycopg2'):
        logging.error('Cannot proceed without psycopg2')
        return
    
    if not install_if_missing('azure-identity'):
        logging.error('Cannot proceed without azure-identity')
        return
    
    try:
        import psycopg2
        from azure.identity import DefaultAzureCredential
        
        # Get database connection info from environment variables
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')  # Your Function App name
        
        if not all([db_host, db_name, db_user]):
            logging.error('Missing database configuration!')
            logging.error('Required: DB_HOST, DB_NAME, DB_USER')
            return
        
        logging.info(f'Database: {db_host}/{db_name}')
        logging.info(f'User: {db_user}')
        
        # Get Azure AD access token using Managed Identity
        logging.info('Getting access token from Managed Identity...')
        credential = DefaultAzureCredential()
        token_response = credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        access_token = token_response.token
        
        logging.info('✓ Token obtained successfully')
        
        # Connect to PostgreSQL using the token as password
        logging.info('Connecting to PostgreSQL with token...')
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=access_token,
            sslmode='require'
        )
        
        logging.info('✓ Connected successfully!')
        
        cur = conn.cursor()
        
        # Get table name from environment variable
        table_name = os.environ.get('DB_TABLE', 'your_table_name')
        
        query = f"SELECT COUNT(*) FROM {table_name}"
        logging.info(f'Executing: {query}')
        
        cur.execute(query)
        record_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        logging.info(f'✓ Query successful!')
        logging.info(f'✓ Record count: {record_count}')
        logging.info(f'✓ Threshold: 10')
        
        # Check if below threshold
        if record_count < 10:
            logging.warning('⚠️ ALERT: Record count below threshold!')
            send_email_alert(record_count)
        else:
            logging.info('✓ Status: OK (above threshold)')
        
        logging.info('=' * 50)
        logging.info('Database check completed')
        logging.info('=' * 50)
        
    except Exception as e:
        logging.error('=' * 50)
        logging.error(f'ERROR: {str(e)}')
        logging.error('=' * 50)
        import traceback
        logging.error(traceback.format_exc())


def send_email_alert(record_count):
    """Send email alert via SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    try:
        # Get SMTP settings from environment variables
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        recipient_email = os.environ.get('ALERT_EMAIL', 'admin@company.com')
        
        if not all([smtp_server, smtp_user, smtp_password]):
            logging.error('Email not configured! Missing SMTP settings')
            return
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f'⚠️ Database Alert: Only {record_count} Records!'
        
        body = f"""
DATABASE ALERT
{'=' * 50}

⚠️  Record count is below threshold!

Current count: {record_count}
Threshold:     10
Status:        CRITICAL

Time:          {datetime.utcnow()} UTC

Please investigate immediately.

{'=' * 50}
This is an automated alert from Azure Functions.
Authentication: Managed Identity (no passwords)
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        logging.info(f'Sending email to {recipient_email}...')
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logging.info('✓ Email sent successfully!')
        
    except Exception as e:
        logging.error(f'Failed to send email: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())
```

---

## **Step 5: Update Environment Variables**

Go to **Settings** → **Environment variables** and add these:

### **Database Settings (NO PASSWORD!):**

```
Name: DB_HOST
Value: yourserver.postgres.database.azure.com

Name: DB_NAME  
Value: your_database_name

Name: DB_USER
Value: dataplatform
(This must match your Function App name exactly!)

Name: DB_TABLE
Value: your_table_name
```

### **Email Settings (same as before):**

```
Name: SMTP_SERVER
Value: smtp.office365.com

Name: SMTP_PORT
Value: 587

Name: SMTP_USER
Value: your-email@company.com

Name: SMTP_PASSWORD
Value: your-password

Name: ALERT_EMAIL
Value: admin@company.com
```

Click **Apply** to save.

---

## **Step 6: Test the Connection**

Create a simple test function first to verify the Managed Identity works:

```python
import azure.functions as func
import logging
import os
import sys
import subprocess

def install_if_missing(package, import_name=None):
    if import_name is None:
        import_name = package.replace('-', '_')
    try:
        __import__(import_name)
        return True
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        return True

app = func.FunctionApp()

@app.schedule(schedule="0 */30 * * * *", arg_name="myTimer", run_on_startup=False)
def test_managed_identity(myTimer: func.TimerRequest) -> None:
    logging.info('Testing Managed Identity setup...')
    
    install_if_missing('azure-identity')
    
    try:
        from azure.identity import DefaultAzureCredential
        
        logging.info('✓ azure-identity imported')
        
        # Test getting token
        credential = DefaultAzureCredential()
        token_response = credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        
        logging.info('✓ Token obtained successfully!')
        logging.info(f'  Token length: {len(token_response.token)} chars')
        logging.info(f'  Expires in: {token_response.expires_on}')
        
        # Test database connection
        install_if_missing('psycopg2-binary', 'psycopg2')
        import psycopg2
        
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        
        logging.info(f'Connecting to: {db_host}')
        logging.info(f'Database: {db_name}')
        logging.info(f'User: {db_user}')
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=token_response.token,
            sslmode='require'
        )
        
        logging.info('✓ Database connection successful!')
        
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        logging.info(f'✓ PostgreSQL version: {version}')
        
        cur.close()
        conn.close()
        
        logging.info('✓ All tests passed!')
        
    except Exception as e:
        logging.error(f'✗ Test failed: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())
```

---

## **Troubleshooting**

### If you get "password authentication failed for user"

This means the PostgreSQL user wasn't created properly. Run this SQL as your Azure AD admin:

```sql
-- Connect as your Azure AD admin
CREATE ROLE "dataplatform" WITH LOGIN;
GRANT CONNECT ON DATABASE your_db TO "dataplatform";
GRANT USAGE ON SCHEMA public TO "dataplatform";
GRANT SELECT ON your_table TO "dataplatform";
```

### If you get "DefaultAzureCredential failed to retrieve token"

- Make sure System Assigned Identity is **ON**
- Restart the Function App
- Check that the Function App name matches the PostgreSQL role name

### If you get "no pg_hba.conf entry for host"

- In PostgreSQL → **Networking** → **Firewall rules**
- Add rule: `0.0.0.0` to `0.0.0.0` for Azure services

---

## **Summary of Changes**

**Old way (insecure):**
```
DB_CONNECTION_STRING = "host=... user=admin password=SecretPass123 ..."
```

**New way (secure with Managed Identity):**
```
DB_HOST = "server.postgres.database.azure.com"
DB_NAME = "mydb"
DB_USER = "dataplatform"  # Function App name
# NO PASSWORD! Token is fetched automatically
```

**Benefits:**
- ✅ No passwords stored anywhere
- ✅ Tokens rotate automatically
- ✅ Audit trail in Azure AD
- ✅ Compliant with security best practices
- ✅ No credential management needed

---

Here’s a ready-to-run Azure Function (Python) that runs on a schedule, queries Postgres, and emails if the recent row count is below a threshold.

---

# 1) Folder layout

```
pg-freshness-func/
├─ function_app.py
├─ freshness/__init__.py
├─ freshness/function.json
├─ requirements.txt
└─ local.settings.json         # (local dev only)
```

---

# 2) The timer-triggered function

`freshness/__init__.py`

```python
import os
import json
import logging
from datetime import timezone, datetime
import azure.functions as func
import psycopg2
from azure.identity import DefaultAzureCredential
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def _aad_token():
    # Azure AD token for Azure Database for PostgreSQL
    # Resource: https://ossrdbms-aad.database.windows.net/.default
    cred = DefaultAzureCredential()
    token = cred.get_token("https://ossrdbms-aad.database.windows.net/.default")
    return token.token


def _pg_connect():
    """
    Supports two modes:
      AAD (recommended): set PG_AUTH=AAD and provide PGHOST, PGDATABASE, PGUSER
      Password: set PG_AUTH=PASSWORD and provide PGHOST, PGDATABASE, PGUSER, PGPASSWORD
    """
    host = os.environ["PGHOST"]
    db = os.environ["PGDATABASE"]
    user = os.environ["PGUSER"]
    sslmode = os.environ.get("PGSSLMODE", "require")
    auth_mode = os.environ.get("PG_AUTH", "AAD").upper()

    if auth_mode == "AAD":
        password = _aad_token()
    else:
        password = os.environ["PGPASSWORD"]

    return psycopg2.connect(
        host=host,
        dbname=db,
        user=user,
        password=password,
        sslmode=sslmode,
        connect_timeout=15,
    )


def _send_email(stale_msg: str):
    api_key = os.environ["SENDGRID_API_KEY"]
    to_emails = [e.strip() for e in os.environ["ALERT_TO"].split(",") if e.strip()]
    from_email = os.environ.get("ALERT_FROM", "alerts@no-reply.local")

    sg = SendGridAPIClient(api_key)
    mail = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject=os.environ.get("ALERT_SUBJECT", "Postgres freshness alert"),
        plain_text_content=stale_msg,
    )
    sg.send(mail)


def _check_one(conn, table_fqn: str, ts_column: str, window_hours: int, min_rows: int):
    """Returns (ok: bool, details: dict)"""
    schema, table = table_fqn.split(".", 1)
    with conn.cursor() as cur:
        # Count rows in the recent window
        cur.execute(
            f"""
            select
              count(*) as rows_window,
              max({psycopg2.sql.Identifier(ts_column).string}) as last_ts
            from {psycopg2.sql.Identifier(schema).string}.{psycopg2.sql.Identifier(table).string}
            where {psycopg2.sql.Identifier(ts_column).string} >= now() - make_interval(hours => %s)
            """,
            (window_hours,),
        )
        rows_window, last_ts = cur.fetchone()

    lag_hours = None
    if last_ts is not None:
        lag_hours = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600.0

    ok = rows_window >= min_rows
    return ok, {
        "table": table_fqn,
        "ts_column": ts_column,
        "rows_window": int(rows_window),
        "min_rows": int(min_rows),
        "window_hours": int(window_hours),
        "last_ts": None if last_ts is None else last_ts.isoformat(),
        "lag_hours": lag_hours,
    }


def load_targets():
    """
    Targets are provided via env var TARGETS_JSON for flexibility, e.g.:

    [
      {"table": "events.pttreceive", "ts_column": "created_at", "window_hours": 6, "min_rows": 10},
      {"table": "events.gpsstart",   "ts_column": "created_at", "window_hours": 6, "min_rows": 10}
    ]
    """
    raw = os.environ.get("TARGETS_JSON", "").strip()
    if not raw:
        # Single-table fallback using simple env vars
        return [{
            "table": os.environ["TABLE"],
            "ts_column": os.environ["TS_COLUMN"],
            "window_hours": int(os.environ.get("WINDOW_HOURS", "6")),
            "min_rows": int(os.environ.get("MIN_ROWS", "10")),
        }]
    return json.loads(raw)


def format_alert(stales):
    lines = []
    lines.append("One or more Postgres sources look stale (below min_rows in the recent window):\n")
    for s in stales:
        lh = "n/a" if s["lag_hours"] is None else f"{s['lag_hours']:.2f}h"
        lines.append(
            f"- {s['table']} | rows_in_{s['window_hours']}h={s['rows_window']} "
            f"(min {s['min_rows']}) | last_ts={s['last_ts']} | lag={lh}"
        )
    return "\n".join(lines)


def main(mytimer: func.TimerRequest) -> None:
    logging.info("freshness: timer fired")
    targets = load_targets()
    stales = []

    try:
        with _pg_connect() as conn:
            for t in targets:
                ok, details = _check_one(
                    conn,
                    table_fqn=t["table"],
                    ts_column=t["ts_column"],
                    window_hours=int(t["window_hours"]),
                    min_rows=int(t["min_rows"]),
                )
                logging.info("freshness: %s => %s", details["table"], "OK" if ok else "STALE")
                if not ok:
                    stales.append(details)
    except Exception as e:
        # If the health check itself fails, send an operator email
        msg = f"freshness: failed to execute check: {e}"
        logging.exception(msg)
        _send_email(msg)
        return

    if stales:
        _send_email(format_alert(stales))
    else:
        logging.info("freshness: all targets OK")
```

`freshness/function.json`

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */15 * * * *"
    }
  ]
}
```

> The schedule above runs every 15 minutes. Adjust as needed.

---

# 3) Host entry point

`function_app.py`

```python
import azure.functions as func

app = func.FunctionApp()

# The folder "freshness" contains the timer function.
# For v4.x Python model, discovery is automatic if you prefer;
# Keeping this file minimal for clarity.
```

---

# 4) Dependencies

`requirements.txt`

```
azure-functions
psycopg2-binary
azure-identity
sendgrid
```

---

# 5) Local settings (for dev only)

`local.settings.json` (do not commit secrets)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "PGHOST": "your-flexible-server.postgres.database.azure.com",
    "PGDATABASE": "weavix",
    "PGUSER": "your-aad-user-or-managed-identity-upn",
    "PGSSLMODE": "require",
    "PG_AUTH": "AAD",

    "TABLE": "events.pttreceive",
    "TS_COLUMN": "created_at",
    "WINDOW_HOURS": "6",
    "MIN_ROWS": "10",

    "TARGETS_JSON": "",

    "SENDGRID_API_KEY": "<your-sendgrid-api-key>",
    "ALERT_TO": "alice@example.com,bob@example.com",
    "ALERT_FROM": "alerts@example.com",
    "ALERT_SUBJECT": "Postgres freshness alert"
  }
}
```

> For multiple tables, leave `TABLE/TS_COLUMN/WINDOW_*` blank and set `TARGETS_JSON` to a JSON array (see docstring in code).

---

# 6) Postgres permissions (AAD recommended)

In your Postgres (Flexible Server) session as an admin:

```sql
-- Create a Postgres role mapped to your Function App's managed identity (or your AAD user)
-- From an AAD admin session:
SET aad_validate_oids_in_tenant = off;

CREATE ROLE "your-function-mi-name" WITH LOGIN IN ROLE azure_ad_user;
GRANT CONNECT ON DATABASE weavix TO "your-function-mi-name";
GRANT USAGE ON SCHEMA events TO "your-function-mi-name";
GRANT SELECT ON ALL TABLES IN SCHEMA events TO "your-function-mi-name";
-- (If you watch tables in other schemas, grant similarly.)
```

Then set `PGUSER` to that AAD principal (UPN-style or the exact role name you created). The code fetches an AAD token automatically.

---

# 7) Deploy

If you created the Function App in the Azure Portal already, the easiest path is Zip Deploy from your machine:

```
# From the project root (pg-freshness-func/)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Zip the app
zip -r app.zip .

# Deploy (replace placeholders)
az functionapp deployment source config-zip \
  -g <your-rg> -n <your-funcapp-name> \
  --src app.zip
```

Now set the app settings (environment variables) on the Function App:

```
az functionapp config appsettings set -g <your-rg> -n <your-funcapp-name> --settings \
  PGHOST=your-flexible-server.postgres.database.azure.com \
  PGDATABASE=weavix \
  PGUSER="your-function-mi-name" \
  PGSSLMODE=require \
  PG_AUTH=AAD \
  TABLE=events.pttreceive \
  TS_COLUMN=created_at \
  WINDOW_HOURS=6 \
  MIN_ROWS=10 \
  SENDGRID_API_KEY=<key> \
  ALERT_TO="alice@example.com,bob@example.com" \
  ALERT_FROM="alerts@example.com" \
  ALERT_SUBJECT="Postgres freshness alert"
```

If you enabled **Managed Identity** on the Function App, you don’t need any password—AAD token auth is used.

---

# 8) Using Microsoft Graph instead of SendGrid (optional)

If you prefer sending email via Microsoft 365:

* Grant your Function’s **managed identity** the **Mail.Send** application permission in Entra ID for Microsoft Graph, and **admin-consent** it.
* Use `azure-identity` + `msgraph-sdk` (or raw `requests`) to call `POST https://graph.microsoft.com/v1.0/users/{sender}/sendMail`.

If you want this variant, say the word and I’ll drop in the Graph-based `send_email()` function.

---

# 9) Operational tips

* Index the timestamp column(s) you query:

  ```
  create index concurrently on events.pttreceive (created_at desc);
  ```
* If you monitor several tables, use `TARGETS_JSON` to list them all and send a single consolidated email.
* To avoid alert spam, you can add simple deduping: keep a small blob or App Setting `LAST_ALERT_HASH` and only send if the payload changed; or throttle to once per hour while stale.

---

If you tell me the exact table(s) and timestamp column(s), I can pre-fill `TARGETS_JSON` for you.

