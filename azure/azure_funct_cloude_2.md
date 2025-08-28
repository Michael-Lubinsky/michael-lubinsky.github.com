# How to Run the EventHub Processor


You're absolutely right! The `createPartitionClient` method doesn't exist in the Azure Event Hubs SDK. I made an error in the implementation. Let me fix this by using the correct approach with the subscription-based API.Actually, let me provide you with a better approach that uses the correct Event Hubs SDK patterns. The issue is that the Azure Event Hubs SDK has different approaches for consuming events, and the `createPartitionClient` method doesn't exist.## **The Root Cause**

The error occurs because I was using a non-existent method. The Azure Event Hubs SDK for Node.js uses a **subscription-based approach**, not partition clients. Here are the correct methods:

### **Available Methods in Azure Event Hubs SDK:**

1. **`consumerClient.subscribe()`** - Subscribe to all partitions
2. **`consumerClient.subscribe(partitionId, ...)`** - Subscribe to specific partition  
3. **`consumerClient.getPartitionIds()`** - Get partition IDs
4. **`consumerClient.close()`** - Close the client

### **What I Fixed:**

1. **Removed the non-existent `createPartitionClient()` method**
2. **Used proper subscription-based approach** with `consumerClient.subscribe()`
3. **Added two reading strategies**:
   - **Primary**: Subscribe to all partitions at once (recommended)
   - **Alternative**: Sequential partition reading if needed
4. **Proper timeout handling** using `setTimeout` with Promise resolution
5. **Better error handling** for subscriber conflicts

### **Key Differences in the Corrected Version:**

```javascript
// ❌ WRONG (doesn't exist):
const partitionClient = this.consumerClient.createPartitionClient(partitionId);

// ✅ CORRECT (subscription-based):
const subscription = this.consumerClient.subscribe(partitionId, {
  processEvents: async (events, context) => { /* handle events */ },
  processError: async (err, context) => { /* handle errors */ }
});
```

### **How to Use the Corrected Version:**

```javascript
const EventHubProcessor = require('./corrected-eventhub-processor');

const mockContext = {
    log: {
        info: console.log,
        error: console.error,
        warn: console.warn
    },
    done: () => console.log('Done')
};

async function test() {
    const processor = new EventHubProcessor();
    try {
        const result = await processor.processEvents(mockContext);
        console.log('Success:', result);
    } finally {
        await processor.close();
    }
}

test().catch(console.error);
```

This corrected version uses the proper Azure Event Hubs SDK patterns and should work without the `createPartitionClient` error. The subscription approach is actually more efficient and handles the "already has subscriber" issue better.


## Prerequisites

### 1. Install Dependencies
```bash
npm install @azure/event-hubs @azure/storage-file-datalake @azure/identity
```

### 2. Set Up Azure Authentication
Choose one of these methods:

#### Option A: Azure CLI (Recommended for Local Development)
```bash
az login
```

#### Option B: Service Principal with Environment Variables
```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

#### Option C: Managed Identity (For Azure-hosted applications)
No additional setup needed when running in Azure.

### 3. Set Environment Variables
```bash
# Required
export EVENT_HUB_NAMESPACE="weavix-reporting-dev-ehns.servicebus.windows.net"
export EVENT_HUB_NAME="telemetry-stream-parallel-hub"
export CONSUMER_GROUP="telemetry"
export AZURE_STORAGE_ACCOUNT_NAME="weavixdatalakedevsa"
export ADLS_FILESYSTEM_NAME="adls"
export ADLS_BASE_PATH="adls"

# Optional
export MAX_BATCH_SIZE="1000"
export MAX_WAIT_TIME_MS="300000"
export MAX_WAIT_TIME_SECONDS="5"
export ENABLE_COMPRESSION="true"
```

## Running Options

### Option 1: Local Testing (Current Setup)

Create a test runner file:

```javascript
// test-runner.js
const EventHubProcessor = require('./improved-processor');

const mockContext = {
    log: {
        info: (message) => console.log(`INFO: ${message}`),
        error: (message, ...args) => console.error(`ERROR: ${message}`, ...args),
        warn: (message) => console.warn(`WARN: ${message}`)
    },
    done: () => {
        console.log('Function execution completed.');
    }
};

async function runTest() {
    const processor = new EventHubProcessor();
    
    try {
        const result = await processor.processEvents(mockContext);
        console.log('Processing result:', result);
    } catch (error) {
        console.error('Test failed:', error);
    } finally {
        await processor.close();
        mockContext.done();
    }
}

runTest().catch(console.error);
```

Run with:
```bash
node test-runner.js
```

### Option 2: Azure Function (Timer Trigger)

Create the Azure Function structure:

```
my-function-app/
├── host.json
├── package.json
├── EventHubProcessor/
│   ├── function.json
│   └── index.js
└── local.settings.json
```

**host.json:**
```json
{
  "version": "2.0",
  "functionTimeout": "00:10:00",
  "extensions": {
    "eventHubs": {
      "maxBatchSize": 1000
    }
  }
}
```

**EventHubProcessor/function.json:**
```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */5 * * * *",
      "runOnStartup": false
    }
  ]
}
```

**EventHubProcessor/index.js:**
```javascript
const EventHubProcessor = require('../improved-processor');

