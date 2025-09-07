To upload the CSV file to Snowflake and automatically create the table, you'll need to use Snowflake's SQL commands. Here's a script that will handle this:This script provides three methods to upload your CSV file to Snowflake and automatically create the table:

## Key Features:

1. **Automatic table creation** - Table name derived from filename (removes .csv)
2. **Schema inference** - Uses Snowflake's `INFER_SCHEMA` to automatically detect column types from the CSV
3. **Header handling** - Uses the first row as column names
4. **Azure integration** - Creates an external stage pointing to your ADLS Gen2 storage

## How it works:

1. **Creates a file format** - Defines CSV parsing rules
2. **Creates an external stage** - Points to your Azure storage with SAS token
3. **Infers schema** - Automatically detects column names and types from your CSV
4. **Creates table** - Uses the inferred schema
5. **Loads data** - Copies data from Azure to Snowflake table

## Usage:

**Before running, update these variables in the script:**
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER` 
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_SCHEMA`

**Then run:**
```bash
# Save the script as snowflake_upload.sh
chmod +x snowflake_upload.sh
./snowflake_upload.sh consolepageviewed_20250906_210303.csv
```

## Three execution options:

1. **SnowSQL** (recommended) - Automatic execution if SnowSQL is installed
2. **Python script** - Alternative using Python connector
3. **Manual** - Copy the generated SQL to Snowflake Web UI

The script will automatically generate a SAS token for Snowflake to access your Azure storage and handle the entire process of creating the table and loading the data.



```bash
#!/bin/bash

# Snowflake Configuration
SNOWFLAKE_ACCOUNT="your-account.snowflakecomputing.com"
SNOWFLAKE_USER="your-username"
SNOWFLAKE_PASSWORD="your-password"  # Or use key-pair authentication
SNOWFLAKE_WAREHOUSE="your-warehouse"
SNOWFLAKE_DATABASE="your-database"
SNOWFLAKE_SCHEMA="your-schema"

# Azure Storage Configuration (from your previous script)
storageacct=weavixdatalakedevsa
container=adls

# File information
OUTPUT_FILE="${1:-consolepageviewed_20250906_210303.csv}"  # Pass filename as argument or use default
TABLE_NAME=$(basename "$OUTPUT_FILE" .csv)  # Remove .csv extension

echo "Processing file: $OUTPUT_FILE"
echo "Will create table: $TABLE_NAME"

# Create Snowflake SQL commands
STAGE_NAME="${TABLE_NAME}_stage"
FILE_FORMAT_NAME="${TABLE_NAME}_csv_format"

# Generate Snowflake SQL script
cat > /tmp/snowflake_upload.sql << EOF
-- Use the specified database and schema
USE DATABASE ${SNOWFLAKE_DATABASE};
USE SCHEMA ${SNOWFLAKE_SCHEMA};
USE WAREHOUSE ${SNOWFLAKE_WAREHOUSE};

-- Create file format for CSV
CREATE OR REPLACE FILE FORMAT ${FILE_FORMAT_NAME}
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    REPLACE_INVALID_CHARACTERS = TRUE
    DATE_FORMAT = 'AUTO'
    TIME_FORMAT = 'AUTO'
    TIMESTAMP_FORMAT = 'AUTO';

-- Create external stage pointing to Azure ADLS Gen2
CREATE OR REPLACE STAGE ${STAGE_NAME}
    URL = 'azure://weavixdatalakedevsa.dfs.core.windows.net/adls/'
    CREDENTIALS = (
        AZURE_SAS_TOKEN = '${SAS_TOKEN}'
    )
    FILE_FORMAT = ${FILE_FORMAT_NAME};

-- List files in stage to verify connection
LIST @${STAGE_NAME}/${OUTPUT_FILE};

-- Create table with inferred schema
CREATE OR REPLACE TABLE ${TABLE_NAME}
    USING TEMPLATE (
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
        FROM TABLE(
            INFER_SCHEMA(
                LOCATION => '@${STAGE_NAME}/${OUTPUT_FILE}',
                FILE_FORMAT => '${FILE_FORMAT_NAME}'
            )
        )
    );

-- Load data into the table
COPY INTO ${TABLE_NAME}
    FROM '@${STAGE_NAME}/${OUTPUT_FILE}'
    FILE_FORMAT = (FORMAT_NAME = '${FILE_FORMAT_NAME}')
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- Show table info
DESCRIBE TABLE ${TABLE_NAME};

-- Show sample data
SELECT * FROM ${TABLE_NAME} LIMIT 10;

-- Show row count
SELECT COUNT(*) as TOTAL_ROWS FROM ${TABLE_NAME};
EOF

echo "Generated Snowflake SQL script at /tmp/snowflake_upload.sql"

# Method 1: Using SnowSQL (if installed)
if command -v snowsql &> /dev/null; then
    echo "Executing via SnowSQL..."
    
    # Get fresh SAS token for Snowflake to use
    echo "Generating SAS token for Snowflake..."
    SAS_TOKEN=$(az storage container generate-sas \
        --as-user \
        --auth-mode login \
        --account-name "$storageacct" \
        --name "$container" \
        --permissions rl \
        --expiry "$(date -u -v+1d '+%Y-%m-%dT%H:%MZ')" \
        --output tsv)
    
    if [ -z "$SAS_TOKEN" ]; then
        echo "Error: Failed to generate SAS token for Snowflake"
        exit 1
    fi
    
    # Replace SAS_TOKEN placeholder in SQL file
    sed -i.bak "s/\${SAS_TOKEN}/$SAS_TOKEN/g" /tmp/snowflake_upload.sql
    
    # Execute the SQL script
    snowsql \
        -a "$SNOWFLAKE_ACCOUNT" \
        -u "$SNOWFLAKE_USER" \
        -f /tmp/snowflake_upload.sql \
        --variable "database=$SNOWFLAKE_DATABASE" \
        --variable "schema=$SNOWFLAKE_SCHEMA" \
        --variable "warehouse=$SNOWFLAKE_WAREHOUSE"
        
    echo "Snowflake upload completed!"
    
else
    echo "SnowSQL not found. Please install SnowSQL or use the generated SQL script manually."
    echo "SQL script location: /tmp/snowflake_upload.sql"
    echo ""
    echo "To install SnowSQL:"
    echo "1. Download from: https://docs.snowflake.com/en/user-guide/snowsql-install-config.html"
    echo "2. Or use pip: pip install snowflake-connector-python"
    echo ""
    echo "Alternative: Copy the SQL commands and run them in Snowflake Web UI"
fi

# Method 2: Using Python (alternative)
cat > /tmp/snowflake_upload.py << 'PYTHON_EOF'
#!/usr/bin/env python3
import snowflake.connector
import os
import sys

# Configuration
SNOWFLAKE_CONFIG = {
    'account': os.getenv('SNOWFLAKE_ACCOUNT', 'your-account'),
    'user': os.getenv('SNOWFLAKE_USER', 'your-username'),
    'password': os.getenv('SNOWFLAKE_PASSWORD', 'your-password'),
    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'your-warehouse'),
    'database': os.getenv('SNOWFLAKE_DATABASE', 'your-database'),
    'schema': os.getenv('SNOWFLAKE_SCHEMA', 'your-schema')
}

def upload_to_snowflake(output_file, sas_token):
    table_name = os.path.splitext(output_file)[0]
    
    try:
        # Connect to Snowflake
        conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        cursor = conn.cursor()
        
        # Read and execute SQL script
        with open('/tmp/snowflake_upload.sql', 'r') as f:
            sql_script = f.read()
            
        # Replace variables
        sql_script = sql_script.replace('${SAS_TOKEN}', sas_token)
        
        # Execute commands
        for statement in sql_script.split(';'):
            if statement.strip():
                print(f"Executing: {statement.strip()[:100]}...")
                cursor.execute(statement)
                
        print(f"Successfully created table {table_name} and loaded data")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "consolepageviewed_20250906_210303.csv"
    sas_token = sys.argv[2] if len(sys.argv) > 2 else ""
    upload_to_snowflake(output_file, sas_token)
PYTHON_EOF

chmod +x /tmp/snowflake_upload.py

echo ""
echo "Alternative Python script created at: /tmp/snowflake_upload.py"
echo ""
echo "Usage options:"
echo "1. SnowSQL: ./snowflake_upload.sh [filename]"
echo "2. Python: python3 /tmp/snowflake_upload.py [filename] [sas_token]"
echo "3. Manual: Copy SQL from /tmp/snowflake_upload.sql to Snowflake Web UI"
```


