# Azure Eventhub

### Azure Event Hubs

<https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features?WT.mc_id=Portal-Microsoft_Azure_EventHub>

In Event Hubs, a single Event Hub is roughly analogous to a Kafka topic; inside it you have partitions and consumer groups.

#### Event retention

Published events are removed from an event hub based on a configurable, timed-based retention policy. Here are a few important points:
- The default value and shortest possible retention period is 1 hour.  
- For Event Hubs Standard, the maximum retention period is 7 days.  
- For Event Hubs Premium and Dedicated, the maximum retention period is 90 days.  

If you need to archive events beyond the allowed retention period, you can have them automatically stored in Azure Storage or Azure Data Lake by turning on the Event Hubs Capture feature.

Event Hubs Capture enables you to automatically capture the streaming data in Event Hubs and save it to your choice of either a Blob storage account, or an Azure Data Lake Storage account.   
You can enable capture from the Azure portal, and specify a minimum size and time window to perform the capture.   
Using Event Hubs Capture, you specify your own Azure Blob Storage account and container, or Azure Data Lake Storage account, one of which is used to store the captured data.  
Captured data is written in the Apache Avro format.

#### Mapping of events to partitions

Specifying a partition key enables keeping related events together in the same partition and in the exact order in which they arrived.   
The partition key is some string that is derived from your application context and identifies the interrelationship of the events.  


#### Checkpointing

Checkpointing is a process by which readers mark or commit their position within a partition event sequence.   
Checkpointing is the responsibility of the consumer and occurs on a per-partition basis within a consumer group.  
This responsibility means that for each consumer group, each partition reader must keep track of its current position in the event stream, and can inform the service when it considers the data stream complete.


If a reader disconnects from a partition, when it reconnects it begins reading at the checkpoint that was previously submitted by the last reader of that partition in that consumer group.  

When the reader connects, it passes the offset to the event hub to specify the location at which to start reading. In this way, you can use checkpointing to both mark events as "complete" by downstream applications, and to provide resiliency if a failover between readers running on different machines occurs.  

It's possible to return to older data by specifying a lower offset from this checkpointing process. Through this mechanism, checkpointing enables both failover resiliency and event stream replay.


#### Claude suggestion for checkpoint fix

Looking at your code, I can see the main issue with EventHub checkpoint handling. Your current implementation creates a custom checkpoint file in ADLS Gen2, but it doesn't integrate with the Azure EventHub SDK's built-in checkpoint store mechanism. This means your consumer will always start from the latest position and won't properly resume from where it left off.

Let me fix this by implementing proper EventHub checkpointing using Azure Blob Storage as the checkpoint store.Here are the key fixes I've implemented to properly handle EventHub checkpoints:

## Major Changes Made:

### 1. **Proper Checkpoint Store Integration**
- Added `@azure/eventhubs-checkpointstore-blob` dependency for Azure Blob checkpoint store
- Configured `BlobCheckpointStore` to persist checkpoints in Azure Blob Storage
- EventHub consumer now automatically resumes from the last processed position

### 2. **Built-in Checkpoint Management**
- Replaced custom checkpoint logic with Azure SDK's built-in checkpointing
- Uses `partitionContext.updateCheckpoint(event)` method for proper checkpoint updates
- Checkpoints are now stored in the Azure-standard format that EventHub SDK understands

### 3. **Enhanced Configuration**
```javascript
checkpointContainerName: process.env.CHECKPOINT_CONTAINER_NAME || 'eventhub-checkpoints',
checkpointFrequency: parseInt(process.env.CHECKPOINT_FREQUENCY) || 10, // Checkpoint every N batches
startFromBeginning: process.env.START_FROM_BEGINNING === "true"
```

### 4. **Improved Event Processing Flow**
- Events are tracked per partition during processing
- Checkpoints are updated after successful data serialization to ADLS Gen2
- Only the latest processed event per partition is checkpointed
- Configurable checkpoint frequency to balance performance vs. reliability

