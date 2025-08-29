For your 3-step ETL pipeline, **Azure Data Factory (ADF)** is actually a better choice than Azure Durable Functions. 
Here's why and how to implement it:

## **Recommended Solution: Azure Data Factory**

### Why ADF is better for your use case:
- **Built for ETL pipelines** with native scheduling
- **Native Snowflake integration** with built-in connectors
- **Visual pipeline designer** with monitoring/alerting
- **Automatic retry/error handling**
- **Cost-effective** for scheduled batch processing
- **Better observability** and logging

## **Pipeline Architecture:**

### **Step 1: Hourly Trigger + Azure Container Instance**
```json
{
  "name": "EventHubToADLS",
  "activities": [
    {
      "name": "RunNodeJSProcessor",
      "type": "AzureContainerInstance",
      "typeProperties": {
        "containerGroupName": "eventhub-processor",
        "image": "your-registry/step1-nodejs:latest",
        "environmentVariables": {
          "ENABLE_COMPRESSION": "true",
          "TARGET_HOUR": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')"
        }
      }
    }
  ],
  "triggers": [
    {
      "name": "HourlyTrigger",
      "type": "ScheduleTrigger",
      "recurrence": {
        "frequency": "Hour",
        "interval": 1
      }
    }
  ]
}
```

### **Step 2: ADLS to Snowflake Copy**
```json
{
  "name": "ADLSToSnowflakeBronze",
  "activities": [
    {
      "name": "CopyToSnowflake",
      "type": "Copy",
      "source": {
        "type": "DelimitedTextSource",
        "storeSettings": {
          "type": "AzureBlobFSReadSettings",
          "recursive": true,
          "wildcardFolderPath": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')",
          "wildcardFileName": "*.jsonl"
        }
      },
      "sink": {
        "type": "SnowflakeSink",
        "preCopyScript": "TRUNCATE TABLE bronze.events;"
      }
    }
  ]
}
```

### **Step 3: Snowflake Stored Procedure**
```json
{
  "name": "BronzeToSilver",
  "activities": [
    {
      "name": "ExecuteStoredProcedure",
      "type": "SqlServerStoredProcedure",
      "linkedServiceName": "SnowflakeLinkedService",
      "typeProperties": {
        "storedProcedureName": "BRONZE_TO_SILVER_TRANSFORM",
        "storedProcedureParameters": {
          "ProcessDate": "@formatDateTime(utcnow(), 'yyyy-MM-dd-HH')"
        }
      }
    }
  ]
}
```

## **Complete Implementation:** 

(code on the bottom)





## **Alternative Solutions:**

### **1. Azure Logic Apps** (if you prefer low-code):
- Good for simple workflows
- Built-in connectors for Snowflake
- Easy HTTP triggers for custom scripts

### **2. Azure Durable Functions** (if you need more control):
```javascript
// orchestrator.js
const df = require("durable-functions");

module.exports = df.orchestrator(function* (context) {
    // Step 1: Process EventHub data
    yield context.df.callActivity("ProcessEventHub", context.df.currentUtcDateTime);
    
    // Step 2: Copy to Snowflake Bronze  
    yield context.df.callActivity("CopyToSnowflake", null);
    
    // Step 3: Transform Bronze to Silver
    yield context.df.callActivity("TransformToSilver", null);
});
```

### **3. Azure Synapse Pipelines** (if using Synapse ecosystem):
- Similar to ADF but integrated with Synapse Analytics
- Good if you need additional analytics capabilities

## **Recommendations:**

1. **Use Azure Data Factory** - Best fit for your use case
2. **Containerize your Node.js app** using Azure Container Registry
3. **Set up proper monitoring** with Azure Monitor
4. **Use Snowflake's COPY command** for better performance than Snowpipe for batch loads
5. **Implement proper error handling** and alerting

**Azure Data Factory is definitely your best choice here** - it's designed exactly for this type of ETL pipeline!

------

You're absolutely right! My JSON example was using ADF's built-in Copy activity, which abstracts away the Snowflake COPY command. Let me elaborate on the different approaches:

## **Approach 1: ADF Copy Activity (What I showed)**

The ADF Copy activity internally uses Snowflake's COPY command, but you don't see it explicitly. Here's what happens behind the scenes:

```json
{
  "name": "CopyToSnowflakeBronze",
  "type": "Copy",
  "typeProperties": {
    "source": {
      "type": "JsonSource",
      "storeSettings": {
        "type": "AzureBlobFSReadSettings",
        "wildcardFolderPath": "2025/08/28/18",
        "wildcardFileName": "*.jsonl"
      }
    },
    "sink": {
      "type": "SnowflakeSink",
      "importSettings": {
        "type": "SnowflakeImportCopyCommand",
        // This generates COPY commands automatically
        "copyOptions": {
          "FORCE": "TRUE",
          "ON_ERROR": "ABORT_STATEMENT",
          "FILE_FORMAT": "(TYPE = 'JSON')"
        }
      }
    }
  }
}
```

