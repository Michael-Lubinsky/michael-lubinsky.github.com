# MONGO SNOW CLAUDE

## Architecture Overview

```
MongoDB → Azure Data Factory → Azure Data Lake Gen2 → Snowflake → Analytics Layer
    ↓              ↓                    ↓              ↓
Change Streams → Event Hub → Functions → Staging → Transformation → Star Schema
```

## 1. Data Ingestion Layer

### Azure Data Factory (ADF) Pipeline Design

**Components:**
- **MongoDB Linked Service**: Connect to MongoDB with connection pooling
- **Snowflake Linked Service**: Native Snowflake connector
- **Azure Data Lake Gen2**: Staging area for large datasets
- **Azure Event Hub**: Real-time change capture
- **Azure Functions**: Lightweight transformations

### Pipeline Types:

#### A. Full Load Pipeline (Initial & Periodic)
```json
{
  "name": "MongoDB-Full-Load",
  "activities": [
    {
      "name": "Get-Collection-List",
      "type": "Lookup",
      "source": "MongoDB",
      "query": "db.runCommand('listCollections')"
    },
    {
      "name": "For-Each-Collection",
      "type": "ForEach",
      "items": "@activity('Get-Collection-List').output",
      "activities": [
        {
          "name": "Copy-Collection-to-ADLS",
          "type": "Copy",
          "source": {
            "type": "MongoDbV2Source",
            "batchSize": 10000
          },
          "sink": {
            "type": "ParquetSink",
            "path": "raw/mongodb/@{item().name}/@{utcnow('yyyy/MM/dd')}"
          }
        }
      ]
    }
  ]
}
```

#### B. Incremental Load Pipeline (CDC)
- Use MongoDB Change Streams via Azure Event Hub
- Azure Functions trigger on document changes
- Capture: inserts, updates, deletes with timestamps

## 2. Data Lake Storage Strategy

### Azure Data Lake Gen2 Structure:
```
/datalake
  /raw
    /mongodb
      /collection_name
        /year=2024/month=01/day=15
          - partition by date for efficient querying
  /staging
    /flattened
      /collection_name_flattened
  /processed
    /snowflake_ready
      /fact_tables
      /dimension_tables
```

## 3. Data Transformation Layer

### Schema Design Philosophy for Analytics

#### MongoDB Document → Snowflake Table Transformation:

**1. Flatten Nested JSON Strategy:**
```sql
-- Original MongoDB Document
{
  "_id": "507f1f77bcf86cd799439011",
  "user": {
    "name": "John Doe",
    "address": {
      "street": "123 Main St",
      "city": "Seattle",
      "coordinates": [47.6062, -122.3321]
    }
  },
  "orders": [
    {"id": "ord1", "amount": 100, "items": ["item1", "item2"]},
    {"id": "ord2", "amount": 200, "items": ["item3"]}
  ],
  "metadata": {
    "created_at": "2024-01-15T10:30:00Z",
    "tags": ["premium", "active"]
  }
}

-- Transformed to Snowflake Tables:

-- Main Entity Table (users)
CREATE TABLE users (
    id STRING PRIMARY KEY,
    name STRING,
    address_street STRING,
    address_city STRING,
    address_lat FLOAT,
    address_lng FLOAT,
    created_at TIMESTAMP,
    tags ARRAY,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Normalized Related Entity (orders)
CREATE TABLE user_orders (
    user_id STRING,
    order_id STRING,
    amount DECIMAL(10,2),
    order_sequence INT,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (user_id, order_id)
);

-- Junction Table for Many-to-Many (order_items)
CREATE TABLE order_items (
    user_id STRING,
    order_id STRING,
    item_id STRING,
    item_sequence INT,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### Transformation Rules:

#### 1. **Primitive Fields**: Direct mapping
```sql
-- MongoDB: {"name": "John", "age": 30}
-- Snowflake: name STRING, age INT
```

#### 2. **Nested Objects**: Flatten with underscore notation
```sql
-- MongoDB: {"address": {"city": "Seattle", "zip": "98101"}}
-- Snowflake: address_city STRING, address_zip STRING
```

#### 3. **Arrays of Primitives**: Use Snowflake ARRAY type
```sql
-- MongoDB: {"tags": ["premium", "active"]}
-- Snowflake: tags ARRAY
```

#### 4. **Arrays of Objects**: Separate table with foreign key
```sql
-- MongoDB: {"orders": [{"id": "1", "amount": 100}]}
-- Snowflake: Separate orders table with user_id foreign key
```

#### 5. **Dynamic/Unknown Fields**: Store as VARIANT
```sql
-- MongoDB: {"custom_fields": {"field1": "value1", "field2": 123}}
-- Snowflake: custom_fields VARIANT
```

## 4. Azure Functions for Real-time Processing

### Change Stream Processor Function:
```python
import azure.functions as func
import snowflake.connector
import json

