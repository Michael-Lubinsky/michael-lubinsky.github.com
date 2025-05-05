## what is a difference between Amanon SQS queue and Kafka?

 

Amazon SQS (Simple Queue Service) and **Apache Kafka** are both messaging systems, but they serve different purposes and have different architectures. Here's a concise comparison:

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

|Feature | Amazon SQS |  Apache Kafka |
|Model  | Message Queue (P2P) | Event Stream (Pub/Sub)

Retention |  Up to 14 days  | Configurable (time/size based)

Ordering | FIFO or unordered | Ordered within partition

Delivery | At-least-once / Exactly-once | Configurable

Consumer Model| One message = one consumer | Multiple consumers possible

Use Case | Decoupling apps, simple queues | Stream processing, analytics



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
### Amazon Glue paper

https://www.vldb.org/pvldb/vol16/p3557-saxena.pdf


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
 
Join 15K+ Navigating Their AWS Cloud & Tech Journey: https://lnkd.in/gVKek9iG
