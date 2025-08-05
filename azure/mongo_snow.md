

### **Overview of Pipelines**
1. **Pipeline #1**: MQTT Broker -> Azure Event Hub -> Mongo -> Postgres (Current)
2. **Pipeline #2**: MQTT Broker -> Azure Event Hub -> (Mongo and Azure Blob Storage) -> Snowflake
3. **Pipeline #3**: MQTT Broker -> Azure Event Hub -> (Mongo and Snowflake)
4. **Pipeline #4**: MQTT Broker -> Azure Event Hub -> Mongo -> Snowflake (New)

---

### **Pipeline #4: MQTT Broker -> Azure Event Hub -> Mongo -> Snowflake**
In this pipeline, data flows from the MQTT Broker to Azure Event Hub, then to MongoDB for operational storage, and subsequently to Snowflake for analytics, replacing Postgres.

**Analysis:**
- **Architecture**: 
  - Sequential flow: Event Hub ingests data, MongoDB stores it operationally, and data is then extracted and loaded into Snowflake for analytics.
  - MongoDB acts as the operational database, while Snowflake serves as the analytical database.
  - Requires an ETL process to move data from MongoDB to Snowflake, similar to Pipeline #1’s Mongo-to-Postgres flow.
- **Performance**: 
  - MongoDB efficiently handles high-throughput, schema-flexible IoT data from Event Hub.
  - Snowflake excels at analytical queries, offering superior performance for large-scale, complex analytics compared to Postgres.
  - The ETL process from MongoDB to Snowflake introduces latency, depending on the frequency (batch vs. near real-time) and complexity of transformations.
- **Cost**: 
  - MongoDB costs depend on the deployment (e.g., Azure Cosmos DB for MongoDB or MongoDB Atlas).
  - Snowflake costs include storage (per TB/month) and compute (credits/hour), which can be optimized with auto-scaling and auto-suspend.
  - ETL processes (e.g., using Azure Data Factory) add compute and data movement costs, similar to Pipeline #1.
  - Compared to Pipeline #1, replacing Postgres with Snowflake may increase costs due to Snowflake’s pricing model but eliminates Postgres-related costs.
- **Scalability**: 
  - MongoDB scales horizontally for write-heavy IoT workloads.
  - Snowflake’s separation of compute and storage ensures high scalability for analytical workloads, outperforming Postgres in Pipeline #1.
  - The ETL process may become a bottleneck if not optimized for large data volumes.
- **Complexity**: 
  - Similar to Pipeline #1, managing two databases (MongoDB and Snowflake) and an ETL pipeline increases operational overhead.
  - Less complex than Pipeline #2 (no Blob Storage), but more complex than Pipeline #3 (no direct streaming to Snowflake).
  - ETL requires schema mapping and transformation from MongoDB’s flexible schema to Snowflake’s structured schema.
- **Data Consistency**: 
  - The ETL process risks data inconsistencies or delays if not carefully managed (e.g., schema mismatches or failures in data transfer).
  - Similar to Pipeline #1, but Snowflake’s robust data integrity features (e.g., ACID compliance) mitigate some risks compared to Postgres.
- **Alignment with Goal**: Fully aligns with the goal by eliminating Postgres and using Snowflake for analytics.

**Summary**: Pipeline #4 is a straightforward replacement of Postgres with Snowflake in the current architecture. It leverages MongoDB for operational storage and Snowflake for analytics but inherits the complexity and latency of an ETL process, similar to Pipeline #1.

---

### **Comparison with Previous Pipelines**

