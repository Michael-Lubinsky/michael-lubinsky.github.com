#!/bin/bash

# Snowflake Configuration
SNOWFLAKE_ACCOUNT="blekkbh-hna21809"
SNOWFLAKE_USER="mlubinsky"
SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
SNOWFLAKE_DATABASE="weavix"
SNOWFLAKE_SCHEMA="events"

# Azure Storage Configuration
storageacct=weavixdatalakedevsa
container=adls

# Parameters
SOURCE_DIR="${1:-events_20250907_041000}"  # Directory containing CSV files
TABLE_PREFIX="${2:-}"                      # Optional prefix for table names
SKIP_EXISTING="${3:-false}"               # Skip tables that already exist

echo "Source directory: $SOURCE_DIR"
echo "Table prefix: ${TABLE_PREFIX:-none}"
echo "Skip existing tables: $SKIP_EXISTING"

# Get SAS token for Snowflake
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
    echo "Error: Failed to generate SAS token"
    exit 1
fi

# Get list of CSV files from Azure
echo "Getting file list from Azure Storage..."
az storage fs file list \
    --account-name "$storageacct" \
    --auth-mode login \
    --file-system "$container" \
    --path "$SOURCE_DIR" \
    --query "[?ends_with(name, '.csv') || ends_with(name, '.csv.gz')].name" \
    --output tsv > /tmp/file_list.txt

FILE_COUNT=$(wc -l < /tmp/file_list.txt)
echo "Found $FILE_COUNT CSV files to process"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "No CSV files found in directory: $SOURCE_DIR"
    exit 1
fi

# Create shared file format for all tables
SHARED_FORMAT_NAME="${SNOWFLAKE_SCHEMA}_csv_format"
SHARED_STAGE_NAME="${SNOWFLAKE_SCHEMA}_stage"

# Create initial SQL setup
cat > /tmp/snowflake_schema_setup.sql << SQLEOF
-- Use the specified database and schema
USE DATABASE ${SNOWFLAKE_DATABASE};
USE SCHEMA ${SNOWFLAKE_SCHEMA};
USE WAREHOUSE ${SNOWFLAKE_WAREHOUSE};

-- Create shared file format for CSV files
CREATE OR REPLACE FILE FORMAT ${SHARED_FORMAT_NAME}
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 0
    PARSE_HEADER = TRUE
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    REPLACE_INVALID_CHARACTERS = TRUE
    DATE_FORMAT = 'AUTO'
    TIME_FORMAT = 'AUTO'
    TIMESTAMP_FORMAT = 'AUTO'
    COMPRESSION = 'AUTO';

-- Create shared external stage
CREATE OR REPLACE STAGE ${SHARED_STAGE_NAME}
    URL = 'azure://weavixdatalakedevsa.blob.core.windows.net/adls/${SOURCE_DIR}/'
    CREDENTIALS = (
        AZURE_SAS_TOKEN = '${SAS_TOKEN}'
    )
    FILE_FORMAT = ${SHARED_FORMAT_NAME};

-- Verify stage works
LIST @${SHARED_STAGE_NAME};
SQLEOF

# Execute setup
echo "Setting up Snowflake stage and file format..."
if command -v snowsql &> /dev/null; then
    snowsql \
        -a "$SNOWFLAKE_ACCOUNT" \
        -u "$SNOWFLAKE_USER" \
        -w "$SNOWFLAKE_WAREHOUSE" \
        -d "$SNOWFLAKE_DATABASE" \
        -s "$SNOWFLAKE_SCHEMA" \
        -f /tmp/snowflake_schema_setup.sql
else
    echo "SnowSQL not found. Please install it or run SQL manually."
    exit 1
fi

# Process each file
PROCESSED_COUNT=0
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0

