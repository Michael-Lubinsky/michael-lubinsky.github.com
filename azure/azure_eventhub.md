# Azure Eventhub

### Azure Event Hubs

<https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features?WT.mc_id=Portal-Microsoft_Azure_EventHub>

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



### `EventHubConsumerClient` is the JavaScript client you use to **receive** events from an Azure Event Hub 
(all partitions or specific ones). 
It exposes methods like `subscribe(...)`, `getPartitionIds()`, `getEventHubProperties()`,  
and works with Azure AD credentials or connection strings.   
With a Blob **checkpoint store**, it can checkpoint offsets and **load-balance** partitions across multiple consumers in the same consumer group.  

Full docs (official Microsoft Learn):

* API reference for `EventHubConsumerClient` (JS). ([Microsoft Learn][1])
* JS client library overview + guides & auth options. ([Microsoft Learn][2])
* Official samples (receive/send, checkpointing). ([Microsoft Learn][3])

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

If you tell me which of the three scenarios you want, I can show the exact code/config (same group with load-balancing vs. separate groups).

[1]: https://learn.microsoft.com/en-us/javascript/api/overview/azure/event-hubs-readme?view=azure-node-latest&utm_source=chatgpt.com "Azure Event Hubs client library for JavaScript"
[2]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features?utm_source=chatgpt.com "Overview of features - Azure Event Hubs"
[3]: https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-about?utm_source=chatgpt.com "Azure Event Hubs: Data streaming platform with Kafka ..."
[4]: https://learn.microsoft.com/en-us/javascript/api/%40azure/event-hubs/subscribeoptions?view=azure-node-latest&utm_source=chatgpt.com "SubscribeOptions interface"