module.exports = async function (context, myTimer) {
    const processor = new EventHubProcessor();
    
    try {
        const result = await processor.processEvents(context);
        context.log.info('Processing completed:', result);
        return result;
    } catch (error) {
        context.log.error('Processing failed:', error);
        throw error;
    } finally {
        await processor.close();
    }
};
```

**local.settings.json:**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "EVENT_HUB_NAMESPACE": "weavix-reporting-dev-ehns.servicebus.windows.net",
    "EVENT_HUB_NAME": "telemetry-stream-parallel-hub",
    "CONSUMER_GROUP": "telemetry",
    "AZURE_STORAGE_ACCOUNT_NAME": "weavixdatalakedevsa",
    "ADLS_FILESYSTEM_NAME": "adls",
    "ADLS_BASE_PATH": "adls",
    "MAX_BATCH_SIZE": "1000",
    "ENABLE_COMPRESSION": "true"
  }
}
```

Run locally:
```bash
npm install -g azure-functions-core-tools@4
func start
```

### Option 3: Event Hub Trigger (Alternative)

For real-time processing, use an Event Hub trigger instead of timer:

**function.json:**
```json
{
  "bindings": [
    {
      "type": "eventHubTrigger",
      "name": "eventHubMessages",
      "direction": "in",
      "eventHubName": "telemetry-stream-parallel-hub",
      "connection": "EventHubConnectionString",
      "consumerGroup": "telemetry",
      "cardinality": "many"
    }
  ]
}
```

### Option 4: Standalone Node.js Application

Create a complete standalone app:

```javascript
// app.js
const EventHubProcessor = require('./improved-processor');

class StandaloneRunner {
    constructor(intervalMinutes = 5) {
        this.processor = new EventHubProcessor();
        this.intervalMs = intervalMinutes * 60 * 1000;
        this.running = false;
    }
    
    createMockContext() {
        return {
            log: {
                info: (message) => console.log(`[${new Date().toISOString()}] INFO: ${message}`),
                error: (message, ...args) => console.error(`[${new Date().toISOString()}] ERROR: ${message}`, ...args),
                warn: (message) => console.warn(`[${new Date().toISOString()}] WARN: ${message}`)
            },
            done: () => console.log(`[${new Date().toISOString()}] Processing cycle completed.`)
        };
    }
    
    async start() {
        this.running = true;
        console.log(`Starting EventHub processor with ${this.intervalMs/1000}s interval...`);
        
        while (this.running) {
            try {
                const context = this.createMockContext();
                const result = await this.processor.processEvents(context);
                console.log(`Processed ${result.processedEvents} events, created ${result.files.length} files`);
                
                if (this.running) {
                    await new Promise(resolve => setTimeout(resolve, this.intervalMs));
                }
            } catch (error) {
                console.error('Processing cycle failed:', error);
                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, 30000));
            }
        }
    }
    
    async stop() {
        console.log('Stopping processor...');
        this.running = false;
        await this.processor.close();
        console.log('Processor stopped.');
    }
}

// Handle graceful shutdown
const runner = new StandaloneRunner(5); // 5 minutes

process.on('SIGINT', async () => {
    await runner.stop();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    await runner.stop();
    process.exit(0);
});

runner.start().catch(console.error);
```

Run with:
```bash
node app.js
```

## Deployment Options

### Azure Function App
```bash
# Deploy to Azure
func azure functionapp publish your-function-app-name
```

### Docker Container
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .

CMD ["node", "app.js"]
```

### Azure Container Instances
```bash
# Build and run in ACI
docker build -t eventhub-processor .
az container create \
  --resource-group myResourceGroup \
  --name eventhub-processor \
  --image eventhub-processor \
  --restart-policy Always \
  --environment-variables \
    EVENT_HUB_NAMESPACE="your-namespace" \
    AZURE_STORAGE_ACCOUNT_NAME="your-storage"
```

## Monitoring & Troubleshooting

### Check Application Insights
- Monitor function executions
- View custom telemetry
- Set up alerts for failures

### View Storage Account
- Check ADLS Gen2 for created files
- Verify checkpoint files
- Monitor storage metrics

### Event Hub Metrics
- Monitor consumer lag
- Check partition distribution
- View throughput metrics

### Common Issues
1. **Authentication Errors**: Ensure proper RBAC roles (Event Hubs Data Receiver, Storage Blob Data Contributor)
2. **Network Issues**: Check firewall rules and virtual network settings
3. **Throttling**: Monitor Event Hub and Storage account limits
4. **Memory Issues**: Adjust batch sizes for large events



This error occurs because the Event Hub partition already has an active subscriber, and Event Hubs enforce a single active reader per partition per consumer group. Let me fix the code to handle this properly.Now let me also provide you with an alternative approach that's more robust for handling this scenario:## **Root Cause & Solutions**

The "Partition already has a subscriber" error occurs because:

1. **Multiple processes** are trying to read from the same partition with the same consumer group
2. **Previous connections** weren't properly closed
3. **Azure Functions scaling** created multiple instances reading simultaneously

## **Quick Fix Options:**

### **Option 1: Use the Updated Code (Recommended)**
The updated code in the first artifact now:
- Uses `receiveBatch` instead of `subscribe` (more reliable for batch processing)
- Processes partitions sequentially instead of in parallel
- Has proper error handling for subscriber conflicts
- Gracefully skips conflicted partitions

### **Option 2: Use a Unique Consumer Group**
Add this to your environment variables:
```bash
export CONSUMER_GROUP="telemetry-$(date +%s)"  # Unique consumer group
```

### **Option 3: Use the Alternative Robust Approach**
The second artifact provides multiple reading strategies with automatic fallback.

## **Test the Fix:**

```javascript
// test-fixed.js
const EventHubProcessor = require('./improved-processor'); // Updated version

