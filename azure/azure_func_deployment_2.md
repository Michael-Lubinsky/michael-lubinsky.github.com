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
