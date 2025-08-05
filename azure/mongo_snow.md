# Data Transfer From MongoDB to Snowflake
Weavix MongoDB collections can be updated
New Weavix MongoDB can be created any time

In this case we need to implement Change Data Capture (CDC) Pipeline

```
MongoDB
   |
   |  (Azure Function / Python on Timer Trigger)
   v
Python App on Azure Container Instance (ACI) or Azure Functions (long-running)
   |
   |  [Extract → Flatten → Save Parquet to Azure Blob]
   v
Azure Blob Storage
   |
   |  [Snowflake COPY INTO from Azure Stage]
   v
Snowflake (optimized flat tables)
```
| Component                                | Reason to Keep                      |
| ---------------------------------------- | ----------------------------------- |
| **Azure Functions** or **Timer Trigger** | Lightweight and cheap orchestration |
| **Python**                               | Simple ETL logic — easy to manage   |
| **Azure Container Instance (ACI)**       | Cost-effective for periodic jobs    |
| **Blob Storage**                         | Durable, scalable staging layer     |
| **Snowflake**                            | Final analytics warehouse           |

Optional Advanced Scenarios

| Feature               | Solution without Databricks                   |
| --------------------- | --------------------------------------------- |
| Real-time ingestion   | Use MongoDB Change Streams + Azure Event Hubs |
| Parallel processing   | Use Azure Durable Functions or Azure Batch    |
| Schema inference      | Handled by Python `pandas` + Parquet schema   |
| Complex normalization | Done in Python before writing to blob         |
| Monitoring            | Use Azure Monitor or add logging to Snowflake |



## Azure Data Factory Pipeline 

Why Use Azure Data Factory (ADF) for MongoDB → Snowflake?
Azure Data Factory (ADF) is absolutely a strong candidate for this use case. 
It was omitted in the first pipeline because:

You asked for efficiency, and

ADF can sometimes feel heavy or costly for simple or highly dynamic Mongo collections 
(e.g., auto-discovering new collections and schemas)

But for managed orchestration and low-code pipelines, ADF does make sense, especially if:

### When ADF is a Good Fit

| Scenario                                 | ADF Strength            |
| ---------------------------------------- | ----------------------- |
| Scheduled, automated data movement       | ✅ Native                |
| Azure-native data orchestration          | ✅ Excellent integration |
| Transformations with minimal code        | ✅ Built-in Data Flows   |
| Monitoring and retry logic               | ✅ Built-in              |
| Team prefers low-code / visual pipelines | ✅ Ideal                 |


### Where ADF Has Limitations

| Scenario                                  | Reason                                                                                                            |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **MongoDB with many dynamic collections** | ADF is not dynamic — you must **manually define** each collection-to-sink mapping or generate it programmatically |
| **Need to flatten deeply nested JSON**    | ADF has limited ability to handle complex nested data without external transformation (i.e., Python or Spark)     |
| **Need full schema control / versioning** | Easier in code-based ETL than ADF UI                                                                              |
| **Frequent schema drift**                 | Harder to manage in ADF UI                                                                                        |



Azure Data Factory Pipeline

- Triggers the pipeline on a schedule (every N minutes/hours)
- Lists all collections in MongoDB
- Submits each collection for processing via event or job queue (e.g., Azure Queue)


### Are you recommending Azure Function or Azure data factory fir thi pipeline?


Great question! Let me clarify the optimal approach.  
I recommend Azure Data Factory as the primary orchestrator with minimal Azure Functions only where absolutely necessary.

Recommended Approach: ADF-Centric Pipeline
Azure Data Factory Should Handle:
1 Collection Discovery - Using native MongoDB connector
2 Data Movement - MongoDB to ADLS Gen2 to Snowflake
3 Orchestration - Scheduling, error handling, monitoring
4 Change Data Capture - Through scheduled incremental loads

Azure Functions Only For:
1 MongoDB Change Streams (if real-time CDC is critical)
2 Complex custom logic that ADF can't handle natively

#### Why ADF-Centric is Better:

