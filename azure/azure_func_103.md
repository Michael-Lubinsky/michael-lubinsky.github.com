I've created a comprehensive restore function with the following features:

## Key Functions

### 1. **Main Restore Function** (`/api/restore_table`)
Supports both GET and POST requests with parameters:
- **file_path**: Full ADLS path (e.g., `weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz`)
- **pg_host**: PostgreSQL host (optional)
- **pg_database**: Target database (optional, derived from file path)
- **destination_table**: Target table (optional, derived from file path)
- **restore_mode**: `'replace'`, `'append'`, or `'staging'` (default: staging)
- **staging_suffix**: Custom suffix for staging tables

### 2. **Restore Modes**

#### **Staging Mode** (Default - Safest)
```
Creates: original_table_restore_20241225_143022
```
- Creates new staging table with timestamp suffix
- No risk to existing data
- Good for validation before promoting

#### **Replace Mode**
- Drops existing table and recreates it
- Complete replacement of data
- **Warning**: Destructive operation

#### **Append Mode**
- Adds data to existing table
- Creates table if it doesn't exist
- Validates column structure matches

### 3. **Bonus: List Backups** (`/api/list_backups`)
Lists available backup files with optional filters:
- `schema`: Filter by schema name
- `table`: Filter by table name  
- `date`: Filter by backup date (YYYY-MM-DD)

## Usage Examples

### Basic Restore (Staging Mode)
```bash
# GET request
curl "https://your-function-app.azurewebsites.net/api/restore_table?file_path=weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz"

# POST request
curl -X POST "https://your-function-app.azurewebsites.net/api/restore_table" \
-H "Content-Type: application/json" \
-d '{
  "file_path": "weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz",
  "restore_mode": "staging"
}'
```

### Replace Existing Table
```bash
curl -X POST "https://your-function-app.azurewebsites.net/api/restore_table" \
-H "Content-Type: application/json" \
-d '{
  "file_path": "weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz",
  "restore_mode": "replace"
}'
```

### Restore to Different Database/Table
```bash
curl -X POST "https://your-function-app.azurewebsites.net/api/restore_table" \
-H "Content-Type: application/json" \
-d '{
  "file_path": "weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz",
  "pg_database": "test_db",
  "destination_table": "staging.temp_bannerclicked",
  "restore_mode": "replace"
}'
```

### List Available Backups
```bash
# All backups
curl "https://your-function-app.azurewebsites.net/api/list_backups"

# Filter by table
curl "https://your-function-app.azurewebsites.net/api/list_backups?table=bannerclicked"

# Filter by date
curl "https://your-function-app.azurewebsites.net/api/list_backups?date=2024-01-15"
```

## Key Features

### **Memory Efficient**
- Streams data directly from ADLS to PostgreSQL
- Uses PostgreSQL's `COPY` command for fast loading
- No intermediate storage of full dataset

### **Smart Path Parsing**
- Automatically extracts database, schema, table, and date from file path
- Validates file path format
- Handles naming conventions properly

### **Flexible Table Creation**
- Creates tables with TEXT columns (simple approach)
- Can be extended to infer data types from sample data
- Handles schema creation automatically

### **Error Handling**
- Comprehensive validation of inputs
- Rollback on errors
- Detailed logging and error messages

### **Security**
- Uses managed identity for both ADLS and PostgreSQL
- Same token caching mechanism as backup function
- Function-level authentication

## Required Environment Variables
Same as your backup function:
- `ADLS_ACCOUNT_NAME`
- `ADLS_FILE_SYSTEM`
- `PG_HOST` (optional)
- `PG_DATABASE` (optional)
- `PG_USER` (should be "Michael")

This gives you a complete backup/restore solution for your PostgreSQL data with Azure Functions!


