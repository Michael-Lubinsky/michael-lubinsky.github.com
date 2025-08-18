
## **MongoDB Atlas**
- **Atlas** is MongoDB’s fully managed **Database-as-a-Service (DBaaS)**.  
- It runs MongoDB clusters for you on **AWS, Azure, or GCP**, so you don’t have to manage servers, replication, backups, or scaling yourself.  
- Key features:
  - Automated deployment, patching, upgrades  
  - Built-in monitoring and alerting  
  - Horizontal scaling (sharding)  
  - Global clusters with multi-region support  
  - Integrated security (encryption, RBAC, auditing)  
  - One-click integration with services like **Charts, Atlas Search, Atlas Data Lake, Atlas Functions**  

Think of it as: *“MongoDB in the cloud, production-ready out of the box.”*

---

## **Atlas Stream Processing (ASP)**
- **ASP** is a **real-time data processing framework** built into MongoDB Atlas.  
- It lets you **consume streams of events** (like Kafka topics, Event Hubs, or MongoDB Change Streams) and process them using a **declarative query language (MQL)**, similar to writing Mongo queries.  
- Key features:
  - **Ingest** from multiple sources: Kafka, Event Hubs, Confluent Cloud, and even MongoDB Change Streams  
  - **Process** with Mongo’s aggregation pipeline (filter, join, window, transform) in real time  
  - **Output** to Atlas databases, other streams, or external sinks  
  - Built-in support for **windowing functions** (time-based aggregations)  
  - Can run **stateful stream processing** jobs without needing Spark/Flink infrastructure  

In other words, ASP lets you **treat event streams like live collections** and query them in real time with familiar MongoDB syntax.  

---

### **Example Use Case**
- You have an **IoT fleet** sending device telemetry.  
- Events arrive in **Azure Event Hub**.  
- **Atlas Stream Processing** subscribes to Event Hub, aggregates device health metrics every 5 minutes, and writes the results into an Atlas collection.  
- Downstream apps or dashboards query that collection for live analytics.  

---

### **Why It Matters**
- Normally, you’d need **Kafka Streams, Spark Streaming, or Flink** to do this.  
- With ASP, you do it *inside Atlas* with the same MongoDB query language, no heavy infra.  

---

👉 In short:  
- **Atlas** = MongoDB’s managed cloud database service.  
- **Atlas Stream Processing** = managed real-time stream analytics built into Atlas, powered by MongoDB’s aggregation framework.  


# Atlas Stream Processing → Azure Event Hubs (Kafka) → ADLS via Capture

Below is a concrete, copy-pasteable path to implement “MongoDB Atlas Stream Processing (ASP) → Azure Event Hubs → Azure Data Lake Storage (ADLS Gen2) using Event Hubs Capture.” It also covers Private Link notes for Azure.

At a high level:

1. ASP reads change events from your MongoDB collection(s),
2. ASP emits them to **Azure Event Hubs’ Kafka endpoint**,
3. Event Hubs **Capture** writes batches to **ADLS** (Avro by default; Parquet via the no-code portal option). ([MongoDB][1], [Microsoft Learn][2])

---

## Prereqs

* **MongoDB Atlas** project + a cluster with Change Streams enabled (Serverless isn’t a valid `$source`). ([MongoDB][3])
* **Atlas Stream Processing instance** in Azure (Provider=`AZURE`, Region like `eastus`). ([MongoDB][4])
* **Azure**: Resource Group, Event Hubs Namespace (Standard/SKU or higher; **Basic tier doesn’t support Kafka**), an Event Hub (topic), and an **ADLS Gen2** Storage account + container. ([Microsoft Learn][2])
* Optional: **Private Link** from ASP to Event Hubs (supported), if you need private networking. ([MongoDB][1])

---

## Step 1 — Create Azure Event Hubs + enable Capture to ADLS

> You can use the Azure Portal (simplest) or CLI. Capture writes in **time/size windows** to Storage; default **Avro**, with Parquet available via the no-code (portal) experience. Managed identity is supported for Capture auth. ([Microsoft Learn][5])

**Portal path (quick):**
Create: *Event Hubs Namespace* → *Event Hub*. Then open the Event Hub → **Capture** → turn **On**, choose your **Storage account** (ADLS Gen2) and **Container**, set **Capture window** (e.g., 5 min or 100MB), and optionally “skip empty archives.” ([Microsoft Learn][5])

**CLI skeleton (reference):**

```bash
# create EH namespace + hub
az eventhubs namespace create -g <rg> -n <ns> -l <region> --sku Standard
az eventhubs eventhub create -g <rg> --namespace-name <ns> -n <hub> --partition-count 4

# enable Capture to ADLS Gen2
az eventhubs eventhub update \
  -g <rg> --namespace-name <ns> -n <hub> \
  --enable-capture true \
  --destination-name EventHubArchive.AzureBlockBlob \
  --storage-account <storageAccountNameOrId> \
  --blob-container <containerName> \
  --skip-empty-archives true \
  --capture-interval 300 \
  --capture-size-limit 104857600
```

(See CLI params for Capture destination & retention knobs.) ([Microsoft Learn][6])

**Notes:**

* Capture writes a folder hierarchy per hub/partition with time-bucketed files. The **default format is Avro**; you can also configure **Parquet via the portal’s no-code option**. ([Microsoft Learn][7])
* If you prefer, enable **Managed Identity** for Capture (recommended) so Event Hubs writes to ADLS without keys. ([Microsoft Learn][8])

---

## Step 2 — Know the Kafka endpoint settings for Event Hubs

Event Hubs exposes a **Kafka-compatible endpoint** at:
`<namespace>.servicebus.windows.net:9093` with **TLS** and **SASL/SSL**. For simple clients, use **SASL/PLAIN** with the username **`$ConnectionString`** and the Event Hubs **connection string** as the password (namespace-level or hub-level policy). Example Kafka client properties:

```
bootstrap.servers=<NAMESPACE>.servicebus.windows.net:9093
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required \
  username="$ConnectionString" \
  password="Endpoint=sb://<NAMESPACE>.servicebus.windows.net/;SharedAccessKeyName=<KeyName>;SharedAccessKey=<KeyValue>";
```

(Passwordless/OAUTHBEARER is supported by Event Hubs, but Atlas Kafka connections support PLAIN/SCRAM; use **PLAIN** here.) ([Microsoft Learn][2], [MongoDB][1])

---

## Step 3 — Create an Atlas Stream Processing (ASP) instance on Azure

