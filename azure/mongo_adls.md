How to stream MongoDB change events into Azure Data Lake Storage Gen2 (ADLS v2) 
with partitioned folders like:
```
database1/collection1/year=2024/month=01/day=15/
```
It uses:
-- MongoDB Change Streams (Node.js driver)  
-- Azure Data Lake SDK (@azure/storage-file-datalake)  
-- One-object-per-file (simple & reliable).    
At the end you’ll also see how to switch to rolling JSONL files if you prefer bigger files.

### 1) Prereqs
- MongoDB must be a replica set or sharded cluster (Change Streams requirement).  
- Grant a user permission to watch the target collections or database.  
- Node.js 18+ recommended.

Install deps:

```
npm init -y
npm i mongodb @azure/storage-file-datalake uuid p-limit
```
Environment variables (for local dev, put in .env or export in shell):

```ini
# Mongo
MONGO_URI="mongodb+srv://user:pass@cluster.example.mongodb.net/?retryWrites=true&w=majority"
MONGO_DB="database1"            # set if you watch a single db (optional if using client.watch)
MONGO_COLL="collection1"        # set if you watch a single collection (optional)
MONGO_FULL_DOC="updateLookup"   # ensures fullDocument for updates

# Azure ADLS Gen2
ADLS_ACCOUNT_URL="https://<account>.dfs.core.windows.net"
ADLS_FILESYSTEM="raw"           # name of the container/filesystem
ADLS_SAS=""                     # EITHER SAS OR KEY (choose one)
ADLS_SHARED_KEY=""              # storage account key if not using SAS

# Checkpointing (resume token)
RESUME_TOKEN_PATH="./resume-token.json"
```
You can authenticate with either a SAS token or a Storage Account Key. 
If using SAS, include it in ADLS_ACCOUNT_URL  
(e.g., https://acct.dfs.core.windows.net?<sas>),  
or keep it separate and append in code.

### 2) Code (per-event file, partitioned folders)
stream-mongo-to-adls.js:

 
```js
'use strict';

const { MongoClient, Timestamp } = require('mongodb');
const { DataLakeServiceClient, StorageSharedKeyCredential } = require('@azure/storage-file-datalake');
const { randomUUID } = require('uuid');
const fs = require('fs');

function getEnv(name, required = false) {
  const v = process.env[name];
  if (required && (!v || v.trim() === '')) {
    throw new Error(`Missing env var: ${name}`);
  }
  return v;
}

function loadResumeToken(path) {
  try {
    if (fs.existsSync(path)) {
      const txt = fs.readFileSync(path, 'utf8');
      if (txt) return JSON.parse(txt);
    }
  } catch (_) {}
  return null;
}

function saveResumeToken(path, token) {
  try {
    fs.writeFileSync(path, JSON.stringify(token), 'utf8');
  } catch (err) {
    console.error('Failed to persist resume token:', err);
  }
}

function pad2(n) { return String(n).padStart(2, '0'); }

function partitionPathFromEvent(evt) {
  let d;
  if (evt.clusterTime instanceof Timestamp) {
    const seconds = evt.clusterTime.getHighBits();
    d = new Date(seconds * 1000);
  } else if (evt.wallTime) {
    d = new Date(evt.wallTime);
  } else if (evt.fullDocument && evt.fullDocument._id && evt.fullDocument._id.getTimestamp) {
    d = evt.fullDocument._id.getTimestamp();
  } else {
    d = new Date();
  }

  const year = d.getUTCFullYear();
  const month = pad2(d.getUTCMonth() + 1);
  const day = pad2(d.getUTCDate());

  const db = evt.ns?.db ?? 'unknown_db';
  const coll = evt.ns?.coll ?? 'unknown_coll';

  return `${db}/${coll}/year=${year}/month=${month}/day=${day}`;
}

function fileSafeOp(opType) {
  return (opType || 'unknown').toLowerCase();
}

async function getDataLakeFileSystemClient() {
  const accountUrl = getEnv('ADLS_ACCOUNT_URL', true);
  const fsName = getEnv('ADLS_FILESYSTEM', true);
  const sas = getEnv('ADLS_SAS', false);
  const key = getEnv('ADLS_SHARED_KEY', false);

  let serviceClient;
  if (sas && sas.trim() !== '') {
    const url = accountUrl.includes('?') ? accountUrl : `${accountUrl}?${sas}`;
    serviceClient = new DataLakeServiceClient(url);
  } else if (key && key.trim() !== '') {
    const accountName = new URL(accountUrl).host.split('.')[0];
    const cred = new StorageSharedKeyCredential(accountName, key);
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  } else {
    throw new Error('Provide either ADLS_SAS or ADLS_SHARED_KEY credentials.');
  }

  const fsClient = serviceClient.getFileSystemClient(fsName);
  await fsClient.createIfNotExists();
  return fsClient;
}

async function ensureDirectory(fsClient, dirPath) {
  const dirClient = fsClient.getDirectoryClient(dirPath);
  await dirClient.createIfNotExists();
  return dirClient;
}

async function writeEventAsIndividualFile(fsClient, evt) {
  const dirPath = partitionPathFromEvent(evt);
  const dirClient = await ensureDirectory(fsClient, dirPath);

  const op = fileSafeOp(evt.operationType);
  const idPart = evt.documentKey?._id ? String(evt.documentKey._id).replace(/[^a-zA-Z0-9_-]/g, '_') : randomUUID();
  const fileName = `${op}-${idPart}-${Date.now()}.json`;

  const fileClient = dirClient.getFileClient(fileName);

  const payload = {
    _meta: {
      operationType: evt.operationType,
      clusterTime: evt.clusterTime ? evt.clusterTime.toString() : null,
      txnNumber: evt.txnNumber ?? null,
      lsid: evt.lsid ?? null,
      ns: evt.ns ?? null
    },
    documentKey: evt.documentKey ?? null,
    fullDocument: evt.fullDocument ?? null,
    updateDescription: evt.updateDescription ?? null,
    fullDocumentBeforeChange: evt.fullDocumentBeforeChange ?? null
  };

  const body = Buffer.from(JSON.stringify(payload) + '\n', 'utf8');

  await fileClient.create();
  await fileClient.append(body, 0, body.length);
  await fileClient.flush(body.length);
}

async function run() {
  const mongoUri = getEnv('MONGO_URI', true);
  const dbName = getEnv('MONGO_DB', false);
  const collName = getEnv('MONGO_COLL', false);
  const fullDoc = getEnv('MONGO_FULL_DOC', false) || 'updateLookup';
  const resumePath = getEnv('RESUME_TOKEN_PATH', false) || './resume-token.json';

  const fsClient = await getDataLakeFileSystemClient();

  const client = new MongoClient(mongoUri);

  await client.connect();

  let watchTarget;
  if (dbName && collName) {
    watchTarget = client.db(dbName).collection(collName);
    console.log(`Watching collection ${dbName}.${collName}`);
  } else if (dbName) {
    watchTarget = client.db(dbName);
    console.log(`Watching database ${dbName}`);
  } else {
    watchTarget = client;
    console.log(`Watching entire deployment`);
  }

  const resumeToken = loadResumeToken(resumePath);

  const csOpts = {
    fullDocument: fullDoc,
    fullDocumentBeforeChange: 'whenAvailable',
    resumeAfter: resumeToken || undefined,
    batchSize: 100,
    maxAwaitTimeMS: 20000
  };

  const pipeline = [];

  const changeStream = watchTarget.watch(pipeline, csOpts);

  changeStream.on('change', async (evt) => {
    try {
      await writeEventAsIndividualFile(fsClient, evt);
      if (evt._id) {
        saveResumeToken(resumePath, evt._id);
      }
    } catch (err) {
      console.error('Failed to write event to ADLS:', err);
    }
  });

  changeStream.on('error', async (err) => {
    console.error('Change stream error:', err);
    try { await changeStream.close(); } catch (_) {}
    try { await client.close(); } catch (_) {}
    process.exit(1);
  });

  changeStream.on('end', async () => {
    console.warn('Change stream ended.');
    try { await client.close(); } catch (_) {}
  });

  process.on('SIGINT', async () => {
    console.log('SIGINT received, closing...');
    try { await changeStream.close(); } catch (_) {}
    try { await client.close(); } catch (_) {}
    process.exit(0);
  });
}

run().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});
```
Run it:
```
node stream-mongo-to-adls.js
```
As events arrive, you’ll see files like:

```
raw/
 └─ database1/
    └─ collection1/
       └─ year=2025/
          └─ month=08/
             └─ day=10/
                ├─ insert-...json
                ├─ update-...json
                └─ delete-...json
```
### 3) Notes & options
#### A) Scope selection
Collection scope gives the exact db/collection in evt.ns, which your partition path uses.

Database scope works for all collections in a db.

Deployment scope (client.watch) captures all dbs/collections—your partition path will still work  
because it uses evt.ns.db and evt.ns.coll.

#### B) fullDocument on updates
Set fullDocument: 'updateLookup' so evt.fullDocument   
contains the post-image on updates (a second query fetch).

#### C) Resume tokens (reliability)
The script writes evt._id (the resume token) to resume-token.json after each successful ADLS write.

On restart, it resumes from exactly the last processed event.

Store the token in a durable place (e.g., another ADLS file, a small Mongo collection, or Azure Table).

#### D) Throughput & parallelism
The sample writes each event serially. For higher throughput, buffer events and write in parallel (limit concurrency to avoid throttling).

Example libs: p-limit (already installed), or write to an in-memory queue and flush.

#### E) File count vs analytics performance
Many small files are simple but not ideal for downstream analytics.

If you prefer rolling JSONL:

- Create hourly (or 5-min) files: .../events-YYYYMMDD-HH.jsonl.

- Use ADLS append + flush to append events to the same file.

- Track file length (getProperties().contentLength) to find the next append offset.

- Rotate files on time boundary or size threshold (e.g., 128 MB).

- Periodically compact to Parquet using a separate Spark/ADF job.

A minimal rolling-writer sketch:

```js
// Sketch only – integrate into the main file writer:
async function appendJsonl(fsClient, dirClient, fileName, line) {
  const fileClient = dirClient.getFileClient(fileName);
  let currentLen = 0;
  if (!(await fileClient.exists())) {
    await fileClient.create();
  } else {
    const props = await fileClient.getProperties();
    currentLen = props.contentLength || 0;
  }
  const body = Buffer.from(line + '\n', 'utf8');
  await fileClient.append(body, currentLen, body.length);
  await fileClient.flush(currentLen + body.length);
}
```
#### F) Security & auth
For production, prefer Managed Identity or Service Principal (AAD) with RBAC on the container.

If you switch to AAD auth, use @azure/identity and pass a credential to DataLakeServiceClient.

#### G) Filtering
Add $match in pipeline to exclude noisy ops or to target specific collections when using wider scopes.

#### H) Pre/Post Images (optional)
If you enable pre/post images on the collection,  
you can capture fullDocumentBeforeChange for   
updates/deletes by keeping  
fullDocumentBeforeChange: 'whenAvailable'.

### 4) Operational checklist
- Run this service under a supervisor (systemd, PM2, Kubernetes, Azure Container Apps).

- Alert on errors and restarts.

- Periodically verify ADLS partition health and file counts.

- Downstream jobs (ADF, Databricks, Synapse, or Snowflake external stages) can read from the partition paths:

db/collection/year=YYYY/month=MM/day=DD/

### 5) (Optional) Transform to Parquet downstream
- Keep the raw JSONL/JSON as the bronze layer.

- Use a scheduled Spark/ADF pipeline to read year=YYYY/month=MM/day=DD/, normalize fields, write Parquet partitioned by the same keys into a silver/ container or folder.

- Point Snowflake external stage to the Parquet path for efficient analytics.


### Rolling JSONL

Rolling JSONL means instead of writing one file per event (which creates thousands or millions of tiny files),  
you keep a single JSONL file open for a fixed time window or until it reaches a size limit,   
and keep appending new events to it.

JSONL stands for JSON Lines — a text format where each line is a valid JSON object:

```json

{"_id": 1, "name": "Alice"}
{"_id": 2, "name": "Bob"}
{"_id": 3, "name": "Charlie"}
```
There are no commas and no array brackets — each line is its own JSON document.

#### Why "rolling"?
Rolling means you replace or rotate the active file periodically — for example:

- Every hour → events-2025-08-09-13.jsonl, events-2025-08-09-14.jsonl

- Every day → events-2025-08-09.jsonl

- Or when the file size hits a limit (e.g., 128 MB), you roll to events-2025-08-09-13-part2.jsonl.

When you "roll", you close the current file and start writing a new one.

#### Advantages over one-file-per-event
- Much fewer files → better for analytics (Snowflake, Databricks, Spark perform badly with lots of tiny files).

- Easy append → you can just append a line for each event.

- Easy to read → each line is self-contained JSON.

#### How it works with ADLS Gen2
When using rolling JSONL, you:

- Decide your partition path (e.g., db/collection/year=2025/month=08/day=09/).

- Create or open a file like events-2025-08-09-13.jsonl in that directory.

- Append each event’s JSON string + newline (\n).

- Keep track of append offset (ADLS requires it for append() calls).

- When rotation condition is met (time or size), close the file and start a new one.

# Extend the earlier MongoDB change stream → ADLS code to switch from per-event files to rolling hourly JSONL with offset tracking so you can feed the data into Snowflake efficiently.


 Rolling Hourly JSONL with Offset Tracking

This is an extension of the previous sample.  
Instead of writing **one file per event**, it keeps **one JSONL file per hour** (per `db/collection/year=YYYY/month=MM/day=DD/hour=HH/`)  
and **appends** new events to it.  
The code tracks and updates the **append offset** required by ADLS Gen2.

It’s optimized for downstream analytics (e.g., Snowflake external tables) by reducing the number of tiny files.

### 1) Prerequisites

- MongoDB replica set or sharded cluster (required for Change Streams).
- AADLS Gen2 account + container (filesystem).
- Node.js 18+ recommended.

Install dependencies:
```
npm init -y
npm i mongodb @azure/storage-file-datalake @azure/identity uuid p-limit
```
Environment variables (example):

Mongo
```ini
MONGO_URI="mongodb+srv://user:pass@cluster.example.mongodb.net/?retryWrites=true&w=majority"
MONGO_DB="database1" # optional if watching entire deployment
MONGO_COLL="collection1" # optional if watching database/deployment
MONGO_FULL_DOC="updateLookup" # 'default' | 'updateLookup' (recommended)

Azure ADLS Gen2
ADLS_ACCOUNT_URL="https://<account>.dfs.core.windows.net"
ADLS_FILESYSTEM="raw"

Auth option A: Shared Key
ADLS_SHARED_KEY=""

Auth option B: SAS (append ?<SAS> to URL or put SAS here)
ADLS_SAS=""

(Optional) Auth option C: Managed Identity / Service Principal (see code)
AZURE_CLIENT_ID=""
AZURE_TENANT_ID=""
AZURE_CLIENT_SECRET=""

Checkpointing (resume token persistence)
RESUME_TOKEN_PATH="./resume-token.json"

File rotation policy
ROLL_MAX_HOURS="1" # fixed to 1h windows; keep for compatibility/future
MAX_FILE_BYTES="134217728" # 128 MiB (size trigger if you want to roll earlier; 0 to disable)
```

### 2) Key behavior

- **Partition path**: `db/collection/year=YYYY/month=MM/day=DD/hour=HH/`
- **Rolling file name**: `events-YYYYMMDD-HH.jsonl`
- **Offset tracking**: On first open, the writer fetches `contentLength` as the starting offset; thereafter, it caches offsets and serializes appends per file to avoid race conditions.
- **Rotation**: On each event, the target file is derived from the event’s UTC hour. If the event’s hour differs from the last open hour for that partition, the writer “rolls” (switches) to the new hourly file. Optional size-based rotation is also included.
- **Resume tokens**: Persisted after a successful append so the stream resumes exactly after the last written event.


### 3) Code: `stream-mongo-to-adls-rolling-jsonl.js`

```js
'use strict';

/**
 * MongoDB Change Streams → ADLS Gen2 Rolling Hourly JSONL Writer
 *
 * Folders: db/collection/year=YYYY/month=MM/day=DD/hour=HH/
 * File:    events-YYYYMMDD-HH.jsonl
 *
 * - Tracks ADLS append offset (contentLength) to support append/flush.
 * - Serializes writes per file to avoid concurrent append races.
 * - Rolls files hourly by event UTC time; optional size-based rolling.
 */

const fs = require('fs');
const { randomUUID } = require('uuid');
const pLimit = require('p-limit');
const { MongoClient, Timestamp } = require('mongodb');
const {
  DataLakeServiceClient,
  StorageSharedKeyCredential
} = require('@azure/storage-file-datalake');
const {
  DefaultAzureCredential,
  ClientSecretCredential
} = require('@azure/identity');

function getEnv(name, required = false, fallback = undefined) {
  const v = process.env[name];
  if (required && (!v || v.trim() === '')) {
    throw new Error(`Missing env var: ${name}`);
  }
  return v?.trim() ?? fallback;
}

function pad2(n) { return String(n).padStart(2, '0'); }

function tsToDate(evt) {
  // Prefer clusterTime (BSON Timestamp, seconds = high bits)
  if (evt?.clusterTime instanceof Timestamp) {
    const seconds = evt.clusterTime.getHighBits();
    return new Date(seconds * 1000);
  }
  // Wall time if present
  if (evt?.wallTime) {
    return new Date(evt.wallTime);
  }
  // Fallback to ObjectId timestamp when available
  if (evt?.fullDocument?._id?.getTimestamp) {
    return evt.fullDocument._id.getTimestamp();
  }
  // Last resort
  return new Date();
}

function derivePartition(evt) {
  const d = tsToDate(evt);
  const year = d.getUTCFullYear();
  const month = pad2(d.getUTCMonth() + 1);
  const day = pad2(d.getUTCDate());
  const hour = pad2(d.getUTCHours());

  const db = evt?.ns?.db ?? 'unknown_db';
  const coll = evt?.ns?.coll ?? 'unknown_coll';

  return {
    db,
    coll,
    year,
    month,
    day,
    hour,
    dir: `${db}/${coll}/year=${year}/month=${month}/day=${day}/hour=${hour}`,
    fileBase: `events-${year}${month}${day}-${hour}.jsonl`
  };
}

function loadResumeToken(path) {
  try {
    if (fs.existsSync(path)) {
      const txt = fs.readFileSync(path, 'utf8');
      if (txt) return JSON.parse(txt);
    }
  } catch (_) {}
  return null;
}

function saveResumeToken(path, token) {
  try {
    fs.writeFileSync(path, JSON.stringify(token), 'utf8');
  } catch (err) {
    console.error('Failed to persist resume token:', err);
  }
}

async function buildServiceClient() {
  const accountUrl = getEnv('ADLS_ACCOUNT_URL', true);
  const fsName = getEnv('ADLS_FILESYSTEM', true);
  const key = getEnv('ADLS_SHARED_KEY');
  const sas = getEnv('ADLS_SAS');
  const clientId = getEnv('AZURE_CLIENT_ID');
  const tenantId = getEnv('AZURE_TENANT_ID');
  const clientSecret = getEnv('AZURE_CLIENT_SECRET');

  let serviceClient;

  if (sas) {
    // Use SAS appended to URL
    const url = accountUrl.includes('?') ? accountUrl : `${accountUrl}?${sas}`;
    serviceClient = new DataLakeServiceClient(url);
  } else if (key) {
    // Shared key
    const accountName = new URL(accountUrl).host.split('.')[0];
    const cred = new StorageSharedKeyCredential(accountName, key);
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  } else if (clientId && tenantId && clientSecret) {
    // Service Principal
    const cred = new ClientSecretCredential(tenantId, clientId, clientSecret);
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  } else {
    // Managed Identity / Default creds chain
    const cred = new DefaultAzureCredential();
    serviceClient = new DataLakeServiceClient(accountUrl, cred);
  }

  const fsClient = serviceClient.getFileSystemClient(fsName);
  await fsClient.createIfNotExists();
  return fsClient;
}

/**
 * RollingFileWriter
 * - Manages per-partition per-hour files.
 * - Serializes append() calls per file.
 * - Caches current offset; refreshes once on first open (or after restart).
 */
class RollingFileWriter {
  constructor(fsClient, opts = {}) {
    this.fsClient = fsClient;
    this.maxFileBytes = Number(getEnv('MAX_FILE_BYTES', false, '0')) || 0; // 0 = disable size-based roll
    this.files = new Map(); // key -> { dirClient, fileClient, path, offset, mutex, opened }
    this.dirCache = new Map(); // dirPath -> dirClient
    this.concurrency = opts.concurrency || 8;
    this.globalLimiter = pLimit(this.concurrency);
  }

  async ensureDir(dirPath) {
    if (this.dirCache.has(dirPath)) return this.dirCache.get(dirPath);
    const dirClient = this.fsClient.getDirectoryClient(dirPath);
    await dirClient.createIfNotExists();
    this.dirCache.set(dirPath, dirClient);
    return dirClient;
  }

  _fileKey(dirPath, fileName) {
    return `${dirPath}::${fileName}`;
  }

  async _openFile(dirClient, dirPath, fileName) {
    const key = this._fileKey(dirPath, fileName);
    if (this.files.has(key)) return this.files.get(key);

    const fileClient = dirClient.getFileClient(fileName);
    let offset = 0;

    // Determine starting offset (contentLength)
    const exists = await fileClient.exists();
    if (!exists) {
      await fileClient.create();
    } else {
      const props = await fileClient.getProperties();
      offset = Number(props.contentLength || 0);
    }

    const entry = {
      dirClient,
      fileClient,
      path: `${dirPath}/${fileName}`,
      offset,
      opened: true,
      // simple per-file mutex via a chained promise
      lock: Promise.resolve()
    };

    this.files.set(key, entry);
    return entry;
  }

  async appendLine(dirPath, fileName, lineBuffer) {
    const dirClient = await this.ensureDir(dirPath);
    const entry = await this._openFile(dirClient, dirPath, fileName);

    // Optionally roll by size (if enabled)
    if (this.maxFileBytes > 0 && (entry.offset + lineBuffer.length) > this.maxFileBytes) {
      // Close current file by switching name to a part suffix
      const rolledName = fileName.replace(/\.jsonl$/i, '') + `-part-${Date.now()}.jsonl`;
      // No actual "close" op required; just switch to a new file
      const newEntry = await this._openFile(dirClient, dirPath, rolledName);
      return this._appendWithLock(newEntry, lineBuffer);
    }

    return this._appendWithLock(entry, lineBuffer);
  }

  async _appendWithLock(entry, body) {
    // Serialize appends per file
    entry.lock = entry.lock.then(async () => {
      const start = entry.offset;
      await entry.fileClient.append(body, start, body.length);
      const newLen = start + body.length;
      await entry.fileClient.flush(newLen);
      entry.offset = newLen;
    }).catch((err) => {
      console.error(`Append error for ${entry.path}:`, err);
      // Allow subsequent operations; don't block chain forever
    });
    return entry.lock;
  }
}

function serializeEvent(evt) {
  // Keep metadata useful for downstream
  const payload = {
    _meta: {
      operationType: evt.operationType,
      clusterTime: evt.clusterTime ? evt.clusterTime.toString() : null,
      ns: evt.ns ?? null,
      txnNumber: evt.txnNumber ?? null,
      lsid: evt.lsid ?? null
    },
    documentKey: evt.documentKey ?? null,
    fullDocument: evt.fullDocument ?? null,
    updateDescription: evt.updateDescription ?? null,
    fullDocumentBeforeChange: evt.fullDocumentBeforeChange ?? null
  };
  return Buffer.from(JSON.stringify(payload) + '\n', 'utf8');
}

async function main() {
  const mongoUri = getEnv('MONGO_URI', true);
  const dbName = getEnv('MONGO_DB');
  const collName = getEnv('MONGO_COLL');
  const fullDoc = getEnv('MONGO_FULL_DOC', false, 'updateLookup');
  const resumePath = getEnv('RESUME_TOKEN_PATH', false, './resume-token.json');

  const fsClient = await buildServiceClient();
  const writer = new RollingFileWriter(fsClient, { concurrency: 8 });

  const client = new MongoClient(mongoUri, {
    // optional tuning:
    // maxPoolSize: 20,
    // retryWrites: true,
    // readPreference: 'primary',
  });

  await client.connect();

  let watchTarget;
  if (dbName && collName) {
    watchTarget = client.db(dbName).collection(collName);
    console.log(`Watching collection ${dbName}.${collName}`);
  } else if (dbName) {
    watchTarget = client.db(dbName);
    console.log(`Watching database ${dbName}`);
  } else {
    watchTarget = client;
    console.log(`Watching entire deployment (all databases)`);
  }

  const resumeToken = loadResumeToken(resumePath);

  const csOpts = {
    fullDocument: fullDoc,
    fullDocumentBeforeChange: 'whenAvailable',
    resumeAfter: resumeToken || undefined,
    batchSize: 100,
    maxAwaitTimeMS: 20000
  };

  const pipeline = [
    // Example: filter to core ops
    // { $match: { operationType: { $in: ['insert','update','replace','delete'] } } }
  ];

  const changeStream = watchTarget.watch(pipeline, csOpts);

  changeStream.on('change', async (evt) => {
    try {
      // derive partition + hourly file
      const part = derivePartition(evt);
      const fileName = part.fileBase; // events-YYYYMMDD-HH.jsonl
      const line = serializeEvent(evt);

      await writer.appendLine(part.dir, fileName, line);

      // Persist resume token after successful write
      if (evt._id) {
        saveResumeToken(resumePath, evt._id);
      }
    } catch (err) {
      console.error('Failed to append event to ADLS:', err);
    }
  });

  changeStream.on('error', async (err) => {
    console.error('Change stream error:', err);
    try { await changeStream.close(); } catch (_) {}
    try { await client.close(); } catch (_) {}
    process.exit(1);
  });

  changeStream.on('end', async () => {
    console.warn('Change stream ended.');
    try { await client.close(); } catch (_) {}
  });

  process.on('SIGINT', async () => {
    console.log('SIGINT received, closing...');
    try { await changeStream.close(); } catch (_) {}
    try { await client.close(); } catch (_) {}
    process.exit(0);
  });
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});
```
### 4) Run
``` 
node stream-mongo-to-adls-rolling-jsonl.js
```
Events will accumulate under:

```
raw/
 └─ database1/
    └─ collection1/
       └─ year=2025/
          └─ month=08/
             └─ day=10/
                └─ hour=19/
                   └─ events-20250810-19.jsonl
```                   
### 5) Notes for Snowflake
Point a Snowflake external stage at the raw/ container or a narrower prefix.

Use an external table or COPY INTO to ingest JSONL. Each line is a separate JSON doc.

Partition pruning with folder-style partitions like year=YYYY/month=MM/day=DD/hour=HH/ can be done with directory table / regexes or staged path filters during COPY INTO.

Example external table sketch (adjust to your naming and stage):

```sql
CREATE EXTERNAL TABLE bronze_events
WITH LOCATION=@my_stage/raw/
FILE_FORMAT=(TYPE=JSON STRIP_OUTER_ARRAY=TRUE)
AUTO_REFRESH=FALSE
PATTERN='.*events-.*\.jsonl'
;
```
(You can also extract year, month, day, hour from the path using Snowflake’s METADATA$FILENAME or directory tables depending on your setup.)

6) Options and hardening
Size-based roll: set MAX_FILE_BYTES (e.g., 268435456 = 256 MiB) to create additional -part-<epoch>.jsonl when a single hour gets too large.

