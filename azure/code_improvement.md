Great — thanks for sharing the full file. Your `BlobNotFound (404)` is happening because in `writeToBlob()` you check existence like this:

```js
const fileExists = fileClient.exists(); // <-- missing await
if (!fileExists) { ... } else { ... }
```

`exists()` returns a **Promise**. A Promise is always truthy, so your code always goes into the **else** branch and calls `getProperties()` (or `read()`), which makes a **HEAD** call to the Blob endpoint for a file that doesn’t exist yet → `404 BlobNotFound` (exactly what you saw in the log).

There are a few more small issues in that block (undefined variables, gz append path). Below is a **drop-in fix** for `writeToBlob()` that:

* awaits `exists()` correctly
* creates the ADLS **directory** (real dirs on DFS) and **file** when missing
* appends to existing **.jsonl** files safely
* avoids appending to **.gz** (creates a new unique file instead)
* removes undefined vars (`newContent`, `eventType`) and sets metadata with strings

> Also fix your config flag:
> `includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "false"` ➜ **should be**
> `includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "true"`

---

### Replace your `writeToBlob()` with this

```js
async writeToBlob(data, batchId, context) {
  const now = new Date();
  const year  = now.getUTCFullYear();
  const month = String(now.getUTCMonth() + 1).padStart(2, '0');
  const day   = String(now.getUTCDate()).padStart(2, '0');
  const hour  = String(now.getUTCHours()).padStart(2, '0');

  const groupedEvents = this.groupEventsByCollection(data);
  const uploadedFiles = [];

  for (const [dbcollection, events] of Object.entries(groupedEvents)) {
    const folderPath = `${year}/${month}/${day}/${hour}`;
    await this.ensureDirectoryExists(folderPath); // DFS needs real dirs

    // Build base filename
    const gzip = !!config.processing.compressionEnabled;
    const base = config.processing.includeBatchIdInFilename
      ? `${dbcollection}-${batchId}`
      : `${dbcollection}`;
    const ext = gzip ? `.jsonl.gz` : `.jsonl`;

    let fileName = `${base}${ext}`;
    let fullPath = `${folderPath}/${fileName}`;

    // Serialize JSONL
    const jsonl = events.map(rec => JSON.stringify(rec)).join('\n') + '\n';
    let contentBuf = Buffer.from(jsonl, 'utf8');
    if (gzip) {
      contentBuf = zlib.gzipSync(contentBuf);
    }

    // Get a file client for target path
    let fileClient = this.fileSystemClient.getFileClient(fullPath);

    // Avoid appending to .gz — create a unique new file if it already exists
    if (gzip && await fileClient.exists()) {
      const ts = now.toISOString().replace(/[:.]/g, '-');
      fileName = `${base}-${ts}${ext}`;
      fullPath = `${folderPath}/${fileName}`;
      fileClient = this.fileSystemClient.getFileClient(fullPath);
    }

    // Create if missing, else append to end (jsonl only)
    if (!(await fileClient.exists())) {
      await fileClient.create();
      await fileClient.append(contentBuf, 0, contentBuf.length);
      await fileClient.flush(contentBuf.length);
    } else {
      // appending only supported here for non-gz
      const props = await fileClient.getProperties();  // SAFE now, it exists
      const currentSize = Number(props.contentLength) || 0;
      await fileClient.append(contentBuf, currentSize, contentBuf.length);
      await fileClient.flush(currentSize + contentBuf.length);
    }

    // Optional HTTP headers (content type)
    // await fileClient.setHttpHeaders({ contentType: gzip ? "application/gzip" : "application/x-ndjson" });

    // Metadata values must be strings
    const eventType = this.getEventType(events[0]) || 'unknown_event';
    await fileClient.setMetadata({
      batchId,
      recordCount: String(events.length),
      processedAt: now.toISOString(),
      eventType,
      compressed: String(gzip),
      originalSize: String(jsonl.length),
      storedSize: String(contentBuf.length)
    });

    uploadedFiles.push(fullPath);
    context.log.info(`Uploaded ${events.length} records to ${fullPath} (${contentBuf.length} bytes)`);
  }

  return uploadedFiles;
}
```

---

### What else I fixed / tidied

