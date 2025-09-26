<https://learn.microsoft.com/en-us/azure/azure-functions/functions-overview>

<https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview?tabs=in-process%2Cnodejs-v3%2Cv1-model&pivots=csharp>


### How  to run Azure Function  **once per hour** 
and read from **Azure Event Hubs** using an **Azure Functions (JavaScript)** **Timer Trigger**. The function uses **AAD (DefaultAzureCredential)** and a **Blob checkpoint store** so each hourly run resumes where the last one left off (no reprocessing).

---
You already have a Node.js file (say `index.js`) and you want to run it as an **Azure Function** that executes every hour.  
Here’s the step-by-step:

---

# 1. Create a Function App (Node.js runtime)

From your project folder (where your Node.js file is):

```bash
func init my-func-app --worker-runtime node --language javascript
cd my-func-app
```

This sets up the boilerplate for an Azure Function App using Node.js.

---

# 2. Add a Timer-triggered Function

Create a new function with a **timer trigger**:

```bash
func new --template "Timer trigger" --name MyHourlyJob
```

This creates:

* `MyHourlyJob/index.js`
* `MyHourlyJob/function.json`

---

# 3. Configure the Schedule

Open `MyHourlyJob/function.json`. You’ll see something like:

```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */5 * * * *"
    }
  ]
}
```

* The `schedule` is a **CRON expression**.
* For “every hour, at minute 0” → use:

```json
"schedule": "0 0 * * * *"
```

---

# 4. Call Your Node.js File

Inside `MyHourlyJob/index.js`, require and call your existing module. Example:

```js
const myProcessor = require('../path-to-your-file');  // adjust path

module.exports = async function (context, myTimer) {
    context.log('Hourly function triggered:', new Date().toISOString());

    try {
        const result = await myProcessor(); // if your file exports a function
        context.log('Success:', result);
    } catch (err) {
        context.log.error('Error in hourly job:', err);
    }
};
```

---

# 5. Run Locally (Test)

Make sure you have the Azure Functions Core Tools installed (`npm i -g azure-functions-core-tools@4`).
Run:

```bash
func start
```

It will execute your function on schedule locally.

---

# 6. Deploy to Azure

If you haven’t yet, create the Azure resources:

```bash
az functionapp create \
  --resource-group <your-resource-group> \
  --consumption-plan-location <region> \
  --runtime node \
  --runtime-version 18 \
  --functions-version 4 \
  --name <your-func-app-name> \
  --storage-account <your-storage-account>
```

Then deploy:

```bash
func azure functionapp publish <your-func-app-name>
```

---

# ✅ Summary

* Use **Timer Trigger** Azure Function.
* Configure CRON `0 0 * * * *` for hourly execution.
* Inside the function, **require your Node.js file** and call it.
* Test locally with `func start`, then deploy with `func azure functionapp publish`.

---

Do you want me to also show the **CRON schedule examples** (like every 30 min, daily at midnight, etc.) so you can tweak the schedule easily later?

---

## Project layout 
```
my-hourly-func/
├─ host.json
├─ local.settings.json          # local-only secrets/settings
├─ package.json
├─ pullHourly/                  # the Timer-triggered function
│  ├─ function.json
│  └─ index.js
```

---

## 1) Create the Function

```bash
mkdir my-hourly-func && cd my-hourly-func
func init . --worker-runtime javascript --model V4
func new --template "Timer trigger" --name pullHourly
npm i @azure/identity @azure/event-hubs @azure/storage-blob @azure/eventhubs-checkpointstore-blob
```

---

## 2) Bindings (cron schedule = every hour on the hour, UTC)

**pullHourly/function.json**

```json
{
  "bindings": [
    {
      "name": "myTimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 * * * *"
    }
  ]
}
```

Notes:

* NCRONTAB format is: `{second} {minute} {hour} {day} {month} {day-of-week}`.
* The schedule is **UTC** by default. If you need local time, either (a) adjust the cron for your offset, or (b) on **Windows plans** set the app setting `WEBSITE_TIME_ZONE=America/Los_Angeles`. On Linux plans, keep UTC and adjust the cron.

---

## 3) Timer function code (reads up to N seconds, checkpoints, then exits)

**pullHourly/index.js**

