# How to Run the EventHub Processor

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