const mockContext = {
    log: {
        info: (msg) => console.log(`[INFO] ${msg}`),
        error: (msg, err) => console.error(`[ERROR] ${msg}`, err),
        warn: (msg) => console.warn(`[WARN] ${msg}`)
    },
    done: () => console.log('Done')
};

async function test() {
    const processor = new EventHubProcessor();
    try {
        console.log('Starting test...');
        const result = await processor.processEvents(mockContext);
        console.log('Test completed:', result);
    } catch (error) {
        console.error('Test failed:', error);
    } finally {
        await processor.close();
    }
}

test().catch(console.error);
```

## **Production Recommendations:**

1. **Use Azure Functions with Event Hub Trigger** instead of manual polling:
```json
{
  "type": "eventHubTrigger",
  "name": "eventHubMessages",
  "direction": "in",
  "eventHubName": "telemetry-stream-parallel-hub",
  "connection": "EventHubConnectionString",
  "consumerGroup": "telemetry"
}
```

2. **Implement proper scaling rules** to avoid conflicts
3. **Use Blob-based checkpoint store** for production workloads
4. **Monitor consumer lag** in Azure portal

Try the updated code - it should handle the subscriber conflicts much better!


--- fixed from bottom
```js
const { EventHubConsumerClient, latestEventPosition } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");
const crypto = require('crypto');
const zlib = require('zlib');

