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
## program which every hour reads the files created by previous script and uploaded them into Snowflake  bronze database tables using Snowflake copy command.

The Snowflake table name should match the collection name.

Planning script implementation
Snowflake supports loading NDJSON files directly with TYPE = JSON, parsing each line as a separate JSON object.

The program needs to install snowflake-sdk via npm for Snowflake connectivity.

Let's consider using SAS tokens for secure Azure access in the script.

Environment variables will likely include Snowflake connection details like account and user.

For scheduling, setInterval can run the script every hour in Node.js.
Configuring SAS token generation
The script needs STORAGE_ACCOUNT_KEY in environment variables to generate SAS tokens.

SAS tokens expire after 24 hours, ensuring read access for Azure storage.

Next, let's plan how to handle file existence checks in the script.

```js
const snowflake = require('snowflake-sdk');
const { StorageSharedKeyCredential, generateDataLakeSASQueryParameters, DataLakeSASPermissions } = require("@azure/storage-file-datalake");

// Load environment variables
const EVENT_HUB_CONNECTION_STRING = process.env.EVENT_HUB_CONNECTION_STRING; // Not used, but for consistency
const EVENT_HUB_NAME = process.env.EVENT_HUB_NAME; // Not used
const CONSUMER_GROUP = process.env.CONSUMER_GROUP || "$Default"; // Not used
const STORAGE_ACCOUNT_NAME = process.env.STORAGE_ACCOUNT_NAME;
const STORAGE_ACCOUNT_KEY = process.env.STORAGE_ACCOUNT_KEY;
const FILE_SYSTEM_NAME = process.env.FILE_SYSTEM_NAME;
const DB_NAME = process.env.DB_NAME || "mydb";
const COLLECTION_NAME = process.env.COLLECTION_NAME || "mycollection";
const SNOWFLAKE_ACCOUNT = process.env.SNOWFLAKE_ACCOUNT;
const SNOWFLAKE_USER = process.env.SNOWFLAKE_USER;
const SNOWFLAKE_PASSWORD = process.env.SNOWFLAKE_PASSWORD;
const SNOWFLAKE_DATABASE = process.env.SNOWFLAKE_DATABASE || "BRONZE";
const SNOWFLAKE_SCHEMA = process.env.SNOWFLAKE_SCHEMA || "PUBLIC";

// Validate required env vars
if (!STORAGE_ACCOUNT_NAME || !STORAGE_ACCOUNT_KEY || !FILE_SYSTEM_NAME || !SNOWFLAKE_ACCOUNT || !SNOWFLAKE_USER || !SNOWFLAKE_PASSWORD) {
  console.error("Missing required environment variables.");
  process.exit(1);
}

// Snowflake connection
const connection = snowflake.createConnection({
  account: SNOWFLAKE_ACCOUNT,
  username: SNOWFLAKE_USER,
  password: SNOWFLAKE_PASSWORD,
  database: SNOWFLAKE_DATABASE,
  schema: SNOWFLAKE_SCHEMA,
});

connection.connect((err, conn) => {
  if (err) {
    console.error("Unable to connect to Snowflake:", err);
    process.exit(1);
  }
  console.log("Connected to Snowflake.");
});

// Function to generate SAS token for a directory
function generateSasToken(directoryPath) {
  const credential = new StorageSharedKeyCredential(STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY);
  const sasOptions = {
    fileSystemName: FILE_SYSTEM_NAME,
    pathName: directoryPath,
    permissions: DataLakeSASPermissions.parse("r"),
    startsOn: new Date(),
    expiresOn: new Date(Date.now() + 3600 * 1000 * 24), // 24 hours
  };
  const sasQueryParameters = generateDataLakeSASQueryParameters(sasOptions, credential);
  return sasQueryParameters.toString();
}

// Function to load data for a specific hour partition
async function loadHourPartition(yyyy, mm, dd, hh) {
  const directoryPath = `${DB_NAME}/${COLLECTION_NAME}/year=${yyyy}/month=${mm}/day=${dd}/hour=${hh}/`;
  const sasToken = generateSasToken(directoryPath);
  const url = `azure://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${FILE_SYSTEM_NAME}/${directoryPath}?${sasToken}`;

  const sql = `
    COPY INTO ${COLLECTION_NAME}
    FROM '${url}'
    FILE_FORMAT = (TYPE = 'JSON' COMPRESSION = 'NONE')
    PATTERN = '.*\\.jsonl';
  `;

  return new Promise((resolve, reject) => {
    connection.execute({
      sqlText: sql,
      complete: (err, stmt, rows) => {
        if (err) {
          console.error(`Failed to execute COPY for ${yyyy}-${mm}-${dd} ${hh}:`, err);
          reject(err);
        } else {
          console.log(`Successfully loaded data for ${yyyy}-${mm}-${dd} ${hh}. Rows loaded: ${stmt.getNumRowsLoaded()}`);
          resolve(rows);
        }
      }
    });
  });
}

