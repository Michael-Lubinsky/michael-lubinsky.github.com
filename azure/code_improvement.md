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

If you want, I can fold the patches above directly into your file and give you the full merged version. Otherwise, drop these in and ping me with any new errors or logs; I’ll iterate quickly.


