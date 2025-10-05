Here are advanced best practices for using `psycopg2`:

Here are comprehensive examples of `psycopg2.extras` module usage:

## 1. DictCursor & RealDictCursor

Access rows as dictionaries instead of tuples:

```python
from psycopg2.extras import DictCursor, RealDictCursor

# DictCursor - supports both dict and tuple access
cursor = conn.cursor(cursor_factory=DictCursor)
cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (1,))
row = cursor.fetchone()

print(row['name'])    # Dict-style access
print(row[1])         # Tuple-style access still works
print(dict(row))      # Convert to dict

# RealDictCursor - true dict, no tuple access
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute("SELECT id, name, email FROM users")
rows = cursor.fetchall()

for row in rows:
    print(row['name'])  # Only dict access
    # row[0] would fail - not a tuple
```

## 2. NamedTupleCursor

Access columns as named tuple attributes:

```python
from psycopg2.extras import NamedTupleCursor

cursor = conn.cursor(cursor_factory=NamedTupleCursor)
cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (1,))
user = cursor.fetchone()

print(user.id)      # Attribute access
print(user.name)    # Clear and readable
print(user.email)   # Type-safe

# Still a tuple
print(user[0])      # Also works
```

## 3. execute_batch - Batch Execution

Much faster than loop for multiple inserts/updates:

```python
from psycopg2.extras import execute_batch

# Data to insert
data = [
    (1, 'Alice', 'alice@example.com'),
    (2, 'Bob', 'bob@example.com'),
    (3, 'Charlie', 'charlie@example.com'),
    # ... 10,000 more rows
]

# Slow way
for row in data:
    cursor.execute("INSERT INTO users (id, name, email) VALUES (%s, %s, %s)", row)

# Fast way - batched
execute_batch(
    cursor,
    "INSERT INTO users (id, name, email) VALUES (%s, %s, %s)",
    data,
    page_size=100  # Execute 100 at a time
)

# Works with any SQL
updates = [(25, 1), (30, 2), (35, 3)]
execute_batch(
    cursor,
    "UPDATE users SET age = %s WHERE id = %s",
    updates,
    page_size=50
)
```

## 4. execute_values - Fastest Bulk Insert

Uses PostgreSQL's multi-row VALUES syntax:

```python
from psycopg2.extras import execute_values

data = [
    ('Alice', 'alice@example.com', 25),
    ('Bob', 'bob@example.com', 30),
    ('Charlie', 'charlie@example.com', 35),
]

# Fastest bulk insert
execute_values(
    cursor,
    "INSERT INTO users (name, email, age) VALUES %s",
    data
)

# With RETURNING clause
execute_values(
    cursor,
    "INSERT INTO users (name, email) VALUES %s RETURNING id",
    [('Alice', 'alice@example.com'), ('Bob', 'bob@example.com')],
    fetch=True  # Fetch returned values
)
inserted_ids = cursor.fetchall()

# Custom template for complex inserts
execute_values(
    cursor,
    "INSERT INTO users (name, email, created_at) VALUES %s",
    [('Alice', 'alice@example.com'), ('Bob', 'bob@example.com')],
    template="(%s, %s, NOW())",  # Add NOW() for each row
    page_size=1000
)
```

## 5. LoggingConnection & LoggingCursor

Debug SQL queries:

```python
from psycopg2.extras import LoggingConnection, LoggingCursor
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('psycopg2')

# Create logging connection
conn = psycopg2.connect(
    ...,
    connection_factory=LoggingConnection
)
conn.initialize(logger)

# All queries are logged
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = %s", (1,))
# Logs: SELECT * FROM users WHERE id = 1
```

## 6. Json & Jsonb Adapters

Handle JSON data types:

```python
from psycopg2.extras import Json, register_default_json

# Insert Python dict as JSON
data = {'name': 'Alice', 'tags': ['user', 'admin'], 'score': 95}

cursor.execute(
    "INSERT INTO records (data) VALUES (%s)",
    (Json(data),)  # Converts dict to JSON
)

# Register default JSON handling
register_default_json(conn)

# Now dicts are automatically converted
cursor.execute(
    "INSERT INTO records (data) VALUES (%s)",
    ({'key': 'value'},)  # No Json() wrapper needed
)

# Query JSON data
cursor.execute("SELECT data FROM records WHERE id = %s", (1,))
row = cursor.fetchone()
print(row[0])  # Automatically decoded to Python dict
```

## 7. register_hstore - PostgreSQL hstore Type

Work with hstore key-value pairs:

```python
from psycopg2.extras import register_hstore

# Enable hstore support
register_hstore(conn)

# Insert Python dict as hstore
tags = {'color': 'red', 'size': 'large', 'material': 'cotton'}
cursor.execute(
    "INSERT INTO products (tags) VALUES (%s)",
    (tags,)
)

# Query returns Python dict
cursor.execute("SELECT tags FROM products WHERE id = %s", (1,))
product_tags = cursor.fetchone()[0]
print(product_tags['color'])  # 'red'
```

## 8. register_uuid - Handle UUIDs

```python
from psycopg2.extras import register_uuid
import uuid

register_uuid()

# Use Python UUID objects
user_id = uuid.uuid4()
cursor.execute(
    "INSERT INTO users (id, name) VALUES (%s, %s)",
    (user_id, 'Alice')
)

# Query returns UUID objects
cursor.execute("SELECT id FROM users WHERE name = %s", ('Alice',))
retrieved_id = cursor.fetchone()[0]
print(type(retrieved_id))  # <class 'uuid.UUID'>
```

## 9. register_composite - Custom Composite Types

```python
from psycopg2.extras import register_composite

# Create composite type in PostgreSQL
cursor.execute("""
    CREATE TYPE address AS (
        street TEXT,
        city TEXT,
        zip TEXT
    )
""")

# Register it
register_composite('address', cursor)

# Use named tuples
from collections import namedtuple
Address = namedtuple('Address', ['street', 'city', 'zip'])

addr = Address('123 Main St', 'New York', '10001')
cursor.execute(
    "INSERT INTO users (name, address) VALUES (%s, %s)",
    ('Alice', addr)
)
```

## 10. wait_select - Async Query Handling

```python
from psycopg2.extras import wait_select
from psycopg2 import extensions

conn.set_session(autocommit=True)
cursor = conn.cursor()

# Start long-running query asynchronously
cursor.execute("SELECT pg_sleep(5)")

# Poll until complete
while True:
    state = conn.poll()
    
    if state == extensions.POLL_OK:
        print("Query complete")
        break
    elif state == extensions.POLL_READ:
        wait_select(conn)  # Wait for read ready
    elif state == extensions.POLL_WRITE:
        wait_select(conn)  # Wait for write ready
    
    # Do other work here
    print("Doing other work...")
```

## 11. MinTimeLoggingConnection - Log Slow Queries

```python
from psycopg2.extras import MinTimeLoggingConnection
import logging

logger = logging.getLogger('slow_queries')
logger.setLevel(logging.INFO)

# Log queries taking > 100ms
conn = psycopg2.connect(
    ...,
    connection_factory=MinTimeLoggingConnection
)
conn.initialize(logger, mintime=0.1)  # 100ms threshold

cursor = conn.cursor()
cursor.execute("SELECT pg_sleep(0.2)")  # This will be logged
cursor.execute("SELECT 1")  # This won't (too fast)
```

## 12. ReplicationCursor - Logical Replication

```python
from psycopg2.extras import ReplicationCursor, LogicalReplicationConnection

# Connect as replication connection
conn = psycopg2.connect(
    ...,
    connection_factory=LogicalReplicationConnection
)

cursor = conn.cursor(cursor_factory=ReplicationCursor)

# Create replication slot
cursor.create_replication_slot('my_slot', output_plugin='test_decoding')

# Start consuming changes
cursor.start_replication(slot_name='my_slot')

# Process changes
for msg in cursor:
    print(f"Change: {msg.payload}")
    cursor.send_feedback(flush_lsn=msg.data_start)
```