```bash
# Atlas CLI (log in first: `atlas auth login`)
atlas streams instances create my-asp --provider AZURE --region eastus
```

Region naming for Azure uses forms like `eastus`. ([MongoDB][4])

---

## Step 4 — Register connections in ASP’s **Connection Registry**

You’ll add **two** connections:

1. **Atlas Database** connection (source): picks which Atlas cluster/db/collection to watch.
2. **Kafka connection** to **Event Hubs** (sink): points ASP at Event Hubs’ Kafka endpoint.

### 4a) Add the Atlas Database connection (source)

Via the Atlas UI: Stream Processing → your instance → **Configure** → **Connection Registry** → **+ Add Connection** → **Atlas Database**, select your cluster, give it a name, e.g., `atlasSrc`. (This is the connection you reference from `$source`.) ([MongoDB][9])

### 4b) Add the Kafka connection to Event Hubs (sink)

Create a JSON config file `evh-kafka.json` like this:

```json
{
  "name": "evhKafka",
  "type": "Kafka",
  "bootstrapServers": "<namespace>.servicebus.windows.net:9093",
  "security": { "protocol": "SASL_SSL" },
  "authentication": {
    "mechanism": "PLAIN",
    "username": "$ConnectionString",
    "password": "Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<KeyName>;SharedAccessKey=<KeyValue>"
  }
}
```

Then register it:

```bash
atlas streams connections create -i my-asp -f evh-kafka.json
```

> If you require **Private Link** to Event Hubs, first request/create the Private Link in Atlas Stream Processing, then attach it when creating the Kafka connection, e.g.:

```json
{
  "name": "evhKafkaPL",
  "type": "Kafka",
  "bootstrapServers": "<namespace>.servicebus.windows.net:9093",
  "security": { "protocol": "SASL_SSL" },
  "authentication": {
    "mechanism": "PLAIN",
    "username": "$ConnectionString",
    "password": "Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<KeyName>;SharedAccessKey=<KeyValue>"
  },
  "networking": {
    "access": { "type": "PRIVATE_LINK", "connectionId": "<atl_pl_conn_id>" }
  }
}
```

(Atlas docs show Event Hubs Private Link supported and provide a concrete example using `username: "$ConnectionString"`.) ([MongoDB][1])

---

## Step 5 — Define & run the ASP pipeline: `$source` (MongoDB change stream) → transform → `$emit` (Kafka topic/Event Hub)

Connect `mongosh` to your ASP instance (Stream Processing → **Connect** → copy the mongosh URI), then define a pipeline.

**Pick a topic name = your Event Hub name.** In Kafka compatibility, the “topic” is the Event Hub. Ensure the hub exists. ([Microsoft Learn][2])

```javascript
// 1) Change Stream source from your Atlas collection:
const sourceStage = {
  $source: {
    connectionName: "atlasSrc",     // the Atlas DB connection you added
    db: "app",                       // your DB
    coll: ["orders"],                // one or more collections
    // optional: filter at source using a Change Stream pipeline
    config: {
      fullDocument: "whenAvailable",
      pipeline: [
        { $match: { operationType: { $in: ["insert","update","replace"] } } }
      ]
    }
  }
};

// 2) (Optional) Any transforms, projections, schema validation, etc.
// e.g., enrich, remap fields, ensure stable keys for partitioning:
const transformStage = {
  $project: {
    _id: 0,
    orderId: "$fullDocument.orderId",
    amount: "$fullDocument.amount",
    status: "$fullDocument.status",
    ts: "$clusterTime"
  }
};

// 3) Emit to Event Hubs (Kafka) with keying for partition/ordering:
const sinkStage = {
  $emit: {
    connectionName: "evhKafka",
    topic: "orders-events",           // must match the Event Hub name
    config: {
      key: "$orderId",
      keyFormat: "string",
      outputFormat: "relaxedJson",
      headers: { source: "atlas", stream: "orders" }
    }
  }
};

const pipeline = [sourceStage, transformStage, sinkStage];

// Create a named, persistent processor and start it:
sp.createStreamProcessor("orders_to_evh", pipeline);
sp.orders_to_evh.start();
```

* `$source` supports **MongoDB collection/database/cluster change streams** and has options like `fullDocument`, `pipeline` and resume tokens.
* `$emit` is the **sink** to Kafka; you set `topic`, optional `key`, `keyFormat`, `headers`, and `outputFormat`.
  Refer to the stage docs for all fields. ([MongoDB][3])

---

## Step 6 — Verify files in ADLS

Once events flow, **Event Hubs Capture** will land files in your chosen container on the cadence/size you set. Expect Avro unless you chose Parquet in the portal’s no-code capture option. The folder path includes namespace/hub/partition and time buckets. ([Microsoft Learn][7])

---

## Ops & tips

* **Kafka auth/mechanism:** Event Hubs supports Kafka with **SASL\_SSL**; for ASP, use **SASL PLAIN** with `$ConnectionString` + EH connection string (Atlas Kafka mechanisms are PLAIN/SCRAM). ([Microsoft Learn][2], [MongoDB][1])
* **Throughput & partitions:** Size your Event Hub partitions to match expected parallelism; use a stable `key` in `$emit` if you need per-key ordering. (Kafka partition key semantics apply.) ([Microsoft Learn][2])
* **Private networking:** ASP supports **Azure Event Hubs Private Link**; the connection JSON example in docs shows exactly how to attach `networking.access.type: "PRIVATE_LINK"`. ([MongoDB][1])
* **Format & schema:** Capture defaults to **Avro**. If you want **Parquet**, use the portal’s no-code editor for Event Hubs Capture. For upstream validation/conformance, consider `$validate` in ASP before `$emit`. ([Microsoft Learn][7])
* **Monitoring:** Use ASP’s `sp.<name>.stats()` and Atlas UI monitoring, plus Event Hubs metrics (incoming/outgoing, capture success) and Storage metrics. ([MongoDB][10])

---

## Why this design fits “Azure & Private Link” and “Event Hubs → ADLS pipelines”

* **Kafka endpoint in Event Hubs** lets ASP act exactly like a Kafka producer; **no code changes** in the sink stage beyond pointing to the EH bootstrap servers + SASL settings. ([Microsoft Learn][2])
* **ASP supports Kafka as a sink** and **explicitly supports Azure Event Hubs Private Link** in its Kafka connection flow. ([MongoDB][1])
* **Capture** is the native, managed way to **land to ADLS** in time/size windows for lakehouse ingestion. ([Microsoft Learn][5])

---

### References (key docs)

