## How to connect to Postgres from Azure Function

For an Azure Function connecting to Azure Managed PostgreSQL, 
you should use a **Managed Identity** instead of your personal user account. Here's how:

## 1. Enable Managed Identity for Your Azure Function

```bash
# Enable system-assigned managed identity for your function app
az functionapp identity assign \
  --name <your-function-app-name> \
  --resource-group <your-resource-group>

# Get the identity's Object ID (you'll need this)
IDENTITY_OBJECT_ID=$(az functionapp identity show \
  --name <your-function-app-name> \
  --resource-group <your-resource-group> \
  --query principalId -o tsv)

echo "Managed Identity Object ID: $IDENTITY_OBJECT_ID"
```

## 2. Grant Database Access to the Managed Identity

Connect to PostgreSQL and create a user for the managed identity:

```sql
-- Connect as admin first
psql "host=weavix-dev-pg.postgres.database.azure.com ..."

-- Create Azure AD user for the managed identity
-- Replace with your function app name
SET aad_validate_oids_in_tenant = off;
CREATE ROLE "<your-function-app-name>" WITH LOGIN IN ROLE azure_ad_user;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE weavix TO "<your-function-app-name>";
GRANT USAGE ON SCHEMA events TO "<your-function-app-name>";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA events TO "<your-function-app-name>";
```

## 3. Python Code for Azure Function

```python
import psycopg2
from azure.identity import DefaultAzureCredential
import os

def connect_to_postgres():
    # Get token using managed identity
    credential = DefaultAzureCredential()
    token_response = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
    access_token = token_response.token
    
    # PostgreSQL connection
    pg_host = os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
    pg_database = os.environ.get('PG_DB', 'weavix')
    
    # IMPORTANT: The user is your function app name
    # This is the name of the managed identity
    pg_user = os.environ.get('PG_USER', '<your-function-app-name>')
    
    conn = psycopg2.connect(
        host=pg_host,
        database=pg_database,
        user=pg_user,  # Your function app name
        password=access_token,  # Use the access token as password
        sslmode='require',
        port=5432
    )
    
    return conn

# Usage in your Azure Function
def main(req):
    try:
        conn = connect_to_postgres()
        cursor = conn.cursor()
        
        # Your query
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        print(f"PostgreSQL version: {result[0]}")
        
        cursor.close()
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}
```

## 4. Add Environment Variables

In your Function App settings (or `local.settings.json` for local development):

```json
{
  "Values": {
    "PG_HOST": "weavix-dev-pg.postgres.database.azure.com",
    "PG_DB": "weavix",
    "PG_USER": "<your-function-app-name>"
  }
}
```

## 5. Alternative: Use Connection String with Token

```python
import psycopg2
from azure.identity import DefaultAzureCredential

def get_postgres_connection():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
    
    connection_string = (
        f"host=weavix-dev-pg.postgres.database.azure.com "
        f"port=5432 "
        f"dbname=weavix "
        f"user=<your-function-app-name> "
        f"password={token.token} "
        f"sslmode=require"
    )
    
    return psycopg2.connect(connection_string)
```

## 6. Install Required Packages

In your `requirements.txt`:

```
psycopg2-binary
azure-identity
```

## Key Points:

1. ✅ **User is your Function App name** - not your personal email
2. ✅ **Password is the access token** - not a static password
3. ✅ **Token expires** - you may need to refresh it for long-running connections
4. ✅ **Works same as your Kubernetes setup** - uses the same pattern as your telemetry consumer

## For Token Refresh (if needed):

```python
class PostgresConnection:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.conn = None
        self.token_expiry = None
        
    def get_connection(self):
        # Refresh token if expired or close to expiry
        if self.conn is None or self._token_needs_refresh():
            self._reconnect()
        return self.conn
    
    def _token_needs_refresh(self):
        # Refresh 5 minutes before expiry
        if self.token_expiry is None:
            return True
        return (self.token_expiry - time.time()) < 300
    
    def _reconnect(self):
        if self.conn:
            self.conn.close()
        
        token_response = self.credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        self.token_expiry = token_response.expires_on
        
        self.conn = psycopg2.connect(
            host='weavix-dev-pg.postgres.database.azure.com',
            database='weavix',
            user='<your-function-app-name>',
            password=token_response.token,
            sslmode='require'
        )
```

