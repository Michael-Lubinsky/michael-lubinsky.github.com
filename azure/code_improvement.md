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