* **ASP Kafka connection + Azure Event Hubs Private Link** (example JSON, `$ConnectionString` username) and supported SASL mechanisms. ([MongoDB][1])
* **Event Hubs Kafka quickstart** (SASL/SSL 9093, PLAIN with `$ConnectionString`). ([Microsoft Learn][2])
* **Event Hubs Capture overview** (Avro default; Parquet via portal). ([Microsoft Learn][7])
* **Create ASP instance (provider AZURE, region format)**. ([MongoDB][4])
* **ASP stages**: `$source` (MongoDB change streams) and `$emit` (Kafka sink). ([MongoDB][3])

---

If you want, I can tailor the pipeline to your exact DB/collection names, add windowing/aggregation, or provide Terraform for the Azure resources and the Atlas connections.


### Here are two solid ways to land MongoDB changes into ADLS with the exact folder pattern:

collection/YYYY-MM-DD-HH

 
(A) a direct writer (simplest, full control of the path),  
  
(B) an Event Hubs route (use Capture for durability, then a tiny post-process to reshape folders).

---

#### A) Direct: Change Streams → ADLS (exact path)

Pros: exact folder names, lowest moving parts.
Cons: you own buffering/retries/resume.

```javascript
// package.json deps:
//   "mongodb": "^6",
//   "@azure/storage-blob": "^12"
// env vars:
//   MONGO_URI, AZURE_STORAGE_CONNECTION_STRING, ADLS_CONTAINER

import { MongoClient } from "mongodb";
import { BlobServiceClient, AppendBlobClient } from "@azure/storage-blob";

const mongoUri   = process.env.MONGO_URI;
const connStr    = process.env.AZURE_STORAGE_CONNECTION_STRING;
const container  = process.env.ADLS_CONTAINER || "events";

// simple in-memory buffers keyed by "collection|yyyy-mm-dd-hh"
const BUFFERS = new Map();
// flush every N records or every T ms
const FLUSH_COUNT = 500;
const FLUSH_MS = 10_000;

function hourKey(dateUtc) {
  const d = new Date(dateUtc);
  const y  = d.getUTCFullYear();
  const m  = String(d.getUTCMonth()+1).padStart(2,"0");
  const dd = String(d.getUTCDate()).padStart(2,"0");
  const hh = String(d.getUTCHours()).padStart(2,"0");
  return `${y}-${m}-${dd}-${hh}`;
}

function blobPathFor(coll, hour) {
  // folder: collection/YYYY-MM-DD-HH/
  // file: events-YYYYMMDD-HH.jsonl (one per hour per collection)
  const ymdh = hour.replaceAll("-", "");
  const ymd  = ymdh.slice(0,8);
  const HH   = hour.slice(-2);
  return `${coll}/${hour}/events-${ymd}-${HH}.jsonl`;
}

async function ensureAppendBlob(appendClient) {
  try {
    await appendClient.createIfNotExists({ blobHTTPHeaders: { blobContentType: "application/json" }});
  } catch (_) {}
}

async function flushBuffer(bsc, key) {
  const buf = BUFFERS.get(key);
  if (!buf || buf.lines.length === 0) return;

  const { coll, hour } = buf;
  const path = blobPathFor(coll, hour);
  const containerClient = bsc.getContainerClient(container);
  await containerClient.createIfNotExists();
  const appendClient = new AppendBlobClient(containerClient.url + "/" + path, bsc.credential, bsc.pipeline);

  await ensureAppendBlob(appendClient);
  const payload = buf.lines.join("\n") + "\n";
  await appendClient.appendBlock(payload, Buffer.byteLength(payload));
  buf.lines = [];
  buf.lastFlush = Date.now();
}

async function periodicFlusher(bsc) {
  setInterval(async () => {
    const tasks = [];
    for (const [key, buf] of BUFFERS.entries()) {
      if (buf.lines.length >= FLUSH_COUNT || Date.now() - buf.lastFlush >= FLUSH_MS) {
        tasks.push(flushBuffer(bsc, key));
      }
    }
    await Promise.allSettled(tasks);
  }, Math.max(FLUSH_MS, 3000));
}

function addLine(coll, hour, line) {
  const k = `${coll}|${hour}`;
  if (!BUFFERS.has(k)) BUFFERS.set(k, { coll, hour, lines: [], lastFlush: 0 });
  BUFFERS.get(k).lines.push(line);
}

function getUtcSecondsFromClusterTime(bsonTs) {
  // clusterTime is a BSON Timestamp with high bits = seconds
  // if using driver types, prefer toString/seconds getter; fallback:
  return typeof bsonTs?.getHighBits === "function" ? bsonTs.getHighBits() : Math.floor(Date.now()/1000);
}

async function main() {
  const bsc = BlobServiceClient.fromConnectionString(connStr);
  periodicFlusher(bsc);

  const client = new MongoClient(mongoUri);
  await client.connect();

  // watch cluster-level or db-level; here: cluster-level
  const changeStream = client.watch([], { fullDocument: "updateLookup" });

  // TODO: load last resume token from durable storage (e.g., a small state collection)
  // and start from it to guarantee exactly-resume semantics.

  for await (const ev of changeStream) {
    const coll = ev.ns?.coll || "unknown";
    const tsSec = getUtcSecondsFromClusterTime(ev.clusterTime);
    const hour  = hourKey(new Date(tsSec * 1000).toISOString());
    // Keep it lean: serialize the essentials; you can store full event if needed
    const out = {
      op: ev.operationType,
      ns: ev.ns,
      doc: ev.fullDocument ?? null,
      updateDesc: ev.updateDescription ?? null,
      clusterTime: ev.clusterTime
    };
    addLine(coll, hour, JSON.stringify(out));
    // persist resume token ev._id periodically (not shown)
  }
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
```

Notes:

* Uses Append Blobs (cheap, simple “append line” semantics per hour).
* Writes JSONL; easy to `COPY INTO` Snowflake later, or to convert to Parquet in a separate job.
* Persist the **resume token** (`ev._id`) to survive restarts exactly from last processed event.

---

##### B) Event Hubs in the middle: ASP/Producer → Event Hubs → Capture → (reshape to target folders)

Event Hubs Capture chooses its own directory layout (namespace/hub/partition/time). If you must have collection/YYYY-MM-DD-HH, do:

1. **Ingest**: Mongo → (ASP or your producer) → **Event Hubs** (Kafka endpoint).
2. **Land**: **Capture to ADLS** (Avro/Parquet).
3. **Reshape**: tiny post-process that **moves/copies** files into `collection/YYYY-MM-DD-HH/…` based on metadata you include in each message.

