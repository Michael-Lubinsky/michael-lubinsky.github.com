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