* **`await fileClient.exists()`** — the root cause of your 404.
* **Append vs gzip:** appending to `.gz` requires decompress/recompress; instead I create a unique file (timestamp). Keeps it simple and fast.
* **Undefined variables:** removed `newContent` and added a proper `eventType` via your `getEventType()` helper.
* **Metadata strings:** all values must be strings; I wrapped numbers/booleans.
* **Trailing newline:** added `+'\n'` when building JSONL (many tools expect newline-terminated lines).
* **Directory creation:** your `ensureDirectoryExists()` is fine; this uses it once per collection.

---

### Two more small nits you may want to adjust

1. **Config flag** (mentioned above):

```js
// before (wrong)
includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "false",
// after (right)
includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "true",
```

2. **Starting position** for reads
   You use `latestEventPosition`, which only captures **new** events during your wait window. If you expected historical/replay, use a timestamp:

```js
startPosition: { enqueuedOn: new Date(Date.now() - 10 * 60 * 1000) } // last 10 minutes
// or: earliestEventPosition
```


GEMINI:

Thanks for sharing the updated file — you’ve got the structure in a great place: EventHubConsumerClient + BlobCheckpointStore (in its own container) + ADLS writes. I reviewed the code and found a few correctness & robustness tweaks that will save you pain in production.&#x20;

Below are “surgical” patches you can drop in.

---

# 1) Always close the subscription (no leaks)

Right now, the subscription is closed only by the timeout path. If an error triggers early `reject`, the subscription can stay open. Add a small helper and use it in *all* exit paths.

```js
// inside readEventsFromHub, right after let subscription = null;
const closeSub = async () => {
  if (subscription && !subscription.isClosed) {
    try { await subscription.close(); }
    catch (e) { context.log.warn(`Warning closing subscription: ${e.message}`); }
  }
};
```

Use it everywhere you resolve/reject:

```js
const resolveWithEvents = async () => {
  if (isResolved) return;
  isResolved = true;
  await closeSub();                                  // ← ensure closed before resolving
  allEvents.sort((a, b) => new Date(a.enqueuedTimeUtc) - new Date(b.enqueuedTimeUtc));
  context.log.info(`Event Hub reading completed: ${allEvents.length} events from ${processedPartitions.size} partitions`);
  resolve(allEvents);
};

// in processError (fatal branch)
if (!isResolved) {
  isResolved = true;
  await closeSub();                                  // ← close then reject
  return reject(err);
}

// in setTimeout handler
setTimeout(() => {
  if (!isResolved) {
    closeSub().then(resolveWithEvents).catch(() => resolveWithEvents());
  }
}, config.processing.maxWaitTimeSeconds * 1000);
```

---

# 2) Parse Buffer bodies too (not just strings)

Event Hubs often delivers `Uint8Array`/Buffer. Add a tiny helper and use it in `transformEvents`.

```js
function parseEventBody(body) {
  if (body == null) return body;
  if (Buffer.isBuffer(body) || body instanceof Uint8Array) {
    const text = Buffer.from(body).toString('utf8');
    try { return JSON.parse(text); } catch { return text; }
  }
  if (typeof body === 'string') {
    try { return JSON.parse(body); } catch { return body; }
  }
  return body; // already an object/number/etc.
}
```

```js
// in transformEvents
let telemetryEvent = parseEventBody(event.body);
```

---

# 3) Support `basePath` when building folders

You defined `config.blobStorage.basePath` but didn’t use it. Normalize it and prepend.

```js
// near top-level (helper)
const normalizeBase = (p) => (p || '').replace(/^\/+|\/+$/g, '');

// in writeToBlob
const base = normalizeBase(config.blobStorage.basePath);
const folderPath = base
  ? `${base}/${year}/${month}/${day}/${hour}`
  : `${year}/${month}/${day}/${hour}`;

await this.ensureDirectoryExists(folderPath);
```

This way your final paths look like:
`<basePath>/YYYY/MM/DD/HH/<file>.jsonl[.gz]`

---

# 4) Don’t append to .gz (use a new file instead)

`DataLakeFileClient.read()` returns a stream; decompress/append/recompress is slow and tricky. Easiest/fastest: if compression is on **and** a file already exists, write to a new timestamped file. Keep append behavior only for `.jsonl`.