| **Criteria**           | **Pipeline #1 (Mongo -> Postgres)** | **Pipeline #2 (Mongo & Blob -> Snowflake)** | **Pipeline #3 (Mongo & Snowflake)** | **Pipeline #4 (Mongo -> Snowflake)** |
|-----------------------|------------------------------------|--------------------------------------------|------------------------------------|------------------------------------|
| **Architecture**       | MQTT -> Event Hub -> Mongo -> Postgres | MQTT -> Event Hub -> (Mongo & Blob) -> Snowflake | MQTT -> Event Hub -> (Mongo & Snowflake) | MQTT -> Event Hub -> Mongo -> Snowflake |
| **Performance**        | Moderate (Postgres limits analytics, ETL latency) | Good (Blob adds latency, Snowflake excels) | Best (Near real-time, no Blob latency) | Good (ETL latency, Snowflake excels) |
| **Cost**               | High (Mongo + Postgres + ETL) | Moderate (Mongo + Blob + Snowflake + ETL) | Moderate (Mongo + Snowflake, no Blob) | Moderate (Mongo + Snowflake + ETL) |
| **Scalability**        | Limited by Postgres | High (Blob + Snowflake) | High (Snowflake) | High (Snowflake, ETL may limit) |
| **Complexity**         | High (Dual databases + ETL) | Higher (Three systems + ETL) | Moderate (Two systems, streaming) | High (Dual databases + ETL) |
| **Data Consistency**   | Moderate (ETL risks) | Moderate (Parallel writes + ETL risks) | Moderate (Parallel writes risks) | Moderate (ETL risks) |
| **Goal Alignment**     | Does not meet (uses Postgres) | Meets (Snowflake replaces Postgres) | Meets (Snowflake replaces Postgres) | Meets (Snowflake replaces Postgres) |

---

### **Detailed Comparison**
- **Vs. Pipeline #1 (Mongo -> Postgres)**:
  - **Similarities**: Both use a sequential architecture (Mongo -> analytical database) with an ETL process.
  - **Differences**: 
    - Pipeline #4 replaces Postgres with Snowflake, aligning with the goal.
    - Snowflake offers better analytical performance and scalability than Postgres.
    - Costs may shift (Snowflake’s compute/storage vs. Postgres’s instance-based pricing), with Snowflake potentially more expensive for heavy analytics but more efficient for large-scale queries.
    - Complexity remains similar due to the ETL process, but Snowflake’s managed nature reduces some database administration overhead compared to Postgres.
  - **Conclusion**: Pipeline #4 is a direct improvement over Pipeline #1, achieving the goal of using Snowflake while maintaining a similar architecture.

- **Vs. Pipeline #2 (Mongo & Blob -> Snowflake)**:
  - **Similarities**: Both use MongoDB for operational storage and Snowflake for analytics, aligning with the goal.
  - **Differences**: 
    - Pipeline #4 eliminates Blob Storage, simplifying the architecture and reducing storage costs.
    - Pipeline #2’s parallel writes to MongoDB and Blob Storage avoid sequential ETL latency between MongoDB and Snowflake, but Blob-to-Snowflake ETL introduces its own latency.
    - Pipeline #4’s sequential ETL (Mongo -> Snowflake) may be simpler to manage than Pipeline #2’s three-system setup but risks similar latency.
    - Pipeline #2 is better for scenarios requiring a data lake (e.g., archiving or multi-format data storage), while Pipeline #4 is more streamlined.
  - **Conclusion**: Pipeline #4 is simpler and potentially cheaper (no Blob Storage), but Pipeline #2 is better for data lake use cases or when parallel ingestion is preferred.

- **Vs. Pipeline #3 (Mongo & Snowflake)**:
  - **Similarities**: Both use MongoDB and Snowflake, aligning with the goal.
  - **Differences**: 
    - Pipeline #3 sends data directly to both MongoDB and Snowflake in parallel, avoiding ETL latency and simplifying the architecture.
    - Pipeline #4’s sequential flow (Mongo -> Snowflake) introduces ETL latency and complexity, similar to Pipeline #1.
    - Pipeline #3 requires streaming setup (e.g., Snowflake Kafka connector or Snowpipe), which may be complex but eliminates ETL overhead.
    - Pipeline #3 may have higher Snowflake compute costs for streaming but avoids ETL pipeline costs (e.g., Azure Data Factory).
  - **Conclusion**: Pipeline #3 is superior in performance (near real-time) and simplicity (no ETL), but Pipeline #4 may be easier to implement if you’re already familiar with Mongo-to-Postgres ETL processes.