Two light-weight ways to reshape:

• **Azure Function (Timer trigger):**

* List new captured blobs.
* Read Avro headers or parse file body to find `collection` and event timestamps (you can stamp `collection` and hour into the message headers or payload when emitting).
* Copy to `collection/YYYY-MM-DD-HH/…` and delete the original from the landing zone.

• **ADF Mapping Data Flow / Pipeline:**

* Source = landing container
* Derived columns to compute folder path from event payload/headers
* Sink = curated container with dynamic folder path (`@{item().collection}/@{formatDateTime(item().ts,'yyyy-MM-dd-HH')}`)

Tip for Event Hubs pathing:

* When you emit events, include:

  * `collection` in the message (payload or header)
  * a normalized UTC timestamp (e.g., “eventHour” = 2025-08-17-14)
* Your post-process only needs to read minimal metadata to compute the exact folder.

---

# Which should you use?

* **Need the exact folder structure now, with minimal services?** Go with **A (Direct)**.
* **Need durability, fan-out, and Azure-native landing with autoscaling?** Use **B (Event Hubs + Capture)** and add the small **reshape** step.

If you want, tell me your DB/collection names and I’ll:

* wire the direct writer to only watch specific collections, or
* produce the Azure Function (Node.js or Python) that reshapes Event Hubs Capture output into `collection/YYYY-MM-DD-HH/`.




[1]: https://www.mongodb.com/docs/atlas/atlas-stream-processing/kafka-connection/ "Apache Kafka Connections - Atlas - MongoDB Docs"
[2]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-quickstart-kafka-enabled-event-hubs "Quickstart: Use Apache Kafka with Azure Event Hubs - Azure Event Hubs | Microsoft Learn"
[3]: https://www.mongodb.com/docs/atlas/atlas-stream-processing/sp-agg-source/ "$source Stage (Stream Processing) - Atlas - MongoDB Docs"
[4]: https://www.mongodb.com/docs/atlas/cli/current/command/atlas-streams-instances-create/?utm_source=chatgpt.com "atlas streams instances create - Atlas CLI"
[5]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-capture-enable-through-portal?utm_source=chatgpt.com "Event Hubs - Capture streaming events using Azure portal"
[6]: https://learn.microsoft.com/en-us/cli/azure/eventhubs/eventhub?view=azure-cli-latest&utm_source=chatgpt.com "az eventhubs eventhub"
[7]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-capture-overview "Capture Streaming Events - Azure Event Hubs | Microsoft Learn"
[8]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-capture-managed-identity?utm_source=chatgpt.com "Use managed Identities to capture events - Azure Event Hubs"
[9]: https://www.mongodb.com/docs/atlas/atlas-stream-processing/tutorial/?utm_source=chatgpt.com "Get Started with Atlas Stream Processing"
[10]: https://www.mongodb.com/docs/atlas/atlas-stream-processing/manage-stream-processor/?utm_source=chatgpt.com "Manage Stream Processors - Atlas - MongoDB Docs"


## GEMINI

Unfortunately, **MongoDB Atlas Stream Processing** doesn't support writing to **Azure Data Lake Storage (ADLS)** as a sink.  
It primarily focuses on real-time data processing and writing to other stream processing platforms or databases, such as other MongoDB collections, Kafka, and Amazon S3. 
For periodic data exports to ADLS, you'll need to use a different approach.  

-----

## Recommended Approach Using Azure Functions

A robust and common way to achieve your goal is to use an **Azure Function** with a **Node.js** runtime. This serverless solution allows you to schedule a function to run periodically and handle the data export logic.

### 1\. Set Up Your Environment

First, you'll need a **MongoDB Atlas cluster** and an **Azure Storage account** with a **Data Lake Storage Gen2** enabled. Create an Azure Function App in the Azure portal and select a Node.js runtime.

### 2\. Write the Node.js Code

The core of your solution will be a Node.js script that connects to your MongoDB Atlas cluster, queries the desired collection, and writes the data to ADLS.


The provided below code performs a **full collection dump** every hour, not a change stream dump. It connects to the MongoDB database and uses `collection.find({})` to retrieve **all documents** from each collection and then writes that entire dataset to Azure Data Lake Storage (ADLS).

This approach is suitable for periodic full backups or snapshots. If your goal is to capture **only the changes** that occurred in the last hour, you would need to use MongoDB's **Change Streams** feature. This would require a different code structure that listens for real-time changes, buffers them, and then dumps them to ADLS on the hour.

Here is a brief comparison of the two approaches:

* **Full Dump (as shown in my code):**
    * **Pros:** Simple to implement, guarantees a complete snapshot of the data at that specific moment.
    * **Cons:** Inefficient for large collections as it processes the entire dataset every time, potentially leading to high resource usage and storage costs.

* **Change Stream:**
    * **Pros:** Highly efficient as it only processes new, updated, or deleted documents, making it ideal for real-time or near-real-time synchronization.
    * **Cons:** More complex to implement, requires state management to track the last processed change, and a mechanism to handle disconnections and resume from where it left off.
Here's an example of what the code would look like:

```javascript
const { MongoClient } = require('mongodb');
const { BlobServiceClient } = require('@azure/storage-blob');
const { v1: uuidv1 } = require('uuid');

const mongoUri = 'YOUR_MONGODB_ATLAS_CONNECTION_STRING';
const storageAccountName = 'YOUR_AZURE_STORAGE_ACCOUNT_NAME';
const storageAccountKey = 'YOUR_AZURE_STORAGE_ACCOUNT_KEY';

const blobServiceClient = BlobServiceClient.fromConnectionString(
  `DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccountKey};EndpointSuffix=core.windows.net`
);

module.exports = async function (context, myTimer) {
  context.log('Function started.');

  const client = new MongoClient(mongoUri);

  try {
    await client.connect();
    const database = client.db('yourDatabaseName');
    const collections = await database.listCollections().toArray();

    for (const collectionInfo of collections) {
      const collectionName = collectionInfo.name;
      const collection = database.collection(collectionName);
      const documents = await collection.find({}).toArray();

      if (documents.length > 0) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const folderPath = `${collectionName}/${year}-${month}-${day}-${hour}`;
        const fileName = `${uuidv1()}.json`; // Use a unique filename
        const blobName = `${folderPath}/${fileName}`;
        const containerClient = blobServiceClient.getContainerClient('yourContainerName');
        const blockBlobClient = containerClient.getBlockBlobClient(blobName);

        const data = JSON.stringify(documents, null, 2);
        await blockBlobClient.upload(data, data.length);
        context.log(`Successfully uploaded data from collection "${collectionName}" to ADLS at: ${blobName}`);
      }
    }
  } catch (error) {
    context.log.error('An error occurred:', error);
  } finally {
    await client.close();
  }
};
```