Enhanced MongoDB to Snowflake Pipeline for Dynamic Collections

My Recommendation: Azure Data Factory Primary

ADF Advantages:
- Native MongoDB Connector - No custom code needed
- Built-in Error Handling - Automatic retries, dead letter queues
- Visual Pipeline Designer - Easy to maintain and debug
- Enterprise Features - Monitoring, alerting, SLA management
- Cost Predictable - Fixed monthly cost (~$50-100)
- Scaling - Automatic with Data Integration Units

Functions Disadvantages for ETL:

- Timeout Limits - 10 minutes max execution time
- State Management - Complex for long-running processes
- Error Recovery - Manual implementation needed
- Monitoring Complexity - Multiple functions to track
- Cold Start Delays - Inconsistent performance
- 
When to Use Each:

Use ADF For:
✅ Collection Discovery - List collections, get stats
✅ Bulk Data Movement - MongoDB → ADLS → Snowflake
✅ Scheduled Processing - Hourly/daily batch loads
✅ Pipeline Orchestration - Complex workflows
✅ Error Handling - Built-in retry and monitoring

Use Functions Only For:
⚠️ Real-time Change Streams - If sub-hour latency is critical
⚠️ Custom Business Logic - Complex transformations ADF can't handle
⚠️ Event-driven Triggers - Immediate response to specific events

Recommended Hybrid Approach:
90% ADF + 10% Functions

1 Primary Pipeline: ADF handles all collection discovery and bulk data movement
2 Optional Functions: Only for critical collections requiring real-time CDC
3 Event Hub: Bridge between Functions and ADF for real-time triggers


Cost Comparison:
- ADF-Only: $50-100/month + compute costs
- Functions-Heavy: $20-200/month + unpredictable scaling costs
- Hybrid: $70-120/month (predictable)
Bottom Line: Start with ADF-only. Add Functions later only if you need sub-hour latency for specific collections.




**No, you don't need Azure Blob Storage or Azure Container Instances for this pipeline.**

Let me explain why and what you actually need:

## **Azure Blob Storage - NOT Needed**

### Why NOT:
- **Azure Data Lake Gen2 (ADLS Gen2) replaces it** - ADLS Gen2 is built on Blob Storage but optimized for analytics
- **ADLS Gen2 has hierarchical namespace** - Better for organizing data by database/collection/date
- **Native Snowflake integration** - Snowflake works better with ADLS Gen2
- **Better performance** - Optimized for large file operations

### **Use ADLS Gen2 Instead:**
```
Container: datalake
├── raw/mongodb/
│   ├── database1/collection1/year=2024/month=01/day=15/
│   └── database2/collection2/year=2024/month=01/day=15/
├── staging/snowflake/
└── processed/
```

## **Azure Container Instances - NOT Needed**

### Why NOT:
- **Azure Data Factory handles orchestration** - No need for custom containers
- **Serverless approach is better** - Functions scale automatically
- **Additional complexity** - Container management overhead
- **Higher costs** - Always-on containers vs pay-per-execution

### **What Handles Container-like Tasks:**
- **Azure Data Factory** - Pipeline orchestration
- **Azure Functions** - Serverless compute (if needed)
- **Snowflake** - Data processing and transformation

## **What You Actually Need:**## **Storage Architecture:**

### **ADLS Gen2 Structure:**
```
Storage Account: yourdatalake
├── Container: raw
│   └── mongodb/
│       ├── database1/
│       │   ├── collection1/year=2024/month=01/day=15/hour=10/
│       │   └── collection2/year=2024/month=01/day=15/hour=10/
│       └── database2/
│           └── collection3/year=2024/month=01/day=15/hour=10/
├── Container: staging
│   └── snowflake/
└── Container: processed
    └── analytics/
```

## **Why This Architecture Works:**

### **ADLS Gen2 Benefits:**
- **Hierarchical Namespace** - Organize by database/collection/date
- **Snowflake Native Integration** - Direct `COPY INTO` commands
- **Cost Effective** - Pay only for storage used
- **Performance** - Optimized for large analytics workloads
- **Security** - Role-based access control

