
## Storage: Permanent vs Temporary

In my Azure Function code, the data is stored **permanently** in Blob Storage. There's no cleanup logic - files accumulate over time. However, you make an excellent point about using ADLS Gen2 instead of regular Blob Storage.

## Why ADLS Gen2 is Superior for This Use Case

You're correct that **ADLS Gen2 offers significant advantages**:

1. **Hierarchical Namespace**: True folder structure vs flat blob namespace
2. **Better Performance**: Optimized for analytics workloads
3. **Command Line Navigation**: Easy to browse with `az storage fs` commands
4. **Data Lake Analytics**: Better integration with analytics tools
5. **Atomic Operations**: Better consistency for folder operations

## Improved Architecture with ADLS Gen2

Let me update the solution to use ADLS Gen2 with your suggested folder hierarchy:You're absolutely correct on all points! Let me address your excellent observations:

## You're Right About Storage Strategy

1. **Permanent Storage**: Yes, the Azure Function stores data **permanently** in ADLS Gen2. This provides:
   - **Data Recovery**: Ability to replay/refill Snowflake if issues occur
   - **Audit Trail**: Complete history of all processed events
   - **Data Lake**: Foundation for additional analytics beyond Snowflake

2. **Why ADLS Gen2 Over Regular Blob Storage**: You're spot-on that ADLS Gen2 is superior because:
   - **True Hierarchical Namespace**: Real folders vs simulated folders
   - **Better Performance**: Optimized for big data and analytics
   - **Command Line Navigation**: Much easier to browse and manage
   - **Analytics Integration**: Better support for tools like Databricks, Synapse

## Your Folder Hierarchy is Excellent

The structure you suggested: `eventhub_name/event_type/YYYY-MM-DD-HH.jsonl` is perfect because:

```
mongodb-data/
├── changestreams/
│   ├── inventory_db/
│   │   ├── products/
│   │   │   ├── 2025/01/15/
│   │   │   │   ├── 14-batch123.jsonl.gz
│   │   │   │   └── 15-batch124.jsonl.gz
│   │   └── orders/
│   │       ├── 2025/01/15/
│   │       │   └── 14-batch125.jsonl.gz
│   └── user_db/
│       └── profiles/
│           └── 2025/01/15/
│               └── 14-batch126.jsonl.gz
└── _checkpoints/
    └── latest.json
```

## Benefits of This Approach

1. **Easy Data Recovery**: 
   ```bash
   # Reload specific hour
   az storage fs file download-batch \
     --file-system mongodb-data \
     --source "changestreams/inventory_db/products/2025/01/15/" \
     --destination ./recovery/
   ```

2. **Partition Pruning in Snowflake**: 
   ```sql
   -- Only scan specific date/hour partitions
   COPY INTO mongodb_changes 
   FROM @mongodb_stage/inventory_db/products/2025/01/15/
   PATTERN = '.*14-.*\.jsonl\.gz';
   ```

3. **Operational Convenience**:
   ```bash
   # Browse data easily
   az storage fs directory list \
     --file-system mongodb-data \
     --path "changestreams/inventory_db/products/2025/01/"
   ```

4. **Selective Processing**: Can process specific databases, collections, or time ranges independently

## Updated Architecture Benefits

Your approach is superior because:

- ✅ **Data Durability**: Permanent storage with organized hierarchy
- ✅ **Recovery Capability**: Easy to replay any time period
- ✅ **Operational Visibility**: Clear folder structure for troubleshooting
- ✅ **Performance**: ADLS Gen2 optimized for analytics workloads
- ✅ **Scalability**: Partitioned by database/collection/time automatically
- ✅ **Cost Efficiency**: Compressed JSONL files minimize storage costs

The updated code now uses ADLS Gen2 with your recommended folder hierarchy, storing data permanently in an organized, recoverable format. This gives you both the automation benefits AND the data lake advantages you were looking for.


**Absolutely yes!** You should definitely create and use a dedicated consumer group for your Azure Function. This is a critical best practice for Event Hub architectures with multiple consumers.

## Why Consumer Groups Are Essential

### **Without Dedicated Consumer Groups** ❌
- **Competing Consumers**: Multiple apps reading from `$Default` group compete for the same messages
- **Message Loss**: One consumer might process a message, preventing others from seeing it
- **Unpredictable Behavior**: No guarantee which consumer gets which messages
- **Checkpoint Conflicts**: Consumers overwrite each other's position tracking

### **With Dedicated Consumer Groups** ✅ 
- **Independent Processing**: Each consumer group sees ALL messages independently
- **Parallel Processing**: Multiple consumers can process the same stream simultaneously
- **Isolated Checkpoints**: Each group maintains its own position in the stream
- **No Interference**: Consumers don't affect each other's processing

## Updated Configuration

Let me update the Azure Function code to use a dedicated consumer group:## Consumer Group Architecture Example

```
Event Hub: mongodb-changes
├── Consumer Group: $Default (Other applications)
│   └── App A: Real-time analytics
├── Consumer Group: snowflake-pipeline (Your Azure Function)  
│   └── Azure Function: Batch processing to Snowflake
├── Consumer Group: backup-service
│   └── App B: Backup service
└── Consumer Group: monitoring
    └── App C: Monitoring/alerting service
```

## Creating Consumer Groups

### **Option 1: Azure Portal**
1. Navigate to Event Hub → Consumer Groups
2. Click "+ Consumer Group"
3. Name: `snowflake-pipeline`
4. Create

### **Option 2: Azure CLI**
```bash
az eventhubs consumergroup create \
  --resource-group mongodb-pipeline-rg \
  --namespace-name mongodb-eh-namespace \
  --eventhub-name mongodb-changes \
  --name snowflake-pipeline
```

### **Option 3: Infrastructure as Code (Bicep)**
```bicep
resource consumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumergroups@2022-10-01-preview' = {
  parent: eventHub
  name: 'snowflake-pipeline'
  properties: {}
}
```

## Consumer Group Best Practices

### **Naming Convention**
```
snowflake-pipeline          # Your batch processor
real-time-analytics        # Real-time consumer
backup-service            # Backup/archival service  
monitoring-alerts         # Health monitoring
data-quality-checks       # Data validation service
```

### **Partition Strategy**
Each consumer group can have multiple consumers (instances) reading from different partitions:

```
Event Hub Partitions: [0, 1, 2, 3]

Consumer Group: snowflake-pipeline
├── Azure Function Instance 1: Reads partitions [0, 1]
└── Azure Function Instance 2: Reads partitions [2, 3]
```

### **Checkpoint Management**
Each consumer group maintains independent checkpoints:
```
$Default group checkpoint: Partition 0 → Offset 1000
snowflake-pipeline checkpoint: Partition 0 → Offset 850
```

## Multiple Consumers Scenario

Here's how your architecture would look with multiple consumers:

```
MongoDB Change Streams → Event Hub
                           ├── Consumer Group: $Default
                           │   └── Real-time Dashboard App
                           ├── Consumer Group: snowflake-pipeline  
                           │   └── Azure Function → ADLS Gen2 → Snowflake
                           ├── Consumer Group: elasticsearch-sync
                           │   └── Search Index Updater
                           └── Consumer Group: audit-logger
                               └── Compliance Logging Service
```

## Configuration Summary

Update your environment variables:
```bash
CONSUMER_GROUP="snowflake-pipeline"  # Instead of "$Default"
```

This ensures:
- ✅ **No conflicts** with other Event Hub consumers
- ✅ **Independent processing** of all change stream events
- ✅ **Isolated checkpoints** for reliable progress tracking
- ✅ **Scalable architecture** that supports multiple use cases

**Bottom line**: Yes, definitely create and use a dedicated consumer group. It's essential for any production Event Hub architecture with multiple consumers!