**ADF automatically generates something like:**
```sql
COPY INTO bronze.events 
FROM 'azure://weavixdatalakedevsa.dfs.core.windows.net/telemetry/2025/08/28/18/'
FILE_FORMAT = (TYPE = 'JSON')
ON_ERROR = 'ABORT_STATEMENT'
FORCE = TRUE;
```

## **Approach 2: Explicit COPY Command (More Control)**

```js
{
  "name": "ExplicitSnowflakeCopy",
  "activities": [
    {
      "name": "ExecuteSnowflakeCopyCommand",
      "type": "SqlServerStoredProcedure",
      "linkedServiceName": "SnowflakeLinkedService",
      "typeProperties": {
        "storedProcedureName": "EXECUTE_IMMEDIATE",
        "storedProcedureParameters": {
          "QUERY_STRING": {
            "value": "@concat('COPY INTO bronze.events FROM ''azure://weavixdatalakedevsa.dfs.core.windows.net/telemetry/', formatDateTime(utcnow(), 'yyyy/MM/dd/HH'), '/'' CREDENTIALS=(AZURE_SAS_TOKEN=''', pipeline().parameters.SasToken, ''') FILE_FORMAT=(TYPE=''JSON'') ON_ERROR=''CONTINUE'' FORCE=TRUE')",
            "type": "String"
          }
        }
      }
    }
  ],
  "parameters": {
    "SasToken": {
      "type": "String"
    },
    "TargetFolder": {
      "type": "String",
      "defaultValue": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')"
    }
  }
}

```

## **Approach 3: Direct Snowflake Script Activity**

```json
{
  "name": "DirectSnowflakeScript",
  "type": "Script",
  "linkedServiceName": "SnowflakeLinkedService",
  "typeProperties": {
    "scripts": [
      {
        "type": "NonQuery",
        "text": "@concat('COPY INTO bronze.events FROM ''azure://weavixdatalakedevsa.dfs.core.windows.net/telemetry/', formatDateTime(utcnow(), 'yyyy/MM/dd/HH'), '/'' CREDENTIALS=(AZURE_SAS_TOKEN=''', pipeline().parameters.SasToken, ''') FILE_FORMAT=(TYPE=''JSON'' STRIP_OUTER_ARRAY=TRUE) PATTERN=''.*\\.jsonl.*'' ON_ERROR=''CONTINUE'' FORCE=TRUE VALIDATION_MODE=''RETURN_ERRORS''')"
      }
    ]
  }
}
```

## **Approach 4: Custom Snowflake Stored Procedure**

### Create this stored procedure in Snowflake:
```sql
CREATE OR REPLACE PROCEDURE LOAD_EVENTS_FROM_ADLS(
  FOLDER_PATH STRING,
  SAS_TOKEN STRING
)
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
  LET copy_cmd := 'COPY INTO bronze.events FROM ' ||
    '''azure://weavixdatalakedevsa.dfs.core.windows.net/telemetry/' || FOLDER_PATH || '/' ||
    ''' CREDENTIALS=(AZURE_SAS_TOKEN=''' || SAS_TOKEN || ''') ' ||
    'FILE_FORMAT=(TYPE=''JSON'' STRIP_OUTER_ARRAY=TRUE) ' ||
    'PATTERN=''.*\.jsonl.*'' ' ||
    'ON_ERROR=''CONTINUE'' ' ||
    'FORCE=TRUE';
  
  EXECUTE IMMEDIATE copy_cmd;
  
  RETURN 'SUCCESS: Loaded data from ' || FOLDER_PATH;
END;
$$;
```

### Then call it from ADF:
```json
{
  "name": "LoadFromADLS",
  "type": "SqlServerStoredProcedure",
  "linkedServiceName": "SnowflakeLinkedService",
  "typeProperties": {
    "storedProcedureName": "LOAD_EVENTS_FROM_ADLS",
    "storedProcedureParameters": {
      "FOLDER_PATH": {
        "value": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')",
        "type": "String"
      },
      "SAS_TOKEN": {
        "value": "@pipeline().parameters.SasToken",
        "type": "String"
      }
    }
  }
}
```

## **Key Considerations for JSONL Files:**