### **ADF Benefits:**
- **Managed Service** - No infrastructure to maintain
- **Native Connectors** - MongoDB and Snowflake built-in
- **Visual Designer** - Easy pipeline creation and maintenance
- **Enterprise Features** - Monitoring, alerting, retry logic
- **Auto-scaling** - Scales with workload automatically

## **Total Service Requirements:**

### **Minimal Setup (Recommended):**
```
1. Azure Data Factory          ($50-100/month)
2. ADLS Gen2                   ($20-50/month)
3. Azure Key Vault             ($5/month)
4. Snowflake (External)        ($200+/month)
───────────────────────────────────────────
Total Azure Cost: $75-155/month
```

### **With Real-time CDC (If Needed):**
```
1. Azure Data Factory          ($50-100/month)
2. ADLS Gen2                   ($20-50/month)
3. Azure Key Vault             ($5/month)
4. Azure Functions             ($10-30/month)
5. Azure Event Hub             ($10-20/month)
───────────────────────────────────────────
Total Azure Cost: $95-205/month
```

## **Container Alternative (NOT Recommended):**

If you insisted on using containers, you'd need:
- **Azure Container Instances**: $30-100/month (always running)
- **Azure Container Registry**: $5/month
- **Custom code maintenance**: Developer time
- **Orchestration complexity**: Additional logic needed

**This would cost MORE and provide LESS functionality than the ADF approach.**

## **Final Recommendation:**

**Start with just these 3 services:**
1. **Azure Data Factory** - Pipeline orchestration
2. **ADLS Gen2** - Data staging
3. **Azure Key Vault** - Credential management

This gives you a complete, enterprise-grade ETL pipeline for ~$75-155/month in Azure costs (plus Snowflake costs).

Would you like me to show you the specific ADLS Gen2 configuration and how it integrates with ADF and Snowflake?


# Streamlined MongoDB to Snowflake Pipeline (No Spark)

## Recommended Architecture: ADF-Centric

```
MongoDB Collections → Azure Data Factory → ADLS Gen2 → Snowflake → Analytics Tables
        ↓                      ↓             ↓          ↓
   Native Connector      Orchestration    Staging    Native Loading
```

**Optional for Real-time CDC:**
```
MongoDB Change Streams → Azure Functions → Event Hub → ADF Trigger
```

## Required Azure Services

### **Core Services (Required):**

1. **Azure Data Factory** 
   - Pipeline orchestration
   - MongoDB native connector
   - Snowflake native connector
   - Cost: ~$50-100/month

2. **Azure Data Lake Storage Gen2 (ADLS Gen2)**
   - Staging area for data files
   - Hierarchical namespace for organization
   - Native integration with Snowflake
   - Cost: ~$20-50/month (depending on volume)

3. **Azure Key Vault**
   - Store connection strings securely
   - MongoDB credentials
   - Snowflake credentials
   - Cost: ~$5/month

### **Optional Services:**

4. **Azure Functions** (Only if real-time CDC needed)
   - MongoDB Change Streams processing
   - Event-driven triggers
   - Cost: ~$10-30/month

5. **Azure Event Hub** (Only with Functions)
   - Bridge between Functions and ADF
   - Real-time event streaming
   - Cost: ~$10-20/month

### **NOT Needed:**
❌ **Azure Blob Storage** - Replaced by ADLS Gen2  
❌ **Azure Container Instances** - Replaced by ADF + Functions  
❌ **Azure Kubernetes Service** - Overkill for this use case  
❌ **Azure Service Bus** - Event Hub sufficient if needed  
❌ **Azure Logic Apps** - ADF handles orchestration better

## Core Pipeline Components

### 1. Collection Discovery with Azure Data Factory

