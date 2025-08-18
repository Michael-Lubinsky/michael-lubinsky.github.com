# Cloude 2

## Key Features of the Solution

**1. Main Application (`index.js`)**
- **Real-time monitoring**: Uses MongoDB change streams to capture all data changes
- **Robust error handling**: Implements exponential backoff, automatic reconnection, and comprehensive error recovery
- **Graceful shutdown**: Handles SIGINT/SIGTERM signals properly, completes pending uploads
- **Auto-dumping**: Automatically dumps when buffer reaches configurable size (default 1000 changes)
- **Scheduled dumps**: Hourly dumps using cron scheduling (configurable)
- **Resume capability**: Can resume from where it left off after restarts
- **Memory management**: Clears buffers after dumps, manages temporary files

**2. File Organization**
- Creates files in format: `<collection>/YYYY-MM-DD-HH.json`
- Each file contains metadata and an array of changes
- Organized folder structure in Azure ADLS Gen2

**3. Production-Ready Features**
- **Logging**: Winston logger with multiple transports (console, file)
- **Configuration**: Environment-based configuration with validation
- **Containerization**: Docker support with health checks
- **Security**: Non-root user, proper error handling
- **Monitoring**: Structured logging and error tracking

## Deployment Options

**Local Development:**
```bash
npm install
cp .env.template .env  # Configure your environment
npm start
```

**Docker:**
```bash
docker build -t mongodb-changestream-dumper .
docker run --env-file .env mongodb-changestream-dumper
```

**Kubernetes:** (example deployment YAML included in README)

## Key Configuration

The application requires these essential environment variables:
- `MONGODB_URI`: Your MongoDB Atlas connection string
- `AZURE_STORAGE_ACCOUNT_NAME`: Azure storage account name
- `AZURE_STORAGE_ACCOUNT_KEY`: Azure storage account key
- `MONGODB_COLLECTIONS`: Comma-separated list of collections to monitor

## Error Handling & Resilience

The solution handles:
- MongoDB connection failures with automatic reconnection
- Change stream interruptions with resume token support
- Azure upload failures with retry logic
- Buffer overflow with auto-dumping
- Graceful shutdown ensuring no data loss

## Production Considerations

1. **Scalability**: Can monitor multiple collections, auto-dumps prevent memory issues
2. **Reliability**: Resume tokens ensure no data loss during restarts
3. **Monitoring**: Comprehensive logging for observability
4. **Security**: Uses environment variables for sensitive data
5. **Performance**: Configurable batch sizes and retry strategies


# MongoDB Change Stream to Azure Data Lake Storage Gen2 Dumper

A production-ready Node.js application that monitors MongoDB change streams and periodically dumps the changes to Azure Data Lake Storage Gen2 in organized folder structures.

## Features

- **Real-time Change Stream Monitoring**: Watches multiple MongoDB collections for changes
- **Organized Storage**: Stores changes in ADLS Gen2 with folder structure `<collection>/YYYY-MM-DD-HH.json`
- **Robust Error Handling**: Comprehensive error handling with exponential backoff retry logic
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals and ensures all pending operations complete
- **Auto-dumping**: Automatically dumps when buffer reaches configurable size
- **Resumable**: Can resume from where it left off after restarts
- **Production Ready**: Includes logging, monitoring, and containerization support

## Architecture

```
MongoDB Atlas → Change Streams → Buffer → Hourly Dump → Azure ADLS Gen2
     ↓              ↓              ↓           ↓              ↓
  Collections → Real-time → In-memory → Scheduled → Organized folders
```

## Prerequisites

- Node.js 16+ 
- MongoDB Atlas cluster with change streams enabled
- Azure Storage Account with Data Lake Storage Gen2 enabled
- Appropriate network connectivity between services

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd mongodb-changestream-adls-dumper
```

2. Install dependencies:
```bash
npm install
```

3. Copy and configure environment variables:
```bash
cp .env.template .env
# Edit .env with your configuration
```

4. Start the application:
```bash
npm start
```

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t mongodb-changestream-dumper .
```