This approach matches what your Kubernetes pods are doing with `DefaultAzureCredential`! 🔐

* In an Azure Function, use **Managed Identity** and pass an **Entra (AAD) access token** as the PostgreSQL “password”.
* The `user` you put in the connection must be the **managed identity’s name** (or the **UPN** if you’re using a human user). ([Microsoft Learn][1])

Why & which account to use

* Best practice for apps is a **managed identity** (system-assigned or user-assigned) instead of a human user. You map that identity into Postgres and then your code asks Entra for a token at runtime—no secret stored. ([Microsoft Learn][1])
* If you really want to run the Function as a human user, use that user’s **UPN (e.g., `user@tenant.onmicrosoft.com`)** as `user` and still pass the Entra token as the password. Token audience must be `https://ossrdbms-aad.database.windows.net`. ([Microsoft Learn][2])

One-time setup (managed identity)

1. Enable Entra (AAD) auth on your **Azure Database for PostgreSQL – Flexible Server**. ([Microsoft Learn][2])
2. Ensure your Function App has a **managed identity** enabled.
3. In Postgres (connected as the Entra Admin), create a database role for that identity and grant permissions, e.g.:

```sql
-- Run in the 'postgres' database as the Entra Admin
select * from pgaadauth_create_principal('my-func-mi-name', false, false);

-- Then grant what the app needs (schema, tables, etc.)
grant usage on schema my_schema to "my-func-mi-name";
grant select, insert, update, delete on all tables in schema my_schema to "my-func-mi-name";
alter default privileges in schema my_schema grant select, insert, update, delete on tables to "my-func-mi-name";
```

The role name should match the **managed identity’s display name** you created above; Postgres will match the token to the role via the Entra object, not the literal text of the role, but using the MI’s name is the documented path. ([Microsoft Learn][1])

Azure Function (Python) code

```python
import os
import psycopg2
from azure.identity import DefaultAzureCredential

PG_HOST = os.environ["PG_HOST"]  # e.g. weavix-dev-pg.postgres.database.azure.com
PG_DB   = os.environ.get("PG_DB", "weavix")
PG_USER = os.environ["PG_USER"]  # use the managed identity *name* you created (e.g., "my-func-mi-name")

def get_pg_conn():
    # In Azure, DefaultAzureCredential will use the Function's managed identity
    cred = DefaultAzureCredential()

    # IMPORTANT: scope must be the ossrdbms-aad resource with `/.default`
    token = cred.get_token("https://ossrdbms-aad.database.windows.net/.default")

    # psycopg2 expects a string; use token.token
    conn = psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,            # for human user: their UPN (e.g., user@tenant.onmicrosoft.com)
        password=token.token,    # the Entra access token
        sslmode="require",
        connect_timeout=15,
    )
    return conn
```

Notes & gotchas

* **Username to use**

  * Managed identity: the **identity name** you created with `pgaadauth_create_principal('<identity_name>', …)`. ([Microsoft Learn][1])
  * Human user: their **UPN** (e.g., `mlubinsky_weavix.com#EXT#@weavix.onmicrosoft.com`). ([Microsoft Learn][2])
* **Token scope** must be `https://ossrdbms-aad.database.windows.net/.default` (or resource `https://ossrdbms-aad.database.windows.net` when using CLI). Wrong audience = “invalid audience claim”. ([Microsoft Learn][2])
* **Token lifetime** is short (≈5–60 minutes). Acquire a fresh token when opening a connection; don’t cache across function executions. ([Microsoft Learn][2])
* **Networking**: if your server is “Private access (VNet Integration)”, your Function must be integrated into the same VNet/subnet (or have private DNS resolve to the private endpoint). ([Microsoft Learn][3])

If you prefer to run as your own user from code (not recommended for Functions), set:

```python
PG_USER = "mlubinsky_weavix.com#EXT#@weavix.onmicrosoft.com"
token = DefaultAzureCredential().get_token("https://ossrdbms-aad.database.windows.net/.default")
# password = token.token  (same as above)
```

…and make sure that Entra user has a mapped role in the database with the right grants. ([Microsoft Learn][2])