```js
// Reads new events once per hour using AAD and a Blob checkpoint store.
// Each run resumes from the last checkpoint per partition, otherwise
// starts from events enqueued in the last HOUR (configurable).

const { DefaultAzureCredential } = require("@azure/identity");
const { EventHubConsumerClient, earliestEventPosition } = require("@azure/event-hubs");
const { BlobServiceClient } = require("@azure/storage-blob");
const { BlobCheckpointStore } = require("@azure/eventhubs-checkpointstore-blob");

const EH_FQDN = process.env.EVENTHUB_FQDN;              // e.g. "myns.servicebus.windows.net"
const EH_NAME = process.env.EVENTHUB_NAME;              // e.g. "myeventh u b"
const GROUP    = process.env.CONSUMER_GROUP || "$Default";

const BLOB_ACCOUNT_URL = process.env.BLOB_ACCOUNT_URL;  // e.g. "https://mystorage.blob.core.windows.net"
const BLOB_CONTAINER   = process.env.BLOB_CONTAINER || `eh-checkpoints-hourly`;

const MAX_RUN_MS       = Number(process.env.MAX_RUN_MS || 60_000);     // how long to read each hour
const LOOKBACK_MINUTES = Number(process.env.LOOKBACK_MINUTES || 60);   // first run start position

module.exports = async function (context, myTimer) {
  if (!EH_FQDN || !EH_NAME || !BLOB_ACCOUNT_URL) {
    context.log.error("Missing env: EVENTHUB_FQDN, EVENTHUB_NAME, BLOB_ACCOUNT_URL are required.");
    return;
  }

  const credential = new DefaultAzureCredential();

  // Prepare checkpoint store
  const blobSvc = new BlobServiceClient(BLOB_ACCOUNT_URL, credential);
  const container = blobSvc.getContainerClient(BLOB_CONTAINER);
  await container.createIfNotExists();
  const checkpointStore = new BlobCheckpointStore(container);

  // Create consumer client (no connection string; uses AAD)
  const consumer = new EventHubConsumerClient(GROUP, EH_FQDN, EH_NAME, credential, checkpointStore);

  // If no checkpoint exists yet, start from a time window (default: last 60 minutes)
  const fallbackStart = {
    enqueuedOn: new Date(Date.now() - LOOKBACK_MINUTES * 60 * 1000)
  };

  const startOptions = {
    // startPosition is only used for partitions without a checkpoint.
    startPosition: fallbackStart,
    maxBatchSize: 100,            // tune as needed
    maxWaitTimeInSeconds: 5
  };

  context.log(`Starting hourly pull: group=${GROUP}, start=${fallbackStart.enqueuedOn.toISOString()}, window=${MAX_RUN_MS}ms`);

  const subscription = consumer.subscribe(
    {
      processEvents: async (events, ctx) => {
        for (const ev of events) {
          // Your processing here:
          context.log(`[p${ctx.partitionId} seq=${ev.sequenceNumber}]`, safeBody(ev.body));

          // Checkpoint periodically (here: each batch’s last event)
        }
        if (events.length > 0) {
          await ctx.updateCheckpoint(events[events.length - 1]);
        }
      },
      processError: async (err, ctx) => {
        context.log.warn(`Error on partition ${ctx.partitionId}: ${err.message}`);
      }
    },
    startOptions
  );

  // Let it run for MAX_RUN_MS, then stop and exit until next hour
  await delay(MAX_RUN_MS);
  await subscription.close();
  await consumer.close();

  context.log("Hourly pull complete.");
};

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function safeBody(b) {
  try {
    if (Buffer.isBuffer(b)) return b.toString("utf8");
    if (typeof b === "string") return b;
    return JSON.stringify(b);
  } catch {
    return String(b);
  }
}
```

How it works:

* On each hourly invocation:

  * The function subscribes across all partitions.
  * If checkpoints exist, it resumes from there. If not, it starts from events enqueued in the last `LOOKBACK_MINUTES` (default 60).
  * Processes events for `MAX_RUN_MS` (default 60s), checkpoints, then closes and exits.
* Next hour, it picks up from the saved checkpoints.

---

## 4) Local settings (for local test only)

**local.settings.json**

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",  // required placeholder for local run
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "EVENTHUB_FQDN": "myns.servicebus.windows.net",
    "EVENTHUB_NAME": "myeventhub",
    "CONSUMER_GROUP": "$Default",
    "BLOB_ACCOUNT_URL": "https://mystorage.blob.core.windows.net",
    "BLOB_CONTAINER": "eh-checkpoints-hourly",
    "MAX_RUN_MS": "60000",
    "LOOKBACK_MINUTES": "60"
  }
}
```

To run locally:

```bash
func start
```

Sign in for AAD locally (`az login`) or set credentials via environment (service principal) so `DefaultAzureCredential` can authenticate both **Event Hubs** and **Blob Storage**.

---

## 5) Deploy & configure in Azure

```bash
# create resource group, storage, and function app (Consumption, Node)
az group create -n my-func-rg -l westus3
az storage account create -g my-func-rg -n <uniqueStorageName> -l westus3 --sku Standard_LRS
az functionapp create -g my-func-rg -n <uniqueFuncName> \
  --consumption-plan-location westus3 --runtime node --functions-version 4 \
  --storage-account <uniqueStorageName>
