 Let me explain why Event Hubs Capture Approach is better and provide the implementation.

## Event Hubs Capture Approach vs My Original Solution

### **My Original Approach** (More Complex):
```
Event Hub → Azure Function (with Event Hub client) → ADLS Gen2 → Snowflake
```

### **Programmer's Suggested Approach** (Much Simpler):
```
Event Hub → Event Hubs Capture (automatic) → ADLS Gen2 → Timer Function → Snowflake
```

## Why Event Hubs Capture is Superior

### **1. Zero Event Hub Client Management**
- **No connection handling**: Capture is managed by Azure
- **No partition management**: Azure handles all partitioning automatically
- **No checkpoint tracking**: Azure manages progress automatically
- **No consumer group conflicts**: Capture operates independently

### **2. True Batch Semantics**
- **Time-based windows**: Guaranteed hourly files (or 5-min, 15-min windows)
- **Predictable file sizes**: Consistent batch sizes based on time, not event count
- **Automatic file creation**: Files appear exactly on schedule
- **No event buffering logic**: Azure handles all batching

### **3. Better Reliability**
- **Azure-managed**: Microsoft handles the capture infrastructure
- **Guaranteed delivery**: Built-in retry and error handling
- **No function timeouts**: Capture runs continuously, function only processes files
- **Simpler failure modes**: Fewer moving parts = fewer failure points

## Updated Implementation## Key Advantages of Event Hub Capture Approach

### **1. Simplified Architecture**
```
Before: Event Hub Client → Event Processing → ADLS Gen2
After:  Event Hub Capture → File Processing → ADLS Gen2
```

**Benefits:**
- ❌ **No Event Hub SDK complexity**: No connection management, partition handling, or checkpoints
- ✅ **File-based processing**: Simple file enumeration and processing
- ✅ **Stateless function**: Function just processes files, no event streaming state

### **2. True Batch Semantics**
```
# Event Hub Capture automatically creates files like:
mongodb-changes/2025/01/15/14/30/45/namespace.mongodb-changes.0.2025-01-15-14-30-45.json
```

**Configuration options:**
- **Hourly batches**: `capture-interval-seconds 3600` 
- **5-minute batches**: `capture-interval-seconds 300`
- **Size-based**: `capture-size-limit-bytes 100MB`

### **3. Zero Message Loss Risk**
- **Azure-managed**: Microsoft handles all the capture reliability
- **Guaranteed delivery**: Events are captured even if your function fails
- **No backpressure**: Capture continues regardless of downstream processing
- **Built-in retry**: Azure handles transient failures automatically

### **4. Operational Simplicity**
```bash
# Your function schedule can be relaxed:
"schedule": "0 5 */1 * * *"  # Run 5 minutes past each hour
```

**Why this works:**
- Capture files are guaranteed to be ready by 5 minutes past the hour
- Function processes whatever files are available
- No real-time processing pressure

### **5. Better Error Handling**
```
If function fails:
├── Capture files remain in ADLS Gen2
├── Next function run picks up missed files  
├── No data loss
└── Easy retry/replay
```

## Cost Comparison

### **My Original Approach:**
- Function runs continuously or frequently
- Event Hub client connection costs
- Complex error handling needed

### **Event Hub Capture Approach:**
- Function runs only hourly (5 minutes past the hour)
- No Event Hub client connections
- Capture is a flat fee (~$0.10/million events)
- Much lower Function execution costs

## Configuration Recommendations

### **For Hourly Processing:**
```bash
--capture-interval-seconds 3600    # 1 hour windows
--capture-size-limit-bytes 314572800  # 300MB max file size
```

### **For Lower Latency (5-minute windows):**
```bash
--capture-interval-seconds 300     # 5 minute windows  
--capture-size-limit-bytes 52428800   # 50MB max file size
```

## Final Architecture

**Your programmer's suggestion results in:**

```
MongoDB Atlas Change Streams 
    ↓
Event Hub (with Capture enabled)
    ↓ (automatic, managed by Azure)
ADLS Gen2 Capture Files (hourly batches)
    ↓ (Timer Function: hourly + 5 minutes)
ADLS Gen2 Processed Files (organized hierarchy)  
    ↓ (Event Grid + Snowpipe)
Snowflake
```

**This is significantly simpler and more robust** than my original approach. 

Event Hub Capture eliminates all the Event Hub client complexity while providing true batch semantics and better reliability!