// Configuration from environment variables
const config = {
  eventHub: {
    eventHubName: process.env.EVENT_HUB_NAME || 'telemetry-stream-parallel-hub',
    namespace: process.env.EVENT_HUB_NAMESPACE || 'weavix-reporting-dev-ehns.servicebus.windows.net',
    consumerGroup: process.env.CONSUMER_GROUP || 'telemetry'
  },
  blobStorage: {
    accountName: process.env.AZURE_STORAGE_ACCOUNT_NAME || 'weavixdatalakedevsa',
    fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "adls",
    basePath: process.env.ADLS_BASE_PATH || "adls"
  },
  processing: {
    maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
    maxWaitTimeMs: parseInt(process.env.MAX_WAIT_TIME_MS) || 300000, // 5 minutes
    maxWaitTimeSeconds: parseInt(process.env.MAX_WAIT_TIME_SECONDS) || 5,
    fileFormat: "jsonl", 
    compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubProcessor {
  constructor() {
    this.credential = new DefaultAzureCredential();
    
    this.consumerClient = new EventHubConsumerClient(
      config.eventHub.consumerGroup, 
      config.eventHub.namespace, 
      config.eventHub.eventHubName,
      this.credential
    );

    this.dataLakeServiceClient = new DataLakeServiceClient(
      `https://${config.blobStorage.accountName}.dfs.core.windows.net`,
      this.credential
    );

    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      config.blobStorage.fileSystemName
    );
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    context.log.info(`Starting batch processing: ${batchId}`);

    try {
      await this.fileSystemClient.createIfNotExists();
      
      const events = await this.readEventsFromHub(context);
      
      if (events.length === 0) {
        context.log.info("No events to process");
        return { processedEvents: 0, files: [] };
      }

      const processedData = await this.transformEvents(events, context);
      const uploadedFiles = await this.writeToBlob(processedData, batchId, context);
      
      await this.updateCheckpoint(events, context);
      
      const processingTime = Date.now() - startTime;
      context.log.info(`Batch processing completed: ${batchId}, Events: ${events.length}, Files: ${uploadedFiles.length}, Time: ${processingTime}ms`);
      
      return { 
        processedEvents: events.length, 
        files: uploadedFiles,
        processingTimeMs: processingTime 
      };
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  async readOneBatchFromPartition(partitionId, maxEvents = 50, waitTimeSeconds = 5, startPosition = latestEventPosition) {
    const events = [];
    let subscription = null;
    
    try {
      // Create a dedicated consumer client for this partition to avoid conflicts
      const partitionClient = this.consumerClient.createPartitionClient(partitionId, {
        startPosition: startPosition
      });

      const receivedEvents = await partitionClient.receiveBatch(maxEvents, {
        maxWaitTimeInSeconds: waitTimeSeconds
      });

      for (const event of receivedEvents) {
        events.push({
          partitionId: partitionId,
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTimeUtc: event.enqueuedTimeUtc,
          body: event.body,
          properties: event.properties,
          systemProperties: event.systemProperties
        });
      }

      await partitionClient.close();
      return events;

    } catch (error) {
      if (error.message?.includes('already has a subscriber') || 
          error.message?.includes('ReceiverDisconnected')) {
        console.warn(`Partition ${partitionId} already has subscriber, skipping...`);
        return [];
      }
      throw error;
    }
  }

  async readEventsFromHub(context) {
    const allEvents = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    context.log.info(`Reading from ${partitionIds.length} partitions`);
    
    const eventsPerPartition = Math.floor(config.processing.maxBatchSize / partitionIds.length);
    let successfulPartitions = 0;
    let skippedPartitions = 0;
    
    try {
      // Process partitions sequentially to avoid conflicts
      for (const partitionId of partitionIds) {
        try {
          const partitionEvents = await this.readOneBatchFromPartition(
            partitionId, 
            eventsPerPartition, 
            config.processing.maxWaitTimeSeconds
          );
          
          if (partitionEvents.length > 0) {
            allEvents.push(...partitionEvents);
            successfulPartitions++;
            context.log.info(`Partition ${partitionId}: read ${partitionEvents.length} events`);
          } else {
            skippedPartitions++;
          }
          
          // Small delay between partitions to avoid overwhelming the service
          await new Promise(resolve => setTimeout(resolve, 100));
          
        } catch (error) {
          if (error.message?.includes('already has a subscriber') || 
              error.message?.includes('ReceiverDisconnected')) {
            context.log.warn(`Partition ${partitionId} already has subscriber, skipping...`);
            skippedPartitions++;
          } else {
            context.log.error(`Error reading from partition ${partitionId}:`, error);
            // Continue with other partitions
          }
        }
      }

      // Sort by enqueued time for consistent processing order
      allEvents.sort((a, b) => 
        new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc)
      );

      context.log.info(`Read ${allEvents.length} events from Event Hub (${successfulPartitions} successful, ${skippedPartitions} skipped partitions)`);
      return allEvents;

    } catch (error) {
      context.log.error('Error reading events from hub:', error);
      throw error;
    }
  }

  async transformEvents(events, context) {
    const transformed = [];
    let errorCount = 0;

    for (const event of events) {
      try {
        // Parse MongoDB change stream event if it's JSON
        let changeStreamEvent = event.body;
        if (typeof changeStreamEvent === 'string') {
          changeStreamEvent = JSON.parse(changeStreamEvent);
        }

        // Validate required fields
        if (!changeStreamEvent.operationType) {
          throw new Error('Missing operationType in change stream event');
        }

        // Transform to Snowflake-friendly format
        const transformedEvent = {
          // Metadata
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber?.toString(), // Ensure string for consistency
            enqueued_time: event.enqueuedTimeUtc
          },
          
          // MongoDB Change Stream data
          operation_type: changeStreamEvent.operationType,
          database_name: changeStreamEvent.ns?.db || 'unknown_db',
          collection_name: changeStreamEvent.ns?.coll || 'unknown_collection',
          document_key: changeStreamEvent.documentKey,
          full_document: changeStreamEvent.fullDocument,
          update_description: changeStreamEvent.updateDescription,
          cluster_time: changeStreamEvent.clusterTime?.toString(), // Convert to string if present
          
          // Raw event for debugging (optional, can be removed for production)
          raw_event: changeStreamEvent
        };

        transformed.push(transformedEvent);
        
      } catch (error) {
        errorCount++;
        context.log.error(`Error transforming event:`, error);
        
        // Create error record for investigation
        transformed.push({
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          error: error.message,
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber?.toString(),
            enqueued_time: event.enqueuedTimeUtc
          },
          raw_event: event.body
        });
      }
    }

    if (errorCount > 0) {
      context.log.warn(`Encountered ${errorCount} transformation errors out of ${events.length} events`);
    }

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
      
      // Create hierarchical path
      const folderPath = `${config.blobStorage.basePath}/${dbName}/${collName}/${year}/${month}/${day}`;
      let fileName = `${hour}-${batchId}.jsonl`;
      
      context.log.info(`Processing ${events.length} events for ${collectionKey}`);

      // Convert to JSONL format (one JSON per line)
      const jsonlContent = events.map(record => JSON.stringify(record)).join('\n');
      
      let content = Buffer.from(jsonlContent, 'utf8');
      let contentType = 'application/x-ndjson';

      // Apply compression if enabled
      if (config.processing.compressionEnabled) {
        content = zlib.gzipSync(content);
        fileName = fileName + '.gz';
        contentType = 'application/gzip';
      }

      const fullPath = `${folderPath}/${fileName}`;

      try {
        // Ensure directory exists
        await this.ensureDirectoryExists(folderPath);
        
        // Upload file to ADLS Gen2
        const fileClient = this.fileSystemClient.getFileClient(fullPath);
        
        // Create and write file
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
          compressionEnabled: config.processing.compressionEnabled.toString(),
          originalSize: jsonlContent.length.toString(),
          compressedSize: content.length.toString()
        });

        uploadedFiles.push(fullPath);
        context.log.info(`Uploaded ${events.length} records to ${fullPath} (${content.length} bytes)`);
        
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
      if (!error.message?.includes('PathAlreadyExists')) {
        throw error;
      }
    }
  }

  async updateCheckpoint(events, context) {
    if (events.length === 0) return;

    const checkpoint = {
      lastProcessedTime: new Date().toISOString(),
      batchId: crypto.randomUUID(),
      totalEvents: events.length,
      partitionCheckpoints: {}
    };

    // Group events by partition and get latest offset for each
    events.forEach(event => {
      const partitionId = event.partitionId;
      if (!checkpoint.partitionCheckpoints[partitionId] || 
          Number(event.sequenceNumber) > Number(checkpoint.partitionCheckpoints[partitionId].sequenceNumber)) {
        checkpoint.partitionCheckpoints[partitionId] = {
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTime: event.enqueuedTimeUtc
        };
      }
    });

    const checkpointPath = `${config.blobStorage.basePath}/_checkpoints/latest.json`;
    const checkpointClient = this.fileSystemClient.getFileClient(checkpointPath);
    
    const checkpointContent = Buffer.from(JSON.stringify(checkpoint, null, 2), 'utf8');
    
    try {
      // Always recreate checkpoint file to ensure latest data
      await checkpointClient.deleteIfExists();
      await checkpointClient.create();
      await checkpointClient.append(checkpointContent, 0, checkpointContent.length);
      await checkpointClient.flush(checkpointContent.length);

      await checkpointClient.setMetadata({
        updatedAt: new Date().toISOString(),
        eventCount: events.length.toString()
      });

      context.log.info(`Checkpoint updated: ${checkpointPath}`);
      
    } catch (error) {
      context.log.error('Failed to update checkpoint:', error);
      // Don't throw - checkpoint failure shouldn't stop processing
    }
  }

  async close() {
    try {
      await this.consumerClient.close();
    } catch (error) {
      console.error('Error closing consumer client:', error);
    }
  }
}