```

App settings (at minimum):

```bash
az functionapp config appsettings set -g my-func-rg -n <uniqueFuncName> --settings \
  "EVENTHUB_FQDN=myns.servicebus.windows.net" \
  "EVENTHUB_NAME=myeventhub" \
  "CONSUMER_GROUP=$Default" \
  "BLOB_ACCOUNT_URL=https://mystorage.blob.core.windows.net" \
  "BLOB_CONTAINER=eh-checkpoints-hourly" \
  "MAX_RUN_MS=60000" \
  "LOOKBACK_MINUTES=60"
```

Publish:

```bash
func azure functionapp publish <uniqueFuncName>
```

Grant permissions (AAD) to the function’s identity (Managed Identity or your SPN):

* **Event Hubs data-plane:** `Azure Event Hubs Data Receiver` on the namespace (or hub).
* **Blob Storage:** `Storage Blob Data Contributor` on the storage account.
  (Assign via `az role assignment create …` or Portal.)

---

## Alternative: Event Hubs **Capture** + hourly Timer

If you truly want batch/hour semantics and avoid holding any Event Hubs client, enable **Event Hubs Capture** → ADLS Gen2/Blob (hourly or 5-min windows), then the hourly Timer Function enumerates the new files and processes them. This is often simpler and scales well.






# How to run your Node.js code as an Azure Function (JavaScript)

Below is a practical path to take a plain Node.js file and run it as an Azure Function. I’ll show two common trigger styles:

* **HTTP trigger** (wraps “run some code on request”)
* **Event Hubs trigger** (recommended if your code reads from Event Hubs)

I’ll include local run + CLI deployment steps.

---

## Prereqs

```bash
# Azure CLI + login
az --version
az login

# Azure Functions Core Tools (func) — for local run and publish
# macOS (Homebrew):
brew tap azure/functions
brew install azure-functions-core-tools@4

# Node.js 18+ (Functions v4 supports modern Node; Node 20 recommended going forward)
node -v
```

Docs: local dev with Core Tools, JavaScript guide, runtime versions.
\[learn.microsoft.com › functions-run-local] ([Microsoft Learn][1]) · \[learn.microsoft.com › functions-reference-node] ([Microsoft Learn][2]) · \[learn.microsoft.com › functions-versions] ([Microsoft Learn][3])

---

## Option A — Wrap your script in an **HTTP-trigger** function

### 1) Create a JS Function project and HTTP function

```bash
mkdir my-func && cd my-func
func init . --worker-runtime javascript --model V4
func new --template "HTTP trigger" --name runScript
```

This creates `runScript/index.js` (handler) and `runScript/function.json` (bindings). ([Microsoft Learn][1])

### 2) Drop your existing code into a module and call it

```
# file: lib/myScript.js
module.exports = async function runMyScript(context) {
  // your Node.js code here
  context.log("Hello from my script");
  return { ok: true, when: new Date().toISOString() };
}
```

```
# file: runScript/index.js (HTTP handler)
const runMyScript = require('../lib/myScript');

module.exports = async function (context, req) {
  try {
    const result = await runMyScript(context);
    context.res = { status: 200, jsonBody: result };
  } catch (err) {
    context.log.error(err);
    context.res = { status: 500, body: String(err) };
  }
};
```

### 3) Run locally

```bash
func start
# open the URL shown (GET/POST)
```

---

## Option B — **Event Hubs trigger** (recommended for reading from Event Hubs)

If your script uses `EventHubConsumerClient` to poll, switch to the **Event Hubs trigger**. The Functions runtime will read/scale/partition for you; you just process events.

### 1) Add an Event Hubs–triggered function

```bash
func new --template "EventHub trigger" --name onEvents
```

This generates bindings. Update them if needed.

**onEvents/function.json** (example):

```json
{
  "bindings": [
    {
      "type": "eventHubTrigger",
      "name": "events",
      "direction": "in",
      "eventHubName": "YOUR_EVENT_HUB_NAME",
      "connection": "EVENTHUB_CONNECTION",   // app setting name
      "consumerGroup": "$Default",
      "cardinality": "many"
    }
  ]
}
```

**onEvents/index.js** (process a batch):

```js
module.exports = async function (context, events) {
  for (const ev of events) {
    context.log(`partition:${ev.systemProperties?.["x-opt-partition-id"]} seq:${ev.sequenceNumber}`, ev.body);
  }
};
```

* Put your Event Hub **connection string** (listen) into `local.settings.json` under `Values.EVENTHUB_CONNECTION` for local runs.
* Extension/host settings for Event Hubs bindings live in `host.json` (Functions v4 uses extension bundles; keep the default bundle unless you need to change it). ([Microsoft Learn][4])

Local Event Hubs trigger docs and host.json reference:
\[learn.microsoft.com › functions-bindings-event-hubs-trigger] ([Microsoft Learn][4]) · \[learn.microsoft.com › functions-bindings-event-hubs] ([Microsoft Learn][5])

---

## Deploy to Azure (CLI)

> Creates a resource group, storage account (required by Functions), and a Linux Consumption Function App (Functions v4, Node runtime).

```bash
# Variables
RG=my-func-rg
LOC=westus3
STORAGE=func$RANDOM$RANDOM          # must be globally-unique, lowercase
APP=my-func-app-$RANDOM             # must be globally-unique

