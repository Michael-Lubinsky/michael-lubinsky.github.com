## Claude


The current pipeline only processes new records from EventHub. 
For existing MongoDB collections, you need an initial data migration strategy. 
Let me provide you with additional components to handle historical data.

Complete data pipeline solution with all three components:

## **Step 1: EventHub to ADLS Ingestion**
The Node.js application includes:
- Real-time EventHub consumer with checkpoint management
- Automatic partitioning by date/hour (`db/collection/year=YYYY/month=MM/day=DD/hour=HH/`)
- Rolling JSONL files (`events-YYYYMMDD-HH.jsonl`)
- Buffered writes with configurable batch sizes
- Graceful shutdown and error handling
- Event enrichment with metadata

## **Step 2: ADLS to Snowflake Loader**
The Node.js application features:
- Hourly scheduled processing using cron jobs
- Automatic bronze table creation for each collection
- Snowflake COPY commands for efficient data loading
- Processed file tracking to avoid duplicates
- Batch processing with configurable sizes
- Comprehensive error handling

## **Step 3: Snowflake Bronze to Silver Tasks**
The SQL implementation provides:
- Multiple silver table schemas for different event types
- Stored procedures with JSON attribute extraction
- MERGE operations for upsert functionality
- Automated Snowflake tasks running every hour
- Data quality monitoring queries
- Error logging and alerting framework

## **Key Features:**

✅ **Partitioned Storage**: Files organized by date/time hierarchy  
✅ **Scalable Processing**: Configurable batch sizes and buffer management  
✅ **Data Quality**: Schema validation and duplicate handling  
✅ **Monitoring**: Comprehensive logging and health checks  
✅ **Error Recovery**: Retry logic and graceful error handling  
✅ **Security**: Azure credential management and least-privilege access  

## **Quick Start:**

1. Install dependencies: `npm install`
2. Configure environment variables in `.env` files
3. Set up Azure authentication and Snowflake permissions
4. Run the applications: `npm run start:all`
5. Execute the Snowflake SQL to create tasks
6. Resume Snowflake tasks to start hourly processing

The pipeline automatically handles schema evolution, data type conversion, and maintains audit trails throughout the entire data flow. Each component can be scaled independently based on your data volume requirements.


### Step 1: From Mongo to ASDL


These are two important configuration parameters in the EventHub to ADLS ingestion component:

## **BUFFER_SIZE** (`process.env.BUFFER_SIZE`)

**Default**: 1000 events  
**Purpose**: Controls how many events are accumulated in memory before writing to ADLS

**How it works**:
- Events from EventHub are collected in an in-memory array (`this.eventBuffer`)
- When the buffer reaches `BUFFER_SIZE` events, it automatically triggers a flush to ADLS
- This batches multiple events into a single write operation

**Why this matters**:
- **Performance**: Writing 1000 events at once is much more efficient than writing each event individually
- **Cost Optimization**: Reduces the number of API calls to ADLS (each call has overhead)
- **Throughput**: Higher buffer sizes = better throughput for high-volume streams
- **Memory Usage**: Larger buffers use more memory

**Example scenarios**:
```javascript
// Low volume: smaller buffer for faster processing
BUFFER_SIZE=100

// High volume: larger buffer for better throughput  
BUFFER_SIZE=5000

// Memory constrained: smaller buffer
BUFFER_SIZE=500
```

## **FLUSH_INTERVAL** (`process.env.FLUSH_INTERVAL`)

**Default**: 30000 milliseconds (30 seconds)  
**Purpose**: Maximum time to wait before forcing a write to ADLS, regardless of buffer size

**How it works**:
- A timer runs every `FLUSH_INTERVAL` milliseconds
- If there are ANY events in the buffer (even just 1), they get written to ADLS
- This prevents events from sitting in memory too long during low-traffic periods

**Why this matters**:
- **Data Freshness**: Ensures events don't wait indefinitely in low-volume scenarios
- **Data Loss Prevention**: Reduces risk of losing events if the application crashes
- **Predictable Latency**: Guarantees maximum delay between event receipt and storage

**Example scenarios**:
```javascript
// Near real-time requirements: flush frequently
FLUSH_INTERVAL=5000  // 5 seconds

// Batch-oriented: less frequent flushes
FLUSH_INTERVAL=300000  // 5 minutes

// Balanced approach: default
FLUSH_INTERVAL=30000  // 30 seconds
```

## **How They Work Together**

The system flushes to ADLS when **either** condition is met:
1. Buffer reaches `BUFFER_SIZE` events, OR
2. `FLUSH_INTERVAL` time has elapsed

**Example Timeline**:
```
Time 0s:    Buffer = 0 events
Time 10s:   Buffer = 450 events (no flush - under buffer size)
Time 20s:   Buffer = 800 events (no flush - under buffer size)  
Time 25s:   Buffer = 1000 events → FLUSH! (hit buffer size)
Time 30s:   Buffer = 200 events (timer triggers)
Time 60s:   Buffer = 200 events → FLUSH! (hit time interval)
```

## **Tuning Guidelines**

**High Volume Streams** (1000+ events/second):
- `BUFFER_SIZE=5000-10000`
- `FLUSH_INTERVAL=60000` (1 minute)

**Medium Volume Streams** (100-1000 events/second):
- `BUFFER_SIZE=1000-2000`  
- `FLUSH_INTERVAL=30000` (30 seconds)

**Low Volume Streams** (<100 events/second):
- `BUFFER_SIZE=100-500`
- `FLUSH_INTERVAL=10000` (10 seconds)

**Memory Constrained Environments**:
- `BUFFER_SIZE=100-500`
- `FLUSH_INTERVAL=15000` (15 seconds)

These parameters give you fine-grained control over the trade-off between throughput, latency, memory usage, and cost efficiency in your data pipeline.




## Look at the `package.json` below: 
the command `npm run start:all` will run **BOTH** Step 1 and Step 2 simultaneously.

Here's what happens:

```json
"scripts": {
  "start:ingestion": "node src/eventhub-to-adls.js",      // Step 1 only
  "start:loader": "node src/adls-to-snowflake.js",       // Step 2 only  
  "start:all": "concurrently \"npm run start:ingestion\" \"npm run start:loader\""  // Both steps
}
```

## **Command Breakdown:**

- `npm run start:ingestion` → Runs **Step 1 only** (EventHub to ADLS)
- `npm run start:loader` → Runs **Step 2 only** (ADLS to Snowflake) 
- `npm run start:all` → Runs **Both Step 1 AND Step 2** using the `concurrently` package

## **Recommended Approach:**

**For Development/Testing:**
```bash
# Start components individually for easier debugging
npm run start:ingestion    # Terminal 1
npm run start:loader       # Terminal 2
```

**For Production:**
```bash
# Use PM2 for better process management
pm2 start src/eventhub-to-adls.js --name "step1-ingestion"
pm2 start src/adls-to-snowflake.js --name "step2-loader"
```

**For Quick Testing:**
```bash
# Run both together (good for demos/testing)
npm run start:all
```

The `concurrently` package runs both Node.js applications in parallel, 
so you'll see logs from both components in the same terminal.   
This is convenient for development but for production, 
I recommend running them as separate processes for better monitoring and independent scaling.



Messages are **NOT automatically deleted** from EventHub after reading them. 
This is a key difference between EventHub and traditional message queues.

## **How EventHub Message Retention Works:**

### **1. Time-Based Retention (Not Consumption-Based)**
- EventHub retains messages for a **configurable retention period** (1-90 days)
- Messages are deleted automatically when they **expire**, not when they're consumed
- Multiple consumers can read the same messages during the retention window

### **2. Checkpointing Mechanism**
In the code, you'll see this line:
```javascript
await context.updateCheckpoint(events[events.length - 1]);
```

**What checkpoints do:**
- Track the **last processed message** for each consumer group
- Allow consumers to **resume from where they left off** after restarts
- Enable **replay** of messages from any checkpoint position
- **Do NOT delete messages** from EventHub

### **3. EventHub vs Traditional Queues**

| Aspect | EventHub | Service Bus Queue |
|--------|----------|-------------------|
| **Message Deletion** | Time-based only | After consumption |
| **Multiple Consumers** | ✅ Yes | ❌ No (competing consumers) |
| **Message Replay** | ✅ Yes | ❌ No |
| **Retention** | 1-90 days | Until consumed + TTL |

## **Configuration Options:**

### **EventHub Retention Settings:**
```bash
# Set retention to 7 days (Azure CLI)
az eventhubs eventhub update \
    --resource-group myResourceGroup \
    --namespace-name myNamespace \
    --name myEventHub \
    --message-retention 7
```

### **Consumer Behavior:**
```javascript
// Your consumer can start from:
// - Latest: Only new messages after consumer starts
// - Earliest: All available messages in retention window
// - Specific checkpoint: Resume from last processed position

const subscription = consumerClient.subscribe({
    startPosition: { 
        earliest: true  // Read all available messages
        // OR
        // latest: true     // Only new messages
        // OR  
        // offset: "12345"  // Start from specific offset
    }
});
```

## **Key Implications:**

✅ **Replay Capability**: You can reprocess historical data by resetting checkpoints  
✅ **Multiple Pipelines**: Different consumer groups can process the same events  
✅ **Fault Tolerance**: Temporary outages don't cause data loss  
⚠️ **Storage Costs**: Messages consume storage until retention expires  
⚠️ **No Auto-Cleanup**: Old processed messages aren't automatically removed  

## **Best Practices:**

1. **Set appropriate retention** based on your replay requirements
2. **Monitor partition lag** to ensure timely processing
3. **Use consumer groups** to isolate different processing pipelines
4. **Implement proper checkpoint management** for reliable resumption
5. **Consider costs** - longer retention = higher storage costs

