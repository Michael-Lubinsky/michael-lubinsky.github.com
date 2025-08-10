## GROK

Please write Node.js program which reads from Azure EventHub and serialize into Azure Data Lake Storage Gen2 (ADLS v2) with partitioned folders like:
Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/

Rolling file name: events-YYYYMMDD-HH.jsonl with 1 json line per event.
```js
const { EventHubConsumerClient } = require("@azure/event-hubs");
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");

// Load environment variables
const EVENT_HUB_CONNECTION_STRING = process.env.EVENT_HUB_CONNECTION_STRING;
const EVENT_HUB_NAME = process.env.EVENT_HUB_NAME;
const CONSUMER_GROUP = process.env.CONSUMER_GROUP || "$Default";
const STORAGE_ACCOUNT_NAME = process.env.STORAGE_ACCOUNT_NAME;
const FILE_SYSTEM_NAME = process.env.FILE_SYSTEM_NAME;
const DB_NAME = process.env.DB_NAME || "mydb";
const COLLECTION_NAME = process.env.COLLECTION_NAME || "mycollection";

// Validate required env vars
if (!EVENT_HUB_CONNECTION_STRING || !EVENT_HUB_NAME || !STORAGE_ACCOUNT_NAME || !FILE_SYSTEM_NAME) {
  console.error("Missing required environment variables.");
  process.exit(1);
}

// DataLakeServiceClient setup
const serviceClient = new DataLakeServiceClient(
  `https://${STORAGE_ACCOUNT_NAME}.dfs.core.windows.net`,
  new DefaultAzureCredential()
);
const fileSystemClient = serviceClient.getFileSystemClient(FILE_SYSTEM_NAME);

// Batching setup
const batches = new Map();
const BATCH_SIZE = 1000; // Flush when batch reaches this size
const FLUSH_INTERVAL = 10000; // Flush every 10 seconds

// Function to append data to a file in ADLS Gen2
async function appendToFile(path, data) {
  const fileClient = fileSystemClient.getFileClient(path);
  const exists = await fileClient.exists();
  if (!exists) {
    await fileClient.create();
  }
  const buffer = Buffer.from(data, "utf8");
  const contentLength = buffer.length;
  const properties = await fileClient.getProperties();
  const position = properties.contentLength || 0;
  await fileClient.append(buffer, position, contentLength);
  await fileClient.flush(position + contentLength);
}

// Function to flush a specific batch
async function flush(path) {
  const lines = batches.get(path);
  if (lines && lines.length > 0) {
    const data = lines.join("");
    await appendToFile(path, data);
    batches.set(path, []); // Reset batch
  }
}

// Periodic flush for all batches
setInterval(async () => {
  for (const path of batches.keys()) {
    await flush(path);
  }
}, FLUSH_INTERVAL);

// Handle graceful shutdown
process.on("SIGTERM", async () => {
  console.log("Flushing remaining batches...");
  for (const path of batches.keys()) {
    await flush(path);
  }
  process.exit(0);
});
process.on("SIGINT", async () => {
  console.log("Flushing remaining batches...");
  for (const path of batches.keys()) {
    await flush(path);
  }
  process.exit(0);
});

// EventHub setup
const consumerClient = new EventHubConsumerClient(
  CONSUMER_GROUP,
  EVENT_HUB_CONNECTION_STRING,
  EVENT_HUB_NAME
);

const subscription = consumerClient.subscribe(
  {
    processEvents: async (events, context) => {
      for (const event of events) {
        const time = event.enqueuedTimeUtc;
        const yyyy = time.getUTCFullYear();
        const mm = String(time.getUTCMonth() + 1).padStart(2, "0");
        const dd = String(time.getUTCDate()).padStart(2, "0");
        const hh = String(time.getUTCHours()).padStart(2, "0");
        const fileName = `events-${yyyy}${mm}${dd}-${hh}.jsonl`;
        const partitionPath = `${DB_NAME}/${COLLECTION_NAME}/year=${yyyy}/month=${mm}/day=${dd}/hour=${hh}/${fileName}`;

        const jsonLine = JSON.stringify(event.body) + "\n";

        if (!batches.has(partitionPath)) {
          batches.set(partitionPath, []);
        }
        batches.get(partitionPath).push(jsonLine);

        if (batches.get(partitionPath).length >= BATCH_SIZE) {
          await flush(partitionPath);
        }
      }
    },
    processError: async (error, context) => {
      console.error("Error processing events:", error);
    },
  },
  { startingPosition: "@latest" } // Start from the latest events
);

console.log("Consumer started. Press Ctrl+C to stop.");
```