```js
// in writeToBlob, right before checking exists()
const gzip = !!config.processing.compressionEnabled;
const baseName = config.processing.includeBatchIdInFilename ? `${eventType}-${batchId}` : eventType;
const ext = gzip ? `.jsonl.gz` : `.jsonl`;
let fileName = `${baseName}${ext}`;
let fullPath = `${folderPath}/${fileName}`;
let fileClient = this.fileSystemClient.getFileClient(fullPath);

// serialize content
const jsonl = events.map(r => JSON.stringify(r)).join('\n') + '\n';
let content = Buffer.from(jsonl, 'utf8');
if (gzip) content = zlib.gzipSync(content);

// If gzip + exists → create a unique new file instead of append
if (gzip && await fileClient.exists()) {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  fileName = `${baseName}-${ts}${ext}`;
  fullPath = `${folderPath}/${fileName}`;
  fileClient = this.fileSystemClient.getFileClient(fullPath);
}

if (!(await fileClient.exists())) {
  await fileClient.create();
  await fileClient.append(content, 0, content.length);
  await fileClient.flush(content.length);
} else {
  const props = await fileClient.getProperties();
  const currentSize = Number(props.contentLength) || 0;
  await fileClient.append(content, currentSize, content.length);
  await fileClient.flush(currentSize + content.length);
}

// (optional) set content-type header (helpful downstream)
await fileClient.setHttpHeaders({ contentType: gzip ? "application/gzip" : "application/x-ndjson" });

// metadata: keys are stored lowercased by service; values must be strings
await fileClient.setMetadata({
  batchid: batchId,
  recordcount: String(events.length),
  processedat: now.toISOString(),
  eventtype: eventType,
  compressionenabled: String(gzip),
  originalsize: String(jsonl.length),
  storedsize: String(content.length)
});
```

> You mentioned the “metadata key fix” — the service normalizes keys to lowercase. I recommend sending lowercase (as above) for consistency.

---

# 5) Flip this config flag

You still have:

```js
includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "false",
```

Make it truthy when the env var is `"true"`:

```js
includeBatchIdInFilename: process.env.INCLUDE_BATCH_ID === "true",
```

---

# 6) Minor nits

* You store `partitionContext` inside **each event object** (it’s heavy and unused later). You already keep the most recent event per partition in `this.processedEvents`; consider removing `partitionContext` from each `allEvents.push({...})` to reduce memory pressure on large batches.
* `contentType` variable in `writeToBlob` is assigned but not used — remove it (or set via `setHttpHeaders`, as shown).
* `startTime` in `readEventsFromHub` is unused — remove it.

---

# 7) Checkpointing approach

👍 Using `BlobCheckpointStore` + `partitionContext.updateCheckpoint()` is the recommended path. Your `Promise.allSettled` pattern is good — one failed partition won’t block the others. Since you now checkpoint **every** successful batch, you’ll minimize reprocessing on restarts.

---

## Quick test checklist

1. **Dry run** with no events: should initialize storage, then “No events to process” and exit cleanly.
2. **Burst of events:** verify multiple grouped files appear under `basePath/YYYY/MM/DD/HH/…` and that `.gz` behavior creates a new file per batch when the name already exists.
3. **Resume from checkpoint:** send events, run once, stop; send more events; start again — should pick up from the last checkpoint per-partition.
4. **Multi-partition:** confirm `updateCheckpoints` logs show each partition’s offset/sequenceNumber advancing.

---

### Claude

Looking at your latest version, you've made some solid improvements, but I notice a critical issue with the checkpoint logic that could cause data loss. Let me review the key changes and provide feedback:

## Your Improvements:

1. **Better error handling structure** - The `EventHubErrorHandler` now returns clearer outcome objects
2. **Improved event body parsing** - The `parseEventBody` function handles different data types robustly
3. **Cleaner code organization** - Better variable naming and structure
4. **Resource management** - Added `isClosed` check before closing subscription
5. **Content-Type headers** - Added proper HTTP headers for the uploaded files

## Critical Issue Found:

There's a significant problem in your `readEventsFromHub` method that could cause data loss:

```javascript
// This is problematic:
allEvents.push({
  partitionId,
  offset: ev.offset,
  // ... other fields
  // Missing: partitionContext reference
});

// But you track for checkpointing separately:
this.processedEvents.set(partitionId, { event: ev, partitionContext });
```

**The Problem**: The events in `allEvents` don't have partition context references, but your checkpointing logic depends on the partition context being available. If there's an error during processing, you might checkpoint events that weren't actually processed successfully.