module.exports = EventHubProcessor;
```
---- ROBUST
```js
const { EventHubConsumerClient, latestEventPosition } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");
const crypto = require('crypto');

class RobustEventHubProcessor {
  constructor() {
    this.credential = new DefaultAzureCredential();
    this.activeClients = new Map(); // Track active partition clients
    
    // Configuration
    this.config = {
      eventHub: {
        eventHubName: process.env.EVENT_HUB_NAME || 'telemetry-stream-parallel-hub',
        namespace: process.env.EVENT_HUB_NAMESPACE || 'weavix-reporting-dev-ehns.servicebus.windows.net',
        consumerGroup: process.env.CONSUMER_GROUP || 'telemetry'
      },
      blobStorage: {
        accountName: process.env.AZURE_STORAGE_ACCOUNT_NAME || 'weavixdatalakedevsa',
        fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "adls",
        basePath: process.env.ADLS_BASE_PATH || "adls"
      },
      processing: {
        maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
        maxWaitTimeSeconds: parseInt(process.env.MAX_WAIT_TIME_SECONDS) || 30,
        retryAttempts: parseInt(process.env.RETRY_ATTEMPTS) || 3,
        retryDelayMs: parseInt(process.env.RETRY_DELAY_MS) || 1000,
        compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
      }
    };

    this.consumerClient = new EventHubConsumerClient(
      this.config.eventHub.consumerGroup, 
      this.config.eventHub.namespace, 
      this.config.eventHub.eventHubName,
      this.credential
    );

    this.dataLakeServiceClient = new DataLakeServiceClient(
      `https://${this.config.blobStorage.accountName}.dfs.core.windows.net`,
      this.credential
    );

    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      this.config.blobStorage.fileSystemName
    );
  }

  // Method 1: Use subscription-based approach with conflict handling
  async readEventsWithSubscription(context) {
    const allEvents = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    const maxEventsPerPartition = Math.floor(this.config.processing.maxBatchSize / partitionIds.length);
    
    context.log.info(`Reading from ${partitionIds.length} partitions using subscription approach`);

    let subscription = null;
    
    try {
      subscription = this.consumerClient.subscribe(
        {
          processEvents: async (events, partitionContext) => {
            const partitionId = partitionContext.partitionId;
            
            for (const event of events) {
              allEvents.push({
                partitionId: partitionId,
                offset: event.offset,
                sequenceNumber: event.sequenceNumber,
                enqueuedTimeUtc: event.enqueuedTimeUtc,
                body: event.body,
                properties: event.properties,
                systemProperties: event.systemProperties
              });

              // Limit events per partition
              const partitionEvents = allEvents.filter(e => e.partitionId === partitionId);
              if (partitionEvents.length >= maxEventsPerPartition) {
                context.log.info(`Reached max events for partition ${partitionId}: ${partitionEvents.length}`);
                break;
              }
            }
          },
          processError: async (err, partitionContext) => {
            if (err.message?.includes('already has a subscriber')) {
              context.log.warn(`Partition ${partitionContext.partitionId} already has subscriber - this is expected in multi-instance scenarios`);
            } else {
              context.log.error(`Error on partition ${partitionContext.partitionId}:`, err);
            }
          }
        },
        {
          startPosition: latestEventPosition,
          maxBatchSize: 100,
          maxWaitTimeInSeconds: this.config.processing.maxWaitTimeSeconds
        }
      );

      // Wait for events to be collected
      await new Promise(resolve => setTimeout(resolve, this.config.processing.maxWaitTimeSeconds * 1000));

    } finally {
      if (subscription) {
        await subscription.close();
      }
    }

    // Sort events by enqueued time
    allEvents.sort((a, b) => new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc));
    
    context.log.info(`Collected ${allEvents.length} events from subscription`);
    return allEvents;
  }

  // Method 2: Use individual partition clients with better error handling
  async readEventsWithPartitionClients(context) {
    const allEvents = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    const eventsPerPartition = Math.floor(this.config.processing.maxBatchSize / partitionIds.length);
    
    context.log.info(`Reading from ${partitionIds.length} partitions using partition clients`);

    // Process partitions one at a time to avoid conflicts
    for (const partitionId of partitionIds) {
      let partitionClient = null;
      
      try {
        // Create partition client with retry logic
        partitionClient = await this.createPartitionClientWithRetry(partitionId, context);
        
        if (!partitionClient) {
          context.log.warn(`Skipping partition ${partitionId} - could not create client`);
          continue;
        }

        const events = await partitionClient.receiveBatch(eventsPerPartition, {
          maxWaitTimeInSeconds: Math.min(this.config.processing.maxWaitTimeSeconds, 10)
        });

        for (const event of events) {
          allEvents.push({
            partitionId: partitionId,
            offset: event.offset,
            sequenceNumber: event.sequenceNumber,
            enqueuedTimeUtc: event.enqueuedTimeUtc,
            body: event.body,
            properties: event.properties,
            systemProperties: event.systemProperties
          });
        }

        context.log.info(`Partition ${partitionId}: read ${events.length} events`);

      } catch (error) {
        if (this.isConflictError(error)) {
          context.log.warn(`Partition ${partitionId} conflict: ${error.message}`);
        } else {
          context.log.error(`Error reading partition ${partitionId}:`, error);
        }
      } finally {
        if (partitionClient) {
          try {
            await partitionClient.close();
          } catch (closeError) {
            context.log.warn(`Error closing partition client ${partitionId}:`, closeError.message);
          }
        }
      }

      // Small delay between partitions
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    // Sort events by enqueued time
    allEvents.sort((a, b) => new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc));
    
    context.log.info(`Collected ${allEvents.length} events from partition clients`);
    return allEvents;
  }

  async createPartitionClientWithRetry(partitionId, context, attempt = 1) {
    try {
      const partitionClient = this.consumerClient.createPartitionClient(partitionId, {
        startPosition: latestEventPosition
      });
      
      return partitionClient;
      
    } catch (error) {
      if (this.isConflictError(error) && attempt < this.config.processing.retryAttempts) {
        context.log.info(`Retrying partition ${partitionId}, attempt ${attempt + 1}`);
        await new Promise(resolve => setTimeout(resolve, this.config.processing.retryDelayMs * attempt));
        return this.createPartitionClientWithRetry(partitionId, context, attempt + 1);
      }
      
      if (this.isConflictError(error)) {
        context.log.warn(`Partition ${partitionId} has active subscriber after ${attempt} attempts`);
        return null; // Skip this partition
      }
      
      throw error;
    }
  }

  isConflictError(error) {
    const message = error.message?.toLowerCase() || '';
    return message.includes('already has a subscriber') || 
           message.includes('receiverdisconnected') ||
           message.includes('conflict') ||
           message.includes('partition is owned by another receiver');
  }

  // Method 3: Checkpoint-based approach (recommended for production)
  async readEventsFromCheckpoint(context) {
    const allEvents = [];
    let subscription = null;
    
    try {
      // Use a unique consumer group or ensure only one instance per consumer group
      const uniqueConsumerGroup = `${this.config.eventHub.consumerGroup}-${crypto.randomUUID().slice(0, 8)}`;
      
      const checkpointStore = new InMemoryCheckpointStore(); // You might want to use Blob checkpoint store in production
      
      const consumerClient = new EventHubConsumerClient(
        uniqueConsumerGroup,
        this.config.eventHub.namespace,
        this.config.eventHub.eventHubName,
        this.credential,
        checkpointStore
      );

      subscription = consumerClient.subscribe(
        {
          processEvents: async (events, partitionContext) => {
            for (const event of events) {
              allEvents.push({
                partitionId: partitionContext.partitionId,
                offset: event.offset,
                sequenceNumber: event.sequenceNumber,
                enqueuedTimeUtc: event.enqueuedTimeUtc,
                body: event.body,
                properties: event.properties,
                systemProperties: event.systemProperties
              });
            }
            
            // Update checkpoint
            if (events.length > 0) {
              await partitionContext.updateCheckpoint(events[events.length - 1]);
            }
          },
          processError: async (err, partitionContext) => {
            context.log.error(`Error on partition ${partitionContext.partitionId}:`, err);
          }
        },
        {
          startPosition: latestEventPosition,
          maxBatchSize: 100
        }
      );

      // Wait for events
      await new Promise(resolve => setTimeout(resolve, this.config.processing.maxWaitTimeSeconds * 1000));

      await consumerClient.close();

    } catch (error) {
      context.log.error('Error in checkpoint-based reading:', error);
      throw error;
    }

    allEvents.sort((a, b) => new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc));
    context.log.info(`Collected ${allEvents.length} events with checkpoint approach`);
    return allEvents;
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    context.log.info(`Starting batch processing: ${batchId}`);

    try {
      await this.fileSystemClient.createIfNotExists();
      
      // Try different reading strategies
      let events = [];
      
      try {
        // Strategy 1: Partition clients (most reliable for batch processing)
        events = await this.readEventsWithPartitionClients(context);
      } catch (error) {
        context.log.warn('Partition client approach failed, trying subscription:', error.message);
        
        try {
          // Strategy 2: Subscription approach
          events = await this.readEventsWithSubscription(context);
        } catch (subscriptionError) {
          context.log.error('Both reading strategies failed:', subscriptionError);
          throw subscriptionError;
        }
      }
      
      if (events.length === 0) {
        context.log.info("No events to process");
        return { processedEvents: 0, files: [], processingTimeMs: Date.now() - startTime };
      }

      const processedData = await this.transformEvents(events, context);
      const uploadedFiles = await this.writeToBlob(processedData, batchId, context);
      await this.updateCheckpoint(events, context);
      
      const processingTime = Date.now() - startTime;
      context.log.info(`Batch processing completed: ${batchId}, Events: ${events.length}, Files: ${uploadedFiles.length}, Time: ${processingTime}ms`);
      
      return { 
        processedEvents: events.length, 
        files: uploadedFiles,
        processingTimeMs: processingTime 
      };
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  // Include the rest of your transform, write, and utility methods here...
  // (transformEvents, writeToBlob, updateCheckpoint, etc.)
  
  async close() {
    // Close all active clients
    for (const [partitionId, client] of this.activeClients.entries()) {
      try {
        await client.close();
      } catch (error) {
        console.warn(`Error closing client for partition ${partitionId}:`, error.message);
      }
    }
    this.activeClients.clear();
    
    try {
      await this.consumerClient.close();
    } catch (error) {
      console.error('Error closing consumer client:', error);
    }
  }
}

