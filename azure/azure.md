## Microsoft Azure Cloud Platform

<https://learn.microsoft.com/en-us/azure>

<https://learn.microsoft.com/en-us/training/browse/>

<https://learn.microsoft.com/en-us/collections/7ppetn16mm3r3e>

<https://learn.microsoft.com/en-us/training/support/faq?pivots=sandbox>

<https://topmate.io/asheesh/921914>

<https://medium.com/@kazarmax/from-api-to-dashboard-building-an-end-to-end-etl-pipeline-with-azure-9b498daa2ef6>
 
Azure is cloud computing platform offering hundreds of services for infrastructure, application development, data, AI, networking, and more.

🔧 Key Features:
Infrastructure as a Service (IaaS) – Virtual Machines, networking  
Platform as a Service (PaaS) – Web Apps, Azure SQL, Kubernetes  
Data services – Azure Data Lake, Azure Synapse, Cosmos DB  
AI and ML – Azure OpenAI, Azure ML  
DevOps – GitHub Actions, Azure DevOps Pipelines  
Identity – Azure AD (now Microsoft Entra ID)  

📌 Azure is a foundational platform for building and running any kind of application or data system in the cloud.


### 1. Azure Blob Storage
What it is:
A scalable object storage service for storing unstructured data like images, videos, CSV files, Parquet files, backups, and logs.

🔹 Key Points:
Ideal for data lakes, backup, and archive.

Stores files in containers.

Supports hot, cool, and archive tiers for cost control.

Used by Azure Synapse, Data Factory, and others as a data source or sink.

🔧 Example use cases:

Storing raw data for analytics

Hosting files for machine learning

Serving images/documents to web apps

### 2. Azure Logic Apps
What it is:
A low-code integration and automation platform to connect apps, data, and services using workflows.

🔹 Key Points:
Trigger-based execution (e.g., when a file arrives, send email).

Pre-built connectors to Office 365, SQL, Salesforce, Twitter, etc.

Uses a visual designer and can embed custom code or Azure Functions.

🔧 Example use cases:

Automatically send alerts when data files land in Blob Storage

Post new SharePoint items to Microsoft Teams

Daily email reports of sales from a SQL database

###  3. Azure Data Factory (ADF)
What it is:
A cloud-based ETL/ELT orchestration tool to move, transform, and load data across systems.

🔹 Key Points:
No-code + code-based data pipelines (via GUI or JSON).

Supports on-premise and cloud data sources.

Can run Spark, SQL, or custom Python scripts.

Integrated with Azure Synapse, Databricks, Snowflake, etc.

🔧 Example use cases:

Pulling data from Oracle DB and transforming it before saving to Blob or Synapse.

Automating daily data refreshes.

Combining multiple CSVs into one Parquet dataset.

###  4. Azure Synapse Analytics
What it is:
A unified data analytics platform that combines data warehousing, big data processing, and data exploration.

🔹 Key Points:
Supports T-SQL queries (dedicated pools) and Spark (serverless pools).

Integrates with Azure Data Lake, Power BI, and ADF.

Can query both structured and unstructured data.

🔧 Example use cases:

Building enterprise data warehouses.

Analyzing big data using Spark notebooks.

Serving BI dashboards via Power BI.

###  5. Azure Purview (now part of Microsoft Purview)
What it is:
A data governance and data catalog service for discovering, classifying, and managing data across your organization.

🔹 Key Points:
Automatically scans data sources to extract metadata.

Builds a data catalog with lineage, classification (e.g., PII, GDPR tags).

Helps govern access, ensure compliance, and understand data usage.

🔧 Example use cases:

Finding all tables containing email addresses.

Tracing where a KPI column originates in a Power BI dashboard.

Cataloging and classifying data across Azure, on-prem, and SaaS systems.

###  How They Work Together (End-to-End Pipeline):
Blob Storage: Raw sales data (CSV, JSON, Parquet) is ingested.

Data Factory: Moves and transforms data into a refined format.

Synapse Analytics: Stores data in a warehouse and enables complex queries and dashboards.

Logic Apps: Sends alerts when data fails or completes loading.