The main issue is in this error: 

**"Provided Azure storage endpoint 'weavixdatalakedevsa.dfs.core.windows.net' is currently not supported."**

Snowflake doesn't support the ADLS Gen2 DFS endpoint (`dfs.core.windows.net`) directly. You need to use the Blob Storage endpoint instead (`blob.core.windows.net`).

Let me fix the script to use the correct endpoint:The key fix is changing from `dfs.core.windows.net` to `blob.core.windows.net`. Even though your storage account is ADLS Gen2, Snowflake accesses it through the Blob Storage API endpoint.

However, there's another issue - we need to generate a SAS token that works with the Blob Storage endpoint. Let me also update the SAS token generation:I changed the SAS token generation to use `--auth-mode key` instead of `--auth-mode login` because Snowflake typically works better with account key-based SAS tokens when accessing Azure storage.

**Important:** For the `--auth-mode key` to work, you'll need to either:

1. **Set your storage account key as an environment variable:**
   ```bash
   export AZURE_STORAGE_KEY="your-storage-account-key"
   ```

2. **Or use Azure CLI login with sufficient permissions:**
   ```bash
   az login
   ```

3. **Or provide the key directly in the command** (update the script to include `--account-key` parameter)

Try running the updated script. If you get an authentication error for the SAS token generation, you can find your storage account key in the Azure portal under Storage Account → Access Keys.

The main changes:
1. ✅ **Fixed endpoint**: `blob.core.windows.net` instead of `dfs.core.windows.net`
2. ✅ **Updated SAS token auth**: Uses account key method for better Snowflake compatibility

Run the script again and it should create the stage successfully this time.
