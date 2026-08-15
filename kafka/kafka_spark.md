## Kafka Spark

For **almost real-time ingestion from Kafka into Apache Spark**, 
the standard approach is **Spark Structured Streaming**.

The basic architecture is:

```text
Producers
   |
   v
Kafka topics
   |
   v
Spark Structured Streaming
   |
   +--> transformations / aggregations
   |
   v
Delta / S3 / database / another Kafka topic
```

Spark does not normally process each Kafka message individually the instant it arrives. Instead, Structured Streaming typically uses **micro-batches**. For example, every 1–5 seconds Spark reads all new Kafka records, processes them, and writes the results. For most applications this is considered near-real-time.

A simple PySpark example looks like this:

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder.getOrCreate()

kafka_df = (
    spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka1:9092,kafka2:9092")
        .option("subscribe", "events")
        .option("startingOffsets", "latest")
        .load()
)
```

Kafka returns several columns, including:

```text
key
value
topic
partition
offset
timestamp
```

Both `key` and `value` are binary, so normally you convert `value` to a string and parse it. For JSON events:

```python
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, StringType, LongType

schema = StructType([
    StructField("user_id", StringType()),
    StructField("event_type", StringType()),
    StructField("timestamp", LongType())
])

events = (
    kafka_df
        .selectExpr("CAST(value AS STRING) AS json")
        .select(from_json("json", schema).alias("data"))
        .select("data.*")
)
```

Now `events` behaves almost like a normal Spark DataFrame, except that it continuously receives new rows.

You can transform it:

```python
filtered = events.filter(
    col("event_type") == "purchase"
)
```

and write it continuously. For example, to a Delta table:

```python
query = (
    filtered.writeStream
        .format("delta")
        .outputMode("append")
        .option(
            "checkpointLocation",
            "s3://my-bucket/checkpoints/purchases"
        )
        .trigger(processingTime="5 seconds")
        .start(
            "s3://my-bucket/delta/purchases"
        )
)

query.awaitTermination()
```

The important line for latency is:

```python
.trigger(processingTime="5 seconds")
```

It means roughly:

> Every 5 seconds, check Kafka for new records and process everything that arrived.

You can use:

```python
.trigger(processingTime="1 second")
```

for lower latency, but very small micro-batches can become inefficient because Spark has scheduling overhead. For high-volume data, 2–10 seconds is often a reasonable starting point.

### How Spark knows what was already read

Kafka records have an `(topic, partition, offset)` identity. For example:

```text
topic      partition    offset
events     0            1001
events     0            1002
events     1            875
```

Spark keeps track of the Kafka offsets it has processed.

The critical piece is the checkpoint:

```python
.option("checkpointLocation",
        "s3://my-bucket/checkpoints/events")
```

If the Spark job crashes and restarts, Spark can read its checkpoint and continue roughly from:

```text
partition 0 -> offset 1003
partition 1 -> offset 876
```

instead of starting again from the beginning.

Therefore, **never casually delete the checkpoint of a production stream**.

### Kafka partitions and Spark parallelism

Kafka scalability comes largely from partitions.

Suppose the topic has:

```text
events
  partition 0
  partition 1
  partition 2
  partition 3
  partition 4
  partition 5
```

Spark can process these partitions in parallel:

```text
Kafka                   Spark

partition 0 -------> task
partition 1 -------> task
partition 2 -------> task
partition 3 -------> task
partition 4 -------> task
partition 5 -------> task
```

So if Kafka has only one partition, adding a huge Spark cluster usually won't help Kafka-reading parallelism very much.

### Stateful processing

Structured Streaming becomes especially useful when you need things such as:

```text
Kafka events
     |
     v
Spark
     |
     +-- deduplication
     +-- window aggregation
     +-- joins
     +-- sessionization
     +-- anomaly detection
     |
     v
Delta table
```

For example, count events every minute:

```python
from pyspark.sql.functions import window

counts = (
    events
      .groupBy(
          window(col("event_timestamp"), "1 minute"),
          col("event_type")
      )
      .count()
)
```

For late-arriving events, you normally introduce a **watermark**:

```python
events = events.withWatermark(
    "event_timestamp",
    "10 minutes"
)
```

This tells Spark that events may arrive late, but after a certain point Spark is allowed to discard old streaming state.

### Deduplication

Suppose Kafka occasionally receives the same event twice:

```text
event_id = abc123
event_id = abc123
```

You could do:

```python
deduplicated = (
    events
      .withWatermark("event_timestamp", "10 minutes")
      .dropDuplicates(["event_id"])
)
```

This is important because Kafka/Spark pipelines should generally be designed assuming duplicate delivery is possible somewhere in the overall pipeline.

### If you need UPSERT/MERGE

One common pattern, especially with Databricks, is:

```text
Kafka
   |
Structured Streaming
   |
foreachBatch()
   |
MERGE INTO Delta
```

For example:

```python
from delta.tables import DeltaTable

def upsert_to_delta(batch_df, batch_id):

    target = DeltaTable.forName(
        spark,
        "prod.events"
    )

    (
        target.alias("t")
        .merge(
            batch_df.alias("s"),
            "t.event_id = s.event_id"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )


query = (
    events.writeStream
      .foreachBatch(upsert_to_delta)
      .option(
          "checkpointLocation",
          "s3://bucket/checkpoints/events"
      )
      .trigger(processingTime="5 seconds")
      .start()
)
```

This is a very common production architecture:

```text
Kafka
  |
  | continuously
  v
Spark Structured Streaming
  |
  | 5-second micro batches
  v
foreachBatch
  |
  | MERGE
  v
Delta table
  |
  v
Databricks SQL / BI dashboard
```

If you have a dashboard querying the Delta table through Databricks SQL, the overall latency could therefore be something like:

```text
Kafka arrival                 0 sec
Spark micro-batch             0-5 sec
processing                    1-3 sec
Delta commit                  <1 sec
dashboard query               1-3 sec
-----------------------------------
roughly                       2-12 sec
```

That is **near-real-time**, rather than hard real-time.

The key interview-level distinction is:

**Kafka** provides durable, scalable event transport.

**Spark Structured Streaming** consumes those events and performs distributed transformations.

**Checkpointing + Kafka offsets** provide recovery.

**Micro-batches** give second-level latency.

**Watermarks** deal with late data.

**Delta/DB/Kafka** is typically the downstream sink.

For the kind of Databricks pipelines you have been working with, **Kafka → Spark Structured Streaming → Delta → Databricks SQL dashboard** is a very natural architecture.