This aligns with Microsoft’s guidance for Entra auth with PostgreSQL and for using managed identities to connect without secrets. ([Microsoft Learn][2])

Want me to add a tiny health-check function (runs `SELECT 1`) and a retry wrapper you can drop into your Function App?

[1]: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/security-connect-with-managed-identity "Connect with Managed Identity - Azure Database for PostgreSQL | Microsoft Learn"
[2]: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/security-entra-configure "Use Microsoft Entra ID Authentication - Azure Database for PostgreSQL | Microsoft Learn"
[3]: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/connect-python?utm_source=chatgpt.com "Connect Using Python - Azure Database for PostgreSQL"


## Under Function App -> Settings -> Identity there are 2 tabs.
System Assigned: On
Object (principal) ID : 04a9fcc9-de20-4078-a327-cf935088b0bb

It means: Your Azure Function already has a System-assigned Managed Identity enabled.

Object (principal) ID: 04a9fcc9-de20-4078-a327-cf935088b0bb

Now you need to grant this identity access to PostgreSQL:
 

**Object (principal) ID**: `04a9fcc9-de20-4078-a327-cf935088b0bb`

Now you need to grant this identity access to PostgreSQL:

## Step 1: Grant PostgreSQL Access to the Managed Identity

Connect to PostgreSQL as admin:

```bash
psql "host=weavix-dev-pg.postgres.database.azure.com \
      port=5432 \
      dbname=weavix \
      user=mlubinsky_weavix.com#EXT#@weavix.onmicrosoft.com \
      password=$(az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv) \
      sslmode=require"
```

Then run these SQL commands:

```sql
-- Get your Function App name (it's the identity username)
-- You can find it in: Portal → Function App → Overview → Name

-- Create Azure AD role for the managed identity
-- Replace <your-function-app-name> with actual name
SET aad_validate_oids_in_tenant = off;
CREATE ROLE "<your-function-app-name>" WITH LOGIN IN ROLE azure_ad_user;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE weavix TO "<your-function-app-name>";
GRANT USAGE ON SCHEMA public TO "<your-function-app-name>";
GRANT USAGE ON SCHEMA events TO "<your-function-app-name>";

-- Grant table permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "<your-function-app-name>";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA events TO "<your-function-app-name>";

-- Grant future table permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<your-function-app-name>";
ALTER DEFAULT PRIVILEGES IN SCHEMA events GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<your-function-app-name>";

-- Verify the role was created
\du
```

## Step 2: Update Your Python Code

```python
import psycopg2
from azure.identity import DefaultAzureCredential
import os
import logging

def get_postgres_connection():
    """Connect to PostgreSQL using Managed Identity"""
    try:
        # Get access token using managed identity
        credential = DefaultAzureCredential()
        token_response = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        access_token = token_response.token
        
        # Connection parameters
        pg_host = os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
        pg_database = os.environ.get('PG_DB', 'weavix')
        pg_user = os.environ.get('PG_USER')  # Your function app name
        
        if not pg_user:
            raise ValueError("PG_USER environment variable not set")
        
        logging.info(f"Connecting to PostgreSQL as user: {pg_user}")
        
        # Connect
        conn = psycopg2.connect(
            host=pg_host,
            database=pg_database,
            user=pg_user,
            password=access_token,  # Token as password
            sslmode='require',
            port=5432,
            connect_timeout=10
        )
        
        logging.info("Successfully connected to PostgreSQL")
        return conn
        
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {e}")
        raise

# Your function
def main(timer):
    logging.info('Timer triggered - starting CSV export')
    
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Your query
        cursor.execute("SELECT * FROM your_table LIMIT 10")
        results = cursor.fetchall()
        
        logging.info(f"Retrieved {len(results)} rows")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        raise
```

## Step 3: Set Environment Variables

In your Function App settings (Portal → Configuration → Application settings):

Add these settings:

```
PG_HOST = weavix-dev-pg.postgres.database.azure.com
PG_DB = weavix
PG_USER = <your-function-app-name>
```

To find your function app name:
```bash
# It's shown in the portal, or:
az functionapp list --query "[].name" -o table
```

## Step 4: Verify in PostgreSQL

