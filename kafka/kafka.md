pip install confluent-kafka

<!-- https://medium.com/@yunusgurguz11/building-a-real-time-flight-data-pipeline-with-kafka-spark-and-airflow-a657d4e2e3de -->

#### Kafka Producer:
Example 1
```python
from confluent_kafka import Producer
import json

producer = Producer({'bootstrap.servers': 'localhost:9092'})

record_key = "user123"
record_value = json.dumps({
    "timestamp": "2025-04-30T14:35:00Z",
    "url": "https://example.com/page",
    "device_id": "dev456"
})

producer.produce(
    topic="clickstream",
    key=record_key,
    value=record_value.encode("utf-8"),
    headers={"source": "web"}
)
producer.flush()

```
Example 2: with callback (recommended)
```python
from confluent_kafka import Producer

conf = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

producer.produce("clickstream", key="user1", value="page1", callback=delivery_report)
producer.flush()
```
#### Kafka Consumer
```python
from confluent_kafka import Consumer

conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'clickstream-group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)
consumer.subscribe(['clickstream'])

while True:
    msg = consumer.poll(1.0)  # If no messages are available after 1 second → returns None.
    if msg is None:
        continue
    if msg.error():
        print(f"Error: {msg.error()}")
        continue
    print(f"Received: {msg.key()} - {msg.value().decode('utf-8')}")

```


<https://kafka-python.readthedocs.io/en/master/>
#### Kafka Producer:
```python

from kafka import KafkaProducer
import json
from time import sleep
from json import dumps
kafka_servers = ["localhost:9092"]
try:
    topic_name = 'incremental_updates'
    myproducer = KafkaProducer(bootstrap_servers=kafka_servers, value_serializer=lambda x: dumps(x).encode('utf-8'))
    #open file , read and send the data
    f = open("test_file.csv", 'r')
    for msg in f:
    #for e in range(100):
        csv_data = msg
        print(csv_data)
        #data = {'data' : csv_data}
        #myproducer.send('incremental_updates_test', value=data)
        # sleep(300)
        #myproducer.flush()
        future = myproducer.send('incremental_updates_test',value=csv_data)
        # Block for 'synchronous' sends
        try:
            record_metadata = future.get(timeout=10)
        except KafkaError as e:
            # Decide what to do if produce request failed...
            print("kafka producer exception occured\n")
            print(e)
            log.exception()
            pass
# Successful result returns assigned partition and offset
        # print (record_metadata.topic)
        # print (record_metadata.partition)
        # print (record_metadata.offset)
print("total msg sent")
except Exception as e:
    print("kafka producer exception . occured outside\n")
    print(e)
```
#### Kafka Cconsumer:
```python
import kafka
from kafka import KafkaConsumer
from json import loads
# Import sys module
import sys
try:
    # Define server with port
    kafka_servers = ["localhost:9092"]
    # Define topic name from where the message will recieve
    #topicName = 'incremental_updates'
    # Initialize consumer variable
    consumer = KafkaConsumer('incremental_updates_test' ,bootstrap_servers = kafka_servers, enable_auto_commit=True,
                                group_id='my-group1-amit', value_deserializer=lambda x: loads(x.decode('utf-8')))
    #consumer.topics()
    print("list kafka topics")
    #list all the topic_list
    admin_client = kafka.KafkaAdminClient(bootstrap_servers=kafka_servers)
    print(admin_client.list_topics())
    #print(admin_client.describe_topics())

    # Read and print message from consumer
    for msg in consumer:
        #print(msg.value)
        #print("recving data")
        recv_data = msg.value
        #r = recv_data.replace('"', '')
        #record = recv_data.strip('\\n')
        print(recv_data)
except Exception as e:
    print("exception occured in kafka consumer")
    print(e)
sys.exit()
```
#### Create Kafka Topic:
```python
from kafka.admin import KafkaAdminClient, NewTopic
kafka_servers = ["localhost:9092"]
admin_client = KafkaAdminClient(
    bootstrap_servers=kafka_servers,
    client_id='test'
)
topic_list = []
topic_list.append(NewTopic(name="incremental_updates", num_partitions=1, replication_factor=1))
admin_client.create_topics(new_topics=topic_list, validate_only=False)
```