Backpressure: if ingest rate spikes, you can bound concurrency globally (already set to 8) or add an internal queue.

Ordering: Change Streams deliver in-order per shard; cross-shard ordering is not guaranteed. This pattern is append-only and tolerant to interleaving.

Compression: If required, write .jsonl.gz via a gzip stream, but note ADLS append requires you to handle offsets of compressed bytes. Simpler: post-process with a batch job to gzip older files.

Schema drift: Keep raw JSONL in bronze; normalize to Parquet in silver for analytics (Snowflake can read Parquet efficiently via external tables).

# Periodically load rolling JSONL from ADLS Gen2 into Snowflake (COPY INTO vs Snowpipe)

##   Recommendation
- If you need **near-real-time** (seconds–minutes) and are OK configuring Azure Event Grid → Snowflake: **Snowpipe (auto-ingest)**.
- If **hourly or batch** cadence is fine, with simpler ops and strong dedup via load history: **COPY INTO on a schedule** (Snowflake TASK, Airflow, ADF, cron).  
For your “periodically read jsonl files” requirement, I recommend **COPY INTO**.

---

## 1) One-time Snowflake setup (ADLS Gen2 + Stage + File Format)

Replace placeholders `<...>` with your values.

```sql
-- 1A) Storage integration (ADLS Gen2)
-- Ask your Azure admin to grant the generated application (snowflake storage integration)
-- the required Reader permissions on the ADLS container.

CREATE OR REPLACE STORAGE INTEGRATION my_adls_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = AZURE
  ENABLED = TRUE
  AZURE_TENANT_ID = '<your-azure-tenant-id>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://<account>.dfs.core.windows.net/raw');

-- SHOW INTEGRATIONS;  -- Use this to retrieve AZURE_CONSENT_URL and EXTERNAL_OAUTH_APP_ID
-- Complete the Azure side consent, then proceed.

-- 1B) File format for JSONL
CREATE OR REPLACE FILE FORMAT my_jsonl
  TYPE = JSON
  STRIP_OUTER_ARRAY = FALSE
  -- (Optional) IGNORE_UTF8_ERRORS = TRUE
;

-- 1C) External stage pointing to ADLS Gen2 "raw" filesystem (container)
CREATE OR REPLACE STAGE raw_mongo
  URL = 'azure://<account>.dfs.core.windows.net/raw'
  STORAGE_INTEGRATION = my_adls_int
  FILE_FORMAT = my_jsonl
  DIRECTORY = (ENABLE = TRUE);  -- enables directory table if you want to use it
```
#### Target table (bronze)
We’ll land each JSON document as a VARIANT plus useful metadata parsed from the path:

```sql

CREATE OR REPLACE TABLE bronze_events (
  v        VARIANT,
  year     VARCHAR,
  month    VARCHAR,
  day      VARCHAR,
  hour     VARCHAR,
  filename STRING
);
```
## 2) COPY INTO pattern for JSONL (hourly partitions, dedup by load history)
Your ADLS path layout (from your writer):
db/collection/year=YYYY/month=MM/day=DD/hour=HH/events-YYYYMMDD-HH.jsonl

We’ll let Snowflake parse each line into $1 as VARIANT, and derive partitions from METADATA$FILENAME.

```sql

-- Example COPY INTO for a specific db/collection prefix:
-- Replace <db> and <collection> with actual names. Use broader patterns if desired.

COPY INTO bronze_events (v, year, month, day, hour, filename)
FROM (
  SELECT
    $1,  -- each line (JSON object) in JSONL
    REGEXP_SUBSTR(METADATA$FILENAME, 'year=([0-9]{4})', 1, 1, 'e', 1) AS year,
    REGEXP_SUBSTR(METADATA$FILENAME, 'month=([0-9]{2})', 1, 1, 'e', 1) AS month,
    REGEXP_SUBSTR(METADATA$FILENAME, 'day=([0-9]{2})', 1, 1, 'e', 1) AS day,
    REGEXP_SUBSTR(METADATA$FILENAME, 'hour=([0-9]{2})', 1, 1, 'e', 1) AS hour,
    TO_VARCHAR(METADATA$FILENAME) AS filename
  FROM @raw_mongo/<db>/<collection>/
  PATTERN = '.*year=[0-9]{4}/month=[0-9]{2}/day=[0-9]{2}/hour=[0-9]{2}/events-.*\.jsonl'
)
FILE_FORMAT = (FORMAT_NAME = my_jsonl)
ON_ERROR = 'CONTINUE';
```
Notes:

Dedup: Snowflake’s COPY INTO tracks file load history by file name for 64 days, so re-running the same COPY won’t reload the same files (unless FORCE=TRUE or you changed file names).

You can narrow the PATTERN to recent dates/hours if you want to reduce LIST time.

### 3) Simple Python loader (periodic) using snowflake-connector
This script:

Connects to Snowflake

Generates a list of recent hour prefixes (UTC) for the last N hours

Issues COPY INTO for each prefix

Relies on load history to avoid duplicate loads

Install deps:

```
pip install snowflake-connector-python python-dateutil
load_jsonl_to_snowflake.py:
```

```python
import os
import sys
import datetime as dt
from dateutil.tz import tzutc
import snowflake.connector

# Env vars expected:
# SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD (or SNOWFLAKE_PRIVATE_KEY), SNOWFLAKE_ROLE,
# SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
# Also set DB/COLLECTION lists or run with CLI args.

ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT")
USER      = os.getenv("SNOWFLAKE_USER")
PASSWORD  = os.getenv("SNOWFLAKE_PASSWORD")
ROLE      = os.getenv("SNOWFLAKE_ROLE")
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
DATABASE  = os.getenv("SNOWFLAKE_DATABASE")
SCHEMA    = os.getenv("SNOWFLAKE_SCHEMA")

STAGE = "raw_mongo"
TABLE = "bronze_events"

# Which db/collections on ADLS to load:
DBS = os.getenv("MONGO_DBS", "database1").split(",")
COLLS = os.getenv("MONGO_COLLS", "collection1").split(",")

# How many recent hours to load (inclusive of current hour)
RECENT_HOURS = int(os.getenv("RECENT_HOURS", "6"))  # safe overlap
USE_UTC_NOW = dt.datetime.now(tzutc())

COPY_TEMPLATE = """
COPY INTO {table} (v, year, month, day, hour, filename)
FROM (
  SELECT
    $1,
    REGEXP_SUBSTR(METADATA$FILENAME, 'year=([0-9]{{4}})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'month=([0-9]{{2}})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'day=([0-9]{{2}})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'hour=([0-9]{{2}})', 1, 1, 'e', 1),
    TO_VARCHAR(METADATA$FILENAME)
  FROM @{stage}/{db}/{coll}/year={yyyy}/month={mm}/day={dd}/hour={hh}/
  PATTERN = '.*events-.*\\.jsonl'
)
FILE_FORMAT = (FORMAT_NAME = my_jsonl)
ON_ERROR = 'CONTINUE';
"""

def run():
  if not all([ACCOUNT, USER, (PASSWORD or os.getenv("SNOWFLAKE_PRIVATE_KEY")), ROLE, WAREHOUSE, DATABASE, SCHEMA]):
    print("Missing Snowflake connection env vars.", file=sys.stderr)
    sys.exit(2)

  conn = snowflake.connector.connect(
    account=ACCOUNT,
    user=USER,
    password=PASSWORD,
    role=ROLE,
    warehouse=WAREHOUSE,
    database=DATABASE,
    schema=SCHEMA,
  )
  try:
    cur = conn.cursor()
    # Optional: set larger statement timeout if needed
    # cur.execute("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS=1800")

    # For each db/coll and each recent hour prefix
    for db in DBS:
      db = db.strip()
      if not db:
        continue
      for coll in COLLS:
        coll = coll.strip()
        if not coll:
          continue

        for i in range(RECENT_HOURS):
          t = USE_UTC_NOW - dt.timedelta(hours=i)
          yyyy = f"{t.year:04d}"
          mm   = f"{t.month:02d}"
          dd   = f"{t.day:02d}"
          hh   = f"{t.hour:02d}"

          sql = COPY_TEMPLATE.format(
            table=TABLE,
            stage=STAGE,
            db=db,
            coll=coll,
            yyyy=yyyy,
            mm=mm,
            dd=dd,
            hh=hh
          )
          print(f"Loading: {db}/{coll}/year={yyyy}/month={mm}/day={dd}/hour={hh}/ ...")
          cur.execute(sql)

    # Commit is implicit; COPY INTO is DML-like and persists on success.
  finally:
    conn.close()

if __name__ == "__main__":
  run()
```
Run it hourly via cron/Airflow/ADF.   
It’s idempotent because COPY INTO won’t re-ingest files seen before (within the load history retention window).

