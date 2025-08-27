### How  to run Azure Function  **once per hour** 
and read from **Azure Event Hubs** using an **Azure Functions (JavaScript)** **Timer Trigger**. The function uses **AAD (DefaultAzureCredential)** and a **Blob checkpoint store** so each hourly run resumes where the last one left off (no reprocessing).

---

## Project layout (Functions v4, JavaScript)

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
