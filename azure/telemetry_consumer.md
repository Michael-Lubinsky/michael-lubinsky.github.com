 This code sets up an **Azure Event Hubs consumer** that continuously processes telemetry events.  

index.ts
```js
         const options = {
            fileSystemClient: failuresFs,
            dbClient,
            maxRetries: parseInt(env('RETRY_LIMIT'), 10),
            telemetryHubProducer: producer,
        };
        // Sets up event hub producer for sending telemetry events
        configureTelemetryHub(producer);

        const settings: SubscribeOptions = {
            maxBatchSize: 5_000,
            maxWaitTimeInSeconds: toInteger(env('TELEMETRY_STREAM_MAX_WAIT_TIME')),
            startPosition: {
                enqueuedOn: new Date(),
            },
        };

        logger.info(`Transformer settings: ${JSON.stringify(settings)}`);

        let count = 0;
        let lastCheckpoint = new Date();

        setInterval(() => {
            logger.info(`[${processorIdentifier}] processed ${count} events. ${new Date().toString()}`);
            count = 0;
        }, 60_000);

        telemetryHubConsumer.subscribe({
            processEvents: async (events, context) => {
                if (events.length === 0) return;
                await processTelemetryEvents(events, context.partitionId, options);
                count += events.length;
                if (new Date().getTime() - lastCheckpoint.getTime() > 60_000) {
                    lastCheckpoint = new Date();
                    await context.updateCheckpoint(events[events.length - 1]);
                }
            },
            processError: async (err) => logger.error(err, 'Error processing events'),
        }, settings);

        // logs the backpressure of the queue on a regular interval
        SequenceLogger.instance().start(telemetryHubConsumer, checkpointStore);

        sendTelemetryEvent(TelemetryEvent.StartUp, { date: new Date().toString() }).catch((err) => logger.error(err, 'Error sending startup telemetry event'));

        // For non-local environments, create a file for liveness probe
        if (process.env.SETUP_LIVENESS_PROBE === 'true') {
            fs.writeFileSync('/tmp/healthy', 'healthy');
        }
```
## 1. Configuration Setup

```typescript
const options = {
    fileSystemClient: failuresFs,
    dbClient,
    maxRetries: parseInt(env('RETRY_LIMIT'), 10),
    telemetryHubProducer: producer,
};
```

**Purpose:** Bundles all dependencies needed for processing events:
- `fileSystemClient` - Azure Data Lake storage client for writing failed events
- `dbClient` - PostgreSQL/TimescaleDB client for inserting events
- `maxRetries` - How many times to retry failed events before giving up
- `telemetryHubProducer` - For re-queuing failed events or sending telemetry

## 2. Telemetry Hub Configuration

```typescript
configureTelemetryHub(producer);
```

**Purpose:** Sets up the Event Hub producer for sending monitoring/telemetry events about the application itself (not the data being processed).

## 3. Subscription Settings

```typescript
const settings: SubscribeOptions = {
    maxBatchSize: 5_000,
    maxWaitTimeInSeconds: toInteger(env('TELEMETRY_STREAM_MAX_WAIT_TIME')),
    startPosition: {
        enqueuedOn: new Date(),
    },
};
```

**Purpose:** Configures how the consumer reads from Event Hubs:
- `maxBatchSize: 5_000` - Process up to 5,000 events at once per batch
- `maxWaitTimeInSeconds` - How long to wait before processing a partial batch (from env variable)
- `startPosition: { enqueuedOn: new Date() }` - Start reading events from NOW (ignore old backlog)

## 4. Metrics Counter

```typescript
let count = 0;
let lastCheckpoint = new Date();

setInterval(() => {
    logger.info(`[${processorIdentifier}] processed ${count} events. ${new Date().toString()}`);
    count = 0;
}, 60_000);
```

**Purpose:** Logs processing metrics every 60 seconds (60,000 ms):
- Tracks how many events were processed in the last minute
- Resets counter after logging
- Helps monitor throughput (e.g., "processed 12,543 events")

## 5. Main Event Processing Loop

```typescript
telemetryHubConsumer.subscribe({
    processEvents: async (events, context) => {
        if (events.length === 0) return;
        await processTelemetryEvents(events, context.partitionId, options);
        count += events.length;
        if (new Date().getTime() - lastCheckpoint.getTime() > 60_000) {
            lastCheckpoint = new Date();
            await context.updateCheckpoint(events[events.length - 1]);
        }
    },
    processError: async (err) => logger.error(err, 'Error processing events'),
}, settings);
```

**Purpose:** The heart of the consumer - subscribes to Event Hubs and processes incoming events:

### `processEvents` callback:
1. **Receives batches** of events (up to 5,000 at a time)
2. **Early return** if batch is empty
3. **Process events** by calling `processTelemetryEvents()` which:
   - Parses events
   - Writes to CSV (ADLS Gen2)
   - Inserts into database
   - Transforms to silver tables
4. **Updates counter** for metrics
5. **Checkpoints every 60 seconds**:
   - Tells Event Hubs "I've successfully processed up to this point"
   - If the app crashes and restarts, it resumes from the last checkpoint
   - Only checkpoints every 60 seconds to reduce overhead

### `processError` callback:
- Logs any errors that occur during event processing
- Doesn't stop the consumer - it continues processing

## 6. Queue Backpressure Monitoring

```typescript
SequenceLogger.instance().start(telemetryHubConsumer, checkpointStore);
```

**Purpose:** Starts a background monitor that logs how far behind the consumer is:
- Compares the latest sequence number in Event Hubs vs. the consumer's position
- Helps identify if the consumer is falling behind (backpressure)

## 7. Startup Telemetry

```typescript
sendTelemetryEvent(TelemetryEvent.StartUp, { date: new Date().toString() })
    .catch((err) => logger.error(err, 'Error sending startup telemetry event'));
```

**Purpose:** Sends a telemetry event to track when the application starts:
- Useful for monitoring deployments and restarts
- Errors are logged but don't crash the app

## 8. Liveness Probe

```typescript
if (process.env.SETUP_LIVENESS_PROBE === 'true') {
    fs.writeFileSync('/tmp/healthy', 'healthy');
}
```

**Purpose:** Kubernetes/container orchestration support:
- Creates a file that Kubernetes can check to verify the app is running
- Kubernetes will restart the pod if this file doesn't exist or becomes stale
- Common pattern for health checks in containerized environments

## High-Level Flow Summary

```
┌─────────────────────────────────────────────────────────┐
│  Azure Event Hubs (Incoming Telemetry Stream)           │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Consumer subscribes and receives batches (up to 5,000) │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  processTelemetryEvents()                                │
│  • Parse events                                          │
│  • Write CSV to ADLS Gen2                               │
│  • Insert into PostgreSQL/TimescaleDB                    │
│  • Transform to silver tables                            │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Every 60 seconds:                                       │
│  • Log metrics (events processed)                        │
│  • Checkpoint progress                                   │
└─────────────────────────────────────────────────────────┘
```

This is essentially a **streaming ETL pipeline** that:
- Continuously reads from Event Hubs
- Processes events in batches
- Stores data in multiple formats (CSV + Database)
- Monitors performance
- Handles failures gracefully

Does this help clarify what's happening? 🎯