After creating the role, verify it exists:

```sql
-- Check if role exists
SELECT rolname FROM pg_roles WHERE rolname = '<your-function-app-name>';

-- Check permissions
\du <your-function-app-name>
```

## Step 5: Test the Connection

Add this test to your function:

```python
def test_connection():
    """Test PostgreSQL connection"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logging.info(f"PostgreSQL version: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Connection test failed: {e}")
        return False
```

## Summary

Your managed identity Object ID is: `04a9fcc9-de20-4078-a327-cf935088b0bb`

This identity will authenticate as the PostgreSQL user with the same name as your Function App. Just need to:
1. ✅ Create the role in PostgreSQL
2. ✅ Grant permissions
3. ✅ Set `PG_USER` environment variable
4. ✅ Use the Python code above

The authentication flow is identical to your Kubernetes setup! 

Yes — to drop a TimescaleDB partition (chunk) using `drop_chunks()`, **you must be the owner of the hypertable**, or a superuser.

Here’s the breakdown:

---

### 🔒 Ownership Requirement

* **`drop_chunks()`** enforces ownership at the hypertable level.
* Only:

  * The **hypertable owner**, or
  * A **superuser**

  can execute `drop_chunks()` successfully.

Even if another role has been granted **ALL PRIVILEGES** or **EXECUTE** on the function, it will still fail unless that role **owns the hypertable** (or the session has assumed that role via `SET ROLE hypertable_owner;`).

---

### 🧩 Why This Restriction Exists

`drop_chunks()` physically deletes partitioned data and underlying storage.
Postgres’ privilege system treats that as a DDL-level operation, and DDL operations require table ownership.

TimescaleDB checks the owner to prevent accidental or unauthorized partition deletions.

---

### ✅ Workarounds

1. **Execute as the hypertable owner**:

   ```sql
   SET ROLE weavix_admins;  -- or the hypertable’s owner role
   SELECT drop_chunks('schema.table', older_than => '2025-10-01');
   ```

2. **Create a wrapper function owned by the hypertable owner**:

   ```sql
   CREATE OR REPLACE FUNCTION admin_drop_chunks(_table regclass, _older_than interval)
   RETURNS void
   LANGUAGE plpgsql
   SECURITY DEFINER
   AS $$
   BEGIN
     PERFORM drop_chunks(_table, older_than => _older_than);
   END;
   $$;
   ```

   Then grant EXECUTE to other users:

   ```sql
   GRANT EXECUTE ON FUNCTION admin_drop_chunks(regclass, interval) TO your_user;
   ```

   This lets non-owner roles call it indirectly.

---

### 🧠 Summary

| Role                                    | Can Call `drop_chunks()`? | Notes                                |
| --------------------------------------- | ------------------------- | ------------------------------------ |
| Hypertable owner                        | ✅                         | Full control                         |
| Superuser                               | ✅                         | Overrides ownership                  |
| Other user with privileges              | ❌                         | Fails due to ownership check         |
| Role executing SECURITY DEFINER wrapper | ✅                         | If wrapper owned by hypertable owner |

---

 
### your Managed Identity role needs *ownership* of the hypertable (not just privileges), or you must call `drop_chunks()` **through a SECURITY DEFINER wrapper owned by the hypertable owner**. 

Grants like CONNECT/USAGE/SELECT/INSERT/UPDATE are not enough.

Below is a clean, production-safe pattern that works on Azure Database for PostgreSQL (no superuser) and keeps ownership with a controlled role.

---

### 1) Make/confirm a dedicated owner for the hypertable(s)

Pick a role that will “own” the hypertable(s), e.g. `ts_owner` (this can be an existing owner such as `weavix_admins`).

```sql
-- Optional: create an explicit owner role
CREATE ROLE ts_owner NOLOGIN;

-- Make the hypertable owned by ts_owner (repeat per table)
ALTER TABLE events.pttpressed OWNER TO ts_owner;
-- (Owning the hypertable is what matters; Timescale manages its chunks.)
```

If `weavix_admins` is already the owner, you can use it instead of `ts_owner`.

---

### 2) Create a locked-down SECURITY DEFINER wrapper