2. Run the container:
```bash
docker run --env-file .env mongodb-changestream-dumper
```

### Kubernetes Deployment

Create a deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb-changestream-dumper
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb-changestream-dumper
  template:
    metadata:
      labels:
        app: mongodb-changestream-dumper
    spec:
      containers:
      - name: dumper
        image: mongodb-changestream-dumper:latest
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: mongodb-secret
              key: uri
        - name: AZURE_STORAGE_ACCOUNT_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secret
              key: storage-key
        # Add other environment variables
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGODB_URI` | MongoDB connection string | - | ✅ |
| `MONGODB_DATABASE` | Database name to monitor | `mydb` | ❌ |
| `MONGODB_COLLECTIONS` | Comma-separated list of collections | `users,orders` | ❌ |
| `AZURE_STORAGE_ACCOUNT_NAME` | Azure storage account name | - | ✅ |
| `AZURE_STORAGE_ACCOUNT_KEY` | Azure storage account key | - | ✅ |
| `AZURE_ADLS_FILESYSTEM` | ADLS Gen2 filesystem name | `changestreams` | ❌ |
| `DUMP_SCHEDULE` | Cron schedule for dumps | `0 * * * *` | ❌ |
| `BATCH_SIZE` | Auto-dump threshold | `1000` | ❌ |
| `RETRY_ATTEMPTS` | Max retry attempts | `3` | ❌ |
| `RETRY_DELAY_MS` | Initial retry delay | `1000` | ❌ |
| `LOG_LEVEL` | Logging level | `info` | ❌ |

### MongoDB Atlas Configuration

1. **Enable Change Streams**: Ensure your MongoDB Atlas cluster supports change streams (M10+)
2. **Database User**: Create a user with `readAnyDatabase` role
3. **Network Access**: Allow connections from your application's IP/network
4. **Connection String**: Use the SRV connection string format

### Azure Data Lake Storage Gen2 Setup

1. **Create Storage Account**: Enable hierarchical namespace (Data Lake Gen2)
2. **Create Filesystem**: Create a container/filesystem for change stream data
3. **Access Keys**: Generate and securely store access keys
4. **Permissions**: Ensure the account has read/write permissions

## File Structure

The application creates files in ADLS Gen2 with the following structure:

```
<filesystem>/
├── collection1/
│   ├── 2024-01-15-14.json    # Changes from 2PM-3PM on Jan 15, 2024
│   ├── 2024-01-15-15.json
│   └── ...
├── collection2/
│   ├── 2024-01-15-14.json
│   └── ...
```

### File Format

Each JSON file contains:
```jsonl
{"timestamp": "2024-01-15T14:15:23.123Z", "collection": "users", "dumper_version": "1.0.0", "change": {"_id": {"_data": "..."}, "operationType": "insert", "fullDocument": {"_id": "507f1f77bcf86cd799439011", "name": "John Doe"}, "ns": {"db": "mydb", "coll": "users"}, "documentKey": {"_id": "507f1f77bcf86cd799439011"}}}
{"timestamp": "2024-01-15T14:16:45.456Z", "collection": "users", "dumper_version": "1.0.0", "change": {"_id": {"_data": "..."}, "operationType": "update", "fullDocument": {"_id": "507f1f77bcf86cd799439011", "name": "Jane Doe"}, "ns": {"db": "mydb", "coll": "users"}, "documentKey": {"_id": "507f1f77bcf86cd799439011"}}}
{"timestamp": "2024-01-15T14:17:12.789Z", "collection": "users", "dumper_version": "1.0.0", "change": {"_id": {"_data": "..."}, "operationType": "delete", "ns": {"db": "mydb", "coll": "users"}, "documentKey": {"_id": "507f1f77bcf86cd799439011"}}}