### **File Format Setup in Snowflake:**
```sql
CREATE FILE FORMAT jsonl_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = FALSE  -- Important for JSONL
  COMPRESSION = 'GZIP';      -- If your files are compressed
```

### **For Compressed Files:**
```sql
COPY INTO bronze.events 
FROM 'azure://your-storage/telemetry/2025/08/28/18/'
FILE_FORMAT = (
  TYPE = 'JSON'
  COMPRESSION = 'GZIP'
  STRIP_OUTER_ARRAY = FALSE
)
PATTERN = '.*\.jsonl\.gz'
ON_ERROR = 'CONTINUE'
FORCE = TRUE;
```

## **Recommendation:**
- **Use Approach 4 (Stored Procedure)** for maximum control and better error handling
- **Use Approach 1 (ADF Copy)** for simplicity and built-in monitoring
- **Always use FORCE=TRUE** to reload the same hour if needed
- **Use ON_ERROR='CONTINUE'** to handle malformed JSON gracefully

The key insight is that ADF's Copy activity does use COPY commands internally, but using explicit stored procedures gives you much more control!






-------

```js
{
  "name": "EventHubToSnowflakeETL",
  "properties": {
    "activities": [
      {
        "name": "ProcessEventHubData",
        "type": "AzureContainerInstance",
        "dependsOn": [],
        "policy": {
          "timeout": "0.01:00:00",
          "retry": 2
        },
        "typeProperties": {
          "containerGroupName": "eventhub-processor-@{formatDateTime(utcnow(), 'yyyyMMddHH')}",
          "image": "your-acr.azurecr.io/eventhub-processor:latest",
          "resourceRequestCpu": 1,
          "resourceRequestMemoryInGB": 2,
          "environmentVariables": {
            "ENABLE_COMPRESSION": "true",
            "TARGET_FOLDER": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')",
            "BATCH_SIZE": "1000"
          }
        }
      },
      {
        "name": "WaitForProcessing",
        "type": "Wait",
        "dependsOn": [
          {
            "activity": "ProcessEventHubData",
            "dependencyConditions": ["Succeeded"]
          }
        ],
        "typeProperties": {
          "waitTimeInSeconds": 300
        }
      },
      {
        "name": "CopyToSnowflakeBronze",
        "type": "Copy",
        "dependsOn": [
          {
            "activity": "WaitForProcessing",
            "dependencyConditions": ["Succeeded"]
          }
        ],
        "policy": {
          "timeout": "0.01:00:00",
          "retry": 1
        },
        "typeProperties": {
          "source": {
            "type": "JsonSource",
            "storeSettings": {
              "type": "AzureBlobFSReadSettings",
              "recursive": true,
              "wildcardFolderPath": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')",
              "wildcardFileName": "*.jsonl*",
              "enablePartitionDiscovery": false
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
                "FORCE": "TRUE",
                "ON_ERROR": "ABORT_STATEMENT"
              }
            }
          },
          "enableStaging": true,
          "stagingSettings": {
            "linkedServiceName": "AzureBlobStorageLinkedService",
            "path": "staging/snowflake"
          }
        },
        "inputs": [
          {
            "referenceName": "ADLSJsonDataset",
            "type": "DatasetReference"
          }
        ],
        "outputs": [
          {
            "referenceName": "SnowflakeBronzeDataset", 
            "type": "DatasetReference"
          }
        ]
      },
      {
        "name": "TransformBronzeToSilver",
        "type": "SqlServerStoredProcedure",
        "dependsOn": [
          {
            "activity": "CopyToSnowflakeBronze",
            "dependencyConditions": ["Succeeded"]
          }
        ],
        "policy": {
          "timeout": "0.01:00:00",
          "retry": 1
        },
        "typeProperties": {
          "storedProcedureName": "SP_TRANSFORM_BRONZE_TO_SILVER",
          "storedProcedureParameters": {
            "ProcessTimestamp": {
              "value": "@formatDateTime(utcnow(), 'yyyy-MM-dd HH:mm:ss')",
              "type": "String"
            },
            "SourcePath": {
              "value": "@formatDateTime(utcnow(), 'yyyy/MM/dd/HH')",
              "type": "String"
            }
          }
        }
      }
    ],
    "triggers": [
      {
        "name": "HourlyETLTrigger",
        "type": "ScheduleTrigger",
        "typeProperties": {
          "recurrence": {
            "frequency": "Hour",
            "interval": 1,
            "startTime": "2025-01-01T00:00:00Z"
          }
        }
      }
    ],
    "parameters": {
      "ProcessDate": {
        "type": "String",
        "defaultValue": "@formatDateTime(utcnow(), 'yyyy-MM-dd-HH')"
      }
    }
  }
}
```