### 3\. Configure the Function to Run Periodically

In your Azure Function App, you'll need to configure the trigger to run on a schedule.

1.  Navigate to the **Integrate** tab for your function.
2.  Select **Timer trigger** as the trigger type.
3.  Set the **CRON expression** to `0 0 * * * *`. This expression schedules the function to run at the start of every hour.

This setup ensures that the function runs automatically, connects to MongoDB, retrieves the data, and stores it in the specified folder structure in your ADLS container.




### GROK

```javascript
// app.js
// This script exports data from all MongoDB collections in a specified database to Azure Data Lake Storage Gen2 (ADLS Gen2)
// every hour. Data is exported as NDJSON files (one document per line) in the folder structure: collection/YYYY-MM-DD-HH/collection.ndjson
// It uses streaming to handle large collections without loading everything into memory.

// Prerequisites:
// - Install dependencies: npm install mongodb @azure/storage-file-datalake node-cron dotenv
// - Set up .env file with:
//   MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority
//   DB_NAME=your_database_name
//   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<key>;EndpointSuffix=core.windows.net
//   FILE_SYSTEM_NAME=your_adls_container_name
// - Run the script: node app.js

const { MongoClient } = require('mongodb');
const { DataLakeServiceClient } = require('@azure/storage-file-datalake');
const cron = require('node-cron');
const { Readable } = require('stream');
require('dotenv').config();

const mongoUri = process.env.MONGO_URI;
const dbName = process.env.DB_NAME;
const azureConnectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
const fileSystemName = process.env.FILE_SYSTEM_NAME;

async function exportCollections() {
  const mongoClient = new MongoClient(mongoUri);
  await mongoClient.connect();
  const db = mongoClient.db(dbName);
  const collections = await db.listCollections().toArray();

  const serviceClient = DataLakeServiceClient.fromConnectionString(azureConnectionString);
  const fileSystemClient = serviceClient.getFileSystemClient(fileSystemName);

  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const folderSuffix = `${year}-${month}-${day}-${hour}`;

  for (const collInfo of collections) {
    const collectionName = collInfo.name;
    // Skip system collections if needed; for now, export all
    if (collectionName.startsWith('system.')) continue;

    const collection = db.collection(collectionName);
    const directoryPath = `${collectionName}/${folderSuffix}`;
    const directoryClient = fileSystemClient.getDirectoryClient(directoryPath);
    await directoryClient.createIfNotExists();

    const fileClient = directoryClient.getFileClient(`${collectionName}.ndjson`);

    const cursor = collection.find({});
    const readableStream = new Readable({
      read() {}  // No-op, as we push data asynchronously
    });

    (async () => {
      try {
        for await (const doc of cursor) {
          readableStream.push(JSON.stringify(doc) + '\n');
        }
        readableStream.push(null);  // End the stream
      } catch (err) {
        readableStream.destroy(err);
      }
    })();

    // Upload the stream to ADLS Gen2
    await fileClient.upload(readableStream);
    console.log(`Exported ${collectionName} to ${directoryPath}/${collectionName}.ndjson`);
  }

  await mongoClient.close();
}

// Schedule the export every hour (at the start of each hour)
cron.schedule('0 * * * *', () => {
  console.log('Starting hourly export...');
  exportCollections().catch(err => console.error('Export failed:', err));
});

console.log('Scheduler started. Waiting for next hourly run...');
```
Is this script robust for production?
Does it handles errors, timeouts?
Does it has  retry logic?

The provided script is a good starting point but lacks several features critical for production robustness, including comprehensive error handling, timeout management, and retry logic. Below, I’ll evaluate its current state, identify gaps, and provide an enhanced version with improvements for production use.

### Evaluation of the Original Script

1. **Error Handling**:
   - **Current State**: The script has minimal error handling. It catches errors in the main `exportCollections` function and during the streaming process (`readableStream.destroy(err)`), but it doesn’t handle specific failure scenarios like MongoDB connection issues, Azure upload failures, or partial exports.
   - **Gaps**:
     - No handling for MongoDB connection timeouts or authentication failures.
     - No specific handling for Azure connection issues, rate limits, or partial upload failures.
     - No cleanup for failed uploads (e.g., removing incomplete files in ADLS).
     - No logging of errors to a persistent store for monitoring.
     - If one collection fails, others may still proceed, but there’s no mechanism to track partial failures.

2. **Timeouts**:
   - **Current State**: The script doesn’t configure timeouts for MongoDB or Azure operations. It relies on default timeouts, which may be too short or too long for production.
   - **Gaps**:
     - MongoDB operations (e.g., connecting, querying) can hang indefinitely without explicit timeouts.
     - Azure uploads lack timeout settings, risking stalled operations for large datasets.
     - No mechanism to abort long-running exports that exceed a reasonable time.

3. **Retry Logic**:
   - **Current State**: There’s no retry logic for failed operations (e.g., MongoDB queries or Azure uploads).
   - **Gaps**:
     - Transient failures (e.g., network issues, temporary service unavailability) are not retried.
     - No exponential backoff or maximum retry limits to prevent overwhelming services.

4. **Other Production Concerns**:
   - **Concurrency**: The script processes collections sequentially, which may be slow for many collections. It could benefit from controlled concurrency.
   - **Logging**: Console logging is insufficient for production; structured logging to a file or service is needed.
   - **Monitoring**: No metrics or alerts for export success/failure rates or durations.
   - **Data Integrity**: No verification that uploaded data matches the source (e.g., checksums or document counts).
   - **Resource Management**: MongoDB connections are closed properly, but there’s no handling for resource leaks in case of crashes.
   - **Idempotency**: If an export partially completes and is retried, it may overwrite or duplicate data without checks.
   - **Scheduling Overlap**: If an export takes longer than an hour, multiple instances could run concurrently, causing conflicts.

### Enhanced Script with Production-Ready Features

Below is an improved version of the script that addresses these concerns:
- Adds robust error handling for MongoDB and Azure operations.
- Configures timeouts for connections and operations.
- Implements retry logic with exponential backoff.
- Adds structured logging using `winston`.
- Includes basic concurrency control for collections.
- Adds cleanup for failed uploads.
- Ensures idempotency by checking for existing files.

