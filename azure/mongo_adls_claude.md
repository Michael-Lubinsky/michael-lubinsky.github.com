## Claude
### Step 1: From Mongo to ASDL
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



### Step 3 from Bronze to Silver

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
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
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
    PRIMARY KEY (EVENT_ID, USER_ID)
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

-- ================================================================
-- 2. Create Stored Procedures for Bronze to Silver Transformation
-- ================================================================

-- Generic transformation procedure
CREATE OR REPLACE PROCEDURE SILVER.TRANSFORM_BRONZE_TO_SILVER(
    COLLECTION_NAME VARCHAR,
    LOOKBACK_HOURS INTEGER DEFAULT 1
)
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    bronze_table_name VARCHAR;
    sql_stmt VARCHAR;
    rows_processed INTEGER DEFAULT 0;
    start_time TIMESTAMP_NTZ;
    end_time TIMESTAMP_NTZ;
BEGIN
    SET start_time = CURRENT_TIMESTAMP();
    SET bronze_table_name = 'BRONZE.' || COLLECTION_NAME || '_BRONZE';
    SET end_time = DATEADD('hour', -LOOKBACK_HOURS, CURRENT_TIMESTAMP());
    
    -- Dynamic SQL based on collection type
    CASE 
        WHEN COLLECTION_NAME = 'EVENTS' THEN
            SET sql_stmt = '
            MERGE INTO SILVER.EVENTS_SILVER AS target
            USING (
                SELECT 
                    RAW_DATA:event_id::VARCHAR AS EVENT_ID,
                    RAW_DATA:user_id::VARCHAR AS USER_ID,
                    RAW_DATA:session_id::VARCHAR AS SESSION_ID,
                    RAW_DATA:event_type::VARCHAR AS EVENT_TYPE,
                    TO_TIMESTAMP_NTZ(RAW_DATA:timestamp::VARCHAR) AS EVENT_TIMESTAMP,
                    RAW_DATA:properties AS PROPERTIES,
                    RAW_DATA:user_agent::VARCHAR AS USER_AGENT,
                    RAW_DATA:ip_address::VARCHAR AS IP_ADDRESS,
                    RAW_DATA:geo.country::VARCHAR AS COUNTRY,
                    RAW_DATA:geo.city::VARCHAR AS CITY,
                    INGESTION_TIMESTAMP,
                    LOAD_TIMESTAMP,
                    FILE_NAME AS SOURCE_FILE,
                    _PARTITION_PATH AS PARTITION_PATH
                FROM ' || bronze_table_name || '
                WHERE LOAD_TIMESTAMP >= ''' || end_time || '''
                  AND RAW_DATA:event_id IS NOT NULL
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
                    UPDATED_AT = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT (
                    EVENT_ID, USER_ID, SESSION_ID, EVENT_TYPE, EVENT_TIMESTAMP,
                    PROPERTIES, USER_AGENT, IP_ADDRESS, COUNTRY, CITY,
                    INGESTION_TIMESTAMP, LOAD_TIMESTAMP, SOURCE_FILE, PARTITION_PATH
                )
                VALUES (
                    source.EVENT_ID, source.USER_ID, source.SESSION_ID, 
                    
```



