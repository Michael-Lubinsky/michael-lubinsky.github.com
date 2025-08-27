### data recovery process works with the Azure CLI and explain the complete recovery workflow.


Excellent catch! You're absolutely right that using a dedicated consumer group is essential. Here's how the recovery process actually works:

## Consumer Group Isolation

**Multiple consumers can read the same Event Hub data simultaneously** because each consumer group maintains independent:
- **Message Position**: Each group tracks its own offset/checkpoint  
- **Processing State**: Groups don't interfere with each other
- **Message Visibility**: ALL groups see ALL messages independently

## Recovery Process Breakdown

### **Step 1: Azure CLI Authentication**
```bash
az login  # Authenticates your session
az account set --subscription "your-sub-id"  # Sets active subscription
```

### **Step 2: File Discovery and Download**
The `download-batch` command:
1. **Lists files** in the ADLS Gen2 directory path
2. **Downloads ALL files** from that path recursively
3. **Preserves structure** in the local destination folder
4. **Handles compression** automatically (detects .gz files)

### **Step 3: Local File Structure**
After running the recovery command, you get:
```
./recovery/
├── 00-batch-abc123.jsonl.gz    # All events from midnight hour
├── 01-batch-def456.jsonl.gz    # All events from 1 AM hour  
├── 14-batch-xyz789.jsonl.gz    # All events from 2 PM hour (if this is what failed)
└── 23-batch-mno345.jsonl.gz    # All events from 11 PM hour
```

## Why This Recovery Works Perfectly

### **Data Completeness**
Your Azure Function using the `snowflake-pipeline` consumer group processes **ALL events** independently of other consumers, so the ADLS Gen2 files contain the complete dataset for recovery.

### **Time-Based Organization** 
The folder hierarchy I implemented:
```
changestreams/inventory_db/products/2025/01/15/
├── 00-batch123.jsonl.gz  ← 12:00 AM - 12:59 AM data
├── 01-batch124.jsonl.gz  ← 01:00 AM - 01:59 AM data
├── 14-batch125.jsonl.gz  ← 02:00 PM - 02:59 PM data  
└── 23-batch126.jsonl.gz  ← 11:00 PM - 11:59 PM data
```

### **Granular Recovery Options**

**Recover specific hour:**
```bash
az storage fs file download \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/15/14-batch125.jsonl.gz" \
  --destination ./recovery/hour-14.jsonl.gz
```

**Recover date range:**
```bash
# Download multiple days
for day in {15..17}; do
  az storage fs file download-batch \
    --file-system mongodb-data \
    --source "changestreams/inventory_db/products/2025/01/${day}/" \
    --destination "./recovery/day-${day}/"
done
```

**Recover specific collection across time:**
```bash
# All products data for January 2025
az storage fs file download-batch \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/" \
  --destination ./recovery/products-january/ \
  --recursive
```

## Advanced Recovery Features

### **Browse Before Download**
```bash
# List available files for a specific day
az storage fs file list \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --path "changestreams/inventory_db/products/2025/01/15/" \
  --output table

# Output:
# Name                     LastModified              ContentLength
# 00-batch123.jsonl.gz     2025-01-15T01:05:00Z     1024567
# 01-batch124.jsonl.gz     2025-01-15T02:05:00Z     998234
# 14-batch125.jsonl.gz     2025-01-15T15:05:00Z     1156789
```

### **Inspect File Content**
```bash
# Download and inspect without full recovery
az storage fs file download \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/15/14-batch125.jsonl.gz" \
  --destination ./temp-inspect.jsonl.gz

# View first few records
gunzip -c ./temp-inspect.jsonl.gz | head -5 | jq '.'
```

### **Recovery with Filtering**
```bash
# Download only insert operations (filter by pattern if needed)
az storage fs file download-batch \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/15/" \
  --destination ./recovery/inserts-only/ \
  --pattern "*insert*.jsonl.gz"  # If you organize by operation type
```

## Key Benefits of This Approach

