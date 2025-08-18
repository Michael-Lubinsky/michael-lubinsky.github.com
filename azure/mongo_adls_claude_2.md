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

```json
{
  "metadata": {
    "collection": "users",
    "timestamp": "2024-01-15T14:30:00.000Z",
    "count": 250,
    "dumper_version": "1.0.0"
  },
  "changes": [
    {
      "timestamp": "2024-01-15T14:15:23.123Z",
      "change": {
        "_id": {"_data": "..."},
        "operationType": "insert",
        "fullDocument": {...},
        "ns": {"db": "mydb", "coll": "users"},
        "documentKey": {"_id": "..."}
      }
    }
  ]
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