## 13. execute_mogrify - See Generated SQL

```python
from psycopg2.extras import execute_values

# See what SQL execute_values generates
cursor = conn.cursor()
sql = "INSERT INTO users (name, email) VALUES %s"
data = [('Alice', 'a@test.com'), ('Bob', 'b@test.com')]

# Generate SQL without executing
template = execute_values(
    cursor,
    sql,
    data,
    fetch=False
)
# Returns the actual VALUES clause that would be executed
```

## 14. Inet Adapter - Network Addresses

```python
from psycopg2.extras import register_inet
import ipaddress

register_inet()

# Use Python ipaddress objects
ip = ipaddress.ip_address('192.168.1.1')
network = ipaddress.ip_network('10.0.0.0/24')

cursor.execute(
    "INSERT INTO servers (ip, network) VALUES (%s, %s)",
    (ip, network)
)

# Query returns ipaddress objects
cursor.execute("SELECT ip FROM servers")
server_ip = cursor.fetchone()[0]
print(type(server_ip))  # <class 'ipaddress.IPv4Address'>
```

## Practical Combined Example:

```python
from psycopg2.extras import (
    RealDictCursor, execute_values, Json, 
    LoggingConnection, register_default_json
)

# Logging connection with dict cursor
conn = psycopg2.connect(..., connection_factory=LoggingConnection)
conn.initialize(logger)
register_default_json(conn)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# Bulk insert with JSON
users = [
    ('Alice', {'role': 'admin', 'permissions': ['read', 'write']}),
    ('Bob', {'role': 'user', 'permissions': ['read']}),
]

execute_values(
    cursor,
    "INSERT INTO users (name, metadata) VALUES %s RETURNING id, name, metadata",
    users,
    fetch=True
)

# Get results as dicts
for user in cursor.fetchall():
    print(f"User {user['name']} has permissions: {user['metadata']['permissions']}")
```

These `psycopg2.extras` utilities significantly improve productivity, performance, and code clarity when working with PostgreSQL.

## 1. Connection Pooling

Use connection pools instead of creating connections repeatedly:

```python
from psycopg2 import pool

# Create pool once (module level)
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host='...',
    database='...',
    user='...',
    password='...'
)

# Get/return connections
def get_conn():
    return connection_pool.getconn()

def return_conn(conn):
    connection_pool.putconn(conn)

# Always return connections
try:
    conn = get_conn()
    # use connection
finally:
    return_conn(conn)
```

## 2. Server-Side Cursors for Large Result Sets

Avoid loading millions of rows into memory:

```python
# Client-side cursor (default) - loads ALL rows into memory
cursor = conn.cursor()
cursor.execute("SELECT * FROM huge_table")  # Loads everything!
rows = cursor.fetchall()  # Memory exhausted

# Server-side cursor - fetches in batches
cursor = conn.cursor(name='my_cursor')  # Named cursor = server-side
cursor.execute("SELECT * FROM huge_table")

# Iterate without loading everything
for row in cursor:
    process(row)  # Fetches in batches

# Or fetch in chunks
while True:
    rows = cursor.fetchmany(1000)
    if not rows:
        break
    process_batch(rows)
```

## 3. Execute Batch for Bulk Inserts

Much faster than individual inserts:

```python
from psycopg2.extras import execute_batch, execute_values

# Slow - one transaction per row
for row in data:
    cursor.execute("INSERT INTO table VALUES (%s, %s)", row)

# Fast - batched execution
execute_batch(
    cursor,
    "INSERT INTO table VALUES (%s, %s)",
    data,
    page_size=1000
)

# Fastest - VALUES clause (PostgreSQL 8.2+)
execute_values(
    cursor,
    "INSERT INTO table (col1, col2) VALUES %s",
    data,
    page_size=1000
)
```

## 4. Connection Context Managers

Automatic commit/rollback:

```python
# Manual management (error-prone)
conn = psycopg2.connect(...)
try:
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
except:
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()

# Better - context managers
with psycopg2.connect(...) as conn:
    with conn.cursor() as cursor:
        cursor.execute(...)
        # Auto-commit on success, auto-rollback on exception
```

