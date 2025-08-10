### How to serialize periodically  MongoDB change stream into Azure Data Lake Storage Gen2 (ADLS v2) 
with partitioned folders like:

Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/
Rolling file name: events-YYYYMMDD-HH.jsonl
with 1 json line per event

### Gemini

To serialize a MongoDB change stream into Azure Data Lake Storage Gen2 (ADLS v2) with the specified partitioned folder structure, you'll need to create a data pipeline. The most common and effective way to do this is by using a combination of **MongoDB connectors**, a **message broker**, and a **data processing engine**. Here's a step-by-step guide on how to set it up:

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
