## Types of Drift:
### Schema Drift
Structural changes in the data, such as:

New or missing columns
Changed data types
Renamed fields

### Data Drift
Statistical or distributional changes in the data, such as:
Shift in the range, mean, or variance of values
Different frequency of categories
Changing patterns over time

### Concept Drift
In ML pipelines: changes in the relationship between features and target, affecting model accuracy.

✅ Why Drift Matters:
Causes ETL/ELT jobs to fail or produce incorrect results
Impacts machine learning model accuracy
Leads to data quality degradation
Breaks dashboard metrics or downstream logic

✅ Handling Schema Drift:
Dynamic schema inference (e.g., Auto Loader in Databricks)
Flexible schema evolution in formats like Parquet, Delta Lake, or Avro
Versioned schemas using schema registry (e.g., in Kafka)
Field-level validations to detect changes
Alerts or quarantine logic for unknown fields

✅ Handling Data/Concept Drift:
Monitoring tools to track statistics and distributions
Drift detection libraries (e.g., Evidently, River, Alibi Detect)
Retraining models or recalibrating thresholds
Data validation frameworks like Great Expectations or Deequ

✅ In Practice:
Drift handling is often a combination of:
Automation (auto schema handling, alerting)
Governance (schema contracts, metadata tracking)
Observability (logs, metrics, quality checks)
Adaptability (self-healing pipelines, human-in-the-loop decisions)

Apache Parquet, Avro, ORC support evolving schemas.

These formats store metadata about schema alongside the data.
 
✅ Good for: Schema enforcement + efficient storage
2. Schema Registry
Centralized schema versioning and validation (e.g., Confluent Schema Registry for Avro, Protobuf, JSON).

Useful in Kafka pipelines to validate producers/consumers.
 
✅ Enforces contracts
✅ Enables schema compatibility checks (backward, forward)
3. Delta Lake / Apache Iceberg / Hudi
Support schema evolution out-of-the-box (e.g., adding/removing columns).

Delta Lake on Databricks allows:

```python
df.write.format("delta").option("mergeSchema", "true").save(path)
```
✅ Automatic merge of new schema versions
✅ Schema enforcement + versioning
4. Schema Inference Tools

Use tools like Databricks Auto Loader, which can infer and evolve schema automatically:

```python
df = (
  spark.readStream
  .format("cloudFiles")
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
  .load("s3://my-bucket")
)
```
✅ Useful for streaming ingestion
5. Schema Validation Frameworks
Add validation steps in pipelines to detect and reject incompatible schema changes:
Great Expectations
Deequ (AWS)
TFX Data Validation

✅ Prevents bad data from propagating
6. Metadata and Governance
Track schema history using:

Apache Atlas
Unity Catalog (Databricks)
AWS Glue Catalog
Hive Metastore

 
✅ Enables audit, impact analysis, lineage tracking


| Practice                                | Why It Matters                       |
| --------------------------------------- | ------------------------------------ |
| Define **schema compatibility rules**   | Prevents breaking downstream systems |
| Store **schema with data**              | Enables reproducibility              |
| Use **explicit schema definitions**     | Avoids brittle auto-inference        |
| Implement **alerting for schema drift** | Early warning of upstream changes    |
| Version your schema                     | Manage changes without downtime      |


#### Databricks: Schema Drift Handling in Auto Loader / Delta Lake
Databricks’ Auto Loader with Delta Lake supports automatic schema evolution when ingesting files (e.g., JSON, CSV, Parquet).

Example: Auto Loader with mergeSchema
```python
df = (
    spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")  # Auto handle new fields
    .load("s3://your-bucket/input-data")
)

df.writeStream \
    .format("delta") \
    .option("mergeSchema", "true") \  # Enable schema evolution
    .option("checkpointLocation", "s3://your-bucket/checkpoint") \
    .start("s3://your-bucket/output-delta-table")
```
Notes:
mergeSchema=true: Delta Lake automatically merges new columns into the table.

cloudFiles.schemaEvolutionMode=addNewColumns: Handles schema drift in streaming.

### Kafka: Schema Drift Handling with Confluent Schema Registry
Kafka itself doesn’t handle schema drift; instead, it relies on a Schema Registry when using Avro, JSON Schema, or Protobuf.

🔹 Example: Avro + Schema Registry
Producer serializes data with Avro:

```python
from confluent_kafka.avro import AvroProducer

value_schema_str = """
{
  "namespace": "example",
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "name", "type": "string"},
    {"name": "age", "type": "int"}
  ]
}
"""

# Producer sends data that conforms to versioned schema
producer = AvroProducer({
    'bootstrap.servers': 'broker:9092',
    'schema.registry.url': 'http://schema-registry:8081'
}, default_value_schema=value_schema_str)

producer.produce(topic='users', value={"name": "Alice", "age": 30})
```
🔹 Schema Compatibility Rules in Registry:
Backward / Forward / Full

