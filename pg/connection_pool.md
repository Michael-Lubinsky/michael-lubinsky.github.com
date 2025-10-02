## Checking Connection Pooling Configuration

### Method 1: Check Server Parameters

```sql
-- Check if pgBouncer is enabled (Azure's built-in pooler)
SHOW azure.extensions;

-- Check current connection limits
SHOW max_connections;

-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- View connection details
SELECT 
    datname,
    usename,
    application_name,
    client_addr,
    state,
    backend_start
FROM pg_stat_activity
WHERE state = 'active';
```

### Method 2: Azure Portal

1. Go to your **Azure Database for PostgreSQL flexible server**
2. **Server parameters** (left menu)
3. Search for:
   - `max_connections` - Current max connections
   - `connection_throttling` - Connection throttling settings
   - `pgbouncer` - If built-in pooler is available (some tiers)

### Method 3: Azure CLI

```bash
# Get server parameters
az postgres flexible-server parameter show \
    --resource-group <resource-group> \
    --server-name <server-name> \
    --name max_connections

# List all parameters
az postgres flexible-server parameter list \
    --resource-group <resource-group> \
    --server-name <server-name> \
    --query "[?name=='max_connections' || name=='connection_throttling']"
```

## Max Connections in Azure PostgreSQL Flexible Server

Azure automatically sets `max_connections` based on SKU:

| vCores | Default max_connections |
|--------|------------------------|
| 1      | 50                     |
| 2      | 100                    |
| 4      | 200                    |
| 8      | 400                    |
| 16     | 800                    |
| 32     | 1500                   |
| 64     | 2000                   |

**Formula:** Approximately `50 + (vCores * 25)` connections

## Recommended Configuration

### For Your Backup Script:

```python
# Use connection pooling in your Python code
import psycopg2
from psycopg2 import pool

# Create connection pool (do this once at module level)
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,  # Keep this LOW for backup scripts
    host=os.environ.get('PG_HOST'),
    database=os.environ.get('PG_DATABASE'),
    user=os.environ.get('PG_USER'),
    password=os.environ.get('PG_PASSWORD'),
    sslmode='require'
)

def get_postgres_connection():
    """Get connection from pool"""
    return connection_pool.getconn()

def return_connection(conn):
    """Return connection to pool"""
    connection_pool.putconn(conn)

# Usage in your backup function
def backup_table(table, backup_date):
    conn = get_postgres_connection()
    try:
        # Your backup logic
        pass
    finally:
        return_connection(conn)
```

### Recommended Limits:

**For backup/batch operations:**
- **1-5 connections** per script/VM
- Don't create new connections for each query
- Reuse connections or use a small pool

**General guidelines:**
- Reserve **80%** of max_connections for application
- Reserve **20%** for admin/maintenance
- Example: 200 max → use max 160 for apps, keep 40 free

**For your VM running backups:**
```python
# Conservative pool size
maxconn=5  # More than enough for sequential backups
```

## Check Current Usage:

```sql
-- See how many connections you're actually using
SELECT 
    count(*) as total_connections,
    count(*) FILTER (WHERE state = 'active') as active,
    count(*) FILTER (WHERE state = 'idle') as idle,
    max_connections
FROM pg_stat_activity
CROSS JOIN (SELECT setting::int as max_connections FROM pg_settings WHERE name = 'max_connections') mc;

-- See connections by application
SELECT 
    application_name,
    count(*) as connections
FROM pg_stat_activity
GROUP BY application_name
ORDER BY connections DESC;
```

## Optimize Your Code:

```python
def backup_multiple_tables(tables, start_date, end_date):
    """Efficient multi-table backup using single connection"""
    dates = generate_date_range(start_date, end_date)
    
    # Get ONE connection for all backups
    conn = get_postgres_connection()
    try:
        for table in tables:
            for date in dates:
                # Reuse the same connection
                backup_table_with_connection(conn, table, date)
    finally:
        conn.close()
```

Your backup script should use **1-5 connections maximum**. Creating hundreds of connections will exhaust the pool and cause failures.