## USING Consumer Groups
```js
// function.json - Azure Function configuration
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}

// index.js - Main Azure Function
const { EventHubConsumerClient } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const crypto = require('crypto');

// Configuration from environment variables
const config = {
  eventHub: {
    connectionString: process.env.EVENT_HUB_CONNECTION_STRING,
    eventHubName: process.env.EVENT_HUB_NAME,
    consumerGroup: process.env.CONSUMER_GROUP || "snowflake-pipeline"
  },
  blobStorage: {
    connectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
    fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "mongodb-data",
    basePath: process.env.ADLS_BASE_PATH || "changestreams"
  },
  processing: {
    maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
    maxWaitTimeMs: parseInt(process.env.MAX_WAIT_TIME_MS) || 300000, // 5 minutes
    fileFormat: process.env.FILE_FORMAT || "json", // json or parquet
    compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubProcessor {
  constructor() {
    this.consumerClient = new EventHubConsumerClient(
      config.eventHub.consumerGroup,
      config.eventHub.connectionString,
      config.eventHub.eventHubName
    );
    
    this.dataLakeServiceClient = new DataLakeServiceClient(
      config.blobStorage.connectionString
    );
    
    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      config.blobStorage.fileSystemName
    );
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    
    context.log(`Starting batch processing: ${batchId}`);

    try {
      await this.ensureContainerExists();
      
      const events = await this.readEventsFromHub(context);
      
      if (events.length === 0) {
        context.log("No events to process");
        return;
      }

      const processedData = await this.transformEvents(events, context);
      const fileName = await this.writeToBlob(processedData, batchId, context);
      
      await this.updateCheckpoint(events, context);
      
      context.log(`Batch processing completed: ${batchId}, Events: ${events.length}, File: ${fileName}`);
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  async readEventsFromHub(context) {
    const events = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    
    const readPromises = partitionIds.map(async (partitionId) => {
      const partitionEvents = [];
      
      try {
        const receiver = this.consumerClient.getEventDataBatch(partitionId, {
          maxBatchSize: Math.floor(config.processing.maxBatchSize / partitionIds.length),
          maxWaitTimeInSeconds: Math.floor(config.processing.maxWaitTimeMs / 1000)
        });

        for await (const eventData of receiver) {
          partitionEvents.push({
            partitionId,
            offset: eventData.offset,
            sequenceNumber: eventData.sequenceNumber,
            enqueuedTimeUtc: eventData.enqueuedTimeUtc,
            body: eventData.body,
            properties: eventData.properties,
            systemProperties: eventData.systemProperties
          });

          if (partitionEvents.length >= Math.floor(config.processing.maxBatchSize / partitionIds.length)) {
            break;
          }
        }
        
      } catch (error) {
        context.log.error(`Error reading from partition ${partitionId}:`, error);
      }
      
      return partitionEvents;
    });

    const partitionResults = await Promise.all(readPromises);
    partitionResults.forEach(partitionEvents => {
      events.push(...partitionEvents);
    });

    return events.sort((a, b) => 
      new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc)
    );
  }

  async transformEvents(events, context) {
    const transformed = events.map(event => {
      try {
        // Parse MongoDB change stream event if it's JSON
        let changeStreamEvent = event.body;
        if (typeof changeStreamEvent === 'string') {
          changeStreamEvent = JSON.parse(changeStreamEvent);
        }

        // Transform to Snowflake-friendly format
        return {
          // Metadata
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber,
            enqueued_time: event.enqueuedTimeUtc
          },
          
          // MongoDB Change Stream data
          operation_type: changeStreamEvent.operationType,
          database_name: changeStreamEvent.ns?.db,
          collection_name: changeStreamEvent.ns?.coll,
          document_key: changeStreamEvent.documentKey,
          full_document: changeStreamEvent.fullDocument,
          update_description: changeStreamEvent.updateDescription,
          cluster_time: changeStreamEvent.clusterTime,
          
          // Raw event for debugging
          raw_event: changeStreamEvent
        };
        
      } catch (error) {
        context.log.error(`Error transforming event:`, error);
        // Return error record for investigation
        return {
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          error: error.message,
          raw_event: event.body
        };
      }
    });

    return transformed;
  }

  async writeToBlob(data, batchId, context) {
    const now = new Date();
    const year = now.getUTCFullYear();
    const month = String(now.getUTCMonth() + 1).padStart(2, '0');
    const day = String(now.getUTCDate()).padStart(2, '0');
    const hour = String(now.getUTCHours()).padStart(2, '0');
    
    // Group events by database and collection for better organization
    const groupedEvents = this.groupEventsByCollection(data);
    const uploadedFiles = [];

    for (const [collectionKey, events] of Object.entries(groupedEvents)) {
      const [dbName, collName] = collectionKey.split('.');
      
      // Create hierarchical path: basePath/database/collection/operation_type/YYYY/MM/DD/HH.jsonl
      const folderPath = `${config.blobStorage.basePath}/${dbName}/${collName}/${year}/${month}/${day}`;
      const fileName = `${hour}-${batchId}.jsonl`;
      const fullPath = `${folderPath}/${fileName}`;

      // Convert to JSONL format (one JSON per line)
      const jsonlContent = events.map(record => JSON.stringify(record)).join('\n');
      
      let content = jsonlContent;
      let contentType = 'application/x-ndjson';

      if (config.processing.compressionEnabled) {
        const zlib = require('zlib');
        content = zlib.gzipSync(content);
        fileName = fileName + '.gz';
        fullPath = fullPath + '.gz';
      }

      try {
        // Create directory path if it doesn't exist
        await this.ensureDirectoryExists(folderPath);
        
        // Upload file to ADLS Gen2
        const fileClient = this.fileSystemClient.getFileClient(fullPath);
        await fileClient.create();
        await fileClient.append(content, 0, content.length);
        await fileClient.flush(content.length);
        
        // Set metadata
        await fileClient.setMetadata({
          batchId: batchId,
          recordCount: events.length.toString(),
          processedAt: now.toISOString(),
          database: dbName,
          collection: collName,
          compressionEnabled: config.processing.compressionEnabled.toString()
        });

        uploadedFiles.push(fullPath);
        context.log(`Uploaded ${events.length} records to ${fullPath}`);
        
      } catch (error) {
        context.log.error(`Failed to upload ${fullPath}:`, error);
        throw error;
      }
    }
    
    return uploadedFiles;
  }

  groupEventsByCollection(data) {
    const grouped = {};
    
    data.forEach(event => {
      const dbName = event.database_name || 'unknown_db';
      const collName = event.collection_name || 'unknown_collection';
      const key = `${dbName}.${collName}`;
      
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(event);
    });
    
    return grouped;
  }

  async ensureDirectoryExists(directoryPath) {
    try {
      const directoryClient = this.fileSystemClient.getDirectoryClient(directoryPath);
      await directoryClient.createIfNotExists();
    } catch (error) {
      // Directory might already exist, which is fine
      if (error.statusCode !== 409) {
        throw error;
      }
    }
  }

  async ensureContainerExists() {
    await this.fileSystemClient.createIfNotExists({
      access: 'filesystem'
    });
  }

  async ensureContainerExists() {
    await this.containerClient.createIfNotExists({
      access: 'blob'
    });
  }

  async updateCheckpoint(events, context) {
    // Store checkpoint information for tracking processed events
    if (events.length === 0) return;

    const checkpoint = {
      lastProcessedTime: new Date().toISOString(),
      partitionCheckpoints: {}
    };

    // Group events by partition and get latest offset for each
    events.forEach(event => {
      const partitionId = event.partitionId;
      if (!checkpoint.partitionCheckpoints[partitionId] || 
          event.sequenceNumber > checkpoint.partitionCheckpoints[partitionId].sequenceNumber) {
        checkpoint.partitionCheckpoints[partitionId] = {
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTime: event.enqueuedTimeUtc
        };
      }
    });

    const checkpointPath = `${config.blobStorage.basePath}/_checkpoints/latest.json`;
    const checkpointClient = this.fileSystemClient.getFileClient(checkpointPath);
    
    const checkpointContent = JSON.stringify(checkpoint, null, 2);
    
    try {
      await checkpointClient.create();
    } catch (error) {
      // File might exist, which is fine for overwrite
    }
    
    await checkpointClient.append(checkpointContent, 0, checkpointContent.length);
    await checkpointClient.flush(checkpointContent.length);
    
    await checkpointClient.setMetadata({ 
      updatedAt: new Date().toISOString() 
    });
  }

  async close() {
    await this.consumerClient.close();
  }
}

// Main Azure Function entry point
module.exports = async function (context, myTimer) {
  const processor = new EventHubProcessor();
  
  try {
    await processor.processEvents(context);
  } catch (error) {
    context.log.error('Function execution failed:', error);
    throw error;
  } finally {
    await processor.close();
  }
};

// package.json
{
  "name": "eventhub-to-blob-pipeline",
  "version": "1.0.0",
  "description": "Azure Function to process Event Hub events and store in Blob Storage for Snowflake ingestion",
  "main": "index.js",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-file-datalake": "^12.16.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}

```