### 5. **Better Error Handling**
- Checkpoint failures don't stop event processing
- Each partition's checkpoint is updated independently
- Proper cleanup of processed events after checkpointing

## Required Dependencies:
Make sure to install the checkpoint store package:
```bash
npm install @azure/eventhubs-checkpointstore-blob
```

## Environment Variables to Add:
```bash
# Checkpoint configuration
CHECKPOINT_CONTAINER_NAME=eventhub-checkpoints
CHECKPOINT_FREQUENCY=10
START_FROM_BEGINNING=false
```

## How It Works:

1. **First Run**: If `START_FROM_BEGINNING=true`, processes from the beginning of the stream. Otherwise starts from latest.

2. **Subsequent Runs**: Automatically resumes from the last checkpointed position for each partition.

3. **Checkpointing**: Updates checkpoints every N batches (configurable) after successful data upload to ADLS Gen2.

4. **Recovery**: If the process crashes and restarts, it will automatically resume from the last checkpoint.

The key improvement is that your consumer will now properly resume processing from where it left off, preventing duplicate processing and ensuring no events are lost during restarts or failures.



Gemini suggestion for checkpoint fix:

Short answer: your code isn’t “wrong,” but it’s **not an Event Hubs checkpoint store**. You’re just writing a JSON file to ADLS Gen2. The “use an isolated container” guidance applies to the **official Blob checkpoint store** (`BlobCheckpointStore`) that the SDK knows how to use. Since you aren’t passing a checkpoint store to `EventHubConsumerClient`, the SDK will **not resume** from your `_checkpoints/latest.json`, nor will it load-balance/coordinate from it.

### What the doc means by “isolated container”

When you use the official checkpoint store:

* You create a **separate blob container** (e.g. `eh-checkpoints-myapp`), dedicated to checkpoints/ownership.
* You pass it to the consumer client; the SDK then writes **per-partition** checkpoints and uses leases for load-balancing.

### What your code does

* Aggregates offsets per partition and writes a single file `_checkpoints/latest.json` in your **data** filesystem.
* The Event Hubs SDK **doesn’t read this file**, so next run will start from `latestEventPosition` (new events only), not from your JSON.

If your goal is “proper” checkpointing & resume/load-balancing, switch to the official store:

```js
import { DefaultAzureCredential } from "@azure/identity";
import { EventHubConsumerClient } from "@azure/event-hubs";
import { BlobServiceClient } from "@azure/storage-blob";
import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";

const credential = new DefaultAzureCredential();

// dedicated container just for checkpoints
const blobSvc = new BlobServiceClient(`https://${ACCOUNT}.blob.core.windows.net`, credential);
const container = blobSvc.getContainerClient("eh-checkpoints-changestream");
await container.createIfNotExists();

const checkpointStore = new BlobCheckpointStore(container);

const consumer = new EventHubConsumerClient(
  CONSUMER_GROUP,
  EVENTHUB_FQDN,
  EVENTHUB_NAME,
  credential,
  checkpointStore
);