## 5. Use execute_mogrify for Debugging

See the actual SQL being executed:

```python
query = cursor.mogrify("SELECT * FROM users WHERE id = %s", (user_id,))
print(query.decode('utf-8'))  # See exact SQL with values

# Useful for debugging
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## 6. Prepared Statements

For repeated queries with different parameters:

```python
# Prepare once
cursor.execute("PREPARE user_query AS SELECT * FROM users WHERE id = $1")

# Execute many times (faster)
for user_id in user_ids:
    cursor.execute("EXECUTE user_query (%s)", (user_id,))
    
# Cleanup
cursor.execute("DEALLOCATE user_query")
```

## 7. Use DictCursor for Named Access

Access columns by name instead of index:

```python
from psycopg2.extras import RealDictCursor

# Regular cursor - access by index
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM users")
row = cursor.fetchone()
print(row[0], row[1])  # Fragile

# DictCursor - access by name
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute("SELECT id, name FROM users")
row = cursor.fetchone()
print(row['id'], row['name'])  # Clear
```

## 8. Proper Error Handling

Distinguish different error types:

```python
import psycopg2
from psycopg2 import errorcodes

try:
    cursor.execute(...)
except psycopg2.IntegrityError as e:
    if e.pgcode == errorcodes.UNIQUE_VIOLATION:
        # Handle duplicate key
        pass
    elif e.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
        # Handle FK violation
        pass
except psycopg2.OperationalError as e:
    # Connection issues, retry logic
    pass
except psycopg2.DatabaseError as e:
    # Other DB errors
    pass
```

## 9. COPY for Bulk Operations

Fastest way to import/export data:

```python
# Export to CSV
with open('output.csv', 'w') as f:
    cursor.copy_expert(
        "COPY table TO STDOUT WITH CSV HEADER",
        f
    )

# Import from CSV
with open('input.csv', 'r') as f:
    cursor.copy_expert(
        "COPY table FROM STDIN WITH CSV HEADER",
        f
    )

# Copy with StringIO (in-memory)
import io
buffer = io.StringIO()
buffer.write("col1,col2\n1,2\n3,4\n")
buffer.seek(0)
cursor.copy_expert("COPY table FROM STDIN WITH CSV HEADER", buffer)
```

## 10. Savepoints for Nested Transactions

Partial rollbacks:

```python
cursor.execute("BEGIN")
try:
    cursor.execute("INSERT INTO users ...")
    
    cursor.execute("SAVEPOINT sp1")
    try:
        cursor.execute("INSERT INTO orders ...")
    except:
        cursor.execute("ROLLBACK TO SAVEPOINT sp1")
        # First insert still valid
    
    cursor.execute("COMMIT")
except:
    cursor.execute("ROLLBACK")
```

## 11. Connection String with SSL/Security

```python
conn = psycopg2.connect(
    host='...',
    sslmode='require',  # Force SSL
    sslrootcert='/path/to/ca.crt',
    sslcert='/path/to/client.crt',
    sslkey='/path/to/client.key',
    connect_timeout=10,
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5
)
```

## 12. Use Asynchronous Operations (psycopg2.extras)

For concurrent operations:

```python
from psycopg2.extras import wait_select

# Start async query
conn.set_session(autocommit=True)
cursor = conn.cursor()
cursor.execute("SELECT pg_sleep(10)")  # Long query

# Do other work while waiting
while True:
    state = conn.poll()
    if state == psycopg2.extensions.POLL_OK:
        break
    elif state == psycopg2.extensions.POLL_READ:
        wait_select(conn)
    elif state == psycopg2.extensions.POLL_WRITE:
        wait_select(conn)
```

## 13. Register Custom Type Adapters

```python
from psycopg2.extensions import register_adapter, AsIs
import json

# Adapt Python dict to PostgreSQL JSON
def adapt_dict(d):
    return AsIs(f"'{json.dumps(d)}'::json")