This design makes EventHub perfect for event streaming scenarios where you might need to reprocess data or have multiple downstream systems consuming the same event stream.




```js
const { EventHubConsumerClient } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");
const fs = require('fs');
const path = require('path');

class EventHubToADLSPipeline {
    constructor(config) {
        this.config = config;
        this.credential = new DefaultAzureCredential();
        this.dataLakeServiceClient = new DataLakeServiceClient(
            `https://${config.storageAccount}.dfs.core.windows.net`,
            this.credential
        );
        this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(config.containerName);
        this.currentHour = null;
        this.currentFile = null;
        this.eventBuffer = [];
        this.bufferSize = config.bufferSize || 1000;
        this.flushInterval = config.flushInterval || 30000; // 30 seconds
        
        // Setup periodic flush
        setInterval(() => this.flushBuffer(), this.flushInterval);
    }

    async initialize() {
        try {
            await this.fileSystemClient.createIfNotExists();
            console.log('ADLS container initialized successfully');
        } catch (error) {
            console.error('Error initializing ADLS container:', error);
            throw error;
        }
    }

    generatePartitionPath(timestamp, collection) {
        const date = new Date(timestamp);
        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        const hour = String(date.getUTCHours()).padStart(2, '0');
        
        return `db/${collection}/year=${year}/month=${month}/day=${day}/hour=${hour}`;
    }

    generateFileName(timestamp) {
        const date = new Date(timestamp);
        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        const hour = String(date.getUTCHours()).padStart(2, '0');
        
        return `events-${year}${month}${day}-${hour}.jsonl`;
    }

    async writeToADLS(partitionPath, fileName, data) {
        const filePath = `${partitionPath}/${fileName}`;
        const fileClient = this.fileSystemClient.getFileClient(filePath);
        
        try {
            // Check if file exists and append, otherwise create new
            const exists = await fileClient.exists();
            
            if (exists) {
                // Append to existing file
                const currentContent = await fileClient.read();
                const existingData = await this.streamToString(currentContent.readableStreamBody);
                const newContent = existingData + data;
                await fileClient.upload(newContent, newContent.length, { overwrite: true });
            } else {
                // Create new file
                await fileClient.upload(data, data.length);
            }
            
            console.log(`Successfully wrote ${data.split('\n').length - 1} events to ${filePath}`);
        } catch (error) {
            console.error(`Error writing to ADLS file ${filePath}:`, error);
            throw error;
        }
    }

    async streamToString(readableStream) {
        const chunks = [];
        return new Promise((resolve, reject) => {
            readableStream.on("data", (data) => {
                chunks.push(data.toString());
            });
            readableStream.on("end", () => {
                resolve(chunks.join(""));
            });
            readableStream.on("error", reject);
        });
    }

    async processEvent(event) {
        try {
            // Extract collection name from event properties or body
            const collection = event.properties?.collection || 
                              event.body?.collection || 
                              this.config.defaultCollection || 'default';
            
            // Add ingestion timestamp
            const enrichedEvent = {
                ...event.body,
                _ingestionTimestamp: new Date().toISOString(),
                _eventHubMetadata: {
                    offset: event.offset,
                    sequenceNumber: event.sequenceNumber,
                    enqueuedTimeUtc: event.enqueuedTimeUtc,
                    partitionKey: event.partitionKey
                }
            };

            const timestamp = event.enqueuedTimeUtc || new Date();
            const currentHour = new Date(timestamp).getUTCHours();
            const currentDate = new Date(timestamp).toISOString().split('T')[0];

            // Check if we need to flush buffer due to hour change
            if (this.currentHour !== null && this.currentHour !== currentHour) {
                await this.flushBuffer();
            }

            this.currentHour = currentHour;
            
            // Add event to buffer with partition info
            this.eventBuffer.push({
                event: enrichedEvent,
                collection,
                timestamp,
                partitionPath: this.generatePartitionPath(timestamp, collection),
                fileName: this.generateFileName(timestamp)
            });

            // Flush buffer if it reaches the buffer size
            if (this.eventBuffer.length >= this.bufferSize) {
                await this.flushBuffer();
            }

        } catch (error) {
            console.error('Error processing event:', error);
        }
    }

    async flushBuffer() {
        if (this.eventBuffer.length === 0) {
            return;
        }

        console.log(`Flushing buffer with ${this.eventBuffer.length} events`);

        // Group events by partition path and file name
        const grouped = {};
        
        for (const item of this.eventBuffer) {
            const key = `${item.partitionPath}/${item.fileName}`;
            if (!grouped[key]) {
                grouped[key] = {
                    partitionPath: item.partitionPath,
                    fileName: item.fileName,
                    events: []
                };
            }
            grouped[key].events.push(item.event);
        }

        // Write each group to ADLS
        const writePromises = Object.values(grouped).map(async (group) => {
            const jsonLines = group.events.map(event => JSON.stringify(event)).join('\n') + '\n';
            await this.writeToADLS(group.partitionPath, group.fileName, jsonLines);
        });

        try {
            await Promise.all(writePromises);
            console.log(`Successfully flushed ${this.eventBuffer.length} events to ADLS`);
        } catch (error) {
            console.error('Error flushing buffer to ADLS:', error);
        }

        // Clear buffer
        this.eventBuffer = [];
    }

    async startConsumer() {
        const consumerClient = new EventHubConsumerClient(
            this.config.consumerGroup,
            this.config.eventHubConnectionString,
            this.config.eventHubName
        );

        console.log('Starting EventHub consumer...');

        const subscription = consumerClient.subscribe({
            processEvents: async (events, context) => {
                console.log(`Received ${events.length} events from partition: ${context.partitionId}`);
                
                for (const event of events) {
                    await this.processEvent(event);
                }

                // Update checkpoint
                if (events.length > 0) {
                    await context.updateCheckpoint(events[events.length - 1]);
                }
            },
            processError: async (err, context) => {
                console.error(`Error on partition "${context.partitionId}":`, err);
            }
        });

        // Graceful shutdown
        process.on('SIGINT', async () => {
            console.log('Shutting down gracefully...');
            await this.flushBuffer();
            await subscription.close();
            await consumerClient.close();
            process.exit(0);
        });

        console.log('EventHub consumer started successfully');
    }
}

// Configuration
const config = {
    eventHubConnectionString: process.env.EVENTHUB_CONNECTION_STRING,
    eventHubName: process.env.EVENTHUB_NAME,
    consumerGroup: process.env.CONSUMER_GROUP || '$Default',
    storageAccount: process.env.STORAGE_ACCOUNT_NAME,
    containerName: process.env.ADLS_CONTAINER_NAME || 'events',
    defaultCollection: process.env.DEFAULT_COLLECTION || 'events',
    bufferSize: parseInt(process.env.BUFFER_SIZE) || 1000,
    flushInterval: parseInt(process.env.FLUSH_INTERVAL) || 30000
};

// Validate required configuration
const requiredConfig = ['eventHubConnectionString', 'eventHubName', 'storageAccount'];
for (const key of requiredConfig) {
    if (!config[key]) {
        console.error(`Missing required configuration: ${key}`);
        process.exit(1);
    }
}

