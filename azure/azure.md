## Microsoft Azure – Cloud Platform

<https://learn.microsoft.com/en-us/azure>
 
A broad, general-purpose cloud computing platform offering hundreds of services for infrastructure, application development, data, AI, networking, and more.

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




<https://github.com/Azure/azure-cli/releases>

<https://skphd.medium.com/top-100-azure-data-engineering-interview-questions-and-answers-24a65e8e6866>
