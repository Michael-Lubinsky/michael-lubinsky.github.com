### MongoDB change stream writes into Azure EventHub.

How to read from Azure EventHub and serialize into 
Azure Data Lake Storage Gen2 (ADLS v2)
with partitioned folders like:
Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/ Rolling file name: events-YYYYMMDD-HH.jsonl 
with 1 json line per event?


### How to serialize periodically  MongoDB change stream into Azure Data Lake Storage Gen2 (ADLS v2) 
with partitioned folders like:

Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/
Rolling file name: events-YYYYMMDD-HH.jsonl
with 1 json line per event

### Gemini

To serialize a MongoDB change stream into Azure Data Lake Storage Gen2 (ADLS v2) with the specified partitioned folder structure, you'll need to create a data pipeline.   
The most common and effective way to do this is by using a combination of **MongoDB connectors**, a **message broker**,
and a **data processing engine**. 
Here's a step-by-step guide on how to set it up:

***

## 1. Capture Changes with a MongoDB Connector

The first step is to capture the change stream events from MongoDB. The most efficient way to do this is by using a **MongoDB connector for a distributed streaming platform**. 

* **Debezium:** This is an open-source distributed platform for change data capture (CDC). Debezium's MongoDB connector captures row-level changes from a MongoDB replica set or sharded cluster and streams them to a message broker.
* **MongoDB Kafka Connector:** This is a dedicated connector for Apache Kafka. It's built specifically to capture change streams and publish them as Kafka topics.

***

## 2. Stream Events to a Message Broker

The change events captured by the connector are then streamed to a **message broker**. This serves as a buffer and provides a reliable way to handle the data before it's written to ADLS v2.

* **Apache Kafka:** Kafka is the industry standard for this type of task. It's a high-throughput, fault-tolerant, and scalable distributed streaming platform. The connector will publish the change events to a specific Kafka topic, with each event being a separate message.
* **Azure Event Hubs:** This is Azure's fully managed equivalent of Kafka. If your infrastructure is already in Azure, using Event Hubs can simplify management and integration.

***

## 3. Process and Land Data to ADLS v2

This is the most critical step, where you consume the messages from the message broker, transform them, and write them to ADLS v2 with the desired partitioning. You can use a few different tools for this:

### Option A: Apache Spark or Flink

This is the most flexible and scalable option. You'll need to write a streaming job that reads from Kafka or Event Hubs.

1.  **Read from the Topic:** The job will read messages from the specified topic, which contain the MongoDB change events.
2.  **Extract and Transform:** You'll need to parse the JSON content of each message to extract the relevant fields, such as the `db`, `collection`, and the `operationTime` or `clusterTime` timestamp.
3.  **Partitioning Logic:** Use the timestamp to calculate the `year`, `month`, `day`, and `hour`. This will dynamically create the correct folder structure.
4.  **Write to ADLS v2:** Use the `spark.sql` or `flink` API to write the data in JSON Line (JSONL) format. The output path should be constructed dynamically based on the partitioning logic: `abfss://<container_name>@<storage_account_name>.dfs.core.windows.net/db/collection/year=YYYY/month=MM/day=DD/hour=HH/`.
5.  **Rolling File:** The Spark or Flink job can be configured to write files on a time basis (e.g., every hour) to create the `events-YYYYMMDD-HH.jsonl` files.

### Option B: Azure Data Factory (ADF)

If you prefer a low-code/no-code approach, you can use Azure Data Factory, though it may be less flexible for real-time streaming.

1.  **Trigger:** Use a tumbling window trigger to run the pipeline at a set interval (e.g., every hour).
2.  **Source:** The source will be your Kafka or Event Hubs topic.
3.  **Data Flow:** Use a Data Flow activity to consume the events. In the data flow:
    * **Parse JSON:** Parse the incoming JSON message.
    * **Derived Column:** Use derived columns to extract the date parts (`YYYY`, `MM`, `DD`, `HH`) from the timestamp field.
    * **Sink:** The sink will be your ADLS v2. Configure the sink to use the derived columns for the file path partitioning.
4.  **Partitioning:** ADF's sink settings allow you to specify dynamic content for the folder path. You can use expressions like `@formatDateTime(item().timestamp, 'yyyy/MM/dd/HH')` to create the partitioned folders automatically.

### Option C: Azure Functions