#### ADF Discovery Pipeline
```json
{
  "name": "MongoDB-Collection-Discovery",
  "activities": [
    {
      "name": "List-MongoDB-Collections",
      "type": "Lookup",
      "typeProperties": {
        "source": {
          "type": "MongoDbV2Source",
          "query": "db.runCommand('listCollections')"
        },
        "dataset": {
          "referenceName": "MongoDB_Admin_Dataset"
        },
        "firstRowOnly": false
      }
    },
    {
      "name": "Update-Collection-Registry",
      "type": "ForEach",
      "dependsOn": [{"activity": "List-MongoDB-Collections", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "items": "@activity('List-MongoDB-Collections').output.value",
        "activities": [
          {
            "name": "Get-Collection-Stats",
            "type": "Lookup",
            "typeProperties": {
              "source": {
                "type": "MongoDbV2Source",
                "query": "@concat('db.', item().name, '.stats()')"
              }
            }
          },
          {
            "name": "Upsert-to-Snowflake-Registry",
            "type": "Copy",
            "dependsOn": [{"activity": "Get-Collection-Stats", "dependencyConditions": ["Succeeded"]}],
            "typeProperties": {
              "source": {
                "type": "RestSource",
                "additionalColumns": [
                  {"name": "database_name", "value": "@pipeline().parameters.database_name"},
                  {"name": "collection_name", "value": "@item().name"},
                  {"name": "document_count", "value": "@activity('Get-Collection-Stats').output.firstRow.count"},
                  {"name": "discovery_timestamp", "value": "@utcnow()"}
                ]
              },
              "sink": {
                "type": "SnowflakeSink",
                "preCopyScript": "MERGE INTO mongodb_collection_registry AS target USING (VALUES ('@{pipeline().parameters.database_name}', '@{item().name}', @{activity('Get-Collection-Stats').output.firstRow.count}, CURRENT_TIMESTAMP())) AS source(database_name, collection_name, document_count, updated_at) ON target.database_name = source.database_name AND target.collection_name = source.collection_name WHEN MATCHED THEN UPDATE SET document_count = source.document_count, updated_at = source.updated_at WHEN NOT MATCHED THEN INSERT VALUES (source.database_name, source.collection_name, source.document_count, 'ACTIVE', CURRENT_TIMESTAMP(), source.updated_at);"
              }
            }
          }
        ]
      }
    }
  ]
}
```

### 2. Change Data Capture with Azure Functions

#### MongoDB Change Stream Function
```python
# change_stream_function.py
import azure.functions as func
import pymongo
import json
import logging
from azure.storage.filedatalake import DataLakeServiceClient
from datetime import datetime
import os

def main(timer: func.TimerTrigger) -> None:
    """Process change streams for all active collections"""
    
    # Get active collections from environment or Azure Key Vault
    active_collections = get_active_collections()
    
    mongo_client = pymongo.MongoClient(os.environ['MONGODB_CONNECTION_STRING'])
    adls_client = DataLakeServiceClient.from_connection_string(
        os.environ['ADLS_CONNECTION_STRING']
    )
    
    for db_name, collection_name in active_collections:
        process_collection_changes(mongo_client, adls_client, db_name, collection_name)

def process_collection_changes(mongo_client, adls_client, db_name, collection_name):
    """Process changes for a single collection"""
    
    collection = mongo_client[db_name][collection_name]
    
    # Get last processed timestamp (stored in Azure Table Storage or Snowflake)
    last_processed = get_last_processed_timestamp(db_name, collection_name)
    
    # Create resume token filter
    pipeline = [
        {'$match': {
            'operationType': {'$in': ['insert', 'update', 'delete', 'replace']},
            'clusterTime': {'$gt': last_processed} if last_processed else {}
        }}
    ]
    
    changes_batch = []
    batch_size = 1000
    
    try:
        # Use change stream with time limit
        with collection.watch(pipeline, full_document='updateLookup', max_await_time_ms=30000) as stream:
            
            for change in stream:
                if len(changes_batch) >= batch_size:
                    write_batch_to_adls(adls_client, changes_batch, db_name, collection_name)
                    changes_batch = []
                
                # Process change document
                processed_change = {
                    'operation_type': change['operationType'],
                    'database_name': db_name,
                    'collection_name': collection_name,
                    'timestamp': change['clusterTime'].as_datetime().isoformat(),
                    'document_id': str(change.get('documentKey', {}).get('_id', '')),
                    'full_document': change.get('fullDocument'),
                    'update_description': change.get('updateDescription'),
                    'processing_timestamp': datetime.utcnow().isoformat()
                }
                
                changes_batch.append(processed_change)
            
            # Write remaining changes
            if changes_batch:
                write_batch_to_adls(adls_client, changes_batch, db_name, collection_name)
                
    except Exception as e:
        logging.error(f"Error processing changes for {db_name}.{collection_name}: {e}")

def write_batch_to_adls(adls_client, changes_batch, db_name, collection_name):
    """Write batch of changes to ADLS Gen2"""
    
    now = datetime.utcnow()
    file_path = (f"raw/mongodb/{db_name}/{collection_name}/"
                f"year={now.year}/month={now.month:02d}/day={now.day:02d}/"
                f"batch_{now.timestamp()}.json")
    
    # Write as JSONL format for efficient Snowflake loading
    jsonl_content = '\n'.join([json.dumps(change, default=str) for change in changes_batch])
    
    try:
        file_system_client = adls_client.get_file_system_client("datalake")
        file_client = file_system_client.get_file_client(file_path)
        file_client.upload_data(jsonl_content, overwrite=True)
        
        logging.info(f"Written {len(changes_batch)} changes to {file_path}")
        
    except Exception as e:
        logging.error(f"Error writing to ADLS: {e}")
```

