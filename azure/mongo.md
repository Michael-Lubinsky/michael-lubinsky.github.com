
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

I’ll give you (A) a direct writer (simplest, full control of the path), and (B) an Event Hubs route (use Capture for durability, then a tiny post-process to reshape folders).

---

# A) Direct: Change Streams → ADLS (exact path)

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

# B) Event Hubs in the middle: ASP/Producer → Event Hubs → Capture → (reshape to target folders)

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

Unfortunately, **MongoDB Atlas Stream Processing** doesn't support writing to **Azure Data Lake Storage (ADLS)** as a sink. It primarily focuses on real-time data processing and writing to other stream processing platforms or databases, such as other MongoDB collections, Kafka, and Amazon S3. For periodic data exports to ADLS, you'll need to use a different approach.

-----

## Recommended Approach Using Azure Functions

A robust and common way to achieve your goal is to use an **Azure Function** with a **Node.js** runtime. This serverless solution allows you to schedule a function to run periodically and handle the data export logic.

### 1\. Set Up Your Environment

First, you'll need a **MongoDB Atlas cluster** and an **Azure Storage account** with a **Data Lake Storage Gen2** enabled. Create an Azure Function App in the Azure portal and select a Node.js runtime.

### 2\. Write the Node.js Code

The core of your solution will be a Node.js script that connects to your MongoDB Atlas cluster, queries the desired collection, and writes the data to ADLS.

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