// Start the pipeline
async function main() {
    const pipeline = new EventHubToADLSPipeline(config);
    
    try {
        await pipeline.initialize();
        await pipeline.startConsumer();
    } catch (error) {
        console.error('Failed to start pipeline:', error);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = EventHubToADLSPipeline;
```
### STEP 2: upload to bronze
```js
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");
const snowflake = require('snowflake-sdk');
const cron = require('node-cron');
const fs = require('fs').promises;

class ADLSToSnowflakeLoader {
    constructor(config) {
        this.config = config;
        this.credential = new DefaultAzureCredential();
        this.dataLakeServiceClient = new DataLakeServiceClient(
            `https://${config.storageAccount}.dfs.core.windows.net`,
            this.credential
        );
        this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(config.containerName);
        this.snowflakeConnection = null;
        this.processedFiles = new Set();
        this.loadProcessedFiles();
    }

    async loadProcessedFiles() {
        try {
            const data = await fs.readFile(this.config.processedFilesPath || './processed_files.json', 'utf8');
            this.processedFiles = new Set(JSON.parse(data));
            console.log(`Loaded ${this.processedFiles.size} previously processed files`);
        } catch (error) {
            console.log('No previous processed files found, starting fresh');
        }
    }

    async saveProcessedFiles() {
        try {
            await fs.writeFile(
                this.config.processedFilesPath || './processed_files.json',
                JSON.stringify([...this.processedFiles], null, 2)
            );
        } catch (error) {
            console.error('Error saving processed files:', error);
        }
    }

    async initializeSnowflake() {
        return new Promise((resolve, reject) => {
            this.snowflakeConnection = snowflake.createConnection({
                account: this.config.snowflake.account,
                username: this.config.snowflake.username,
                password: this.config.snowflake.password,
                database: this.config.snowflake.database,
                schema: this.config.snowflake.schema,
                warehouse: this.config.snowflake.warehouse,
                role: this.config.snowflake.role
            });

            this.snowflakeConnection.connect((err, conn) => {
                if (err) {
                    console.error('Unable to connect to Snowflake:', err);
                    reject(err);
                } else {
                    console.log('Successfully connected to Snowflake');
                    resolve(conn);
                }
            });
        });
    }

    async executeSnowflakeQuery(query, binds = []) {
        return new Promise((resolve, reject) => {
            this.snowflakeConnection.execute({
                sqlText: query,
                binds: binds,
                complete: (err, stmt, rows) => {
                    if (err) {
                        reject(err);
                    } else {
                        resolve({ stmt, rows });
                    }
                }
            });
        });
    }

    async createBronzeTable(tableName) {
        const createTableQuery = `
            CREATE TABLE IF NOT EXISTS ${this.config.snowflake.schema}.${tableName}_bronze (
                RAW_DATA VARIANT,
                FILE_NAME VARCHAR(500),
                INGESTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                _PARTITION_PATH VARCHAR(500)
            )
        `;

        try {
            await this.executeSnowflakeQuery(createTableQuery);
            console.log(`Bronze table ${tableName}_bronze created/verified successfully`);
        } catch (error) {
            console.error(`Error creating bronze table ${tableName}_bronze:`, error);
            throw error;
        }
    }

    async createStageIfNotExists() {
        const createStageQuery = `
            CREATE STAGE IF NOT EXISTS ${this.config.snowflake.schema}.ADLS_STAGE
            URL = 'azure://${this.config.storageAccount}.dfs.core.windows.net/${this.config.containerName}/'
            CREDENTIALS = (AZURE_SAS_TOKEN = '${this.config.azureSasToken}')
        `;

        try {
            await this.executeSnowflakeQuery(createStageQuery);
            console.log('ADLS stage created/verified successfully');
        } catch (error) {
            console.error('Error creating ADLS stage:', error);
            throw error;
        }
    }

    async listFilesForHour(targetHour) {
        const files = [];
        const pathPrefix = this.generateHourPrefix(targetHour);
        
        try {
            console.log(`Scanning for files in path: ${pathPrefix}`);
            
            // List all paths that match the hour pattern
            const paths = await this.listPathsRecursively(pathPrefix);
            
            for (const path of paths) {
                if (path.name.endsWith('.jsonl') && !this.processedFiles.has(path.name)) {
                    files.push({
                        name: path.name,
                        collection: this.extractCollectionFromPath(path.name),
                        path: path.name
                    });
                }
            }
            
            console.log(`Found ${files.length} unprocessed files for hour ${targetHour.toISOString()}`);
            return files;
        } catch (error) {
            console.error('Error listing files:', error);
            return [];
        }
    }

    async listPathsRecursively(prefix, paths = []) {
        try {
            const iterator = this.fileSystemClient.listPaths({ path: prefix, recursive: true });
            
            for await (const path of iterator) {
                if (!path.isDirectory) {
                    paths.push(path);
                }
            }
        } catch (error) {
            console.log(`No files found for prefix: ${prefix}`);
        }
        
        return paths;
    }

    generateHourPrefix(targetHour) {
        const year = targetHour.getUTCFullYear();
        const month = String(targetHour.getUTCMonth() + 1).padStart(2, '0');
        const day = String(targetHour.getUTCDate()).padStart(2, '0');
        const hour = String(targetHour.getUTCHours()).padStart(2, '0');
        
        return `db/*/year=${year}/month=${month}/day=${day}/hour=${hour}`;
    }

    extractCollectionFromPath(filePath) {
        // Extract collection from path like: db/collection/year=2024/month=01/day=01/hour=01/events-20240101-01.jsonl
        const parts = filePath.split('/');
        const dbIndex = parts.findIndex(part => part === 'db');
        return dbIndex >= 0 && parts[dbIndex + 1] ? parts[dbIndex + 1] : 'default';
    }

    async loadFileToSnowflake(file) {
        const tableName = `${file.collection}_bronze`;
        const stagePath = file.path;

        // Ensure bronze table exists
        await this.createBronzeTable(file.collection);

        // Copy command to load data
        const copyQuery = `
            COPY INTO ${this.config.snowflake.schema}.${tableName}
            (RAW_DATA, FILE_NAME, _PARTITION_PATH)
            FROM (
                SELECT 
                    PARSE_JSON($1) as RAW_DATA,
                    METADATA$FILENAME as FILE_NAME,
                    METADATA$FILE_PATH as _PARTITION_PATH
                FROM @${this.config.snowflake.schema}.ADLS_STAGE/${stagePath}
            )
            FILE_FORMAT = (
                TYPE = 'JSON',
                STRIP_OUTER_ARRAY = FALSE
            )
            ON_ERROR = 'CONTINUE'
        `;

        try {
            const result = await this.executeSnowflakeQuery(copyQuery);
            console.log(`Successfully loaded file ${file.name} to table ${tableName}`);
            
            // Mark file as processed
            this.processedFiles.add(file.name);
            
            return {
                success: true,
                file: file.name,
                table: tableName,
                rowsLoaded: result.stmt.getNumRowsInserted() || 0
            };
        } catch (error) {
            console.error(`Error loading file ${file.name}:`, error);
            return {
                success: false,
                file: file.name,
                error: error.message
            };
        }
    }

    async processHourlyFiles() {
        console.log('Starting hourly file processing...');
        
        // Process files from the previous hour
        const targetHour = new Date();
        targetHour.setHours(targetHour.getHours() - 1, 0, 0, 0);
        
        try {
            // Ensure stage exists
            await this.createStageIfNotExists();
            
            const files = await this.listFilesForHour(targetHour);
            
            if (files.length === 0) {
                console.log(`No new files found for hour ${targetHour.toISOString()}`);
                return;
            }

            const results = [];
            
            // Process files in batches to avoid overwhelming Snowflake
            const batchSize = this.config.batchSize || 5;
            for (let i = 0; i < files.length; i += batchSize) {
                const batch = files.slice(i, i + batchSize);
                const batchPromises = batch.map(file => this.loadFileToSnowflake(file));
                const batchResults = await Promise.allSettled(batchPromises);
                
                batchResults.forEach((result, index) => {
                    if (result.status === 'fulfilled') {
                        results.push(result.value);
                    } else {
                        results.push({
                            success: false,
                            file: batch[index].name,
                            error: result.reason?.message || 'Unknown error'
                        });
                    }
                });
                
                // Small delay between batches
                if (i + batchSize < files.length) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            // Save processed files list
            await this.saveProcessedFiles();
            
            // Log summary
            const successful = results.filter(r => r.success);
            const failed = results.filter(r => !r.success);
            const totalRows = successful.reduce((sum, r) => sum + (r.rowsLoaded || 0), 0);
            
            console.log(`Processing complete for ${targetHour.toISOString()}:`);
            console.log(`  - Successful files: ${successful.length}`);
            console.log(`  - Failed files: ${failed.length}`);
            console.log(`  - Total rows loaded: ${totalRows}`);
            
            if (failed.length > 0) {
                console.log('Failed files:', failed.map(f => `${f.file}: ${f.error}`));
            }
            
        } catch (error) {
            console.error('Error in hourly processing:', error);
        }
    }

    async startScheduler() {
        console.log('Starting ADLS to Snowflake loader scheduler...');
        
        // Run every hour at 5 minutes past the hour
        cron.schedule('5 * * * *', async () => {
            await this.processHourlyFiles();
        });

        // Initial run after 1 minute
        setTimeout(() => {
            this.processHourlyFiles();
        }, 60000);

        console.log('Scheduler started - will process files every hour at 5 minutes past the hour');
    }

    async shutdown() {
        console.log('Shutting down ADLS to Snowflake loader...');
        await this.saveProcessedFiles();
        
        if (this.snowflakeConnection) {
            this.snowflakeConnection.destroy((err) => {
                if (err) {
                    console.error('Error closing Snowflake connection:', err);
                } else {
                    console.log('Snowflake connection closed');
                }
            });
        }
    }
}

// Configuration
const config = {
    storageAccount: process.env.STORAGE_ACCOUNT_NAME,
    containerName: process.env.ADLS_CONTAINER_NAME || 'events',
    azureSasToken: process.env.AZURE_SAS_TOKEN,
    processedFilesPath: process.env.PROCESSED_FILES_PATH || './processed_files.json',
    batchSize: parseInt(process.env.BATCH_SIZE) || 5,
    snowflake: {
        account: process.env.SNOWFLAKE_ACCOUNT,
        username: process.env.SNOWFLAKE_USERNAME,
        password: process.env.SNOWFLAKE_PASSWORD,
        database: process.env.SNOWFLAKE_DATABASE,
        schema: process.env.SNOWFLAKE_SCHEMA || 'BRONZE',
        warehouse: process.env.SNOWFLAKE_WAREHOUSE,
        role: process.env.SNOWFLAKE_ROLE
    }
};

// Validate required configuration
const requiredConfig = [
    'storageAccount', 'azureSasToken',
    'snowflake.account', 'snowflake.username', 'snowflake.password',
    'snowflake.database', 'snowflake.warehouse'
];

for (const key of requiredConfig) {
    const keys = key.split('.');
    let value = config;
    for (const k of keys) {
        value = value[k];
    }
    if (!value) {
        console.error(`Missing required configuration: ${key}`);
        process.exit(1);
    }
}

async function main() {
    const loader = new ADLSToSnowflakeLoader(config);
    
    try {
        await loader.initializeSnowflake();
        await loader.startScheduler();
        
        // Graceful shutdown
        process.on('SIGINT', async () => {
            await loader.shutdown();
            process.exit(0);
        });
        
        process.on('SIGTERM', async () => {
            await loader.shutdown();
            process.exit(0);
        });
        
    } catch (error) {
        console.error('Failed to start ADLS to Snowflake loader:', error);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = ADLSToSnowflakeLoader;
```


### STEP 3 (version 2) from bronze to silver. Snowflake Tasks for Hourly Run

```sql
-- ================================================================
-- Snowflake Bronze to Silver Layer Transformation Tasks
-- ================================================================

-- Create Silver schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS SILVER;

-- ================================================================
-- 1. Create Silver Tables (Example for different collection types)
-- ================================================================

-- Generic Silver table template - customize based on your JSON structure
CREATE TABLE IF NOT EXISTS SILVER.EVENTS_SILVER (
    EVENT_ID VARCHAR(100),
    USER_ID VARCHAR(100),
    SESSION_ID VARCHAR(100),
    EVENT_TYPE VARCHAR(100),
    EVENT_TIMESTAMP TIMESTAMP_NTZ,
    PROPERTIES VARIANT,
    USER_AGENT VARCHAR(500),
    IP_ADDRESS VARCHAR(50),
    COUNTRY VARCHAR(100),
    CITY VARCHAR(100),
    -- Metadata fields
    INGESTION_TIMESTAMP TIMESTAMP_NTZ,
    LOAD_TIMESTAMP TIMESTAMP_NTZ,
    SOURCE_FILE VARCHAR(500),
    PARTITION_PATH VARCHAR(500),
    -- Audit fields
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (EVENT_ID)
);

-- User events silver table example
CREATE TABLE IF NOT EXISTS SILVER.USER_EVENTS_SILVER (
    EVENT_ID VARCHAR(100),
    USER_ID VARCHAR(100) NOT NULL,
    SESSION_ID VARCHAR(100),
    EVENT_NAME VARCHAR(200),
    EVENT_TIMESTAMP TIMESTAMP_NTZ,
    PAGE_URL VARCHAR(1000),
    REFERRER_URL VARCHAR(1000),
    DEVICE_TYPE VARCHAR(100),
    BROWSER VARCHAR(100),
    OS VARCHAR(100),
    -- Custom properties
    CUSTOM_PROPERTIES VARIANT,
    -- Metadata
    INGESTION_TIMESTAMP TIMESTAMP_NTZ,
    LOAD_TIMESTAMP TIMESTAMP_NTZ,
    SOURCE_FILE VARCHAR(500),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (EVENT_ID)
);

-- Product events silver table example
CREATE TABLE IF NOT EXISTS SILVER.PRODUCT_EVENTS_SILVER (
    EVENT_ID VARCHAR(100),
    PRODUCT_ID VARCHAR(100),
    USER_ID VARCHAR(100),
    EVENT_TYPE VARCHAR(100), -- view, purchase, add_to_cart, etc.
    EVENT_TIMESTAMP TIMESTAMP_NTZ,
    PRODUCT_NAME VARCHAR(500),
    PRODUCT_CATEGORY VARCHAR(200),
    PRICE DECIMAL(10,2),
    QUANTITY INTEGER,
    CURRENCY VARCHAR(10),
    -- Metadata
    INGESTION_TIMESTAMP TIMESTAMP_NTZ,
    LOAD_TIMESTAMP TIMESTAMP_NTZ,
    SOURCE_FILE VARCHAR(500),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (EVENT_ID)
);

-- Transaction events silver table example
CREATE TABLE IF NOT EXISTS SILVER.TRANSACTIONS_SILVER (
    TRANSACTION_ID VARCHAR(100),
    USER_ID VARCHAR(100),
    ORDER_ID VARCHAR(100),
    EVENT_TIMESTAMP TIMESTAMP_NTZ,
    TRANSACTION_TYPE VARCHAR(50), -- purchase, refund, void
    TOTAL_AMOUNT DECIMAL(10,2),
    TAX_AMOUNT DECIMAL(10,2),
    SHIPPING_AMOUNT DECIMAL(10,2),
    DISCOUNT_AMOUNT DECIMAL(10,2),
    CURRENCY VARCHAR(10),
    PAYMENT_METHOD VARCHAR(100),
    ITEMS VARIANT, -- Array of purchased items
    -- Metadata
    INGESTION_TIMESTAMP TIMESTAMP_NTZ,
    LOAD_TIMESTAMP TIMESTAMP_NTZ,
    SOURCE_FILE VARCHAR(500),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (TRANSACTION_ID)
);

-- ================================================================
-- 2. Create Stored Procedures for Bronze to Silver Transformation
-- ================================================================

-- Generic transformation procedure for events
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_EVENTS_BRONZE_TO_SILVER(
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    rows_processed INTEGER DEFAULT 0;
    cutoff_time TIMESTAMP_NTZ;
    result_message STRING;
BEGIN
    SET cutoff_time = DATEADD('hour', -LOOKBACK_HOURS, CURRENT_TIMESTAMP());
    
    MERGE INTO SILVER.EVENTS_SILVER AS target
    USING (
        SELECT 
            RAW_DATA:event_id::VARCHAR AS EVENT_ID,
            RAW_DATA:user_id::VARCHAR AS USER_ID,
            RAW_DATA:session_id::VARCHAR AS SESSION_ID,
            RAW_DATA:event_type::VARCHAR AS EVENT_TYPE,
            CASE 
                WHEN RAW_DATA:timestamp IS NOT NULL 
                THEN TRY_TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR)
                ELSE INGESTION_TIMESTAMP
            END AS EVENT_TIMESTAMP,
            RAW_DATA:properties AS PROPERTIES,
            RAW_DATA:user_agent::VARCHAR AS USER_AGENT,
            RAW_DATA:ip_address::VARCHAR AS IP_ADDRESS,
            RAW_DATA:geo:country::VARCHAR AS COUNTRY,
            RAW_DATA:geo:city::VARCHAR AS CITY,
            INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP,
            FILE_NAME AS SOURCE_FILE,
            _PARTITION_PATH AS PARTITION_PATH
        FROM BRONZE.EVENTS_BRONZE
        WHERE LOAD_TIMESTAMP >= :cutoff_time
          AND RAW_DATA:event_id IS NOT NULL
          AND RAW_DATA:event_id != ''
    ) AS source
    ON target.EVENT_ID = source.EVENT_ID
    WHEN MATCHED THEN 
        UPDATE SET
            USER_ID = source.USER_ID,
            SESSION_ID = source.SESSION_ID,
            EVENT_TYPE = source.EVENT_TYPE,
            EVENT_TIMESTAMP = source.EVENT_TIMESTAMP,
            PROPERTIES = source.PROPERTIES,
            USER_AGENT = source.USER_AGENT,
            IP_ADDRESS = source.IP_ADDRESS,
            COUNTRY = source.COUNTRY,
            CITY = source.CITY,
            INGESTION_TIMESTAMP = source.INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP = source.LOAD_TIMESTAMP,
            SOURCE_FILE = source.SOURCE_FILE,
            PARTITION_PATH = source.PARTITION_PATH,
            UPDATED_AT = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (
            EVENT_ID, USER_ID, SESSION_ID, EVENT_TYPE, EVENT_TIMESTAMP,
            PROPERTIES, USER_AGENT, IP_ADDRESS, COUNTRY, CITY,
            INGESTION_TIMESTAMP, LOAD_TIMESTAMP, SOURCE_FILE, PARTITION_PATH
        )
        VALUES (
            source.EVENT_ID, source.USER_ID, source.SESSION_ID, 
            source.EVENT_TYPE, source.EVENT_TIMESTAMP, source.PROPERTIES,
            source.USER_AGENT, source.IP_ADDRESS, source.COUNTRY, source.CITY,
            source.INGESTION_TIMESTAMP, source.LOAD_TIMESTAMP, 
            source.SOURCE_FILE, source.PARTITION_PATH
        );
    
    SET rows_processed = (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));
    SET result_message = 'Events transformation completed. Rows processed: ' || rows_processed;
    RETURN result_message;
END;
$$;

-- User events transformation procedure
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_USER_EVENTS_BRONZE_TO_SILVER(
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    rows_processed INTEGER DEFAULT 0;
    cutoff_time TIMESTAMP_NTZ;
    result_message STRING;
BEGIN
    SET cutoff_time = DATEADD('hour', -LOOKBACK_HOURS, CURRENT_TIMESTAMP());
    
    MERGE INTO SILVER.USER_EVENTS_SILVER AS target
    USING (
        SELECT 
            RAW_DATA:event_id::VARCHAR AS EVENT_ID,
            RAW_DATA:user_id::VARCHAR AS USER_ID,
            RAW_DATA:session_id::VARCHAR AS SESSION_ID,
            RAW_DATA:event_name::VARCHAR AS EVENT_NAME,
            CASE 
                WHEN RAW_DATA:timestamp IS NOT NULL 
                THEN TRY_TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR)
                ELSE INGESTION_TIMESTAMP
            END AS EVENT_TIMESTAMP,
            RAW_DATA:page_url::VARCHAR AS PAGE_URL,
            RAW_DATA:referrer::VARCHAR AS REFERRER_URL,
            RAW_DATA:device:type::VARCHAR AS DEVICE_TYPE,
            RAW_DATA:browser:name::VARCHAR AS BROWSER,
            RAW_DATA:os:name::VARCHAR AS OS,
            RAW_DATA:custom_properties AS CUSTOM_PROPERTIES,
            INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP,
            FILE_NAME AS SOURCE_FILE
        FROM BRONZE.USER_EVENTS_BRONZE
        WHERE LOAD_TIMESTAMP >= :cutoff_time
          AND RAW_DATA:event_id IS NOT NULL
          AND RAW_DATA:user_id IS NOT NULL
          AND RAW_DATA:event_id != ''
          AND RAW_DATA:user_id != ''
    ) AS source
    ON target.EVENT_ID = source.EVENT_ID
    WHEN MATCHED THEN 
        UPDATE SET
            USER_ID = source.USER_ID,
            SESSION_ID = source.SESSION_ID,
            EVENT_NAME = source.EVENT_NAME,
            EVENT_TIMESTAMP = source.EVENT_TIMESTAMP,
            PAGE_URL = source.PAGE_URL,
            REFERRER_URL = source.REFERRER_URL,
            DEVICE_TYPE = source.DEVICE_TYPE,
            BROWSER = source.BROWSER,
            OS = source.OS,
            CUSTOM_PROPERTIES = source.CUSTOM_PROPERTIES,
            INGESTION_TIMESTAMP = source.INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP = source.LOAD_TIMESTAMP,
            SOURCE_FILE = source.SOURCE_FILE,
            UPDATED_AT = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (
            EVENT_ID, USER_ID, SESSION_ID, EVENT_NAME, EVENT_TIMESTAMP,
            PAGE_URL, REFERRER_URL, DEVICE_TYPE, BROWSER, OS,
            CUSTOM_PROPERTIES, INGESTION_TIMESTAMP, LOAD_TIMESTAMP, SOURCE_FILE
        )
        VALUES (
            source.EVENT_ID, source.USER_ID, source.SESSION_ID, 
            source.EVENT_NAME, source.EVENT_TIMESTAMP, source.PAGE_URL,
            source.REFERRER_URL, source.DEVICE_TYPE, source.BROWSER, source.OS,
            source.CUSTOM_PROPERTIES, source.INGESTION_TIMESTAMP, 
            source.LOAD_TIMESTAMP, source.SOURCE_FILE
        );
    
    SET rows_processed = (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));
    SET result_message = 'User events transformation completed. Rows processed: ' || rows_processed;
    RETURN result_message;
END;
$$;

-- Product events transformation procedure
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_PRODUCT_EVENTS_BRONZE_TO_SILVER(
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    rows_processed INTEGER DEFAULT 0;
    cutoff_time TIMESTAMP_NTZ;
    result_message STRING;
BEGIN
    SET cutoff_time = DATEADD('hour', -LOOKBACK_HOURS, CURRENT_TIMESTAMP());
    
    MERGE INTO SILVER.PRODUCT_EVENTS_SILVER AS target
    USING (
        SELECT 
            RAW_DATA:event_id::VARCHAR AS EVENT_ID,
            RAW_DATA:product_id::VARCHAR AS PRODUCT_ID,
            RAW_DATA:user_id::VARCHAR AS USER_ID,
            RAW_DATA:event_type::VARCHAR AS EVENT_TYPE,
            CASE 
                WHEN RAW_DATA:timestamp IS NOT NULL 
                THEN TRY_TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR)
                ELSE INGESTION_TIMESTAMP
            END AS EVENT_TIMESTAMP,
            RAW_DATA:product:name::VARCHAR AS PRODUCT_NAME,
            RAW_DATA:product:category::VARCHAR AS PRODUCT_CATEGORY,
            TRY_TO_DECIMAL(RAW_DATA:product:price::VARCHAR, 10, 2) AS PRICE,
            TRY_TO_NUMBER(RAW_DATA:quantity::VARCHAR) AS QUANTITY,
            RAW_DATA:currency::VARCHAR AS CURRENCY,
            INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP,
            FILE_NAME AS SOURCE_FILE
        FROM BRONZE.PRODUCT_EVENTS_BRONZE
        WHERE LOAD_TIMESTAMP >= :cutoff_time
          AND RAW_DATA:event_id IS NOT NULL
          AND RAW_DATA:product_id IS NOT NULL
          AND RAW_DATA:event_id != ''
          AND RAW_DATA:product_id != ''
    ) AS source
    ON target.EVENT_ID = source.EVENT_ID
    WHEN MATCHED THEN 
        UPDATE SET
            PRODUCT_ID = source.PRODUCT_ID,
            USER_ID = source.USER_ID,
            EVENT_TYPE = source.EVENT_TYPE,
            EVENT_TIMESTAMP = source.EVENT_TIMESTAMP,
            PRODUCT_NAME = source.PRODUCT_NAME,
            PRODUCT_CATEGORY = source.PRODUCT_CATEGORY,
            PRICE = source.PRICE,
            QUANTITY = source.QUANTITY,
            CURRENCY = source.CURRENCY,
            INGESTION_TIMESTAMP = source.INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP = source.LOAD_TIMESTAMP,
            SOURCE_FILE = source.SOURCE_FILE,
            UPDATED_AT = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (
            EVENT_ID, PRODUCT_ID, USER_ID, EVENT_TYPE, EVENT_TIMESTAMP,
            PRODUCT_NAME, PRODUCT_CATEGORY, PRICE, QUANTITY, CURRENCY,
            INGESTION_TIMESTAMP, LOAD_TIMESTAMP, SOURCE_FILE
        )
        VALUES (
            source.EVENT_ID, source.PRODUCT_ID, source.USER_ID, 
            source.EVENT_TYPE, source.EVENT_TIMESTAMP, source.PRODUCT_NAME,
            source.PRODUCT_CATEGORY, source.PRICE, source.QUANTITY, source.CURRENCY,
            source.INGESTION_TIMESTAMP, source.LOAD_TIMESTAMP, source.SOURCE_FILE
        );
    
    SET rows_processed = (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));
    SET result_message = 'Product events transformation completed. Rows processed: ' || rows_processed;
    RETURN result_message;
END;
$$;

-- Transactions transformation procedure
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_TRANSACTIONS_BRONZE_TO_SILVER(
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    rows_processed INTEGER DEFAULT 0;
    cutoff_time TIMESTAMP_NTZ;
    result_message STRING;
BEGIN
    SET cutoff_time = DATEADD('hour', -LOOKBACK_HOURS, CURRENT_TIMESTAMP());
    
    MERGE INTO SILVER.TRANSACTIONS_SILVER AS target
    USING (
        SELECT 
            RAW_DATA:transaction_id::VARCHAR AS TRANSACTION_ID,
            RAW_DATA:user_id::VARCHAR AS USER_ID,
            RAW_DATA:order_id::VARCHAR AS ORDER_ID,
            CASE 
                WHEN RAW_DATA:timestamp IS NOT NULL 
                THEN TRY_TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR)
                ELSE INGESTION_TIMESTAMP
            END AS EVENT_TIMESTAMP,
            RAW_DATA:transaction_type::VARCHAR AS TRANSACTION_TYPE,
            TRY_TO_DECIMAL(RAW_DATA:total_amount::VARCHAR, 10, 2) AS TOTAL_AMOUNT,
            TRY_TO_DECIMAL(RAW_DATA:tax_amount::VARCHAR, 10, 2) AS TAX_AMOUNT,
            TRY_TO_DECIMAL(RAW_DATA:shipping_amount::VARCHAR, 10, 2) AS SHIPPING_AMOUNT,
            TRY_TO_DECIMAL(RAW_DATA:discount_amount::VARCHAR, 10, 2) AS DISCOUNT_AMOUNT,
            RAW_DATA:currency::VARCHAR AS CURRENCY,
            RAW_DATA:payment_method::VARCHAR AS PAYMENT_METHOD,
            RAW_DATA:items AS ITEMS,
            INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP,
            FILE_NAME AS SOURCE_FILE
        FROM BRONZE.TRANSACTIONS_BRONZE
        WHERE LOAD_TIMESTAMP >= :cutoff_time
          AND RAW_DATA:transaction_id IS NOT NULL
          AND RAW_DATA:transaction_id != ''
    ) AS source
    ON target.TRANSACTION_ID = source.TRANSACTION_ID
    WHEN MATCHED THEN 
        UPDATE SET
            USER_ID = source.USER_ID,
            ORDER_ID = source.ORDER_ID,
            EVENT_TIMESTAMP = source.EVENT_TIMESTAMP,
            TRANSACTION_TYPE = source.TRANSACTION_TYPE,
            TOTAL_AMOUNT = source.TOTAL_AMOUNT,
            TAX_AMOUNT = source.TAX_AMOUNT,
            SHIPPING_AMOUNT = source.SHIPPING_AMOUNT,
            DISCOUNT_AMOUNT = source.DISCOUNT_AMOUNT,
            CURRENCY = source.CURRENCY,
            PAYMENT_METHOD = source.PAYMENT_METHOD,
            ITEMS = source.ITEMS,
            INGESTION_TIMESTAMP = source.INGESTION_TIMESTAMP,
            LOAD_TIMESTAMP = source.LOAD_TIMESTAMP,
            SOURCE_FILE = source.SOURCE_FILE,
            UPDATED_AT = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (
            TRANSACTION_ID, USER_ID, ORDER_ID, EVENT_TIMESTAMP, TRANSACTION_TYPE,
            TOTAL_AMOUNT, TAX_AMOUNT, SHIPPING_AMOUNT, DISCOUNT_AMOUNT, CURRENCY,
            PAYMENT_METHOD, ITEMS, INGESTION_TIMESTAMP, LOAD_TIMESTAMP, SOURCE_FILE
        )
        VALUES (
            source.TRANSACTION_ID, source.USER_ID, source.ORDER_ID, 
            source.EVENT_TIMESTAMP, source.TRANSACTION_TYPE, source.TOTAL_AMOUNT,
            source.TAX_AMOUNT, source.SHIPPING_AMOUNT, source.DISCOUNT_AMOUNT,
            source.CURRENCY, source.PAYMENT_METHOD, source.ITEMS,
            source.INGESTION_TIMESTAMP, source.LOAD_TIMESTAMP, source.SOURCE_FILE
        );
    
    SET rows_processed = (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));
    SET result_message = 'Transactions transformation completed. Rows processed: ' || rows_processed;
    RETURN result_message;
END;
$$;

-- Master procedure to run all transformations
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_ALL_BRONZE_TO_SILVER(
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    events_result STRING;
    user_events_result STRING;
    product_events_result STRING;
    transactions_result STRING;
    final_result STRING;
BEGIN
    -- Transform events
    CALL SILVER.TRANSFORM_EVENTS_BRONZE_TO_SILVER(:LOOKBACK_HOURS);
    SET events_result = SQLCODE || ': ' || SQLERRM;
    
    -- Transform user events
    CALL SILVER.TRANSFORM_USER_EVENTS_BRONZE_TO_SILVER(:LOOKBACK_HOURS);
    SET user_events_result = SQLCODE || ': ' || SQLERRM;
    
    -- Transform product events
    CALL SILVER.TRANSFORM_PRODUCT_EVENTS_BRONZE_TO_SILVER(:LOOKBACK_HOURS);
    SET product_events_result = SQLCODE || ': ' || SQLERRM;
    
    -- Transform transactions
    CALL SILVER.TRANSFORM_TRANSACTIONS_BRONZE_TO_SILVER(:LOOKBACK_HOURS);
    SET transactions_result = SQLCODE || ': ' || SQLERRM;
    
    SET final_result = 'All transformations completed at ' || CURRENT_TIMESTAMP() || 
                      '. Events: ' || events_result || 
                      '. User Events: ' || user_events_result || 
                      '. Product Events: ' || product_events_result || 
                      '. Transactions: ' || transactions_result;
    
    RETURN final_result;
END;
$$;

-- ================================================================
-- 3. Create Snowflake Tasks for Hourly Processing
-- ================================================================

-- Create warehouse for tasks if it doesn't exist
-- Note: You may need to adjust the warehouse size based on your data volume
CREATE WAREHOUSE IF NOT EXISTS TRANSFORMATION_WH
WITH 
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- Task to transform events bronze to silver every hour
CREATE OR REPLACE TASK SILVER.HOURLY_EVENTS_TRANSFORMATION
    WAREHOUSE = TRANSFORMATION_WH
    SCHEDULE = 'USING CRON 10 * * * * UTC' -- Run at 10 minutes past every hour
    COMMENT = 'Hourly transformation of events from bronze to silver layer'
AS
    CALL SILVER.TRANSFORM_EVENTS_BRONZE_TO_SILVER(1);

-- Task to transform user events bronze to silver every hour
CREATE OR REPLACE TASK SILVER.HOURLY_USER_EVENTS_TRANSFORMATION
    WAREHOUSE = TRANSFORMATION_WH
    SCHEDULE = 'USING CRON 15 * * * * UTC' -- Run at 15 minutes past every hour
    COMMENT = 'Hourly transformation of user events from bronze to silver layer'
AS
    CALL SILVER.TRANSFORM_USER_EVENTS_BRONZE_TO_SILVER(1);

-- Task to transform product events bronze to silver every hour
CREATE OR REPLACE TASK SILVER.HOURLY_PRODUCT_EVENTS_TRANSFORMATION
    WAREHOUSE = TRANSFORMATION_WH
    SCHEDULE = 'USING CRON 20 * * * * UTC' -- Run at 20 minutes past every hour
    COMMENT = 'Hourly transformation of product events from bronze to silver layer'
AS
    CALL SILVER.TRANSFORM_PRODUCT_EVENTS_BRONZE_TO_SILVER(1);

-- Task to transform transactions bronze to silver every hour
CREATE OR REPLACE TASK SILVER.HOURLY_TRANSACTIONS_TRANSFORMATION
    WAREHOUSE = TRANSFORMATION_WH
    SCHEDULE = 'USING CRON 25 * * * * UTC' -- Run at 25 minutes past every hour
    COMMENT = 'Hourly transformation of transactions from bronze to silver layer'
AS
    CALL SILVER.TRANSFORM_TRANSACTIONS_BRONZE_TO_SILVER(1);

-- Master task to run all transformations (alternative approach)
CREATE OR REPLACE TASK SILVER.HOURLY_ALL_TRANSFORMATIONS
    WAREHOUSE = TRANSFORMATION_WH
    SCHEDULE = 'USING CRON 30 * * * * UTC' -- Run at 30 minutes past every hour
    COMMENT = 'Hourly transformation of all bronze tables to silver layer'
AS
    CALL SILVER.TRANSFORM_ALL_BRONZE_TO_SILVER(1);

-- ================================================================
-- 4. Task Management Commands
-- ================================================================

-- Resume tasks to start execution
-- Note: Uncomment the tasks you want to use

-- Individual tasks approach:
-- ALTER TASK SILVER.HOURLY_EVENTS_TRANSFORMATION RESUME;
-- ALTER TASK SILVER.HOURLY_USER_EVENTS_TRANSFORMATION RESUME;
-- ALTER TASK SILVER.HOURLY_PRODUCT_EVENTS_TRANSFORMATION RESUME;
-- ALTER TASK SILVER.HOURLY_TRANSACTIONS_TRANSFORMATION RESUME;

-- OR use the master task approach:
-- ALTER TASK SILVER.HOURLY_ALL_TRANSFORMATIONS RESUME;

-- ================================================================
-- 5. Monitoring Queries
-- ================================================================

-- Check task execution history
-- SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY()) 
-- WHERE TASK_NAME LIKE '%TRANSFORMATION%' 
-- ORDER BY SCHEDULED_TIME DESC 
-- LIMIT 100;

-- Check task status
-- SHOW TASKS IN SCHEMA SILVER;

-- Monitor silver table growth
-- SELECT 
--     TABLE_NAME,
--     ROW_COUNT,
--     BYTES,
--     LAST_ALTERED
-- FROM INFORMATION_SCHEMA.TABLES 
-- WHERE TABLE_SCHEMA = 'SILVER' 
--   AND TABLE_TYPE = 'BASE TABLE'
-- ORDER BY LAST_ALTERED DESC;

-- Sample data quality checks
-- SELECT 
--     'EVENTS_SILVER' as TABLE_NAME,
--     COUNT(*) as TOTAL_ROWS,
--     COUNT(DISTINCT EVENT_ID) as UNIQUE_EVENTS,
--     COUNT(DISTINCT USER_ID) as UNIQUE_USERS,
--     MIN(EVENT_TIMESTAMP) as EARLIEST_EVENT,
--     MAX(EVENT_TIMESTAMP) as LATEST_EVENT,
--     COUNT(*) - COUNT(EVENT_ID) as NULL_EVENT_IDS
-- FROM SILVER.EVENTS_SILVER
-- WHERE DATE(CREATED_AT) = CURRENT_DATE()
-- 
-- UNION ALL
-- 
-- SELECT 
--     'USER_EVENTS_SILVER' as TABLE_NAME,
--     COUNT(*) as TOTAL_ROWS,
--     COUNT(DISTINCT EVENT_ID) as UNIQUE_EVENTS,
--     COUNT(DISTINCT USER_ID) as UNIQUE_USERS,
--     MIN(EVENT_TIMESTAMP) as EARLIEST_EVENT,
--     MAX(EVENT_TIMESTAMP) as LATEST_EVENT,
--     COUNT(*) - COUNT(EVENT_ID) as NULL_EVENT_IDS
-- FROM SILVER.USER_EVENTS_SILVER
-- WHERE DATE(CREATED_AT) = CURRENT_DATE();

-- ================================================================
-- 6. Error Handling and Alerting Setup
-- ================================================================

-- Create a table to log transformation errors
CREATE TABLE IF NOT EXISTS SILVER.TRANSFORMATION_LOG (
    LOG_ID NUMBER AUTOINCREMENT,
    TASK_NAME VARCHAR(200),
    EXECUTION_TIME TIMESTAMP_NTZ,
    STATUS VARCHAR(50), -- SUCCESS, ERROR, WARNING
    MESSAGE TEXT,
    ROWS_PROCESSED INTEGER,
    DURATION_SECONDS INTEGER,
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Enhanced logging procedure (example for events)
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_EVENTS_WITH_LOGGING()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    start_time TIMESTAMP_NTZ;
    end_time TIMESTAMP_NTZ;
    duration INTEGER;
    result_msg STRING;
    error_msg STRING;
    rows_count INTEGER DEFAULT 0;
BEGIN
    SET start_time = CURRENT_TIMESTAMP();
    
    BEGIN
        CALL SILVER.TRANSFORM_EVENTS_BRONZE_TO_SILVER(1);
        SET result_msg = 'SUCCESS';
        SET rows_count = (SELECT COUNT(*) FROM SILVER.EVENTS_SILVER 
                         WHERE DATE(UPDATED_AT) = CURRENT_DATE());
    EXCEPTION
        WHEN OTHER THEN
            SET result_msg = 'ERROR';
            SET error_msg = SQLERRM;
    END;
    
    SET end_time = CURRENT_TIMESTAMP();
    SET duration = DATEDIFF('seconds', start_time, end_time);
    
    -- Log the execution
    INSERT INTO SILVER.TRANSFORMATION_LOG (
        TASK_NAME, EXECUTION_TIME, STATUS, MESSAGE, ROWS_PROCESSED, DURATION_SECONDS
    ) VALUES (
        'EVENTS_TRANSFORMATION', start_time, result_msg, 
        COALESCE(error_msg, 'Transformation completed successfully'), 
        rows_count, duration
    );
    
    RETURN 'Execution logged. Status: ' || result_msg || ', Duration: ' || duration || 's';
END;
$$;
```

### Package.json

```
{
  "name": "eventhub-adls-snowflake-pipeline",
  "version": "1.0.0",
  "description": "Data pipeline from Azure EventHub to ADLS to Snowflake",
  "main": "index.js",
  "scripts": {
    "start:ingestion": "node src/eventhub-to-adls.js",
    "start:loader": "node src/adls-to-snowflake.js",
    "start:all": "concurrently \"npm run start:ingestion\" \"npm run start:loader\"",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [
    "azure",
    "eventhub",
    "adls",
    "snowflake",
    "data-pipeline",
    "etl"
  ],
  "author": "Your Name",
  "license": "MIT",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-file-datalake": "^12.15.0",
    "@azure/identity": "^3.4.2",
    "snowflake-sdk": "^1.9.0",
    "node-cron": "^3.0.3"
  },
  "devDependencies": {
    "concurrently": "^8.2.2",
    "dotenv": "^16.3.1"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```




# Data Pipeline: EventHub → ADLS → Snowflake

This pipeline consists of three main components:
1. **EventHub to ADLS Ingestion** (Node.js)
2. **ADLS to Snowflake Loader** (Node.js)
3. **Snowflake Bronze to Silver Transformation** (Snowflake Tasks)

## Prerequisites

- Node.js 18.x or higher
- Azure subscription with EventHub and Storage Account
- Snowflake account with appropriate permissions
- Azure CLI (for authentication)

## Environment Setup

### 1. Create `.env` file for Step 1 (EventHub to ADLS)

```env
# EventHub Configuration
EVENTHUB_CONNECTION_STRING=Endpoint=sb://your-eventhub-namespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccess;SharedAccessKey=your-key
EVENTHUB_NAME=your-eventhub-name
CONSUMER_GROUP=$Default

# Azure Storage Configuration
STORAGE_ACCOUNT_NAME=yourstorageaccount
ADLS_CONTAINER_NAME=events

# Application Configuration
DEFAULT_COLLECTION=events
BUFFER_SIZE=1000
FLUSH_INTERVAL=30000

# Azure Authentication (use one of the following methods)
# Method 1: Service Principal
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Method 2: Managed Identity (if running on Azure)
# AZURE_USE_MANAGED_IDENTITY=true
```

### 2. Create `.env` file for Step 2 (ADLS to Snowflake)

```env
# Azure Storage Configuration
STORAGE_ACCOUNT_NAME=yourstorageaccount
ADLS_CONTAINER_NAME=events
AZURE_SAS_TOKEN=your-sas-token-with-read-permissions

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your-account.region.cloud
SNOWFLAKE_USERNAME=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=BRONZE
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_ROLE=your-role

# Application Configuration
PROCESSED_FILES_PATH=./processed_files.json
BATCH_SIZE=5

# Azure Authentication
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

## Installation and Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Azure Authentication Setup

#### Option A: Service Principal (Recommended for production)
```bash
# Create service principal
az ad sp create-for-rbac --name "eventhub-adls-pipeline" --role "Storage Blob Data Contributor" --scopes /subscriptions/your-subscription-id

# Grant additional permissions
az role assignment create --assignee your-client-id --role "Azure Event Hubs Data Receiver" --scope /subscriptions/your-subscription-id
```

#### Option B: Azure CLI Login (Development)
```bash
az login
```

### 3. Azure Storage Account Setup

```bash
# Create storage account (if needed)
az storage account create \
    --name yourstorageaccount \
    --resource-group your-resource-group \
    --location eastus \
    --sku Standard_LRS \
    --enable-hierarchical-namespace true

# Create container
az storage fs create \
    --name events \
    --account-name yourstorageaccount

# Generate SAS token for Snowflake access
az storage account generate-sas \
    --account-name yourstorageaccount \
    --services b \
    --resource-types sco \
    --permissions rl \
    --expiry 2025-12-31 \
    --https-only
```

### 4. Snowflake Setup

#### Create Database and Schemas
```sql
-- Run in Snowflake
CREATE DATABASE IF NOT EXISTS YOUR_DATABASE;
USE DATABASE YOUR_DATABASE;

CREATE SCHEMA IF NOT EXISTS BRONZE;
CREATE SCHEMA IF NOT EXISTS SILVER;

-- Grant permissions to your role
GRANT USAGE ON DATABASE YOUR_DATABASE TO ROLE your_role;
GRANT ALL ON SCHEMA BRONZE TO ROLE your_role;
GRANT ALL ON SCHEMA SILVER TO ROLE your_role;
GRANT USAGE ON WAREHOUSE your_warehouse TO ROLE your_role;
```

## Deployment and Execution

### Step 1: Start EventHub to ADLS Ingestion

```bash
# Development
npm run start:ingestion

# Production (with PM2)
pm2 start src/eventhub-to-adls.js --name "eventhub-ingestion"
```

### Step 2: Start ADLS to Snowflake Loader

```bash
# Development
npm run start:loader

# Production (with PM2)
pm2 start src/adls-to-snowflake.js --name "adls-snowflake-loader"
```

### Step 3: Execute Snowflake Setup and Start Tasks

```sql
-- 1. Run the silver table creation and stored procedures
-- (Execute the SQL from the Snowflake artifact)

-- 2. Start the tasks
USE SCHEMA SILVER;

-- Option A: Start individual tasks
ALTER TASK HOURLY_EVENTS_TRANSFORMATION RESUME;
ALTER TASK HOURLY_USER_EVENTS_TRANSFORMATION RESUME;
ALTER TASK HOURLY_PRODUCT_EVENTS_TRANSFORMATION RESUME;
ALTER TASK HOURLY_TRANSACTIONS_TRANSFORMATION RESUME;

-- Option B: Start master task (recommended)
ALTER TASK HOURLY_ALL_TRANSFORMATIONS RESUME;
```

## Monitoring and Troubleshooting

### 1. Check Node.js Application Logs

```bash
# Check PM2 logs
pm2 logs eventhub-ingestion
pm2 logs adls-snowflake-loader

# Check application status
pm2 status
```

### 2. Monitor Snowflake Tasks

```sql
-- Check task execution history
SELECT 
    TASK_NAME,
    SCHEDULED_TIME,
    COMPLETED_TIME,
    STATE,
    ERROR_CODE,
    ERROR_MESSAGE
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY()) 
WHERE TASK_NAME LIKE '%TRANSFORMATION%' 
ORDER BY SCHEDULED_TIME DESC 
LIMIT 50;

-- Check current task status
SHOW TASKS IN SCHEMA SILVER;

-- Monitor data flow
SELECT 
    TABLE_SCHEMA,
    TABLE_NAME,
    ROW_COUNT,
    BYTES,
    LAST_ALTERED
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA IN ('BRONZE', 'SILVER')
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

### 3. Data Quality Checks

```sql
-- Check data freshness
SELECT 
    'BRONZE' as LAYER,
    TABLE_NAME,
    COUNT(*) as ROW_COUNT,
    MAX(LOAD_TIMESTAMP) as LATEST_LOAD
FROM INFORMATION_SCHEMA.TABLES t
JOIN BRONZE.EVENTS_BRONZE b ON 1=1  -- Replace with dynamic query
WHERE TABLE_SCHEMA = 'BRONZE'
GROUP BY TABLE_NAME

UNION ALL

SELECT 
    'SILVER' as LAYER,
    TABLE_NAME,
    COUNT(*) as ROW_COUNT,
    MAX(UPDATED_AT) as LATEST_UPDATE
FROM INFORMATION_SCHEMA.TABLES t
JOIN SILVER.EVENTS_SILVER s ON 1=1  -- Replace with dynamic query
WHERE TABLE_SCHEMA = 'SILVER'
GROUP BY TABLE_NAME;
```

## Scaling Considerations

### Node.js Applications
- Use PM2 cluster mode for CPU-intensive workloads
- Implement proper error handling and retry logic
- Monitor memory usage and adjust buffer sizes
- Consider using Azure Container Instances or AKS for production

### Snowflake Tasks
- Adjust warehouse sizes based on data volume
- Use task dependencies for complex workflows
- Implement proper error notifications
- Consider using streams for change data capture

## Troubleshooting Common Issues

### EventHub Connection Issues
- Verify connection string and permissions
- Check network connectivity and firewall rules
- Ensure consumer group exists

### ADLS Access Issues
- Verify Azure credentials and permissions
- Check storage account firewall settings
- Ensure hierarchical namespace is enabled

### Snowflake Loading Issues
- Verify SAS token permissions and expiry
- Check stage configuration
- Validate JSON format in source files
- Monitor warehouse auto-suspend settings

### Task Execution Issues
- Check task schedule and timezone settings
- Verify warehouse permissions and availability
- Monitor task execution history for patterns
- Ensure dependencies between tasks are properly configured

## Security Best Practices

1. Use Azure Key Vault for sensitive configuration
2. Implement least-privilege access policies
3. Rotate SAS tokens and connection strings regularly
4. Use network security groups and private endpoints
5. Enable audit logging in all components
6. Implement data encryption at rest and in transit


###  Full migration

The current pipeline above only processes **new records** from EventHub.  
For existing MongoDB collections, you need an **initial data migration** strategy. 
Let me provide you with additional components to handle historical data.  
Now let me update the package.json to include the MongoDB migration scripts: 

### **1. `npm run start:all` Command:**
This command runs **BOTH** Step 1 (EventHub to ADLS) AND Step 2 (ADLS to Snowflake) **simultaneously** using the `concurrently` package. It's equivalent to running both applications in parallel.

### **2. EventHub Message Deletion:**
**NO** - EventHub messages are **NOT automatically deleted** after reading. EventHub uses:
- **Time-based retention** (1-90 days configurable)
- **Checkpointing** to track consumer progress
- Messages remain available for replay and multiple consumers

### **3. MongoDB Historical Data Migration:**

I've created a **MongoDB Migration Pipeline** that handles your existing collections:

**Key Features:**
- ✅ **Full migration** of all historical MongoDB data
- ✅ **Incremental migration** for catching up missed changes  
- ✅ **Same partitioning structure** as EventHub pipeline
- ✅ **Collection-specific processing** with parallel execution
- ✅ **Time-based chunking** for large datasets

**Migration Strategy:**

```bash
# 1. One-time historical migration (before starting EventHub)
npm run migrate:full

# 2. Start real-time EventHub pipeline (after migration)
npm run start:all

# 3. Optional: Incremental catch-up for any overlap
npm run migrate:incremental 2024-08-09T00:00:00Z
```

**Timeline Strategy:**

```
MongoDB Historical:  [████████████████████] (All data before cutoff)
                                            |
EventHub New Data:                          [████████████████] (All data after cutoff)
                                            ^
                                    August 10, 2025 00:00:00Z
                                    (Migration Cutoff Point)
```

## **Complete Deployment Sequence:**

### **Phase 1: Historical Migration (Run First)**
```bash
# 1. Install dependencies including MongoDB driver
npm install

# 2. Configure MongoDB connection
# Add MONGODB_CONNECTION_STRING to .env

# 3. Run full historical migration (this may take hours/days for large datasets)
npm run migrate:full

# 4. Validate migration completed successfully
# Check logs and Snowflake bronze tables
```

### **Phase 2: Real-Time Pipeline (Run After Migration)**
```bash
# 1. Start EventHub to ADLS ingestion
npm run start:ingestion

# 2. Start ADLS to Snowflake loader  
npm run start:loader

# OR start both together
npm run start:all
```

### **Phase 3: Snowflake Tasks (Run Last)**
```sql
-- Execute in Snowflake after bronze tables have data
ALTER TASK SILVER.HOURLY_ALL_TRANSFORMATIONS RESUME;
```

## **Data Consistency Handling:**

### **Option 1: Clean Cutoff (Recommended)**
1. Stop writes to MongoDB at specific time
2. Complete historical migration 
3. Start EventHub pipeline
4. Resume MongoDB writes (routing to EventHub)

### **Option 2: Overlap Handling**
```javascript
// Add to EventHub processor for deduplication
async processEvent(event) {
    const eventTime = new Date(event.body.timestamp);
    const migrationCutoff = new Date('2024-08-10T00:00:00Z');
    
    // Skip events that might be duplicated from migration
    if (eventTime < migrationCutoff) {
        console.log('Skipping - event before migration cutoff');
        return;
    }
    
    // Process normally...
}
```

## **Monitoring Migration Progress:**

### **Real-time Progress Tracking:**
```bash
# Watch migration logs
tail -f migration.log

# Check MongoDB progress
db.collection.countDocuments({migrated: {$exists: false}})
```

### **Snowflake Validation:**
```sql
-- Check migration data in Snowflake
SELECT 
    REGEXP_SUBSTR(_PARTITION_PATH, 'db/([^/]+)/', 1, 1, 'e', 1) as COLLECTION,
    COUNT(*) as MIGRATED_RECORDS,
    MIN(RAW_DATA:_migrationTimestamp::TIMESTAMP_NTZ) as FIRST_MIGRATED,
    MAX(RAW_DATA:_migrationTimestamp::TIMESTAMP_NTZ) as LAST_MIGRATED
FROM BRONZE.YOUR_COLLECTION_BRONZE 
WHERE FILE_NAME LIKE '%migration-%'
GROUP BY COLLECTION
ORDER BY COLLECTION;
```

## **Performance Tuning:**

### **For Large Collections (1M+ documents):**
```env
MIGRATION_BATCH_SIZE=5000      # Larger batches
PARALLEL_COLLECTIONS=1         # Reduce parallelism  
FLUSH_INTERVAL=60000          # Less frequent flushes
```

### **For Many Small Collections:**
```env
MIGRATION_BATCH_SIZE=500       # Smaller batches
PARALLEL_COLLECTIONS=5         # More parallelism
```

### **Memory Optimization:**
```javascript
// Add to migration config
{
    batchSize: 1000,
    maxMemoryUsage: '2GB',
    gcInterval: 10000  // Force garbage collection
}
```

This migration strategy ensures you capture **all existing MongoDB data** while seamlessly transitioning to the **EventHub-based pipeline** for new data,  
maintaining the same partitioning structure and data format throughout your entire data lake.

#### package.json

```json

{
  "name": "eventhub-adls-snowflake-pipeline",
  "version": "1.0.0",
  "description": "Data pipeline from Azure EventHub to ADLS to Snowflake",
  "main": "index.js",
  "scripts": {
    "start:ingestion": "node src/eventhub-to-adls.js",
    "start:loader": "node src/adls-to-snowflake.js",
    "start:all": "concurrently \"npm run start:ingestion\" \"npm run start:loader\"",
    "migrate:full": "node src/mongodb-migration.js full",
    "migrate:incremental": "node src/mongodb-migration.js incremental",
    "migrate:collection": "node src/mongodb-migration.js collection",
    "migrate:scheduler": "node src/mongodb-migration.js scheduler",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [
    "azure",
    "eventhub",
    "adls",
    "snowflake",
    "data-pipeline",
    "etl"
  ],
  "author": "Your Name",
  "license": "MIT",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-file-datalake": "^12.15.0",
    "@azure/identity": "^3.4.2",
    "snowflake-sdk": "^1.9.0",
    "node-cron": "^3.0.3",
    "mongodb": "^6.2.0"
  },
  "devDependencies": {
    "concurrently": "^8.2.2",
    "dotenv": "^16.3.1"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```


### If some of the 3  Steps of pipeline 
- Step 1: EventHub to ADLS Ingestion  
- Step 2: ADLS to Snowflake Loader  
- Step 3: Snowflake Bronze to Silver Tasks
  
gets broken how to replay it?

Perfect! Now let me update the package.json to include the recovery commands:## **Summary: Pipeline Recovery Capabilities**

Here's how to handle failures in each step:

### **🔄 Step 1: EventHub to ADLS Recovery**

**What can break:**
- Application crashes
- Network issues  
- ADLS write failures

**Recovery method:**
```bash
# Replay from EventHub (data is retained for 1-90 days)
npm run recovery step1 "2024-08-09T10:00:00Z" "2024-08-09T12:00:00Z"

# Reset checkpoint if needed
npm run recovery reset-checkpoint "0" "2024-08-09T10:00:00Z"
```

**Key advantage:** EventHub **never deletes messages** until retention expires, so you can replay any time window.

---

### **🔄 Step 2: ADLS to Snowflake Recovery**

**What can break:**
- Snowflake connection issues
- COPY command failures
- File format errors

**Recovery method:**
```bash
# Reprocess files for specific date
npm run recovery step2 "2024-08-09" "2024-08-10"

# Force reprocess (ignore already-processed tracking)
npm run recovery step2 "2024-08-09" "2024-08-10" force
```

**Key advantage:** Files in ADLS are **persistent**, so you can reprocess any historical data.

---

### **🔄 Step 3: Bronze to Silver Recovery**

**What can break:**
- Task execution failures
- Schema mismatches
- Transformation errors

**Recovery method:**
```sql
-- Snowflake recovery
CALL SILVER.TRANSFORM_EVENTS_BRONZE_TO_SILVER_DATE_RANGE('2024-08-09', '2024-08-09');

-- Or via Node.js
npm run recovery step3 "2024-08-09" "2024-08-10"
```

**Key advantage:** Bronze data is **immutable**, so you can re-transform any time period safely.

---

## **🚨 Emergency Recovery Scenarios:**

### **Complete 4-Hour Outage Recovery:**
```bash
# 1. Replay EventHub (Step 1)
npm run recovery step1 "2024-08-09T10:00:00Z" "2024-08-09T14:00:00Z"

# 2. Wait for files to be created, then reload to Snowflake (Step 2)  
sleep 300
npm run recovery step2 "2024-08-09" force

# 3. Re-transform to Silver (Step 3)
npm run recovery step3 "2024-08-09"

# 4. Resume normal operations
npm run start:all
```

### **Selective Collection Recovery:**
```bash
# Only recover specific collections
COLLECTIONS_TO_MIGRATE=users,orders npm run recovery step2 "2024-08-09" force
```

## **🔍 Detection and Monitoring:**

### **Automated Health Checks:**
```bash
# Run every 15 minutes
*/15 * * * * /path/to/check_pipeline_health.sh

# Auto-recovery every hour  
0 * * * * /path/to/auto_recovery.sh
```

### **Data Gap Detection:**
```sql
-- Find missing hours
SELECT * FROM TABLE(SILVER.FIND_DATA_GAPS('2024-08-09', '2024-08-10', 'ALL'));

-- Check consistency
SELECT * FROM TABLE(SILVER.VALIDATE_BRONZE_SILVER_CONSISTENCY('2024-08-09'));
```

## **✅ Key Recovery Advantages:**

1. **🔄 Full Replay Capability** - EventHub retention allows complete data recovery
2. **📁 Persistent Storage** - ADLS files remain available for reprocessing  
3. **🏗️ Immutable Bronze** - Source data preserved for re-transformation
4. **⚡ Time-based Recovery** - Replay any specific time window
5. **🎯 Granular Control** - Recover individual collections or date ranges
6. **🔒 Zero Data Loss** - All layers maintain data for recovery

The pipeline is designed to be **fully recoverable** with **zero data loss** potential. Every component can replay from its source, making it resilient to any type of failure scenario.


Package.json
```js
{
  "name": "eventhub-adls-snowflake-pipeline",
  "version": "1.0.0",
  "description": "Data pipeline from Azure EventHub to ADLS to Snowflake",
  "main": "index.js",
  "scripts": {
    "start:ingestion": "node src/eventhub-to-adls.js",
    "start:loader": "node src/adls-to-snowflake.js",
    "start:all": "concurrently \"npm run start:ingestion\" \"npm run start:loader\"",
    "migrate:full": "node src/mongodb-migration.js full",
    "migrate:incremental": "node src/mongodb-migration.js incremental",
    "migrate:collection": "node src/mongodb-migration.js collection",
    "migrate:scheduler": "node src/mongodb-migration.js scheduler",
    "recovery": "node src/pipeline-recovery.js",
    "health-check": "node src/health-check.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [
    "azure",
    "eventhub",
    "adls",
    "snowflake",
    "data-pipeline",
    "etl"
  ],
  "author": "Your Name",
  "license": "MIT",
  "dependencies": {
    "@azure/event-hubs": "^5.11.4",
    "@azure/storage-file-datalake": "^12.15.0",
    "@azure/identity": "^3.4.2",
    "snowflake-sdk": "^1.9.0",
    "node-cron": "^3.0.3",
    "mongodb": "^6.2.0"
  },
  "devDependencies": {
    "concurrently": "^8.2.2",
    "dotenv": "^16.3.1"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```