Create the wrapper in a separate schema (e.g. `admin`), owned by the hypertable owner. Set a safe `search_path` to avoid hijacking.

```sql
-- Schema owned by the hypertable owner
CREATE SCHEMA IF NOT EXISTS admin AUTHORIZATION ts_owner;

-- Wrapper: drop older than a relative interval (common case)
CREATE OR REPLACE FUNCTION admin.drop_chunks_older_than(_tbl regclass, _older_than interval)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, admin
AS $$
BEGIN
  PERFORM drop_chunks(_tbl, older_than => _older_than);
END;
$$;

-- Optional: wrapper for an explicit time window
CREATE OR REPLACE FUNCTION admin.drop_chunks_between(_tbl regclass, _newer_than timestamptz, _older_than timestamptz)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, admin
AS $$
BEGIN
  PERFORM drop_chunks(_tbl, newer_than => _newer_than, older_than => _older_than);
END;
$$;

-- Lock down and grant only EXECUTE
REVOKE ALL ON FUNCTION admin.drop_chunks_older_than(regclass, interval) FROM PUBLIC;
REVOKE ALL ON FUNCTION admin.drop_chunks_between(regclass, timestamptz, timestamptz) FROM PUBLIC;

-- Grant EXECUTE to your AAD role that maps to the Function App’s Managed Identity
GRANT EXECUTE ON FUNCTION admin.drop_chunks_older_than(regclass, interval) TO "<your-function-app-name>";
GRANT EXECUTE ON FUNCTION admin.drop_chunks_between(regclass, timestamptz, timestamptz) TO "<your-function-app-name>";
```

Notes:

* The **function owner must be the hypertable owner** (here `ts_owner`). If you created the function as another role, run `ALTER FUNCTION ... OWNER TO ts_owner;`.
* Don’t rely on `azure_pg_admin`—it isn’t superuser and does not bypass ownership checks.

---

### 3) Map your Managed Identity to a database role (AAD)

For a system-assigned MI, create a DB role that matches its AAD principal (display name or object id). You already did:

```sql
SET aad_validate_oids_in_tenant = off;
CREATE ROLE "<your-function-app-name>" WITH LOGIN IN ROLE azure_ad_user;

-- Minimal grants for connecting + executing wrapper
GRANT CONNECT ON DATABASE weavix TO "<your-function-app-name>";
GRANT USAGE ON SCHEMA admin TO "<your-function-app-name>";
GRANT EXECUTE ON FUNCTION admin.drop_chunks_older_than(regclass, interval) TO "<your-function-app-name>";
```

(Your earlier `USAGE`/`SELECT` on `events` are not required for the drop unless you also read/write data; the wrapper performs the privileged action.)

If you use a **user-assigned** MI, you’ll typically want the DB role named by its object id GUID, and you must request a token specifically for that client id in your app. The database `ROLE` name must exactly match the AAD principal you authenticate as.

---

### 4) Azure Function (Python) connection and call

Acquire an AAD token for the PostgreSQL resource and pass it as the password. Use the MI-mapped DB user name for `user=`.

```python
import psycopg2
from azure.identity import DefaultAzureCredential

PG_HOST = "weavix-dev-pg.postgres.database.azure.com"
PG_DB   = "weavix"
PG_USER = "<your-function-app-name>"  # must match the DB ROLE you created
RESOURCE = "https://ossrdbms-aad.database.windows.net/.default"

cred = DefaultAzureCredential()
token = cred.get_token(RESOURCE).token  # pass this as password

conn = psycopg2.connect(
    host=PG_HOST,
    dbname=PG_DB,
    user=PG_USER,
    password=token,
    sslmode="require",
)

with conn, conn.cursor() as cur:
    # Drop chunks older than 30 days on a given hypertable
    cur.execute("SELECT admin.drop_chunks_older_than(%s, %s);",
                ("events.pttpressed", "30 days"))
```

Tips:

* For **user-assigned MI**, ensure your Function App has `AZURE_CLIENT_ID` set, so `DefaultAzureCredential` picks the correct identity.
* You don’t need to pass any special libpq `options` when using psycopg2 for AAD tokens.

---

### 5) If you really want the MI to own the hypertable

You could transfer ownership to the MI role:

```sql
ALTER TABLE events.pttpressed OWNER TO "<your-function-app-name>";
```

But that can complicate admin/maintenance; most teams prefer keeping ownership with a dedicated owner role and exposing a **SECURITY DEFINER** wrapper.

---

### Why your current grants aren’t enough

`drop_chunks()` performs DDL-like destructive operations under TimescaleDB’s authority. Postgres requires **table ownership** (or superuser, which you don’t have in Azure) for such operations. Plain GRANTs don’t satisfy that requirement. The **SECURITY DEFINER** wrapper executes with the owner’s privileges, solving the problem safely.

---

 
## pg_cron and chunk drop
Here’s a secure, least-privilege pattern to schedule TimescaleDB chunk drops with `pg_cron` when the **cron job user is not the hypertable owner**.

---

## Roles and ownership

1. Pick/confirm a dedicated owner for the hypertables, e.g. `ts_owner` (this role owns the hypertables).

```sql
-- Optional: create an explicit owner role (no login)
CREATE ROLE ts_owner NOLOGIN;

-- Make sure each hypertable is owned by ts_owner
ALTER TABLE events.pttpressed OWNER TO ts_owner;
-- repeat for other hypertables you will manage
```

2. Create a minimal “job runner” role (the identity that will schedule/own the cron jobs). It does **not** need table ownership.

```sql
-- The role that will schedule/own pg_cron jobs
CREATE ROLE cron_runner LOGIN;

GRANT CONNECT ON DATABASE weavix TO cron_runner;
```

---

## SECURITY DEFINER wrapper (owned by the hypertable owner)

Put privileged logic in a `SECURITY DEFINER` function owned by `ts_owner`. Lock down search_path and add timeouts inside the function body to avoid long blocks.

```sql
-- Schema to hold admin functions; owned by ts_owner
CREATE SCHEMA IF NOT EXISTS admin AUTHORIZATION ts_owner;

-- Optional: simple log table for observability
CREATE TABLE IF NOT EXISTS admin.chunk_maintenance_log (
  id              bigserial PRIMARY KEY,
  ts              timestamptz NOT NULL DEFAULT now(),
  table_regclass  regclass    NOT NULL,
  older_than      interval    NOT NULL,
  rows_dropped    bigint      NULL,       -- if you later capture stats
  note            text        NULL
);
ALTER TABLE admin.chunk_maintenance_log OWNER TO ts_owner;

-- Strict wrapper. Runs with ts_owner privileges.
CREATE OR REPLACE FUNCTION admin.drop_chunks_older_than(_tbl regclass, _older_than interval)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, admin
AS $$
DECLARE
  _schema text := split_part(_tbl::text, '.', 1);
  _owner  name;
BEGIN
  -- Defensive checks: only allow specific schema(s)
  IF _schema NOT IN ('events', 'metrics', 'silver', 'gold') THEN
    RAISE EXCEPTION 'Forbidden schema for drop_chunks(): %', _schema;
  END IF;

  -- Make sure ts_owner actually owns the hypertable (or adjust as needed)
  SELECT rolname INTO _owner
  FROM pg_class c JOIN pg_roles r ON r.oid = c.relowner
  WHERE c.oid = _tbl;
  IF _owner <> 'ts_owner' THEN
    RAISE EXCEPTION 'Hypertable % is not owned by ts_owner (owner=%)', _tbl, _owner;
  END IF;

  -- Keep operations snappy; avoid blocking prod workloads
  PERFORM set_config('lock_timeout', '5s', true);
  PERFORM set_config('statement_timeout', '2min', true);

  -- Actual drop
  PERFORM drop_chunks(_tbl, older_than => _older_than);

  -- Lightweight audit trail
  INSERT INTO admin.chunk_maintenance_log(table_regclass, older_than, note)
  VALUES (_tbl, _older_than, 'pg_cron run');
END;
$$;

-- Lock down permissions and grant only EXECUTE to the job runner
REVOKE ALL ON FUNCTION admin.drop_chunks_older_than(regclass, interval) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin.drop_chunks_older_than(regclass, interval) TO cron_runner;

-- Ensure function owner is ts_owner (very important for SECURITY DEFINER)
ALTER FUNCTION admin.drop_chunks_older_than(regclass, interval) OWNER TO ts_owner;
```