// Function to compute and load previous hour
async function loadPreviousHour() {
  const now = new Date();
  const previous = new Date(now.getTime() - 3600000);
  const yyyy = previous.getUTCFullYear();
  const mm = String(previous.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(previous.getUTCDate()).padStart(2, "0");
  const hh = String(previous.getUTCHours()).padStart(2, "0");

  console.log(`Loading data for ${yyyy}-${mm}-${dd} ${hh}...`);
  try {
    await loadHourPartition(yyyy, mm, dd, hh);
  } catch (err) {
    console.error("Error loading previous hour:", err);
  }
}

// Run every hour (3600000 ms)
setInterval(loadPreviousHour, 3600000);

// Run once on startup for the immediate previous hour
loadPreviousHour();

// Handle graceful shutdown
process.on("SIGTERM", () => {
  console.log("Terminating...");
  connection.destroy();
  process.exit(0);
});
process.on("SIGINT", () => {
  console.log("Terminating...");
  connection.destroy();
  process.exit(0);
});

console.log("Loader started. Running every hour.");
```
## Snowflake task which will read from the bronze tables every hour the new json records added in last hour   
extract some json attributes and store in silver layer tables.


```
-- Assume the bronze table is created with the following structure (if not, create it accordingly)
CREATE TABLE IF NOT EXISTS BRONZE.PUBLIC.mycollection (
    data VARIANT,
    load_time TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Note: Update the COPY INTO command in the Node.js loader script to include the load_time column:
-- COPY INTO mycollection (data, load_time)
-- FROM (SELECT parse_json($1), CURRENT_TIMESTAMP() FROM '${url}')
-- FILE_FORMAT = (TYPE = 'JSON' COMPRESSION = 'NONE')
-- PATTERN = '.*\\.jsonl';

-- Create the silver schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS BRONZE.SILVER;

-- Create the silver table with extracted attributes (assuming JSON structure has id, user_id, event_type, event_timestamp)
CREATE TABLE IF NOT EXISTS BRONZE.SILVER.mycollection (
    id STRING,
    user_id STRING,
    event_type STRING,
    event_timestamp TIMESTAMP_NTZ,
    load_time TIMESTAMP_NTZ
);

-- Create a stream on the bronze table to capture new inserts
CREATE STREAM IF NOT EXISTS BRONZE.PUBLIC.mycollection_stream ON TABLE BRONZE.PUBLIC.mycollection APPEND_ONLY = TRUE;

-- Create the task to run every hour
CREATE TASK IF NOT EXISTS BRONZE.PUBLIC.process_mycollection_to_silver
    WAREHOUSE = 'COMPUTE_WH'  -- Replace with your warehouse name
    SCHEDULE = '60 MINUTE'
AS
    INSERT INTO BRONZE.SILVER.mycollection (id, user_id, event_type, event_timestamp, load_time)
    SELECT 
        data:id::STRING AS id,
        data:user_id::STRING AS user_id,
        data:event_type::STRING AS event_type,
        data:event_timestamp::TIMESTAMP_NTZ AS event_timestamp,
        load_time
    FROM BRONZE.PUBLIC.mycollection_stream
    WHERE load_time >= DATEADD(HOUR, -1, CURRENT_TIMESTAMP());

-- Resume the task to start scheduling
ALTER TASK BRONZE.PUBLIC.process_mycollection_to_silver RESUME;
```