---

### **Recommendation**
**Pipeline #3** remains the best choice from the previous comparison due to its simplicity, near-real-time performance, and elimination of ETL overhead. However, **Pipeline #4** is a viable alternative if:
- You prefer a sequential architecture similar to your current setup (Pipeline #1), leveraging existing ETL expertise.
- Real-time analytics is not critical, and batch ETL from MongoDB to Snowflake is acceptable.
- You want to avoid the complexity of setting up direct streaming to Snowflake (e.g., Kafka connector or Snowpipe).

**Comparison to Pipeline #4**:
- **Pipeline #4** is a direct evolution of your current pipeline (Pipeline #1), replacing Postgres with Snowflake while maintaining the same structure. It’s easier to transition to if you’re accustomed to Mongo-to-Postgres ETL processes.
- However, it inherits the same drawbacks as Pipeline #1: ETL latency, complexity, and potential data consistency issues.
- Compared to Pipeline #3, Pipeline #4 is less performant (due to ETL latency) and more complex (due to ETL management) but may be easier to implement if streaming to Snowflake is not feasible.

**Action Steps for Pipeline #4**:
1. Reuse existing Mongo-to-Postgres ETL logic, adapting it for Snowflake (e.g., using Azure Data Factory or Snowflake’s COPY command).
2. Define schema mappings from MongoDB’s flexible schema to Snowflake’s structured tables, handling IoT data variability.
3. Optimize ETL frequency (e.g., batch vs. micro-batch) based on latency requirements.
4. Monitor Snowflake compute costs and optimize with auto-scaling/auto-suspend.
5. Compare costs using Azure and Snowflake pricing calculators, factoring in ETL (e.g., Data Factory) and Snowflake compute/storage.

**When to Choose Pipeline #4**:
- If transitioning from Pipeline #1 and you want minimal changes to the existing architecture.
- If real-time analytics is not a priority, and batch processing is sufficient.
- If your team lacks expertise in streaming setups (e.g., Snowflake Kafka connector).

**When to Prefer Pipeline #3**:
- If near-real-time analytics is critical.
- If you want to minimize complexity by eliminating ETL processes.
- If you can invest in configuring streaming ingestion to Snowflake.

**Memory Integration**: Based on your prior question about transferring data from MQTT to Snowflake on Azure (July 29, 2025), Pipeline #4 aligns with a sequential approach you may have considered, but Pipeline #3 was likely recommended for its direct streaming efficiency. If you’re leaning toward Pipeline #4 due to familiarity with your current ETL setup, I can provide detailed guidance on adapting it for Snowflake.

Let me know if you need specific implementation details (e.g., ETL setup with Azure Data Factory, Snowflake schema design, or cost estimates) or if you want to explore Pipeline #3’s streaming setup further.




```python
import pymongo
from snowflake.connector import connect
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
import pandas as pd
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB and Snowflake connection configurations
MONGO_URI = "mongodb://<user>:<password>@<host>:<port>/<database>"
MONGO_DB = "<mongo_database>"
MONGO_COLLECTION = "<mongo_collection>"

SNOWFLAKE_ACCOUNT = "<snowflake_account>"
SNOWFLAKE_USER = "<snowflake_user>"
SNOWFLAKE_PASSWORD = "<snowflake_password>"
SNOWFLAKE_DATABASE = "<snowflake_database>"
SNOWFLAKE_SCHEMA = "<snowflake_schema>"
SNOWFLAKE_WAREHOUSE = "<snowflake_warehouse>"
SNOWFLAKE_ROLE = "<snowflake_role>"

# Snowflake connection using snowflake-connector-python
def get_snowflake_connection():
    try:
        conn = connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
            role=SNOWFLAKE_ROLE
        )
        logger.info("Connected to Snowflake")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        raise

# Snowflake SQLAlchemy engine for pandas
def get_snowflake_engine():
    try:
        engine = create_engine(URL(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
            role=SNOWFLAKE_ROLE
        ))
        logger.info("Snowflake SQLAlchemy engine created")
        return engine
    except Exception as e:
        logger.error(f"Failed to create Snowflake engine: {e}")
        raise

# Connect to MongoDB
def get_mongo_collection():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        logger.info(f"Connected to MongoDB collection: {MONGO_COLLECTION}")
        return collection
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

# Transform MongoDB document by unrolling nested JSON
def transform_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unroll nested JSON from MongoDB into a flat structure for Snowflake.
    Example MongoDB document:
    {
        "_id": "123",
        "device_id": "sensor_001",
        "timestamp": ISODate("2025-08-04T12:00:00Z"),
        "readings": {
            "temperature": 25.5,
            "humidity": 60,
            "metadata": {
                "location": "room_1",
                "unit": "C"
            }
        }
    }
    Transformed to:
    {
        "id": "123",
        "device_id": "sensor_001",
        "timestamp": "2025-08-04 12:00:00",
        "temperature": 25.5,
        "humidity": 60,
        "location": "room_1",
        "unit": "C"
    }
    """
    try:
        flat_doc = {}
        flat_doc["id"] = str(doc.get("_id", uuid.uuid4()))
        flat_doc["device_id"] = doc.get("device_id")
        flat_doc["timestamp"] = doc.get("timestamp", datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')

        # Unroll nested 'readings' field
        readings = doc.get("readings", {})
        flat_doc["temperature"] = readings.get("temperature")
        flat_doc["humidity"] = readings.get("humidity")

        # Unroll nested 'metadata' within 'readings'
        metadata = readings.get("metadata", {})
        flat_doc["location"] = metadata.get("location")
        flat_doc["unit"] = metadata.get("unit")

        # Remove None values to avoid issues in Snowflake
        return {k: v for k, v in flat_doc.items() if v is not None}
    except Exception as e:
        logger.error(f"Error transforming document {doc.get('_id')}: {e}")
        return None

# Create Snowflake table with optimized schema
def create_snowflake_table(conn):
    try:
        cursor = conn.cursor()
        create_table_query = """
        CREATE OR REPLACE TABLE sensor_data (
            id VARCHAR(50) PRIMARY KEY,
            device_id VARCHAR(50),
            timestamp TIMESTAMP_NTZ,
            temperature FLOAT,
            humidity FLOAT,
            location VARCHAR(100),
            unit VARCHAR(10),
            ingestion_time TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        CLUSTER BY (device_id, timestamp);
        """
        cursor.execute(create_table_query)
        logger.info("Snowflake table 'sensor_data' created with clustering")
        cursor.close()
    except Exception as e:
        logger.error(f"Failed to create Snowflake table: {e}")
        raise

# Load data into Snowflake
def load_to_snowflake(data: List[Dict], engine):
    try:
        df = pd.DataFrame(data)
        df.to_sql('sensor_data', engine, schema=SNOWFLAKE_SCHEMA, if_exists='append', index=False)
        logger.info(f"Loaded {len(data)} records to Snowflake")
    except Exception as e:
        logger.error(f"Failed to load data to Snowflake: {e}")
        raise

# Main ETL function
def mongo_to_snowflake_etl(batch_size: int = 1000):
    try:
        # Connect to MongoDB and Snowflake
        mongo_collection = get_mongo_collection()
        snowflake_conn = get_snowflake_connection()
        snowflake_engine = get_snowflake_engine()

        # Create Snowflake table
        create_snowflake_table(snowflake_conn)

        # Fetch and process MongoDB documents in batches
        cursor = mongo_collection.find()
        batch = []
        for doc in cursor:
            transformed_doc = transform_document(doc)
            if transformed_doc:
                batch.append(transformed_doc)
            if len(batch) >= batch_size:
                load_to_snowflake(batch, snowflake_engine)
                batch = []
        
        # Load remaining documents
        if batch:
            load_to_snowflake(batch, snowflake_engine)

        logger.info("ETL process completed successfully")
        snowflake_conn.close()
    except Exception as e:
        logger.error(f"ETL process failed: {e}")
        raise

if __name__ == "__main__":
    mongo_to_snowflake_etl()
```