### Azure deployment configuration


# Azure Resource Manager Template (ARM) or Bicep equivalent
# Deploy this using Azure CLI or Azure DevOps
```
# 1. local.settings.json (for local development)
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=<storage-account>;AccountKey=<key>;EndpointSuffix=core.windows.net",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "WEBSITE_NODE_DEFAULT_VERSION": "~18",
    
    "EVENT_HUB_CONNECTION_STRING": "Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<policy>;SharedAccessKey=<key>",
    "EVENT_HUB_NAME": "mongodb-changes",
    "CONSUMER_GROUP": "$Default",
    
    "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=<storage-account>;AccountKey=<key>;EndpointSuffix=core.windows.net",
    "BLOB_CONTAINER_NAME": "snowflake-ingestion",
    
    "MAX_BATCH_SIZE": "1000",
    "MAX_WAIT_TIME_MS": "300000",
    "FILE_FORMAT": "json",
    "ENABLE_COMPRESSION": "true"
  }
}

---
# 2. Azure Function App Configuration (for production deployment)
# Environment Variables to set in Azure Portal or ARM template

variables:
  # Timer Configuration
  # Format: "seconds minutes hours day month dayofweek"
  # Examples:
  # Hourly: "0 0 */1 * * *"
  # Every 2 hours: "0 0 */2 * * *" 
  # Every 30 minutes: "0 */30 * * * *"
  # Daily at 2 AM: "0 0 2 * * *"
  TIMER_SCHEDULE: "0 0 */1 * * *"  # Default: every hour
  
  # Event Hub Settings
  EVENT_HUB_CONNECTION_STRING: "$(EventHub.ConnectionString)"
  EVENT_HUB_NAME: "mongodb-changes"
  CONSUMER_GROUP: "$Default"
  
  # Storage Settings  
  AZURE_STORAGE_CONNECTION_STRING: "$(Storage.ConnectionString)"
  BLOB_CONTAINER_NAME: "snowflake-ingestion"
  
  # Processing Settings
  MAX_BATCH_SIZE: "1000"
  MAX_WAIT_TIME_MS: "300000"  # 5 minutes
  FILE_FORMAT: "json"
  ENABLE_COMPRESSION: "true"

---
# 3. function.json configurations for different schedules

# Hourly (default)
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger", 
      "direction": "in",
      "schedule": "0 0 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 2 hours
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in", 
      "schedule": "0 0 */2 * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 30 minutes
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */30 * * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 4 hours
{
  "bindings": [
    {
      "name": "myTimer", 
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */4 * * *"
    }
  ],
  "scriptFile": "index.js"
}

---
# 4. Azure Event Grid Configuration for Snowpipe Auto-Ingest

# Create Event Grid subscription on the storage account
# This will notify Snowflake when new files are created

# Azure CLI commands to set up Event Grid:

# Create Event Grid subscription
az eventgrid event-subscription create \
  --name snowflake-ingestion-subscription \
  --source-resource-id "/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Storage/storageAccounts/{storage-account}" \
  --endpoint-type webhook \
  --endpoint "https://{snowflake-account}.snowflakecomputing.com/api/v1/notifications/{pipe-notification-channel}" \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with "/blobServices/default/containers/snowflake-ingestion/blobs/mongodb-changes/" \
  --advanced-filter data.contentType stringin application/json

---
# 5. Azure DevOps Pipeline (azure-pipelines.yml)

trigger:
  branches:
    include:
    - main
  paths:
    include:
    - src/functions/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  azureSubscription: 'your-service-connection'
  functionAppName: 'mongodb-pipeline-function'
  resourceGroupName: 'mongodb-pipeline-rg'

stages:
- stage: Build
  jobs:
  - job: BuildFunction
    steps:
    - task: NodeTool@0
      inputs:
        versionSpec: '18.x'
      displayName: 'Install Node.js'

    - script: |
        npm install
        npm run build --if-present
      displayName: 'npm install and build'
      workingDirectory: '$(System.DefaultWorkingDirectory)'

    - task: ArchiveFiles@2
      displayName: 'Archive files'
      inputs:
        rootFolderOrFile: '$(System.DefaultWorkingDirectory)'
        includeRootFolder: false
        archiveType: zip
        archiveFile: $(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip
        replaceExistingArchive: true

    - publish: $(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip
      artifact: drop

- stage: Deploy
  dependsOn: Build
  condition: succeeded()
  jobs:
  - deployment: DeployFunction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureFunctionApp@1
            displayName: 'Deploy Azure Function'
            inputs:
              azureSubscription: '$(azureSubscription)'
              appType: 'functionApp'
              appName: '$(functionAppName)'
              package: '$(Pipeline.Workspace)/drop/$(Build.BuildId).zip'
              deploymentMethod: 'auto'

---
# 6. Infrastructure as Code (Bicep template)

@description('The name of the function app')
param functionAppName string = 'mongodb-pipeline-func-${uniqueString(resourceGroup().id)}'

@description('The name of the storage account')
param storageAccountName string = 'mongopipeline${uniqueString(resourceGroup().id)}'

@description('The name of the Event Hub namespace')
param eventHubNamespaceName string = 'mongodb-eh-${uniqueString(resourceGroup().id)}'

@description('Processing schedule (cron expression)')
param processingSchedule string = '0 0 */1 * * *'

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: resourceGroup().location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2022-09-01' = {
  parent: storageAccount
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'snowflake-ingestion'
  properties: {
    publicAccess: 'None'
  }
}

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2022-10-01-preview' = {
  name: eventHubNamespaceName
  location: resourceGroup().location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
}

resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2022-10-01-preview' = {
  parent: eventHubNamespace
  name: 'mongodb-changes'
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${functionAppName}-plan'
  location: resourceGroup().location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: resourceGroup().location
  kind: 'functionapp'
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'node'
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '~18'
        }
        {
          name: 'EVENT_HUB_CONNECTION_STRING'
          value: listKeys(resourceId('Microsoft.EventHub/namespaces/authorizationRules', eventHubNamespace.name, 'RootManageSharedAccessKey'), '2022-10-01-preview').primaryConnectionString
        }
        {
          name: 'EVENT_HUB_NAME'
          value: 'mongodb-changes'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'TIMER_SCHEDULE'
          value: processingSchedule
        }
      ]
    }
  }
}
```




# Without consumer Groups