Prevent incompatible changes (e.g., removing required fields)

🔹 Detecting Drift:
Use schema evolution policies + monitoring

Add automated schema validation (e.g., Kafka Connect SMT or MirrorMaker2)

✅ 3. Airflow: Schema Drift Handling with Data Validation and Alerts
Airflow doesn’t manage schema directly but orchestrates validation and alerting tasks.

🔹 Example: Use Great Expectations in an Airflow DAG
```python

from airflow import DAG
from airflow.operators.python import PythonOperator
from great_expectations.dataset import SparkDFDataset

def validate_data(**kwargs):
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    df = spark.read.parquet("s3://your-bucket/input-data")

    ge_df = SparkDFDataset(df)
    ge_df.expect_column_to_exist("user_id")
    ge_df.expect_column_values_to_be_of_type("age", "IntegerType")

    results = ge_df.validate()
    if not results["success"]:
        raise ValueError("Schema drift detected!")

with DAG("schema_drift_detection", start_date=datetime(2024, 1, 1), schedule_interval="@daily") as dag:
    validate = PythonOperator(
        task_id="validate_schema",
        python_callable=validate_data
    )
```
🔹 What this does:
Validates input schema

Raises exception if unexpected schema drift is found

Can trigger email/Slack alerts or branch execution paths

| Tool           | Role in Drift Handling                | Technique                                  |
| -------------- | ------------------------------------- | ------------------------------------------ |
| **Databricks** | Ingestion + Storage                   | `mergeSchema`, `Auto Loader`, Delta format |
| **Kafka**      | Transport + Contract Enforcement      | Avro/Protobuf with Schema Registry         |
| **Airflow**    | Orchestration + Validation + Alerting | Great Expectations, custom checks   |


### Great Expectations

Great Expectations lets you define "expectations"—assertions about your data—that can be automatically tested in your pipelines. 

It also creates human-readable documentation and provides tools to integrate with data stores, orchestration frameworks, and data catalogs.

| Feature                         | Description                                                            |
| ------------------------------- | ---------------------------------------------------------------------- |
| **Expectations**                | Declarative rules about data (e.g., column `age` must be ≥ 0)          |
| **Data profiling**              | Auto-generates expectations from sample data                           |
| **Data validation**             | Run checks and return pass/fail results with metrics                   |
| **Rich reporting**              | Generates HTML validation reports and data docs                        |
| **Integration-ready**           | Works with Airflow, dbt, Prefect, Databricks, Snowflake, S3, GCS, etc. |
| **Versioned and Parameterized** | Expectation suites can be versioned and reused across datasets         |

Supported Data Sources
Local files (CSV, Parquet, JSON)  
Databases: Postgres, Snowflake, Redshift, BigQuery, etc.  
DataFrames: Pandas and PySpark  
Cloud storage: S3, GCS, Azure Blob (via Pandas/Spark readers)  
```python
import great_expectations as ge
import pandas as pd

df = pd.DataFrame({"age": [25, 40, 31, -5]})
ge_df = ge.from_pandas(df)

# Add expectations
ge_df.expect_column_values_to_be_between("age", min_value=0, max_value=100)

# Validate
result = ge_df.validate()
print(result["success"])  # False due to -5
```
When you run great_expectations init, it sets up a directory like this:
```bash
great_expectations/
├── expectations/            # Expectation suites
├── checkpoints/             # Validation configs
├── great_expectations.yml   # Config file
├── plugins/                 # Custom expectations
├── uncommitted/             # Secrets and run-time files
```


Types of Expectations
| Category           | Examples                                                                   |
| ------------------ | -------------------------------------------------------------------------- |
| **Table-level**    | `expect_table_row_count_to_be_between`                                     |
| **Column-level**   | `expect_column_values_to_be_unique`, `expect_column_to_exist`              |
| **Statistical**    | `expect_column_mean_to_be_between`, `expect_column_median_to_be`           |
| **Regex/Format**   | `expect_column_values_to_match_regex`                                      |
| **Datetime/Nulls** | `expect_column_values_to_not_be_null`, `expect_column_values_to_be_in_set` |

Airflow DAG Task with great expectations:
```python
from great_expectations_provider.operators.great_expectations import GreatExpectationsOperator

GreatExpectationsOperator(
    task_id='validate_data',
    checkpoint_name='my_checkpoint',
    data_context_root_dir='/opt/airflow/great_expectations',
)
```

Databricks Notebook
```python
from great_expectations.dataset import SparkDFDataset

df = spark.read.json("/mnt/input.json")
ge_df = SparkDFDataset(df)
ge_df.expect_column_values_to_not_be_null("user_id")
ge_df.validate()
```
Benefits
Catches data drift and quality issues early  
Improves trust in data and pipelines  
Self-documenting: creates browsable data quality reports  
Integrates into CI/CD and orchestration tools