### 3. Optional: Real-time CDC with Azure Functions (Only if needed)

#### Minimal Change Stream Function (Only for Critical Collections)
```python
# Optional: Real-time CDC for critical collections only
import azure.functions as func
import pymongo
from azure.eventhub import EventHubProducerClient, EventData
import json
import os

def main(timer: func.TimerTrigger) -> None:
    """Lightweight change stream processor for critical collections only"""
    
    # Only process collections marked as 'REALTIME' in registry
    critical_collections = [
        ('prod_db', 'orders'),
        ('prod_db', 'payments'),
        ('prod_db', 'user_sessions')
    ]
    
    mongo_client = pymongo.MongoClient(os.environ['MONGODB_CONNECTION_STRING'])
    event_hub_client = EventHubProducerClient.from_connection_string(
        os.environ['EVENT_HUB_CONNECTION_STRING']
    )
    
    for db_name, collection_name in critical_collections:
        try:
            collection = mongo_client[db_name][collection_name]
            
            # Simple change stream for last 5 minutes
            pipeline = [{'$match': {'operationType': {'$in': ['insert', 'update', 'delete']}}}]
            
            with collection.watch(pipeline, full_document='updateLookup', max_await_time_ms=5000) as stream:
                changes = []
                for change in stream:
                    if len(changes) >= 100:  # Small batches
                        break
                        
                    changes.append({
                        'database': db_name,
                        'collection': collection_name,
                        'operation': change['operationType'],
                        'document_id': str(change.get('documentKey', {}).get('_id')),
                        'document': change.get('fullDocument'),
                        'timestamp': change['clusterTime'].as_datetime().isoformat()
                    })
                
                # Send to Event Hub to trigger ADF
                if changes:
                    event_data = EventData(json.dumps(changes))
                    event_hub_client.send_batch([event_data])
                    
        except Exception as e:
            print(f"Error processing {db_name}.{collection_name}: {e}")
```

### 4. Snowflake Native Processing

