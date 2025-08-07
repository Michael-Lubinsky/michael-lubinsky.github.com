There is is MongoDB with many collections. Collections may be updated often.
Please explain how to use Azure Data Factory to run periodic job to serialize collections to ADLS Gen2.
Is it recommended to use MongoDB change Stream for it?
How to layout the folders in ADLS Gen2?

MongoDB → ADF (Pipeline) → ADLS Gen2 (Parquet/JSON layout) → [Optional: Snowflake or Synapse for analytics]

## ✅ Architecture Overview

```
MongoDB → ADF (Pipeline) → ADLS Gen2 (Parquet/JSON layout) → [Optional: Snowflake or Synapse for analytics]
```

---

## 🔁 Option 1: Periodic Full Extract (recommended for small/moderate collections)

### 🔧 Steps:
1. **Create a Linked Service** to MongoDB in ADF using the **MongoDB Atlas connector** or via **Self-hosted Integration Runtime** (if on-prem).
2. **Create a Dataset** for each MongoDB collection.
3. **Build a Pipeline** with:
   - **Copy Activity**: from MongoDB to ADLS Gen2.
   - Set **source query** if you want incremental behavior using a `lastModified` timestamp field.
4. **Configure Schedule Trigger**: run every 5m / 1h / daily, depending on freshness needs.
5. **Store in ADLS Gen2**: use Parquet or JSON format.



In the context of MongoDB → ADLS Gen2 via Azure Data Factory,  
here's how you can generally classify small to moderate collections:


| Category     | Document Count    | Data Volume per Collection | Recommended ADF Mode                     |
| ------------ | ----------------- | -------------------------- | ---------------------------------------- |
| **Small**    | < 1 million docs  | < 1 GB                     | Periodic full extract ✅                  |
| **Moderate** | 1–10 million docs | 1–10 GB                    | Periodic full extract ✅                  |
| **Large**    | > 10 million docs | > 10 GB                    | Change streams or incremental extract ⚠️ |

Considerations Beyond Size
1. Change Frequency
If a collection updates very frequently (e.g., > 5% of docs/hour), full extract might cause high I/O or outdated snapshots.

2. Index Availability
If collections have an indexed updated_at or _id field, you can use incremental extract even for moderate/large datasets.

3. Network & Runtime Limits
ADF copy activities may timeout or throttle if transferring multi-GB unindexed documents frequently.

4. Downstream Consumers
If consumers (e.g., Snowflake, Synapse) are only interested in deltas or aggregates, a full extract wastes resources.


Periodic Full Extract is fine if:

- Collection is < 10 GB
- Extract takes < 15 minutes per collection
- Changes are not extremely frequent
- Otherwise, use Change Streams or incremental lastModified-based sync


---

## ⚙️ Option 2: Incremental Loads Using Change Streams (for real-time/delta sync)

### ✅ When to use Change Streams:
Use **MongoDB Change Streams** **only if**:
- You need **near-real-time** updates.
- Your MongoDB version supports replica sets and change streams.
- You need to track inserts, updates, and deletes incrementally.

### 🔧 How:
ADF **does not natively support Change Streams**, so you would:

1. Build a **custom app** (Python, Node.js, etc.) that:
   - Subscribes to MongoDB change streams.
   - Writes the change events to **ADLS Gen2** or to a queue (e.g., Azure Event Hub or Kafka).
2. Use **ADF or Azure Data Explorer** to batch process those events from ADLS or the queue.

> ⚠️ Change Streams are powerful but add operational complexity. Prefer periodic batch if the freshness requirement allows.

---

## 📁 Folder Layout in ADLS Gen2

To ensure clarity, traceability, and partitioning for downstream use, follow this layout:

```
/mongo_export/
  └── <collection_name>/
        └── year=<yyyy>/
              └── month=<mm>/
                    └── day=<dd>/
                          └── hour=<hh>/ (optional if high-frequency)
                            └── export_<timestamp>.parquet
```

### 🔁 Example:
```
/mongo_export/users/year=2025/month=08/day=06/users_20250806T140000.parquet
/mongo_export/orders/year=2025/month=08/day=06/orders_20250806T140000.parquet
```

This structure:
- Supports **partition pruning**.
- Keeps historical snapshots for **auditing/versioning**.
- Scales well for downstream **Spark/Snowflake/Synapse** queries.

---

## ✅ Summary

| Feature | Periodic Copy | Change Streams |
|--------|----------------|----------------|
| **Ease of setup** | ✅ Very easy (ADF GUI) | ❌ Custom coding required |
| **Latency** | ❌ Depends on schedule (e.g., hourly) | ✅ Near real-time |
| **Scalability** | ✅ Scales with partitions | ⚠️ Need to manage scaling manually |
| **Best for** | Snapshots, audit, historical loads | Real-time sync, low-latency apps |

---

Let me know if you want the full ADF JSON pipeline template or the Python code to stream from MongoDB.