```javascript
// app.js
// Enhanced script to export MongoDB collections to ADLS Gen2 hourly with production-ready features.
// Exports data as NDJSON files in the format: collection/YYYY-MM-DD-HH/collection.ndjson
// Features: error handling, timeouts, retries, structured logging, concurrency, idempotency.

// Prerequisites:
// - Install dependencies: npm install mongodb @azure/storage-file-datalake node-cron dotenv winston p-limit
// - Set up .env file with:
//   MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority
//   DB_NAME=your_database_name
//   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<key>;EndpointSuffix=core.windows.net
//   FILE_SYSTEM_NAME=your_adls_container_name
// - Run the script: node app.js

const { MongoClient } = require('mongodb');
const { DataLakeServiceClient } = require('@azure/storage-file-datalake');
const cron = require('node-cron');
const winston = require('winston');
const pLimit = require('p-limit');
const { Readable } = require('stream');
require('dotenv').config();

// Configuration
const config = {
  mongoUri: process.env.MONGO_URI,
  dbName: process.env.DB_NAME,
  azureConnectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
  fileSystemName: process.env.FILE_SYSTEM_NAME,
  mongoConnectTimeout: 5000, // 5 seconds
  mongoSocketTimeout: 30000, // 30 seconds
  azureUploadTimeout: 600000, // 10 minutes
  maxRetries: 3,
  retryDelay: 1000, // Initial delay in ms
  maxConcurrency: 3, // Process 3 collections at a time
};

// Structured logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'export.log' }),
    new winston.transports.Console(),
  ],
});

// Retry helper with exponential backoff
async function withRetry(operation, maxRetries = config.maxRetries, delay = config.retryDelay) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (err) {
      if (attempt === maxRetries) throw err;
      logger.warn(`Retry ${attempt}/${maxRetries} after error: ${err.message}`);
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)));
    }
  }
}

// Export a single collection
async function exportCollection(db, collectionName, fileSystemClient, folderSuffix) {
  const collection = db.collection(collectionName);
  const directoryPath = `${collectionName}/${folderSuffix}`;
  const directoryClient = fileSystemClient.getDirectoryClient(directoryPath);
  const fileClient = directoryClient.getFileClient(`${collectionName}.ndjson`);

  // Check if file already exists (idempotency)
  const exists = await withRetry(async () => {
    try {
      await fileClient.getProperties();
      return true;
    } catch (err) {
      if (err.statusCode === 404) return false;
      throw err;
    }
  });
  if (exists) {
    logger.info(`Skipping ${collectionName}: File already exists at ${directoryPath}/${collectionName}.ndjson`);
    return;
  }

  await withRetry(async () => directoryClient.createIfNotExists());

  const cursor = collection.find({}).maxTimeMS(config.mongoSocketTimeout);
  const readableStream = new Readable({
    read() {},
  });

  let docCount = 0;
  (async () => {
    try {
      for await (const doc of cursor) {
        readableStream.push(JSON.stringify(doc) + '\n');
        docCount++;
      }
      readableStream.push(null);
    } catch (err) {
      readableStream.destroy(err);
    }
  })();

  try {
    await withRetry(async () => {
      const uploadPromise = fileClient.upload(readableStream, {
        timeout: config.azureUploadTimeout,
      });
      // Timeout wrapper
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Azure upload timed out')), config.azureUploadTimeout)
      );
      await Promise.race([uploadPromise, timeoutPromise]);
    });
    logger.info(`Exported ${collectionName} (${docCount} docs) to ${directoryPath}/${collectionName}.ndjson`);
  } catch (err) {
    logger.error(`Failed to export ${collectionName}: ${err.message}`);
    // Clean up partial upload
    await withRetry(async () => fileClient.deleteIfExists());
    throw err;
  }
}

// Main export function
async function exportCollections() {
  const startTime = Date.now();
  logger.info('Starting hourly export...');

  let mongoClient;
  try {
    // Connect to MongoDB with timeout
    mongoClient = new MongoClient(config.mongoUri, {
      connectTimeoutMS: config.mongoConnectTimeout,
      socketTimeoutMS: config.mongoSocketTimeout,
    });
    await withRetry(async () => mongoClient.connect());
    const db = mongoClient.db(config.dbName);
    const collections = await withRetry(async () => db.listCollections().toArray());

    const serviceClient = DataLakeServiceClient.fromConnectionString(config.azureConnectionString);
    const fileSystemClient = serviceClient.getFileSystemClient(config.fileSystemName);

    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const folderSuffix = `${year}-${month}-${day}-${hour}`;

    // Limit concurrency
    const limit = pLimit(config.maxConcurrency);
    const exportPromises = collections
      .filter(coll => !coll.name.startsWith('system.'))
      .map(coll =>
        limit(() =>
          exportCollection(db, coll.name, fileSystemClient, folderSuffix).catch(err => {
            logger.error(`Collection ${coll.name} export failed: ${err.message}`);
            return null; // Continue with other collections
          })
        )
      );

    await Promise.all(exportPromises);
    logger.info(`Export completed in ${(Date.now() - startTime) / 1000}s`);
  } catch (err) {
    logger.error(`Export job failed: ${err.message}`);
    throw err;
  } finally {
    if (mongoClient) await mongoClient.close();
  }
}

// Prevent overlapping runs
let isRunning = false;

// Schedule the export every hour
cron.schedule('0 * * * *', async () => {
  if (isRunning) {
    logger.warn('Previous export still running, skipping this run');
    return;
  }
  isRunning = true;
  try {
    await exportCollections();
  } catch (err) {
    logger.error('Hourly export failed', { error: err.message });
  } finally {
    isRunning = false;
  }
});

logger.info('Scheduler started. Waiting for next hourly run...');
```

### Improvements Made

1. **Error Handling**:
   - Specific error handling for MongoDB connections, queries, and Azure uploads.
   - Cleanup of partial uploads to avoid orphaned files.
   - Structured logging with `winston` to both console and file (`export.log`) for monitoring.

2. **Timeouts**:
   - MongoDB connection and query timeouts set to 5s and 30s, respectively.
   - Azure upload timeout set to 10 minutes, with a `Promise.race` to enforce it.
   - Configurable via `config` object.

3. **Retry Logic**:
   - Added `withRetry` helper with exponential backoff (1s, 2s, 4s for 3 retries).
   - Applied to MongoDB connections, collection listing, directory creation, file existence checks, and uploads.

4. **Concurrency**:
   - Uses `p-limit` to process up to 3 collections concurrently, reducing runtime for many collections while avoiding overwhelming resources.
   - Configurable via `maxConcurrency`.