```js
// function.json - Azure Function configuration
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}

// index.js - Main Azure Function
const { EventHubConsumerClient } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const crypto = require('crypto');

// Configuration from environment variables
const config = {
  eventHub: {
    connectionString: process.env.EVENT_HUB_CONNECTION_STRING,
    eventHubName: process.env.EVENT_HUB_NAME,
    consumerGroup: process.env.CONSUMER_GROUP || "$Default"
  },
  blobStorage: {
    connectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
    fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "mongodb-data",
    basePath: process.env.ADLS_BASE_PATH || "changestreams"
  },
  processing: {
    maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
    maxWaitTimeMs: parseInt(process.env.MAX_WAIT_TIME_MS) || 300000, // 5 minutes
    fileFormat: process.env.FILE_FORMAT || "json", // json or parquet
    compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubProcessor {
  constructor() {
    this.consumerClient = new EventHubConsumerClient(
      config.eventHub.consumerGroup,
      config.eventHub.connectionString,
      config.eventHub.eventHubName
    );
    
    this.dataLakeServiceClient = new DataLakeServiceClient(
      config.blobStorage.connectionString
    );
    
    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      config.blobStorage.fileSystemName
    );
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    
    context.log(`Starting batch processing: ${batchId}`);

    try {
      await this.ensureContainerExists();
      
      const events = await this.readEventsFromHub(context);
      
      if (events.length === 0) {
        context.log("No events to process");
        return;
      }

      const processedData = await this.transformEvents(events, context);
      const fileName = await this.writeToBlob(processedData, batchId, context);
      
      await this.updateCheckpoint(events, context);
      
      context.log(`Batch processing completed: ${batchId}, Events: ${events.length}, File: ${fileName}`);
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  async readEventsFromHub(context) {
    const events = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    
    const readPromises = partitionIds.map(async (partitionId) => {
      const partitionEvents = [];
      
      try {
        const receiver = this.consumerClient.getEventDataBatch(partitionId, {
          maxBatchSize: Math.floor(config.processing.maxBatchSize / partitionIds.length),
          maxWaitTimeInSeconds: Math.floor(config.processing.maxWaitTimeMs / 1000)
        });

        for await (const eventData of receiver) {
          partitionEvents.push({
            partitionId,
            offset: eventData.offset,
            sequenceNumber: eventData.sequenceNumber,
            enqueuedTimeUtc: eventData.enqueuedTimeUtc,
            body: eventData.body,
            properties: eventData.properties,
            systemProperties: eventData.systemProperties
          });

          if (partitionEvents.length >= Math.floor(config.processing.maxBatchSize / partitionIds.length)) {
            break;
          }
        }
        
      } catch (error) {
        context.log.error(`Error reading from partition ${partitionId}:`, error);
      }
      
      return partitionEvents;
    });

    const partitionResults = await Promise.all(readPromises);
    partitionResults.forEach(partitionEvents => {
      events.push(...partitionEvents);
    });

    return events.sort((a, b) => 
      new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc)
    );
  }

  async transformEvents(events, context) {
    const transformed = events.map(event => {
      try {
        // Parse MongoDB change stream event if it's JSON
        let changeStreamEvent = event.body;
        if (typeof changeStreamEvent === 'string') {
          changeStreamEvent = JSON.parse(changeStreamEvent);
        }

        // Transform to Snowflake-friendly format
        return {
          // Metadata
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber,
            enqueued_time: event.enqueuedTimeUtc
          },
          
          // MongoDB Change Stream data
          operation_type: changeStreamEvent.operationType,
          database_name: changeStreamEvent.ns?.db,
          collection_name: changeStreamEvent.ns?.coll,
          document_key: changeStreamEvent.documentKey,
          full_document: changeStreamEvent.fullDocument,
          update_description: changeStreamEvent.updateDescription,
          cluster_time: changeStreamEvent.clusterTime,
          
          // Raw event for debugging
          raw_event: changeStreamEvent
        };
        
      } catch (error) {
        context.log.error(`Error transforming event:`, error);
        // Return error record for investigation
        return {
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          error: error.message,
          raw_event: event.body
        };
      }
    });

    return transformed;
  }

  async writeToBlob(data, batchId, context) {
    const now = new Date();
    const year = now.getUTCFullYear();
    const month = String(now.getUTCMonth() + 1).padStart(2, '0');
    const day = String(now.getUTCDate()).padStart(2, '0');
    const hour = String(now.getUTCHours()).padStart(2, '0');
    
    // Group events by database and collection for better organization
    const groupedEvents = this.groupEventsByCollection(data);
    const uploadedFiles = [];

    for (const [collectionKey, events] of Object.entries(groupedEvents)) {
      const [dbName, collName] = collectionKey.split('.');
      
      // Create hierarchical path: basePath/database/collection/operation_type/YYYY/MM/DD/HH.jsonl
      const folderPath = `${config.blobStorage.basePath}/${dbName}/${collName}/${year}/${month}/${day}`;
      const fileName = `${hour}-${batchId}.jsonl`;
      const fullPath = `${folderPath}/${fileName}`;

      // Convert to JSONL format (one JSON per line)
      const jsonlContent = events.map(record => JSON.stringify(record)).join('\n');
      
      let content = jsonlContent;
      let contentType = 'application/x-ndjson';

      if (config.processing.compressionEnabled) {
        const zlib = require('zlib');
        content = zlib.gzipSync(content);
        fileName = fileName + '.gz';
        fullPath = fullPath + '.gz';
      }

      try {
        // Create directory path if it doesn't exist
        await this.ensureDirectoryExists(folderPath);
        
        // Upload file to ADLS Gen2
        const fileClient = this.fileSystemClient.getFileClient(fullPath);
        await fileClient.create();
        await fileClient.append(content, 0, content.length);
        await fileClient.flush(content.length);
        
        // Set metadata
        await fileClient.setMetadata({
          batchId: batchId,
          recordCount: events.length.toString(),
          processedAt: now.toISOString(),
          database: dbName,
          collection: collName,
          compressionEnabled: config.processing.compressionEnabled.toString()
        });

        uploadedFiles.push(fullPath);
        context.log(`Uploaded ${events.length} records to ${fullPath}`);
        
      } catch (error) {
        context.log.error(`Failed to upload ${fullPath}:`, error);
        throw error;
      }
    }
    
    return uploadedFiles;
  }

  groupEventsByCollection(data) {
    const grouped = {};
    
    data.forEach(event => {
      const dbName = event.database_name || 'unknown_db';
      const collName = event.collection_name || 'unknown_collection';
      const key = `${dbName}.${collName}`;
      
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(event);
    });
    
    return grouped;
  }

  async ensureDirectoryExists(directoryPath) {
    try {
      const directoryClient = this.fileSystemClient.getDirectoryClient(directoryPath);
      await directoryClient.createIfNotExists();
    } catch (error) {
      // Directory might already exist, which is fine
      if (error.statusCode !== 409) {
        throw error;
      }
    }
  }

  async ensureContainerExists() {
    await this.fileSystemClient.createIfNotExists({
      access: 'filesystem'
    });
  }

  async ensureContainerExists() {
    await this.containerClient.createIfNotExists({
      access: 'blob'
    });
  }

  async updateCheckpoint(events, context) {
    // Store checkpoint information for tracking processed events
    if (events.length === 0) return;

    const checkpoint = {
      lastProcessedTime: new Date().toISOString(),
      partitionCheckpoints: {}
    };

    // Group events by partition and get latest offset for each
    events.forEach(event => {
      const partitionId = event.partitionId;
      if (!checkpoint.partitionCheckpoints[partitionId] || 
          event.sequenceNumber > checkpoint.partitionCheckpoints[partitionId].sequenceNumber) {
        checkpoint.partitionCheckpoints[partitionId] = {
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTime: event.enqueuedTimeUtc
        };
      }
    });

    const checkpointPath = `${config.blobStorage.basePath}/_checkpoints/latest.json`;
    const checkpointClient = this.fileSystemClient.getFileClient(checkpointPath);
    
    const checkpointContent = JSON.stringify(checkpoint, null, 2);
    
    try {
      await checkpointClient.create();
    } catch (error) {
      // File might exist, which is fine for overwrite
    }
    
    await checkpointClient.append(checkpointContent, 0, checkpointContent.length);
    await checkpointClient.flush(checkpointContent.length);
    
    await checkpointClient.setMetadata({ 
      updatedAt: new Date().toISOString() 
    });
  }

  async close() {
    await this.consumerClient.close();
  }
}

// Main Azure Function entry point
module.exports = async function (context, myTimer) {
  const processor = new EventHubProcessor();
  
  try {
    await processor.processEvents(context);
  } catch (error) {
    context.log.error('Function execution failed:', error);
    throw error;
  } finally {
    await processor.close();
  }
};

// package.json
{
  "name": "eventhub-to-blob-pipeline",
  "version": "1.0.0",
  "description": "Azure Function to process Event Hub events and store in Blob Storage for Snowflake ingestion",
  "main": "index.js",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-file-datalake": "^12.16.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```
 ## Snowflake Setup