register_adapter(dict, adapt_dict)

# Now you can insert dicts directly
cursor.execute(
    "INSERT INTO table (data) VALUES (%s)",
    ({'key': 'value'},)
)
```

## 14. LISTEN/NOTIFY for Pub/Sub

```python
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

# Subscribe
cursor.execute("LISTEN my_channel")

# Wait for notifications
while True:
    conn.poll()
    while conn.notifies:
        notify = conn.notifies.pop(0)
        print(f"Received: {notify.payload}")
```

## 15. Query Timeouts

```python
# Set statement timeout
cursor.execute("SET statement_timeout = 5000")  # 5 seconds
cursor.execute("SELECT pg_sleep(10)")  # Will timeout

# Or at connection level
conn = psycopg2.connect(..., options="-c statement_timeout=5000")
```

These practices significantly improve performance, security, and reliability when working with PostgreSQL through psycopg2.

The `psycopg2.sql` module is used for **safe SQL composition** to prevent SQL injection. Here are the main use cases:

## 1. `sql.Identifier` - Table/Column Names

Use when inserting **user-controlled** or **variable** table/column names:

```python
# ❌ DANGEROUS - SQL injection risk
schema = "public"
table = "users"
query = f"SELECT * FROM {schema}.{table}"  # User could inject: "public.users; DROP TABLE users--"

# ✅ SAFE
query = sql.SQL("SELECT * FROM {}.{}").format(
    sql.Identifier(schema),
    sql.Identifier(table)
)
# Produces: SELECT * FROM "public"."users"
```

**When to use:**
- Dynamic table names
- Dynamic schema names
- Dynamic column names
- Building DDL statements (CREATE, DROP, ALTER)

## 2. `sql.Literal` - Values in SQL Statements

Use for **values** when you can't use parameter placeholders (`%s`):

```python
# ❌ DANGEROUS
date = "2024-01-01"
query = f"SELECT * FROM table WHERE date = '{date}'"  # Injection risk

# ✅ SAFE with Literal
query = sql.SQL("SELECT * FROM table WHERE date = {date}").format(
    date=sql.Literal(date)
)
# Produces: SELECT * FROM table WHERE date = '2024-01-01'

# ✅ EVEN BETTER - use parameters when possible
cursor.execute("SELECT * FROM table WHERE date = %s", (date,))
```

**When to use:**
- Inside COPY subqueries (can't use `%s`)
- Dynamic SQL generation where parameters don't work
- Building complex queries programmatically

## 3. `sql.SQL` - SQL Fragments

Compose SQL strings safely:

```python
# Build complex queries
parts = [
    sql.SQL("SELECT * FROM"),
    sql.Identifier("schema", "table"),
    sql.SQL("WHERE"),
    sql.Identifier("column"),
    sql.SQL("="),
    sql.Literal("value")
]
query = sql.SQL(" ").join(parts)
```

## 4. `sql.Composed` - Combine Multiple Parts

```python
# Combine different SQL components
table_ref = sql.SQL("{}.{}").format(
    sql.Identifier("public"),
    sql.Identifier("users")
)

where_clause = sql.SQL("WHERE {} = {}").format(
    sql.Identifier("id"),
    sql.Literal(123)
)

query = sql.Composed([
    sql.SQL("SELECT * FROM"),
    table_ref,
    where_clause
])
```

## Real-World Examples from Your Code:

### Example 1: Dynamic Column Selection
```python
def min_column(conn, schema, table_name, col):
    # col is variable - must use Identifier
    query = sql.SQL("SELECT min({column}) FROM {schema}.{table}").format(
        column=sql.Identifier(col),
        schema=sql.Identifier(schema),
        table=sql.Identifier(table_name)
    )
    cursor.execute(query)
```

### Example 2: COPY with Subquery (Your Case)
```python
# Can't use %s parameters in COPY subquery, so use Literal
select_query = sql.SQL("""
    SELECT * FROM {schema}.{table}
    WHERE {column} >= {date}::date
""").format(
    schema=sql.Identifier(schema),
    table=sql.Identifier(table_name),
    column=sql.Identifier(partition_column),
    date=sql.Literal(backup_date)  # Must use Literal - can't use %s here
)

copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH CSV").format(
    query=select_query
)
```

### Example 3: CREATE TABLE
```python
create_sql = sql.SQL("CREATE TABLE {}.{} (LIKE {}.{} INCLUDING ALL)").format(
    sql.Identifier(dest_schema),
    sql.Identifier(dest_table),
    sql.Identifier(src_schema),
    sql.Identifier(src_table)
)
```

### Example 4: DROP TABLE
```python
drop_sql = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
    sql.Identifier(schema),
    sql.Identifier(table)
)
```

## When NOT to Use sql.SQL:

```python
# ✅ Use parameters (%s) for simple value substitution
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ❌ Don't use sql.Literal for this
cursor.execute(
    sql.SQL("SELECT * FROM users WHERE id = {}").format(
        sql.Literal(user_id)
    )
)
```

## Summary:

| Use Case | Tool | Example |
|----------|------|---------|
| Table/column names | `sql.Identifier` | `sql.Identifier("users")` → `"users"` |
| Values (when %s won't work) | `sql.Literal` | `sql.Literal('2024-01-01')` → `'2024-01-01'` |
| SQL keywords/fragments | `sql.SQL` | `sql.SQL("SELECT * FROM")` |
| Combining parts | `sql.Composed` | Join multiple SQL pieces |
| Simple values | `%s` parameters | `cursor.execute("... WHERE x = %s", (val,))` |

**Rule of thumb:** Use `sql.SQL` components when building dynamic SQL structure; use `%s` parameters for simple value substitution.


`copy_expert()` is a psycopg2 method that executes PostgreSQL's `COPY` command with a file-like object.

## What it does:

```python
cursor.copy_expert(sql, file_object)
```

Executes a COPY SQL command and reads/writes data from/to the `file_object`.

## Two main uses:

### 1. Export (COPY TO):
```python
# Export table to file
with open('output.csv', 'w') as f:
    cursor.copy_expert("COPY my_table TO STDOUT WITH CSV HEADER", f)
```

### 2. Import (COPY FROM):
```python
# Import file to table  
with open('input.csv', 'r') as f:
    cursor.copy_expert("COPY my_table FROM STDIN WITH CSV HEADER", f)
```

## In your code:

```python
cursor.copy_expert(copy_sql, gz_file)
```

This executes a COPY command that:
1. Runs the SELECT query (the subquery in your COPY statement)
2. Formats results as CSV with headers
3. Writes the CSV output directly to `gz_file` (which compresses it)

## Why use it instead of regular queries?

**Much faster** than fetching rows in Python:

```python
# Slow - Python processes each row
cursor.execute("SELECT * FROM table")
for row in cursor.fetchall():
    write_to_file(row)

# Fast - PostgreSQL writes directly to file
cursor.copy_expert("COPY table TO STDOUT WITH CSV", file)
```

PostgreSQL handles all the CSV formatting and writing internally, avoiding the Python overhead.

## Key difference from copy_to/copy_from:

- `copy_to()` / `copy_from()` - simpler but less flexible
- `copy_expert()` - accepts any COPY SQL including subqueries

Your code uses `copy_expert()` because you need a subquery with WHERE clause:

```python
COPY (SELECT * FROM table WHERE date = '2024-01-01') TO STDOUT
```

Regular `copy_to()` can't handle subqueries.

The bottleneck is likely the temporary file I/O and the sequential nature of: write to temp file → compress → upload. Here are faster approaches:

## Option 1: Stream Directly to ADLS (Fastest)

Eliminate the temporary file entirely by streaming compressed data directly to ADLS:

```python
import io

