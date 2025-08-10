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