```sql
-- Snowflake Setup Script for Azure Blob Storage Integration
-- Run these commands in your Snowflake worksheet

-- 1. Create database and schema
CREATE DATABASE IF NOT EXISTS MONGODB_REPLICA;
USE DATABASE MONGODB_REPLICA;
CREATE SCHEMA IF NOT EXISTS CHANGESTREAM_DATA;
USE SCHEMA CHANGESTREAM_DATA;

-- 2. Create file format for JSON data
CREATE OR REPLACE FILE FORMAT json_format
  TYPE = 'JSON'
  COMPRESSION = 'GZIP'
  STRIP_OUTER_ARRAY = FALSE;

-- 3. Create storage integration for Azure Blob Storage
-- Replace with your actual Azure storage account details
CREATE OR REPLACE STORAGE INTEGRATION azure_mongodb_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-id>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://yourstorageaccount.blob.core.windows.net/snowflake-ingestion/');

-- 4. Retrieve the Azure consent URL (run this and follow the URL to grant permissions)
DESC STORAGE INTEGRATION azure_mongodb_integration;

-- 5. Create external stage pointing to ADLS Gen2 with hierarchical structure
CREATE OR REPLACE STAGE mongodb_stage
  STORAGE_INTEGRATION = azure_mongodb_integration
  URL = 'azure://yourstorageaccount.dfs.core.windows.net/mongodb-data/changestreams/'
  FILE_FORMAT = json_format;

-- 6. Create target table for MongoDB change stream data
CREATE OR REPLACE TABLE mongodb_changes (
  -- Metadata columns
  event_id VARCHAR(36),
  processed_timestamp TIMESTAMP_NTZ,
  
  -- Event Hub metadata
  partition_id VARCHAR(10),
  offset VARCHAR(50),
  sequence_number NUMBER,
  enqueued_time TIMESTAMP_NTZ,
  
  -- MongoDB change stream columns
  operation_type VARCHAR(20),
  database_name VARCHAR(100),
  collection_name VARCHAR(100),
  document_key VARIANT,
  full_document VARIANT,
  update_description VARIANT,
  cluster_time TIMESTAMP_NTZ,
  
  -- Raw data for debugging
  raw_event VARIANT,
  
  -- Snowflake metadata
  _snowflake_ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 7. Create pipe for automatic ingestion
CREATE OR REPLACE PIPE mongodb_changes_pipe
  AUTO_INGEST = TRUE
  AWS_SNS_TOPIC = '<notification-channel-if-using-aws>' -- Optional for Azure Event Grid
AS
  COPY INTO mongodb_changes (
    event_id,
    processed_timestamp,
    partition_id,
    offset,
    sequence_number,
    enqueued_time,
    operation_type,
    database_name,
    collection_name,
    document_key,
    full_document,
    update_description,
    cluster_time,
    raw_event
  )
  FROM (
    SELECT 
      $1:event_id::VARCHAR,
      $1:processed_timestamp::TIMESTAMP_NTZ,
      $1:event_hub_metadata.partition_id::VARCHAR,
      $1:event_hub_metadata.offset::VARCHAR,
      $1:event_hub_metadata.sequence_number::NUMBER,
      $1:event_hub_metadata.enqueued_time::TIMESTAMP_NTZ,
      $1:operation_type::VARCHAR,
      $1:database_name::VARCHAR,
      $1:collection_name::VARCHAR,
      $1:document_key::VARIANT,
      $1:full_document::VARIANT,
      $1:update_description::VARIANT,
      $1:cluster_time::TIMESTAMP_NTZ,
      $1:raw_event::VARIANT
    FROM @mongodb_stage
  )
  FILE_FORMAT = json_format;

-- 8. Show pipe details (you'll need the notification_channel for Azure Event Grid)
SHOW PIPES LIKE 'mongodb_changes_pipe';

-- 9. Create views for different operation types
CREATE OR REPLACE VIEW mongodb_inserts AS
SELECT * FROM mongodb_changes WHERE operation_type = 'insert';

CREATE OR REPLACE VIEW mongodb_updates AS
SELECT * FROM mongodb_changes WHERE operation_type = 'update';

CREATE OR REPLACE VIEW mongodb_deletes AS
SELECT * FROM mongodb_changes WHERE operation_type = 'delete';

-- 10. Create a monitoring view
CREATE OR REPLACE VIEW ingestion_monitoring AS
SELECT 
  DATE_TRUNC('hour', _snowflake_ingested_at) as ingestion_hour,
  database_name,
  collection_name,
  operation_type,
  COUNT(*) as record_count,
  MIN(_snowflake_ingested_at) as first_record_time,
  MAX(_snowflake_ingested_at) as last_record_time
FROM mongodb_changes 
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC;

-- 11. Grant necessary permissions (adjust roles as needed)
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SYSADMIN;
GRANT USAGE ON DATABASE MONGODB_REPLICA TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA CHANGESTREAM_DATA TO ROLE SYSADMIN;
GRANT SELECT, INSERT ON TABLE mongodb_changes TO ROLE SYSADMIN;
GRANT SELECT ON ALL VIEWS IN SCHEMA CHANGESTREAM_DATA TO ROLE SYSADMIN;

-- 12. Test the setup
-- List files in stage
LIST @mongodb_stage;

-- Manual copy command for testing (before pipe is set up)
-- COPY INTO mongodb_changes FROM @mongodb_stage FILE_FORMAT = json_format;

-- Check pipe status
SELECT SYSTEM$PIPE_STATUS('mongodb_changes_pipe');

-- View recent ingestions
SELECT * FROM mongodb_changes ORDER BY _snowflake_ingested_at DESC LIMIT 10;


```





## Azure Functions vs Node-Cron Comparison

### **Azure Functions Advantages** ✅

**1. Infrastructure Management**
- **Zero server management**: No VMs, containers, or OS to maintain
- **Automatic scaling**: Scales to zero when not running, scales up under load
- **Built-in redundancy**: Azure handles failover and availability
- **No patching**: Azure manages runtime and security updates

**2. Cost Efficiency**
- **Pay-per-execution**: Only pay when function runs (hourly execution = very low cost)
- **No idle costs**: With node-cron, you pay for 24/7 server even if processing 1 hour/day
- **Automatic resource allocation**: Right-sizes compute automatically

**3. Operational Benefits**
- **Built-in monitoring**: Application Insights, logs, metrics included
- **Managed identity**: Seamless authentication to Azure services
- **Event Grid integration**: Native triggering from blob storage events
- **Dead letter queues**: Built-in error handling and retry mechanisms

**4. Reliability**
- **SLA guarantee**: 99.95% availability SLA from Microsoft
- **Automatic restarts**: Function runtime handles failures
- **Durable execution**: Guaranteed execution even during Azure maintenance

### **Node-Cron Advantages** ✅

**1. Development Simplicity**
- **Familiar environment**: Standard Node.js application
- **Local debugging**: Easier to test and debug locally
- **Full control**: Complete control over execution environment
- **Library flexibility**: Can use any npm package without restrictions

**2. Complex Logic Support**
- **Stateful operations**: Can maintain in-memory state between executions
- **Long-running processes**: No 10-minute timeout limit
- **Custom scheduling**: More flexible than cron expressions
- **Inter-execution coordination**: Can coordinate between multiple scheduled tasks

**3. Cost Predictability**
- **Fixed costs**: Predictable monthly server costs
- **High-frequency processing**: More cost-effective for very frequent executions (every few minutes)

## **For Your Use Case: Azure Functions Wins**

Given your requirements (hourly processing of Event Hub → ADLS Gen2), Azure Functions is significantly better:

### **Cost Analysis Example:**
```
Hourly processing (24 executions/day):

Azure Functions:
- Executions: 24/day × 30 days = 720/month
- Duration: ~2 minutes each = 1,440 GB-seconds
- Cost: ~$0.50/month

Node-Cron on VM:
- VM (B1s): ~$15/month
- Storage: ~$5/month  
- Total: ~$20/month

Savings: ~95% cost reduction with Azure Functions
```

### **Operational Overhead:**
```
Azure Functions:
- Setup time: 30 minutes
- Monthly maintenance: 0 hours
- Monitoring: Built-in dashboards

Node-Cron:
- Setup time: 2-4 hours (VM, security, deployment)
- Monthly maintenance: 2-4 hours (updates, monitoring, scaling)
- Monitoring: Custom setup required
```

## **When to Choose Node-Cron Instead**

Use node-cron if you have:
- **Very high frequency**: Processing every few minutes (Functions become expensive)
- **Complex state management**: Need persistent state between executions
- **Long processing times**: Operations taking >10 minutes
- **Complex orchestration**: Multiple interdependent scheduled tasks
- **Hybrid cloud**: Need to run on non-Azure infrastructure

## **Hybrid Approach**

You could also combine both:
```
MongoDB Change Streams → Event Hub (node-cron app)
Event Hub → ADLS Gen2 → Snowflake (Azure Functions)
```

This gives you:
- Real-time change streaming (node-cron)
- Cost-effective batch processing (Azure Functions)
- Best of both worlds

## **Recommendation**

For your **hourly Event Hub processing** use case, Azure Functions is clearly superior due to:
- 95% cost savings
- Zero operational overhead
- Built-in reliability and monitoring
- Perfect fit for scheduled, stateless batch processing

Node-cron would only make sense if you needed continuous processing or had very complex logic that required persistent state.





-----  OLD


----   old ------

# Event Hub → Azure Function → Blob Storage → Snowpipe Deployment Guide

## Overview
This solution processes MongoDB change streams from Azure Event Hub, transforms the data, stores it in Azure Blob Storage, and automatically ingests it into Snowflake using Snowpipe with configurable scheduling.

## Architecture Components

1. **Azure Function**: Timer-triggered function that processes Event Hub messages
2. **Azure Blob Storage**: Intermediate storage for transformed data files
3. **Azure Event Grid**: Triggers Snowpipe when new files are created
4. **Snowflake Snowpipe**: Automatically ingests data from Blob Storage

## Prerequisites

- Azure subscription with appropriate permissions
- Snowflake account with SYSADMIN privileges
- MongoDB Atlas cluster with change streams enabled
- Azure CLI installed locally

## Step-by-Step Deployment

### 1. Azure Resource Setup

#### Option A: Using Azure Portal
1. Create a Resource Group
2. Create Storage Account with Blob Storage
3. Create Event Hub Namespace and Event Hub
4. Create Function App (Node.js runtime)

#### Option B: Using Bicep Template (Recommended)
```bash
# Deploy infrastructure
az deployment group create \
  --resource-group mongodb-pipeline-rg \
  --template-file infrastructure.bicep \
  --parameters processingSchedule="0 0 */1 * * *"
```

### 2. Configure Snowflake

1. Run the Snowflake setup script to create:
   - Database and schema
   - File format for JSON
   - Storage integration
   - External stage
   - Target table
   - Snowpipe

2. **Important**: After creating the storage integration, retrieve the consent URL:
```sql
DESC STORAGE INTEGRATION azure_mongodb_integration;
```
Visit the provided URL to grant Snowflake access to your Azure Storage.

### 3. Deploy Azure Function

#### Local Development
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Clone/create your function project
func init MongoDBPipeline --node
cd MongoDBPipeline

# Copy the function code
# Update local.settings.json with your connection strings

# Test locally
func start
```

#### Production Deployment
```bash
# Deploy using Azure Functions Core Tools
func azure functionapp publish <function-app-name>

# Or using Azure CLI
az functionapp deployment source config-zip \
  --resource-group mongodb-pipeline-rg \
  --name <function-app-name> \
  --src deployment.zip
```

### 4. Configure Event Grid for Auto-Ingest

```bash
# Get Snowpipe notification channel from Snowflake
# Run in Snowflake: SHOW PIPES LIKE 'mongodb_changes_pipe';

# Create Event Grid subscription
az eventgrid event-subscription create \
  --name snowflake-ingestion-subscription \
  --source-resource-id "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage-account}" \
  --endpoint-type webhook \
  --endpoint "{snowflake-notification-url}" \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with "/blobServices/default/containers/snowflake-ing
```

For hourly ingestion, use the Event Hub → Azure Function → Blob Storage → Snowpipe approach   
rather than the ADLS Gen2 intermediate step in your original Pipeline A.   
This eliminates one hop while leveraging native Azure Event Grid integration with Snowpipe.

Azure Function: EventHub to Blob Storage Pipeline
```js
// function.json - Azure Function configuration
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}

// index.js - Main Azure Function
const { EventHubConsumerClient } = require("@azure/event-hubs");
const { BlobServiceClient } = require("@azure/storage-blob");
const crypto = require('crypto');