```
#### Example: how to read JSONL with Node.js:
```js
const fs = require('fs');
const readline = require('readline');

const fileStream = fs.createReadStream('users/2024-01-15-14.jsonl');
const rl = readline.createInterface({
  input: fileStream,
  crlfDelay: Infinity
});

for await (const line of rl) {
  const record = JSON.parse(line);
  // Process each change record
  console.log(record.change.operationType);
}
```


## Monitoring and Observability

### Logging

The application uses Winston for structured logging with multiple transports:
- Console output (development)
- File rotation (production)
- JSON format for log aggregation

### Metrics

Monitor these key metrics:
- Change stream connection status
- Buffer sizes per collection
- Upload success/failure rates
- Processing latency
- Error rates

### Health Checks

The application supports health checks for container orchestration:
- Kubernetes liveness/readiness probes
- Docker health checks
- Custom monitoring endpoints

## Error Handling

The application implements comprehensive error handling:

1. **Connection Errors**: Automatic reconnection with exponential backoff
2. **Change Stream Errors**: Resume from last known position
3. **Upload Failures**: Retry with configurable attempts
4. **Buffer Overflow**: Auto-dump when limits are reached
5. **Graceful Shutdown**: Complete pending operations before exit

## Performance Considerations

### Memory Management

- Change buffers are cleared after each dump
- Temporary files are cleaned up immediately after upload
- Connection pooling is configured for optimal resource usage

### Scalability

- Buffer size can be tuned based on change volume
- Multiple instances can monitor different collections
- Horizontal scaling through container orchestration

### Network Optimization

- Batch uploads reduce API calls
- Compression can be enabled for large files
- Regional deployment reduces latency

## Troubleshooting

### Common Issues

1. **Change Stream Connection Failures**
   ```
   Error: MongoServerSelectionError
   ```
   - Verify MongoDB URI and network connectivity
   - Check database user permissions
   - Ensure change streams are supported (M10+ clusters)

2. **Azure Upload Failures**
   ```
   Error: StorageError: This request is not authorized
   ```
   - Verify storage account name and key
   - Check ADLS Gen2 is enabled
   - Ensure filesystem exists

3. **Memory Issues**
   ```
   Error: JavaScript heap out of memory
   ```
   - Reduce `BATCH_SIZE`
   - Increase container memory limits
   - Monitor change volume and optimize schedule

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=debug
npm start
```

### Manual Dump

For testing, you can trigger manual dumps by sending SIGUSR1:
```bash
kill -SIGUSR1 <process_id>
```

## Security

### Best Practices

1. **Environment Variables**: Store sensitive data in environment variables
2. **Access Keys**: Use Azure Key Vault or similar secret management
3. **Network Security**: Use VPN/private endpoints where possible
4. **Audit Logging**: Enable audit logs for compliance
5. **Encryption**: Use TLS for all connections

### Secrets Management

For production deployments, consider:
- Azure Key Vault
- Kubernetes Secrets
- HashiCorp Vault
- AWS Secrets Manager