def main(event: func.EventHubEvent):
    # Parse MongoDB change event
    change_doc = json.loads(event.get_body().decode('utf-8'))
    
    operation_type = change_doc['operationType']  # insert, update, delete
    collection_name = change_doc['ns']['coll']
    
    if operation_type == 'insert':
        process_insert(change_doc, collection_name)
    elif operation_type == 'update':
        process_update(change_doc, collection_name)
    elif operation_type == 'delete':
        process_delete(change_doc, collection_name)

def process_insert(change_doc, collection_name):
    flattened_doc = flatten_document(change_doc['fullDocument'])
    upsert_to_snowflake(flattened_doc, collection_name)
```

## 5. Snowflake Schema Design for Analytics

### Star Schema Approach:

#### Fact Tables (Transaction Data):
```sql
-- High-volume, frequently updated collections
CREATE TABLE fact_transactions (
    transaction_id STRING PRIMARY KEY,
    user_id STRING,
    product_id STRING,
    merchant_id STRING,
    amount DECIMAL(12,2),
    transaction_date DATE,
    transaction_timestamp TIMESTAMP,
    -- Dimensions as foreign keys
    date_key INT,
    user_key INT,
    product_key INT,
    etl_batch_id STRING,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
) 
CLUSTER BY (transaction_date, user_id);
```

#### Dimension Tables (Reference Data):
```sql
-- Slowly changing dimensions
CREATE TABLE dim_users (
    user_key INT AUTOINCREMENT PRIMARY KEY,
    user_id STRING UNIQUE,
    user_name STRING,
    user_email STRING,
    user_segment STRING,
    address_city STRING,
    address_country STRING,
    -- SCD Type 2 fields
    effective_date TIMESTAMP,
    expiry_date TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (user_id);
```

### Clustering Strategy:
- **Fact Tables**: Cluster by date + high-cardinality dimension
- **Dimension Tables**: Cluster by business key
- **Large Tables**: Multi-column clustering

## 6. Efficient Table Joins in Snowflake

### Join Optimization Strategies:

#### 1. **Clustering Keys for Co-location**:
```sql
-- Cluster both tables on join keys
ALTER TABLE fact_orders CLUSTER BY (customer_id, order_date);
ALTER TABLE dim_customers CLUSTER BY (customer_id);
```

#### 2. **Materialized Views for Complex Joins**:
```sql
CREATE MATERIALIZED VIEW mv_customer_order_summary
CLUSTER BY (customer_id, order_month) AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.customer_segment,
    DATE_TRUNC('month', o.order_date) as order_month,
    COUNT(*) as order_count,
    SUM(o.order_amount) as total_amount
FROM dim_customers c
JOIN fact_orders o ON c.customer_id = o.customer_id
WHERE c.is_current = TRUE
GROUP BY 1,2,3,4;
```

#### 3. **Query Optimization Patterns**:
```sql
-- Use explicit join conditions
-- Push down filters early
-- Use appropriate join types

SELECT /*+ USE_CACHED_RESULT(FALSE) */
    c.customer_segment,
    p.product_category,
    SUM(f.amount) as revenue
FROM fact_transactions f
JOIN dim_customers c ON f.customer_id = c.customer_id
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.transaction_date >= '2024-01-01'
    AND c.is_current = TRUE
    AND c.customer_segment IN ('Premium', 'Enterprise')
GROUP BY 1,2
ORDER BY 3 DESC;
```

## 7. Pipeline Orchestration & Monitoring

### Azure Data Factory Schedule:
```json
{
  "triggers": [
    {
      "name": "DailyFullLoad",
      "type": "ScheduleTrigger",
      "recurrence": {
        "frequency": "Day",
        "interval": 1,
        "startTime": "2024-01-01T02:00:00Z"
      }
    },
    {
      "name": "HourlyIncremental",
      "type": "ScheduleTrigger", 
      "recurrence": {
        "frequency": "Hour",
        "interval": 1
      }
    }
  ]
}
```

### Monitoring & Alerting:
- **Azure Monitor**: Pipeline execution metrics
- **Snowflake Query History**: Performance monitoring
- **Data Quality Checks**: Row counts, schema validation
- **Cost Monitoring**: Snowflake credits and Azure costs

## 8. Performance Optimizations

### MongoDB Side:
- **Indexes**: Ensure indexes on frequently queried fields
- **Read Preferences**: Use secondary replicas for ETL
- **Connection Pooling**: Optimize connection management

### Azure Data Factory:
- **Parallel Activities**: Process multiple collections simultaneously
- **Data Integration Units**: Scale compute for large transfers
- **Incremental Loading**: Use change streams for real-time updates

### Snowflake Side:
- **Warehouse Sizing**: Auto-suspend/resume for cost optimization
- **Multi-cluster Warehouses**: Scale for concurrent workloads
- **Result Caching**: Enable for repeated analytical queries
- **Micro-partitions**: Leverage automatic partitioning

## 9. Data Governance & Quality

### Schema Evolution:
```sql
-- Handle new fields dynamically
CREATE OR REPLACE PROCEDURE handle_schema_evolution()
RETURNS STRING
LANGUAGE JAVASCRIPT
AS $$
  // Detect new fields in staging
  // Alter target tables
  // Update transformation logic
$$;
```

### Data Quality Framework:
- **Validation Rules**: Check data types, nulls, ranges
- **Reconciliation**: Compare row counts between source and target
- **Data Lineage**: Track data flow from MongoDB to Snowflake
- **Audit Logging**: Maintain ETL execution history

This pipeline provides a robust, scalable solution for moving MongoDB data to Snowflake while optimizing for analytical workloads through proper schema design and efficient joining strategies.





########
# Enhanced MongoDB to Snowflake Pipeline for Dynamic Collections
############
## Architecture Overview

```
MongoDB Collections → Azure Databricks (CDC) → ADLS Gen2 → Snowflake → Analytics Tables
        ↓                      ↓                ↓          ↓
   Change Streams      Collection Discovery   Staging    Transformation
```

## Core Pipeline Components

### 1. Dynamic Collection Discovery & Monitoring

#### Collection Registry in Snowflake
```sql
-- Track all MongoDB collections and their processing status
CREATE TABLE mongodb_collection_registry (
    database_name STRING,
    collection_name STRING,
    first_discovered TIMESTAMP,
    last_processed TIMESTAMP,
    processing_status STRING, -- 'ACTIVE', 'PAUSED', 'ERROR'
    schema_version STRING,
    record_count BIGINT,
    last_change_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (database_name, collection_name)
);

-- Track schema evolution
CREATE TABLE collection_schema_history (
    database_name STRING,
    collection_name STRING,
    schema_hash STRING,
    schema_json VARIANT,
    discovered_at TIMESTAMP,
    field_count INT,
    PRIMARY KEY (database_name, collection_name, schema_hash)
);
```

#### Azure Databricks Discovery Notebook
```python
# discovery_notebook.py
from pyspark.sql import SparkSession
from pymongo import MongoClient
import json
from datetime import datetime

class MongoCollectionDiscovery:
    def __init__(self, mongo_connection_string, snowflake_options):
        self.mongo_client = MongoClient(mongo_connection_string)
        self.snowflake_options = snowflake_options
        
    def discover_collections(self):
        """Discover all collections across all databases"""
        discovered_collections = []
        
        for db_name in self.mongo_client.list_database_names():
            if db_name not in ['admin', 'config', 'local']:  # Skip system DBs
                db = self.mongo_client[db_name]
                for collection_name in db.list_collection_names():
                    collection_info = {
                        'database_name': db_name,
                        'collection_name': collection_name,
                        'record_count': db[collection_name].count_documents({}),
                        'last_change_timestamp': self.get_latest_timestamp(db[collection_name]),
                        'schema_sample': self.sample_schema(db[collection_name])
                    }
                    discovered_collections.append(collection_info)
        
        return discovered_collections
    
    def sample_schema(self, collection, sample_size=1000):
        """Sample documents to infer schema structure"""
        pipeline = [{"$sample": {"size": sample_size}}]
        sample_docs = list(collection.aggregate(pipeline))
        
        # Analyze schema structure
        schema_fields = set()
        for doc in sample_docs:
            schema_fields.update(self.extract_field_paths(doc))
        
        return {
            'field_paths': list(schema_fields),
            'sample_count': len(sample_docs),
            'schema_hash': hash(str(sorted(schema_fields)))
        }
    
    def extract_field_paths(self, doc, prefix=""):
        """Recursively extract all field paths from a document"""
        paths = []
        for key, value in doc.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.append(current_path)
            
            if isinstance(value, dict):
                paths.extend(self.extract_field_paths(value, current_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                paths.extend(self.extract_field_paths(value[0], f"{current_path}[]"))
        
        return paths

# Execute discovery and update registry
discovery = MongoCollectionDiscovery(mongo_conn_string, snowflake_options)
collections = discovery.discover_collections()

# Update Snowflake registry
spark.sql(f"""
MERGE INTO mongodb_collection_registry AS target
USING (VALUES {','.join([f"('{c['database_name']}', '{c['collection_name']}', CURRENT_TIMESTAMP(), NULL, 'DISCOVERED', '{c['schema_sample']['schema_hash']}', {c['record_count']}, '{c['last_change_timestamp']}')" for c in collections])}) AS source(database_name, collection_name, first_discovered, last_processed, processing_status, schema_version, record_count, last_change_timestamp)
ON target.database_name = source.database_name AND target.collection_name = source.collection_name
WHEN MATCHED THEN UPDATE SET 
    record_count = source.record_count,
    last_change_timestamp = source.last_change_timestamp,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT VALUES (
    source.database_name, source.collection_name, source.first_discovered, 
    source.last_processed, source.processing_status, source.schema_version, 
    source.record_count, source.last_change_timestamp, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
);
""")
```

### 2. Change Data Capture (CDC) Pipeline

#### Multi-Collection Change Stream Processor
```python
# cdc_processor.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from azure.storage.filedatalake import DataLakeServiceClient
import json
from datetime import datetime
import hashlib

class MongoChangeStreamProcessor:
    def __init__(self, mongo_connection_string, adls_connection_string):
        self.mongo_client = AsyncIOMotorClient(mongo_connection_string)
        self.adls_client = DataLakeServiceClient.from_connection_string(adls_connection_string)
        self.active_streams = {}
        
    async def start_collection_stream(self, database_name, collection_name):
        """Start change stream for a specific collection"""
        collection = self.mongo_client[database_name][collection_name]
        
        # Configure change stream options
        pipeline = [
            {'$match': {
                'operationType': {'$in': ['insert', 'update', 'delete', 'replace']}
            }}
        ]
        
        options = {
            'full_document': 'updateLookup',  # Get full document for updates
            'max_await_time_ms': 1000
        }
        
        stream_key = f"{database_name}.{collection_name}"
        
        try:
            async with collection.watch(pipeline, **options) as stream:
                self.active_streams[stream_key] = stream
                print(f"Started change stream for {stream_key}")
                
                async for change in stream:
                    await self.process_change_event(change, database_name, collection_name)
                    
        except Exception as e:
            print(f"Error in change stream for {stream_key}: {e}")
            # Implement retry logic
            
    async def process_change_event(self, change_event, database_name, collection_name):
        """Process individual change events"""
        operation_type = change_event['operationType']
        timestamp = change_event['clusterTime']
        
        # Prepare the change document
        processed_change = {
            'operation_type': operation_type,
            'database_name': database_name,
            'collection_name': collection_name,
            'timestamp': timestamp.as_datetime().isoformat(),
            'document_id': str(change_event.get('documentKey', {}).get('_id')),
            'full_document': change_event.get('fullDocument'),
            'update_description': change_event.get('updateDescription'),
            'processing_timestamp': datetime.utcnow().isoformat()
        }
        
        # Write to ADLS Gen2
        await self.write_to_adls(processed_change, database_name, collection_name)
        
    async def write_to_adls(self, change_doc, database_name, collection_name):
        """Write change document to ADLS Gen2 in organized structure"""
        now = datetime.utcnow()
        
        # Organize by database/collection/date/hour for efficient processing
        file_path = (f"raw/mongodb/{database_name}/{collection_name}/"
                    f"year={now.year}/month={now.month:02d}/day={now.day:02d}/"
                    f"hour={now.hour:02d}/{now.timestamp()}.json")
        
        file_system_client = self.adls_client.get_file_system_client("datalake")
        file_client = file_system_client.get_file_client(file_path)
        
        try:
            await file_client.upload_data(
                json.dumps(change_doc, default=str),
                overwrite=True
            )
        except Exception as e:
            print(f"Error writing to ADLS: {e}")
            # Implement retry/dead letter queue logic
            
    async def start_multi_collection_processing(self):
        """Start change streams for all active collections"""
        # Get active collections from registry
        active_collections = self.get_active_collections_from_snowflake()
        
        tasks = []
        for db_name, collection_name in active_collections:
            task = asyncio.create_task(
                self.start_collection_stream(db_name, collection_name)
            )
            tasks.append(task)
            
        # Run all change streams concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

# Start the CDC processor
processor = MongoChangeStreamProcessor(mongo_conn_string, adls_conn_string)
asyncio.run(processor.start_multi_collection_processing())
```

### 3. Azure Data Factory Orchestration

#### Master Pipeline Configuration
```json
{
  "name": "MongoDB-to-Snowflake-Master-Pipeline",
  "parameters": {
    "processing_window_hours": {
      "type": "int",
      "defaultValue": 1
    }
  },
  "activities": [
    {
      "name": "Discovery-Phase",
      "type": "DatabricksNotebook",
      "dependsOn": [],
      "policy": {
        "timeout": "0:10:00",
        "retry": 3
      },
      "typeProperties": {
        "notebookPath": "/notebooks/discovery_notebook",
        "baseParameters": {
          "execution_timestamp": "@utcnow()"
        }
      }
    },
    {
      "name": "Get-Active-Collections",
      "type": "Lookup",
      "dependsOn": [{"activity": "Discovery-Phase", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "source": {
          "type": "SnowflakeSource",
          "query": "SELECT database_name, collection_name FROM mongodb_collection_registry WHERE processing_status = 'ACTIVE'"
        },
        "firstRowOnly": false
      }
    },
    {
      "name": "Process-Collections",
      "type": "ForEach",
      "dependsOn": [{"activity": "Get-Active-Collections", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "items": "@activity('Get-Active-Collections').output.value",
        "isSequential": false,
        "batchCount": 5,
        "activities": [
          {
            "name": "Process-Collection-Changes",
            "type": "ExecutePipeline",
            "typeProperties": {
              "pipeline": {
                "referenceName": "Process-Single-Collection-Pipeline"
              },
              "parameters": {
                "database_name": "@item().database_name",
                "collection_name": "@item().collection_name",
                "processing_window_hours": "@pipeline().parameters.processing_window_hours"
              }
            }
          }
        ]
      }
    },
    {
      "name": "Snowflake-Post-Processing",
      "type": "SqlServerStoredProcedure",
      "dependsOn": [{"activity": "Process-Collections", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "storedProcedureName": "sp_process_mongodb_changes"
      }
    }
  ],
  "triggers": [
    {
      "name": "HourlyTrigger",
      "type": "ScheduleTrigger",
      "typeProperties": {
        "recurrence": {
          "frequency": "Hour",
          "interval": 1,
          "startTime": "2024-01-01T00:00:00Z"
        }
      }
    }
  ]
}
```

#### Single Collection Processing Pipeline
```json
{
  "name": "Process-Single-Collection-Pipeline",
  "parameters": {
    "database_name": {"type": "string"},
    "collection_name": {"type": "string"},
    "processing_window_hours": {"type": "int", "defaultValue": 1}
  },
  "activities": [
    {
      "name": "Copy-Changes-to-Snowflake",
      "type": "Copy",
      "typeProperties": {
        "source": {
          "type": "JsonSource",
          "storeSettings": {
            "type": "AzureBlobFSReadSettings",
            "recursive": true,
            "wildcardFolderPath": "raw/mongodb/@{pipeline().parameters.database_name}/@{pipeline().parameters.collection_name}",
            "wildcardFileName": "*.json",
            "modifiedDatetimeStart": "@addHours(utcnow(), mul(-1, pipeline().parameters.processing_window_hours))",
            "modifiedDatetimeEnd": "@utcnow()"
          }
        },
        "sink": {
          "type": "SnowflakeSink",
          "preCopyScript": "CREATE TABLE IF NOT EXISTS staging_@{pipeline().parameters.database_name}_@{pipeline().parameters.collection_name} (change_data VARIANT, load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP())",
          "importSettings": {
            "type": "SnowflakeImportCopyCommand"
          }
        },
        "enableStaging": true,
        "stagingSettings": {
          "linkedServiceName": "AzureDataLakeStorageGen2",
          "path": "staging/snowflake"
        }
      }
    },
    {
      "name": "Process-Changes-in-Snowflake",
      "type": "SqlServerStoredProcedure",
      "dependsOn": [{"activity": "Copy-Changes-to-Snowflake", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "storedProcedureName": "sp_process_collection_changes",
        "storedProcedureParameters": {
          "database_name": "@pipeline().parameters.database_name",
          "collection_name": "@pipeline().parameters.collection_name"
        }
      }
    }
  ]
}
```

### 4. Snowflake Schema Design & Processing

#### Dynamic Table Creation
```sql
-- Stored procedure to create tables dynamically based on schema discovery
CREATE OR REPLACE PROCEDURE sp_create_collection_table(
    database_name STRING,
    collection_name STRING,
    schema_json VARIANT
)
RETURNS STRING
LANGUAGE JAVASCRIPT
AS $$
    var table_name = DATABASE_NAME.toLowerCase() + "_" + COLLECTION_NAME.toLowerCase();
    var staging_table = "staging_" + DATABASE_NAME.toLowerCase() + "_" + COLLECTION_NAME.toLowerCase();
    
    // Create main table with VARIANT column and common fields
    var create_main_sql = `
        CREATE TABLE IF NOT EXISTS ${table_name} (
            _id STRING PRIMARY KEY,
            document_data VARIANT,
            operation_type STRING,
            source_timestamp TIMESTAMP,
            etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            is_current BOOLEAN DEFAULT TRUE,
            version_number INT DEFAULT 1
        )
        CLUSTER BY (_id, source_timestamp);
    `;
    
    // Create staging table
    var create_staging_sql = `
        CREATE TABLE IF NOT EXISTS ${staging_table} (
            change_data VARIANT,
            load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        );
    `;
    
    // Execute table creation
    var stmt1 = snowflake.createStatement({sqlText: create_main_sql});
    var stmt2 = snowflake.createStatement({sqlText: create_staging_sql});
    
    stmt1.execute();
    stmt2.execute();
    
    return `Tables created: ${table_name}, ${staging_table}`;
$$;

-- Process changes from staging to main tables
CREATE OR REPLACE PROCEDURE sp_process_collection_changes(
    database_name STRING,
    collection_name STRING
)
RETURNS STRING
LANGUAGE SQL
AS $$
DECLARE
    table_name STRING := LOWER(database_name) || '_' || LOWER(collection_name);
    staging_table STRING := 'staging_' || LOWER(database_name) || '_' || LOWER(collection_name);
    processed_count INT := 0;
BEGIN
    -- Process inserts and updates
    EXECUTE IMMEDIATE $$
        MERGE INTO $$ || table_name || $$ AS target
        USING (
            SELECT 
                change_data:document_id::STRING as _id,
                change_data:full_document as document_data,
                change_data:operation_type::STRING as operation_type,
                change_data:timestamp::TIMESTAMP as source_timestamp,
                CURRENT_TIMESTAMP() as etl_timestamp,
                ROW_NUMBER() OVER (PARTITION BY change_data:document_id ORDER BY change_data:timestamp DESC) as rn
            FROM $$ || staging_table || $$
            WHERE change_data:operation_type IN ('insert', 'update', 'replace')
        ) AS source
        ON target._id = source._id
        WHEN MATCHED AND source.rn = 1 THEN UPDATE SET
            document_data = source.document_data,
            operation_type = source.operation_type,
            source_timestamp = source.source_timestamp,
            etl_timestamp = source.etl_timestamp,
            version_number = target.version_number + 1
        WHEN NOT MATCHED AND source.rn = 1 THEN INSERT (
            _id, document_data, operation_type, source_timestamp, etl_timestamp, is_current, version_number
        ) VALUES (
            source._id, source.document_data, source.operation_type, 
            source.source_timestamp, source.etl_timestamp, TRUE, 1
        );
    $$;
    
    -- Process deletes
    EXECUTE IMMEDIATE $$
        UPDATE $$ || table_name || $$
        SET is_current = FALSE, etl_timestamp = CURRENT_TIMESTAMP()
        WHERE _id IN (
            SELECT change_data:document_id::STRING
            FROM $$ || staging_table || $$
            WHERE change_data:operation_type = 'delete'
        );
    $$;
    
    -- Clean up staging table
    EXECUTE IMMEDIATE 'DELETE FROM ' || staging_table;
    
    -- Update collection registry
    UPDATE mongodb_collection_registry 
    SET last_processed = CURRENT_TIMESTAMP(),
        updated_at = CURRENT_TIMESTAMP()
    WHERE database_name = :database_name 
    AND collection_name = :collection_name;
    
    RETURN 'Processing completed for ' || table_name;
END;
$$;
```

#### Analytics-Optimized Views
```sql
-- Create flattened views for common query patterns
CREATE OR REPLACE PROCEDURE sp_create_analytics_views(
    database_name STRING,
    collection_name STRING
)
RETURNS STRING
LANGUAGE JAVASCRIPT
AS $$
    var table_name = DATABASE_NAME.toLowerCase() + "_" + COLLECTION_NAME.toLowerCase();
    var view_name = table_name + "_analytics";
    
    // Analyze document structure to create appropriate view
    var analysis_sql = `
        SELECT DISTINCT 
            f.key as field_path,
            TYPEOF(f.value) as field_type,
            COUNT(*) as frequency
        FROM ${table_name},
        LATERAL FLATTEN(document_data, RECURSIVE => TRUE) f
        WHERE is_current = TRUE
        GROUP BY f.key, TYPEOF(f.value)
        ORDER BY frequency DESC
        LIMIT 50;
    `;
    
    var stmt = snowflake.createStatement({sqlText: analysis_sql});
    var result = stmt.execute();
    
    var select_fields = [];
    while (result.next()) {
        var field_path = result.getColumnValue(1);
        var field_type = result.getColumnValue(2);
        
        // Clean field name for SQL compatibility
        var clean_name = field_path.replace(/[^a-zA-Z0-9_]/g, '_');
        
        if (field_type === 'STRING') {
            select_fields.push(`document_data:${field_path}::STRING as ${clean_name}`);
        } else if (field_type === 'INTEGER') {
            select_fields.push(`document_data:${field_path}::INT as ${clean_name}`);
        } else if (field_type === 'DECIMAL') {
            select_fields.push(`document_data:${field_path}::DECIMAL as ${clean_name}`);
        } else if (field_type === 'BOOLEAN') {
            select_fields.push(`document_data:${field_path}::BOOLEAN as ${clean_name}`);
        } else if (field_type === 'TIMESTAMP_NTZ') {
            select_fields.push(`document_data:${field_path}::TIMESTAMP as ${clean_name}`);
        }
    }
    
    // Create the analytics view
    var create_view_sql = `
        CREATE OR REPLACE VIEW ${view_name} AS
        SELECT 
            _id,
            ${select_fields.join(',\n            ')},
            source_timestamp,
            etl_timestamp
        FROM ${table_name}
        WHERE is_current = TRUE;
    `;
    
    var create_stmt = snowflake.createStatement({sqlText: create_view_sql});
    create_stmt.execute();
    
    return `Analytics view created: ${view_name}`;
$$;
```

### 5. Monitoring & Operations

#### Pipeline Health Dashboard
```sql
-- Collection processing metrics
CREATE OR REPLACE VIEW v_pipeline_health AS
SELECT 
    r.database_name,
    r.collection_name,
    r.processing_status,
    r.record_count,
    r.last_processed,
    DATEDIFF('hour', r.last_processed, CURRENT_TIMESTAMP()) as hours_since_last_update,
    CASE 
        WHEN DATEDIFF('hour', r.last_processed, CURRENT_TIMESTAMP()) > 2 THEN 'STALE'
        WHEN r.processing_status = 'ERROR' THEN 'ERROR'
        ELSE 'HEALTHY'
    END as health_status,
    
    -- Get latest processing metrics
    m.total_documents_processed,
    m.avg_processing_time_minutes,
    m.error_count
FROM mongodb_collection_registry r
LEFT JOIN (
    SELECT 
        database_name,
        collection_name,
        COUNT(*) as total_documents_processed,
        AVG(DATEDIFF('minute', source_timestamp, etl_timestamp)) as avg_processing_time_minutes,
        SUM(CASE WHEN operation_type = 'error' THEN 1 ELSE 0 END) as error_count
    FROM information_schema.tables t,
    LATERAL (
        SELECT database_name, collection_name, operation_type, source_timestamp, etl_timestamp
        FROM IDENTIFIER(t.table_name)
        WHERE etl_timestamp >= DATEADD('day', -1, CURRENT_TIMESTAMP())
    ) 
    WHERE t.table_name LIKE '%_analytics'
    GROUP BY database_name, collection_name
) m ON r.database_name = m.database_name AND r.collection_name = m.collection_name;

-- Alerting queries
SELECT * FROM v_pipeline_health WHERE health_status IN ('STALE', 'ERROR');
```

### 6. Performance Optimizations

#### Parallel Processing Configuration
```python
# Optimize Databricks cluster for MongoDB workloads
databricks_config = {
    "cluster_name": "mongodb-etl-cluster",
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "Standard_D8s_v3",  # Memory optimized for JSON processing
    "num_workers": 4,
    "autoscale": {
        "min_workers": 2,
        "max_workers": 8
    },
    "spark_conf": {
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
        "spark.mongodb.input.partitioner": "MongoSamplePartitioner",
        "spark.mongodb.input.partitionerOptions.partitionSizeMB": "64"
    }
}

# Snowflake warehouse sizing strategy
warehouse_config = {
    "etl_warehouse": {
        "size": "LARGE",
        "auto_suspend": 60,  # seconds
        "auto_resume": True,
        "initially_suspended": False
    },
    "analytics_warehouse": {
        "size": "MEDIUM", 
        "auto_suspend": 300,
        "auto_resume": True,
        "multi_cluster": {
            "min_clusters": 1,
            "max_clusters": 3,
            "scaling_policy": "STANDARD"
        }
    }
}
```

This enhanced pipeline design provides:

1. **Automatic Discovery**: Continuously monitors for new collections and schema changes
2. **Efficient CDC**: Uses MongoDB Change Streams for real-time data capture
3. **Scalable Processing**: Handles multiple collections in parallel with configurable batch sizes
4. **Schema Evolution**: Automatically adapts to changing document structures
5. **Analytics Optimization**: Creates flattened views optimized for common query patterns
6. **Comprehensive Monitoring**: Tracks pipeline health and performance metrics
7. **Cost Optimization**: Uses auto-scaling and intelligent resource management

The pipeline can handle your dynamic environment where new collections are frequently created and existing ones are updated, providing efficient and automated data movement from MongoDB to Snowflake.

# Pipeline without Apache Spark

# Streamlined MongoDB to Snowflake Pipeline (No Spark)

## Simplified Architecture

```
MongoDB Collections → Azure Functions/Logic Apps → ADLS Gen2 → Snowflake → Analytics Tables
        ↓                      ↓                    ↓          ↓
   Change Streams         Direct Processing      Staging    Native Loading
```

## Why No Spark/Databricks?

**Cost Issues with Spark:**
- Additional compute layer ($200-500+ per month for clusters)
- Complex cluster management and tuning
- Over-engineering for JSON processing
- Longer startup times (2-5 minutes per job)

**Simpler Alternatives:**
- Azure Functions: Pay-per-execution ($0.20 per million executions)
- MongoDB native connectors in ADF
- Snowflake's native JSON processing capabilities

## Core Pipeline Components

### 1. Collection Discovery with Azure Functions

#### Function App for MongoDB Discovery
```python
# discovery_function.py
import azure.functions as func
import pymongo
import json
import logging
from azure.storage.filedatalake import DataLakeServiceClient
import snowflake.connector

def main(timer: func.TimerTrigger) -> None:
    """Runs every hour to discover new collections"""
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient(os.environ['MONGODB_CONNECTION_STRING'])
    
    # Snowflake connection
    snowflake_conn = snowflake.connector.connect(
        user=os.environ['SNOWFLAKE_USER'],
        password=os.environ['SNOWFLAKE_PASSWORD'],
        account=os.environ['SNOWFLAKE_ACCOUNT'],
        warehouse=os.environ['SNOWFLAKE_WAREHOUSE'],
        database=os.environ['SNOWFLAKE_DATABASE'],
        schema=os.environ['SNOWFLAKE_SCHEMA']
    )
    
    discovered_collections = []
    
    # Discover all collections
    for db_name in mongo_client.list_database_names():
        if db_name not in ['admin', 'config', 'local']:
            db = mongo_client[db_name]
            for collection_name in db.list_collection_names():
                # Get basic stats
                stats = db.command("collStats", collection_name)
                
                collection_info = {
                    'database_name': db_name,
                    'collection_name': collection_name,
                    'document_count': stats.get('count', 0),
                    'size_bytes': stats.get('size', 0),
                    'avg_obj_size': stats.get('avgObjSize', 0)
                }
                discovered_collections.append(collection_info)
    
    # Update Snowflake registry
    cursor = snowflake_conn.cursor()
    
    for collection in discovered_collections:
        cursor.execute("""
            MERGE INTO mongodb_collection_registry AS target
            USING (SELECT %s as database_name, %s as collection_name, %s as document_count) AS source
            ON target.database_name = source.database_name 
            AND target.collection_name = source.collection_name
            WHEN MATCHED THEN UPDATE SET 
                document_count = source.document_count,
                updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT 
                (database_name, collection_name, document_count, processing_status, created_at, updated_at)
            VALUES 
                (source.database_name, source.collection_name, source.document_count, 'ACTIVE', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """, (collection['database_name'], collection['collection_name'], collection['document_count']))
    
    snowflake_conn.commit()
    cursor.close()
    snowflake_conn.close()
    
    logging.info(f"Discovered {len(discovered_collections)} collections")
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

### 3. Azure Data Factory - Simplified Pipeline

#### Master Pipeline (No Databricks)
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