const subscription = consumer.subscribe({
  processEvents: async (events, ctx) => {
    // ...process...
    if (events.length) {
      await ctx.updateCheckpoint(events[events.length - 1]); // SDK persists per-partition checkpoint
    }
  },
  processError: async (err) => console.error(err)
});
```

### If you want to keep your custom JSON file

That’s fine as an **audit/log**, but to make it functional you’d need to:

1. **Read it at startup** and construct **per-partition** start positions.

2. Use **per-partition clients** so you can pass different `startPosition` for each partition:

   ```js
   const positions = {/* "0": { sequenceNumber: "..." }, ... */};
   for (const pid of await consumer.getPartitionIds()) {
     const pc = consumer.createPartitionClient(pid, { startPosition: positions[pid] ?? latestEventPosition });
     const events = await pc.receiveBatch(…);
     await pc.close();
   }
   ```

   (A single `subscribe({ startPosition })` can only take **one** start position for **all** partitions.)

3. Handle **concurrency/atomicity**:

   * Avoid `deleteIfExists()` + `create()` races; write to a temp file and **rename** to `latest.json`, or include an ETag condition.
   * If multiple instances run, they’ll overwrite each other—no leases/ownership.

4. Consider keeping the checkpoint file in its **own filesystem/container** so it doesn’t get picked up by downstream ingestion/lifecycle policies (this mirrors the “isolated container” advice).

### Verdict

* If you want real Event Hubs checkpointing & scaling: **Yes, there’s an issue**—you’re not using a checkpoint store the SDK understands.
* If you only want a human-readable progress file: your code is **okay**, but it doesn’t influence the consumer’s starting point, and you should harden it (atomic writes, per-partition starts, isolation).


### `EventHubConsumerClient` is the JavaScript client you use to **receive** events from an Azure Event Hub 
(all partitions or specific ones). 
It exposes methods like `subscribe(...)`, `getPartitionIds()`, `getEventHubProperties()`,  
and works with Azure AD credentials or connection strings.   
With a Blob **checkpoint store**, it can checkpoint offsets and **load-balance** partitions across multiple consumers in the same consumer group.  

Full docs (official Microsoft Learn):

* API reference for `EventHubConsumerClient` (JS). ([Microsoft Learn][1])
* JS client library overview + guides & auth options. ([Microsoft Learn][2])
* Official samples (receive/send, checkpointing). ([Microsoft Learn][3])

AAD = Azure Active Directory.  
Minimal AAD example (no connection string):

```js
import { DefaultAzureCredential } from "@azure/identity";
import { EventHubConsumerClient, latestEventPosition } from "@azure/event-hubs";

const credential = new DefaultAzureCredential();
const consumer = new EventHubConsumerClient(
  "$Default",                      // consumer group
  "mynamespace.servicebus.windows.net", // FQDN
  "myeventhub",                    // event hub name
  credential
);

const subscription = consumer.subscribe(
  {
    processEvents: async (events, ctx) => {
      for (const ev of events) {
        console.log(`[${ctx.partitionId}]`, ev.body);
      }
    },
    processError: async (err, ctx) => {
      console.error(`[${ctx.partitionId}]`, err.message);
    }
  },
  { startPosition: latestEventPosition }
);