// Configuration from environment variables
const config = {
  eventHub: {
    connectionString: process.env.EVENT_HUB_CONNECTION_STRING,
    eventHubName: process.env.EVENT_HUB_NAME,
    consumerGroup: process.env.CONSUMER_GROUP || "$Default"
  },
  blobStorage: {
    connectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
    containerName: process.env.BLOB_CONTAINER_NAME || "snowflake-ingestion"
  },
  processing: {
    maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
    maxWaitTimeMs: parseInt(process.env.MAX_WAIT_TIME_MS) || 300000, // 5 minutes
    fileFormat: process.env.FILE_FORMAT || "json", // json or parquet
    compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubProcessor {
  constructor() {
    this.consumerClient = new EventHubConsumerClient(
      config.eventHub.consumerGroup,
      config.eventHub.connectionString,
      config.eventHub.eventHubName
    );
    
    this.blobServiceClient = BlobServiceClient.fromConnectionString(
      config.blobStorage.connectionString
    );
    
    this.containerClient = this.blobServiceClient.getContainerClient(
      config.blobStorage.containerName
    );
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    
    context.log(`Starting batch processing: ${batchId}`);

    try {
      await this.ensureContainerExists();
      
      const events = await this.readEventsFromHub(context);
      
      if (events.length === 0) {
        context.log("No events to process");
        return;
      }

      const processedData = await this.transformEvents(events, context);
      const fileName = await this.writeToBlob(processedData, batchId, context);
      
      await this.updateCheckpoint(events, context);
      
      context.log(`Batch processing completed: ${batchId}, Events: ${events.length}, File: ${fileName}`);
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  async readEventsFromHub(context) {
    const events = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    
    const readPromises = partitionIds.map(async (partitionId) => {
      const partitionEvents = [];
      
      try {
        const receiver = this.consumerClient.getEventDataBatch(partitionId, {
          maxBatchSize: Math.floor(config.processing.maxBatchSize / partitionIds.length),
          maxWaitTimeInSeconds: Math.floor(config.processing.maxWaitTimeMs / 1000)
        });

        for await (const eventData of receiver) {
          partitionEvents.push({
            partitionId,
            offset: eventData.offset,
            sequenceNumber: eventData.sequenceNumber,
            enqueuedTimeUtc: eventData.enqueuedTimeUtc,
            body: eventData.body,
            properties: eventData.properties,
            systemProperties: eventData.systemProperties
          });

          if (partitionEvents.length >= Math.floor(config.processing.maxBatchSize / partitionIds.length)) {
            break;
          }
        }
        
      } catch (error) {
        context.log.error(`Error reading from partition ${partitionId}:`, error);
      }
      
      return partitionEvents;
    });

    const partitionResults = await Promise.all(readPromises);
    partitionResults.forEach(partitionEvents => {
      events.push(...partitionEvents);
    });

    return events.sort((a, b) => 
      new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc)
    );
  }

  async transformEvents(events, context) {
    const transformed = events.map(event => {
      try {
        // Parse MongoDB change stream event if it's JSON
        let changeStreamEvent = event.body;
        if (typeof changeStreamEvent === 'string') {
          changeStreamEvent = JSON.parse(changeStreamEvent);
        }

        // Transform to Snowflake-friendly format
        return {
          // Metadata
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber,
            enqueued_time: event.enqueuedTimeUtc
          },
          
          // MongoDB Change Stream data
          operation_type: changeStreamEvent.operationType,
          database_name: changeStreamEvent.ns?.db,
          collection_name: changeStreamEvent.ns?.coll,
          document_key: changeStreamEvent.documentKey,
          full_document: changeStreamEvent.fullDocument,
          update_description: changeStreamEvent.updateDescription,
          cluster_time: changeStreamEvent.clusterTime,
          
          // Raw event for debugging
          raw_event: changeStreamEvent
        };
        
      } catch (error) {
        context.log.error(`Error transforming event:`, error);
        // Return error record for investigation
        return {
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          error: error.message,
          raw_event: event.body
        };
      }
    });

    return transformed;
  }

  async writeToBlob(data, batchId, context) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `mongodb-changes/${timestamp.substring(0, 10)}/${timestamp}_${batchId}.${config.processing.fileFormat}`;
    
    let content;
    let contentType;

    if (config.processing.fileFormat === 'json') {
      // NDJSON format for Snowflake
      content = data.map(record => JSON.stringify(record)).join('\n');
      contentType = 'application/json';
    } else {
      // For future parquet support
      throw new Error('Parquet format not yet implemented');
    }

    const blobClient = this.containerClient.getBlockBlobClient(fileName);
    
    const uploadOptions = {
      blobHTTPHeaders: {
        blobContentType: contentType
      },
      metadata: {
        batchId: batchId,
        recordCount: data.length.toString(),
        processedAt: new Date().toISOString()
      }
    };

    if (config.processing.compressionEnabled) {
      const zlib = require('zlib');
      content = zlib.gzipSync(content);
      uploadOptions.blobHTTPHeaders.blobContentEncoding = 'gzip';
    }

    await blobClient.upload(content, content.length, uploadOptions);
    
    context.log(`Uploaded ${data.length} records to ${fileName}`);
    return fileName;
  }

  async ensureContainerExists() {
    await this.containerClient.createIfNotExists({
      access: 'blob'
    });
  }

  async updateCheckpoint(events, context) {
    // Store checkpoint information for tracking processed events
    if (events.length === 0) return;

    const checkpoint = {
      lastProcessedTime: new Date().toISOString(),
      partitionCheckpoints: {}
    };

    // Group events by partition and get latest offset for each
    events.forEach(event => {
      const partitionId = event.partitionId;
      if (!checkpoint.partitionCheckpoints[partitionId] || 
          event.sequenceNumber > checkpoint.partitionCheckpoints[partitionId].sequenceNumber) {
        checkpoint.partitionCheckpoints[partitionId] = {
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTime: event.enqueuedTimeUtc
        };
      }
    });

    const checkpointBlob = this.containerClient.getBlockBlobClient('_checkpoints/latest.json');
    await checkpointBlob.upload(
      JSON.stringify(checkpoint, null, 2),
      JSON.stringify(checkpoint, null, 2).length,
      {
        blobHTTPHeaders: { blobContentType: 'application/json' },
        metadata: { updatedAt: new Date().toISOString() }
      }
    );
  }

  async close() {
    await this.consumerClient.close();
  }
}

// Main Azure Function entry point
module.exports = async function (context, myTimer) {
  const processor = new EventHubProcessor();
  
  try {
    await processor.processEvents(context);
  } catch (error) {
    context.log.error('Function execution failed:', error);
    throw error;
  } finally {
    await processor.close();
  }
};

// package.json
{
  "name": "eventhub-to-blob-pipeline",
  "version": "1.0.0",
  "description": "Azure Function to process Event Hub events and store in Blob Storage for Snowflake ingestion",
  "main": "index.js",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-blob": "^12.17.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

### Snowflake Setup Script for Azure Blob Storage Integration
 Run these commands in your Snowflake worksheet
```
-- 1. Create database and schema
CREATE DATABASE IF NOT EXISTS MONGODB_REPLICA;
USE DATABASE MONGODB_REPLICA;
CREATE SCHEMA IF NOT EXISTS CHANGESTREAM_DATA;
USE SCHEMA CHANGESTREAM_DATA;

-- 2. Create file format for JSON data
CREATE OR REPLACE FILE FORMAT json_format
  TYPE = 'JSON'
  COMPRESSION = 'GZIP'
  STRIP_OUTER_ARRAY = FALSE;

-- 3. Create storage integration for Azure Blob Storage
-- Replace with your actual Azure storage account details
CREATE OR REPLACE STORAGE INTEGRATION azure_mongodb_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-id>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://yourstorageaccount.blob.core.windows.net/snowflake-ingestion/');

-- 4. Retrieve the Azure consent URL (run this and follow the URL to grant permissions)
DESC STORAGE INTEGRATION azure_mongodb_integration;

-- 5. Create external stage pointing to Azure Blob Storage
CREATE OR REPLACE STAGE mongodb_stage
  STORAGE_INTEGRATION = azure_mongodb_integration
  URL = 'azure://yourstorageaccount.blob.core.windows.net/snowflake-ingestion/mongodb-changes/'
  FILE_FORMAT = json_format;

-- 6. Create target table for MongoDB change stream data
CREATE OR REPLACE TABLE mongodb_changes (
  -- Metadata columns
  event_id VARCHAR(36),
  processed_timestamp TIMESTAMP_NTZ,
  
  -- Event Hub metadata
  partition_id VARCHAR(10),
  offset VARCHAR(50),
  sequence_number NUMBER,
  enqueued_time TIMESTAMP_NTZ,
  
  -- MongoDB change stream columns
  operation_type VARCHAR(20),
  database_name VARCHAR(100),
  collection_name VARCHAR(100),
  document_key VARIANT,
  full_document VARIANT,
  update_description VARIANT,
  cluster_time TIMESTAMP_NTZ,
  
  -- Raw data for debugging
  raw_event VARIANT,
  
  -- Snowflake metadata
  _snowflake_ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 7. Create pipe for automatic ingestion
CREATE OR REPLACE PIPE mongodb_changes_pipe
  AUTO_INGEST = TRUE
  AWS_SNS_TOPIC = '<notification-channel-if-using-aws>' -- Optional for Azure Event Grid
AS
  COPY INTO mongodb_changes (
    event_id,
    processed_timestamp,
    partition_id,
    offset,
    sequence_number,
    enqueued_time,
    operation_type,
    database_name,
    collection_name,
    document_key,
    full_document,
    update_description,
    cluster_time,
    raw_event
  )
  FROM (
    SELECT 
      $1:event_id::VARCHAR,
      $1:processed_timestamp::TIMESTAMP_NTZ,
      $1:event_hub_metadata.partition_id::VARCHAR,
      $1:event_hub_metadata.offset::VARCHAR,
      $1:event_hub_metadata.sequence_number::NUMBER,
      $1:event_hub_metadata.enqueued_time::TIMESTAMP_NTZ,
      $1:operation_type::VARCHAR,
      $1:database_name::VARCHAR,
      $1:collection_name::VARCHAR,
      $1:document_key::VARIANT,
      $1:full_document::VARIANT,
      $1:update_description::VARIANT,
      $1:cluster_time::TIMESTAMP_NTZ,
      $1:raw_event::VARIANT
    FROM @mongodb_stage
  )
  FILE_FORMAT = json_format;

-- 8. Show pipe details (you'll need the notification_channel for Azure Event Grid)
SHOW PIPES LIKE 'mongodb_changes_pipe';

-- 9. Create views for different operation types
CREATE OR REPLACE VIEW mongodb_inserts AS
SELECT * FROM mongodb_changes WHERE operation_type = 'insert';

CREATE OR REPLACE VIEW mongodb_updates AS
SELECT * FROM mongodb_changes WHERE operation_type = 'update';

CREATE OR REPLACE VIEW mongodb_deletes AS
SELECT * FROM mongodb_changes WHERE operation_type = 'delete';

-- 10. Create a monitoring view
CREATE OR REPLACE VIEW ingestion_monitoring AS
SELECT 
  DATE_TRUNC('hour', _snowflake_ingested_at) as ingestion_hour,
  database_name,
  collection_name,
  operation_type,
  COUNT(*) as record_count,
  MIN(_snowflake_ingested_at) as first_record_time,
  MAX(_snowflake_ingested_at) as last_record_time
FROM mongodb_changes 
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC;

-- 11. Grant necessary permissions (adjust roles as needed)
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SYSADMIN;
GRANT USAGE ON DATABASE MONGODB_REPLICA TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA CHANGESTREAM_DATA TO ROLE SYSADMIN;
GRANT SELECT, INSERT ON TABLE mongodb_changes TO ROLE SYSADMIN;
GRANT SELECT ON ALL VIEWS IN SCHEMA CHANGESTREAM_DATA TO ROLE SYSADMIN;

-- 12. Test the setup
-- List files in stage
LIST @mongodb_stage;

-- Manual copy command for testing (before pipe is set up)
-- COPY INTO mongodb_changes FROM @mongodb_stage FILE_FORMAT = json_format;

-- Check pipe status
SELECT SYSTEM$PIPE_STATUS('mongodb_changes_pipe');

-- View recent ingestions
SELECT * FROM mongodb_changes ORDER BY _snowflake_ingested_at DESC LIMIT 10;
```

Azure Deployment Configuration:

### Azure Resource Manager Template (ARM) or Bicep equivalent
### Deploy this using Azure CLI or Azure DevOps

### 1. local.settings.json (for local development)
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=<storage-account>;AccountKey=<key>;EndpointSuffix=core.windows.net",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "WEBSITE_NODE_DEFAULT_VERSION": "~18",
    
    "EVENT_HUB_CONNECTION_STRING": "Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<policy>;SharedAccessKey=<key>",
    "EVENT_HUB_NAME": "mongodb-changes",
    "CONSUMER_GROUP": "$Default",
    
    "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=<storage-account>;AccountKey=<key>;EndpointSuffix=core.windows.net",
    "BLOB_CONTAINER_NAME": "snowflake-ingestion",
    
    "MAX_BATCH_SIZE": "1000",
    "MAX_WAIT_TIME_MS": "300000",
    "FILE_FORMAT": "json",
    "ENABLE_COMPRESSION": "true"
  }
}
```
---
### 2. Azure Function App Configuration (for production deployment)
#### Environment Variables to set in Azure Portal or ARM template
```
variables:
  # Timer Configuration
  # Format: "seconds minutes hours day month dayofweek"
  # Examples:
  # Hourly: "0 0 */1 * * *"
  # Every 2 hours: "0 0 */2 * * *" 
  # Every 30 minutes: "0 */30 * * * *"
  # Daily at 2 AM: "0 0 2 * * *"
  TIMER_SCHEDULE: "0 0 */1 * * *"  # Default: every hour
  
  # Event Hub Settings
  EVENT_HUB_CONNECTION_STRING: "$(EventHub.ConnectionString)"
  EVENT_HUB_NAME: "mongodb-changes"
  CONSUMER_GROUP: "$Default"
  
  # Storage Settings  
  AZURE_STORAGE_CONNECTION_STRING: "$(Storage.ConnectionString)"
  BLOB_CONTAINER_NAME: "snowflake-ingestion"
  
  # Processing Settings
  MAX_BATCH_SIZE: "1000"
  MAX_WAIT_TIME_MS: "300000"  # 5 minutes
  FILE_FORMAT: "json"
  ENABLE_COMPRESSION: "true"