For a more custom, lightweight solution, you could write an Azure Function.

1.  **Trigger:** The function would be triggered by new messages on Event Hubs or Kafka.
2.  **Logic:** The function would consume the message, parse the JSON, and use the Azure Storage SDK to write the data to a blob in ADLS v2.
3.  **Path Construction:** The code would dynamically construct the full blob path with the partitioned folders and the rolling filename. 

***

## Summary of the Data Flow

1.  **MongoDB** captures changes.
2.  A **Debezium/MongoDB Connector** reads these changes.
3.  The connector publishes the changes to a **Kafka/Event Hubs topic**.
4.  A **Spark/Flink job**, **ADF pipeline**, or **Azure Function** consumes the topic.
5.  The processing job transforms the data and constructs the dynamic path.
6.  The data is written to **ADLS v2** in the specified partitioned folders with the JSONL format.

This architecture ensures a scalable, reliable, and fault-tolerant way to serialize your MongoDB change stream data to ADLS v2.

###
This code sets up a listener for MongoDB change events and writes them to ADLS v2.   
The script uses a helper function to dynamically generate the correct partition path and filename based on the current date and time.  
It then uses the @azure/storage-file-datalake SDK to append each JSON-formatted event to the appropriate file.

For this to work, you'll need to set the required environment variables (MONGO_URI, AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY,  
and ADLS_CONTAINER_NAME) for your specific setup.

You can modify this code to handle more complex scenarios, like adding retry logic for failed writes or using a different partitioning scheme.

```js
// Install these packages with: npm install mongodb @azure/storage-file-datalake
const { MongoClient } = require('mongodb');
const { DataLakeServiceClient } = require('@azure/storage-file-datalake');

// =================================================================================================
// Configuration - Use environment variables for production secrets!
// =================================================================================================

const mongoUri = process.env.MONGO_URI || 'mongodb://localhost:27017';
const azureStorageAccountName = process.env.AZURE_STORAGE_ACCOUNT_NAME || 'your-adls-account-name';
const azureStorageAccountKey = process.env.AZURE_STORAGE_ACCOUNT_KEY || 'your-adls-account-key';
const adlsContainerName = process.env.ADLS_CONTAINER_NAME || 'mongo-changes';
const dbName = 'your_database';
const collectionName = 'your_collection';

const adlsConnectionString = `DefaultEndpointsProtocol=https;AccountName=${azureStorageAccountName};AccountKey=${azureStorageAccountKey};EndpointSuffix=core.windows.net`;

// =================================================================================================
// Helper function to get a date-based partition path and file name
// =================================================================================================

function getPartitionPathAndFilename() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');

    // Create the directory path for the current hour
    const partitionPath = `${dbName}/${collectionName}/year=${year}/month=${month}/day=${day}/hour=${hour}`;
    
    // Create the rolling filename for the current hour
    const fileName = `events-${year}${month}${day}-${hour}.jsonl`;

    return { partitionPath, fileName };
}

// =================================================================================================
// Main function to connect and start the change stream
// =================================================================================================

async function startChangeStream() {
    let mongoClient;
    let adlsClient;
    
    try {
        // --- 1. Connect to Azure Data Lake Storage Gen2 ---
        adlsClient = DataLakeServiceClient.fromConnectionString(adlsConnectionString);
        const fileSystemClient = adlsClient.getFileSystemClient(adlsContainerName);
        
        console.log('Successfully connected to Azure ADLS Gen2 container.');

        // --- 2. Connect to MongoDB ---
        mongoClient = new MongoClient(mongoUri);
        await mongoClient.connect();
        const db = mongoClient.db(dbName);
        const collection = db.collection(collectionName);
        
        console.log('Successfully connected to MongoDB.');
        
        // --- 3. Subscribe to the change stream ---
        // Use a full document pre-image and post-image to get the entire document state
        // before and after the change. This is only available for some change types.
        const changeStream = collection.watch([], {
            fullDocument: 'updateLookup'
        });
        
        console.log(`Watching for changes on ${dbName}.${collectionName}...`);

        // --- 4. Listen for change events ---
        changeStream.on('change', async (change) => {
            try {
                // Get the path and filename for the current hour
                const { partitionPath, fileName } = getPartitionPathAndFilename();
                
                // Get a reference to the directory client
                const directoryClient = fileSystemClient.getDirectoryClient(partitionPath);
                
                // Create the directory if it doesn't exist
                await directoryClient.createIfNotExists();
                
                // Get a reference to the rolling file
                const fileClient = directoryClient.getFileClient(fileName);

                // Check if the file exists before appending
                // Note: The append API can create the file, but this is a good practice.
                try {
                    await fileClient.getProperties();
                } catch (error) {
                    if (error.statusCode === 404) {
                        await fileClient.create();
                    }
                }
                
                // Convert the change event object to a JSON line
                const eventJson = JSON.stringify(change) + '\n';
                const eventBuffer = Buffer.from(eventJson, 'utf-8');
                
                // Get the current file size to know where to append
                const fileSize = (await fileClient.getProperties()).contentLength;
                
                // Append the event data to the rolling file
                await fileClient.append(eventBuffer, fileSize, eventBuffer.length);
                
                // Flush the appended data to commit it to the file
                await fileClient.flush(fileSize + eventBuffer.length);
                
                console.log(`Change event written to: ${partitionPath}/${fileName}`);

            } catch (adlsError) {
                console.error('Error writing to Azure Data Lake Storage:', adlsError.message);
                // In a production environment, you would add retry logic here.
            }
        });
        
        changeStream.on('error', (err) => {
            console.error('Change stream error:', err);
        });

        // Keep the process alive
        await new Promise(() => {});

    } catch (error) {
        console.error('An error occurred:', error);
    } finally {
        // Graceful shutdown
        process.on('SIGINT', async () => {
            console.log('\nShutting down...');
            if (mongoClient) {
                await mongoClient.close();
                console.log('MongoDB client closed.');
            }
            // ADLS client doesn't need to be explicitly closed
            process.exit(0);
        });
    }
}

// Start the application
startChangeStream();

```