<https://habr.com/en/articles/872976/>
<https://medium.com/@cobch7/kafka-architecture-43333849e0f4>


### 🧩 1. **Kafka Broker Configuration**

This defines how the Kafka server (broker) operates.

-   **File location** (default):
    
    `$KAFKA_HOME/config/server.properties`
    
-   **Key settings** in `server.properties`:
    
```    
broker.id=0
listeners=PLAINTEXT://:9092
log.dirs=/tmp/kafka-logs
num.partitions=6
default.replication.factor=3
zookeeper.connect=localhost:2181
```    

You can pass this file when starting Kafka:

`bin/kafka-server-start.sh config/server.properties`

* * *

### 🧩 2. **Kafka Producer & Consumer Configuration**

These are usually **not stored on the server** but provided at runtime by client applications (e.g., in Java, Python, Spark, Flink, etc.).

#### Option A: **Pass via code**

Example in Java:

```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
```

#### Option B: **Load from config file**

You can define a config file, e.g., `producer.properties` or `consumer.properties`, and load it:

```bash
bin/kafka-console-producer.sh --broker-list localhost:9092 --topic test --producer.config producer.properties  
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test --consumer.config consumer.properties
```

Typical file locations:

-   `producer.properties`: stored with app configs or deployed in `/etc/kafka/` or `conf/`
    
-   `consumer.properties`: same as above, application-specific
    

* * *

### 🧩 3. **Kafka Connect Configs**

Stored as JSON files, typically:

-   Custom location: e.g., `connectors/clickstream-postgres-sink.json`
    
-   Or deployed directly via REST to Kafka Connect.
    
* * *
 
Here's a **sample directory structure** to organize Kafka-related config files   
for a production-grade data pipeline involving Kafka, Connect, Spark/Flink, and consumers.

* * *

## 📂 Recommended Kafka Config Directory Layout

graphql
```
/opt/clickstream-pipeline/
├── kafka/
│   ├── config/
│   │   ├── server.properties            # Kafka broker config
│   │   ├── producer.properties          # Common producer config
│   │   ├── consumer.properties          # Common consumer config
│   │   └── topics-config.json           # Optional topic creation script or metadata
│   └── bin/                             # Kafka CLI tools (optional symlink)
│
├── kafka-connect/
│   ├── connectors/
│   │   ├── postgres-sink.json           # Kafka Connect config for PostgreSQL
│   │   ├── s3-sink.json                 # Kafka Connect config for Amazon S3
│   │   └── bigquery-sink.json           # Kafka Connect config for BigQuery
│   ├── plugins/                         # Custom connector JARs or unpacked directories
│   └── worker.properties                # Kafka Connect distributed or standalone mode
│
├── spark/
│   ├── spark-submit.sh                  # Script to submit Spark job
│   └── application.conf                 # Spark streaming app config
│
├── flink/
│   ├── flink-job.sh                     # Script to launch Flink job
│   └── flink-config.yaml                # Optional Flink job configuration
│
├── logs/
│   ├── kafka/                           # Kafka broker logs
│   ├── connect/                         # Connect logs
│   └── apps/                            # Spark/Flink application logs
│
├── docker/
│   └── docker-compose.yml               # Optional full local stack
│
└── README.md

```

* * *

## ✅ Tips for Managing Configs

-   **Use environment variables** inside config files where needed, e.g., `${KAFKA_BROKER}` for secrets injection.
    
-   Store version-controlled configs in Git; exclude secrets or mount them at runtime.
    
-   Separate dev/test/prod config directories or override with environment-specific values via CI/CD.




## 🧭 Apache Kafka — Key Configuration

### ✅ Broker-side

Parameter  Recommended Value    Purpose

`num.partitions`   100–500 (depends on topic throughput & consumer parallelism)  Enables parallelism across partitions.

`log.retention.hours` 72 (or per data lifecycle)   Controls how long Kafka retains data.

`log.segment.bytes`  512MB–1GB Smaller segments improve log cleaning efficiency.

`log.retention.check.interval.ms` 300000 Controls how often retention is enforced.

`num.replica.fetchers` ≥ 2 Helps with faster replication.

