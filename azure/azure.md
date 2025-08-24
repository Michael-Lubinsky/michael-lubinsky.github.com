## Microsoft Azure Cloud Platform

CLI

<https://learn.microsoft.com/en-us/cli/azure/?view=azure-cli-latest>


<https://learn.microsoft.com/en-us/azure>

<https://learn.microsoft.com/en-us/training/browse/>

<https://learn.microsoft.com/en-us/collections/7ppetn16mm3r3e>

<https://learn.microsoft.com/en-us/training/support/faq?pivots=sandbox>

<https://topmate.io/asheesh/921914>

<https://medium.com/@kazarmax/from-api-to-dashboard-building-an-end-to-end-etl-pipeline-with-azure-9b498daa2ef6>

<https://medium.com/@connect.hashblock/i-built-a-fastapi-system-that-handled-1-billion-events-per-day-heres-the-architecture-c73fb7dd7eb1>
 
Azure is cloud computing platform offering hundreds of services for infrastructure, application development, data, AI, networking, and more.

🔧 Key Features:
Infrastructure as a Service (IaaS) – Virtual Machines, networking  
Platform as a Service (PaaS) – Web Apps, Azure SQL, Kubernetes  
Data services – Azure Data Lake, Azure Synapse, Cosmos DB  
AI and ML – Azure OpenAI, Azure ML  
DevOps – GitHub Actions, Azure DevOps Pipelines  
Identity – Azure AD (now Microsoft Entra ID)  


### Azure Event Hubs

<https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features?WT.mc_id=Portal-Microsoft_Azure_EventHub>

#### Event retention

Published events are removed from an event hub based on a configurable, timed-based retention policy. Here are a few important points:
- The default value and shortest possible retention period is 1 hour.  
- For Event Hubs Standard, the maximum retention period is 7 days.  
- For Event Hubs Premium and Dedicated, the maximum retention period is 90 days.  

If you need to archive events beyond the allowed retention period, you can have them automatically stored in Azure Storage or Azure Data Lake by turning on the Event Hubs Capture feature.

Event Hubs Capture enables you to automatically capture the streaming data in Event Hubs and save it to your choice of either a Blob storage account, or an Azure Data Lake Storage account.   
You can enable capture from the Azure portal, and specify a minimum size and time window to perform the capture.   
Using Event Hubs Capture, you specify your own Azure Blob Storage account and container, or Azure Data Lake Storage account, one of which is used to store the captured data.  
Captured data is written in the Apache Avro format.

#### Mapping of events to partitions

Specifying a partition key enables keeping related events together in the same partition and in the exact order in which they arrived.   
The partition key is some string that is derived from your application context and identifies the interrelationship of the events.  


#### Checkpointing

Checkpointing is a process by which readers mark or commit their position within a partition event sequence.   
Checkpointing is the responsibility of the consumer and occurs on a per-partition basis within a consumer group.  
This responsibility means that for each consumer group, each partition reader must keep track of its current position in the event stream, and can inform the service when it considers the data stream complete.
If a reader disconnects from a partition, when it reconnects it begins reading at the checkpoint that was previously submitted by the last reader of that partition in that consumer group. 
When the reader connects, it passes the offset to the event hub to specify the location at which to start reading. In this way, you can use checkpointing to both mark events as "complete" by downstream applications, and to provide resiliency if a failover between readers running on different machines occurs.  
It's possible to return to older data by specifying a lower offset from this checkpointing process. Through this mechanism, checkpointing enables both failover resiliency and event stream replay.

#### Send events to or receive events from event hubs by using JavaScript
<https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-node-get-started-send?tabs=passwordless%2Croles-azure-portal>

### 1. Azure Blob Storage

Azure Data Lake Storage Gen2 (ADLS Gen2) 

<https://learn.microsoft.com/en-us/azure/data-factory/connector-azure-data-lake-storage?tabs=data-factory>

<https://azure.github.io/Storage/docs/analytics/hitchhikers-guide-to-the-datalake/>