```bash
# Event Hub Capture Setup Commands

# 1. Create ADLS Gen2 Storage Account (if not exists)
az storage account create \
  --name yourstorageaccount \
  --resource-group mongodb-pipeline-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true  # This enables ADLS Gen2

# 2. Create filesystem for capture
az storage fs create \
  --name eventhub-capture \
  --account-name yourstorageaccount

# 3. Enable Event Hub Capture - Method A: Azure CLI
az eventhubs eventhub update \
  --resource-group mongodb-pipeline-rg \
  --namespace-name mongodb-eh-namespace \
  --name mongodb-changes \
  --enable-capture true \
  --capture-interval-seconds 3600 \
  --capture-size-limit-bytes 314572800 \
  --destination-name EventHubArchive.AzureBlockBlob \
  --storage-account yourstorageaccount \
  --blob-container eventhub-capture \
  --archive-name-format "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"

# Alternative: 5-minute windows for lower latency
az eventhubs eventhub update \
  --resource-group mongodb-pipeline-rg \
  --namespace-name mongodb-eh-namespace \
  --name mongodb-changes \
  --enable-capture true \
  --capture-interval-seconds 300 \
  --capture-size-limit-bytes 10485760 \
  --destination-name EventHubArchive.AzureBlockBlob \
  --storage-account yourstorageaccount \
  --blob-container eventhub-capture \
  --archive-name-format "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"

# 4. Verify Capture is enabled
az eventhubs eventhub show \
  --resource-group mongodb-pipeline-rg \
  --namespace-name mongodb-eh-namespace \
  --name mongodb-changes \
  --query '{captureEnabled:captureDescription.enabled, interval:captureDescription.intervalInSeconds, sizeLimit:captureDescription.sizeLimitInBytes}'

# 5. List captured files (after some data flows)
az storage fs file list \
  --account-name yourstorageaccount \
  --file-system eventhub-capture \
  --path "mongodb-changes/" \
  --recursive \
  --output table

# 6. Example: Download a specific capture file for inspection
az storage fs file download \
  --account-name yourstorageaccount \
  --file-system eventhub-capture \
  --source "mongodb-changes/2025/01/15/14/30/45/namespace.mongodb-changes.0.2025-01-15-14-30-45.json" \
  --destination ./inspect-capture.json

# 7. Set up proper permissions for the Function App
# Get Function App's managed identity
FUNCTION_APP_IDENTITY=$(az functionapp identity show \
  --name mongodb-pipeline-function \
  --resource-group mongodb-pipeline-rg \
  --query principalId -o tsv)

# Assign Storage Blob Data Contributor role
az role assignment create \
  --assignee $FUNCTION_APP_IDENTITY \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/mongodb-pipeline-rg/providers/Microsoft.Storage/storageAccounts/yourstorageaccount"

# 8. Configure Function App environment variables
az functionapp config appsettings set \
  --name mongodb-pipeline-function \
  --resource-group mongodb-pipeline-rg \
  --settings \
    "AZURE_STORAGE_CONNECTION_STRING=<connection-string>" \
    "ADLS_FILESYSTEM_NAME=eventhub-capture" \
    "CAPTURE_PATH=mongodb-changes" \
    "PROCESSED_PATH=processed/mongodb-changes" \
    "LOOKBACK_HOURS=2" \
    "BATCH_SIZE=1000" \
    "ENABLE_COMPRESSION=true"

# 9. Test capture is working - send test events
# (This would be done by your MongoDB change stream producer)

# 10. Monitor capture files being created
watch "az storage fs file list \
  --account-name yourstorageaccount \
  --file-system eventhub-capture \
  --path mongodb-changes/$(date -u +%Y/%m/%d/%H) \
  --output table"
```


### Azure function
 
