<https://blog.det.life/stop-using-the-console-how-i-manage-aws-s3-faster-with-just-the-cli-218101c555b5>

<https://docs.getmoto.org/en/latest/index.html>

<https://caylent.com/blog/mocking-aws-calls-using-moto>

<https://aws.amazon.com/blogs/devops/unit-testing-aws-lambda-with-python-and-mock-aws-services/>

## What is a difference between Amanon SQS queue and Kafka?

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




**comparison of AWS (Amazon Web Services) vs GCP (Google Cloud Platform)** across key dimensions, from pricing and services to ease of use and ecosystem:

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

 
**BigQuery** is **Google Cloud Platform’s (GCP)** **fully-managed, serverless data warehouse** designed for fast SQL analytics on large-scale datasets.

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

Aspect | **BigQuery**| **Redshift**
|--------|------------|---------------|
| **Query Engine** | Dremel-based, columnar | PostgreSQL-based MPP, columnar 
| **Concurrency** | High, auto-managed | Limited; concurrency scaling helps
| **Indexing** | No indexes; uses partitions and clustering | Uses sort keys and distribution keys

✅ **Advantage**:

-   **BigQuery**: Better at massive, ad hoc queries without tuning.
    
-   **Redshift**: Faster if **tuned** for known workloads.
    

* * *

### 💲 **3\. Pricing Model**

Category | **BigQuery** | **Redshift**
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

Feature | **BigQuery** | **Redshift**|
|--------|------------|---------------|
| **Best with**| GCP services (Dataflow, Pub/Sub, Looker, Vertex AI) | AWS ecosystem (S3, Glue, QuickSight, SageMaker)
| **External Sources** | Federated queries (GCS, Sheets, Cloud SQL)| Federated queries (S3, Aurora, RDS)
| **BI Tool Support** | Excellent (Looker, Tableau, Power BI) | Excellent (QuickSight, Tableau, Power BI)

✅ **Both** integrate well with major BI tools, but are more seamless within their native cloud ecosystems.

* * *

### 🤖 **5\. ML & AI Integration**

Feature | **BigQuery** | **Redshift**
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

Feature | **BigQuery** | **Amazon Redshift** |
|--------|------------|---------------|
| **Architecture** | Serverless |  Managed cluster-based 
| **Cost Efficiency** | Best for bursty / sporadic usage | Best for steady-state usage
| **ML Integration** | Built-in (BigQuery ML) | External (SageMaker) |**Performance Optimization** | Automatic | Manual (keys, distribution)
| **User Experience** | Simple & fast | More control, more complexity


### AWS Links

https://www.vldb.org/pvldb/vol16/p3557-saxena.pdf  Amazon Glue paper


https://www.pluralsight.com/resources/blog/cloud/which-aws-certification-should-i-take

AWS S3 explained: https://medium.com/@joudwawad/aws-s3-deep-dive-1c19ad58af40

https://habr.com/ru/companies/runity/articles/898710/

https://github.com/lusingander/stu S3 explorer


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
 
*Some resources will incur costs so make sure you manage that and terminate when you conclude your work. 
 
  AWS Cloud & Tech Journey: https://lnkd.in/gVKek9iG

  