### Ingest  into Snowflake bronze layer. 
It connects to both Azure and Snowflake, and uses Snowflake's PUT and COPY INTO commands for efficient bulk loading. The table is created with a single VARIANT column to hold the raw JSON, which is a common practice for a bronze layer to preserve the original data.

You can set this script to run on an hourly schedule using a task scheduler like cron on a virtual machine, a service like Azure Functions, or a workflow orchestrator like Apache Airflow. 
```python
# Install these packages with: pip install azure-storage-file-datalake snowflake-connector-python
import os
import io
import json
from datetime import datetime, timedelta
from azure.storage.filedatalake import DataLakeServiceClient
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

# =================================================================================================
# Configuration - Use environment variables for production secrets!
# =================================================================================================
# Azure ADLS Gen2 Configuration
AZURE_STORAGE_ACCOUNT_NAME = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'your-adls-account-name')
AZURE_STORAGE_ACCOUNT_KEY = os.getenv('AZURE_STORAGE_ACCOUNT_KEY', 'your-adls-account-key')
ADLS_CONTAINER_NAME = os.getenv('ADLS_CONTAINER_NAME', 'mongo-changes')

# Snowflake Configuration
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT', 'your-snowflake-account')
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER', 'your-snowflake-user')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD', 'your-snowflake-password')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE', 'your-snowflake-warehouse')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE', 'your-snowflake-database')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA', 'public')

# MongoDB configuration used for pathing
DB_NAME = 'your_database'
COLLECTION_NAME = 'your_collection'
SNOWFLAKE_TABLE_NAME = COLLECTION_NAME.upper()  # Use uppercase for Snowflake table name convention

# =================================================================================================
# Main script to connect and orchestrate the ingestion
# =================================================================================================

def create_adls_client():
    """Initializes and returns an Azure Data Lake Service Client."""
    try:
        service_client = DataLakeServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net",
            credential=AZURE_STORAGE_ACCOUNT_KEY
        )
        return service_client
    except Exception as e:
        print(f"Error creating ADLS client: {e}")
        return None

def create_snowflake_connection():
    """Initializes and returns a Snowflake connection."""
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        return conn
    except Exception as e:
        print(f"Error creating Snowflake connection: {e}")
        return None

def get_hourly_path(date_time):
    """Constructs the ADLS path for a given date and time."""
    year = date_time.strftime('%Y')
    month = date_time.strftime('%m')
    day = date_time.strftime('%d')
    hour = date_time.strftime('%H')
    return f"{DB_NAME}/{COLLECTION_NAME}/year={year}/month={month}/day={day}/hour={hour}/"

def process_and_load_hourly_data():
    """
    Processes files from ADLS for the previous hour and loads them into Snowflake.
    This is designed to be run on the hour (e.g., at 10:00 AM) to process the 9:00 AM - 9:59 AM data.
    """
    adls_client = create_adls_client()
    if not adls_client:
        return

    snowflake_conn = create_snowflake_connection()
    if not snowflake_conn:
        return

    try:
        # We process the PREVIOUS hour to ensure the file is complete
        now = datetime.utcnow()
        target_time = now - timedelta(hours=1)

        print(f"Processing data for hour: {target_time.strftime('%Y-%m-%d %H:00')}")

        directory_path = get_hourly_path(target_time)
        file_name = f"events-{target_time.strftime('%Y%m%d-%H')}.jsonl"

        file_system_client = adls_client.get_file_system_client(ADLS_CONTAINER_NAME)
        directory_client = file_system_client.get_directory_client(directory_path)
        file_client = directory_client.get_file_client(file_name)

        if not file_client.exists():
            print(f"No file found at {directory_path}{file_name}. Skipping...")
            return

        print(f"File found: {directory_path}{file_name}. Downloading...")
        
        # Download the file content
        downloaded_file = file_client.download_file()
        file_content = downloaded_file.readall()
        
        # Create a temporary stage in Snowflake to upload the file
        with snowflake_conn.cursor() as cur:
            # Create a temporary internal stage
            stage_name = f"TEMP_MONGO_LOAD_STAGE_{int(datetime.now().timestamp())}"
            cur.execute(f"CREATE TEMPORARY STAGE {stage_name};")
            
            # Create the table if it doesn't exist
            # Assuming a simple structure for the bronze layer: one column for the raw JSON
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {SNOWFLAKE_TABLE_NAME} (
                RAW_JSON VARIANT
            );
            """
            cur.execute(create_table_sql)

            # Upload the file content to the temporary stage
            with io.BytesIO(file_content) as file_stream:
                cur.execute(f"PUT file://{file_stream} @{stage_name}/{file_name}")

            # Copy data from the staged file into the table
            copy_into_sql = f"""
            COPY INTO {SNOWFLAKE_TABLE_NAME}
            FROM (SELECT T.$1 FROM @{stage_name}/{file_name} T)
            FILE_FORMAT = (TYPE = 'JSON' STRIP_OUTER_ARRAY = FALSE)
            ON_ERROR = 'CONTINUE';
            """
            cur.execute(copy_into_sql)
            
            print(f"Successfully loaded data from {file_name} into Snowflake table {SNOWFLAKE_TABLE_NAME}.")

    except Exception as e:
        print(f"An error occurred during the load process: {e}")
    finally:
        if snowflake_conn:
            snowflake_conn.close()
            print("Snowflake connection closed.")

if __name__ == '__main__':
    process_and_load_hourly_data()
```
## Snowflake script that creates a silver layer table and a periodic task to load data from the bronze layer. 
This script uses a STREAM to efficiently capture new changes from the bronze table, ensuring you only process the data that has been added since the last run.
This script demonstrates how to set up a robust, idempotent process for moving data from a raw bronze layer to a structured silver layer in Snowflake. The MERGE statement is crucial here as it allows you to handle insert, update, and delete operations from the MongoDB change stream correctly.