// later:
// await subscription.close(); await consumer.close();
```

(For coordinated checkpoints/load-balancing, add the Blob checkpoint store package and pass it to the constructor.) ([Microsoft Learn][4])

Permissions tip: to receive, your identity needs **Azure Event Hubs Data Receiver** on the hub/namespace.  
Quickstarts also show connection-string alternatives if you prefer. ([Microsoft Learn][5])

[1]: https://learn.microsoft.com/en-us/javascript/api/%40azure/event-hubs/eventhubconsumerclient?view=azure-node-latest&utm_source=chatgpt.com "EventHubConsumerClient class | Microsoft Learn"
[2]: https://learn.microsoft.com/en-us/javascript/api/overview/azure/event-hubs-readme?view=azure-node-latest&utm_source=chatgpt.com "Azure Event Hubs client library for JavaScript"
[3]: https://learn.microsoft.com/en-us/samples/azure/azure-sdk-for-js/event-hubs-javascript/?utm_source=chatgpt.com "Azure Event Hubs client library samples for JavaScript"
[4]: https://learn.microsoft.com/en-us/javascript/api/overview/azure/eventhubs-checkpointstore-blob-readme?view=azure-node-latest&utm_source=chatgpt.com "Azure Event Hubs Checkpoint Store client library for ..."
[5]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-node-get-started-send?utm_source=chatgpt.com "Send or receive events using JavaScript - Azure Event Hubs"



#### Send events to or receive events from event hubs by using JavaScript
<https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-node-get-started-send?tabs=passwordless%2Croles-azure-portal>


## When two Node.js applications read from the same Event Hub using `EventHubConsumerClient`  

they will compete for the same events unless you configure them properly. The key concept to understand here is the **consumer group**.

An Azure Event Hub can have multiple consumer groups. A consumer group is a view over the entire Event Hub data stream.   
It acts like a unique pointer, allowing multiple applications to read the same events from the Event Hub without interfering with each other.

### How It Works

1.  **Shared Consumer Group:** If both of your Node.js applications use the same consumer group (like the default `$Default`), they will **compete** to receive events. Only one application's partition consumer can "own" a specific partition at a time. The Event Hub service uses a load-balancing mechanism to distribute the partitions among the competing consumers. So, at any given moment, one app might read from partition 0 and another from partition 1, but they won't both read from the same partition simultaneously.

2.  **Dedicated Consumer Groups:** For most use cases, it's best to have each application use its own dedicated consumer group. If App A uses `consumerGroupA` and App B uses `consumerGroupB`, they will both receive a **full copy** of all events sent to the Event Hub, completely independently of each other. This is the standard pattern for a publish-subscribe model, where each subscriber gets its own copy of the messages.

### The "eventhub-to-adls" Canvas

The code in the `eventhub-to-adls` Canvas uses the `$Default` consumer group. If you were to run two instances of this program, they would effectively be competing for partitions. The Event Hub service would handle the load balancing, ensuring that each event is processed exactly once by one of the running instances.

To have two applications read the same data independently, you would need to:

1.  Create a new consumer group in the Azure Portal or via the Azure CLI (e.g., `adls-archiver-cg`).
2.  Update one of your applications to use this new consumer group name in its configuration.

By using separate consumer groups, your two applications can operate on the same data stream without any conflict, which is typically the desired behavior for a robust, decoupled system.



Short answer: it depends on **consumer groups** and whether the apps **coordinate via a checkpoint store**.

### Scenarios

* **Same consumer group + shared checkpoint store (BlobCheckpointStore)**
  The SDK will **load-balance partitions** between the two apps and **checkpoint** progress. If one app stops, the other takes over. This is the recommended way to scale out a single logical consumer. ([Microsoft Learn][1])

* **Same consumer group + no checkpoint store (or different stores)**
  The apps don’t coordinate, so they can **both read the same partitions**, causing **duplicate processing**. Event Hubs allows up to **5 concurrent readers per partition per consumer group**, but Microsoft recommends **one active reader per partition** to avoid duplicates. ([Microsoft Learn][2])

* **Different consumer groups**
  Each app has its **own independent view** of the stream (own offsets), so **both receive all events** from all partitions. Use this when the apps serve **different workloads/pipelines**. ([Microsoft Learn][3])

### (Optional) Exclusive readers / “epoch”

If you need to force **exactly one** reader per partition in a consumer group, you can set an **owner level** (aka epoch) so the highest owner wins and others are disconnected. In JS, this is the `ownerLevel` option on `subscribe()`. Usually you don’t need this when using the checkpoint store. ([Microsoft Learn][4])

### How to coordinate two Node apps (JS)

Use the blob checkpoint store so they cooperate:

```js
import { DefaultAzureCredential } from "@azure/identity";
import { EventHubConsumerClient } from "@azure/event-hubs";
import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";
import { BlobServiceClient } from "@azure/storage-blob";

const credential = new DefaultAzureCredential();

const blobSvc = new BlobServiceClient(`https://${ACCOUNT}.blob.core.windows.net`, credential);
const container = blobSvc.getContainerClient("eh-checkpoints");
await container.createIfNotExists();

const checkpointStore = new BlobCheckpointStore(container);

const consumer = new EventHubConsumerClient(
  "$Default",
  "mynamespace.servicebus.windows.net",
  "myeventhub",
  credential,
  checkpointStore            // <<< enables load-balancing + checkpoints
);

