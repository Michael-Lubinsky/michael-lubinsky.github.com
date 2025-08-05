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


### Are you recommending Azure Function or Azure data factory fir thi pipeline?


Great question! Let me clarify the optimal approach.  
I recommend Azure Data Factory as the primary orchestrator with minimal Azure Functions only where absolutely necessary.

Recommended Approach: ADF-Centric Pipeline
Azure Data Factory Should Handle:
1 Collection Discovery - Using native MongoDB connector
2 Data Movement - MongoDB to ADLS Gen2 to Snowflake
3 Orchestration - Scheduling, error handling, monitoring
4 Change Data Capture - Through scheduled incremental loads

Azure Functions Only For:
1 MongoDB Change Streams (if real-time CDC is critical)
2 Complex custom logic that ADF can't handle natively

#### Why ADF-Centric is Better:

Enhanced MongoDB to Snowflake Pipeline for Dynamic Collections

My Recommendation: Azure Data Factory Primary

ADF Advantages:
- Native MongoDB Connector - No custom code needed
- Built-in Error Handling - Automatic retries, dead letter queues
- Visual Pipeline Designer - Easy to maintain and debug
- Enterprise Features - Monitoring, alerting, SLA management
- Cost Predictable - Fixed monthly cost (~$50-100)
- Scaling - Automatic with Data Integration Units

Functions Disadvantages for ETL:

- Timeout Limits - 10 minutes max execution time
- State Management - Complex for long-running processes
- Error Recovery - Manual implementation needed
- Monitoring Complexity - Multiple functions to track
- Cold Start Delays - Inconsistent performance
- 
When to Use Each:

Use ADF For:
✅ Collection Discovery - List collections, get stats
✅ Bulk Data Movement - MongoDB → ADLS → Snowflake
✅ Scheduled Processing - Hourly/daily batch loads
✅ Pipeline Orchestration - Complex workflows
✅ Error Handling - Built-in retry and monitoring

Use Functions Only For:
⚠️ Real-time Change Streams - If sub-hour latency is critical
⚠️ Custom Business Logic - Complex transformations ADF can't handle
⚠️ Event-driven Triggers - Immediate response to specific events

Recommended Hybrid Approach:
90% ADF + 10% Functions

1 Primary Pipeline: ADF handles all collection discovery and bulk data movement
2 Optional Functions: Only for critical collections requiring real-time CDC
3 Event Hub: Bridge between Functions and ADF for real-time triggers


Cost Comparison:
- ADF-Only: $50-100/month + compute costs
- Functions-Heavy: $20-200/month + unpredictable scaling costs
- Hybrid: $70-120/month (predictable)
Bottom Line: Start with ADF-only. Add Functions later only if you need sub-hour latency for specific collections.


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
