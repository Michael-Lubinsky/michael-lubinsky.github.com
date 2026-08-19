### AWS
 

## Athena
**Serverless, interactive SQL query engine** for data sitting directly in S3 — no loading, no infrastructure.
- Runs on Presto/Trino under the hood; queries data in-place using schemas registered in the **Glue Data Catalog**.
- Pay per TB scanned (or flat-rate with reserved capacity) — no cluster to provision or pay for when idle.
- Best for: ad-hoc analytics, log analysis, querying data lakes without standing up a warehouse.
- Cost/perf tip: partition your S3 data and use columnar formats (Parquet/ORC) — dramatically cuts bytes scanned and cost.

## RDS (Relational Database Service)
**Managed relational database service** — AWS handles provisioning, patching, backups, and failover for standard SQL engines.
- Supported engines: PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, and **Aurora** (AWS's own MySQL/Postgres-compatible engine with better performance/scaling).
- Handles automated backups, Multi-AZ failover (synchronous standby in another AZ), read replicas for scaling reads, and automated patching.
- **RDS vs. Aurora:** Aurora is AWS's proprietary storage engine (compatible with Postgres/MySQL wire protocol) — faster, auto-scaling storage, more expensive baseline, often the default recommendation now for new builds.
- Given your background with PostgreSQL Flexible Server on Azure — RDS PostgreSQL is the direct AWS equivalent, same idea of managed Postgres with less manual ops.

## Step Functions *(recap — see full comparison above)*
Serverless orchestrator — coordinates multi-step workflows across AWS services (Lambda, Glue, ECS) using state machines defined in Amazon States Language, with built-in retry/error handling and a visual execution graph.

## EventBridge *(recap)*
Serverless event bus — routes events by content-based pattern matching to targets (Lambda, Step Functions, SQS, etc.); also handles scheduled/cron triggers (absorbed the old CloudWatch Events functionality).

## CloudWatch *(recap)*
Core monitoring/observability service — Metrics, Logs (+ Logs Insights for querying), Alarms (threshold or anomaly-based), and Dashboards across your AWS resources and custom app metrics.

## EMR (Elastic MapReduce)
**Managed big-data cluster service** — runs Spark, Hadoop, Hive, Presto, and other big-data frameworks on a cluster you provision (unlike Glue, which is fully serverless).
- You choose instance types, cluster size, and can attach it to S3 (EMRFS) as the storage layer.
- Offers far more configurability/tuning than Glue — custom bootstrap actions, specific Spark configs, long-running or transient clusters.
- **EMR vs. Glue:** Glue = serverless, less config, pay-per-DPU-hour, good for straightforward ETL. EMR = you manage cluster lifecycle/sizing, more knobs to tune, better for heavy/custom big-data workloads or when you need full Hadoop-ecosystem tooling (Hive, HBase, Presto) beyond Spark alone.
- **EMR vs. Databricks** (closer to your daily stack): Databricks is a more polished, managed Spark platform with notebooks, Delta Lake, Unity Catalog, and MLOps tooling built in; EMR is more raw/DIY — cheaper at the infra level but more operational overhead and fewer built-in collaboration/governance features.

## ECS / EKS *(recap)*
Both are container orchestrators. **ECS** is AWS's own simpler, proprietary orchestrator (Fargate for serverless, or EC2-backed) with tight AWS-native integration. **EKS** is managed **Kubernetes** — standard K8s API, more powerful/portable ecosystem, steeper learning curve.

---

**Quick mental map for your stack:** Athena/EMR sit near Glue (data processing/query layer), RDS is your transactional DB layer (parallel to your Postgres/DynamoDB work), Step Functions/EventBridge are the orchestration/event layer, CloudWatch is observability across all of it, and ECS/EKS are for running your own containerized services rather than data pipeline steps.

Here's a realistic pipeline that uses all three together — this is a very common real-world pattern, and a great one to bring up in an interview.

## The Scenario
A CSV file lands in S3 → this should trigger a Glue crawler to catalog it → then a Glue ETL job to clean/transform it → with the whole thing orchestrated and tracked by Step Functions, kicked off by EventBridge.

## How the Three Pieces Connect

```
S3 upload → EventBridge (detects the event) → triggers Step Functions execution
                                                          │
                                    ┌─────────────────────┼─────────────────────┐
                                    ▼                                           ▼
                          Glue Crawler (catalog schema)          Glue ETL Job (transform data)
                                    │                                           │
                                    └─────────────► sequenced by Step Functions ◄┘
```

**Role of each service:**
- **EventBridge** — the trigger/listener. Watches for the S3 "Object Created" event and fires when a new file lands.
- **Step Functions** — the conductor. Defines the sequence: run crawler → wait for it to finish → run ETL job → handle success/failure.
- **Glue** — the actual workers. The crawler infers schema and updates the Data Catalog; the ETL job does the real data transformation (Spark under the hood).

## 1. EventBridge Rule (triggers Step Functions on S3 upload)

```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": { "name": ["my-raw-data-bucket"] },
    "object": { "key": [{ "prefix": "incoming/" }] }
  }
}
```
This rule matches any new object landing under `incoming/` in the bucket, and its target is set to the Step Functions state machine below.

## 2. Step Functions State Machine (orchestrates Glue)

```json
{
  "Comment": "Crawl then transform new S3 data",
  "StartAt": "RunCrawler",
  "States": {
    "RunCrawler": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:glue:startCrawler",
      "Parameters": { "Name": "raw-data-crawler" },
      "Next": "WaitForCrawler"
    },
    "WaitForCrawler": {
      "Type": "Wait",
      "Seconds": 30,
      "Next": "CheckCrawlerStatus"
    },
    "CheckCrawlerStatus": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:glue:getCrawler",
      "Parameters": { "Name": "raw-data-crawler" },
      "Next": "IsCrawlerDone",
      "ResultPath": "$.crawlerStatus"
    },
    "IsCrawlerDone": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.crawlerStatus.Crawler.State",
          "StringEquals": "READY",
          "Next": "RunETLJob"
        }
      ],
      "Default": "WaitForCrawler"
    },
    "RunETLJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": { "JobName": "transform-raw-data" },
      "Next": "Success",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyFailure"
        }
      ]
    },
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:123456789012:pipeline-failures",
        "Message": "Glue ETL job failed"
      },
      "End": true
    },
    "Success": {
      "Type": "Succeed"
    }
  }
}
```

**Notable details worth mentioning in an interview:**
- `startJobRun.sync` is a **`.sync` service integration** — Step Functions natively waits for the Glue job to actually finish (success or failure) rather than just firing-and-forgetting, no manual polling needed.
- The crawler doesn't support `.sync`, so the poll loop (`WaitForCrawler` → `CheckCrawlerStatus` → `IsCrawlerDone`) is a common manual pattern for services without native sync support.
- `Catch` gives you built-in error handling — route failures to an SNS notification without writing custom retry/exception code.

## Why This Combination Is a Good Pattern to Cite

- **Decoupling**: EventBridge means the *producer* (whatever writes to S3) doesn't need to know anything about the pipeline that consumes it — you could add more consumers later without touching the upload process.
- **No idle infrastructure**: everything here — EventBridge, Step Functions, Glue — is serverless. You only pay when a file actually lands and the pipeline runs.
- **Visual debuggability**: Step Functions gives you a graph showing exactly which state ran, how long each took, and where it failed — much easier to debug than chained Lambda functions with custom orchestration logic.

Want me to extend this into a version where a Databricks job (rather than Glue) is the transformation step — closer to your actual day-to-day stack?
 

## Redshift vs Athena

**Redshift** is a **managed data warehouse** — a persistent cluster with its own columnar storage, built for complex, high-performance analytics on data you've loaded *into* it.

**Athena** is a **serverless query engine** — no storage of its own, queries data *in place* in S3.

They connect via **Redshift Spectrum**, a feature that lets Redshift query data directly in S3 (same idea as Athena) *without* loading it into Redshift's local storage first — extending your warehouse queries out to your data lake.

## How Redshift Reads S3 Data (Two Paths)

1. **COPY command** — bulk-loads S3 data *into* Redshift's own storage for fast, repeated querying. This is the traditional warehouse pattern: ETL data in, then query the local copy.
2. **Redshift Spectrum** — queries S3 data *without* loading it, using the same **Glue Data Catalog** that Athena uses for table/schema definitions. Spectrum spins up separate, transient compute (external to your Redshift cluster) just for the S3-scanning portion of a query, then joins the result with data already sitting in Redshift.

## Athena vs. Redshift Spectrum — Nearly the Same Underlying Idea

| | Athena | Redshift Spectrum |
|---|---|---|
| Storage | None — S3 only | Redshift cluster storage + S3 (via Spectrum) |
| Compute | Fully serverless, ephemeral per query | Requires a running Redshift cluster; Spectrum compute is separate/elastic but still tied to that cluster |
| Catalog | Glue Data Catalog | Glue Data Catalog (same catalog!) |
| Billing | Per TB scanned | Cluster hourly cost + per-TB-scanned for the Spectrum portion |
| Best for | Ad-hoc queries, no standing infra | Joining S3 data with existing warehouse tables, BI tool queries needing consistent low latency |

**They can literally query the same S3 table registered in the same Glue Catalog** — the difference is *where the compute lives* and whether you already have a Redshift cluster running.

## Practical Decision

- **No existing warehouse, just want to query S3 data occasionally** → Athena. Zero infra, pay only per query.
- **Already running Redshift, need to join S3 (lake) data with warehouse tables in one query** (e.g., join historical archived data in S3 with recent hot data in Redshift) → Redshift Spectrum.
- **High-frequency, latency-sensitive dashboards** → often worth `COPY`-ing hot data into Redshift proper rather than repeatedly scanning S3 via either Athena or Spectrum — local columnar storage is faster than any external S3 scan.

**One more architectural note relevant to your stack:** since Databricks/Delta Lake also often lands data in S3 with Glue Catalog registration, the same S3 tables can potentially be queried by Databricks, Athena, *and* Redshift Spectrum simultaneously — a common "one copy of data, many query engines" pattern (sometimes called a lakehouse architecture) that avoids duplicating data across systems.


<https://awstip.com/>
<https://www.exampro.co/>

## What is a difference between Amazon SQS queue and Kafka?

Amazon SQS (Simple Queue Service) and **Apache Kafka** are both messaging systems,  
but they serve different purposes and have different architectures.   
Here's a concise comparison:

* * *

### **1\. Purpose & Use Cases**

-   **Amazon SQS**:
    
    -   **Message queue** (point-to-point communication).
        
    -   Designed for **decoupling** components of a distributed system.
        
    -   Common use: triggering background jobs, task queues, simple event-driven workflows.
        
-   **Kafka**:
    
    -   **Distributed event streaming platform** (publish-subscribe model).
        
    -   Designed for **high-throughput, durable event streaming** and real-time analytics.
        
    -   Common use: real-time data pipelines, logs, stream processing, analytics.
        

* * *

### **2\. Message Retention**

-   **SQS**:
    
    -   Default retention up to **14 days** (standard queue).
        
    -   Once a message is consumed and deleted, it's gone.
        
-   **Kafka**:
    
    -   Messages can be retained **for a configured period or size**, regardless of whether they're consumed.
        
    -   Allows **replay** of messages.
        

* * *

### **3\. Ordering**

-   **SQS**:
    
    -   **Standard Queue**: No guaranteed order, possible duplicates.
        
    -   **FIFO Queue**: Guarantees **first-in-first-out** and exactly-once processing (but with lower throughput).
        
-   **Kafka**:
    
    -   Guarantees **ordering within a partition**.
        

* * *

### **4\. Delivery Semantics**

-   **SQS**:
    
    -   **At-least-once** delivery (you may need to handle duplicates).
        
    -   FIFO queues offer **exactly-once** within some constraints.
        
-   **Kafka**:
    
    -   Supports **at-least-once**, **at-most-once**, and with proper setup, **exactly-once** processing.
        

* * *

### **5\. Throughput and Scalability**

-   **SQS**:
    
    -   Highly scalable, **but throughput is lower** than Kafka.
        
    -   AWS manages scaling automatically.
        
-   **Kafka**:
    
    -   Extremely **high throughput**, scalable via partitions and broker nodes.
        
    -   You manage the scaling or use a managed service (e.g., Amazon MSK, Confluent Cloud).
        

* * *

### **6\. Consumer Model**

-   **SQS**:
    
    -   Consumers **pull** messages.
        
    -   Each message is delivered to **one consumer only** (unless using fan-out with SNS).
        
-   **Kafka**:
    
    -   Consumers **pull** messages, but allows **multiple consumers** (consumer groups) to read independently.
        

* * *

### **7\. Durability and Reliability**

-   **SQS**:
    
    -   Durable and reliable as a fully managed AWS service.
        
-   **Kafka**:
    
    -   Durable and fault-tolerant, but requires correct configuration and infrastructure if self-hosted.
        

* * *

### **Summary Table**

| Feature        | Amazon SQS                     | Apache Kafka                   |
| -------------- | ------------------------------ | ------------------------------ |
| Model          | Message Queue (P2P)            | Event Stream (Pub/Sub)         |
| Retention      | Up to 14 days                  | Configurable (time/size based) |
| Ordering       | FIFO or unordered              | Ordered within partition       |
| Delivery       | At-least-once / Exactly-once   | Configurable                   |
| Consumer Model | One message = one consumer     | Multiple consumers possible    |
| Use Case       | Decoupling apps, simple queues | Stream processing, analytics   |

<img width="1024" height="1536" alt="image" src="https://github.com/user-attachments/assets/b0d6a84f-8995-4bb6-8d62-749dbae2ebbd" />


<!--
```
I’m happy to share that I’ve obtained a new certification: AWS Certified Data Engineer – Associate from Amazon Web Services (AWS)!

I worked with a wide range of AWS services throughout this journey, covering everything from data ingestion, transformation, storage, orchestration, to security and monitoring.
Some of the key services I got hands-on with include:

Analytics & Processing:
 Athena for interactive querying, EMR for big data processing with Spark, AWS Glue and Glue DataBrew for ETL and data prep, Redshift for warehousing, Kinesis (both Data Streams and Firehose) and Amazon MSK for streaming data, OpenSearch for search & analytics, and QuickSight for easy data visualization.

Orchestration & Workflow Automation:
 Step Functions, EventBridge, Amazon MWAA (Managed Apache Airflow), and even Lambda triggers to build robust, event-driven pipelines.

Storage & Data Lakes:
 Amazon S3 for scalable storage (with lifecycle policies), S3 Glacier for archiving, EFS and EBS for persistent volumes, and AWS Lake Formation to build and secure data lakes.

Databases:
 RDS and Redshift for relational workloads, DynamoDB for NoSQL, Amazon Keyspaces (Cassandra), DocumentDB (MongoDB-compatible), and even Neptune and MemoryDB for graph and in-memory DB needs.

Compute & Containers:
 Lambda for serverless computing, EC2 for managed compute, ECS and EKS for container orchestration, and AWS SAM for deploying serverless apps.

 Developer Tools & Infrastructure as Code:
 CloudFormation, CDK, CodeCommit, CodeBuild, and CodePipeline helped me practice CI/CD and infrastructure automation.

 Monitoring, Security, and Governance:
 CloudWatch, CloudTrail, and AWS Config for visibility and auditing, IAM for access control, Secrets Manager for credential storage, Macie for PII detection, and KMS for encryption.

 Migration & Integration:
 I also explored AWS DMS and SCT for data migration, Transfer Family and DataSync for moving data in and out of AWS, and AppFlow for SaaS integrations.

```

-->


**Comparison of AWS (Amazon Web Services) vs GCP (Google Cloud Platform)** 
across key dimensions, from pricing and services to ease of use and ecosystem:

* * *

### 🧱 **1\. Core Services and Breadth**

| Feature            | **AWS**                         | **GCP**                                    |
| ------------------ | ------------------------------- | ------------------------------------------ |
| **Compute**        | EC2, Lambda, ECS, EKS, etc.     | Compute Engine, Cloud Functions, GKE       |
| **Storage**        | S3, EBS, EFS                    | Cloud Storage, Persistent Disks, Filestore |
| **Databases**      | RDS, DynamoDB, Aurora, Redshift | Cloud SQL, Firestore, BigQuery, Spanner    |
| **AI/ML Services** | SageMaker, Rekognition, Lex     | Vertex AI, AutoML, TPUs, BigQuery ML       |
| **Big Data**       | EMR, Glue, Redshift             | BigQuery, Dataflow, Dataproc               |


🔸 **Summary**:

-   **AWS** has the **widest service portfolio**, offering mature services in every category.
    
-   **GCP** excels in **data analytics (BigQuery)** and **machine learning**, leveraging Google’s own infrastructure and AI research.
    

* * *

### 💲 **2\. Pricing**

| Area                    | **AWS**                       | **GCP**                                   |
| ----------------------- | ----------------------------- | ----------------------------------------- |
| **Pricing Model**       | Pay-as-you-go, reserved, spot | Pay-as-you-go, sustained-use discounts    |
| **Free Tier**           | Yes, 12-month + always free   | Yes, always free + generous trial credits |
| **Sustained Discounts** | Limited                       | Automatic & more generous                 |
| **Preemptible/Spot**    | Spot Instances                | Preemptible VMs                           |


🔸 **Summary**:

-   **GCP tends to be cheaper**, especially for **long-running workloads** due to automatic **sustained-use discounts**.
    
-   AWS offers more pricing models, but can be harder to estimate.
    

* * *

### 🧠 **3\. Ease of Use**

| Feature              | **AWS**                              | **GCP**                        |
| -------------------- | ------------------------------------ | ------------------------------ |
| **Console UI/UX**    | Functional but complex               | Cleaner and more intuitive     |
| **Learning Curve**   | Steeper (due to size and complexity) | Gentler for beginners          |
| **Docs & Tutorials** | Extensive but sometimes scattered    | Concise and developer-friendly |


🔸 **Summary**:

-   **GCP** has a **more user-friendly interface and experience**, especially for newer developers.
    
-   **AWS** is more enterprise-oriented, offering immense flexibility at the cost of complexity.
    

* * *

### 🌍 **4\. Global Infrastructure**

| Metric             | **AWS**                              | **GCP**                                                   |
| ------------------ | ------------------------------------ | --------------------------------------------------------- |
| **Regions (2024)** | 33+ regions, 100+ AZs                | 40+ regions                                               |
| **Network**        | Excellent, optimized global backbone | Industry-leading backbone (same as Google Search/YouTube) |


🔸 **Summary**:  
Both have strong infrastructure, but **Google’s network performance** 
(e.g. latency and bandwidth) is often superior due to their own global fiber network.

* * *

### 🔐 **5\. Security and Compliance**

| Feature            | **AWS**                   | **GCP**                      |
| ------------------ | ------------------------- | ---------------------------- |
| **Certifications** | Broadest in the market    | Strong but slightly fewer    |
| **Security Tools** | IAM, GuardDuty, Inspector | IAM, Security Command Center |
| **Zero Trust**     | Supported                 | Native with BeyondCorp       |


🔸 **Summary**:  
Both meet high security standards. GCP’s **BeyondCorp** is notable for built-in zero trust architecture.

* * *

### 👥 **6\. Ecosystem & Market Share**

| Factor                       | **AWS**                       | **GCP**                              |
| ---------------------------- | ----------------------------- | ------------------------------------ |
| **Market Share (2024)**      | \~30–32%                      | \~10–12%                             |
| **Community & Integrations** | Largest ecosystem             | Growing rapidly, good OSS support    |
| **Enterprise Adoption**      | Strongest enterprise presence | Popular with data/AI-heavy companies |

 

🔸 **Summary**:

-   **AWS dominates the market** with the largest user and partner ecosystem.
    
-   **GCP appeals strongly to data engineers, AI/ML teams, and startups.**
    

* * *

### 🏁 **Conclusion: Which to Choose?**

| Scenario                                 | Recommended Platform          |
| ---------------------------------------- | ----------------------------- |
| Broad enterprise workloads & flexibility | **AWS**                       |
| Data analytics, ML/AI, or startups       | **GCP**                       |
| Simple pricing and intuitive UX          | **GCP**                       |
| Long-term hybrid cloud / GovCloud        | **AWS**                       |
| Cost-sensitive development               | **GCP (especially BigQuery)** |


**GCP (especially BigQuery)**

 
**BigQuery** is **Google Cloud Platform’s (GCP)** **fully-managed, serverless data warehouse**   
designed for fast SQL analytics on large-scale datasets.

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

* * *

### 💲 **Pricing**

-   **Storage**: ~$0.02/GB/month (for active storage)
    
-   **Query**: ~$5 per TB scanned (first 1 TB/month is free)
    
-   **Streaming inserts**: ~$0.01 per 200 MB
    
-   **Flat-rate pricing**: Available for large, predictable workloads
    

🔸   Use **partitioned** and **clustered tables** to reduce costs by limiting the amount of data scanned.

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
    

* * *

### 🚀 Summary

**BigQuery** is:

> A powerful, SQL-driven analytics engine for massive-scale data — fast, flexible, and managed by Google.

###  The closest **AWS equivalent** to **Google BigQuery** is **Amazon Redshift**.

Here’s a direct, practical comparison between **BigQuery** and **Amazon Redshift**, 
based on core features, performance, pricing, and use cases:

* * *

### 🧱 **1\. Architecture & Management**

|Feature | **BigQuery** | **Amazon Redshift**
|--------|------------|---------------|
| **Type** | Serverless, fully-managed data warehouse | Managed data warehouse (not serverless)
| **Compute/Storage** | Fully separated (decoupled) | Partially decoupled (RA3 nodes separate storage)
| **Scaling** | Auto-scales transparently | Manual or scheduled scaling (Elastic Resize, concurrency scaling)
| **Maintenance** | Zero maintenance by user | Requires some management (node types, vacuum, etc.)

✅ **Advantage**: **BigQuery** for fully serverless architecture — no need to manage clusters.

* * *

### 💾 **2\. Performance & Speed**

| Aspect | **BigQuery**| **Redshift**
|--------|------------|---------------|
| **Query Engine** | Dremel-based, columnar | PostgreSQL-based MPP, columnar 
| **Concurrency** | High, auto-managed | Limited; concurrency scaling helps
| **Indexing** | No indexes; uses partitions and clustering | Uses sort keys and distribution keys

✅ **Advantage**:

-   **BigQuery**: Better at massive, ad hoc queries without tuning.
    
-   **Redshift**: Faster if **tuned** for known workloads.
    

* * *

### 💲 **3\. Pricing Model**

| Category | **BigQuery** | **Redshift**
|--------|------------|---------------|
| **Query** | Pay-per-query ($5/TB scanned) | Pay-per-hour (on-demand), or reserved instance
| **Storage** | ~$0.02/GB/month | ~$0.024/GB/month (RA3 managed storage)
| **Free Tier** | 1 TB queries/month + 10 GB storage | Redshift Serverless free tier (750 hrs/month)
| **Flat Rate Option** | Yes, with slots | Yes (with provisioned or Serverless capacity)

✅ **Advantage**:

-   **BigQuery** is **cheaper for low or unpredictable workloads**.
    
-   **Redshift** is **better for constant, high-throughput workloads** with known usage.
    

* * *

### 🔌 **4\. Ecosystem & Integrations**

| Feature | **BigQuery** | **Redshift**|
|--------|------------|---------------|
| **Best with**| GCP services (Dataflow, Pub/Sub, Looker, Vertex AI) | AWS ecosystem (S3, Glue, QuickSight, SageMaker)
| **External Sources** | Federated queries (GCS, Sheets, Cloud SQL)| Federated queries (S3, Aurora, RDS)
| **BI Tool Support** | Excellent (Looker, Tableau, Power BI) | Excellent (QuickSight, Tableau, Power BI)

✅ **Both** integrate well with major BI tools, but are more seamless within their native cloud ecosystems.

* * *

### 🤖 **5\. ML & AI Integration**

| Feature | **BigQuery** | **Redshift**
|--------|------------|---------------|
| **Built-in ML** | Yes (BigQuery ML — SQL-based ML) | Limited (integrates with SageMaker)
| **AI Features** | Native model training in SQL | External via Redshift ML (calls SageMaker)

✅ **Advantage**: **BigQuery**, for SQL-based machine learning without leaving the warehouse.

* * *

### ✅ **When to Choose What**

| Use Case | Recommended Platform       | 
|----------|--------------------------|
| Ad hoc queries on large datasets |**BigQuery**  |
| Fully serverless, no cluster management| **BigQuery**
| Tight AWS ecosystem integration | **Redshift**
| High concurrency + predictable workloads | **Redshift (with tuning)**
| SQL-based ML modeling | **BigQuery**
| Real-time data ingestion & analysis | **BigQuery**

* * *

### 🏁 Summary

| Feature | **BigQuery** | **Amazon Redshift** |
|--------|------------|---------------|
| **Architecture** | Serverless |  Managed cluster-based |
| **Cost Efficiency** | Best for bursty / sporadic usage | Best for steady-state usage |
| **ML Integration** | Built-in (BigQuery ML) | External (SageMaker) |**Performance Optimization** | Automatic | Manual (keys, distribution) |
| **User Experience** | Simple & fast | More control, more complexity |


### AWS Links

https://blog.dataengineerthings.org/building-an-end-to-end-data-pipeline-on-aws-with-lambda-s3-glue-redshift-and-step-functions-7dec6d794c0a

<https://github.com/lusingander/stu> S3 explorer

<https://habr.com/ru/companies/k2tech/articles/929906/> S3 explained


<https://www.vldb.org/pvldb/vol16/p3557-saxena.pdf>  Amazon Glue paper


<https://www.pluralsight.com/resources/blog/cloud/which-aws-certification-should-i-take>

AWS S3 explained: <https://medium.com/@joudwawad/aws-s3-deep-dive-1c19ad58af40>

<https://habr.com/ru/companies/runity/articles/898710/>




1. Create a Static Website Using Amazon S3 
https://lnkd.in/ggz9MBGD 
 
2. Launch and Configure an EC2 Instance 
https://lnkd.in/g5dxUwsW 
 
3. Set Up an Application Load Balancer 
https://lnkd.in/grzxzCds 
 
4. Implement Auto Scaling 
https://lnkd.in/gi9KS-2N 
 
5. Create a VPC with Public and Private Subnets 
https://lnkd.in/gMzSY9VE 
 
6. Set Up an Amazon RDS Database 
https://lnkd.in/gnAd-pN9 
 
7. Implement an S3 Lifecycle Policy 
https://lnkd.in/ghQpFTcp 
 
8. Set Up CloudFront Distribution 
https://lnkd.in/gxv6p27R 
 
9. Implement IAM Roles and Policies 
https://lnkd.in/gY8dZMbi 
 
10. Set Up a Simple Serverless Application 
https://lnkd.in/ggqBu-Vj 
 

 
<https://blog.det.life/stop-using-the-console-how-i-manage-aws-s3-faster-with-just-the-cli-218101c555b5>

<https://docs.getmoto.org/en/latest/index.html>

<https://caylent.com/blog/mocking-aws-calls-using-moto>


## lambda

<https://habr.com/ru/companies/otus/articles/954920/>

<https://aws.amazon.com/blogs/devops/unit-testing-aws-lambda-with-python-and-mock-aws-services/>

<https://asrathore08.medium.com/running-spark-on-aws-cloud-297f5aed70eb>

<https://medium.com/@data.dev.backyard/data-ingestion-patterns-in-aws-a-practical-guide-234897e9de57>

<https://medium.com/@mayursurani/mastering-aws-data-engineering-the-ultimate-technical-interview-guide-that-will-land-you-your-3365b6947352> 
 
 
  AWS Cloud & Tech Journey: https://lnkd.in/gVKek9iG

  