## 4) Snowflake TASK (built-in scheduler) alternative
Have Snowflake run COPY INTO every N minutes (no external orchestrator needed):

```sql

-- Warehouse for the task
CREATE OR REPLACE WAREHOUSE WH_LOAD
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
;

-- Task that loads new JSONL hourly for a given db/coll prefix
CREATE OR REPLACE TASK task_load_database1_collection1_hourly
  WAREHOUSE = WH_LOAD
  SCHEDULE = 'USING CRON 5 * * * * UTC'   -- at minute 5 of every hour
AS
COPY INTO bronze_events (v, year, month, day, hour, filename)
FROM (
  SELECT
    $1,
    REGEXP_SUBSTR(METADATA$FILENAME, 'year=([0-9]{4})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'month=([0-9]{2})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'day=([0-9]{2})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'hour=([0-9]{2})', 1, 1, 'e', 1),
    TO_VARCHAR(METADATA$FILENAME)
  FROM @raw_mongo/database1/collection1/
  PATTERN = '.*year=[0-9]{4}/month=[0-9]{2}/day=[0-9]{2}/hour=[0-9]{2}/events-.*\.jsonl'
)
FILE_FORMAT = (FORMAT_NAME = my_jsonl)
ON_ERROR = 'CONTINUE'
;

-- Enable the task
ALTER TASK task_load_database1_collection1_hourly RESUME;
```
You can create one task per db/collection, or one broader task that targets multiple prefixes with separate COPY statements.

