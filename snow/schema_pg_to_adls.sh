#!/bin/bash

# Configuration
HOST=weavix-dev-pg.postgres.database.azure.com
USER='mlubinsky_weavix.com#EXT#@weavix.onmicrosoft.com'
storageacct=weavixdatalakedevsa
container=adls
TENANT=229fe1cd-3500-42fe-9667-2d9a5d2473a0

# Schema and compression settings
SCHEMA_NAME="${1:-events}"
USE_COMPRESSION="${2:-true}"
SKIP_TABLES="${3:-}"  # Comma-separated list of tables to skip

echo "Schema: $SCHEMA_NAME"
echo "Compression: $USE_COMPRESSION"
if [ -n "$SKIP_TABLES" ]; then
    echo "Skipping tables: $SKIP_TABLES"
fi

# Create output directory for this run
RUN_ID=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${SCHEMA_NAME}_${RUN_ID}"
echo "Output directory: $OUTPUT_DIR"

# Generate expiry date (macOS compatible)
expiry=$(date -u -v+1d '+%Y-%m-%dT%H:%MZ')

# Generate SAS token
echo "Generating SAS token..."
SAS=$(az storage container generate-sas \
  --as-user \
  --auth-mode login \
  --account-name "$storageacct" \
  --name "$container" \
  --permissions cwl \
  --expiry "$expiry" \
  --output tsv)

if [ -z "$SAS" ]; then
    echo "Error: Failed to generate SAS token"
    exit 1
fi

# Get access token for PostgreSQL
echo "Getting PostgreSQL access token..."
ACCESS_TOKEN=$(az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up temporary files..."
    rm -f /tmp/table_list.txt
    rm -f /tmp/${SCHEMA_NAME}_*.csv*
}
trap cleanup EXIT

echo "Getting table list from schema: $SCHEMA_NAME"

# Get list of tables in the schema
psql "host=${HOST} port=5432 dbname=weavix user=${USER} password=${ACCESS_TOKEN} sslmode=require" \
     -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = '${SCHEMA_NAME}' AND table_type = 'BASE TABLE';" \
     > /tmp/table_list.txt

# Remove whitespace and empty lines
sed -i.bak 's/^[ \t]*//;s/[ \t]*$//' /tmp/table_list.txt
sed -i.bak '/^$/d' /tmp/table_list.txt

TABLE_COUNT=$(wc -l < /tmp/table_list.txt)
echo "Found $TABLE_COUNT tables in schema $SCHEMA_NAME"

if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "No tables found in schema $SCHEMA_NAME"
    exit 1
fi

# Create summary variables
PROCESSED_COUNT=0
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0

# Process each table
while IFS= read -r table_name; do
    [ -z "$table_name" ] && continue
    
    PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    echo ""
    echo "[$PROCESSED_COUNT/$TABLE_COUNT] Processing table: $table_name"
    
    # Check if table should be skipped
    if [[ ",$SKIP_TABLES," == *",$table_name,"* ]]; then
        echo "  Skipping $table_name (in skip list)"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    # Get row count
    ROW_COUNT=$(psql "host=${HOST} port=5432 dbname=weavix user=${USER} password=${ACCESS_TOKEN} sslmode=require" \
                -t -c "SELECT COUNT(*) FROM ${SCHEMA_NAME}.${table_name};" 2>/dev/null | tr -d ' ')
    
    echo "  Table $table_name has $ROW_COUNT rows"
    
    if [ "$ROW_COUNT" -eq 0 ]; then
        echo "  Warning: Table $table_name is empty, skipping"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    # Determine output filename
    if [ "$USE_COMPRESSION" = "true" ]; then
        OUTPUT_FILE="${OUTPUT_DIR}/${table_name}.csv.gz"
        temp_file="/tmp/${table_name}.csv"
    else
        OUTPUT_FILE="${OUTPUT_DIR}/${table_name}.csv"
        temp_file="/tmp/${table_name}.csv"
    fi
    
    echo "  Exporting to: $OUTPUT_FILE"
    
    # Export data to temporary file
    echo "  Extracting data from PostgreSQL..."
    psql "host=${HOST} port=5432 dbname=weavix user=${USER} password=${ACCESS_TOKEN} sslmode=require" \
         -c "\copy (SELECT * FROM ${SCHEMA_NAME}.${table_name}) TO STDOUT WITH CSV HEADER" > "$temp_file"
    
    PSQL_EXIT_CODE=$?
    
    if [ $PSQL_EXIT_CODE -ne 0 ]; then
        echo "  ERROR: PostgreSQL export failed for $table_name"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
    fi
    
    # Check file size
    TEMP_FILE_SIZE=$(wc -c < "$temp_file")
    echo "  Exported file size: $TEMP_FILE_SIZE bytes"
    
    if [ "$TEMP_FILE_SIZE" -eq 0 ]; then
        echo "  WARNING: Exported file is empty for $table_name"
        rm -f "$temp_file"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
    fi
    
    # Compress if requested
    if [ "$USE_COMPRESSION" = "true" ]; then
        echo "  Compressing file..."
        gzip "$temp_file"
        temp_file="${temp_file}.gz"
        COMPRESSED_SIZE=$(wc -c < "$temp_file")
        COMPRESSION_RATIO=$(echo "scale=1; $COMPRESSED_SIZE * 100 / $TEMP_FILE_SIZE" | bc)
        echo "  Compressed size: $COMPRESSED_SIZE bytes (${COMPRESSION_RATIO}% of original)"
    fi
    
    # Upload to Azure
    echo "  Uploading to Azure Storage..."
    DEST_URL="https://${storageacct}.dfs.core.windows.net/${container}/${OUTPUT_FILE}?${SAS}"
    
    azcopy copy "$temp_file" "$DEST_URL" \
      --from-to=LocalBlobFS \
      --content-type "text/csv" \
      --overwrite=true \
      --check-length=false \
      --log-level=ERROR
    
    AZCOPY_EXIT_CODE=$?
    
    if [ $AZCOPY_EXIT_CODE -eq 0 ]; then
        echo "  ✓ Successfully uploaded $table_name"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ✗ Failed to upload $table_name"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    
    # Clean up temp file
    rm -f "$temp_file"
    
done < /tmp/table_list.txt

echo ""
echo "=========================================="
echo "EXPORT SUMMARY"
echo "=========================================="
echo "Schema: $SCHEMA_NAME"
echo "Output directory: $OUTPUT_DIR"
echo "Compression: $USE_COMPRESSION"
echo "Total tables found: $TABLE_COUNT"
echo "Successfully exported: $SUCCESS_COUNT"
echo "Failed exports: $FAILED_COUNT"
echo "Skipped tables: $SKIPPED_COUNT"
echo "=========================================="

# List uploaded files
echo ""
echo "Files uploaded to Azure Storage:"
az storage fs file list \
    --account-name "$storageacct" \
    --auth-mode login \
    --file-system "$container" \
    --path "$OUTPUT_DIR" \
    -o table

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "WARNING: $FAILED_COUNT tables failed to export"
    exit 1
else
    echo ""
    echo "All tables exported successfully!"
fi