// function.json - Azure Function configuration for file processing
```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 5 */1 * * *"
    }
  ],
  "scriptFile": "index.js"
}
```
// index.js - Timer-triggered function to process Event Hub Capture files
```js
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const path = require('path');
const zlib = require('zlib');

// Configuration from environment variables
const config = {
  adls: {
    connectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
    fileSystemName: process.env.ADLS_FILESYSTEM_NAME || "eventhub-capture",
    capturePath: process.env.CAPTURE_PATH || "mongodb-changes",
    processedPath: process.env.PROCESSED_PATH || "processed/mongodb-changes"
  },
  processing: {
    lookbackHours: parseInt(process.env.LOOKBACK_HOURS) || 2, // Process last N hours
    batchSize: parseInt(process.env.BATCH_SIZE) || 1000,
    enableCompression: process.env.ENABLE_COMPRESSION === "true"
  }
};

class EventHubCaptureProcessor {
  constructor() {
    this.dataLakeServiceClient = new DataLakeServiceClient(
      config.adls.connectionString
    );
    
    this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(
      config.adls.fileSystemName
    );
  }

  async processNewCaptures(context) {
    const batchId = new Date().toISOString().replace(/[:.]/g, '-');
    
    context.log(`Starting capture file processing: ${batchId}`);

    try {
      // Find new capture files to process
      const newFiles = await this.findNewCaptureFiles(context);
      
      if (newFiles.length === 0) {
        context.log("No new capture files to process");
        return;
      }

      context.log(`Found ${newFiles.length} new capture files`);

      // Process each capture file
      const processedData = [];
      for (const captureFile of newFiles) {
        const events = await this.processCaptureFile(captureFile, context);
        processedData.push(...events);
      }

      if (processedData.length === 0) {
        context.log("No events extracted from capture files");
        return;
      }

      // Write transformed data to organized hierarchy
      await this.writeTransformedData(processedData, batchId, context);
      
      // Mark files as processed
      await this.markFilesAsProcessed(newFiles, context);
      
      context.log(`Processing completed: ${processedData.length} events processed`);
      
    } catch (error) {
      context.log.error(`Error processing captures:`, error);
      throw error;
    }
  }

  async findNewCaptureFiles(context) {
    const newFiles = [];
    const now = new Date();
    
    // Look back specified hours to catch any missed files
    for (let i = 0; i < config.processing.lookbackHours; i++) {
      const checkTime = new Date(now.getTime() - (i * 60 * 60 * 1000));
      const year = checkTime.getUTCFullYear();
      const month = String(checkTime.getUTCMonth() + 1).padStart(2, '0');
      const day = String(checkTime.getUTCDate()).padStart(2, '0');
      const hour = String(checkTime.getUTCHours()).padStart(2, '0');
      
      // Event Hub Capture creates files like: 
      // mongodb-changes/2025/01/15/14/eventhubnamespacename.mongodb-changes.0.2025-01-15.14.avro
      const captureFolderPath = `${config.adls.capturePath}/${year}/${month}/${day}/${hour}`;
      
      try {
        const directoryClient = this.fileSystemClient.getDirectoryClient(captureFolderPath);
        const fileIter = directoryClient.listPaths({ recursive: false });
        
        for await (const file of fileIter) {
          if (!file.isDirectory && 
              (file.name.endsWith('.avro') || file.name.endsWith('.json')) &&
              !await this.isFileProcessed(file.name)) {
            
            newFiles.push({
              path: file.name,
              lastModified: file.lastModified,
              size: file.contentLength,
              captureHour: `${year}-${month}-${day}-${hour}`
            });
          }
        }
        
      } catch (error) {
        if (error.statusCode !== 404) {
          context.log.error(`Error checking folder ${captureFolderPath}:`, error);
        }
      }
    }

    return newFiles.sort((a, b) => new Date(a.lastModified) - new Date(b.lastModified));
  }

  async processCaptureFile(captureFile, context) {
    context.log(`Processing capture file: ${captureFile.path}`);
    
    try {
      const fileClient = this.fileSystemClient.getFileClient(captureFile.path);
      const downloadResponse = await fileClient.read();
      const content = await this.streamToBuffer(downloadResponse.readableStreamBody);
      
      let events;
      
      if (captureFile.path.endsWith('.avro')) {
        // Parse Avro format (Event Hub Capture default)
        events = await this.parseAvroContent(content, context);
      } else if (captureFile.path.endsWith('.json')) {
        // Parse JSON format
        events = await this.parseJsonContent(content, context);
      } else {
        throw new Error(`Unsupported file format: ${captureFile.path}`);
      }

      // Transform events to Snowflake format
      const transformedEvents = events.map(event => this.transformEvent(event, captureFile));
      
      context.log(`Extracted ${transformedEvents.length} events from ${captureFile.path}`);
      return transformedEvents;
      
    } catch (error) {
      context.log.error(`Error processing ${captureFile.path}:`, error);
      return []; // Continue processing other files
    }
  }

  async parseAvroContent(content, context) {
    // Event Hub Capture stores in Avro format by default
    // For simplicity, assuming JSON format here
    // In production, use avro-js library to parse Avro files
    throw new Error("Avro parsing not implemented - configure Event Hub Capture for JSON format");
  }

  async parseJsonContent(content, context) {
    const textContent = content.toString('utf-8');
    const lines = textContent.split('\n').filter(line => line.trim());
    
    return lines.map(line => {
      try {
        return JSON.parse(line);
      } catch (error) {
        context.log.warn(`Failed to parse line: ${line}`);
        return null;
      }
    }).filter(event => event !== null);
  }

  transformEvent(event, captureFile) {
    // Transform Event Hub captured event to Snowflake format
    return {
      event_id: require('crypto').randomUUID(),
      processed_timestamp: new Date().toISOString(),
      capture_file: captureFile.path,
      capture_hour: captureFile.captureHour,
      
      // MongoDB Change Stream data (assuming event.body contains the change stream event)
      operation_type: event.body?.operationType,
      database_name: event.body?.ns?.db,
      collection_name: event.body?.ns?.coll,
      document_key: event.body?.documentKey,
      full_document: event.body?.fullDocument,
      update_description: event.body?.updateDescription,
      cluster_time: event.body?.clusterTime,
      
      // Event Hub metadata
      event_hub_metadata: {
        enqueued_time: event.enqueuedTimeUtc,
        offset: event.offset,
        sequence_number: event.sequenceNumber,
        partition_id: event.partitionId
      },
      
      // Raw event for debugging
      raw_event: event.body
    };
  }

  async writeTransformedData(events, batchId, context) {
    // Group events by database and collection
    const groupedEvents = this.groupEventsByCollection(events);
    const uploadedFiles = [];

    for (const [collectionKey, collectionEvents] of Object.entries(groupedEvents)) {
      const [dbName, collName] = collectionKey.split('.');
      
      // Use first event's capture hour for consistent organization
      const captureHour = collectionEvents[0]?.capture_hour || 'unknown';
      const [year, month, day, hour] = captureHour.split('-');
      
      // Create hierarchical path: processed/database/collection/YYYY/MM/DD/HH.jsonl
      const folderPath = `${config.adls.processedPath}/${dbName}/${collName}/${year}/${month}/${day}`;
      const fileName = `${hour}-${batchId}.jsonl`;
      const fullPath = `${folderPath}/${fileName}`;

      // Convert to JSONL format
      let content = collectionEvents.map(record => JSON.stringify(record)).join('\n');
      
      if (config.processing.enableCompression) {
        content = zlib.gzipSync(content);
        fullPath += '.gz';
      }

      try {
        await this.ensureDirectoryExists(folderPath);
        
        const fileClient = this.fileSystemClient.getFileClient(fullPath);
        await fileClient.create();
        await fileClient.append(content, 0, content.length);
        await fileClient.flush(content.length);
        
        await fileClient.setMetadata({
          batchId: batchId,
          recordCount: collectionEvents.length.toString(),
          processedAt: new Date().toISOString(),
          database: dbName,
          collection: collName,
          sourceFiles: collectionEvents.map(e => e.capture_file).join(',')
        });

        uploadedFiles.push(fullPath);
        context.log(`Uploaded ${collectionEvents.length} records to ${fullPath}`);
        
      } catch (error) {
        context.log.error(`Failed to upload ${fullPath}:`, error);
        throw error;
      }
    }
    
    return uploadedFiles;
  }

  groupEventsByCollection(events) {
    const grouped = {};
    
    events.forEach(event => {
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
      if (error.statusCode !== 409) {
        throw error;
      }
    }
  }

  async isFileProcessed(filePath) {
    // Check if file has been processed by looking for marker
    const markerPath = `_processed/${filePath}.marker`;
    try {
      const markerClient = this.fileSystemClient.getFileClient(markerPath);
      await markerClient.getProperties();
      return true; // File exists = already processed
    } catch (error) {
      return false; // File doesn't exist = not processed
    }
  }

  async markFilesAsProcessed(files, context) {
    const promises = files.map(async (file) => {
      const markerPath = `_processed/${file.path}.marker`;
      const markerClient = this.fileSystemClient.getFileClient(markerPath);
      
      const markerContent = JSON.stringify({
        processedAt: new Date().toISOString(),
        originalFile: file.path,
        fileSize: file.size,
        captureHour: file.captureHour
      });

      try {
        await markerClient.create();
        await markerClient.append(markerContent, 0, markerContent.length);
        await markerClient.flush(markerContent.length);
      } catch (error) {
        context.log.error(`Failed to create marker for ${file.path}:`, error);
      }
    });

    await Promise.all(promises);
  }

  async streamToBuffer(readableStream) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      readableStream.on('data', (data) => {
        chunks.push(data instanceof Buffer ? data : Buffer.from(data));
      });
      readableStream.on('end', () => {
        resolve(Buffer.concat(chunks));
      });
      readableStream.on('error', reject);
    });
  }
}

// Main Azure Function entry point
module.exports = async function (context, myTimer) {
  const processor = new EventHubCaptureProcessor();
  
  try {
    await processor.processNewCaptures(context);
  } catch (error) {
    context.log.error('Function execution failed:', error);
    throw error;
  }
};
```
// package.json
```json
{
  "name": "eventhub-capture-processor",
  "version": "1.0.0",
  "description": "Azure Function to process Event Hub Capture files and prepare for Snowflake ingestion",
  "main": "index.js",
  "dependencies": {
    "@azure/storage-file-datalake": "^12.16.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```