#### Direct JSON Processing in Snowflake
```sql
-- Create staging table for raw JSON
CREATE TABLE IF NOT EXISTS mongodb_raw_staging (
    file_name STRING,
    raw_data VARIANT,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Create file format for JSON loading
CREATE OR REPLACE FILE FORMAT json_format
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = FALSE
    COMMENT = 'JSON format for MongoDB data';

-- Load data directly from ADLS Gen2
COPY INTO mongodb_raw_staging (file_name, raw_data)
FROM (
    SELECT 
        METADATA$FILENAME,
        $1
    FROM @adls_mongodb_stage/raw/mongodb/
)
FILE_FORMAT = json_format
PATTERN = '.*\.json'
ON_ERROR = CONTINUE;

-- Process the raw data into structured tables
CREATE OR REPLACE PROCEDURE sp_process_mongodb_raw_data()
RETURNS STRING
LANGUAGE SQL
AS $$
BEGIN
    -- Dynamic processing based on database and collection
    LET cursor_sql := 'SELECT DISTINCT 
                        raw_data:database_name::STRING as db_name,
                        raw_data:collection_name::STRING as coll_name
                      FROM mongodb_raw_staging 
                      WHERE load_timestamp >= DATEADD(hour, -1, CURRENT_TIMESTAMP())';
    
    LET cursor_result CURSOR FOR IDENTIFIER(:cursor_sql);
    
    FOR record IN cursor_result DO
        LET table_name := LOWER(record.db_name) || '_' || LOWER(record.coll_name);
        
        -- Create target table if not exists
        EXECUTE IMMEDIATE 'CREATE TABLE IF NOT EXISTS ' || :table_name || ' (
            _id STRING PRIMARY KEY,
            document_data VARIANT,
            operation_type STRING,
            source_timestamp TIMESTAMP,
            etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            is_current BOOLEAN DEFAULT TRUE
        ) CLUSTER BY (_id)';
        
        -- Process the changes
        EXECUTE IMMEDIATE '
            MERGE INTO ' || :table_name || ' AS target
            USING (
                SELECT 
                    raw_data:document_id::STRING as _id,
                    raw_data:full_document as document_data,
                    raw_data:operation_type::STRING as operation_type,
                    raw_data:timestamp::TIMESTAMP as source_timestamp
                FROM mongodb_raw_staging 
                WHERE raw_data:database_name = ''' || record.db_name || '''
                AND raw_data:collection_name = ''' || record.coll_name || '''
                AND load_timestamp >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
            ) AS source
            ON target._id = source._id
            WHEN MATCHED THEN UPDATE SET
                document_data = source.document_data,
                operation_type = source.operation_type,
                source_timestamp = source.source_timestamp,
                etl_timestamp = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT VALUES (
                source._id, source.document_data, source.operation_type, 
                source.source_timestamp, CURRENT_TIMESTAMP(), TRUE
            )';
            
        -- Handle deletes
        EXECUTE IMMEDIATE '
            UPDATE ' || :table_name || '
            SET is_current = FALSE, 
                etl_timestamp = CURRENT_TIMESTAMP()
            WHERE _id IN (
                SELECT raw_data:document_id::STRING
                FROM mongodb_raw_staging 
                WHERE raw_data:database_name = ''' || record.db_name || '''
                AND raw_data:collection_name = ''' || record.coll_name || '''
                AND raw_data:operation_type = ''delete''
                AND load_timestamp >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
            )';
    END FOR;
    
    -- Clean up processed staging data
    DELETE FROM mongodb_raw_staging 
    WHERE load_timestamp < DATEADD(hour, -1, CURRENT_TIMESTAMP());
    
    RETURN 'Processing completed';
END;
$$;
```

### 5. Analytics Views with Native Snowflake