`message.max.bytes`  1MB–10MB  Adjust based on max message size.

`replica.lag.time.max.ms` 10000 Controls follower sync timing.

### ✅ Producer-side

Parameter Recommended Value  Purpose

`acks`  `all` Ensures durability via ISR (in-sync replicas).

`compression.type` `lz4` or `zstd` Improves throughput and reduces disk I/O.

`linger.ms` 5–10 Slight batching improves performance.

`batch.size` 32KB–64KB Adjust for network efficiency.

`retries` 3+ Handles transient errors gracefully.

### ✅ Consumer-side

Parameter Recommended Value Purpose

`max.poll.records` 500–1000 Controls how many messages per fetch.

`fetch.max.bytes` 1MB–50MB Adjust to support large messages. 

`auto.offset.reset` `latest` or `earliest` Depends on restart behavior.

`enable.auto.commit` `false` You should commit manually after processing.

* * *

## ⚙️ Apache Spark Structured Streaming

### ✅ Spark Config

Parameter Recommended Value Purpose

`spark.sql.shuffle.partitions`  100–200+ More partitions improve parallelism.

`spark.streaming.backpressure.enabled` `true` Enables auto-rate adjustment (batch mode only).

`spark.streaming.kafka.maxRatePerPartition` 1000–5000 Rate control per Kafka partition. 

`spark.sql.streaming.stateStore.maintenanceInterval` ~30s Cleans up old state.

`spark.sql.streaming.stateStore.providerClass` `RocksDB` (if using Delta Live Tables) Improves stateful operations.

`spark.sql.streaming.join.stateFormatVersion` `2` Required for production stateful joins.

`spark.executor.memory` 4–16GB Based on workload.

`spark.executor.cores` 2–4 Tune based on cluster size.

`spark.streaming.stopGracefullyOnShutdown` `true` Allows clean exit.

> Note: Spark runs on **micro-batches**, not true streaming. Use **watermarking** and **windowing** for stream joins.

* * *

## 🔁 Apache Flink — Key Parameters

### ✅ Flink Config

Parameter Recommended Value Purpose

`taskmanager.numberOfTaskSlots` 2–4 per core Controls parallelism.

`parallelism.default` 100+ Matches Kafka partitions.

`restart-strategy` `fixed-delay` or `failure-rate` Handles transient failures.

`state.backend` `rocksdb` For large stateful processing.

`state.checkpoints.dir` `hdfs://...` or `s3://...`

Checkpoint storage.

`execution.checkpointing.interval` 1–2 minutes Frequency of checkpoints.

`execution.checkpointing.mode` `EXACTLY_ONCE` Guarantees consistency. 
`state.savepoints.dir`

optional

Manual savepoint path. `state.backend.rocksdb.localdir` fast local SSD path

Improves RocksDB performance.

### ✅ Kafka Source in Flink

Parameter Recommended Value Purpose

`flink.kafka.consumer.group.id` unique-per-job Ensures isolation.

`auto.offset.reset` `earliest` or `latest` Depends on use case.

`enable.auto.commit` `false` Flink manages commits via checkpointing.

### ✅ Flink Join Tuning

-   Use **interval joins** or **temporal joins** for state-efficient joins.
    
-   Set **TTL** on state (`state.ttl` config) to avoid memory bloat.
    

* * *

## 📊 Sizing Guidance

Component Example Config

Kafka topic 100–200 partitions (scale based on consumer count)

Spark/Flink task slots 200–400 for 100M events/day (depends on complexity) Checkpointing

Store to HDFS/S3 every 1–2 mins

DLQ topic Enable a separate Kafka topic (dead-letter) for failed events

* * *

## ✅ 1. Sample `flink-conf.yaml`

```

jobmanager.rpc.address: jobmanager
taskmanager.numberOfTaskSlots: 4
parallelism.default: 200

# Enable checkpointing (5-minute SLA, use lower interval)
execution.checkpointing.interval: 2m
execution.checkpointing.mode: EXACTLY_ONCE
state.backend: rocksdb
state.backend.rocksdb.localdir: /tmp/flink-rocksdb
state.checkpoints.dir: s3://your-bucket/flink-checkpoints
state.savepoints.dir: s3://your-bucket/flink-savepoints

restart-strategy: fixed-delay
restart-strategy.fixed-delay.attempts: 3
restart-strategy.fixed-delay.delay: 10 s

# Optional for state TTL
state.ttl.enabled: true
```

