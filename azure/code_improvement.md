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

If you want, I can re-emit your file with items 1–4 folded in (no behavioral changes other than earlier stop when cap reached).