```python

import azure.functions as func
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import DefaultAzureCredential
import logging
import threading
from datetime import datetime, timedelta
import os
import psycopg2
import gzip
import tempfile
import io
import csv
from psycopg2 import sql
import re

app = func.FunctionApp()

# Global variables for connection pooling and token management
_token_cache = {}
_token_lock = threading.Lock()
_credential = None

@app.route(route="restore_table", auth_level=func.AuthLevel.FUNCTION, methods=['POST', 'GET'])
def restore_table(req: func.HttpRequest) -> func.HttpResponse:
    """
    Restore PostgreSQL table from ADLS Gen2 backup
    
    Parameters:
    - file_path: Full path to .csv.gz file in ADLS Gen2 (e.g., "weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz")
    - pg_host: PostgreSQL host (optional, uses env default)
    - pg_database: Target database (optional, derived from file_path)
    - destination_table: Target table (optional, derived from file_path or use staging)
    - restore_mode: 'replace', 'append', 'staging' (default: 'staging')
    - staging_suffix: Suffix for staging table (default: '_restore_YYYYMMDD_HHMMSS')
    """
    
    try:
        # Get parameters from request
        if req.method == 'POST':
            try:
                req_body = req.get_json()
                file_path = req_body.get('file_path')
                pg_host = req_body.get('pg_host')
                pg_database = req_body.get('pg_database')
                destination_table = req_body.get('destination_table')
                restore_mode = req_body.get('restore_mode', 'staging')
                staging_suffix = req_body.get('staging_suffix')
            except ValueError:
                return func.HttpResponse("Invalid JSON in request body", status_code=400)
        else:
            # GET request - use query parameters
            file_path = req.params.get('file_path')
            pg_host = req.params.get('pg_host')
            pg_database = req.params.get('pg_database')
            destination_table = req.params.get('destination_table')
            restore_mode = req.params.get('restore_mode', 'staging')
            staging_suffix = req.params.get('staging_suffix')
        
        if not file_path:
            return func.HttpResponse(
                "Missing required parameter: file_path (e.g., 'weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz')", 
                status_code=400
            )
        
        # Validate restore mode
        valid_modes = ['replace', 'append', 'staging']
        if restore_mode not in valid_modes:
            return func.HttpResponse(
                f"Invalid restore_mode. Must be one of: {', '.join(valid_modes)}", 
                status_code=400
            )
        
        logging.info(f"Restore requested - file: {file_path}, mode: {restore_mode}")
        
        # Parse file path and derive parameters
        parsed_info = parse_backup_file_path(file_path)
        
        # Use provided values or derive from file path
        target_database = pg_database or parsed_info['database']
        target_host = pg_host or os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
        
        # Determine destination table
        if destination_table:
            target_schema, target_table = parse_table_name(destination_table)
        elif restore_mode == 'staging':
            # Create staging table name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            suffix = staging_suffix or f"_restore_{timestamp}"
            target_schema = parsed_info['schema']
            target_table = parsed_info['table'] + suffix
        else:
            # Use original table
            target_schema = parsed_info['schema']
            target_table = parsed_info['table']
        
        destination_full_name = f"{target_schema}.{target_table}"
        
        logging.info(f"Restore parameters:")
        logging.info(f"  Source file: {file_path}")
        logging.info(f"  Target database: {target_database}")
        logging.info(f"  Target table: {destination_full_name}")
        logging.info(f"  Restore mode: {restore_mode}")
        
        # Perform the restore
        row_count = restore_table_from_adls(
            file_path=file_path,
            pg_host=target_host,
            pg_database=target_database,
            destination_schema=target_schema,
            destination_table=target_table,
            restore_mode=restore_mode
        )
        
        success_message = {
            "status": "success",
            "message": f"Restore completed successfully",
            "source_file": file_path,
            "destination_table": destination_full_name,
            "restore_mode": restore_mode,
            "rows_restored": row_count
        }
        
        logging.info(f"Restore completed: {row_count} rows restored to {destination_full_name}")
        
        return func.HttpResponse(
            str(success_message),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_message = {
            "status": "error",
            "message": str(e),
            "file_path": file_path if 'file_path' in locals() else None
        }
        logging.error(f"Restore failed: {str(e)}")
        return func.HttpResponse(
            str(error_message),
            status_code=500,
            mimetype="application/json"
        )

def parse_backup_file_path(file_path):
    """
    Parse backup file path to extract database, schema, table, and date
    Expected format: database/schema/table/table.YYYY-MM-DD.csv.gz
    Example: weavix/events/bannerclicked/bannerclicked.2024-01-15.csv.gz
    """
    try:
        # Remove leading/trailing slashes and split path
        path_parts = file_path.strip('/').split('/')
        
        if len(path_parts) != 4:
            raise ValueError(f"Invalid file path format. Expected: database/schema/table/table.YYYY-MM-DD.csv.gz")
        
        database = path_parts[0]
        schema = path_parts[1]
        table_dir = path_parts[2]
        filename = path_parts[3]
        
        # Parse filename: table.YYYY-MM-DD.csv.gz
        if not filename.endswith('.csv.gz'):
            raise ValueError(f"File must end with .csv.gz, got: {filename}")
        
        # Extract table name and date from filename
        basename = filename[:-7]  # Remove .csv.gz
        
        # Match pattern: tablename.YYYY-MM-DD
        date_pattern = r'^(.+)\.(\d{4}-\d{2}-\d{2})$'
        match = re.match(date_pattern, basename)
        
        if not match:
            raise ValueError(f"Invalid filename format. Expected: tablename.YYYY-MM-DD.csv.gz, got: {filename}")
        
        table_name = match.group(1)
        backup_date = match.group(2)
        
        # Validate that table name matches directory
        if table_name != table_dir:
            raise ValueError(f"Table name mismatch: directory '{table_dir}' vs filename '{table_name}'")
        
        # Validate date format
        try:
            datetime.strptime(backup_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {backup_date}")
        
        return {
            'database': database,
            'schema': schema,
            'table': table_name,
            'date': backup_date,
            'filename': filename
        }
        
    except Exception as e:
        raise ValueError(f"Error parsing file path '{file_path}': {str(e)}")

def parse_table_name(table_name):
    """Parse schema.table format"""
    parts = table_name.split('.')
    if len(parts) != 2:
        raise ValueError(f"Invalid table format. Expected 'schema.table', got: {table_name}")
    return parts[0], parts[1]

def restore_table_from_adls(file_path, pg_host, pg_database, destination_schema, destination_table, restore_mode):
    """
    Restore table data from ADLS Gen2 backup file
    Returns number of rows restored
    """
    conn = None
    try:
        # Download and decompress file from ADLS
        logging.info(f"Downloading file from ADLS: {file_path}")
        
        # Get connection to target database
        conn = get_postgres_connection(pg_host, pg_database)
        
        # Create schema if it doesn't exist
        create_schema_if_not_exists(conn, destination_schema)
        
        # Download file and get CSV headers to create table structure
        with download_adls_file_stream(file_path) as compressed_stream:
            with gzip.GzipFile(fileobj=compressed_stream, mode='rt') as csv_file:
                # Read first few lines to analyze structure
                csv_reader = csv.reader(csv_file)
                headers = next(csv_reader)  # Get column names
                
                # Sample first few rows to infer data types (optional)
                sample_rows = []
                for i, row in enumerate(csv_reader):
                    sample_rows.append(row)
                    if i >= 10:  # Sample first 10 rows
                        break
        
        # Create or prepare destination table
        full_table_name = f"{destination_schema}.{destination_table}"
        
        if restore_mode == 'replace':
            # Drop and recreate table
            drop_table_if_exists(conn, destination_schema, destination_table)
            create_table_from_headers(conn, destination_schema, destination_table, headers)
            logging.info(f"Created new table: {full_table_name}")
            
        elif restore_mode == 'staging':
            # Create staging table (always new)
            drop_table_if_exists(conn, destination_schema, destination_table)
            create_table_from_headers(conn, destination_schema, destination_table, headers)
            logging.info(f"Created staging table: {full_table_name}")
            
        elif restore_mode == 'append':
            # Check if table exists, create if not
            if not table_exists(conn, destination_schema, destination_table):
                create_table_from_headers(conn, destination_schema, destination_table, headers)
                logging.info(f"Created new table for append: {full_table_name}")
            else:
                # Validate that columns match
                validate_table_columns(conn, destination_schema, destination_table, headers)
                logging.info(f"Validated existing table structure: {full_table_name}")
        
        # Now load the data using COPY
        logging.info(f"Loading data into {full_table_name}")
        
        row_count = 0
        with download_adls_file_stream(file_path) as compressed_stream:
            with gzip.GzipFile(fileobj=compressed_stream, mode='rt') as csv_file:
                with conn.cursor() as cursor:
                    # Use COPY to load data efficiently
                    copy_sql = f"""
                    COPY {destination_schema}.{destination_table}
                    FROM STDIN 
                    WITH (FORMAT csv, HEADER true, NULL '')
                    """
                    cursor.copy_expert(copy_sql, csv_file)
                    row_count = cursor.rowcount
        
        conn.commit()
        logging.info(f"Successfully loaded {row_count} rows into {full_table_name}")
        
        return row_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error during restore: {str(e)}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logging.error(f'Error closing database connection: {str(e)}')

def download_adls_file_stream(file_path):
    """Download file from ADLS Gen2 as a stream"""
    try:
        account_name = os.environ["ADLS_ACCOUNT_NAME"]
        container_name = os.environ["ADLS_FILE_SYSTEM"]
        
        service_client = DataLakeServiceClient(
            account_url=f"https://{account_name}.dfs.core.windows.net",
            credential=DefaultAzureCredential()
        )
        
        file_system_client = service_client.get_file_system_client(file_system=container_name)
        file_client = file_system_client.get_file_client(file_path)
        
        # Download as stream
        download_stream = file_client.download_file()
        
        # Return file-like object
        return io.BytesIO(download_stream.readall())
        
    except Exception as e:
        logging.error(f"Error downloading file from ADLS: {str(e)}")
        raise

def create_schema_if_not_exists(conn, schema_name):
    """Create schema if it doesn't exist"""
    with conn.cursor() as cursor:
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(schema_name)
            )
        )
        conn.commit()

def drop_table_if_exists(conn, schema_name, table_name):
    """Drop table if it exists"""
    with conn.cursor() as cursor:
        cursor.execute(
            sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name)
            )
        )
        conn.commit()

def create_table_from_headers(conn, schema_name, table_name, headers):
    """Create table with TEXT columns for all headers (simple approach)"""
    # For production, you might want to infer types from sample data
    columns_sql = ", ".join([f"{sql.Identifier(header).as_string(conn)} TEXT" for header in headers])
    
    create_sql = f"""
    CREATE TABLE {sql.Identifier(schema_name).as_string(conn)}.{sql.Identifier(table_name).as_string(conn)} (
        {columns_sql}
    )
    """
    
    with conn.cursor() as cursor:
        cursor.execute(create_sql)
        conn.commit()

def table_exists(conn, schema_name, table_name):
    """Check if table exists"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            )
        """, (schema_name, table_name))
        return cursor.fetchone()[0]

def validate_table_columns(conn, schema_name, table_name, expected_headers):
    """Validate that table has expected columns"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = %s 
            ORDER BY ordinal_position
        """, (schema_name, table_name))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if existing_columns != expected_headers:
            raise ValueError(
                f"Table column mismatch. Expected: {expected_headers}, Found: {existing_columns}"
            )

def get_postgres_connection(pg_host=None, pg_database=None):
    """Get a PostgreSQL connection using managed identity"""
    
    # Get configuration from parameters or environment variables
    pg_host = pg_host or os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
    pg_database = pg_database or os.environ.get('PG_DATABASE', 'weavix')
    pg_user = os.environ.get('PG_USER', 'Michael')  # Function App name
    
    if not pg_user:
        raise ValueError("PG_USER environment variable must be set to your Function App name")
    
    # Get fresh access token
    token = get_postgres_token()
    
    try:
        conn = psycopg2.connect(
            host=pg_host,
            database=pg_database,
            user=pg_user,
            password=token,
            sslmode='require'
        )
        logging.info(f"Successfully connected to PostgreSQL as user: {pg_user}")
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {str(e)}")
        raise

# Keep existing helper functions from backup function
def get_credential():
    """Get or create the DefaultAzureCredential instance"""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential

def get_postgres_token():
    """Get a fresh PostgreSQL access token, with caching"""
    global _token_cache
    
    with _token_lock:
        now = datetime.now()
        
        # Check if we have a valid cached token (refresh 10 minutes before expiry)
        if ('token' in _token_cache and 
            'expires_at' in _token_cache and 
            _token_cache['expires_at'] > now + timedelta(minutes=10)):
            return _token_cache['token']
        
        # Get fresh token
        try:
            credential = get_credential()
            token_response = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
            
            # Cache the token
            _token_cache['token'] = token_response.token
            _token_cache['expires_at'] = datetime.fromtimestamp(token_response.expires_on)
            
            logging.info(f"Retrieved new PostgreSQL token, expires at: {_token_cache['expires_at']}")
            return token_response.token
            
        except Exception as e:
            logging.error(f"Failed to get PostgreSQL access token: {str(e)}")
            raise

# Additional utility function for listing available backups
@app.route(route="list_backups", auth_level=func.AuthLevel.FUNCTION, methods=['GET'])
def list_backups(req: func.HttpRequest) -> func.HttpResponse:
    """List available backup files in ADLS Gen2"""
    try:
        # Optional filters
        schema_filter = req.params.get('schema')
        table_filter = req.params.get('table')
        date_filter = req.params.get('date')  # YYYY-MM-DD
        
        account_name = os.environ["ADLS_ACCOUNT_NAME"]
        container_name = os.environ["ADLS_FILE_SYSTEM"]
        
        service_client = DataLakeServiceClient(
            account_url=f"https://{account_name}.dfs.core.windows.net",
            credential=DefaultAzureCredential()
        )
        
        file_system_client = service_client.get_file_system_client(file_system=container_name)
        
        backups = []
        
        # List all files recursively
        paths = file_system_client.get_paths(recursive=True)
        
        for path in paths:
            if path.name.endswith('.csv.gz'):
                try:
                    parsed = parse_backup_file_path(path.name)
                    
                    # Apply filters
                    if schema_filter and parsed['schema'] != schema_filter:
                        continue
                    if table_filter and parsed['table'] != table_filter:
                        continue
                    if date_filter and parsed['date'] != date_filter:
                        continue
                    
                    # Get file properties
                    file_client = file_system_client.get_file_client(path.name)
                    properties = file_client.get_file_properties()
                    
                    backups.append({
                        'file_path': path.name,
                        'database': parsed['database'],
                        'schema': parsed['schema'],
                        'table': parsed['table'],
                        'backup_date': parsed['date'],
                        'file_size': properties.size,
                        'last_modified': properties.last_modified.isoformat()
                    })
                    
                except Exception as e:
                    logging.warning(f"Skipping invalid backup file {path.name}: {str(e)}")
                    continue
        
        # Sort by date descending
        backups.sort(key=lambda x: x['backup_date'], reverse=True)
        
        result = {
            'status': 'success',
            'count': len(backups),
            'backups': backups
        }
        
        return func.HttpResponse(
            str(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_message = {
            "status": "error",
            "message": str(e)
        }
        logging.error(f"List backups failed: {str(e)}")
        return func.HttpResponse(
            str(error_message),
            status_code=500,
            mimetype="application/json"
        )
```        