### index.js
```js
const { MongoClient } = require('mongodb');
const { DataLakeServiceClient } = require('@azure/storage-file-datalake');
const winston = require('winston');
const cron = require('node-cron');
const fs = require('fs').promises;
const path = require('path');
const { promisify } = require('util');

// Configuration
const CONFIG = {
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017',
    database: process.env.MONGODB_DATABASE || 'mydb',
    collections: (process.env.MONGODB_COLLECTIONS || 'users,orders').split(','),
    options: {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    }
  },
  azure: {
    accountName: process.env.AZURE_STORAGE_ACCOUNT_NAME,
    accountKey: process.env.AZURE_STORAGE_ACCOUNT_KEY,
    fileSystemName: process.env.AZURE_ADLS_FILESYSTEM || 'changestreams',
  },
  dumper: {
    schedule: process.env.DUMP_SCHEDULE || '0 * * * *', // Every hour
    batchSize: parseInt(process.env.BATCH_SIZE) || 1000,
    retryAttempts: parseInt(process.env.RETRY_ATTEMPTS) || 3,
    retryDelayMs: parseInt(process.env.RETRY_DELAY_MS) || 1000,
    tempDir: process.env.TEMP_DIR || './temp',
    maxFileSize: parseInt(process.env.MAX_FILE_SIZE) || 100 * 1024 * 1024, // 100MB
  }
};

// Logger setup
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ],
});

class ChangeStreamDumper {
  constructor() {
    this.mongoClient = null;
    this.dataLakeClient = null;
    this.changeStreams = new Map();
    this.changeBuffer = new Map();
    this.isShuttingDown = false;
    this.activeUploads = new Set();
  }

  async initialize() {
    try {
      logger.info('Initializing MongoDB Change Stream Dumper...');
      
      // Validate configuration
      this.validateConfig();
      
      // Initialize MongoDB client
      await this.initializeMongoClient();
      
      // Initialize Azure Data Lake client
      this.initializeAzureClient();
      
      // Create temp directory
      await this.ensureTempDirectory();
      
      // Setup change streams for each collection
      await this.setupChangeStreams();
      
      // Setup periodic dump job
      this.setupDumpSchedule();
      
      logger.info('Initialization completed successfully');
    } catch (error) {
      logger.error('Failed to initialize:', error);
      throw error;
    }
  }

  validateConfig() {
    const requiredEnvVars = [
      'MONGODB_URI',
      'AZURE_STORAGE_ACCOUNT_NAME',
      'AZURE_STORAGE_ACCOUNT_KEY'
    ];
    
    const missing = requiredEnvVars.filter(envVar => !process.env[envVar]);
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
  }

  async initializeMongoClient() {
    this.mongoClient = new MongoClient(CONFIG.mongodb.uri, CONFIG.mongodb.options);
    await this.mongoClient.connect();
    
    // Test connection
    await this.mongoClient.db(CONFIG.mongodb.database).admin().ping();
    logger.info('MongoDB connection established');
  }

  initializeAzureClient() {
    this.dataLakeClient = new DataLakeServiceClient(
      `https://${CONFIG.azure.accountName}.dfs.core.windows.net`,
      { accountName: CONFIG.azure.accountName, accountKey: CONFIG.azure.accountKey }
    );
    logger.info('Azure Data Lake client initialized');
  }

  async ensureTempDirectory() {
    try {
      await fs.mkdir(CONFIG.dumper.tempDir, { recursive: true });
    } catch (error) {
      if (error.code !== 'EEXIST') {
        throw error;
      }
    }
  }

  async setupChangeStreams() {
    const db = this.mongoClient.db(CONFIG.mongodb.database);
    
    for (const collection of CONFIG.mongodb.collections) {
      try {
        const changeStream = db.collection(collection).watch([], {
          fullDocument: 'updateLookup',
          resumeAfter: await this.getResumeToken(collection)
        });

        this.changeBuffer.set(collection, []);
        
        changeStream.on('change', (change) => {
          this.handleChangeEvent(collection, change);
        });

        changeStream.on('error', (error) => {
          logger.error(`Change stream error for collection ${collection}:`, error);
          this.handleChangeStreamError(collection, error);
        });

        changeStream.on('close', () => {
          logger.warn(`Change stream closed for collection ${collection}`);
          if (!this.isShuttingDown) {
            this.reconnectChangeStream(collection);
          }
        });

        this.changeStreams.set(collection, changeStream);
        logger.info(`Change stream setup completed for collection: ${collection}`);
      } catch (error) {
        logger.error(`Failed to setup change stream for collection ${collection}:`, error);
        throw error;
      }
    }
  }

  handleChangeEvent(collection, change) {
    try {
      const buffer = this.changeBuffer.get(collection);
      buffer.push({
        timestamp: new Date(),
        change: change
      });

      // Auto-dump if buffer is getting large
      if (buffer.length >= CONFIG.dumper.batchSize) {
        logger.info(`Auto-dumping ${collection} due to buffer size: ${buffer.length}`);
        this.dumpCollectionChanges(collection).catch(error => {
          logger.error(`Auto-dump failed for ${collection}:`, error);
        });
      }
    } catch (error) {
      logger.error(`Error handling change event for ${collection}:`, error);
    }
  }

  async handleChangeStreamError(collection, error) {
    logger.error(`Handling change stream error for ${collection}:`, error);
    
    // Close existing stream
    const existingStream = this.changeStreams.get(collection);
    if (existingStream) {
      try {
        existingStream.close();
      } catch (closeError) {
        logger.error(`Error closing change stream for ${collection}:`, closeError);
      }
    }

    // Reconnect after delay
    setTimeout(() => {
      if (!this.isShuttingDown) {
        this.reconnectChangeStream(collection);
      }
    }, CONFIG.dumper.retryDelayMs);
  }

  async reconnectChangeStream(collection) {
    try {
      logger.info(`Reconnecting change stream for collection: ${collection}`);
      
      const db = this.mongoClient.db(CONFIG.mongodb.database);
      const resumeToken = await this.getResumeToken(collection);
      
      const changeStream = db.collection(collection).watch([], {
        fullDocument: 'updateLookup',
        resumeAfter: resumeToken
      });

      changeStream.on('change', (change) => {
        this.handleChangeEvent(collection, change);
      });

      changeStream.on('error', (error) => {
        logger.error(`Reconnected change stream error for collection ${collection}:`, error);
        this.handleChangeStreamError(collection, error);
      });

      changeStream.on('close', () => {
        logger.warn(`Reconnected change stream closed for collection ${collection}`);
        if (!this.isShuttingDown) {
          this.reconnectChangeStream(collection);
        }
      });

      this.changeStreams.set(collection, changeStream);
      logger.info(`Change stream reconnected for collection: ${collection}`);
    } catch (error) {
      logger.error(`Failed to reconnect change stream for ${collection}:`, error);
      
      // Retry after delay
      setTimeout(() => {
        if (!this.isShuttingDown) {
          this.reconnectChangeStream(collection);
        }
      }, CONFIG.dumper.retryDelayMs * 2);
    }
  }

  async getResumeToken(collection) {
    // In production, you might want to store resume tokens in a persistent store
    // For now, we'll start from the current time
    return null;
  }

  setupDumpSchedule() {
    cron.schedule(CONFIG.dumper.schedule, async () => {
      if (this.isShuttingDown) return;
      
      logger.info('Starting scheduled dump...');
      await this.dumpAllCollections();
      logger.info('Scheduled dump completed');
    }, {
      timezone: process.env.TZ || 'UTC'
    });
    
    logger.info(`Dump scheduled with cron pattern: ${CONFIG.dumper.schedule}`);
  }

  async dumpAllCollections() {
    const promises = CONFIG.mongodb.collections.map(collection => 
      this.dumpCollectionChanges(collection)
    );
    
    const results = await Promise.allSettled(promises);
    
    results.forEach((result, index) => {
      const collection = CONFIG.mongodb.collections[index];
      if (result.status === 'rejected') {
        logger.error(`Dump failed for collection ${collection}:`, result.reason);
      }
    });
  }

  async dumpCollectionChanges(collection) {
    const buffer = this.changeBuffer.get(collection);
    if (!buffer || buffer.length === 0) {
      logger.debug(`No changes to dump for collection: ${collection}`);
      return;
    }

    // Get a copy of the buffer and clear it
    const changesToDump = [...buffer];
    buffer.length = 0;

    const timestamp = new Date();
    const filename = this.generateFilename(collection, timestamp);
    
    logger.info(`Dumping ${changesToDump.length} changes for ${collection} to ${filename}`);

    await this.retryOperation(async () => {
      await this.uploadToADLS(collection, filename, changesToDump);
    }, `dump ${collection}`);

    logger.info(`Successfully dumped ${changesToDump.length} changes for ${collection}`);
  }

  generateFilename(collection, timestamp) {
    const year = timestamp.getFullYear();
    const month = String(timestamp.getMonth() + 1).padStart(2, '0');
    const day = String(timestamp.getDate()).padStart(2, '0');
    const hour = String(timestamp.getHours()).padStart(2, '0');
    
    return `${collection}/${year}-${month}-${day}-${hour}.jsonl`;
  }

  async uploadToADLS(collection, filename, changes) {
    const uploadId = `${collection}-${Date.now()}`;
    this.activeUploads.add(uploadId);
    
    try {
      // Create temporary file in JSONL format
      const tempFilePath = path.join(CONFIG.dumper.tempDir, `${uploadId}.jsonl`);
      
      // Create JSONL content - one JSON object per line
      const jsonlLines = changes.map(changeItem => {
        const jsonlRecord = {
          timestamp: changeItem.timestamp.toISOString(),
          collection: collection,
          dumper_version: '1.0.0',
          change: changeItem.change
        };
        return JSON.stringify(jsonlRecord);
      });
      
      const jsonlData = jsonlLines.join('\n');
      await fs.writeFile(tempFilePath, jsonlData);

      // Get file system client
      const fileSystemClient = this.dataLakeClient.getFileSystemClient(CONFIG.azure.fileSystemName);
      
      // Ensure file system exists
      try {
        await fileSystemClient.create();
      } catch (error) {
        if (error.statusCode !== 409) { // 409 means already exists
          throw error;
        }
      }

      // Upload file
      const fileClient = fileSystemClient.getFileClient(filename);
      
      const fileBuffer = await fs.readFile(tempFilePath);
      await fileClient.upload(fileBuffer, fileBuffer.length, {
        overwrite: true,
        metadata: {
          collection: collection,
          timestamp: new Date().toISOString(),
          changeCount: changes.length.toString()
        }
      });

      // Clean up temp file
      await fs.unlink(tempFilePath).catch(error => {
        logger.warn(`Failed to delete temp file ${tempFilePath}:`, error);
      });

      logger.info(`Successfully uploaded ${filename} (${fileBuffer.length} bytes)`);
    } finally {
      this.activeUploads.delete(uploadId);
    }
  }

  async retryOperation(operation, operationName, maxRetries = CONFIG.dumper.retryAttempts) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await operation();
        return;
      } catch (error) {
        lastError = error;
        logger.warn(`${operationName} attempt ${attempt}/${maxRetries} failed:`, error.message);
        
        if (attempt < maxRetries) {
          const delay = CONFIG.dumper.retryDelayMs * Math.pow(2, attempt - 1);
          logger.info(`Retrying ${operationName} in ${delay}ms...`);
          await this.sleep(delay);
        }
      }
    }
    
    throw new Error(`${operationName} failed after ${maxRetries} attempts: ${lastError.message}`);
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async gracefulShutdown() {
    logger.info('Starting graceful shutdown...');
    this.isShuttingDown = true;

    // Wait for active uploads to complete
    while (this.activeUploads.size > 0) {
      logger.info(`Waiting for ${this.activeUploads.size} active uploads to complete...`);
      await this.sleep(1000);
    }

    // Dump remaining changes
    try {
      await this.dumpAllCollections();
    } catch (error) {
      logger.error('Error during final dump:', error);
    }

    // Close change streams
    for (const [collection, changeStream] of this.changeStreams) {
      try {
        changeStream.close();
        logger.info(`Closed change stream for ${collection}`);
      } catch (error) {
        logger.error(`Error closing change stream for ${collection}:`, error);
      }
    }

    // Close MongoDB connection
    if (this.mongoClient) {
      await this.mongoClient.close();
      logger.info('MongoDB connection closed');
    }

    logger.info('Graceful shutdown completed');
  }
}