✅ **Independent Consumer Groups**: Your Snowflake pipeline never conflicts with other Event Hub consumers

✅ **Complete Data Preservation**: Every processed event is permanently stored in organized hierarchy

✅ **Surgical Recovery**: Can recover exact time periods, collections, or operations

✅ **Command Line Efficiency**: Easy automation and scripting for recovery operations

✅ **No Service Disruption**: Recovery operations don't affect ongoing data processing

✅ **Audit Capability**: Can trace exactly what data was processed when

The consumer group isolation is what makes this recovery approach so powerful - 
your Azure Function captures and stores ALL events independently, creating a complete, 
recoverable audit trail in ADLS Gen2's hierarchical structure.


# ADLS Gen2 Data Recovery Guide

## How the Recovery Script Works

### 1. Azure CLI Command Breakdown

```bash
az storage fs file download-batch \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/15/" \
  --destination ./recovery/
```

**Component Explanation:**

- `az storage fs file download-batch`: Azure CLI command for bulk file downloads from ADLS Gen2
- `--file-system mongodb-data`: The ADLS Gen2 filesystem name (container equivalent)
- `--source "changestreams/inventory_db/products/2025/01/15/"`: The folder path in ADLS Gen2
- `--destination ./recovery/`: Local directory where files will be downloaded

### 2. What Actually Happens

1. **Authentication**: Azure CLI uses your logged-in credentials or service principal
2. **File Discovery**: Lists all files in the specified ADLS Gen2 directory
3. **Bulk Download**: Downloads all files preserving the folder structure
4. **Local Storage**: Creates local replica of the remote folder structure

### 3. Example File Structure After Download

```
./recovery/
├── 00-batch-abc123.jsonl.gz    # Hour 00 batch
├── 01-batch-def456.jsonl.gz    # Hour 01 batch  
├── 02-batch-ghi789.jsonl.gz    # Hour 02 batch
└── ...
```

## Complete Recovery Scenarios

### Scenario 1: Recover Specific Hour for One Collection

```bash
# 1. Set up authentication
az login
az account set --subscription "your-subscription-id"

# 2. Download specific hour data
az storage fs file download-batch \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/products/2025/01/15/" \
  --destination ./recovery/products/2025-01-15/ \
  --pattern "14-*.jsonl.gz"  # Only hour 14

# 3. Verify download
ls -la ./recovery/products/2025-01-15/
# Output: 14-batch-xyz789.jsonl.gz
```

### Scenario 2: Recover Entire Day for Database

```bash
# Download all collections for entire day
az storage fs file download-batch \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --source "changestreams/inventory_db/" \
  --destination ./recovery/inventory_db/ \
  --pattern "*/2025/01/15/*.jsonl.gz"
```

### Scenario 3: Recover Multiple Hours

```bash
# Download specific time range (hours 10-15)
for hour in {10..15}; do
  hour_padded=$(printf "%02d" $hour)
  az storage fs file download-batch \
    --account-name yourstorageaccount \
    --file-system mongodb-data \
    --source "changestreams/inventory_db/products/2025/01/15/" \
    --destination "./recovery/products/hour-${hour_padded}/" \
    --pattern "${hour_padded}-*.jsonl.gz"
done
```

## Data Recovery to Snowflake

### Method 1: Direct COPY Command (Recommended)