## Recommended Fix:## Key Improvements in My Final Version:

### 1. **Safe Checkpoint Logic**
- Renamed `processedEvents` to `successfullyProcessedEvents` for clarity
- Added `markEventsAsProcessed()` method that only marks events as ready for checkpointing AFTER successful storage
- Events are only checkpointed after they're confirmed written to ADLS Gen2

### 2. **Data Integrity Protection**
- Preserve `_partitionContext` and `_originalEvent` through the processing pipeline
- Clean these internal fields before serializing to storage
- Clear processed events on any error to prevent partial checkpointing

### 3. **Better Error Recovery**
- Clear `successfullyProcessedEvents` on batch failure to prevent inconsistent state
- More detailed checkpoint operation reporting

### 4. **Resource Management**
- Improved subscription cleanup with proper error handling
- Better timeout messaging

## Critical Benefits:

1. **No Data Loss**: Events are only checkpointed after successful storage
2. **No Duplicate Processing**: Proper checkpoint management prevents reprocessing
3. **Crash Recovery**: Consumer restarts from last successfully processed position
4. **Partition Independence**: Each partition's checkpoint is managed separately

## Testing Recommendations:

1. **Test checkpoint recovery**: Stop the process mid-batch and restart to verify it resumes correctly
2. **Test with failures**: Introduce storage failures to ensure events aren't checkpointed until successfully stored
3. **Monitor checkpoint container**: Verify checkpoints are being created in blob storage

Your code was quite close! The main issue was the timing of when events get marked for checkpointing. The fixed version ensures data integrity by only checkpointing events that have been successfully processed and stored.



chatgpt

Thanks for the upload — I read your new `telemetry-reader.js`. The changes you described are there and they’re solid: you now (a) use a real **BlobCheckpointStore**; (b) carry `_partitionContext`/`_originalEvent` through the pipeline, only **marking** events after a successful ADLS write; (c) checkpoint via `Promise.allSettled`; (d) normalize/use `basePath`; (e) set proper `Content-Type`; and (f) cleanly close the subscription. Nice work.&#x20;

Here are a few **surgical fixes/cleanups** I recommend:

1. ### Simplify/strengthen checkpoint aggregation

Right now each per-partition `updateCheckpoint()` has its own `.catch(...)` **and** you also use `allSettled`. That means every promise ends up *fulfilled* (because of the catch), so `allSettled` doesn’t buy you signal. Either approach is fine; the simplest is to **remove the inner `.catch`** and rely on `allSettled`:

```js
// build ops without .catch
const ops = [];
for (const [pid, info] of this.successfullyProcessedEvents.entries()) {
  ops.push(info.partitionContext.updateCheckpoint(info.event).then(() => ({ pid, ok: true })));
}

// evaluate results and log
const results = await Promise.allSettled(ops);
const ok = results.filter(r => r.status === 'fulfilled').length;
const failed = results.length - ok;
context.log.info(`Checkpoint operations: ${ok}/${results.length} succeeded`);
if (failed) {
  results.forEach((r, i) => {
    if (r.status === 'rejected') context.log.error(`Checkpoint failed [${i}]: ${r.reason?.message || r.reason}`);
  });
}
this.successfullyProcessedEvents.clear();
```

2. ### Remove an unused variable

You create `partitionContextMap` in `readEventsFromHub` but never use it. Safe to delete.

3. ### (Optional) honor a global cap and end early

You timebox reads (good), but if you want to **hard-cap** total events per run, stop as soon as you reach the target:

```js
const MAX_TOTAL = config.processing.maxBatchSize;
if (allEvents.length >= MAX_TOTAL) {
  context.log.info(`Reached cap of ${MAX_TOTAL} events; closing subscription early`);
  await closeSub();
  return resolveWithEvents();
}
```

(Place that right after you push into `allEvents` in `processEvents`.)

4. ### Avoid repeated directory checks

You call `ensureDirectoryExists(baseFolder)` inside the loop over event groups. Move it **before** the loop:

```js
await this.ensureDirectoryExists(baseFolder);
for (const [eventType, events] of Object.entries(groups)) {
  // ...
}
```

5. ### Grouping fallback

If some events don’t have `raw_event.event`, consider a fallback (e.g., `"unknown"` is fine) or use a different discriminator if your payloads provide one (e.g., `telemetryEvent.type`).