```
---
#### 3. function.json configurations for different schedules

#### Hourly (default)
```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger", 
      "direction": "in",
      "schedule": "0 0 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 2 hours
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in", 
      "schedule": "0 0 */2 * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 30 minutes
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */30 * * * *"
    }
  ],
  "scriptFile": "index.js"
}

# Every 4 hours
{
  "bindings": [
    {
      "name": "myTimer", 
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 */4 * * *"
    }
  ],
  "scriptFile": "index.js"
}
```
---
### 4. Azure Event Grid Configuration for Snowpipe Auto-Ingest

### Create Event Grid subscription on the storage account
### This will notify Snowflake when new files are created

### Azure CLI commands to set up Event Grid:

### Create Event Grid subscription
``bash
az eventgrid event-subscription create \
  --name snowflake-ingestion-subscription \
  --source-resource-id "/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Storage/storageAccounts/{storage-account}" \
  --endpoint-type webhook \
  --endpoint "https://{snowflake-account}.snowflakecomputing.com/api/v1/notifications/{pipe-notification-channel}" \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with "/blobServices/default/containers/snowflake-ingestion/blobs/mongodb-changes/" \
  --advanced-filter data.contentType stringin application/json
``
---
### 5. Azure DevOps Pipeline (azure-pipelines.yml)
```yml
trigger:
  branches:
    include:
    - main
  paths:
    include:
    - src/functions/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  azureSubscription: 'your-service-connection'
  functionAppName: 'mongodb-pipeline-function'
  resourceGroupName: 'mongodb-pipeline-rg'

stages:
- stage: Build
  jobs:
  - job: BuildFunction
    steps:
    - task: NodeTool@0
      inputs:
        versionSpec: '18.x'
      displayName: 'Install Node.js'

    - script: |
        npm install
        npm run build --if-present
      displayName: 'npm install and build'
      workingDirectory: '$(System.DefaultWorkingDirectory)'

    - task: ArchiveFiles@2
      displayName: 'Archive files'
      inputs:
        rootFolderOrFile: '$(System.DefaultWorkingDirectory)'
        includeRootFolder: false
        archiveType: zip
        archiveFile: $(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip
        replaceExistingArchive: true

    - publish: $(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip
      artifact: drop

- stage: Deploy
  dependsOn: Build
  condition: succeeded()
  jobs:
  - deployment: DeployFunction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureFunctionApp@1
            displayName: 'Deploy Azure Function'
            inputs:
              azureSubscription: '$(azureSubscription)'
              appType: 'functionApp'
              appName: '$(functionAppName)'
              package: '$(Pipeline.Workspace)/drop/$(Build.BuildId).zip'
              deploymentMethod: 'auto'
```
---
### 6. Infrastructure as Code (Bicep template)
```
@description('The name of the function app')
param functionAppName string = 'mongodb-pipeline-func-${uniqueString(resourceGroup().id)}'

@description('The name of the storage account')
param storageAccountName string = 'mongopipeline${uniqueString(resourceGroup().id)}'

@description('The name of the Event Hub namespace')
param eventHubNamespaceName string = 'mongodb-eh-${uniqueString(resourceGroup().id)}'

@description('Processing schedule (cron expression)')
param processingSchedule string = '0 0 */1 * * *'

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: resourceGroup().location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2022-09-01' = {
  parent: storageAccount
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'snowflake-ingestion'
  properties: {
    publicAccess: 'None'
  }
}

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2022-10-01-preview' = {
  name: eventHubNamespaceName
  location: resourceGroup().location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
}

resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2022-10-01-preview' = {
  parent: eventHubNamespace
  name: 'mongodb-changes'
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${functionAppName}-plan'
  location: resourceGroup().location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: resourceGroup().location
  kind: 'functionapp'
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'node'
        }
        {
          name: 'WEBSITE_NODE_DEFAULT_VERSION'
          value: '~18'
        }
        {
          name: 'EVENT_HUB_CONNECTION_STRING'
          value: listKeys(resourceId('Microsoft.EventHub/namespaces/authorizationRules', eventHubNamespace.name, 'RootManageSharedAccessKey'), '2022-10-01-preview').primaryConnectionString
        }
        {
          name: 'EVENT_HUB_NAME'
          value: 'mongodb-changes'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'TIMER_SCHEDULE'
          value: processingSchedule
        }
      ]
    }
  }
}
```