// Simple in-memory checkpoint store for testing
class InMemoryCheckpointStore {
  constructor() {
    this.checkpoints = new Map();
  }

  async listCheckpoints(fullyQualifiedNamespace, eventHubName, consumerGroup) {
    const key = `${fullyQualifiedNamespace}/${eventHubName}/${consumerGroup}`;
    return this.checkpoints.get(key) || [];
  }

  async updateCheckpoint(checkpoint) {
    const key = `${checkpoint.fullyQualifiedNamespace}/${checkpoint.eventHubName}/${checkpoint.consumerGroup}`;
    let checkpoints = this.checkpoints.get(key) || [];
    
    // Update or add checkpoint for this partition
    const existingIndex = checkpoints.findIndex(c => c.partitionId === checkpoint.partitionId);
    if (existingIndex >= 0) {
      checkpoints[existingIndex] = checkpoint;
    } else {
      checkpoints.push(checkpoint);
    }
    
    this.checkpoints.set(key, checkpoints);
  }
}

module.exports = RobustEventHubProcessor;
```

-----------------------------------------------------------------
---- OLD CODE WHICH has problem: Partition already has a subscriber

```js
const { EventHubConsumerClient, latestEventPosition } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");
const crypto = require('crypto');
const zlib = require('zlib');

// Configuration from environment variables
const config = {
  eventHub: {
    eventHubName: process.env.EVENT_HUB_NAME || 'telemetry-stream-parallel-hub',
    namespace: process.env.EVENT_HUB_NAMESPACE || 'weavix-reporting-dev-ehns.servicebus.windows.net',
    consumerGroup: process.env.CONSUMER_GROUP || 'telemetry'
  },
  blobStorage: {
    accountName: process.env.AZURE_STORAGE_ACCOUNT_NAME || 'weavixdatalakedevsa',
    fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "adls",
    basePath: process.env.ADLS_BASE_PATH || "adls"
  },
  processing: {
    maxBatchSize: parseInt(process.env.MAX_BATCH_SIZE) || 1000,
    maxWaitTimeMs: parseInt(process.env.MAX_WAIT_TIME_MS) || 300000, // 5 minutes
    maxWaitTimeSeconds: parseInt(process.env.MAX_WAIT_TIME_SECONDS) || 5,
    fileFormat: "jsonl", 
    compressionEnabled: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubProcessor {
  constructor() {
    this.credential = new DefaultAzureCredential();
    
    this.consumerClient = new EventHubConsumerClient(
      config.eventHub.consumerGroup, 
      config.eventHub.namespace, 
      config.eventHub.eventHubName,
      this.credential
    );

    this.dataLakeServiceClient = new DataLakeServiceClient(
      `https://${config.blobStorage.accountName}.dfs.core.windows.net`,
      this.credential
    );

    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      config.blobStorage.fileSystemName
    );
  }

  async processEvents(context) {
    const startTime = Date.now();
    const batchId = crypto.randomUUID();
    context.log.info(`Starting batch processing: ${batchId}`);

    try {
      await this.fileSystemClient.createIfNotExists();
      
      const events = await this.readEventsFromHub(context);
      
      if (events.length === 0) {
        context.log.info("No events to process");
        return { processedEvents: 0, files: [] };
      }

      const processedData = await this.transformEvents(events, context);
      const uploadedFiles = await this.writeToBlob(processedData, batchId, context);
      
      await this.updateCheckpoint(events, context);
      
      const processingTime = Date.now() - startTime;
      context.log.info(`Batch processing completed: ${batchId}, Events: ${events.length}, Files: ${uploadedFiles.length}, Time: ${processingTime}ms`);
      
      return { 
        processedEvents: events.length, 
        files: uploadedFiles,
        processingTimeMs: processingTime 
      };
      
    } catch (error) {
      context.log.error(`Error processing batch ${batchId}:`, error);
      throw error;
    }
  }

  async readOneBatchFromPartition(partitionId, maxEvents = 50, waitTimeSeconds = 5, startPosition = latestEventPosition) {
    const events = [];
    
    const subscription = this.consumerClient.subscribe(
      {
        processEvents: async (receivedEvents, context) => {
          for (const event of receivedEvents) {
            events.push({
              partitionId: context.partitionId,
              offset: event.offset,
              sequenceNumber: event.sequenceNumber,
              enqueuedTimeUtc: event.enqueuedTimeUtc,
              body: event.body,
              properties: event.properties,
              systemProperties: event.systemProperties
            });
            
            if (events.length >= maxEvents) {
              break;
            }
          }
        },
        processError: async (err, context) => {
          console.error(`Error on partition ${context.partitionId}:`, err);
        }
      },
      {
        startPosition: startPosition,
        maxBatchSize: maxEvents,
        maxWaitTimeInSeconds: waitTimeSeconds
      }
    );

    // Wait for events or timeout
    await new Promise(resolve => setTimeout(resolve, waitTimeSeconds * 1000));
    await subscription.close();
    
    return events;
  }

  async readEventsFromHub(context) {
    const allEvents = [];
    const partitionIds = await this.consumerClient.getPartitionIds();
    context.log.info(`Reading from ${partitionIds.length} partitions`);
    
    const eventsPerPartition = Math.floor(config.processing.maxBatchSize / partitionIds.length);
    
    try {
      const partitionPromises = partitionIds.map(async (partitionId) => {
        try {
          return await this.readOneBatchFromPartition(
            partitionId, 
            eventsPerPartition, 
            config.processing.maxWaitTimeSeconds
          );
        } catch (error) {
          context.log.error(`Error reading from partition ${partitionId}:`, error);
          return [];
        }
      });

      const partitionResults = await Promise.all(partitionPromises);
      
      // Flatten results and add to allEvents
      partitionResults.forEach(partitionEvents => {
        allEvents.push(...partitionEvents);
      });

      // Sort by enqueued time for consistent processing order
      allEvents.sort((a, b) => 
        new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc)
      );

      context.log.info(`Read ${allEvents.length} events from Event Hub`);
      return allEvents;

    } catch (error) {
      context.log.error('Error reading events from hub:', error);
      throw error;
    }
  }

  async transformEvents(events, context) {
    const transformed = [];
    let errorCount = 0;

    for (const event of events) {
      try {
        // Parse MongoDB change stream event if it's JSON
        let changeStreamEvent = event.body;
        if (typeof changeStreamEvent === 'string') {
          changeStreamEvent = JSON.parse(changeStreamEvent);
        }

        // Validate required fields
        if (!changeStreamEvent.operationType) {
          throw new Error('Missing operationType in change stream event');
        }

        // Transform to Snowflake-friendly format
        const transformedEvent = {
          // Metadata
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber?.toString(), // Ensure string for consistency
            enqueued_time: event.enqueuedTimeUtc
          },
          
          // MongoDB Change Stream data
          operation_type: changeStreamEvent.operationType,
          database_name: changeStreamEvent.ns?.db || 'unknown_db',
          collection_name: changeStreamEvent.ns?.coll || 'unknown_collection',
          document_key: changeStreamEvent.documentKey,
          full_document: changeStreamEvent.fullDocument,
          update_description: changeStreamEvent.updateDescription,
          cluster_time: changeStreamEvent.clusterTime?.toString(), // Convert to string if present
          
          // Raw event for debugging (optional, can be removed for production)
          raw_event: changeStreamEvent
        };

        transformed.push(transformedEvent);
        
      } catch (error) {
        errorCount++;
        context.log.error(`Error transforming event:`, error);
        
        // Create error record for investigation
        transformed.push({
          event_id: crypto.randomUUID(),
          processed_timestamp: new Date().toISOString(),
          error: error.message,
          event_hub_metadata: {
            partition_id: event.partitionId,
            offset: event.offset,
            sequence_number: event.sequenceNumber?.toString(),
            enqueued_time: event.enqueuedTimeUtc
          },
          raw_event: event.body
        });
      }
    }

    if (errorCount > 0) {
      context.log.warn(`Encountered ${errorCount} transformation errors out of ${events.length} events`);
    }

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
      
      // Create hierarchical path
      const folderPath = `${config.blobStorage.basePath}/${dbName}/${collName}/${year}/${month}/${day}`;
      let fileName = `${hour}-${batchId}.jsonl`;
      
      context.log.info(`Processing ${events.length} events for ${collectionKey}`);

      // Convert to JSONL format (one JSON per line)
      const jsonlContent = events.map(record => JSON.stringify(record)).join('\n');
      
      let content = Buffer.from(jsonlContent, 'utf8');
      let contentType = 'application/x-ndjson';

      // Apply compression if enabled
      if (config.processing.compressionEnabled) {
        content = zlib.gzipSync(content);
        fileName = fileName + '.gz';
        contentType = 'application/gzip';
      }

      const fullPath = `${folderPath}/${fileName}`;

      try {
        // Ensure directory exists
        await this.ensureDirectoryExists(folderPath);
        
        // Upload file to ADLS Gen2
        const fileClient = this.fileSystemClient.getFileClient(fullPath);
        
        // Create and write file
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
          compressionEnabled: config.processing.compressionEnabled.toString(),
          originalSize: jsonlContent.length.toString(),
          compressedSize: content.length.toString()
        });

        uploadedFiles.push(fullPath);
        context.log.info(`Uploaded ${events.length} records to ${fullPath} (${content.length} bytes)`);
        
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
      if (!error.message?.includes('PathAlreadyExists')) {
        throw error;
      }
    }
  }

  async updateCheckpoint(events, context) {
    if (events.length === 0) return;

    const checkpoint = {
      lastProcessedTime: new Date().toISOString(),
      batchId: crypto.randomUUID(),
      totalEvents: events.length,
      partitionCheckpoints: {}
    };

    // Group events by partition and get latest offset for each
    events.forEach(event => {
      const partitionId = event.partitionId;
      if (!checkpoint.partitionCheckpoints[partitionId] || 
          Number(event.sequenceNumber) > Number(checkpoint.partitionCheckpoints[partitionId].sequenceNumber)) {
        checkpoint.partitionCheckpoints[partitionId] = {
          offset: event.offset,
          sequenceNumber: event.sequenceNumber,
          enqueuedTime: event.enqueuedTimeUtc
        };
      }
    });

    const checkpointPath = `${config.blobStorage.basePath}/_checkpoints/latest.json`;
    const checkpointClient = this.fileSystemClient.getFileClient(checkpointPath);
    
    const checkpointContent = Buffer.from(JSON.stringify(checkpoint, null, 2), 'utf8');
    
    try {
      // Always recreate checkpoint file to ensure latest data
      await checkpointClient.deleteIfExists();
      await checkpointClient.create();
      await checkpointClient.append(checkpointContent, 0, checkpointContent.length);
      await checkpointClient.flush(checkpointContent.length);

      await checkpointClient.setMetadata({
        updatedAt: new Date().toISOString(),
        eventCount: events.length.toString()
      });

      context.log.info(`Checkpoint updated: ${checkpointPath}`);
      
    } catch (error) {
      context.log.error('Failed to update checkpoint:', error);
      // Don't throw - checkpoint failure shouldn't stop processing
    }
  }

  async close() {
    try {
      await this.consumerClient.close();
    } catch (error) {
      console.error('Error closing consumer client:', error);
    }
  }
}

module.exports = EventHubProcessor;
```