# Create resource group + storage
az group create -n $RG -l $LOC
az storage account create -g $RG -n $STORAGE -l $LOC --sku Standard_LRS

# Create the Function App (Linux, Consumption, Node runtime)
az functionapp create \
  -g $RG -n $APP \
  --consumption-plan-location $LOC \
  --runtime node \
  --functions-version 4 \
  --storage-account $STORAGE
```

The CLI supports specifying a Node language version (region/SKU dependent), e.g. `--runtime-version 20` or `18`. Use Node 20+ when possible. ([Microsoft Learn][6], [Azure Docs][7])

### Configure app settings (e.g., Event Hubs connection string)

```bash
# Replace with your Event Hubs connection string (listen)
az functionapp config appsettings set \
  -g $RG -n $APP \
  --settings "EVENTHUB_CONNECTION=Endpoint=sb://<ns>.servicebus.windows.net/...;EntityPath=<hub>"
```

### Publish your code

```bash
# from the project folder (same directory as host.json)
func azure functionapp publish $APP
```

Local + publish references:
\[learn.microsoft.com › functions-run-local] ([Microsoft Learn][1]) · \[learn.microsoft.com › how-to-create-function-azure-cli] ([Microsoft Learn][6])

---

## Notes & good practices

* **Pick the right trigger.** Don’t run a long-lived Event Hubs client inside an HTTP function. Use the **Event Hubs trigger**—it handles partitions, scaling, and checkpointing via the Functions host. ([Microsoft Learn][4])
* **Keep clients static** (top-level) if you use SDK clients in functions to avoid reconnect cost on each invocation. ([Microsoft Learn][2])
* **Node versions.** Azure SDKs are phasing out Node 18 support (Node 20 is current LTS); plan upgrades accordingly. ([GitHub][8])
* **App settings vs local.settings.json.** `local.settings.json` is for local only; use `az functionapp config appsettings set` or Portal for cloud settings. ([Microsoft Learn][1])
* **host.json & extension bundles.** Defaults are fine for most cases; tweak only if you need specific Event Hubs behavior. ([Microsoft Learn][9])

---

## Tiny checklists

**HTTP path**

1. `func init …` → `func new` (HTTP)
2. Call your code from `index.js`
3. `func start` (local)
4. `az functionapp create …` → `func azure functionapp publish`

**Event Hubs path**

1. `func new` (Event Hub trigger)
2. Put connection string into app setting `EVENTHUB_CONNECTION`
3. `func start` (local)
4. Create & publish app; set the same app setting in Azure

If you paste your current Node file (or describe what it does), I can drop it into the right trigger template and hand you a ready-to-publish folder.

[1]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?utm_source=chatgpt.com "Develop Azure Functions locally using Core Tools"
[2]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-node?utm_source=chatgpt.com "Azure Functions Node.js developer guide"
[3]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?utm_source=chatgpt.com "Azure Functions runtime versions overview"
[4]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-event-hubs-trigger?utm_source=chatgpt.com "Azure Event Hubs trigger for Azure Functions"
[5]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-event-hubs?utm_source=chatgpt.com "Azure Event Hubs bindings for Azure Functions"
[6]: https://learn.microsoft.com/en-us/azure/azure-functions/how-to-create-function-azure-cli?utm_source=chatgpt.com "Quickstart: Create a function in Azure from the command line"
[7]: https://docs.azure.cn/en-us/azure-functions/create-first-function-cli-node?utm_source=chatgpt.com "Create a JavaScript function from the command line"
[8]: https://github.com/Azure/azure-sdk-for-js/issues/33017?utm_source=chatgpt.com "end of support for Node.js 18.x in the Azure SDK ..."
[9]: https://learn.microsoft.com/en-us/azure/azure-functions/functions-host-json?utm_source=chatgpt.com "host.json reference for Azure Functions 2.x and later"


# Gemini


## Guide to Deploying and Testing an Azure Function1.

### Prerequisites

Before you can deploy and test your Azure Function, you need to set up your local environment.Node.js:   
Make sure you have Node.js and npm installed. The Azure Functions runtime supports various Node.js versions.  
Azure Functions Core Tools: 
This is a local development kit for Azure Functions. You can install it via npm:n
```
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```
Azure CLI: This command-line tool is used for deploying and managing Azure resources.
```
az login
```
Event Hubs and Storage Account: You'll need an Event Hubs namespace with an Event Hub and a Storage Account for the consumer group and checkpointing.

2. Local Development
   Initialize your Function project: In an empty directory, run the following command to create a new TypeScript project.
```
 func init . --worker-runtime node --language typescript