Purview: Scans the entire system to catalog and tag sensitive data.


## 📦 1. **Blob Storage (Azure)** – Object Storage

| Azure              | AWS                   | GCP                        |
|--------------------|------------------------|----------------------------|
| **Azure Blob Storage** | **Amazon S3**             | **Google Cloud Storage (GCS)** |
| Use Case           | Unstructured data storage (files, logs, backups, lake) |

---

## 🔄 2. **Logic Apps (Azure)** – Workflow Automation

| Azure              | AWS                     | GCP                             |
|--------------------|--------------------------|----------------------------------|
| **Azure Logic Apps** | **AWS Step Functions** / **EventBridge** | **Cloud Workflows** / **Cloud Functions + Eventarc** |
| Use Case           | Low-code orchestration of events, APIs, and services |

---

## 🏗 3. **Data Factory (Azure)** – Data Integration & ETL/ELT

| Azure                  | AWS                            | GCP                            |
|------------------------|--------------------------------|--------------------------------|
| **Azure Data Factory** | **AWS Glue** / **Data Pipeline** | **Cloud Dataflow** / **Cloud Composer** |
| Use Case               | Data ingestion, transformation, orchestration |

> 💡 Note: ADF is a visual ETL tool; AWS Glue is more code-heavy; GCP Composer is based on Apache Airflow.

---

## 📊 4. **Synapse Analytics (Azure)** – Data Warehouse + Analytics Engine

| Azure                    | AWS                      | GCP                          |
|--------------------------|--------------------------|------------------------------|
| **Azure Synapse**        | **Amazon Redshift**      | **BigQuery**                 |
| Use Case                 | Analytical queries on structured/unstructured data (lakehouse) |

> 💡 Synapse offers SQL + Spark in one UI. BigQuery is serverless; Redshift is cluster-based.

---

## 🔍 5. **Azure Purview (Microsoft Purview)** – Data Catalog & Governance

| Azure                   | AWS                         | GCP                            |
|-------------------------|------------------------------|---------------------------------|
| **Microsoft Purview**   | **AWS Glue Data Catalog** / **AWS Lake Formation** | **Data Catalog** (now part of **Dataplex**) |
| Use Case                | Metadata management, data lineage, classification |

---

## 🔁 Summary Table

| Capability               | Azure                    | AWS                            | GCP                           |
|--------------------------|--------------------------|--------------------------------|-------------------------------|
| Object Storage           | Blob Storage             | S3                             | Cloud Storage                 |
| Workflow Automation      | Logic Apps               | Step Functions / EventBridge   | Workflows / Eventarc          |
| Data Orchestration/ETL   | Data Factory             | AWS Glue / Data Pipeline       | Dataflow / Composer           |
| Analytics/Warehouse      | Synapse Analytics        | Redshift                       | BigQuery                      |
| Data Governance          | Microsoft Purview        | Glue Catalog / Lake Formation  | Dataplex (w/ Data Catalog)    |


## Microsoft Fabric – Unified Data Analytics Platform
 
A Software-as-a-Service (SaaS) offering built on top of Azure, 
focused on end-to-end data analytics — similar in vision to Databricks Lakehouse or Snowflake.

🧠 Core Capabilities:
Unified platform combining:  
   Data Engineering  
   Data Warehousing  
   Real-time analytics  
   Data Science  
   Business Intelligence (Power BI)  
   OneLake – centralized data lake storage (like Delta Lake or Snowflake)

Native Power BI integration  
Notebook and pipeline authoring (like Azure Synapse or Databricks)  
No-code/low-code experience for analysts and data scientists  

📌 Fabric is targeted at data teams who want to perform analytics, visualization,   
and AI from a unified interface without managing infrastructure.