## 5) Snowpipe option (if you want lower latency)
Create pipe (no auto-ingest):
```sql

CREATE OR REPLACE PIPE bronze_events_pipe AS
COPY INTO bronze_events (v, year, month, day, hour, filename)
FROM (
  SELECT
    $1,
    REGEXP_SUBSTR(METADATA$FILENAME, 'year=([0-9]{4})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'month=([0-9]{2})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'day=([0-9]{2})', 1, 1, 'e', 1),
    REGEXP_SUBSTR(METADATA$FILENAME, 'hour=([0-9]{2})', 1, 1, 'e', 1),
    TO_VARCHAR(METADATA$FILENAME)
  FROM @raw_mongo
  PATTERN = '.*events-.*\.jsonl'
)
FILE_FORMAT = (FORMAT_NAME = my_jsonl);

```
Periodic trigger (no Event Grid): you can nudge the pipe to scan by prefix:

```sql

ALTER PIPE bronze_events_pipe REFRESH PREFIX = 'database1/collection1/year=2025/month=08/day=10/';
-- Or a broader prefix if needed
```
If you want true auto-ingest, configure Azure Event Grid → Snowflake on the stage (additional Azure setup required). Then Snowpipe listens for blob create events and loads within minutes automatically.

6) Operational notes
Idempotency: COPY and Snowpipe both use load history to avoid reloading the same file name.

Latency: Snowpipe (auto-ingest) is near-real-time; COPY via TASK/cron is batch (e.g., hourly).

Cost: COPY burns warehouse credits during runs; Snowpipe charges per file/byte ingested but no warehouse needed for ingestion.

Schema: Keep bronze_events.v raw, then transform to typed columns in silver (e.g., CREATE TABLE ... AS SELECT v:field::type ...).

Partition pruning: During transforms, use filename/path to filter specific dates/hours for efficient backfills.