6. ### Tiny polish

* Your `parseEventBody` covers Buffer/Uint8Array/string/object well — keep it.
* Metadata keys are lowercased and values are strings — perfect for ADLS.
* You’re cleaning `_partitionContext`/`_originalEvent` before serializing — exactly right.

---
### Claude

I've reviewed your modified EventHub processor code, and overall it looks well-structured with good improvements. Here's my feedback:

## Positive Changes

**1. Simplified Checkpoint Handling**: The `Promise.allSettled` approach is much cleaner and provides better visibility into which checkpoints succeed/fail.

**2. Hard Cap Implementation**: The early subscription closure when reaching `maxBatchSize` is a good safeguard against runaway processing.

**3. Directory Optimization**: Moving `ensureDirectoryExists` outside the loop is efficient - no need to check/create the same directory multiple times.

**4. Clean State Management**: Removing the unused `partitionContextMap` simplifies the code.

## Areas for Improvement

**1. Error Handling Gap**
```javascript
// In processEvents() catch block:
this.successfullyProcessedEvents.clear();
```
This clears ALL processed events on any failure, even if some files were successfully written. Consider only clearing events that actually failed to persist.

**2. Potential Race Condition**
The subscription might continue processing events after you call `closeSub()` but before it actually closes. Consider adding a flag:
```javascript
let shouldStop = false;
// Set shouldStop = true before closeSub()
// Check shouldStop in processEvents callback
```

**3. Memory Efficiency**
With a 1000 event cap, you're loading everything into memory. For larger batches, consider streaming or batching the writes.

**4. Checkpoint Timing**
You checkpoint after every successful batch, but what if the function times out? Consider periodic checkpointing for long-running batches.

**5. Metadata Enhancement**
Consider adding more context to file metadata:
```javascript
await file.setMetadata({
  // ... existing metadata
  functionexecutionid: context.executionContext?.invocationId,
  partitionids: JSON.stringify([...new Set(records.map(r => r.event_hub_metadata?.partition_id))]),
});
```

## Minor Suggestions

- Consider making the early closure threshold configurable (maybe 90% of maxBatchSize)
- Add retry logic for the `ensureDirectoryExists` call
- Log partition distribution in the final summary

The code is production-ready as-is, but these improvements would make it more robust for high-volume scenarios. The core logic is sound and your error handling approach is much improved!





I've created an enhanced version of your EventHub processor with all the improvements I suggested. Here are the key enhancements:

## Major Improvements

**1. Smart Error Handling**
- Added `markEventsAsFailed()` to track events that couldn't be persisted
- Only successful events are eligible for checkpointing
- Failed events are excluded from checkpoint operations
- Granular error tracking per event instead of clearing everything on batch failure

**2. Race Condition Protection**
- Added `shouldStop` flag to prevent processing after shutdown begins
- Proper cleanup of periodic timers
- Enhanced subscription closure with better logging

**3. Memory & Performance Optimizations**
- Early cutoff threshold (configurable, defaults to 90% of max batch size)
- Separated upload logic into `uploadEventTypeGroup()` for better error isolation
- Each event type group fails independently - one bad group doesn't kill the whole batch

**4. Periodic Checkpointing**
- Configurable interval-based checkpointing for long-running batches
- Prevents data loss if the function times out
- Automatic cleanup of checkpoint timers

**5. Enhanced Metadata & Monitoring**
- Execution ID tracking in file metadata
- Partition distribution logging with `getPartitionStats()`
- Processor version in metadata for easier debugging
- Health status method for monitoring
- Better structured logging throughout

**6. Robust Retry Logic**
- Exponential backoff for failed operations
- Configurable retry attempts and delays
- Retry wrapper for critical initialization operations

**7. Improved Resource Management**
- Proper cleanup in `close()` method with final checkpointing
- Better error handling in cleanup operations
- Clear separation between successful and failed event tracking

## New Configuration Options

- `EARLY_CUTOFF_THRESHOLD`: When to start graceful shutdown (default: 0.9)
- `CHECKPOINT_INTERVAL_MS`: Periodic checkpoint frequency (default: 10000ms)
- `MAX_RETRIES`: Number of retry attempts (default: 3)
- `RETRY_DELAY_MS`: Base retry delay with exponential backoff (default: 1000ms)