#### Is StorageV2 the same as ADLS Gen2?
```
Not automatically.

ADLS Gen2 (Azure Data Lake Storage Gen2) is not a separate account kind.

It is a set of hierarchical namespace (HNS) features you enable on top of a StorageV2 account.

In other words:

All ADLS Gen2 accounts are StorageV2.
But not all StorageV2 accounts are ADLS Gen2.
You only get true ADLS Gen2 capabilities (like Hadoop-compatible file system, directories, ACLs) if the Hierarchical Namespace setting is enabled.

3. How to check if your StorageV2 account is ADLS Gen2?
- Go to your storage account in the portal.
- Under Data storage → Containers, try to create a file system.
- Or, in Configuration, check if Hierarchical namespace = Enabled.

If enabled, then it’s ADLS Gen2. If not, then it’s just a regular blob storage account.

✅ Summary:

“Kind = StorageV2” means it’s the right account type to support ADLS Gen2.
To confirm it’s really ADLS Gen2, check if Hierarchical Namespace is enabled in the account configuration.
```

## How to create   **ADLS Gen2 storage account**  in **Azure Portal (Web UI)** by creating a **Storage Account** with *Hierarchical namespace* enabled. 

Here’s a step-by-step:


### 1. Sign in

* Go to [https://portal.azure.com](https://portal.azure.com) and log in.

### 2. Start Storage Account creation

* In the top search bar, type **Storage accounts**.
* Click **+ Create**.


### 3. Basics tab

Fill in the required fields:

* **Subscription** → pick your Azure subscription.
* **Resource group** → select an existing one or click **Create new**.
* **Storage account name** → must be globally unique, lowercase letters and numbers only.
* **Region** → where you want it deployed.
* **Performance** → *Standard* (HDD, cheaper) or *Premium* (SSD, faster).
* **Redundancy** → choose replication option (LRS, ZRS, GRS, RA-GRS).


### 4. Advanced tab (important for ADLS Gen2)

* Scroll to **Data Lake Storage Gen2**.
* **Enable hierarchical namespace** → check this box. ✅
  (This is what makes it ADLS Gen2 instead of just Blob storage.)


### 5. Networking / Data Protection / Tags

* Configure if needed (most defaults are fine for a test).


### 6. Review + Create

* Review settings → click **Create**.
* Deployment takes \~1–2 minutes.


### 7. Verify ADLS Gen2

* After deployment, open the storage account.
* In the left menu, under **Data storage**, you’ll see **Containers** and **Data Lake Gen2 features** (like “File systems”).
* If you see **File systems**, then Hierarchical namespace was enabled and it’s ADLS Gen2.

 

## How to create  ADLS Gen2 storage account  using `az CLI` command**  
(i.e., a Storage Account with **Hierarchical Namespace enabled**):

```bash
# Variables (adjust as needed)
RESOURCE_GROUP=myResourceGroup
LOCATION=eastus
STORAGE_ACCOUNT_NAME=mystorageacct123   # must be globally unique and lowercase

# Create resource group (if not already exists)
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create ADLS Gen2 storage account
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true
```

### Explanation of flags:

* `--kind StorageV2` → ensures it’s the modern type that supports ADLS Gen2.
* `--hierarchical-namespace true` → this enables **Data Lake Gen2** features.
* `--sku Standard_LRS` → local redundant storage (you can change to `Standard_ZRS`, `Standard_GRS`, etc. depending on durability needs).

---

✅ After running this, you’ll have an ADLS Gen2 storage account ready.
You can then create **containers (file systems)** inside it with:

```bash
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name mycontainer \
  --auth-mode login
```

 

## ADLS Gen2 on  **Azure Portal (Web UI)**

1. **Search for Storage Accounts** in the top search bar.
2. Click **+ Create**.
3. **Basics tab** → choose subscription, resource group, name, region, redundancy.
4. **Advanced tab** → enable **Hierarchical namespace** ✅ (this makes it ADLS Gen2).
5. **Review + Create** → then click **Create**.
6. After deployment, open the storage account and check for **File systems** under *Data storage* → this confirms ADLS Gen2 is active.

---

## ADLS Gen2 on **Azure CLI**

Here’s the full setup in CLI:

```bash
# Variables
RESOURCE_GROUP=myResourceGroup
LOCATION=eastus
STORAGE_ACCOUNT_NAME=mystorageacct123   # must be globally unique and lowercase

# 1. Create resource group (if not already exists)
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 2. Create ADLS Gen2 storage account
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true

# 3. (Optional) Create a container (file system) inside
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name mycontainer \
  --auth-mode login
```


✅ At this point, whether you used Portal or CLI, you have a working **ADLS Gen2 storage account** with at least one container ready.

You can confirm **Hierarchical Namespace (ADLS Gen2)** is enabled on a storage account using the `az storage account show` command.

Here’s how:

```bash
az storage account show \
  --name mystorageacct123 \
  --resource-group myResourceGroup \
  --query "isHnsEnabled"
```

* If it returns `true` → **Hierarchical namespace is enabled** (this is ADLS Gen2).
* If it returns `false` → it’s just a regular Blob Storage account.

---

For a full property list (so you can see all settings, including replication, SKU, location, etc.):

```bash
az storage account show \
  --name mystorageacct123 \
  --resource-group myResourceGroup \
  --output table
```

You’ll see a column **IsHnsEnabled** → should be `True`. ✅


Once you’ve confirmed **Hierarchical Namespace** is enabled, you can list all containers   
(in ADLS Gen2 they’re called **file systems**) with the CLI:


### **List all containers (file systems)**

```bash
az storage container list \
  --account-name mystorageacct123 \
  --auth-mode login \
  --output table
```

* `--auth-mode login` → uses your Azure login (make sure you did `az login`).
* `--output table` → formats it neatly, showing name, lease status, public access, etc.

Example output:

```
Name        Lease Status    Public Access
----------  --------------  --------------
mycontainer available       None
rawdata     available       None
```

---

### **Alternative (JSON output)**

If you want details (creation time, metadata, etag, etc.):

```bash
az storage container list \
  --account-name mystorageacct123 \
  --auth-mode login \
  --output json
```

---

### **Confirming ADLS Gen2 Structure**

When `isHnsEnabled` is `true` **and** you can see containers via `az storage container list`, that confirms your storage account is an **ADLS Gen2 account**. ✅

---

##  How to **verify and list file systems (containers) in Azure Portal Web UI** for an **ADLS Gen2 storage account**:



### **Steps in Azure Portal**

1. **Go to your Storage Account**

   * In [https://portal.azure.com](https://portal.azure.com), search for **Storage accounts**.
   * Click the name of your ADLS Gen2 storage account (the one you created with hierarchical namespace enabled).

2. **Navigate to Data Storage section**

   * In the left-hand menu, under **Data storage**, click **Containers**.
   * In ADLS Gen2, *containers = file systems*.

3. **View all file systems**

   * You’ll see a list of containers (file systems) that exist in your storage account.
   * Example:

     ```
     Name         Last modified
     -----------  -------------------
     mycontainer  2025-08-24, 10:15 AM
     rawdata      2025-08-24, 10:22 AM
     ```
   * You can click into any of them to browse folders/files (hierarchical because ADLS Gen2 is enabled).

4. **Confirm ADLS Gen2 (Hierarchical Namespace)**

   * Still in the storage account blade, go to **Configuration** (left menu).
   * Look for **Hierarchical namespace** → it should say **Enabled** ✅.

---

So to summarize:

* **Containers** in Portal = **File Systems** in ADLS Gen2.
* **Configuration tab** → check **Hierarchical namespace** is enabled to confirm it’s really Gen2.

---
Here’s how you can **create a new file system (container)** in the **Azure Portal Web UI** for your ADLS Gen2 account:

---

### **Steps in Azure Portal**

1. **Open your Storage Account**

   * Go to [https://portal.azure.com](https://portal.azure.com).
   * Search for **Storage accounts** and click your ADLS Gen2 storage account.

2. **Go to Containers (File Systems)**

   * In the left-hand menu, under **Data storage**, click **Containers**.
   * This shows the list of all existing containers (file systems).

3. **Create a new Container**

   * At the top of the Containers page, click **+ Container**.
   * Fill in details:

     * **Name** → must be lowercase letters, numbers, and hyphens only (e.g., `rawdata`, `bronze-layer`, `2025logs`).
     * **Public access level** → choose:

       * *Private (no anonymous access)* → default, recommended for ADLS Gen2.
       * *Blob* or *Container* if you want anonymous access (rare in ADLS use cases).
     * **Advanced settings** → usually leave defaults.

4. **Click Create**

   * The new container (file system) will now appear in the list.
   * You can click into it to create folders, upload files, etc.

---

### **Verify**

* The new container will be visible immediately in the **Containers** list.
* Since hierarchical namespace is enabled, inside that container you can create a directory tree (folders/subfolders) — unlike classic blob storage where it’s flat.

---

✅ So now you can both **list** all containers and **create new ones** in the same **Containers** page of the storage account in Azure Portal.

---

Would you like me to also show you the **CLI equivalent** (`az storage container create`) alongside the Portal steps, so you have both UI + script methods in one place?

-----
Azure Blog Storage: A scalable object storage service for storing unstructured data like images, videos, CSV files, Parquet files, backups, and logs.

🔹 Key Points:
Ideal for data lakes, backup, and archive.

Stores files in containers.

Supports hot, cool, and archive tiers for cost control.

Used by Azure Synapse, Data Factory, and others as a data source or sink.

🔧 Example use cases:

Storing raw data for analytics

Hosting files for machine learning

Serving images/documents to web apps



Perfect 👍 — here’s a **side-by-side guide** to creating a new **file system (container)** in **Azure Data Lake Storage Gen2**, showing both **Azure Portal UI** and **Azure CLI**:

---

## **Option 1 – Azure Portal (Web UI)**

1. **Open your Storage Account**

   * Log in to [https://portal.azure.com](https://portal.azure.com).
   * Search **Storage accounts** → click your ADLS Gen2 storage account.

2. **Go to Containers**

   * In the left menu, under **Data storage**, click **Containers**.
   * You’ll see the list of existing containers (file systems).

3. **Create New Container**

   * Click **+ Container** (top menu).
   * Enter:

     * **Name** → e.g., `bronze-data` (must be lowercase, no spaces).
     * **Public access level** → choose *Private (default)*.
   * Click **Create**.

✅ Your new container will appear in the list. You can now upload files or create directories inside it.

---

## **Option 2 – Azure CLI**

Equivalent command to create a container (file system):

```bash
# Variables
RESOURCE_GROUP=myResourceGroup
STORAGE_ACCOUNT_NAME=mystorageacct123
CONTAINER_NAME=bronze-data   # must be lowercase

# Create the container
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name $CONTAINER_NAME \
  --auth-mode login
```

* `--auth-mode login` uses your Azure AD login (after `az login`).
* If you want to allow public blob access (not common in ADLS Gen2):

  ```bash
  az storage container create \
    --account-name $STORAGE_ACCOUNT_NAME \
    --name $CONTAINER_NAME \
    --public-access blob \
    --auth-mode login
  ```

---

### **Summary**

* **Portal** → Storage account → **Containers** → **+ Container** → Name → Create.
* **CLI** → `az storage container create ...`.

Both give you a new **ADLS Gen2 file system** that will show up under **Containers** in Portal and via `az storage container list`.

---

👉 Would you like me to also add how to **create a directory (subfolder) inside that container** (Portal + CLI), since that’s the main ADLS Gen2 difference from Blob?





#  2. Azure Logic Apps
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

#   3. Azure Data Factory (ADF)
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

#   4. Azure Synapse Analytics
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

#  5. Azure Purview (now part of Microsoft Purview)
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


# Azure vs AWS vs GCP

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
