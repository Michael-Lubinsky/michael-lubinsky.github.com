# Data Transfer From MongoDB to Snowflake
Weavix MongoDB collections can be updated
New Weavix MongoDB can be created any time

In this case we need to implement Change Data Capture (CDC) Pipeline

```
MongoDB
   |
   |  (Azure Function / Python on Timer Trigger)
   v
Python App on Azure Container Instance (ACI) or Azure Functions (long-running)
   |
   |  [Extract → Flatten → Save Parquet to Azure Blob]
   v
Azure Blob Storage
   |
   |  [Snowflake COPY INTO from Azure Stage]
   v
Snowflake (optimized flat tables)
```
| Component                                | Reason to Keep                      |
| ---------------------------------------- | ----------------------------------- |
| **Azure Functions** or **Timer Trigger** | Lightweight and cheap orchestration |
| **Python**                               | Simple ETL logic — easy to manage   |
| **Azure Container Instance (ACI)**       | Cost-effective for periodic jobs    |
| **Blob Storage**                         | Durable, scalable staging layer     |
| **Snowflake**                            | Final analytics warehouse           |

Optional Advanced Scenarios

| Feature               | Solution without Databricks                   |
| --------------------- | --------------------------------------------- |
| Real-time ingestion   | Use MongoDB Change Streams + Azure Event Hubs |
| Parallel processing   | Use Azure Durable Functions or Azure Batch    |
| Schema inference      | Handled by Python `pandas` + Parquet schema   |
| Complex normalization | Done in Python before writing to blob         |
| Monitoring            | Use Azure Monitor or add logging to Snowflake |



## Azure Data Factory Pipeline 

Why Use Azure Data Factory (ADF) for MongoDB → Snowflake?
Azure Data Factory (ADF) is absolutely a strong candidate for this use case. 
It was omitted in the first pipeline because:

You asked for efficiency, and

ADF can sometimes feel heavy or costly for simple or highly dynamic Mongo collections 
(e.g., auto-discovering new collections and schemas)

But for managed orchestration and low-code pipelines, ADF does make sense, especially if:

### When ADF is a Good Fit

| Scenario                                 | ADF Strength            |
| ---------------------------------------- | ----------------------- |
| Scheduled, automated data movement       | ✅ Native                |
| Azure-native data orchestration          | ✅ Excellent integration |
| Transformations with minimal code        | ✅ Built-in Data Flows   |
| Monitoring and retry logic               | ✅ Built-in              |
| Team prefers low-code / visual pipelines | ✅ Ideal                 |


### Where ADF Has Limitations

| Scenario                                  | Reason                                                                                                            |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **MongoDB with many dynamic collections** | ADF is not dynamic — you must **manually define** each collection-to-sink mapping or generate it programmatically |
| **Need to flatten deeply nested JSON**    | ADF has limited ability to handle complex nested data without external transformation (i.e., Python or Spark)     |
| **Need full schema control / versioning** | Easier in code-based ETL than ADF UI                                                                              |
| **Frequent schema drift**                 | Harder to manage in ADF UI                                                                                        |



Azure Data Factory Pipeline

- Triggers the pipeline on a schedule (every N minutes/hours)
- Lists all collections in MongoDB
- Submits each collection for processing via event or job queue (e.g., Azure Queue)





```json
{
  "name": "MongoDB-to-Snowflake-Direct-Pipeline",
  "activities": [
    {
      "name": "Get-New-Files",
      "type": "GetMetadata",
      "typeProperties": {
        "dataset": {
          "referenceName": "ADLS_MongoDB_Files"
        },
        "fieldList": ["childItems"],
        "storeSettings": {
          "type": "AzureBlobFSReadSettings",
          "recursive": true,
          "modifiedDatetimeStart": "@addHours(utcnow(), -1)",
          "modifiedDatetimeEnd": "@utcnow()"
        }
      }
    },
    {
      "name": "Process-New-Files",
      "type": "ForEach",
      "dependsOn": [{"activity": "Get-New-Files", "dependencyConditions": ["Succeeded"]}],
      "typeProperties": {
        "items": "@activity('Get-New-Files').output.childItems",
        "isSequential": false,
        "batchCount": 10,
        "activities": [
          {
            "name": "Copy-to-Snowflake",
            "type": "Copy",
            "typeProperties": {
              "source": {
                "type": "JsonSource",
                "storeSettings": {
                  "type": "AzureBlobFSReadSettings"
                },
                "formatSettings": {
                  "type": "JsonReadSettings"
                }
              },
              "sink": {
                "type": "SnowflakeSink",
                "importSettings": {
                  "type": "SnowflakeImportCopyCommand",
                  "copyOptions": {
                    "FILE_FORMAT": "(TYPE = 'JSON', STRIP_OUTER_ARRAY = FALSE)"
                  }
                }
              }
            }
          }
        ]
      }
    }
  ],
  "triggers": [
    {
      "name": "HourlyProcessing",
      "type": "ScheduleTrigger",
      "typeProperties": {
        "recurrence": {
          "frequency": "Hour",
          "interval": 1
        }
      }
    }
  ]
}
```