```sql
-- Recover specific hour to temporary table
CREATE OR REPLACE TABLE mongodb_changes_recovery AS
SELECT * FROM mongodb_changes WHERE 1=0; -- Copy structure only

-- Load specific files from ADLS Gen2
COPY INTO mongodb_changes_recovery
FROM @mongodb_stage/inventory_db/products/2025/01/15/
PATTERN = '14-.*\.jsonl\.gz'  -- Hour 14 only
FILE_FORMAT = json_format;

-- Validate recovery data
SELECT COUNT(*) FROM mongodb_changes_recovery;
SELECT operation_type, COUNT(*) FROM mongodb_changes_recovery GROUP BY 1;

-- Merge back to main table (avoiding duplicates)
MERGE INTO mongodb_changes AS target
USING mongodb_changes_recovery AS source
ON target.event_id = source.event_id
WHEN NOT MATCHED THEN INSERT (
  event_id, processed_timestamp, partition_id, offset, sequence_number,
  enqueued_time, operation_type, database_name, collection_name,
  document_key, full_document, update_description, cluster_time, raw_event
) VALUES (
  source.event_id, source.processed_timestamp, source.partition_id, 
  source.offset, source.sequence_number, source.enqueued_time,
  source.operation_type, source.database_name, source.collection_name,
  source.document_key, source.full_document, source.update_description, 
  source.cluster_time, source.raw_event
);
```

### Method 2: Local Processing and Re-upload

```bash
# 1. Download and decompress files locally
mkdir -p ./recovery/processed/
cd ./recovery/products/2025-01-15/

# 2. Decompress and combine files
for file in *.jsonl.gz; do
  gunzip -c "$file" >> ../processed/combined_hour_14.jsonl
done

# 3. Re-upload to different stage location for recovery
az storage fs file upload \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --source ./processed/combined_hour_14.jsonl \
  --path "recovery/inventory_db/products/2025-01-15-hour-14.jsonl"

# 4. Load from recovery location in Snowflake
COPY INTO mongodb_changes_recovery
FROM @mongodb_stage/recovery/inventory_db/products/
PATTERN = '2025-01-15-hour-14\.jsonl'
FILE_FORMAT = json_format;
```

## Advanced Recovery Scripts

### Recovery Automation Script

```bash
#!/bin/bash
# recovery-script.sh

STORAGE_ACCOUNT="yourstorageaccount"
FILESYSTEM="mongodb-data"
DATABASE=$1
COLLECTION=$2
DATE=$3  # Format: 2025/01/15
HOUR=$4  # Format: 14

if [[ -z "$DATABASE" || -z "$COLLECTION" || -z "$DATE" || -z "$HOUR" ]]; then
  echo "Usage: $0 <database> <collection> <YYYY/MM/DD> <HH>"
  echo "Example: $0 inventory_db products 2025/01/15 14"
  exit 1
fi

# Create recovery directory
RECOVERY_DIR="./recovery/${DATABASE}/${COLLECTION}/${DATE/\//-}/hour-${HOUR}"
mkdir -p "$RECOVERY_DIR"

echo "Downloading data for ${DATABASE}.${COLLECTION} on ${DATE} hour ${HOUR}..."

# Download files
az storage fs file download-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --file-system "$FILESYSTEM" \
  --source "changestreams/${DATABASE}/${COLLECTION}/${DATE}/" \
  --destination "$RECOVERY_DIR" \
  --pattern "${HOUR}-*.jsonl.gz"

# Count records
echo "Files downloaded to: $RECOVERY_DIR"
ls -la "$RECOVERY_DIR"

# Optional: Decompress and count records
TOTAL_RECORDS=0
for file in "$RECOVERY_DIR"/*.jsonl.gz; do
  if [[ -f "$file" ]]; then
    RECORDS=$(gunzip -c "$file" | wc -l)
    echo "File $(basename "$file"): $RECORDS records"
    TOTAL_RECORDS=$((TOTAL_RECORDS + RECORDS))
  fi
done

echo "Total records recovered: $TOTAL_RECORDS"
```

### Usage Examples

```bash
# Make script executable
chmod +x recovery-script.sh

# Recover specific hour
./recovery-script.sh inventory_db products 2025/01/15 14

# Recover entire day (loop through hours)
for hour in {00..23}; do
  ./recovery-script.sh inventory_db products 2025/01/15 $hour
done
```

## Consumer Group Configuration

### 1. Create Consumer Group in Azure