```

Create the function: Run this command to create a new timer-triggered function.

```
func new --name HourlyEventHubReader --template "Timer trigger"
```

This will create a new folder HourlyEventHubReader with a function.json and index.ts file.

3. Install dependencies: Install the necessary Azure SDK packages.
```
   npm install @azure/event-hubs @azure/eventhubs-checkpointstore-blob @azure/storage-blob
```
Add the code: Replace the content of ```HourlyEventHubReader/index.ts``` with the code provided in the Canvas above.  
Configure local settings: Create a file named ```local.settings.json``` in the root of your project.   
This is where you'll store your connection strings for local testing. 
Do not check this file into source control.

```ini
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=...",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "EventHubsConnection": "Endpoint=sb://...",
    "EventHubName": "your-eventhub-name",
    "ConsumerGroupName": "your-consumer-group-name"
  }
}
```
5. Local Testing

 To test your function locally, run this command from the root of your project:
```  
   func start
```
This will start the Azure Functions host and you can see your function being triggered and processing events in the terminal output.
4. Deployment to AzureCreate a Function App: 
```
Log in to the Azure portal and create a new Function App. 
Choose a Node.js runtime and an appropriate plan (e.g., Consumption Plan).
Deploy from your local machine: Use the Azure CLI to deploy your function. 
Navigate to your project's root directory and run:func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
```

Configure Application Settings:

In the Azure portal, navigate to your Function App and go to Configuration. 

Add the `EventHubsConnection`, `EventHubName`, and `ConsumerGroupName` settings with their respective values.
This is equivalent to ```local.settings.json``` but for the cloud.

5. Monitoring and Testing in AzureView Logs:

In your Function App in the Azure portal, you can use the Log Stream to see the real-time output of your function's ```context.log``` calls.

Run Now: You can manually trigger your timer function in the portal by clicking the Run button to test the event processing without waiting for the next scheduled run.

This guide should help you get your Azure Function up and running smoothly.  

```js
/**
 * This Azure Function is a timer-triggered function that runs hourly.
 * It connects to an Azure Event Hub, reads all events that have
 * appeared since the last run, and processes them.
 *
 * This example uses the @azure/event-hubs SDK directly within the function.
 *
 * For this to work, you need to have the following environment variables
 * configured in your Function App settings:
 * - EventHubsConnection: The connection string for your Event Hubs namespace.
 * - EventHubName: The name of your Event Hub.
 * - ConsumerGroupName: The name of the consumer group to use.
 *
 * You also need a `function.json` file in the same directory as this file
 * to define the trigger. Here is what that file should contain:
 *
 * {
 * "bindings": [
 * {
 * "type": "timerTrigger",
 * "name": "myTimer",
 * "direction": "in",
 * "schedule": "0 0 * * * *"
 * }
 * ],
 * "scriptFile": "../dist/index.js"
 * }
 */

import { AzureFunction, Context } from "@azure/functions";
import { EventHubConsumerClient, earliestEventPosition } from "@azure/event-hubs";
import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";
import { ContainerClient } from "@azure/storage-blob";

// Ensure environment variables are set for the connection.
const eventHubsConnectionString = process.env.EventHubsConnection;
const eventHubName = process.env.EventHubName;
const consumerGroup = process.env.ConsumerGroupName || "$Default";
const storageConnectionString = process.env.AzureWebJobsStorage; // Default storage for Azure Functions

