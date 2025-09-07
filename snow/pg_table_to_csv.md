```bash
#!/bin/bash

# Configuration
HOST=weavix-dev-pg.postgres.database.azure.com
USER='mlubinsky_weavix.com#EXT#@weavix.onmicrosoft.com'
storageacct=weavixdatalakedevsa
container=adls
TENANT=229fe1cd-3500-42fe-9667-2d9a5d2473a0
TABLE="consolepageviewed"

# Create timestamped output filename to avoid conflicts
#OUTPUT_FILE="${TABLE}_$(date +%Y%m%d_%H%M%S).csv"
OUTPUT_FILE=${TABLE}
echo "Will create file: $OUTPUT_FILE"

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

# Construct destination URL for the container (azcopy will append filename)
DEST_URL="https://${storageacct}.dfs.core.windows.net/${container}/?${SAS}"

echo "Destination URL: ${DEST_URL}"

# Get access token for PostgreSQL
echo "Getting PostgreSQL access token..."
ACCESS_TOKEN=$(az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token"
    exit 1
fi

echo "Connecting to PostgreSQL..."

# Test the connection and get row count
ROW_COUNT=$(psql "host=${HOST} port=5432 dbname=weavix user=${USER} password=${ACCESS_TOKEN} sslmode=require" \
            -t -c "SELECT COUNT(*) FROM events.${TABLE};" 2>/dev/null | tr -d ' ')

echo "Table ${TABLE} has ${ROW_COUNT} rows"

if [ "$ROW_COUNT" -eq 0 ]; then
    echo "Warning: Table is empty!"
fi

# Since stdin piping doesn't work with ADLS Gen2, use a temporary in-memory approach
# Create a temporary file in /tmp (which is typically a tmpfs in memory on many systems)
temp_file="/tmp/${OUTPUT_FILE}"

echo "Using temporary file approach (will be cleaned up): $temp_file"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up temporary file..."
    rm -f "$temp_file"
}
trap cleanup EXIT

echo "Exporting data from PostgreSQL to temporary file..."

# Export data to temporary file
psql "host=${HOST} port=5432 dbname=weavix user=${USER} password=${ACCESS_TOKEN} sslmode=require" \
     -c "\copy (SELECT * FROM events.${TABLE}) TO STDOUT WITH CSV HEADER" > "$temp_file"

PSQL_EXIT_CODE=$?

if [ $PSQL_EXIT_CODE -ne 0 ]; then
    echo "Error: PostgreSQL export failed with exit code $PSQL_EXIT_CODE"
    exit 1
fi

# Check if file was created and has content
if [ ! -f "$temp_file" ]; then
    echo "Error: Temporary file was not created"
    exit 1
fi

TEMP_FILE_SIZE=$(wc -c < "$temp_file")
echo "Temporary file created with size: $TEMP_FILE_SIZE bytes"

if [ "$TEMP_FILE_SIZE" -eq 0 ]; then
    echo "Warning: Temporary file is empty"
fi

echo "Uploading to Azure Storage..."

# Upload the temporary file to Azure
azcopy copy "$temp_file" "$DEST_URL" \
  --from-to=LocalBlobFS \
  --content-type "text/csv" \
  --overwrite=true \
  --check-length=false \
  --log-level=INFO

AZCOPY_EXIT_CODE=$?

echo "PostgreSQL exit code: $PSQL_EXIT_CODE"
echo "AzCopy exit code: $AZCOPY_EXIT_CODE"

if [ $PSQL_EXIT_CODE -eq 0 ] && [ $AZCOPY_EXIT_CODE -eq 0 ]; then
    echo "Export completed successfully!"

    # Verify the upload
    echo "Verifying upload..."
    FILE_SIZE=$(az storage fs file show \
        --account-name "$storageacct" \
        --auth-mode login \
        --file-system "$container" \
        --path "${OUTPUT_FILE}" \
        --query "size" \
        --output tsv 2>/dev/null)

    if [ -n "$FILE_SIZE" ] && [ "$FILE_SIZE" -gt 0 ]; then
        echo "SUCCESS: File uploaded with size: $FILE_SIZE bytes"
        echo "Local temp file size: $TEMP_FILE_SIZE bytes"
        echo "Azure file size: $FILE_SIZE bytes"

        if [ "$FILE_SIZE" -eq "$TEMP_FILE_SIZE" ]; then
            echo "✓ File sizes match - upload successful!"
        else
            echo "⚠ File sizes don't match - possible upload issue"
        fi
    else
        echo "ERROR: File not found or is empty in Azure storage"
    fi

    # List recent files
    echo ""
    echo "Recent files in Azure Storage:"
    az storage fs file list \
        --account-name "$storageacct" \
        --auth-mode login \
        --file-system "$container" \
        --query "[?contains(name, '${TABLE}')]" \
        -o table
else
    echo "Export failed. PostgreSQL: $PSQL_EXIT_CODE, AzCopy: $AZCOPY_EXIT_CODE"
    exit 1
fi%

```