5. **Idempotency**:
   - Checks if the target file already exists in ADLS before exporting, skipping if present.

6. **Scheduling Safety**:
   - Added `isRunning` flag to prevent overlapping cron jobs if an export takes longer than an hour.

7. **Logging**:
   - Structured JSON logging with timestamps, including document counts and export duration.
   - Logs to both file and console for debugging and monitoring.

8. **Data Integrity**:
   - Tracks document count during export for logging, though full checksum verification could be added if needed.

### Additional Recommendations for Production

1. **Monitoring and Alerts**:
   - Integrate with a monitoring service (e.g., Azure Monitor, Prometheus) to track export success/failure rates and durations.
   - Set up alerts for repeated failures or long-running exports.

2. **Data Verification**:
   - Add post-upload verification (e.g., compare document counts or compute checksums) to ensure data integrity.
   - Example: Download the uploaded file and verify line count matches `docCount`.

3. **Configuration Management**:
   - Move sensitive data (e.g., `MONGO_URI`, `AZURE_STORAGE_CONNECTION_STRING`) to a secure vault (e.g., Azure Key Vault).
   - Make timeouts and retry settings configurable via environment variables.

4. **Performance Optimization**:
   - For very large collections, consider batching documents or using MongoDB’s aggregation pipeline to export incrementally (e.g., by timestamp).
   - Tune `maxConcurrency` based on your MongoDB and Azure capacity.

5. **Security**:
   - Ensure MongoDB and Azure credentials are rotated regularly.
   - Use least-privilege access for MongoDB (read-only role) and Azure (write-only to specific container).

6. **Testing**:
   - Test with large datasets to validate memory usage and performance.
   - Simulate network failures to ensure retry logic works as expected.
   - Verify behavior under MongoDB and Azure service outages.

7. **Backup Strategy**:
   - Consider archiving older exports or implementing a retention policy in ADLS to manage storage costs.

### Dependencies
Install the additional dependencies:
```bash
npm install mongodb @azure/storage-file-datalake node-cron dotenv winston p-limit
```

### Running the Script
1. Create a `.env` file with the required variables (see script comments).
2. Run: `node app.js`.
3. Monitor logs in `export.log` and console output.

This enhanced script is much more suitable for production, with robust error handling, timeouts, retries, and logging. 




The provided code **dumps the entire MongoDB collection** to Azure Data Lake Storage Gen2 (ADLS Gen2) every hour, not just the changes from a change stream. It uses `collection.find({})` to retrieve all documents in each collection and exports them as NDJSON files in the format `collection/YYYY-MM-DD-HH/collection.ndjson`.

### Explanation
- **Current Behavior**: The script iterates through all collections in the specified MongoDB database, queries all documents in each collection using `find({})`, and streams them to ADLS Gen2. This means every hour, it exports the full contents of each collection, regardless of whether the data has changed.
- **Change Stream**: MongoDB’s change streams allow you to listen for real-time changes (inserts, updates, deletes) in a collection. The original and enhanced scripts do not use change streams, so they do not track incremental changes.

### If You Want to Export Only Changes (Using Change Streams)
To modify the script to export only changes since the last export (using MongoDB change streams), you’d need to:
1. Use MongoDB’s `watch()` method to monitor changes on each collection.
2. Store a resume token to track the last processed change.
3. Export only the changed documents to ADLS Gen2.
4. Handle change stream events (e.g., inserts, updates, deletes) appropriately.

Here’s an example of how you could modify the script to use change streams for incremental exports. This version assumes you want to export changes hourly, appending them to a file in ADLS Gen2.

### Modified Script for Change Stream Export
This script watches for changes in each collection since the last run and exports only those changes to ADLS Gen2. It stores resume tokens in a local JSON file to ensure continuity across script restarts.

