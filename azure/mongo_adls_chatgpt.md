### ChatGPT
Node.js program which reads from Azure EventHub and serialize into Azure Data Lake Storage Gen2 (ADLS v2) with partitioned folders like:
Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/

Rolling file name: events-YYYYMMDD-HH.jsonl 
with 1 json line per event 


## Node.js: Azure Event Hubs → ADLS Gen2 (Rolling Hourly JSONL, 1 line per event)

Below is a production-ready Node.js program that:
- Reads from **Azure Event Hubs** using `@azure/event-hubs`
- Writes to **Azure Data Lake Storage Gen2** using `@azure/storage-file-datalake`
- Stores events as **rolling hourly JSONL** files (one JSON object per line)
- Partition path: `db/collection/year=YYYY/month=MM/day=DD/hour=HH/`
- Rolling file name: `events-YYYYMMDD-HH.jsonl`
- Tracks ADLS append offsets to safely append
- Sensible defaults with environment variables; supports AAD/Shared Key/SAS auth

---

## 1) Install
```
npm init -y
npm i @azure/event-hubs @azure/storage-file-datalake @azure/identity p-limit
```

---

## 2) Environment

Create `.env` (or export vars):

Event Hubs
```ini
EVENTHUBS_CONNECTION_STRING="Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=<hub-name>"
EVENTHUB_NAME="<hub-name>"
EVENTHUB_CONSUMER_GROUP="$Default" # or your group name

Optional defaults for db/collection if events don't carry them
DEFAULT_DB="database1"
DEFAULT_COLLECTION="collection1"

ADLS Gen2
ADLS_ACCOUNT_URL="https://<account>.dfs.core.windows.net"
ADLS_FILESYSTEM="raw"

Auth option A: Shared Key
ADLS_SHARED_KEY=""

Auth option B: SAS token (either append to URL or set here)
ADLS_SAS=""

Auth option C: AAD (Managed Identity or Service Principal)
AZURE_CLIENT_ID=""
AZURE_TENANT_ID=""
AZURE_CLIENT_SECRET=""

Writer
MAX_CONCURRENCY="8" # max concurrent appends
MAX_FILE_BYTES="0" # 0 = only hourly roll; set e.g. 268435456 for 256MiB size roll

```

Events should include `db` and `collection` in either:
- Application properties: `event.properties.db`, `event.properties.collection`
- Body (JSON): `event.body.db`, `event.body.collection`
If absent, code falls back to `DEFAULT_DB` and `DEFAULT_COLLECTION`.

 

## 3) Program: `eventhub-to-adls-jsonl.js`