#### Automatic View Generation
```sql
-- Create analytics views using Snowflake's JSON functions
CREATE OR REPLACE PROCEDURE sp_create_analytics_view(
    table_name STRING
)
RETURNS STRING
LANGUAGE JAVASCRIPT
AS $$
    // Sample the data to understand structure
    var sample_sql = `
        SELECT document_data
        FROM ${TABLE_NAME}
        WHERE is_current = TRUE
        SAMPLE (100 ROWS)
    `;
    
    var stmt = snowflake.createStatement({sqlText: sample_sql});
    var result = stmt.execute();
    
    var common_fields = {};
    var row_count = 0;
    
    // Analyze document structure
    while (result.next() && row_count < 100) {
        var doc = JSON.parse(result.getColumnValue(1));
        analyzeFields(doc, "", common_fields);
        row_count++;
    }
    
    // Generate view SQL
    var field_selects = ['_id', 'source_timestamp', 'etl_timestamp'];
    
    for (var field in common_fields) {
        if (common_fields[field] > row_count * 0.1) { // Field appears in >10% of docs
            var clean_name = field.replace(/[^a-zA-Z0-9_]/g, '_');
            field_selects.push(`document_data:${field} as ${clean_name}`);
        }
    }
    
    var view_sql = `
        CREATE OR REPLACE VIEW ${TABLE_NAME}_analytics AS
        SELECT ${field_selects.join(',\n               ')}
        FROM ${TABLE_NAME}
        WHERE is_current = TRUE
    `;
    
    var create_stmt = snowflake.createStatement({sqlText: view_sql});
    create_stmt.execute();
    
    return `Analytics view created for ${TABLE_NAME}`;
    
    function analyzeFields(obj, prefix, fields) {
        for (var key in obj) {
            var fullKey = prefix ? prefix + '.' + key : key;
            fields[fullKey] = (fields[fullKey] || 0) + 1;
            
            if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                analyzeFields(obj[key], fullKey, fields);
            }
        }
    }
$$;
```

## Cost Comparison

### Original (with Databricks):
- **Databricks Cluster:** $300-800/month
- **Azure Functions:** $20/month  
- **ADF:** $50/month
- **ADLS Gen2:** $30/month
- **Snowflake:** $200/month
- **Total:** $600-1,100/month

### Streamlined (no Databricks):
- **Azure Functions:** $20/month
- **ADF:** $50/month  
- **ADLS Gen2:** $30/month
- **Snowflake:** $200/month
- **Total:** $300/month

## Benefits of Simplified Approach:

1. **60-70% Cost Reduction:** Eliminates expensive Databricks clusters
2. **Faster Processing:** No cluster startup time (2-5 minutes saved per job)
3. **Native Integration:** Direct MongoDB → ADF → Snowflake flow
4. **Lower Complexity:** Fewer moving parts, easier to maintain
5. **Auto-scaling:** Functions scale automatically with workload
6. **Better Error Handling:** Native ADF retry and monitoring

This streamlined pipeline achieves the same functionality without the Spark overhead, making it much more cost-effective for your MongoDB to Snowflake migration needs.



```json
{
  "name": "MongoDB-to-Snowflake-Direct-Pipeline",
  "activities": [
    {
      "name": "Get-New-Files",
      "type": "GetMetadata",
      "typeProperties": {
        "dataset": {
          "referenceName": "ADLS_MongoDB_Files"
        },
        "fieldList": ["childItems"],
        "storeSettings": {
          "type": "AzureBlobFSReadSettings",
          "recursive": true,
          "modifiedDatetimeStart": "@addHours(utcnow(), -1)",
          "modifiedDatetimeEnd": "@utcnow()"
        }
      }
    },
    {
      "name": "Process-New-Files",
      "type": "ForEach",
      "dependsOn": [{"activity": "Get-New-Files", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "items": "@activity('Get-New-Files').output.childItems",
        "isSequential": false,
        "batchCount": 10,
        "activities": [
          {
            "name": "Copy-to-Snowflake",
            "type": "Copy",
            "typeProperties": {
              "source": {
                "type": "JsonSource",
                "storeSettings": {
                  "type": "AzureBlobFSReadSettings"
                },
                "formatSettings": {
                  "type": "JsonReadSettings"
                }
              },
              "sink": {
                "type": "SnowflakeSink",
                "importSettings": {
                  "type": "SnowflakeImportCopyCommand",
                  "copyOptions": {
                    "FILE_FORMAT": "(TYPE = 'JSON', STRIP_OUTER_ARRAY = FALSE)"
                  }
                }
              }
            }
          }
        ]
      }
    }
  ],
  "triggers": [
    {
      "name": "HourlyProcessing",
      "type": "ScheduleTrigger",
      "typeProperties": {
        "recurrence": {
          "frequency": "Hour",
          "interval": 1
        }
      }
    }
  ]
}
```
