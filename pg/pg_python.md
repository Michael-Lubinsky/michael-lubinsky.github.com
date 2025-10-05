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