| Feature             | **Microsoft Azure**                          | **Microsoft Fabric**                        |
| ------------------- | -------------------------------------------- | ------------------------------------------- |
| Type                | Cloud platform (IaaS/PaaS/SaaS)              | Data analytics SaaS platform                |
| Scope               | General-purpose (compute, storage, AI, etc.) | Analytics, BI, data science                 |
| Users               | Developers, IT admins, cloud architects      | Data analysts, scientists, BI professionals |
| Example Services    | Azure VM, Blob Storage, Azure ML, Cosmos DB  | Data Factory, Data Warehouse, Power BI      |
| Storage             | Azure Data Lake, Blob, Files, etc.           | OneLake (unified lake for all workloads)    |
| Infrastructure Mgmt | Requires user setup                          | Fully managed SaaS                          |
| Comparable To       | AWS/GCP                                      | Snowflake, Databricks, Google BigQuery      |


### Fabric vs AWS & GCP – Service-by-Service

| **Microsoft Fabric Service**          | **AWS Equivalent**                          | **GCP Equivalent**                            | **Purpose**                                    |
| ------------------------------------- | ------------------------------------------- | --------------------------------------------- | ---------------------------------------------- |
| **OneLake**                           | Amazon S3 (w/ Lake Formation)               | Cloud Storage (w/ Dataplex)                   | Centralized data lake for all Fabric workloads |
| **Data Engineering**                  | AWS Glue Studio / EMR / SageMaker Studio    | Cloud Dataproc / Dataflow / Notebooks         | Author Spark notebooks, transform large data   |
| **Data Factory (in Fabric)**          | AWS Glue / Step Functions                   | Cloud Dataflow / Cloud Composer               | No-code/low-code data integration pipelines    |
| **Data Science**                      | SageMaker Studio                            | Vertex AI Workbench                           | Train, experiment, and deploy ML models        |
| **Data Warehouse (Warehouse)**        | Amazon Redshift                             | BigQuery                                      | Petabyte-scale analytics SQL engine            |
| **Data Activator** *(event triggers)* | EventBridge + Lambda + Step Functions       | Eventarc + Cloud Functions                    | Event-based orchestration and alerting         |
| **Real-Time Analytics (KQL Engine)**  | Amazon Kinesis Data Analytics + MSK         | Cloud Pub/Sub + Dataflow + BigQuery           | Streaming analytics with low latency           |
| **Power BI (Embedded in Fabric)**     | QuickSight / Amazon Managed Grafana         | Looker / Data Studio (Looker Studio)          | Dashboards, reporting, visualizations          |
| **Fabric Notebooks (Spark-based)**    | EMR Notebooks / SageMaker Studio Notebooks  | Vertex AI Workbench / Dataproc Notebooks      | Python/Spark notebooks for data processing     |
| **Lakehouse (Delta-like)**            | Lake Formation + S3 + Athena/Glue + Iceberg | Dataplex + Cloud Storage + BigQuery + Iceberg | Lake + warehouse hybrid using open formats     |


| Feature               | **Microsoft Fabric**         | **AWS**                      | **GCP**                     |
| --------------------- | ---------------------------- | ---------------------------- | --------------------------- |
| Type                  | Unified SaaS (Lakehouse)     | Modular cloud services       | Modular cloud services      |
| Primary Lake          | OneLake                      | S3 (with Lake Formation)     | Cloud Storage + Dataplex    |
| Data Warehouse        | Fabric Warehouse             | Amazon Redshift              | BigQuery                    |
| Real-time Analytics   | Fabric Real-Time Analytics   | Kinesis, MSK, Lambda, Athena | Pub/Sub, Dataflow, BigQuery |
| Integrated Dashboards | Power BI                     | QuickSight                   | Looker Studio               |
| ML & AI               | Fabric Data Science, Copilot | SageMaker                    | Vertex AI                   |



### Microsoft Fabric Services and Their Equivalents
#### 1. Unified Data Lake & Storage (OneLake)
Microsoft Fabric: OneLake acts as a single, logical, multi-cloud data lake for your entire organization, built on top of Azure Data Lake Storage Gen2. It provides a unified namespace and avoids data duplication.

AWS:
Amazon S3: The primary object storage service, foundational for building data lakes.
AWS Lake Formation: A service that helps you build, secure, and manage your data lake on Amazon S3. It provides centralized access controls and simplifies the process of setting up a secure data lake.