```sql
-- =================================================================================================
-- Prerequisites
-- 1. Ensure you are in the correct database and schema.
--    USE DATABASE YOUR_SNOWFLAKE_DATABASE;
--    USE SCHEMA PUBLIC;
-- 2. Grant USAGE on the database and schema, and CREATE TABLE and CREATE TASK on the schema
--    to the role that will execute this task.
-- =================================================================================================


-- Step 1: Create the silver layer table
-- This table will have a defined schema, extracting specific attributes from the JSON.
-- We are using the 'your_collection' name from the previous example.
CREATE TABLE IF NOT EXISTS YOUR_COLLECTION_SILVER (
    MONGO_ID        VARCHAR,
    OPERATION_TYPE  VARCHAR,
    FULL_DOCUMENT   VARIANT,  -- Keeping the full document is often useful for debugging
    SOME_FIELD_1    VARCHAR,  -- Example of a specific field from the document
    ANOTHER_FIELD   NUMBER,   -- Another example
    METADATA_LOADED_AT TIMESTAMP_NTZ(9)
);

-- Step 2: Create a stream on the bronze table
-- A stream captures CDC-like changes on a source table, allowing the task to
-- only process new or changed records since the last query.
CREATE OR REPLACE STREAM YOUR_COLLECTION_BRONZE_STREAM ON TABLE YOUR_COLLECTION;

-- Step 3: Create the periodic task
-- This task will run on a schedule (e.g., every hour) to process the stream
-- and merge the data into the silver table.
-- The SCHEDULE parameter uses a cron-like syntax.
CREATE OR REPLACE TASK LOAD_SILVER_FROM_BRONZE
    WAREHOUSE = YOUR_SNOWFLAKE_WAREHOUSE
    SCHEDULE = 'USING CRON 0 * * * * UTC' -- Run every hour at the top of the hour (e.g., 10:00, 11:00, etc.)
    WHEN SYSTEM$STREAM_HAS_DATA('YOUR_COLLECTION_BRONZE_STREAM')
AS
BEGIN
    -- Merge data from the bronze stream into the silver table.
    -- This statement handles inserts and updates based on the MongoDB _id.
    MERGE INTO YOUR_COLLECTION_SILVER AS T
    USING (
        SELECT
            RAW_JSON:fullDocument:_id::VARCHAR AS MONGO_ID,
            RAW_JSON:operationType::VARCHAR AS OPERATION_TYPE,
            RAW_JSON:fullDocument AS FULL_DOCUMENT,
            RAW_JSON:fullDocument:some_field_1::VARCHAR AS SOME_FIELD_1,
            RAW_JSON:fullDocument:another_field::NUMBER AS ANOTHER_FIELD,
            CURRENT_TIMESTAMP() AS METADATA_LOADED_AT
        FROM YOUR_COLLECTION_BRONZE_STREAM
    ) AS S
    ON T.MONGO_ID = S.MONGO_ID
    WHEN MATCHED AND S.OPERATION_TYPE = 'delete' THEN
        -- If the operation is a delete, delete the record from the silver table.
        DELETE
    WHEN MATCHED AND S.OPERATION_TYPE = 'update' THEN
        -- If the operation is an update, update the record.
        UPDATE SET
            T.FULL_DOCUMENT = S.FULL_DOCUMENT,
            T.SOME_FIELD_1 = S.SOME_FIELD_1,
            T.ANOTHER_FIELD = S.ANOTHER_FIELD,
            T.METADATA_LOADED_AT = S.METADATA_LOADED_AT
    WHEN NOT MATCHED AND S.OPERATION_TYPE IN ('insert', 'update') THEN
        -- If the record is new (and not a delete), insert it.
        INSERT (MONGO_ID, OPERATION_TYPE, FULL_DOCUMENT, SOME_FIELD_1, ANOTHER_FIELD, METADATA_LOADED_AT)
        VALUES (S.MONGO_ID, S.OPERATION_TYPE, S.FULL_DOCUMENT, S.SOME_FIELD_1, S.ANOTHER_FIELD, S.METADATA_LOADED_AT);
END;

-- Step 4: Resume the task to activate it
-- The task is initially suspended after creation. This command starts it.
ALTER TASK LOAD_SILVER_FROM_BRONZE RESUME;
```
The Potential for "Out of Sync"
This staggered scheduling and batch processing introduces latency, but not necessarily an "out of sync" problem that results in lost or incorrect data.

The biggest risk is a race condition if the schedules are not properly staggered. For example, if the Python script starts at 10:00 AM to read the 9:00 AM hour's file, and the Node.js application is still writing a late event for 9:00 AM, the Python script might read an incomplete file.

The key to a robust pipeline is to build in a buffer between each stage. A good schedule would look like this:

Node.js: Continuously writes to the file for the current hour (e.g., events-20231027-10.jsonl).

Python Script: Runs at 10:05 AM to process the file from the previous hour (events-20231027-09.jsonl), giving the Node.js app a few minutes to finalize that file and start the next one.

Snowflake Task: The task's SCHEDULE and WHEN clause ensure that it runs at 10:10 AM (or a similar time after the load) and will only process new data that has arrived from the Python script.