const sub = consumer.subscribe({
  processEvents: async (events, ctx) => { /* handle */ },
  processError: async (err) => console.error(err)
});
```

This setup lets multiple instances in the **same consumer group** share work and fail over cleanly. ([Microsoft Learn][1])

### Key limits to remember

* **≤5 readers per partition per consumer group**; recommended **one** active reader per partition to avoid duplicates. ([Microsoft Learn][2])



[1]: https://learn.microsoft.com/en-us/javascript/api/overview/azure/event-hubs-readme?view=azure-node-latest&utm_source=chatgpt.com "Azure Event Hubs client library for JavaScript"
[2]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features?utm_source=chatgpt.com "Overview of features - Azure Event Hubs"
[3]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-about?utm_source=chatgpt.com "Azure Event Hubs: Data streaming platform with Kafka ..."
[4]: https://learn.microsoft.com/en-us/javascript/api/%40azure/event-hubs/subscribeoptions?view=azure-node-latest&utm_source=chatgpt.com "SubscribeOptions interface"


## Here’s how the **“different consumer groups”** setup works and how to do it in Node.js.

* You create **two consumer groups** on the same Event Hub (e.g., `cg-appA` and `cg-appB`).
* **App A** connects with `cg-appA`; **App B** connects with `cg-appB`.
* Each group has its **own cursor/checkpoints**. So:

  * Both apps receive **all** events from all partitions independently.
  * They can start at different positions (e.g., `earliest` vs `latest`) and **won’t affect each other**.
  * If App A falls behind or is stopped, App B is unaffected.
* Use this when two downstreams/pipelines must process the **same stream independently** (e.g., real-time alerts vs. analytics, A/B experiments, version migrations).

Notes:

* Checkpointing is **per consumer group**. Use separate checkpoint stores (or prefixes) for each group.
* Each consumer group has its own concurrency/reader limits per partition—avoid unnecessary multiple readers per partition in the same group.
* Reading the same data in two groups results in **two independent reads** (separate egress).

---

## Create consumer groups (one-time)

```bash
az eventhubs eventhub consumer-group create \
  --resource-group <rg> \
  --namespace-name <namespace> \
  --eventhub-name <hub> \
  --name cg-appA

az eventhubs eventhub consumer-group create \
  --resource-group <rg> \
  --namespace-name <namespace> \
  --eventhub-name <hub> \
  --name cg-appB
```

---

## Minimal Node.js consumer (AAD auth) — run twice with different groups
AAD = Azure Active Directory.
```js
// file: consumer.js
// Usage:
//   export SUBSCRIPTION_ID=<sub-id>        # only needed if you also list namespaces elsewhere
//   export EVENTHUB_FQDN='myns.servicebus.windows.net'
//   export EVENTHUB_NAME='myhub'
//   export CONSUMER_GROUP='cg-appA'         # or cg-appB for the second app
//   node consumer.js
//
// Optional: add a Blob checkpoint store so offsets persist across restarts.

import { DefaultAzureCredential } from "@azure/identity";
import { EventHubConsumerClient, latestEventPosition } from "@azure/event-hubs";

// Optional checkpoint store (recommended for production)
// npm i @azure/storage-blob @azure/eventhubs-checkpointstore-blob
// import { BlobServiceClient } from "@azure/storage-blob";
// import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";

const fqdn = process.env.EVENTHUB_FQDN;          // e.g., "myns.servicebus.windows.net"
const hub  = process.env.EVENTHUB_NAME;          // e.g., "myhub"
const group = process.env.CONSUMER_GROUP || "$Default";

if (!fqdn || !hub) {
  console.error("Please set EVENTHUB_FQDN and EVENTHUB_NAME.");
  process.exit(1);
}

const credential = new DefaultAzureCredential();