// The timer trigger schedules the function to run once an hour.
const timerTrigger: AzureFunction = async function (context: Context, myTimer: any): Promise<void> {
    context.log("Timer trigger function started.");

    // Simple state management: we will use a blob to store the last processed event's sequence number.
    // This is a manual way to track state since we are not using the native EventHubs Trigger.
    const lastRunBlobClient = new ContainerClient(storageConnectionString, "eventhubcheckpoints").getBlobClient("lastRunPosition.json");

    let lastEventPosition: number | undefined;

    try {
        const downloadResponse = await lastRunBlobClient.downloadToBuffer();
        const content = JSON.parse(downloadResponse.toString());
        lastEventPosition = content.sequenceNumber;
        context.log(`Found last processed sequence number: ${lastEventPosition}`);
    } catch (error) {
        // Blob not found, this is the first run.
        context.log("No last run position found, reading from earliest event position.");
    }
    
    // Create the Event Hubs consumer client.
    // The BlobCheckpointStore is used for managing partitions and state across runs.
    const containerClient = new ContainerClient(storageConnectionString, "eventhubcheckpoints");
    await containerClient.createIfNotExists();
    const checkpointStore = new BlobCheckpointStore(containerClient);
    
    // Create the Event Hubs client with the consumer group and checkpoint store.
    const consumerClient = new EventHubConsumerClient(
        consumerGroup,
        eventHubsConnectionString,
        eventHubName,
        checkpointStore
    );

    try {
        // Get all partitions to read from.
        const partitionIds = await consumerClient.getPartitionIds();
        
        let eventsReadCount = 0;
        
        for (const partitionId of partitionIds) {
            context.log(`Starting to read from partition: ${partitionId}`);
            
            // Define the event position to start reading from.
            const eventPosition = lastEventPosition ? { sequenceNumber: lastEventPosition } : earliestEventPosition;

            // Get a single iterator for all events from the specified position.
            const iterator = consumerClient.get \\* allEvents(eventPosition, { partitionId });
            
            // Loop through the events and process them.
            for await (const eventData of iterator) {
                // IMPORTANT: The iterator will continue indefinitely.
                // In a real-world scenario, you would need to implement a timeout or a stopping condition.
                // For this example, we will just read a fixed number of events to prevent an infinite loop.
                if (eventsReadCount >= 500) {
                    context.log("Reached event read limit. Stopping.");
                    break;
                }
                
                context.log(`Processing event from partition ${eventData.partitionId}:`);
                context.log(`  Sequence Number: ${eventData.sequenceNumber}`);
                context.log(`  Body: ${JSON.stringify(eventData.body)}`);
                eventsReadCount++;
            }
        }
        
        // After processing, save the last processed sequence number for the next run.
        // In a real-world scenario, you would checkpoint each partition's position.
        // This example uses a simplified approach.
        // To do this properly with multiple partitions, you would need to store a map of partition IDs to sequence numbers.
        // For demonstration, we'll just save the highest sequence number found.
        // A more robust solution would be to save the position after each event is successfully processed.
        const lastPosition = {
            sequenceNumber: lastEventPosition, // Simplified for demo
            timestamp: new Date().toISOString()
        };
        await lastRunBlobClient.upload(JSON.stringify(lastPosition), lastPosition.length);
        context.log(`Saved last position for next run.`);

    } catch (error) {
        context.error("Error processing Event Hubs messages:", error);
    } finally {
        // Always close the client to prevent resource leaks.
        await consumerClient.close();
        context.log("Event Hubs client closed.");
    }

    context.log("Timer trigger function finished.");
};

export default timerTrigger;



```
## TypeScript/JavaScript Azure Functions have their own evolution,
but it's somewhat different from Python's V1/V2 progression.

## **JavaScript/TypeScript Azure Functions Structure**

### **Current Recommended: Programming Model v4 (Similar to Python V2)**

```
my-function-app/
├─ package.json                   # Dependencies and scripts
├─ tsconfig.json                  # TypeScript configuration
├─ host.json                      # Function app configuration
├─ local.settings.json           # Local environment variables
├─ src/
│  ├─ functions/                 # All functions (decorator-based)
│  │  ├─ httpTrigger.ts
│  │  ├─ timerTrigger.ts
│  │  └─ restoreTable.ts
│  └─ index.ts                   # App registration
├─ dist/                         # Compiled JavaScript output
└─ .funcignore                   # Files to exclude from deployment
```

### **Example Code Structure:**

#### **src/index.ts** (App Registration)
```typescript
import { app } from '@azure/functions';
import * as httpTrigger from './functions/httpTrigger';
import * as timerTrigger from './functions/timerTrigger';
import * as restoreTable from './functions/restoreTable';

// Functions are automatically registered through decorators
export default app;
```

#### **src/functions/restoreTable.ts** (Individual Function)
```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';

// Decorator-based configuration (like Python V2)
app.http('restoreTable', {
    methods: ['GET', 'POST'],
    authLevel: 'function',
    route: 'restore-table',
    handler: restoreTableHandler
});