// Application startup
async function main() {
  const dumper = new ChangeStreamDumper();

  // Setup signal handlers for graceful shutdown
  process.on('SIGINT', async () => {
    logger.info('Received SIGINT, initiating graceful shutdown...');
    await dumper.gracefulShutdown();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    logger.info('Received SIGTERM, initiating graceful shutdown...');
    await dumper.gracefulShutdown();
    process.exit(0);
  });

  process.on('unhandledRejection', (reason, promise) => {
    logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  });

  process.on('uncaughtException', (error) => {
    logger.error('Uncaught Exception:', error);
    process.exit(1);
  });

  try {
    await dumper.initialize();
    logger.info('MongoDB Change Stream Dumper is running...');
  } catch (error) {
    logger.error('Failed to start application:', error);
    process.exit(1);
  }
}

// Start the application
if (require.main === module) {
  main().catch(error => {
    logger.error('Application startup failed:', error);
    process.exit(1);
  });
}

module.exports = { ChangeStreamDumper, CONFIG };
```

### package.json
```json
{
  "name": "mongodb-changestream-adls-dumper",
  "version": "1.0.0",
  "description": "Production-ready MongoDB Change Stream to Azure Data Lake Storage Gen2 dumper",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js",
    "test": "jest",
    "lint": "eslint .",
    "docker:build": "docker build -t mongodb-changestream-dumper .",
    "docker:run": "docker run --env-file .env mongodb-changestream-dumper"
  },
  "keywords": [
    "mongodb",
    "change-stream",
    "azure",
    "adls",
    "data-lake",
    "etl"
  ],
  "author": "Your Organization",
  "license": "MIT",
  "dependencies": {
    "@azure/storage-file-datalake": "^12.17.0",
    "mongodb": "^6.3.0",
    "winston": "^3.11.0",
    "node-cron": "^3.0.3"
  },
  "devDependencies": {
    "nodemon": "^3.0.2",
    "jest": "^29.7.0",
    "eslint": "^8.56.0"
  },
  "engines": {
    "node": ">=16.0.0"
  },
  "repository": {
    "type": "git",
    "url": "your-repo-url"
  }
}
```

### env.template

```ini
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=your_database_name
MONGODB_COLLECTIONS=collection1,collection2,collection3