* * *

### ✅ Flink Job CLI Command

```bash
flink run \
    -c com.yourcompany.ClickstreamJob \   
   -p 200 \   
   -Dexecution.checkpointing.interval=2m \   
   -Dstate.backend=rocksdb \   
   your-flink-job.jar
```

* * *

## ✅ 2. Sample `spark-submit` for Structured Streaming

```bash

spark-submit \
  --class com.yourcompany.ClickstreamSparkJob \
  --master yarn \
  --deploy-mode cluster \
  --num-executors 20 \
  --executor-memory 8G \
  --executor-cores 4 \
  --conf spark.sql.shuffle.partitions=200 \
  --conf spark.streaming.kafka.maxRatePerPartition=3000 \
  --conf spark.sql.streaming.stateStore.maintenanceInterval=30s \
  --conf spark.sql.streaming.join.stateFormatVersion=2 \
  --conf spark.sql.adaptive.enabled=true \
  your-spark-job.jar

```

 Make sure you enable checkpointing inside your code (`writeStream.option("checkpointLocation", ...)`)

 and set the trigger interval (`trigger(ProcessingTime("30 seconds"))`).

* * *

## 📦 Notes

-   Both frameworks can **consume Kafka**, **perform stream–static joins**, and **write back to Kafka or another sink** (e.g., Parquet, Delta, PostgreSQL).
    
-   Use **broadcast joins** (Flink) or **map-side joins** (Spark) for dimension data like users/devices if it fits in memory.
    
-   For **user/device/url lookups**:
    
    -   **Flink**: Use `BroadcastState` or `TemporalTableFunction` + `Table API`.
        
    -   **Spark**: Use `join(broadcast(dim_df))`.
        

* * *


Here are **sample code examples** for both **Apache Flink** (Java) and **Apache Spark Structured Streaming** (PySpark),   
showing how to process Kafka clickstream data and join it with dimension tables (`users`, `urls`, `devices`).

* * *

## ✅ 1. **Apache Flink (Java)** – Kafka + Broadcast Join


```java
// Maven dependencies: flink-streaming-java, flink-connector-kafka, flink-rocksdb-state-backend

public class ClickstreamFlinkJob {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(200);
        env.enableCheckpointing(2 * 60 * 1000); // 2 minutes
        env.setStateBackend(new RocksDBStateBackend("s3://your-bucket/flink-checkpoints", true));

        // Kafka Source
        Properties kafkaProps = new Properties();
        kafkaProps.setProperty("bootstrap.servers", "kafka:9092");
        kafkaProps.setProperty("group.id", "clickstream-consumer");

        FlinkKafkaConsumer<String> kafkaConsumer = new FlinkKafkaConsumer<>(
            "clickstream-topic",
            new SimpleStringSchema(),
            kafkaProps
        );

        DataStream<String> clickstreamRaw = env.addSource(kafkaConsumer);

        // Parse JSON and map to POJO
        DataStream<ClickEvent> clickstream = clickstreamRaw
            .map(new MapFunction<String, ClickEvent>() {
                public ClickEvent map(String value) throws Exception {
                    return new ObjectMapper().readValue(value, ClickEvent.class);
                }
            });

        // Broadcast user/device/url dimension maps
        DataStream<Map<String, User>> users = ... // Load periodically
        DataStream<Map<String, Device>> devices = ...
        DataStream<Map<String, Url>> urls = ...

        MapStateDescriptor<String, User> userStateDesc = new MapStateDescriptor<>("users", BasicTypeInfo.STRING_TYPE_INFO, TypeInformation.of(User.class));
        BroadcastStream<Map<String, User>> userBroadcast = users.broadcast(userStateDesc);

        // Join with broadcast state
        DataStream<EnrichedClick> enriched = clickstream
            .connect(userBroadcast)
            .process(new BroadcastProcessFunction<ClickEvent, Map<String, User>, EnrichedClick>() {
                private MapStateDescriptor<String, User> userStateDesc;

                @Override
                public void processElement(ClickEvent event, ReadOnlyContext ctx, Collector<EnrichedClick> out) throws Exception {
                    ReadOnlyBroadcastState<String, User> state = ctx.getBroadcastState(userStateDesc);
                    User user = state.get(event.userId);
                    if (user != null) {
                        out.collect(new EnrichedClick(event, user));
                    }
                }

                @Override
                public void processBroadcastElement(Map<String, User> value, Context ctx, Collector<EnrichedClick> out) throws Exception {
                    BroadcastState<String, User> state = ctx.getBroadcastState(userStateDesc);
                    for (Map.Entry<String, User> entry : value.entrySet()) {
                        state.put(entry.getKey(), entry.getValue());
                    }
                }
            });

        enriched.addSink(new FlinkKafkaProducer<>("enriched-clickstream", new EnrichedClickSchema(), kafkaProps));

        env.execute("Clickstream Flink Job");
    }
}

```