export async function restoreTableHandler(
    request: HttpRequest, 
    context: InvocationContext
): Promise<HttpResponseInit> {
    context.log(`Http function processed request for url "${request.url}"`);
    
    const filePath = request.query.get('file_path');
    
    if (!filePath) {
        return {
            status: 400,
            body: 'Missing required parameter: file_path'
        };
    }

    try {
        // Your restore logic here
        const result = await performRestore(filePath);
        
        return {
            status: 200,
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
                status: 'success',
                message: 'Restore completed',
                rows_restored: result.rowCount
            })
        };
    } catch (error) {
        context.log.error('Restore failed:', error);
        return {
            status: 500,
            body: JSON.stringify({
                status: 'error',
                message: error.message
            })
        };
    }
}

async function performRestore(filePath: string) {
    // Implementation details
    return { rowCount: 1000 };
}
```

#### **src/functions/timerTrigger.ts** (Timer Function)
```typescript
import { app, InvocationContext, Timer } from '@azure/functions';

app.timer('backupDaily', {
    schedule: '0 0 2 * * *', // 2 AM daily
    handler: backupDailyHandler
});

export async function backupDailyHandler(
    myTimer: Timer, 
    context: InvocationContext
): Promise<void> {
    context.log('Timer function processed request.');
    
    if (myTimer.isPastDue) {
        context.log('Timer function is running late!');
    }
    
    // Your backup logic here
    await performDailyBackup();
}

async function performDailyBackup() {
    // Implementation
}
```

### **package.json**
```json
{
  "name": "azure-functions-typescript-app",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "watch": "tsc --watch",
    "prestart": "npm run build",
    "start": "func start",
    "test": "echo \"No tests yet...\""
  },
  "dependencies": {
    "@azure/functions": "^4.0.0"
  },
  "devDependencies": {
    "@types/node": "^18.x",
    "typescript": "^4.0.0"
  }
}
```

### **tsconfig.json**
```json
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "es6",
    "outDir": "dist",
    "rootDir": "src",
    "sourceMap": true,
    "strict": false,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true
  }
}
```

## **Legacy Structure: Programming Model v3 (Like Python V1)**

```
my-function-app/
├─ package.json
├─ host.json
├─ local.settings.json
├─ HttpTrigger/                   # One folder per function
│  ├─ index.ts                    # Function implementation  
│  └─ function.json               # Function metadata
├─ TimerTrigger/
│  ├─ index.ts
│  └─ function.json
└─ RestoreTable/
   ├─ index.ts
   └─ function.json
```

### **Legacy Example:**

#### **RestoreTable/function.json**
```json
{
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "res"
    }
  ],
  "scriptFile": "../dist/RestoreTable/index.js"
}
```

#### **RestoreTable/index.ts**
```typescript
import { AzureFunction, Context, HttpRequest } from "@azure/functions"

const httpTrigger: AzureFunction = async function (
    context: Context, 
    req: HttpRequest
): Promise<void> {
    context.log('HTTP trigger function processed a request.');
    
    const filePath = req.query.file_path;
    
    context.res = {
        status: 200,
        body: `Processing file: ${filePath}`
    };
};

export default httpTrigger;
```

## **Comparison: TypeScript vs Python Models**

| Aspect | TypeScript v4 | Python V2 | TypeScript v3 (Legacy) | Python V1 (Legacy) |
|--------|---------------|-----------|----------------------|-------------------|
| **Configuration** | Decorators | Decorators | JSON files | JSON files |
| **Structure** | Centralized functions | Single file | One folder per function | One folder per function |
| **Type Safety** | Full TypeScript | Python hints | Full TypeScript | Python hints |
| **Hot Reload** | ✅ Better | ✅ Good | ❌ Limited | ❌ Limited |
| **Testing** | ✅ Easier | ✅ Easier | ❌ Harder | ❌ Harder |
| **IntelliSense** | ✅ Excellent | ✅ Good | ✅ Good | ❌ Limited |

## **Key Differences from Python:**

### **1. Compilation Step**
- **TypeScript**: Requires `tsc` compilation to JavaScript
- **Python**: Interpreted, no compilation needed

### **2. File Organization**
- **TypeScript v4**: Functions in separate files under `src/functions/`
- **Python V2**: All functions in `function_app.py`

### **3. Import System**
- **TypeScript**: Explicit imports/exports with modules
- **Python**: Single file or module imports

## **Recommendation for TypeScript/JS**

**Use Programming Model v4** (the decorator-based approach) because:

✅ **Better Developer Experience**: Hot reload, better testing  
✅ **Type Safety**: Full TypeScript intellisense and error checking  
✅ **Modern Patterns**: Similar to Express.js, Next.js patterns  
✅ **Easier Testing**: Functions are just TypeScript functions  
✅ **Future-Proof**: Microsoft's recommended approach  

The structure is **conceptually similar to Python V2** (decorators, centralized configuration) but with TypeScript-specific patterns (compilation, module system, separate function files).

So yes, TypeScript v4 is the equivalent of Python V2 - both use decorators and modern, developer-friendly patterns!


## Azure Functions in Python
supports two different project structures, and the choice affects how you organize and deploy your functions.

## 1. **V1 Model - Folder-based Structure (Traditional)**

```
functions-restore-chunk/
├─ host.json                      # Function app configuration
├─ local.settings.json           # Local environment variables
├─ requirements.txt              # Python dependencies
├─ RestoreChunk/                 # Function folder
│  ├─ __init__.py               # Function implementation
│  └─ function.json             # Function metadata (triggers, bindings)
├─ BackupTable/                 # Another function
│  ├─ __init__.py
│  └─ function.json
└─ ListBackups/                 # Third function
   ├─ __init__.py
   └─ function.json