```js
'use strict';

/**
 * Azure Event Hubs → ADLS Gen2 (Rolling Hourly JSONL)
 *
 * Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/
 * File name:      events-YYYYMMDD-HH.jsonl
 *
 * - One JSON object per line
 * - Tracks ADLS append offsets (append + flush)
 * - Serializes appends per file to avoid race conditions
 */

const { EventHubConsumerClient, earliestEventPosition } = require('@azure/event-hubs');
const { DataLakeServiceClient, StorageSharedKeyCredential } = require('@azure/storage-file-datalake');
const { DefaultAzureCredential, ClientSecretCredential } = require('@azure/identity');
const pLimit = require('p-limit');
const fs = require('fs');

function getEnv(name, required = false, fallback = undefined) {
  const v = process.env[name];
  if (required && (!v || v.trim() === '')) throw new Error(`Missing env var: ${name}`);
  return (v ?? fallback)?.toString().trim();
}

function pad2(n) { return String(n).padStart(2, '0'); }

function enqueuedToParts(d) {
  const year = d.getUTCFullYear();
  const month = pad2(d.getUTCMonth() + 1);
  const day = pad2(d.getUTCDate());
  const hour = pad2(d.getUTCHours());
  return { year, month, day, hour, yyyymmdd: `${year}${month}${day}` };
}

function pickDbCollection(evt, defaults) {
  // Priority: application properties -> body -> defaults
  let db = evt.properties?.db;
  let collection = evt.properties?.collection;

  const body = evt.body;
  if ((!db || !collection) && body && typeof body === 'object') {
    db = db || body.db;
    collection = collection || body.collection;
  }
  db = (db || defaults.db || 'unknown_db').toString();
  collection = (collection || defaults.collection || 'unknown_coll').toString();
  return { db, collection };
}

function normalizeBody(body) {
  // Ensure serializable JSON without blowing up on Buffers
  if (Buffer.isBuffer(body)) {
    return { base64: body.toString('base64') };
  }
  if (typeof body === 'string') {
    try { return JSON.parse(body); } catch { return { text: body }; }
  }
  return body;
}

function makeLine(eventData) {
  const obj = {
    enqueuedTime: eventData.enqueuedTimeUtc?.toISOString?.() || null,
    sequenceNumber: eventData.sequenceNumber ?? null,
    offset: eventData.offset ?? null,
    partitionKey: eventData.partitionKey ?? null,
    properties: eventData.properties ?? {},
    systemProperties: eventData.systemProperties ?? {},
    body: normalizeBody(eventData.body)
  };
  return Buffer.from(JSON.stringify(obj) + '\n', 'utf8');
}

async function buildFsClient() {
  const accountUrl = getEnv('ADLS_ACCOUNT_URL', true);
  const fsName = getEnv('ADLS_FILESYSTEM', true);

  const sas = getEnv('ADLS_SAS');
  const key = getEnv('ADLS_SHARED_KEY');

  let serviceClient;
  if (sas) {
    const url = accountUrl.includes('?') ? accountUrl : `${accountUrl}?${sas}`;
    serviceClient = new DataLakeServiceClient(url);
  } else if (key) {
    const accountName = new URL(accountUrl).host.split('.')[0];
    const cred = new StorageSharedKeyCredential(accountName, key);
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  } else {
    // AAD (Managed Identity or SP)
    const clientId = getEnv('AZURE_CLIENT_ID');
    const tenantId = getEnv('AZURE_TENANT_ID');
    const clientSecret = getEnv('AZURE_CLIENT_SECRET');
    const cred = (clientId && tenantId && clientSecret)
      ? new ClientSecretCredential(tenantId, clientId, clientSecret)
      : new DefaultAzureCredential();
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  }

  const fsClient = serviceClient.getFileSystemClient(fsName);
  await fsClient.createIfNotExists();
  return fsClient;
}

class RollingFileWriter {
  constructor(fsClient, opts = {}) {
    this.fsClient = fsClient;
    this.dirCache = new Map();   // dirPath -> dirClient
    this.files = new Map();      // key -> { fileClient, offset, lock, path }
    this.maxBytes = Number(getEnv('MAX_FILE_BYTES', false, '0')) || 0;
    this.limiter = pLimit(Number(getEnv('MAX_CONCURRENCY', false, '8')) || 8);
  }

  async ensureDir(dirPath) {
    if (this.dirCache.has(dirPath)) return this.dirCache.get(dirPath);
    const dirClient = this.fsClient.getDirectoryClient(dirPath);
    await dirClient.createIfNotExists();
    this.dirCache.set(dirPath, dirClient);
    return dirClient;
  }

  key(dirPath, fileName) { return `${dirPath}::${fileName}`; }

  async openFile(dirClient, dirPath, fileName) {
    const k = this.key(dirPath, fileName);
    if (this.files.has(k)) return this.files.get(k);
    const fileClient = dirClient.getFileClient(fileName);
    let offset = 0;
    if (await fileClient.exists()) {
      const props = await fileClient.getProperties();
      offset = Number(props.contentLength || 0);
    } else {
      await fileClient.create();
    }
    const entry = { fileClient, offset, lock: Promise.resolve(), path: `${dirPath}/${fileName}` };
    this.files.set(k, entry);
    return entry;
  }

  async append(dirPath, fileName, bodyBuf) {
    return this.limiter(async () => {
      const dir = await this.ensureDir(dirPath);
      const entry = await this.openFile(dir, dirPath, fileName);

      // Optional size-based rolling
      if (this.maxBytes > 0 && (entry.offset + bodyBuf.length) > this.maxBytes) {
        const rolled = fileName.replace(/\.jsonl$/i, '') + `-part-${Date.now()}.jsonl`;
        const newEntry = await this.openFile(dir, dirPath, rolled);
        return this._appendLocked(newEntry, bodyBuf);
      }
      return this._appendLocked(entry, bodyBuf);
    });
  }

  async _appendLocked(entry, buf) {
    entry.lock = entry.lock.then(async () => {
      const start = entry.offset;
      await entry.fileClient.append(buf, start, buf.length);
      const newLen = start + buf.length;
      await entry.fileClient.flush(newLen);
      entry.offset = newLen;
    }).catch((err) => {
      console.error(`Append error for ${entry.path}:`, err);
    });
    return entry.lock;
  }
}

function targetPath(db, coll, enqDate) {
  const { year, month, day, hour, yyyymmdd } = enqueuedToParts(enqDate);
  const dir = `${db}/${coll}/year=${year}/month=${month}/day=${day}/hour=${hour}`;
  const file = `events-${yyyymmdd}-${hour}.jsonl`;
  return { dir, file };
}

async function main() {
  // Event Hubs
  const ehConn = getEnv('EVENTHUBS_CONNECTION_STRING', true);
  const ehName = getEnv('EVENTHUB_NAME'); // optional; may be embedded in connection string
  const consumerGroup = getEnv('EVENTHUB_CONSUMER_GROUP', false, '$Default');

  // Defaults
  const defaults = {
    db: getEnv('DEFAULT_DB', false, 'unknown_db'),
    collection: getEnv('DEFAULT_COLLECTION', false, 'unknown_coll')
  };

  // ADLS
  const fsClient = await buildFsClient();
  const writer = new RollingFileWriter(fsClient);

  const client = new EventHubConsumerClient(
    consumerGroup,
    ehConn,
    ehName || undefined
  );

  console.log(`Starting Event Hubs consumer on group "${consumerGroup}"...`);

  // Receive from all partitions
  const subscription = client.subscribe(
    {
      processEvents: async (events, context) => {
        if (!events.length) return;

        for (const evt of events) {
          try {
            const enqDate = evt.enqueuedTimeUtc ? new Date(evt.enqueuedTimeUtc) : new Date();
            const { db, collection } = pickDbCollection(evt, defaults);
            const { dir, file } = targetPath(db, collection, enqDate);
            const line = makeLine(evt);
            await writer.append(dir, file, line);
          } catch (err) {
            console.error('Failed to process event:', err);
          }
        }
      },
      processError: async (err, context) => {
        console.error(`Event Hubs error on partition ${context.partitionId}:`, err);
      }
    },
    {
      // Tuning
      maxBatchSize: 100,
      maxWaitTimeInSeconds: 15,
      startPosition: earliestEventPosition // or latestEventPosition
    }
  );

  process.on('SIGINT', async () => {
    console.log('SIGINT received; closing subscription...');
    try { await subscription.close(); } catch {}
    await client.close();
    process.exit(0);
  });
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});
```

### 4) Run
 
node eventhub-to-adls-jsonl.js
Events will be written like:

```
raw/
 └─ database1/
    └─ collection1/
       └─ year=2025/
          └─ month=08/
             └─ day=09/
                └─ hour=21/
                   └─ events-20250809-21.jsonl
```
### 5) Notes
Checkpointing: For production, consider @azure/eventhubs-checkpointstore-blob to persist offsets in Azure Blob Storage so the consumer resumes where it left off after restarts.

Throughput: Increase MAX_CONCURRENCY, maxBatchSize, and scale out multiple consumers (with different consumer groups or Event Processor host pattern) if needed.

Size-based rolling: Set MAX_FILE_BYTES to split large hourly files into ...-part-<epoch>.jsonl.

db/collection tagging: Ensure producers set db / collection either in Event Hubs application properties or in the message body, else defaults are used.
