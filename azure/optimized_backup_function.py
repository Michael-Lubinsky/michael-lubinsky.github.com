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

app = func.FunctionApp()

# Global variables for connection pooling and token management
_token_cache = {}
_token_lock = threading.Lock()
_credential = None

# Run at 2 am every day
@app.timer_trigger(schedule="0 0 2 * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def pg_table_day_to_csv(myTimer: func.TimerRequest) -> None:
    """Daily scheduled backup of PostgreSQL tables to ADLS Gen2"""
    if myTimer.past_due:
        logging.info('The timer is past due!')

    try:
        default_tables = "events.bannerclicked" # just for testing 
        tables_string = os.environ.get("TABLES", default_tables)
        tables = [item.strip() for item in tables_string.split(',')]

        # Generate backup date (yesterday's data)
        now = datetime.utcnow()
        backup_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logging.info(f"Starting daily backup for {len(tables)} tables, backup_date: {backup_date}")
        
        success_count = 0
        error_count = 0
        
        for table in tables:
            try:
                backup_table_optimized(table, backup_date)
                success_count += 1
                logging.info(f"Successfully backed up table: {table}")
            except Exception as e:
                error_count += 1
                logging.error(f"Failed to backup table {table}: {str(e)}")
        
        logging.info(f"Daily backup completed. Success: {success_count}, Errors: {error_count}")

    except Exception as e:
        logging.error(f'Error in daily backup: {str(e)}')

def backup_table_optimized(table, backup_date):
    """Memory-optimized backup using PostgreSQL COPY and GZIP streaming"""
    conn = None
    try:
        # Validate table format (schema.table)
        table_parts = table.split('.')
        if len(table_parts) != 2:
            raise ValueError(f"Invalid table format. Expected 'schema.table', got: {table}")

        schema = table_parts[0]
        table_name = table_parts[1]

        database = os.environ.get('PG_DATABASE', 'weavix')
        
        # Get timestamp column from environment or use default
        timestamp_column = os.environ.get('TIMESTAMP_COLUMN', 'historytimestamp')
        
        # Build SQL query - PostgreSQL will handle CSV formatting
        # Using proper schema.table qualification and parameterized dates
        query = f"""
        SELECT * FROM {schema}.{table_name}
        WHERE {timestamp_column} >= '{backup_date}'::date 
        AND {timestamp_column} < '{backup_date}'::date + INTERVAL '1 day'
        """
        
        logging.info(f'Starting optimized backup for table {table}, date: {backup_date}')
        
        # Get database connection
        conn = get_postgres_connection()
        
        # Check if data exists first (optional - for logging)
        with conn.cursor() as cursor:
            count_query = f"""
            SELECT COUNT(*) FROM {schema}.{table_name}
            WHERE {timestamp_column} >= '{backup_date}'::date 
            AND {timestamp_column} < '{backup_date}'::date + INTERVAL '1 day'
            """
            cursor.execute(count_query)
            row_count = cursor.fetchone()[0]
            
            if row_count == 0:
                logging.info(f"No data found for table {table} on date {backup_date}")
                return
            
            logging.info(f"Found {row_count} rows for table {table}")
        
        # Method 1: Using SpooledTemporaryFile (simpler, but may use disk)
        export_table_to_adls_gzip_spooled(conn, query, schema, table_name, backup_date, database)
        
        logging.info(f'Successfully backed up {row_count} rows from {table}')
            
    except Exception as e:
        logging.error(f'Error backing up table {table}: {str(e)}')
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logging.error(f'Error closing database connection: {str(e)}')

def export_table_to_adls_gzip_spooled(conn, sql_query, schema, table_name, backup_date, database):
    """Export using SpooledTemporaryFile - simpler approach"""
    try:
        # ADLS path
        adls_path = f"{database}/{schema}/{table_name}/{table_name}.{backup_date}.csv.gz"
        
        # Use SpooledTemporaryFile - keeps data in memory up to max_size, then spills to disk
        with tempfile.SpooledTemporaryFile(max_size=100*1024*1024) as tmp_file:  # 100 MB threshold
            with gzip.GzipFile(fileobj=tmp_file, mode='wb') as gz_file:
                with conn.cursor() as cursor:
                    # PostgreSQL handles CSV formatting - much faster than Python
                    copy_sql = f"COPY ({sql_query}) TO STDOUT WITH (FORMAT csv, HEADER true)"
                    cursor.copy_expert(copy_sql, gz_file)
            
            # Reset file pointer to beginning
            tmp_file.seek(0)
            
            # Upload to ADLS Gen2
            upload_stream_to_adls_file(
                adls_path,
                tmp_file,
                content_type="application/gzip"
            )
            
            logging.info(f'Successfully uploaded compressed backup to: {adls_path}')
            
    except Exception as e:
        logging.error(f'Error in spooled export: {str(e)}')
        raise

def export_table_to_adls_gzip_streaming(conn, sql_query, schema, table_name, backup_date, database):
    """True streaming approach using pipes - most memory efficient"""
    import os
    import threading
    
    try:
        # ADLS path
        adls_path = f"{database}/{schema}/{table_name}/{table_name}.{backup_date}.csv.gz"
        
        # Create pipe for streaming
        read_fd, write_fd = os.pipe()
        
        # Convert file descriptors to file objects
        read_file = os.fdopen(read_fd, 'rb')
        write_file = os.fdopen(write_fd, 'wb')
        
        exception_holder = {'exception': None}
        
        def writer_thread():
            """Thread that writes gzipped data to the pipe"""
            try:
                with gzip.GzipFile(fileobj=write_file, mode='wb') as gz_file:
                    with conn.cursor() as cursor:
                        copy_sql = f"COPY ({sql_query}) TO STDOUT WITH (FORMAT csv, HEADER true)"
                        cursor.copy_expert(copy_sql, gz_file)
            except Exception as e:
                exception_holder['exception'] = e
                logging.error(f"Writer thread error: {str(e)}")
            finally:
                write_file.close()
        
        # Start writer thread
        writer = threading.Thread(target=writer_thread)
        writer.start()
        
        try:
            # Upload from read end of pipe (streaming)
            upload_stream_to_adls_file(
                adls_path,
                read_file,
                content_type="application/gzip"
            )
        finally:
            read_file.close()
            writer.join()  # Wait for writer thread to finish
        
        # Check if writer thread had an exception
        if exception_holder['exception']:
            raise exception_holder['exception']
            
        logging.info(f'Successfully uploaded streaming backup to: {adls_path}')
        
    except Exception as e:
        logging.error(f'Error in streaming export: {str(e)}')
        raise

def upload_stream_to_adls_file(path, file_stream, content_type):
    """Upload a file stream to ADLS Gen2"""
    try:
        # Create the DataLake service client with managed identity
        account_name = os.environ["ADLS_ACCOUNT_NAME"]
        service_client = DataLakeServiceClient(
            account_url=f"https://{account_name}.dfs.core.windows.net",
            credential=DefaultAzureCredential()
        )
        
        # Get the file system (container) client
        container_name = os.environ["ADLS_FILE_SYSTEM"]
        file_system_client = service_client.get_file_system_client(file_system=container_name)
        file_client = file_system_client.get_file_client(path)
        
        # Delete existing file if it exists
        try:
            file_client.delete_file()
            logging.info(f"Deleted existing file: {path}")
        except Exception:
            # File doesn't exist, which is fine
            pass
        
        # Upload the stream directly
        file_client.upload_data(
            file_stream, 
            overwrite=True,
            content_settings={"content_type": content_type} if content_type else None
        )
        
        # Get file size for logging
        properties = file_client.get_file_properties()
        file_size = properties.size
        
        logging.info(f'Successfully uploaded file: {path} ({file_size} bytes) to container: {container_name}')
        
    except Exception as e:
        logging.error(f'Error uploading stream to ADLS Gen2: {str(e)}')
        raise

# Keep your existing helper functions
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

def get_postgres_connection():
    """Get a PostgreSQL connection using managed identity"""
    
    # Get configuration from environment variables
    pg_host = os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
    pg_database = os.environ.get('PG_DATABASE', 'weavix')
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

# HTTP trigger for manual execution
@app.route(route="backup_manual", auth_level=func.AuthLevel.ANONYMOUS)
def backup_manual(req: func.HttpRequest) -> func.HttpResponse:
    """Manual trigger for testing backups"""
    try:
        # Get parameters from query string
        table = req.params.get('table')  # Example: events.bannerclicked
        date_str = req.params.get('date')
        streaming = req.params.get('streaming', 'false').lower() == 'true'  # Optional streaming mode
        
        if not table:
            return func.HttpResponse(
                "Missing required parameter: table (format: schema.table)", 
                status_code=400
            )
        
        # Parse or default the backup date
        if not date_str:
            # Default to yesterday
            backup_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            try:
                # Validate date format
                datetime.strptime(date_str, '%Y-%m-%d')
                backup_date = date_str
            except ValueError:
                return func.HttpResponse(
                    "Invalid date format. Use YYYY-MM-DD format.", 
                    status_code=400
                )
        
        logging.info(f"Manual backup requested for table: {table}, date: {backup_date}, streaming: {streaming}")
        
        # Perform the backup
        backup_table_optimized(table, backup_date)
        
        success_message = f"Optimized backup completed successfully for {table} on {backup_date}"
        logging.info(success_message)
        
        return func.HttpResponse(success_message, status_code=200)
        
    except Exception as e:
        error_message = f"Manual backup failed: {str(e)}"
        logging.error(error_message)
        return func.HttpResponse(error_message, status_code=500)