```

### **Characteristics:**
- **One function per folder**
- Each function has its own `function.json` with trigger/binding configuration
- Function code goes in `__init__.py`
- **Declarative configuration** via JSON files

### **Example function.json:**
```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

### **Example __init__.py:**
```python
import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    return func.HttpResponse("Hello World!")
```

## 2. **V2 Model - Flat Structure with Decorators (Modern)**

```
functions-restore-chunk/
├─ host.json                      # Function app configuration  
├─ local.settings.json           # Local environment variables
├─ requirements.txt              # Python dependencies
└─ function_app.py               # All functions in one file
```

### **Characteristics:**
- **All functions in a single Python file** (or split across multiple modules)
- **Decorator-based configuration** - no JSON files needed
- Uses `@app.route()`, `@app.timer_trigger()`, etc.
- More **Pythonic** and similar to Flask/FastAPI

### **Example function_app.py:**
```python
import azure.functions as func

app = func.FunctionApp()

@app.route(route="restore_table", auth_level=func.AuthLevel.FUNCTION)
def restore_table(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Restore function!")

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="myTimer")
def backup_daily(myTimer: func.TimerRequest) -> None:
    logging.info("Timer triggered!")

@app.route(route="list_backups")
def list_backups(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("List backups!")
```

## **Key Differences Summary:**

| Aspect | V1 (Folder-based) | V2 (Flat/Decorator) |
|--------|------------------|---------------------|
| **Structure** | One folder per function | Single file(s) |
| **Configuration** | JSON files (`function.json`) | Python decorators |
| **Deployment** | Multiple folders + JSON | Single Python file |
| **Maintenance** | Scattered across folders | Centralized |
| **Learning Curve** | More Azure-specific | More Python-native |
| **Migration** | Harder to refactor | Easier to reorganize |
| **IDE Support** | Limited IntelliSense | Full Python support |

## **Which Should You Use?**

### **Choose V2 (Flat/Decorator) if:**
- ✅ You prefer Python-native development
- ✅ You want better IDE support and debugging
- ✅ You have multiple related functions (like backup/restore)
- ✅ You want easier testing and local development
- ✅ You're starting a new project

### **Choose V1 (Folder-based) if:**
- ✅ You have existing V1 functions to maintain
- ✅ You need very complex binding configurations
- ✅ Your team is already familiar with V1
- ✅ You're working with legacy Azure Functions tooling

## **Your Current Code Uses V2**

The restore function I provided uses the **V2 decorator model**:

```python
app = func.FunctionApp()

@app.route(route="restore_table", auth_level=func.AuthLevel.FUNCTION, methods=['POST', 'GET'])
def restore_table(req: func.HttpRequest) -> func.HttpResponse:
    # Function implementation
    
@app.route(route="list_backups", auth_level=func.AuthLevel.FUNCTION, methods=['GET'])
def list_backups(req: func.HttpRequest) -> func.HttpResponse:
    # Function implementation
```

This means your project structure should be:

```
your-function-app/
├─ host.json
├─ local.settings.json
├─ requirements.txt
└─ function_app.py              # Contains all your functions
```

## **Migration Note**

If you have existing V1 functions, you can gradually migrate them to V2 by:
1. Moving function logic from `__init__.py` to `function_app.py`
2. Converting `function.json` configurations to decorators
3. Removing the individual function folders

**Microsoft recommends V2 for new projects** as it's more maintainable and provides better developer experience.