### Kafka Schema Registry (typically the Confluent Schema Registry)
works with data serialization formats like:

Avro (most common)
Protobuf
JSON Schema

It stores the schemas separately from the data, allowing you to enforce schema contracts and track schema evolution over time.

🧩 Why Use Schema Registry?
| Problem                          | Solution with Schema Registry                         |
| -------------------------------- | ----------------------------------------------------- |
| Changing data format over time   | Supports **schema versioning and evolution**          |
| Consumers breaking on new fields | Enforces **backward/forward compatibility**           |
| No visibility into data format   | Provides **API access to versioned schemas**          |
| Data size inefficiency           | Serializes data efficiently with **Avro + schema ID** |


How It Works (Avro Example)
1. Producer writes Avro data with a schema ID (not the whole schema).
2. Kafka stores just the schema ID + binary data.
3. Consumer fetches the schema using the ID from the registry and deserializes the message correctly.

 API operations:
| API                                       | Purpose                               |
| ----------------------------------------- | ------------------------------------- |
| `POST /subjects/{subject}/versions`       | Register new schema version           |
| `GET /subjects/{subject}/versions/latest` | Get latest version of a schema        |
| `GET /schemas/ids/{id}`                   | Retrieve schema by ID                 |
| `GET /subjects`                           | List all registered subjects (topics) |
  
Example: Python Producer and Consumer with Schema Registry

▶️ Producer (Avro)
```python

from confluent_kafka.avro import AvroProducer

value_schema_str = """
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "name", "type": "string"},
    {"name": "age", "type": "int"}
  ]
}
"""

producer = AvroProducer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}, default_value_schema=value_schema_str)

producer.produce(topic='users', value={"name": "Alice", "age": 30})
producer.flush()
```
▶️ Consumer (Avro)
```python

from confluent_kafka.avro import AvroConsumer

consumer = AvroConsumer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081',
    'group.id': 'user-consumer',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['users'])

while True:
    msg = consumer.poll(1)
    if msg:
        print("Received:", msg.value())
```
Schema Compatibility Modes

| Mode       | Meaning                                                |
| ---------- | ------------------------------------------------------ |
| `BACKWARD` | New schema can read data produced with previous schema |
| `FORWARD`  | Previous schema can read data produced with new schema |
| `FULL`     | Both forward and backward compatible                   |
| `NONE`     | No compatibility enforced                              |

You can set this per subject using:

```bash

PUT /config/<subject>
{
  "compatibility": "BACKWARD"
}
```

#### Deployment Options
Standalone Schema Registry (Confluent open source)
Managed (Confluent Cloud Schema Registry)
Dockerized for local testing
```yaml
services:
  schema-registry:
    image: confluentinc/cp-schema-registry
    environment:
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: PLAINTEXT://kafka:9092
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
```

#### Benefits Recap
Ensures data integrity across Kafka producers and consumers

Supports safe schema evolution

Enables schema reuse and sharing

Reduces payload size (schema ID instead of inline schema)

###  Avro
Apache Avro is a row-based binary serialization format designed for efficient, compact data transmission and schema evolution.

🔹 Key Features:
Schema-first: Requires a schema (usually JSON format) to read/write data  
Compact and fast: Optimized for streaming and message-based systems like Kafka  
Supports schema evolution: Fields can be added/removed with compatibility rules  
Works well with row-based access (e.g., event processing)  

🔹 Example Avro Schema:
```
json

{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "name", "type": "string"},
    {"name": "age", "type": "int"}
  ]
}
```
✅ What is Parquet?
Apache Parquet is a columnar storage format optimized for analytics workloads on large-scale datasets (e.g., in Hive, Spark, Snowflake).

🔹 Key Features:
Columnar: Stores data by columns instead of rows

Efficient for filtering & aggregation: Reads only needed columns

Compression-friendly: Better compression ratios per column

Supports complex nested structures

### AVRO vs Parquet

| Feature                 | **Avro**                           | **Parquet**                         |
| ----------------------- | ---------------------------------- | ----------------------------------- |
| Format Type             | Row-based                          | Columnar                            |
| Use Case                | Streaming, Kafka, RPC              | Analytics, OLAP, Data Lakes         |
| Schema Support          | Yes (inline + registry compatible) | Yes (embedded in metadata)          |
| Compression             | Supported                          | Highly efficient (column-level)     |
| Speed (Write)           | Fast for row insert                | Slower than Avro for row-wise write |
| Speed (Read for subset) | Full row needed                    | Efficient for partial column reads  |
| Nested Data             | Good                               | Excellent                           |
| Schema Evolution        | Strong with registry support       | Basic support (e.g., new columns)   |
| Integration             | Kafka, Confluent, Hive, Spark      | Hive, Spark, Impala, Snowflake      |
| File Size               | Smaller for messages               | Smaller for large tabular datasets  |





