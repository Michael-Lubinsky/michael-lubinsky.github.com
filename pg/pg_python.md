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
