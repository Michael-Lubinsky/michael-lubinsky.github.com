### GCP

### Google Cloud CLI 
https://cloud.google.com/sdk/docs/install

 Google Cloud CLI includes the gcloud, gsutil and bq command-line tools
 <!--
https://medium.com/@asmitha23052002/uploading-files-to-google-cloud-storage-gcs-using-the-gsutil-command-line-tool-71bca0a2b731
-->
Gsutil is deprecated - you need to move to using gcloud storage instead
https://cloud.google.com/storage/docs/discover-object-storage-gcloud

```python
from google.cloud import storage

# Initialize a client
client = storage.Client()

# List all buckets
buckets = client.list_buckets()
for bucket in buckets:
    print("Bucket name:", bucket)
```

* * *

### **GCS (Google Cloud Storage)**

Object storage for any type of data—files, images, backups, logs, etc.

-   **Scalable & Durable:** Stores massive amounts of unstructured data with high durability (11 9's).
    
-   **Buckets & Objects:** Data is stored in _buckets_ and each file is called an _object_.
    
-   **Classes:** Offers different storage classes like Standard, Nearline, Coldline, and Archive based on access frequency and cost.
    
-   **Access:** Can be accessed via REST API, SDKs, or `gsutil` CLI.
    
-   **Use Cases:** Backup, media storage, Big Data input/output, machine learning datasets, website hosting.
    

**Example Use:**  
You can store a `.csv` file in GCS and later read it from a data processing pipeline.

* * *

###   **Pub/Sub (Publish/Subscribe)**

Real-time messaging service for decoupling systems that produce and consume data.


-   **Asynchronous Messaging:** Enables real-time, scalable, event-driven systems.
    
-   **Publisher-Subscriber Model:** Publishers send messages to a _topic_, and subscribers receive messages from that topic.
    
-   **Durability & Scalability:** Supports millions of messages per second.
    
-   **Push & Pull Modes:** Subscribers can either pull messages or have them pushed to a webhook.
    
-   **Use Cases:** Event ingestion pipelines, microservices communication, log aggregation, streaming analytics.
    

**Example Use:**  
A system logs user clicks, publishes each click event to a Pub/Sub topic, and a downstream analytics service consumes these events for processing.

### **How to Configure / Tune Google Pub/Sub**

Because Pub/Sub is **serverless and auto-scaled**, there is **very little infrastructure tuning** you need to do compared to Kafka. But you can still optimize it in several ways depending on your use case:

#### **1\. Subscription Type**

-   **Pull**: Clients fetch messages.
    
-   **Push**: Google Pub/Sub pushes messages to your endpoint (e.g., Cloud Function, HTTP webhook).
    

Choose **pull** for more control, and **push** for simpler, event-driven architectures.

#### **2\. Acknowledge Deadline**

-   The default is 10 seconds; can be extended up to 10 minutes.
    
-   Tune this if your processing logic takes longer.
 

`subscriber.modify_ack_deadline()`

#### **3\. Message Retention**

-   Default: 7 days.
    
-   Can be configured per topic.

`gcloud pubsub topics update YOUR_TOPIC \     --message-retention-duration=168h`

#### **4\. Message Ordering**

-   Disabled by default (no guarantee).
    
-   Enable **ordering keys** if you need ordering by some logical grouping.
    

`gcloud pubsub topics create my-topic --enable-message-ordering`

#### **5\. Flow Control (for Pull subscriptions)**

You can set client-side limits to avoid overloading consumers:
```python
flow_control = pubsub_v1.types.FlowControl(
    max_messages=10,
    max_bytes=1024 * 1024,
    max_lease_duration=300  # seconds
)
```

#### **6\. Batching Settings**

Improve throughput by tuning how messages are batched:

```python
batch_settings = pubsub_v1.types.BatchSettings(
    max_bytes=1024*1024,      # 1 MB
    max_latency=0.01,         # 10 ms
    max_messages=1000
)
```

#### **7\. Dead Letter Topics (DLQ)**

Set up DLQs for failed messages:

```bash
gcloud pubsub subscriptions update my-sub \
  --dead-letter-topic=projects/my-project/topics/my-dlq-topic \
  --max-delivery-attempts=5
```

### **How They Work Together:**

-   You can **store files in GCS**, and when a new file is uploaded, **trigger a Pub/Sub message** to notify downstream systems to process it.
    
-   Example: Uploading a JSON file to GCS triggers a Cloud Function via Pub/Sub to parse and store the data in BigQuery.


### Cloud Function 
is a serverless compute service that lets you run single-purpose functions in response to events—without managing servers or infrastructure.

✅ What is a GCP (Google Cloud) Function?
GCP Cloud Functions are:

Event-driven: Triggered by events from GCP services like Cloud Storage, Pub/Sub, Firebase, or HTTP requests.

Serverless: No need to provision or manage servers; you deploy just the code.

Auto-scaling: Scales up/down automatically based on incoming requests.

Short-lived: Designed for lightweight, stateless tasks.

🧠 Use Cases
| Use Case                    | Example                                   |
|---------------------------|--------------------------------------------|
| **Cloud Storage Trigger**   | Process images when uploaded to a GCS bucket |
| **Pub/Sub Message Handler** | Process log events or notifications          |
| **HTTP API Endpoint**       | Build a lightweight RESTful API              |
| **Firebase Backend Logic**  | Send notifications or validate data          |
| **Scheduled Jobs**          | Run cleanup tasks daily with Cloud Scheduler |


🔧 How to Create a Cloud Function
A. Via Console
Go to GCP Console → Cloud Functions

Click “Create Function”

Choose trigger type:

- HTTP
- Cloud Storage
- Pub/Sub

Write or upload your function code

Click Deploy

B. Via CLI
```
gcloud functions deploy my-function \
  --runtime python311 \
  --trigger-http \
  --entry-point=my_function \
  --region=us-central1 \
  --allow-unauthenticated
```
Example: HTTP Cloud Function in Python
```python
def hello_world(request):
    name = request.args.get('name', 'World')
    return f"Hello, {name}!"
```


| Generation  | Key Differences                                                                      |
| ----------- | ------------------------------------------------------------------------------------ |
| **1st Gen** | Original version, basic runtime support                                              |
| **2nd Gen** | Built on **Cloud Run**, better performance, concurrency, networking, and VPC support |

| Feature           | Description                             |
| ----------------- | --------------------------------------- |
| **Trigger Types** | HTTP, Pub/Sub, Cloud Storage, Scheduler |
| **Scalability**   | Fully managed, auto-scaling             |
| **Pricing**       | Pay only for execution time             |
| **Best For**      | Lightweight, event-driven workloads     |


Google Cloud Functions and Cloud Dataflow are both part of GCP's data and compute ecosystem,   
but they serve different roles and have different strengths.  
However, they can work together in complementary ways, especially in event-driven data pipelines.

| Feature            | **Cloud Function**                       | **Cloud Dataflow**                                |
| ------------------ | ---------------------------------------- | ------------------------------------------------- |
| **Type**           | Serverless function (FaaS)               | Fully managed stream/batch data processing engine |
| **Use case**       | Lightweight event-handling               | Complex ETL, stream/batch processing              |
| **Scale**          | Automatically scales per request         | Scales across VMs/workers                         |
| **Execution time** | Short-lived (minutes)                    | Long-running jobs (can run for hours/days)        |
| **Languages**      | Python, Node.js, Go, Java, etc.          | Java, Python (Apache Beam SDK)                    |
| **Trigger**        | HTTP, Pub/Sub, Cloud Storage, etc.       | Manual, scheduler, or triggered via API           |
| **Pricing model**  | Pay-per-invocation + duration (ms-based) | Pay-per-resource usage (CPU, memory, time)        |


How They Work Together
🧩 Cloud Function as a Trigger for Dataflow
You can use a Cloud Function to start a Dataflow pipeline when:

A file is uploaded to Cloud Storage

A message arrives in Pub/Sub

An HTTP request is received (e.g., from an app)

🔁 Common Pattern:
Event occurs (e.g., file upload to GCS)

Cloud Function is triggered, parses metadata

Cloud Function starts a Dataflow job via REST API or subprocess.run() (with gcloud CLI)

Dataflow processes the data (e.g., ETL, windowed aggregations)

Example: Cloud Function triggering a Dataflow job

```python
import subprocess

def trigger_dataflow(event, context):
    file_path = event['name']
    subprocess.run([
        'gcloud', 'dataflow', 'jobs', 'run', f"etl-job-{context.event_id}",
        '--gcs-location', 'gs://my-bucket/templates/etl-template',
        '--parameters', f'inputFile=gs://my-bucket/{file_path}'
    ])
```

### Dataflow  and Dataproc

**Dataflow** and **Dataproc** are two different Google Cloud services for processing large-scale data — 
but they serve different use cases and are built on different paradigms:

* * *

## 🧠 **High-Level Summary**

| Feature | **Cloud Dataflow** | **Cloud Dataproc**
|--------|---------------------|---------------|
| **Type** | Serverless stream & batch data processing | Managed Apache Hadoop/Spark/Presto clusters
| **Best For** | Stream processing, ETL pipelines | Reusing existing Hadoop/Spark jobs
| **Programming** | Apache Beam SDK (Java, Python) | Native Hadoop/Spark/Presto code (Java, PySpark, etc.)
| **Infrastructure** | Fully managed, auto-scaled | User-managed or semi-managed clusters

* * *

## 🔧 **Cloud Dataflow**

**Dataflow** is Google’s **serverless data processing service** built on **Apache Beam**.

### ✅ Key Features:

-   Supports **both batch and streaming** pipelines
    
-   Uses **Apache Beam SDK**: write once, run anywhere
    
-   **Autoscaling**: No need to manage VMs
    
-   Built-in **windowing, watermarks**, and **late data handling** (for streaming)
    
-   Integrated with **Pub/Sub**, **BigQuery**, **Cloud Storage**, **AI Platform**
    

### 📌 Example Use Cases:

-   Real-time log analysis (e.g. logs from websites or IoT)
    
-   ETL: Load/transform data from GCS to BigQuery
    
-   Event processing with complex time semantics
    

* * *

## 🔨 **Cloud Dataproc**

**Dataproc** is Google’s **managed Hadoop and Spark** service — ideal if you already use these open-source tools.

<https://cloud.google.com/dataproc>

<https://cloud.google.com/dataproc#documentation>

<https://medium.com/@study7vikas/google-cloud-architect-learning-day-42-642a4658221d>


### ✅ Key Features:

-   Deploys **Hadoop, Spark, Hive, Presto** clusters in ~90 seconds
    
-   Easy migration of existing on-prem **Spark/Hadoop** jobs
    
-   You control cluster sizing, scaling, and termination
    
-   Can run **Jupyter notebooks**, PySpark jobs, etc.
    
-   Supports **custom images and init actions**
    

### 📌 Example Use Cases:

-   Legacy Spark/Hadoop batch jobs
    
-   Machine learning workflows using PySpark or MLlib
    
-   Ad hoc analytics with Hive or Presto
    

* * *

## ⚖️ **When to Use Which?**

|Use Case / Facto | **Choose Dataflow** | **Choose Dataproc** |
|-----------------|---------------------|---------------------|
| Real-time stream processing | ✅ Ideal |🚫 Not designed for real-time
| Serverless / No cluster management | ✅ Yes | ❌ You manage cluster lifecycle
| Familiar with Apache Beam | ✅ Native | 🚫 Not supported
| Already using Spark/Hadoop jobs | 🚫 Not compatible | ✅ Ideal
| Long-running batch jobs | ✅ Yes | ✅ Yes
| Ad hoc big data exploration | 🚫 Harder | ✅ Spark notebooks supported
| Pricing model | Pay-per-use | Pay-per-cluster

* * *


-   **Cloud Dataflow** = Best for **streaming + batch**, **serverless**, future-proof ETL.
    
-   **Cloud Dataproc** = Best for **existing Spark/Hadoop** workloads, **more control**.
    

* * *

#### Create Spark Cluster
```bash
gcloud dataproc clusters create my-cluster \
    --region=us-central1 \
    --zone=us-central1-a \
    --master-machine-type=n1-standard-4 \
    --worker-machine-type=n1-standard-4 \
    --num-workers=2 \
    --image-version=2.1-debian11 \
    --enable-component-gateway \
    --optional-components=JUPYTER \
    --bucket=my-bucket


Submit PySpark script stored in Cloud Storage
#--------------------------------------------
gcloud dataproc jobs submit pyspark gs://my-bucket/scripts/my_job.py \
    --cluster=my-cluster \
    --region=us-central1


Submit Spark job using JAR:
#---------------------
gcloud dataproc jobs submit spark \
    --cluster=my-cluster \
    --region=us-central1 \
    --class=com.example.MyApp \
    --jars=gs://my-bucket/jars/my_app.jar

```
 Use Dataproc Jupyter notebook (if enabled)
Navigate to Dataproc → Clusters → Web Interfaces → Jupyter, 
and run your code interactively.


The **closest equivalent to Apache Airflow** in **Google Cloud Platform (GCP)** is:

> ✅ **Cloud Composer**

* * *

## 🧠 What is Cloud Composer?

**Cloud Composer** is GCP’s **managed Apache Airflow service**.  
It provides **workflow orchestration** for your data pipelines — just like open-source Airflow —
but without the burden of managing the underlying infrastructure.

* * *

## 🔧 Key Features

Feature  | Cloud Composer (GCP Managed Airflow) |
|--------|------------| 
| **Orchestrator** | Apache Airflow (open source) |
| **Managed by** | Google Cloud (updates, scaling, security)
| **Language** | Python (Airflow DAGs)
| **Integrations** | BigQuery, Dataflow, Dataproc, Cloud Run, GCS, Pub/Sub, etc.
| **Version Control** | Supports custom Airflow versions
| **UI** | Airflow Web UI via GCP Console
| **Environment Isolation** | Each Composer environment runs in its own GKE cluster
| **Monitoring** | Integrated with Stackdriver (Cloud Logging, Monitoring)

* * *

## 🧬 Common Use Cases

-   Run and schedule ETL jobs
    
-   Trigger Dataflow pipelines or BigQuery scripts
    
-   Manage cross-service dependencies
    
-   Send alerts on job failures
    
-   Chain Python, Bash, SQL, and REST tasks
    

* * *

## 🔁 Example DAG (Python)

```python
from airflow import DAG
from airflow.operators.bash
import BashOperator
from datetime import datetime
 with DAG('my_composer_dag',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily')
 as dag:
       task1 = BashOperator(
            task_id='print_hello',
           bash_command='echo Hello from Composer!'
       )
```
* * *

## ⚖️ Comparison: Cloud Composer vs. Apache Airflow

| Feature | Cloud Composer | Self-hosted Apache Airflow
|--------|--------|----| 
| **Hosting** | GCP-managed (runs on GKE) | User-managed |
| **Setup Time** | Minutes | Hours or more
| **Scaling** | Automatic (within limits) | Manual
|**Integration** | Deep GCP integration | Requires plugins
| **Cost** | Higher (GCP infra + Composer) | Lower infra, but labor cost
| **Upgrades** | Google-managed or manual | Manual

* * *

## 💵 Pricing Notes

Cloud Composer charges based on:

-   **Environment uptime (vCPUs, memory)**
    
-   **Storage (DAGs, logs)**
    
-   **GKE cluster usage**
    

If cost is a concern, **Composer 2** is much more cost-efficient than Composer 1,
due to autoscaling and better separation of control/data planes.

* * *

## 🚀 Summary

> **Cloud Composer = Fully-managed Apache Airflow on Google Cloud**

It’s perfect if you:

-   Want Apache Airflow without the ops headache
    
-   Need native GCP service integration
    
-   Are orchestrating multi-step workflows in BigQuery, Dataflow, Dataproc, etc.


## 🧠 **High-Level Summary**

Feature | **Cloud Composer (Apache Airflow)** | **Google Cloud Workflows**
|--------|------------------------------------|---------------------------|
| **Best For** | Complex, data-oriented workflows | Lightweight, event-driven workflows
| **Programming** | Python-based DAGs | YAML / JSON-like DSL
| **Infrastructure** | Managed Airflow on GKE | Fully serverless
| **Latency** | Higher (Cold start + GKE overhead) | Very low (sub-second triggers)
| **Use Case Type** | Data engineering, batch jobs | Event-driven, microservices, APIs

* * *

## 🔍 **Key Differences**

### 1\. **Use Case Focus**

| Area    | Cloud Composer |      Workflows |
|--------|-----------------|---------------------------|
| Data pipelines| ✅ Ideal (BigQuery, Dataflow, etc.) | 🚫 Not ideal
| Microservice orchestration |  🚫 Complex, overkill | ✅ Designed for this
| API calls & chaining 🚫 Requires Python boilerplate | ✅ Native support
| Long-running workflows | ✅ Handles retries, dependencies | ✅ With constraints
| Real-time workflows | 🚫 Not ideal (GKE startup time) | ✅ Excellent

* * *

### 2\. **Programming Model**

Feature | Cloud Composer |  Workflows
|-------|----------------|----------|
| Language | Python (Airflow DAGs) | YAML/JSON DSL
| Ease of Use | Familiar for Python developers | Simpler for event/API chaining
| Conditional Logic | Python-native | Limited, but supported in DSL
| Retry/Timeouts | Advanced (Airflow operators) Built-in (`retry`, `timeout`, etc.)

* * *

### 3\. **Execution & Performance**

|Feature | Cloud Composer | Workflows |
|-------|----------------|----------|
| Cold start latency | 1–2 minutes (GKE startup) | Sub-second
| Concurrency | High with tuning | High by default
| Autoscaling | Composer 2 supports better scaling | Fully autoscaled

* * *

### 4\. **Integration & Extensibility**

| Integration                   | Cloud Composer (Airflow) | Workflows                    |
| ----------------------------- | ------------------------ | ---------------------------- |
| BigQuery, Dataflow, GCS, etc. | ✅ Built-in operators     | ✅ Via HTTP API calls         |
| Third-party APIs              | ✅ Possible, more complex | ✅ Native in workflows        |
| Cloud Functions / Pub/Sub     | ✅ Good via sensors       | ✅ Excellent (event triggers) |


* * *

### 5\. **Pricing Model**

| Model           | Cloud Composer                               | Workflows                       |
| --------------- | -------------------------------------------- | ------------------------------- |
| Cost Basis      | Environment uptime + resources + GKE cluster | Per execution + step count      |
| Free Tier       | No free tier                                 | Yes — 5,000 steps/month free    |
| Cost Efficiency | Expensive for low-frequency tasks            | Cheap for lightweight workflows |


* * *

## 🧪 Example Use Cases

| Use Case                                     | Recommended Tool |
| -------------------------------------------- | ---------------- |
| ETL pipeline: GCS → Dataflow → BigQuery      | ✅ Cloud Composer |
| Orchestrating Cloud Functions                | ✅ Workflows      |
| Automating ML pipeline with training + eval  | ✅ Cloud Composer |
| Calling multiple external APIs conditionally | ✅ Workflows      |
| Real-time API event → log → notify           | ✅ Workflows      |


* * *

## 🏁 **Summary**


| Feature/Focus       | **Cloud Composer**                | **Google Cloud Workflows**        |
| ------------------- | --------------------------------- | --------------------------------- |
| Orchestration Type  | Data pipelines & batch            | Microservices, APIs, event-driven |
| Developer Skill Fit | Data engineers, Python users      | Cloud developers, low-code users  |
| Infrastructure      | Managed Airflow on GKE            | Fully serverless                  |
| Setup Time          | Minutes to hours                  | Seconds                           |
| Pricing             | Medium to high (persistent infra) | Low (pay-per-use)                 |


### ✅ **Choose Cloud Composer if:**

-   You're a **data engineer** working with BigQuery, Dataflow, or Dataproc.
    
-   You need **complex scheduling**, retries, dependencies, and custom Python logic.
    

### ✅ **Choose Workflows if:**

-   You want a **lightweight, serverless** way to **orchestrate services/APIs**.
    
-   You're working on **event-driven microservices**, Cloud Functions, or HTTP-based flows.
    

* * *


### Cloud SQL   
https://cloud.google.com/sql/docs 
Cloud SQL is a fully-managed database service that helps you set up, maintain, manage, and administer your relational databases on Google Cloud Platform.

You can use Cloud SQL with MySQL, PostgreSQL, or SQL Server.


### BigQuery
fully-managed, serverless data warehouse** designed for fast SQL analytics on large-scale datasets.

* * *

### 🔍 **Key Features of BigQuery**

| Feature                             | Description                        |
| ----------------------------------- | ------------------------------------------------------------------- |
| **Serverless**                      | No infrastructure management — Google handles provisioning, scaling, and maintenance.                    |
| **SQL-Based**                       | Use standard SQL to query structured, semi-structured (JSON), or nested data.                            |
| **Massively Scalable**              | Handles **petabytes** of data with high performance.                                                     |
| **Separation of Storage & Compute** | You can store data separately and only pay for what you query.                                           |
| **Real-Time Analytics**             | Can stream data in and analyze it in near real-time.                                                     |
| **Machine Learning (BigQuery ML)**  | Run ML models directly using SQL, without moving data.                                                   |
| **Federated Queries**               | Query data directly from Google Cloud Storage, Google Sheets, or external databases.                     |
| **Integration**                     | Works well with GCP services like Dataflow, Dataproc, Looker, and external tools like Tableau, Power BI. |


* * *

### 🧪 Example Use Case


```sql
SELECT   country,   COUNT(*) AS num_sales
FROM   `my_project.sales_data.transactions`
WHERE   DATE(transaction_time) = "2025-05-01"
GROUP BY   country ORDER BY   num_sales DESC;
```

This query could scan **terabytes of data** in seconds — no tuning, indexing, or infrastructure setup needed.


When you create a table in BigQuery, the data is stored in Google's proprietary internal columnar storage format  
— not in formats like Parquet, CSV, or external storage such as GCS or S3 
(unless you explicitly configure it that way).

### Exceptions: External Tables (Federated Queries)
You can create external tables in BigQuery that reference data stored outside BigQuery, such as:
| Source                            | Storage Location | Format                            |
| --------------------------------- | ---------------- | --------------------------------- |
| **Google Cloud Storage (GCS)**    | Buckets          | CSV, JSON, Avro, Parquet, ORC     |
| **Google Drive**                  | Files in Drive   | Google Sheets                     |
| **Bigtable, Cloud SQL, Spanner**  | Google-managed   | Native tables                     |
| **Amazon S3 (via Data Transfer)** | S3 bucket        | Parquet, CSV (via scheduled load) |

```sql
CREATE EXTERNAL TABLE my_dataset.gcs_table
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://my-bucket/path/*.parquet']
);
```

| Table Type          | Where Data Is Stored           | Format                      | Performance          |
| ------------------- | ------------------------------ | --------------------------- | -------------------- |
| **Native Table**    | BigQuery internal storage      | Proprietary columnar format | Fastest (optimized)  |
| **External Table**  | GCS / Drive / Cloud SQL        | CSV, JSON, Parquet, etc.    | Slower, limited      |
| **Federated Query** | Other services (via connector) | Source-defined              | Flexible, but slower |


### Querying JSON Fields
You can use the JSON_VALUE, JSON_QUERY, and JSON_EXTRACT functions.

🔸 Example 1: Extract scalar value
```sql

SELECT JSON_VALUE(data, '$.user.name') AS user_name
FROM my_dataset.events;
```
🔸 Example 2: Extract nested object or array
```sql

SELECT JSON_QUERY(data, '$.user.preferences') AS prefs
FROM my_dataset.events;
```
🔸 Example 3: Dot notation (on JSON fields with known structure)
```sql

SELECT data.user.age FROM my_dataset.events;
```
⚠️ Only works if data is parsed to a STRUCT, not plain JSON.

🔄 Loading JSON into BigQuery

A. From GCS JSON file
Use NEWLINE_DELIMITED_JSON format

Map fields to JSON column type or schema

B. Direct Insert
```sql

INSERT INTO my_dataset.events (id, data)
VALUES ('e1', JSON '{"user": {"name": "Alice", "age": 30}}');
```

| Function           | Description                            |
| ------------------ | -------------------------------------- |
| `JSON_VALUE()`     | Extracts scalar (e.g., string, number) |
| `JSON_QUERY()`     | Extracts JSON object or array          |
| `JSON_EXTRACT()`   | Legacy version of `JSON_QUERY()`       |
| `TO_JSON_STRING()` | Converts STRUCT/ARRAY to JSON string   |
| `PARSE_JSON()`     | Converts string to JSON data type      |

In addition to SQL, BigQuery supports several APIs and interfaces to interact with and manage data.   
These APIs allow programmatic access for data ingestion, querying, schema management, job control, and more.

Here’s a breakdown of the APIs and interfaces BigQuery supports:

✅ 1. BigQuery REST API
The primary programmatic interface.

Enables query execution, dataset/table creation, job monitoring, data loading/export, etc.

All client libraries (Python, Java, etc.) are wrappers around this API.

Docs:
https://cloud.google.com/bigquery/docs/reference/rest

✅ 2. BigQuery Client Libraries (SDKs)
Language	Library Name	Purpose  
Python	google-cloud-bigquery	Most popular for data science  
Java	com.google.cloud:google-cloud-bigquery	For Java/Scala-based systems  
Node.js	@google-cloud/bigquery	For serverless and web apps  
Go, C#, PHP	Official libraries also available	Broad language support

Example (Python):

```python

from google.cloud import bigquery

client = bigquery.Client()
query_job = client.query("SELECT name FROM `my_dataset.my_table`")
for row in query_job:
    print(row.name)
```
✅ 3. BigQuery Storage API
Enables fast parallel reads from BigQuery tables (used by Spark, Dataflow, etc.)

More efficient than the REST API for high-throughput reads.

Supports row-level reads, filtering, and column projections.

Use cases:

Connecting BigQuery to Apache Spark, Pandas, Dask, or TensorFlow

Fast batch data transfer into analytics engines

✅ 4. BigQuery Data Transfer Service
Automates data ingestion from:

Google Ads, YouTube, Google Analytics

Amazon S3, Teradata, etc.

Runs on a schedule, no manual ETL code needed.

✅ 5. BigQuery ML API
Allows training and serving ML models directly in BigQuery using SQL.

Models: linear/logistic regression, k-means, XGBoost, deep neural nets, etc.

Example:

```sql
 
CREATE MODEL my_dataset.model_name
OPTIONS(model_type='logistic_reg') AS
SELECT * FROM my_dataset.training_data;
```
✅ 6. BigQuery BI Engine API
Used for accelerating dashboard tools like Looker Studio (formerly Data Studio).

Enables in-memory caching and sub-second performance for dashboards.

Administered via SQL and REST API.

✅ 7. Cloud Console / UI
Not a formal API, but important:

Web-based SQL editor

Schema browser

Job history and monitoring

Interactive charting and result export

✅ 8. bq Command-Line Tool
Part of Google Cloud SDK

CLI wrapper around BigQuery REST API

Example:

```bash

bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM my_dataset.my_table'
```

| Tool/Platform                   | Integration                                           |
| ------------------------------- | ----------------------------------------------------- |
| **Apache Spark**                | Via `spark-bigquery-connector`                        |
| **Apache Beam/Dataflow**        | Native BigQuery I/O connectors                        |
| **Pandas / Jupyter**            | `pandas-gbq` or `google-cloud-bigquery`               |
| **Airflow**                     | `BigQueryOperator`, `BigQueryInsertJobOperator`       |
| **Looker / Tableau / Power BI** | Native connectors to BigQuery                         |
| **Federated Query**             | Query external sources (Cloud SQL, GCS, Sheets, etc.) |


### 💲 **Pricing**

-   **Storage**: ~$0.02/GB/month (for active storage)
    
-   **Query**: ~$5 per TB scanned (first 1 TB/month is free)
    
-   **Streaming inserts**: ~$0.01 per 200 MB
    
-   **Flat-rate pricing**: Available for large, predictable workloads
    

🔸 **Pro tip**: Use **partitioned** and **clustered tables** to reduce costs by limiting the amount of data scanned.

* * *

### 📊 When to Use BigQuery

**Ideal for:**

-   Analyzing huge datasets quickly
    
-   Real-time analytics
    
-   Building dashboards (Looker, Data Studio)
    
-   Running ML/AI on tabular data without exporting
    

**Less ideal for:**

-   OLTP (transaction-heavy systems)
    
-   Small, frequent row-level updates



### Tuning BigQuery 
for performance and cost-efficiency involves a combination of table design,   
query writing best practices, and configuration parameters. Here's a detailed breakdown:

✅ 1. Table Partitioning in BigQuery
Partitioning helps reduce the amount of data scanned, improving query performance and lowering cost.

Types of Partitioning
A. Time-based Partitioning
Partitioned by a DATE, DATETIME, or TIMESTAMP column.

```sql

CREATE TABLE my_dataset.logs
PARTITION BY DATE(timestamp_column)
AS SELECT ...
```
B. Ingestion-time Partitioning
Automatically partitions by load time.

```sql

CREATE TABLE my_dataset.logs
PARTITION BY _PARTITIONTIME
AS SELECT ...
```

C. Integer Range Partitioning
Partitioned by an integer column (e.g. customer ID buckets).

```sql

CREATE TABLE my_dataset.sales
PARTITION BY RANGE_BUCKET(customer_id, GENERATE_ARRAY(1, 1000, 10))
AS SELECT ...
```
💡 Best Practice: Use time partitioning on large log/event/history tables to prune unneeded data during query.

✅ 2. Table Clustering
Clustering sorts data within partitions to optimize filter and join operations.

Clustering Columns
Up to 4 columns

Use columns commonly filtered/joined

```sql

CREATE TABLE my_dataset.sales
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, region
AS SELECT ...
```
💡 Best Practice: Use clustering on high-cardinality columns like user_id, email, or device_id.

✅ 3. Query Hints and Optimizations
A. Table Hints
Use TABLE_DATE_RANGE or _PARTITIONTIME to restrict partitions manually:

```sql

SELECT * FROM my_table
WHERE _PARTITIONTIME BETWEEN '2024-01-01' AND '2024-01-31'
```
For range partitioned tables:

```sql

WHERE customer_id BETWEEN 100 AND 200
```

B. JOIN Strategy Hint
Force the planner to broadcast or shuffle joins:

```sql

SELECT /*+ BROADCAST_JOIN(build_table) */
FROM large_table
JOIN build_table ON ...
```

C. Materialized Views / Temp Tables
Store intermediate results to avoid recomputation:

```sql

CREATE TEMP TABLE temp_result AS
SELECT ... FROM big_table WHERE ...
```
✅ 4. Cost & Performance Tuning Parameters
BigQuery is serverless—you don't manage infrastructure—but you can still tune how it behaves:

| Setting                  | Description                         | Example                           |
| ------------------------ | ----------------------------------- | --------------------------------- |
| **Maximum bytes billed** | Enforce upper limit on query size   | `1 GB`                            |
| **Use cached results**   | Use cache for repeated queries      | `true/false`                      |
| **Destination table**    | Save results to avoid recomputation | Output to permanent or temp table |
| **Labels**               | Add metadata for tracking usage     | `env:prod`, `team:data`           |

    

### B. **Using Slots for Consistent Performance**

-   Default is **on-demand pricing** (pay-per-query)
    
-   For consistent performance on large workloads, consider **reservation-based model (flat-rate slots)** with **autoscaling**
    

* * *

### ✅ 5. **Monitoring and Troubleshooting**

-   Use **Query Execution Details** in UI to:
    
    -   Check **slots used**, **shuffle data size**, **partition filter effectiveness**
        
    -   Identify long-running or inefficient stages
        
-   Use __INFORMATION\_SCHEMA.JOBS\_BY\__ views_\* to programmatically analyze job history and performance


### Other tips

| Practice                        | Why it Helps                                  |
| ------------------------------- | --------------------------------------------- |
| **Select only needed columns**  | Reduces scanned data                          |
| **Use `WITH` (CTEs) carefully** | Break complex queries into reusable logic     |
| **Filter early**                | Apply `WHERE` conditions as early as possible |
| \*\*Avoid SELECT \*\*\*         | Prevent scanning unused columns               |
| **Deduplicate input data**      | Avoid large joins/aggregations on duplicates  |
| **Avoid UDFs if possible**      | UDFs can be slower and less optimized         |

### Example
```sql
SELECT customer_id, SUM(amount) AS total
FROM my_dataset.sales
WHERE DATE(order_date) BETWEEN '2024-01-01' AND '2024-01-31'
  AND region = 'US'
GROUP BY customer_id
```


###  Configure Hadoop on GCP (Dataproc)
In GCP Dataproc, Hadoop (HDFS and MapReduce/YARN) configuration is managed through:

Cluster properties during cluster creation:
--properties flag or via the Console.

Configuration files (e.g., core-site.xml, hdfs-site.xml, yarn-site.xml)
You can customize these using:

Initialization actions

Override configs in cluster creation

### Key Configuration Parameters for HDFS (hdfs-site.xml)

| Parameter                                         | Description                      | Recommended Setting                           |
| ------------------------------------------------- | -------------------------------- | --------------------------------------------- |
| `dfs.replication`                                 | Number of data replicas          | `2` (default is 3; use 2 on GCP to save cost) |
| `dfs.blocksize`                                   | HDFS block size                  | `128MB` or `256MB` for large files            |
| `dfs.namenode.handler.count`                      | Threads handling client requests | `20–100` for large clusters                   |
| `dfs.datanode.max.transfer.threads`               | Controls parallel data transfers | `4096` or more for busy clusters              |
| `dfs.namenode.name.dir` / `dfs.datanode.data.dir` | Storage paths                    | Use separate local SSDs for performance       |

Set via properties:


--properties=hdfs:dfs.replication=2,hdfs:dfs.blocksize=268435456

### YARN & MapReduce Tuning (yarn-site.xml, mapred-site.xml)


| Parameter                                                | Description                     | Recommendation                              |
| -------------------------------------------------------- | ------------------------------- | ------------------------------------------- |
| `yarn.nodemanager.resource.memory-mb`                    | Max memory for containers       | Typically \~85% of node memory              |
| `yarn.scheduler.maximum-allocation-mb`                   | Max memory per container        | Same as above                               |
| `mapreduce.map.memory.mb` / `mapreduce.reduce.memory.mb` | Memory per map/reduce task      | 2048–8192 MB based on job size              |
| `mapreduce.task.io.sort.mb`                              | Buffer for sorting in map tasks | 256–512 MB                                  |
| `mapreduce.reduce.shuffle.parallelcopies`                | Parallel fetchers               | 10–50 based on cluster size                 |
| `yarn.nodemanager.vmem-check-enabled`                    | Disable virtual memory checks   | Often set to `false` to avoid memory errors |


### Core Hadoop Configuration (core-site.xml)
| Parameter             | Description            | Recommended Setting            |
| --------------------- | ---------------------- | ------------------------------ |
| `fs.defaultFS`        | Default filesystem URI | `hdfs://<cluster-name>-m:8020` |
| `io.file.buffer.size` | Buffer size for I/O    | `131072` or higher             |
| `hadoop.tmp.dir`      | Temp directory path    | Use fast disk (e.g. local SSD) |