* * *

## ✅ 2. **Apache Spark Structured Streaming (PySpark)** – Kafka + Broadcast Join

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr
from pyspark.sql.types import StructType, StringType, TimestampType

spark = SparkSession.builder \
    .appName("ClickstreamSparkJob") \
    .getOrCreate()

# Kafka source
clickstream_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "clickstream-topic") \
    .option("startingOffsets", "latest") \
    .load()

# Define schema
schema = StructType() \
    .add("timestamp", TimestampType()) \
    .add("user_id", StringType()) \
    .add("url", StringType()) \
    .add("device_id", StringType())

parsed_df = clickstream_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Load dimension tables
users_df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://db/users") \
    .option("dbtable", "users") \
    .option("user", "user") \
    .option("password", "password") \
    .load()

devices_df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://db/devices") \
    .option("dbtable", "devices") \
    .option("user", "user") \
    .option("password", "password") \
    .load()

urls_df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://db/urls") \
    .option("dbtable", "urls") \
    .option("user", "user") \
    .option("password", "password") \
    .load()

# Join with broadcasted dimension data
enriched_df = parsed_df \
    .join(expr("broadcast(users_df)"), on="user_id", how="left") \
    .join(expr("broadcast(devices_df)"), on="device_id", how="left") \
    .join(expr("broadcast(urls_df)"), on="url", how="left")

# Write to sink
query = enriched_df.writeStream \
    .format("console") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/spark-checkpoints/clickstream") \
    .start()

query.awaitTermination()

```

* * *

## 🧪 Output Format (EnrichedClick)
```json
{
  "timestamp": "2025-04-30T12:00:00Z",
  "user_id": "user_123",
  "device_id": "device_456",
  "url": "/products/abc",
  "user_name": "Alice",
  "device_type": "iPhone",
  "url_category": "product-page"
}
```



* * *

## ✅ Kafka Producer Configuration (e.g., app pushing clickstream)

```
bootstrap.servers=kafka1:9092,kafka2:9092
acks=all
compression.type=snappy
batch.size=32768
linger.ms=10
buffer.memory=67108864
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
max.request.size=1048576
retries=3
```

### Notes:

-   `acks=all`: ensures the message is replicated to all in-sync replicas.
    
-   `compression.type=snappy`: good balance of speed and compression.
    
-   `linger.ms=10`: adds small delay to batch more records together.
    
-   `max.request.size=1MB`: prevents oversized messages.
    
-   `retries=3`: helps handle transient failures.
    

* * *

## ✅ Kafka Consumer Configuration (for Spark/Flink app)

```
# consumer.properties