class CompressedUploadStream:
    """Stream that compresses on-the-fly and uploads to ADLS"""
    def __init__(self, adls_path, service_client, container_name):
        self.buffer = io.BytesIO()
        self.gz_file = gzip.GzipFile(fileobj=self.buffer, mode='wb')
        self.adls_path = adls_path
        self.service_client = service_client
        self.container_name = container_name
        
    def write(self, data):
        self.gz_file.write(data)
        
    def close(self):
        self.gz_file.close()
        self.buffer.seek(0)
        
        fs_client = self.service_client.get_file_system_client(self.container_name)
        file_client = fs_client.get_file_client(self.adls_path)
        file_client.upload_data(self.buffer, overwrite=True)
        self.buffer.close()

# Usage
with conn.cursor() as cursor:
    stream = CompressedUploadStream(adls_path, service_client, container_name)
    copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
        query=select_query
    )
    cursor.copy_expert(copy_sql, stream)
    stream.close()
```

## Option 2: Use Pipe Between PostgreSQL and Compression

Use `copy_to()` with a custom file-like object:

```python
class GzipUploadPipe:
    def __init__(self, adls_path):
        self.buffer = io.BytesIO()
        self.compressor = gzip.GzipFile(fileobj=self.buffer, mode='wb')
        self.adls_path = adls_path
        self.total_written = 0
        
    def write(self, data):
        self.compressor.write(data)
        self.total_written += len(data)
        return len(data)
    
    def flush(self):
        self.compressor.flush()
        
    def close(self):
        self.compressor.close()
        self.buffer.seek(0)
        upload_stream_to_adls_file(self.adls_path, self.buffer, content_type="application/gzip")
        self.buffer.close()

# Usage
with conn.cursor() as cursor:
    with GzipUploadPipe(adls_path) as pipe:
        copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
            query=select_query
        )
        cursor.copy_expert(copy_sql, pipe)
```

## Option 3: Parallel Compression (Complex but Fastest for Large Files)

Use `pigz` (parallel gzip) if available, or Python's `concurrent.futures`:

```python
import subprocess

# Export uncompressed, compress with pigz, upload
with conn.cursor() as cursor:
    # Write to pipe
    proc = subprocess.Popen(
        ['pigz', '-c'],  # Parallel gzip
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    
    copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
        query=select_query
    )
    
    # PostgreSQL writes to pigz stdin
    cursor.copy_expert(copy_sql, proc.stdin)
    proc.stdin.close()
    
    # Read compressed output
    compressed_data = proc.stdout.read()
    proc.wait()
    
    # Upload
    upload_stream_to_adls_file(adls_path, io.BytesIO(compressed_data), content_type="application/gzip")
```

## Option 4: Simplest - Just Remove SpooledTemporaryFile

Use regular `BytesIO` (stays in memory, no disk I/O):

```python
buffer = io.BytesIO()
with gzip.GzipFile(fileobj=buffer, mode='wb') as gz_file:
    with conn.cursor() as cursor:
        copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
            query=select_query
        )
        cursor.copy_expert(copy_sql, gz_file)

buffer.seek(0)
upload_stream_to_adls_file(adls_path, buffer, content_type="application/gzip")
buffer.close()
```

## Performance Comparison:

| Approach | Speed | Memory | Complexity |
|----------|-------|--------|------------|
| Current (SpooledTempFile) | Slow | Low | Simple |
| BytesIO only | **Fast** | Medium | **Simplest** |
| Direct streaming | **Fastest** | Low | Medium |
| Parallel compression (pigz) | **Fastest (large files)** | Medium | Complex |

## Recommendation:

Start with **Option 4** (BytesIO) - simplest change, significant speedup:

```python
def backup_table_safe(conn, table, backup_date, partition_column):
    # ... existing code ...
    
    # Replace SpooledTemporaryFile with BytesIO
    buffer = io.BytesIO()
    try:
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz_file:
            with conn.cursor() as cursor:
                copy_sql = sql.SQL("COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
                    query=select_query
                )
                cursor.copy_expert(copy_sql, gz_file)
        
        buffer.seek(0)
        upload_stream_to_adls_file(adls_path, buffer, content_type="application/gzip")
    finally:
        buffer.close()
```

This eliminates disk I/O completely and should be 2-5x faster for typical backup sizes.