while IFS= read -r file_path; do
    [ -z "$file_path" ] && continue
    
    PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    
    # Extract filename without directory and extension
    filename=$(basename "$file_path")
    table_name=$(echo "$filename" | sed 's/\.csv\.gz$//' | sed 's/\.csv$//')
    
    # Add prefix if specified
    if [ -n "$TABLE_PREFIX" ]; then
        table_name="${TABLE_PREFIX}_${table_name}"
    fi
    
    echo ""
    echo "[$PROCESSED_COUNT/$FILE_COUNT] Processing: $filename -> $table_name"
    
    # Check if table already exists (if skip_existing is true)
    if [ "$SKIP_EXISTING" = "true" ]; then
        TABLE_EXISTS=$(snowsql \
            -a "$SNOWFLAKE_ACCOUNT" \
            -u "$SNOWFLAKE_USER" \
            -w "$SNOWFLAKE_WAREHOUSE" \
            -d "$SNOWFLAKE_DATABASE" \
            -s "$SNOWFLAKE_SCHEMA" \
            -q "SHOW TABLES LIKE '${table_name}'" \
            --output-format=json | jq -r '.[0].name' 2>/dev/null)
        
        if [ "$TABLE_EXISTS" = "$table_name" ]; then
            echo "  Table $table_name already exists, skipping"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            continue
        fi
    fi
    
    # Create SQL for this table
    cat > /tmp/snowflake_table_${table_name}.sql << TABLEEOF
-- Process table: ${table_name}
USE DATABASE ${SNOWFLAKE_DATABASE};
USE SCHEMA ${SNOWFLAKE_SCHEMA};
USE WAREHOUSE ${SNOWFLAKE_WAREHOUSE};

-- Create table with inferred schema
CREATE OR REPLACE TABLE ${table_name}
    USING TEMPLATE (
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
        FROM TABLE(
            INFER_SCHEMA(
                LOCATION => '@${SHARED_STAGE_NAME}/${filename}',
                FILE_FORMAT => '${SHARED_FORMAT_NAME}'
            )
        )
    );

-- Load data into the table
COPY INTO ${table_name}
    FROM '@${SHARED_STAGE_NAME}/${filename}'
    FILE_FORMAT = (FORMAT_NAME = '${SHARED_FORMAT_NAME}')
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- Show results
SELECT COUNT(*) as LOADED_ROWS FROM ${table_name};
TABLEEOF
    
    # Execute table creation and load
    echo "  Creating table and loading data..."
    snowsql \
        -a "$SNOWFLAKE_ACCOUNT" \
        -u "$SNOWFLAKE_USER" \
        -w "$SNOWFLAKE_WAREHOUSE" \
        -d "$SNOWFLAKE_DATABASE" \
        -s "$SNOWFLAKE_SCHEMA" \
        -f /tmp/snowflake_table_${table_name}.sql \
        > /tmp/snowflake_result_${table_name}.log 2>&1
    
    if [ $? -eq 0 ]; then
        # Extract row count from output
        ROW_COUNT=$(grep "LOADED_ROWS" /tmp/snowflake_result_${table_name}.log | tail -1 | awk '{print $3}' || echo "unknown")
        echo "  ✓ Successfully created table $table_name with $ROW_COUNT rows"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ✗ Failed to create table $table_name"
        echo "    Error log: /tmp/snowflake_result_${table_name}.log"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    
    # Clean up temporary SQL file
    rm -f /tmp/snowflake_table_${table_name}.sql
    
done < /tmp/file_list.txt

echo ""
echo "=========================================="
echo "SNOWFLAKE IMPORT SUMMARY"
echo "=========================================="
echo "Source directory: $SOURCE_DIR"
echo "Target schema: ${SNOWFLAKE_DATABASE}.${SNOWFLAKE_SCHEMA}"
echo "Total files found: $FILE_COUNT"
echo "Successfully imported: $SUCCESS_COUNT"
echo "Failed imports: $FAILED_COUNT"
echo "Skipped tables: $SKIPPED_COUNT"
echo "=========================================="

# Show final table list
echo ""
echo "Tables created in ${SNOWFLAKE_DATABASE}.${SNOWFLAKE_SCHEMA}:"
snowsql \
    -a "$SNOWFLAKE_ACCOUNT" \
    -u "$SNOWFLAKE_USER" \
    -w "$SNOWFLAKE_WAREHOUSE" \
    -d "$SNOWFLAKE_DATABASE" \
    -s "$SNOWFLAKE_SCHEMA" \
    -q "SHOW TABLES" \
    --output-format=table

# Clean up
rm -f /tmp/file_list.txt
rm -f /tmp/snowflake_schema_setup.sql
rm -f /tmp/snowflake_result_*.log

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "WARNING: $FAILED_COUNT tables failed to import"
    exit 1
else
    echo ""
    echo "All tables imported successfully!"
fi