The code maintains backward compatibility while adding significant robustness for production workloads. It's now much better equipped to handle partial failures, network issues, and long-running processing scenarios.


### ChatGPT

Awesome progress — this version looks solid and folds in the safety + durability ideas you wanted. Here’s a quick punch-list review with targeted nits/fixes so you can ship it confidently.

# What’s great (and where it lives)

* **Safe checkpointing only after writes succeed.** You now track successes via `markEventsAsProcessed()` and exclude failures with `markEventsAsFailed()`. `updateCheckpoints()` then uses only the success map – exactly what we want for correctness. &#x20;
* **Internal context preserved → stripped at write.** Events carry `_partitionContext` and `_originalEvent` through transform, then you remove them in `uploadEventTypeGroup()` before persisting. &#x20;
* **Periodic checkpointing + timers cleaned up.** `periodicCheckpointInterval` is configurable and you start/clear timers in the subscription lifecycle. &#x20;
* **Early cutoff to avoid running out the clock.** You’re honoring `earlyCutoffThreshold` to stop collecting near the cap and move to persistence.&#x20;
* **Robust body parsing + clearer error semantics.** `parseEventBody()` is defensive (buffers/strings/objects), and `EventHubErrorHandler` returns explicit outcomes (`fatal`, `retryable`). &#x20;
* **Per-type grouped writes with clean metadata & headers.** Writes set `contentType`, add execution/batch/partition metadata, and avoid gzip append by creating timestamped files. &#x20;
* **Exponential backoff wrapper for critical ops.** Nice touch with `retryOperation()`.&#x20;
* **Base path support.** Folder path prepends `ADLS_BASE_PATH` cleanly.&#x20;

# Recommended touch-ups

1. **Import `earliestEventPosition` if you start from the beginning**
   You reference `startFromBeginning ? earliestEventPosition : latestEventPosition` in the reader; ensure you import `earliestEventPosition` from `@azure/event-hubs` alongside `latestEventPosition`. (I don’t see the import in this file snippet.)
   *Fix:*

```js
const { EventHubConsumerClient, latestEventPosition, earliestEventPosition } = require("@azure/event-hubs");
```

(If it’s already there higher up, you’re good.)&#x20;

2. **Timer lifecycle (periodic checkpoint) — make sure it can’t run after shutdown**
   You already start/clear timers around the subscription; double-check you also clear on any early exit path (error/early cutoff) to avoid a late `updateCheckpoints()` running against a disposed client. From your code, you’re calling `clearInterval` when resolving and in `finally`, which is good; just keep that pattern wherever you may resolve early.&#x20;

3. **`Promise.allSettled` style simplification (optional)**
   In `updateCheckpoints()` you build an array of ops that already `.then/.catch()` and then still call `allSettled`. You can simplify to either:

* keep `.then/.catch()` and use `Promise.all`, or
* push **raw** `updateCheckpoint` promises and use `allSettled` to inspect results.
  Current approach is correct but slightly redundant.&#x20;

4. **Consistent env keys in docs vs code**
   Your config reads `CHECKPOINT_INTERVAL_MS`, `MAX_RETRIES`, `RETRY_DELAY_MS`, and `EARLY_CUTOFF_THRESHOLD`. Make sure your deployment environment uses those exact names (and that any README matches them) so the defaults aren’t silently used.&#x20;

5. **Gzip append policy**
   You’ve chosen a smart route: never append to `.gz` (create a timestamped file instead). For transparency in downstream jobs, consider putting a brief note in metadata (e.g., `append_policy: "new_file_on_gzip"`). Not required, just nice-to-have.&#x20;

6. **Partition stats & health**
   You log partition distribution; if you expose `getHealthStatus()` externally (you mentioned it in your notes), ensure it returns a small struct (last batch id, files written, partitions seen, timeouts, etc.) for dashboards. I don’t see `getHealthStatus()` in the uploaded file yet.

# Tiny correctness checks to keep in mind

* You *do* carry `_partitionContext` with each event and only checkpoint after ADLS success — that addresses the earlier “data loss” concern. &#x20;
* You strip the internal fields before serializing (good).&#x20;
* Base folder creation is retry-wrapped (good) and uses the normalized base path.&#x20;

If you want, I can emit a single, clean file that incorporates the small tweaks above (import + simplified `allSettled` path + optional metadata flag). Otherwise, from a durability perspective you’re in great shape.