// OPTIONAL checkpoint store example (uncomment if you want durable checkpoints)
/*
const blobAccount = process.env.BLOB_ACCOUNT;    // e.g., "mystorage"
const blobContainer = process.env.BLOB_CONTAINER || `eh-checkpoints-${group}`;
if (!blobAccount) console.warn("No BLOB_ACCOUNT set; running without checkpointing.");
const blobSvc = blobAccount
  ? new BlobServiceClient(`https://${blobAccount}.blob.core.windows.net`, credential)
  : undefined;
const containerClient = blobSvc && blobSvc.getContainerClient(blobContainer);
if (containerClient) await containerClient.createIfNotExists();
const checkpointStore = containerClient ? new BlobCheckpointStore(containerClient) : undefined;
*/

const consumer = new EventHubConsumerClient(
  group,
  fqdn,
  hub,
  credential
  // , checkpointStore   // pass this 5th arg if you enabled the checkpoint store above
);

const subscription = consumer.subscribe(
  {
    processEvents: async (events, ctx) => {
      for (const ev of events) {
        console.log(`[${group} | partition ${ctx.partitionId} | seq ${ev.sequenceNumber}]`, ev.body);
      }
    },
    processError: async (err, ctx) => {
      console.error(`[${group} | partition ${ctx.partitionId}] ERROR: ${err.message}`);
    }
  },
  {
    startPosition: latestEventPosition,   // or earliestEventPosition
    maxBatchSize: 50,
    maxWaitTimeInSeconds: 5
  }
);

process.on("SIGINT", async () => {
  console.log("\nShutting down…");
  await subscription.close();
  await consumer.close();
  process.exit(0);
});
```

Run two independent apps (each sees the full stream):

```bash
# terminal 1
export EVENTHUB_FQDN='myns.servicebus.windows.net'
export EVENTHUB_NAME='myhub'
export CONSUMER_GROUP='cg-appA'
node consumer.js

# terminal 2
export EVENTHUB_FQDN='myns.servicebus.windows.net'
export EVENTHUB_NAME='myhub'
export CONSUMER_GROUP='cg-appB'
node consumer.js
```

(If you enable checkpointing, point each app to a **different** blob container or use distinct prefixes so their offsets don’t collide.)

---

## When to choose this pattern

* Two (or more) independent pipelines must **both** read everything (e.g., fraud detection and BI).
* You’re migrating consumers (new app in `cg-new`, old app in `cg-old`) and want **parallel run** with safe rollback.
* Different retention/starting points or replay behavior per app (e.g., one starts from `earliest`, the other from `latest`).

If you want, I can add the Blob checkpoint store wiring (with env vars) to make the sample production-ready for both consumer groups.



## `EventHubManagementClient` and `EventHubConsumerClient` are two distinct clients in the Azure Event Hubs library for Node.js, 
each serving a different purpose. 
The core difference lies in their functionality: one is for administrative tasks, and the other is for data operations.

### EventHubManagementClient 🛠️

The **`EventHubManagementClient`** is an administrative client used for managing Event Hubs resources. It's designed for tasks that involve provisioning, configuring, and maintaining the Event Hubs namespace and its entities. You'd typically use this client in a dev-ops or automation script rather than in an application that is actively sending or receiving data.

**Key functions include:**
* Creating, updating, and deleting Event Hubs namespaces.
* Creating, updating, and deleting individual Event Hubs within a namespace.
* Creating, updating, and deleting consumer groups.
* Managing authorization rules and keys.
* Getting properties and metadata for Event Hubs.

***

### EventHubConsumerClient 📊

The **`EventHubConsumerClient`** is a data-plane client used for consuming events from an Event Hub. Its primary function is to read and process the stream of data that has been sent to the Event Hub. It is the component an application uses to receive messages.

**Key functions include:**
* Connecting to an Event Hub and a specific consumer group.
* Receiving events from one or more partitions.
* Handling load balancing when multiple consumer instances are reading from the same consumer group.
* Managing checkpoints to track the last successfully processed event, preventing the application from reprocessing data after a restart. This is a crucial feature for building resilient and scalable consumer applications.

In short, `EventHubManagementClient` is for **control-plane operations** (managing the infrastructure), while `EventHubConsumerClient` is for **data-plane operations** (interacting with the data stream). 
