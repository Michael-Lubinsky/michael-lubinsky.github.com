# Data Transfer From MongoDB to Snowflake
Weavix MongoDB collections can be updated
New Weavix MongoDB can be created any time

In this case we need to implement Change Data Capture (CDC) Pipeline

## Azure Data Factory Pipeline 
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