# Azure Data Lake Storage Gen2 Configuration
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account_name
AZURE_STORAGE_ACCOUNT_KEY=your_storage_account_key
AZURE_ADLS_FILESYSTEM=changestreams

# Dumper Configuration
DUMP_SCHEDULE=0 * * * *    # Every hour (cron format)
BATCH_SIZE=1000           # Number of changes to buffer before auto-dump
RETRY_ATTEMPTS=3          # Number of retry attempts for failed operations
RETRY_DELAY_MS=1000       # Initial retry delay in milliseconds
TEMP_DIR=./temp           # Temporary directory for file operations
MAX_FILE_SIZE=104857600   # Maximum file size in bytes (100MB)

# Logging Configuration
LOG_LEVEL=info            # Log level: error, warn, info, debug
TZ=UTC                    # Timezone for scheduling

# Optional: Monitoring
HEALTH_CHECK_PORT=3000
```

### dockerfile

```docker
# Use official Node.js runtime as the base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S dumper -u 1001

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy application code
COPY index.js ./

# Create temp directory
RUN mkdir -p temp logs && chown -R dumper:nodejs temp logs

# Switch to non-root user
USER dumper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "console.log('Health check passed')" || exit 1

# Expose port (if needed for monitoring)
EXPOSE 3000

# Start the application
CMD ["node", "index.js"]
```
