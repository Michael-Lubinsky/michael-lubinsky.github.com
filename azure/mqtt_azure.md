# Azure event hubs


https://learn.microsoft.com/en-us/azure/event-hubs/

https://azure.microsoft.com/en-us/products/event-hubs

Event Hubs is a managed, real-time data ingestion service that's used to stream millions of events per second from any source to build dynamic data pipelines and respond to business challenges.

Where is Azure Event Hub data stored?  
Event Hubs Capture enables you to automatically capture the streaming data in Event Hubs  
and save it to your choice of either a Blob storage account, or an Azure Data Lake Storage account. 

Data Lake Storage Gen2 extends Azure Blob Storage capabilities and is optimized for analytics workloads.   


## Streaming to Postgres

Streaming data from an Azure source to a PostgreSQL database can be achieved using various Azure services. Here are some common approaches:

### 1. Azure Stream Analytics:
Real-time Processing:
.
Azure Stream Analytics is a fully managed, real-time analytics service designed for processing large volumes of streaming data.
Data Ingestion:
.
You can configure an Azure Stream Analytics job to ingest data from various sources like Azure Event Hubs, Azure IoT Hub, or Azure Blob Storage.
Output to PostgreSQL:
.
The processed data can then be routed as an output to an Azure Database for PostgreSQL instance. This involves defining the output sink within your Stream Analytics job and mapping the fields to your PostgreSQL table schema.
### 2. Azure Data Factory with Streaming Datasets:
Orchestration and Transformation:
Azure Data Factory (ADF) can be used to orchestrate data movement and transformations.
Streaming Datasets:
While not strictly "streaming" in the real-time sense of Stream Analytics, ADF can handle continuous data ingestion and processing by using triggers and tumbling windows to process data incrementally.
Copy Activity:
You can use the Copy Data activity in ADF to move data from various Azure sources (e.g., Azure Blob Storage, Azure Data Lake Storage) to an Azure Database for PostgreSQL.
### 3. Azure Event Hubs and Custom Application Logic:
Event Ingestion:
Azure Event Hubs can act as a highly scalable event ingestion service for capturing real-time data streams.
Custom Application:
You can develop a custom application (e.g., using Azure Functions, Azure WebJobs, or a dedicated virtual machine) to consume events from Event Hubs.
PostgreSQL Write:
This application would then process the events and write them to your Azure Database for PostgreSQL instance using a PostgreSQL client library (e.g., Npgsql for .NET).
### 4. Azure Databricks with Structured Streaming:
Big Data Processing:
.
Azure Databricks provides a powerful platform for big data analytics and machine learning.
Structured Streaming:
.
Databricks' Structured Streaming allows you to process real-time data streams from various sources (e.g., Kafka, Azure Event Hubs) and write them to a PostgreSQL database using JDBC or other connectors.

# MQTT Azure Snowflake

https://www.snowflake.com/en/fundamentals/extracting-insights-from-ioT-data/


https://www.striim.com/integrations/mqtt-azure-sql-database/

https://quickstarts.snowflake.com/guide/getting_started_with_snowpipe_streaming_azure_eventhubs/index.html