Notes:

* The function executes with `ts_owner`’s privileges regardless of who calls it.
* We defensively whitelist schemas and verify the actual owner to prevent misuse.
* We set `lock_timeout`/`statement_timeout` inside the function so callers don’t have to.

---

## `pg_cron` setup and scheduling

Make sure `pg_cron` extension is installed in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

Log in as `cron_runner` (or `SET ROLE cron_runner`) and schedule jobs that call the wrapper. Jobs run with the privileges of the user who schedules them.

Option A (run in the current database):

```sql
SET ROLE cron_runner;

-- Daily at 03:05 server time: keep 30 days for events.pttpressed
SELECT cron.schedule(
  'drop_chunks_events_pttpressed_keep30d',
  '5 3 * * *',
  $$SELECT admin.drop_chunks_older_than('events.pttpressed'::regclass, '30 days'::interval);$$
);
```

Option B (be explicit about database):

```sql
SET ROLE cron_runner;

SELECT cron.schedule_in_database(
  'drop_chunks_events_pttpressed_keep30d',
  '5 3 * * *',
  'weavix',
  $$SELECT admin.drop_chunks_older_than('events.pttpressed'::regclass, '30 days'::interval);$$
);
```

Good hygiene:

* Give each job a unique, descriptive name.
* Create one job per hypertable/retention, or build a multi-table wrapper that loops across a curated list.

To list or change jobs:

```sql
-- See jobs
SELECT * FROM cron.job;

-- Update schedule
SELECT cron.alter_job('drop_chunks_events_pttpressed_keep30d', '10 3 * * *');

-- Remove job
SELECT cron.unschedule('drop_chunks_events_pttpressed_keep30d');
```

---

## Why this is secure

* The cron user (`cron_runner`) has no destructive table privileges.
* The destructive operation happens only inside a `SECURITY DEFINER` function owned by the hypertable owner (`ts_owner`).
* The function validates schema and ownership before acting.
* Tight `search_path` prevents function hijacking.
* Timeouts reduce lock contention risk.
* Optional audit table records each execution.

---

## Using Managed Identity (AAD) for the cron user (optional)

If you want an Azure Function (Managed Identity) to create/maintain the cron jobs:

1. Map the MI to a DB role (e.g., `CREATE ROLE "<mi-name-or-oid>" WITH LOGIN IN ROLE azure_ad_user;`).
2. Grant that role what `cron_runner` has (CONNECT + EXECUTE on the wrapper, and rights to call `cron.schedule*` which live in `pg_cron` schema).
3. From your Function, connect with the MI token and run the `cron.schedule*` statements once at deployment time.

If you prefer, keep a human `cron_runner` for job management and let the Function only call the wrapper ad-hoc.

---

## Optional: one wrapper to manage multiple tables

If you have many hypertables, you can curate a list in a table and loop:

```sql
CREATE TABLE IF NOT EXISTS admin.retention_policy (
  table_regclass regclass PRIMARY KEY,
  keep_interval  interval NOT NULL
);
ALTER TABLE admin.retention_policy OWNER TO ts_owner;

-- Example entries:
INSERT INTO admin.retention_policy VALUES
('events.pttpressed', '30 days'),
('events.pttjitter',  '14 days')
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION admin.enforce_retention_all()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, admin
AS $$
DECLARE r record;
BEGIN
  PERFORM set_config('lock_timeout', '5s', true);
  PERFORM set_config('statement_timeout', '5min', true);
  FOR r IN SELECT * FROM admin.retention_policy LOOP
    PERFORM admin.drop_chunks_older_than(r.table_regclass, r.keep_interval);
  END LOOP;
END;
$$;
ALTER FUNCTION admin.enforce_retention_all() OWNER TO ts_owner;
REVOKE ALL ON FUNCTION admin.enforce_retention_all() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin.enforce_retention_all() TO cron_runner;

-- Then a single cron job:
SET ROLE cron_runner;
SELECT cron.schedule(
  'enforce_timescale_retention_all',
  '0 3 * * *',
  $$SELECT admin.enforce_retention_all();$$
);
```

This keeps all retention policy in data, not code, and still preserves the same security guarantees.