```javascript
// app.js
// Exports changes from MongoDB collections to ADLS Gen2 hourly using change streams.
// Changes are appended as NDJSON files in the format: collection/YYYY-MM-DD-HH/collection.ndjson
// Features: change stream support, resume tokens, error handling, retries, structured logging.

// Prerequisites:
// - Install dependencies: npm install mongodb @azure/storage-file-datalake node-cron dotenv winston p-limit fs-extra
// - Set up .env file with:
//   MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority
//   DB_NAME=your_database_name
//   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<key>;EndpointSuffix=core.windows.net
//   FILE_SYSTEM_NAME=your_adls_container_name
// - Run the script: node app.js
// - Requires MongoDB replica set or sharded cluster for change streams.

// Note: Change streams require a MongoDB replica set or sharded cluster.

const { MongoClient } = require('mongodb');
const { DataLakeServiceClient } = require('@azure/storage-file-datalake');
const cron = require('node-cron');
const winston = require('winston');
const pLimit = require('p-limit');
const fs = require('fs-extra');
const { Readable } = require('stream');
require('dotenv').config();

// Configuration
const config = {
  mongoUri: process.env.MONGO_URI,
  dbName: process.env.DB_NAME,
  azureConnectionString: process.env.AZURE_STORAGE_CONNECTION_STRING,
  fileSystemName: process.env.FILE_SYSTEM_NAME,
  mongoConnectTimeout: 5000,
  mongoSocketTimeout: 30000,
  azureUploadTimeout: 600000,
  maxRetries: 3,
  retryDelay: 1000,
  maxConcurrency: 3,
  resumeTokenFile: 'resumeTokens.json',
};

// Structured logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'export.log' }),
    new winston.transports.Console(),
  ],
});

// Retry helper
async function withRetry(operation, maxRetries = config.maxRetries, delay = config.retryDelay) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (err) {
      if (attempt === maxRetries) throw err;
      logger.warn(`Retry ${attempt}/${maxRetries} after error: ${err.message}`);
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)));
    }
  }
}

// Load and save resume tokens
async function loadResumeTokens() {
  try {
    return await fs.readJson(config.resumeTokenFile);
  } catch (err) {
    if (err.code === 'ENOENT') return {};
    throw err;
  }
}

async function saveResumeToken(collectionName, token) {
  const tokens = await loadResumeTokens();
  tokens[collectionName] = token;
  await fs.writeJson(config.resumeTokenFile, tokens);
}

// Export changes for a single collection
async function exportCollectionChanges(db, collectionName, fileSystemClient, folderSuffix, resumeTokens) {
  const collection = db.collection(collectionName);
  const directoryPath = `${collectionName}/${folderSuffix}`;
  const directoryClient = fileSystemClient.getDirectoryClient(directoryPath);
  const fileClient = directoryClient.getFileClient(`${collectionName}.ndjson`);

  await withRetry(async () => directoryClient.createIfNotExists());

  const readableStream = new Readable({
    read() {},
  });

  let docCount = 0;
  const changeStreamOptions = resumeTokens[collectionName]
    ? { resumeAfter: resumeTokens[collectionName] }
    : {};
  const changeStream = collection.watch([], {
    ...changeStreamOptions,
    maxAwaitTimeMS: config.mongoSocketTimeout,
  });

  try {
    // Process changes until the hour is up or no more changes are available
    const endTime = Date.now() + 60 * 60 * 1000; // 1 hour from now
    while (Date.now() < endTime) {
      const next = await Promise.race([
        changeStream.next(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Change stream timeout')), config.mongoSocketTimeout)
        ),
      ]);
      if (!next) break; // No more changes
      readableStream.push(JSON.stringify(next) + '\n');
      docCount++;
      // Save resume token after each change
      await saveResumeToken(collectionName, next._id);
    }
    readableStream.push(null);
  } catch (err) {
    readableStream.destroy(err);
    throw err;
  } finally {
    await changeStream.close();
  }

  if (docCount === 0) {
    logger.info(`No changes for ${collectionName} in ${folderSuffix}`);
    return;
  }

  try {
    await withRetry(async () => {
      const uploadPromise = fileClient.upload(readableStream, {
        timeout: config.azureUploadTimeout,
      });
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Azure upload timed out')), config.azureUploadTimeout)
      );
      await Promise.race([uploadPromise, timeoutPromise]);
    });
    logger.info(`Exported ${docCount} changes for ${collectionName} to ${directoryPath}/${collectionName}.ndjson`);
  } catch (err) {
    logger.error(`Failed to export changes for ${collectionName}: ${err.message}`);
    await withRetry(async () => fileClient.deleteIfExists());
    throw err;
  }
}

// Main export function
async function exportCollectionChangesHourly() {
  const startTime = Date.now();
  logger.info('Starting hourly change stream export...');

  let mongoClient;
  try {
    mongoClient = new MongoClient(config.mongoUri, {
      connectTimeoutMS: config.mongoConnectTimeout,
      socketTimeoutMS: config.mongoSocketTimeout,
    });
    await withRetry(async () => mongoClient.connect());
    const db = mongoClient.db(config.dbName);
    const collections = await withRetry(async () => db.listCollections().toArray());

    const serviceClient = DataLakeServiceClient.fromConnectionString(config.azureConnectionString);
    const fileSystemClient = serviceClient.getFileSystemClient(config.fileSystemName);

    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const folderSuffix = `${year}-${month}-${day}-${hour}`;

    const resumeTokens = await loadResumeTokens();
    const limit = pLimit(config.maxConcurrency);
    const exportPromises = collections
      .filter(coll => !coll.name.startsWith('system.'))
      .map(coll =>
        limit(() =>
          exportCollectionChanges(db, coll.name, fileSystemClient, folderSuffix, resumeTokens).catch(err => {
            logger.error(`Collection ${coll.name} change export failed: ${err.message}`);
            return null;
          })
        )
      );

    await Promise.all(exportPromises);
    logger.info(`Change stream export completed in ${(Date.now() - startTime) / 1000}s`);
  } catch (err) {
    logger.error(`Export job failed: ${err.message}`);
    throw err;
  } finally {
    if (mongoClient) await mongoClient.close();
  }
}

// Prevent overlapping runs
let isRunning = false;

cron.schedule('0 * * * *', async () => {
  if (isRunning) {
    logger.warn('Previous export still running, skipping this run');
    return;
  }
  isRunning = true;
  try {
    await exportCollectionChangesHourly();
  } catch (err) {
    logger.error('Hourly change stream export failed', { error: err.message });
  } finally {
    isRunning = false;
  }
});

logger.info('Scheduler started. Waiting for next hourly run...');
```

### Key Changes for Change Stream Support
1. **Change Stream Usage**:
   - Uses `collection.watch()` to monitor changes (inserts, updates, deletes) in each collection.
   - Processes changes within the current hour, stopping when the hour ends or no more changes are available.
   - Exports change stream events (including operation type, document, and metadata) as NDJSON.

2. **Resume Tokens**:
   - Stores resume tokens in a `resumeTokens.json` file to track the last processed change per collection.
   - Loads tokens at startup to resume from the last change, ensuring no changes are missed across script restarts.

3. **Incremental Export**:
   - Only changed documents are exported, reducing data volume compared to full collection dumps.
   - If no changes occur in an hour, no file is created.

4. **Dependencies**:
   - Added `fs-extra` for reliable JSON file handling (`npm install fs-extra`).

### Considerations for Change Streams
- **MongoDB Requirements**: Change streams require a MongoDB replica set or sharded cluster. Ensure your MongoDB Atlas deployment meets this requirement.
- **Change Stream Events**: The exported NDJSON files contain full change stream events (e.g., `{ operationType: "insert", fullDocument: {...}, ... }`). If you only want the document data, modify the script to extract `fullDocument` or handle specific operation types.
- **Performance**: Change streams are efficient for incremental updates, but processing many collections with high change rates may require tuning `maxConcurrency`.
- **Storage**: Change stream exports are smaller than full dumps but may still accumulate over time. Implement a retention policy in ADLS if needed.
- **Error Handling**: The script retains robust error handling, retries, and logging from the previous version.

### Choosing Between Full Dump and Change Stream
- **Full Collection Dump** (Original/Enhanced Script):
  - Use when you need a complete snapshot of the collection every hour.
  - Suitable for analytics or backups requiring the full dataset.
  - Higher storage and processing overhead.
- **Change Stream Export** (Modified Script):
  - Use when you only need incremental changes (e.g., for real-time analytics or auditing).
  - Requires a replica set and careful management of resume tokens.
  - Lower storage and processing overhead but requires handling change event formats.

### Additional Notes
- **Testing**: Test the change stream script in a staging environment, especially to verify resume token persistence and handling of high change volumes.
- **Resume Token Storage**: Storing tokens in a JSON file is simple but may not be ideal for distributed systems. Consider storing tokens in MongoDB or another durable store for production.
- **Change Stream Limitations**: Change streams don’t capture historical data before the script starts. If you need an initial full dump, run the original script once, then switch to change streams.

If you want a hybrid approach (e.g., periodic full dumps plus change streams) or further customization (e.g., filtering specific change types), let me know!