bootstrap.servers=kafka1:9092,kafka2:9092
group.id=clickstream-consumer
enable.auto.commit=false
auto.offset.reset=latest
fetch.min.bytes=1048576
max.poll.records=500
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=org.apache.kafka.common.serialization.StringDeserializer
heartbeat.interval.ms=3000
session.timeout.ms=10000
```
### Notes:

-   `enable.auto.commit=false`: you should commit manually in Spark/Flink.
    
-   `fetch.min.bytes=1MB`: improves throughput.
    
-   `auto.offset.reset=latest`: start from the end if no offset exists.
    
-   `max.poll.records=500`: controls batch size for processing.
    
-   Set `isolation.level=read_committed` if using transactions.
    

* * *

## 📦 Should You Use Kafka Connect?

**Yes — for specific use cases:**

### ✅ Use Kafka Connect when:

-   You need to **bulk ingest or export data** to/from Kafka and systems like:
    
    -   PostgreSQL, MySQL, MongoDB
        
    -   S3, HDFS, GCS
        
    -   Elasticsearch, BigQuery, etc.
        
-   You want **low-code / no-code integration**.
    
-   You want connectors with **exactly-once** semantics.
    

### ❌ Avoid Kafka Connect when:

-   You need **complex event transformations or joins** (use Flink/Spark instead).
    
-   Your sources/sinks aren't supported via available connectors.
    
-   You need **low-latency processing** beyond just moving data.
    

* * *

## 📌 Example: Kafka Connect sink to PostgreSQL

```json
{
  "name": "clickstream-postgres-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "tasks.max": "1",
    "topics": "enriched-clickstream",
    "connection.url": "jdbc:postgresql://db:5432/mydb",
    "connection.user": "user",
    "connection.password": "password",
    "auto.create": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_key",
    "pk.fields": "user_id,timestamp",
    "table.name.format": "clickstream_enriched"
  }
}
```


* * *

## ✅ 1. Kafka Connect to **PostgreSQL**

### Requirements:

-   Kafka Connect running with Debezium or Confluent JDBC Sink connector
    
-   PostgreSQL JDBC driver in Kafka Connect plugin path
    

### Connector Configuration:

Save this as `clickstream-postgres-sink.json`:

```json
{
  "name": "clickstream-postgres-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "topics": "enriched-clickstream",
    "tasks.max": "2",
    "connection.url": "jdbc:postgresql://postgres:5432/clickdb",
    "connection.user": "clickuser",
    "connection.password": "clickpass",
    "insert.mode": "upsert",
    "auto.create": "true",
    "auto.evolve": "true",
    "pk.mode": "record_key",
    "pk.fields": "user_id,timestamp",
    "table.name.format": "clickstream_events",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState"
  }
}
```


### Deploy:


`curl -X POST -H "Content-Type: application/json" \   
--data @clickstream-postgres-sink.json \
http://localhost:8083/connectors`

* * *

## ✅ 2. Kafka Connect to **Amazon S3**

### Requirements:

-   Confluent S3 Sink Connector
    
-   AWS credentials available to Kafka Connect
    

### Connector Configuration (`s3-sink.json`):
```json
{   "name": "clickstream-s3-sink",   
"config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "topics": "enriched-clickstream",
    "s3.bucket.name": "your-s3-bucket",
    "s3.region": "us-east-1",
    "s3.part.size": "5242880",
    "flush.size": "1000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd/'hour'=HH",
     "locale": "en",
    "timezone": "UTC",
    "timestamp.extractor": "RecordField",
    "timestamp.field": "timestamp"   }
}
```

* * *

## ✅ 3. Kafka Connect to **Google BigQuery**

### Requirements:

-   Install the [BigQuery sink connector](https://github.com/wepay/kafka-connect-bigquery)
    
-   Set up GCP credentials in environment or key file
    

### Connector Configuration (`bq-sink.json`):
```json
{
  "name": "clickstream-bq-sink",
  "config": {
    "connector.class": "com.wepay.kafka.connect.bigquery.BigQuerySinkConnector",
    "topics": "enriched-clickstream",
    "project": "your-gcp-project",
    "datasets": ".*=clickstream_dataset",
    "autoCreateTables": "true",
    "autoUpdateSchemas": "true",
    "sanitizeTopics": "true",
    "keyfile": "/path/to/service-account.json"
  }
}
```
* * *

## 🔄 Summary

Destination Connector Class Output Format

PostgreSQL `io.confluent.connect.jdbc.JdbcSinkConnector` Tables

Amazon S3 `io.confluent.connect.s3.S3SinkConnector` Parquet/JSON/Avro

Google BigQuery `com.wepay.kafka.connect.bigquery.BigQuerySinkConnector` Native BQ tables