GCP:
Cloud Storage: GCP's highly scalable and durable object storage service, often used as the foundation for data lakes.
Dataplex: A data fabric service that helps you manage, monitor, and govern data across data lakes, data warehouses, and data marts, providing a unified view of your data assets.

#### 2. Data Engineering
Microsoft Fabric: Data Engineering provides a Spark platform for building, managing, and optimizing infrastructures for data collection, storage, processing, and analysis. It integrates with Data Factory for orchestration.

AWS:  
Amazon EMR: A managed cluster platform for running big data frameworks like Apache Spark, Hadoop, Presto, and Flink.
AWS Glue: A serverless data integration service for ETL (Extract, Transform, Load) operations, including data discovery, cataloging, and generating ETL code. It also has a visual data preparation tool (Glue DataBrew).
AWS Data Pipeline: A web service that helps you reliably process and move data between different AWS compute and storage services, as well as on-premises data sources, at specified intervals.

GCP:  
Dataproc: A fully managed service for running Apache Spark, Hadoop, Presto, and other open-source tools.
Dataflow: A fully managed service for executing Apache Beam pipelines for both batch and stream data processing.
Cloud Data Fusion: A fully managed, cloud-native data integration service built on open-source CDAP, offering a graphical interface for building ETL/ELT pipelines.
Cloud Composer: A managed Apache Airflow service for orchestrating complex data workflows.

#### 3. Data Warehousing
Microsoft Fabric: Data Warehouse provides a high-performance SQL data warehouse experience (similar to Azure Synapse Analytics SQL Pool) for analyzing structured and semi-structured data.

AWS:  
Amazon Redshift: A fully managed, petabyte-scale data warehouse service designed for analytics, using columnar storage and parallel processing. Redshift Serverless is also available.

GCP:  
BigQuery: A highly scalable, serverless, and cost-effective enterprise data warehouse designed for analytics. It's known for its ability to run SQL queries on terabytes and petabytes of data in seconds.

#### 4. Data Science
Microsoft Fabric: Data Science enables building, deploying, and operationalizing machine learning models.  
It integrates with Azure Machine Learning for experiment tracking and model registry.

AWS:  
Amazon SageMaker: A fully managed service that provides every developer and data scientist with the ability to build, train, and deploy machine learning models quickly. It includes tools for data preparation, model training, tuning, deployment, and monitoring.
Amazon Rekognition, Amazon Comprehend, Amazon Forecast, etc.: Various pre-trained AI services for specific tasks.

GCP:  
Vertex AI: A unified machine learning platform that combines all of Google Cloud's ML products into a single environment for building, deploying, and scaling ML models. It includes features for data labeling, feature engineering, model training (AutoML and custom), and deployment.
BigQuery ML: Allows users to create and execute machine learning models in BigQuery using standard SQL queries.

#### 5. Real-Time Intelligence / Streaming Analytics
- Microsoft Fabric: Real-Time Intelligence (formerly Real-Time Analytics and Kusto Engine) focuses on ingesting, processing, and analyzing streaming data in near real-time, enabling actions and insights from data in motion. The Real-Time hub provides a unified location for streaming data.

- AWS:  
Amazon Kinesis: A family of services for real-time streaming data, including:
Kinesis Data Streams: For real-time processing of large streams of data.
Kinesis Data Firehose: For loading streaming data into data stores and analytics services.
Kinesis Data Analytics (now Amazon Managed Service for Apache Flink): For real-time analytics on streaming data using SQL or Apache Flink.
Amazon MSK (Managed Streaming for Apache Kafka): A fully managed service for Apache Kafka.

- GCP:  
Cloud Pub/Sub: A real-time messaging service for ingesting and delivering high volumes of events.
Dataflow: (Mentioned under Data Engineering as well) Can be used for stream processing using Apache Beam.
Dataproc: Can run Apache Flink and Spark Streaming for real-time processing.

#### 6. Business Intelligence (BI)
- Microsoft Fabric: Power BI is natively integrated into Fabric for data visualization, reporting, and interactive dashboards. Fabric also includes Copilot for Power BI for AI-enhanced insights.