```bash
# Create dedicated consumer group for Snowflake pipeline
az eventhubs consumergroup create \
  --resource-group mongodb-pipeline-rg \
  --namespace-name mongodb-eh-namespace \
  --eventhub-name mongodb-changes \
  --name snowflake-pipeline

# Create additional consumer groups for other services
az eventhubs consumergroup create \
  --namespace-name mongodb-eh-namespace \
  --eventhub-name mongodb-changes \
  --name real-time-analytics

az eventhubs consumergroup create \
  --namespace-name mongodb-eh-namespace \
  --eventhub-name mongodb-changes \
  --name backup-service
```

### 2. Update Environment Variables

```bash
# Azure Function Configuration
CONSUMER_GROUP="snowflake-pipeline"

# Other Applications
# App A uses: CONSUMER_GROUP="real-time-analytics" 
# App B uses: CONSUMER_GROUP="backup-service"
# App C uses: CONSUMER_GROUP="$Default"
```

## Recovery Verification Process

### 1. Identify Missing Data

```sql
-- In Snowflake: Find gaps in ingested data
WITH hourly_counts AS (
  SELECT 
    DATE_TRUNC('hour', _snowflake_ingested_at) as hour,
    database_name,
    collection_name,
    COUNT(*) as record_count
  FROM mongodb_changes 
  WHERE _snowflake_ingested_at >= '2025-01-15 00:00:00'
    AND _snowflake_ingested_at < '2025-01-16 00:00:00'
  GROUP BY 1, 2, 3
),
expected_hours AS (
  SELECT 
    DATEADD('hour', seq4(), '2025-01-15 00:00:00') as hour,
    'inventory_db' as database_name,
    'products' as collection_name
  FROM TABLE(GENERATOR(ROWCOUNT => 24))
)
SELECT 
  e.hour,
  e.database_name,
  e.collection_name,
  COALESCE(h.record_count, 0) as actual_records
FROM expected_hours e
LEFT JOIN hourly_counts h 
  ON e.hour = h.hour 
  AND e.database_name = h.database_name
  AND e.collection_name = h.collection_name
WHERE COALESCE(h.record_count, 0) = 0  -- Missing hours
ORDER BY e.hour;
```

### 2. Execute Recovery

```bash
# Download missing hour data
./recovery-script.sh inventory_db products 2025/01/15 14

# Verify files exist in ADLS Gen2
az storage fs file list \
  --account-name yourstorageaccount \
  --file-system mongodb-data \
  --path "changestreams/inventory_db/products/2025/01/15/" \
  --query "[?name contains '14-'].{name:name, lastModified:lastModified, contentLength:contentLength}"
```

### 3. Reload to Snowflake

```sql
-- Create temporary recovery table
CREATE OR REPLACE TABLE mongodb_changes_recovery_temp LIKE mongodb_changes;

-- Load missing hour data
COPY INTO mongodb_changes_recovery_temp
FROM @mongodb_stage/inventory_db/products/2025/01/15/
PATTERN = '14-.*\.jsonl\.gz'
FILE_FORMAT = json_format;

-- Verify data looks correct
SELECT * FROM mongodb_changes_recovery_temp LIMIT 10;

-- Insert into main table (avoiding duplicates)
INSERT INTO mongodb_changes 
SELECT * FROM mongodb_changes_recovery_temp
WHERE event_id NOT IN (SELECT event_id FROM mongodb_changes);

-- Clean up
DROP TABLE mongodb_changes_recovery_temp;
```

## Benefits of This Recovery Approach

✅ **Granular Recovery**: Can recover specific hours, days, or collections
✅ **Non-Disruptive**: Recovery doesn't affect ongoing processing
✅ **Data Integrity**: Duplicate detection prevents data corruption
✅ **Audit Trail**: Complete history preserved in hierarchical structure
✅ **Fast Navigation**: Easy to find and recover specific time periods
✅ **Multiple Consumers**: Each service processes independently

The consumer group isolation ensures that your recovery operations and ongoing data processing never interfere with each other,  
while the hierarchical ADLS Gen2 structure makes data recovery operations fast and intuitive.