- AWS:  
Amazon QuickSight: A cloud-native business intelligence service that allows you to create interactive dashboards, perform ad-hoc analysis, and embed visuals into applications.

- GCP:  
Looker: A unified platform for BI, data applications, and embedded analytics (acquired by Google Cloud).
Google Data Studio (Looker Studio): A free, web-based tool for creating customizable reports and dashboards.

#### 7. Data Governance & Cataloging
- Microsoft Fabric: Built-in governance powered by Purview for centralized data discovery, administration, and governance.

- AWS:  
AWS Glue Data Catalog: A centralized metadata repository for data in your data lake and other data sources.
Amazon DataZone: A data management service to make data discoverable and available to business users.

- GCP:  
Data Catalog: A fully managed metadata management service that helps organizations discover, manage, and understand all their data assets.
Dataplex: (Also mentioned under Unified Data Lake) Provides governance and metadata capabilities.

#### 8. Data Integration / Orchestration
- Microsoft Fabric: Data Factory provides data integration capabilities, including over 180 connectors, mirroring for continuous replication, and dataflows for data preparation.

- AWS:  
AWS Glue: (Mentioned under Data Engineering) Its primary function is ETL and data integration.
AWS Step Functions: A serverless workflow service for orchestrating complex distributed applications and data processing pipelines.
Amazon Managed Workflows for Apache Airflow (MWAA):  
A managed service for Apache Airflow, used for orchestrating workflows.
AWS Database Migration Service (DMS): For migrating databases to AWS.

- GCP:  
Cloud Data Fusion: (Mentioned under Data Engineering) For visual ETL/ELT pipeline building.
Cloud Composer: (Mentioned under Data Engineering) For workflow orchestration using Apache Airflow.
Database Migration Service: For migrating databases to Google Cloud.
Microsoft Fabric's key differentiator is the high degree of integration   
and unified experience across these traditionally disparate services, all centered around OneLake.   
While AWS and GCP offer similar functionalities, they typically do so as separate,   
purpose-built services that you integrate yourself,  
providing more granular control but potentially higher complexity.


### Azure Equivalent of Apache Airflow Closest Equivalent:

### 1. **Azure Data Factory (ADF)**
- ADF provides **Pipelines** that orchestrate ETL/ELT workflows.
- Similar to Airflow DAGs for defining sequences of data tasks.
- GUI-based interface instead of code-first.
- Supports scheduling, monitoring, retries, dependencies.

---

## 🔧 Other Alternatives:

### 2. **Azure Synapse Pipelines**
- Built into **Azure Synapse Analytics**.
- Similar to ADF but tightly integrated with Synapse SQL and Spark.

### 3. **Azure Functions + Durable Functions**
- For serverless, code-driven orchestration.
- Durable Functions allow for stateful workflows like Airflow DAGs.
- Best for complex, event-driven control flows.

### 4. **Self-hosted Apache Airflow on Azure**
- Deploy on:
  - **Azure Kubernetes Service (AKS)**
  - **Azure Virtual Machines**
  - **Azure Container Instances** (with Docker)
- Gives you full Airflow flexibility on Azure infrastructure.

---

## 🟦 Managed Airflow on Azure?

Azure **does not** have a native managed Airflow service (unlike GCP's Cloud Composer).  
You can consider third-party managed services like:
- **Astronomer on Azure**
- **Cloud 9 Airflow deployments**

---

## Summary Table

| Feature                  | Apache Airflow        | Azure Equivalent                 |
|--------------------------|------------------------|----------------------------------|
| Workflow orchestration   | Apache Airflow         | Azure Data Fa


### Azure CLI
<https://github.com/Azure/azure-cli/releases>
<https://learn.microsoft.com/en-us/cli/azure/?view=azure-cli-latest>

 https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos?view=azure-cli-latest
 

<https://skphd.medium.com/top-100-azure-data-engineering-interview-questions-and-answers-24a65e8e6866>

<https://www.reddit.com/r/AZURE/comments/1lo4rc9/cloudnetdraw_is_now_a_hosted_tool_automatically/>

<https://artempichugin.com/2025/07/07/a-simple-workbook-to-keep-your-azure-healthy/>
