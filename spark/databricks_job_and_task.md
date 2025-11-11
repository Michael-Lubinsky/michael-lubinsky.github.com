## Databricks Job

It Streamining we use readStream() and writeStream(), checkpoint required
In File arrived we use  read() and merge(), sluster starts on demand

## Trigger Type: File Arrival

S3 (event) → SNS topic → SQS queue → Databricks Auto Loader
```
1. Lambda writes file → s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/file.json                   ↓
2. S3 Event Notification → SQS Queue                       ↓
3. Databricks File Arrival Trigger monitors SQS → Detects new file                       ↓
4. Starts your Databricks Job (streaming query)                      ↓
5. Auto Loader reads from SQS notification → Processes new file(s)                      ↓
6. Checkpoint tracks processed files → No duplicates                     ↓
7. Query completes (if using availableNow) → Cluster stops
```

### Code modification
```
# Change this line from:
.option("cloudFiles.useNotifications", "false")  # ❌ Current

# To this:
.option("cloudFiles.useNotifications", "true")   # ✅ For File Arrival
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

```
writer = (
            flat_stream.writeStream
                .option("checkpointLocation", CONFIG["checkpoint_path"])
                .foreachBatch(upsert_batch)
                .option("mergeSchema", "true")
                .trigger(availableNow=True)        # ### CHANGED: one-shot to fit File-Arrival job
        )
```


## IAM Requirements:

## GROK

# 1. Give Databricks permission to create SNS/SQS for you
```
aws iam create-policy --policy-name DatabricksAutoLoaderNotifications \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["sns:CreateTopic","sns:Subscribe"],"Resource":"*"},
      {"Effect":"Allow","Action":["sqs:*"],"Resource":"*"}
    ]
  }'
```
# Attach the policy to the role
that your Databricks workspace uses for S3 access  
Databricks will now auto-provision an SNS topic + SQS queue 
the first time you start the stream with useNotifications=true.


## 🔐 AWS IAM Permissions (Claude)

### IAM Policy for Databricks

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SQSAccessForAutoLoader",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:*:*:databricks-auto-ingest-*"
    },
    {
      "Sid": "SQSListQueues",
      "Effect": "Allow",
      "Action": "sqs:ListQueues",
      "Resource": "*"
    }
  ]
}
```

### S3 Event Notification to SQS

```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksAutoLoaderNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```

### SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/databricks-instance-role"
      },
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:databricks-auto-ingest-chargeminder"
    }
  ]
}
```

## 🎯 Two Modes of Operation

### Mode 1: Continuous Streaming (Your Current Code)
```python
if CONFIG["trigger_mode"] == "availableNow":
    writer = writer.trigger(availableNow=True)  # ✅ Process files then stop
else:
    writer = writer.trigger(processingTime=CONFIG["processing_time"])  # Continuous
```

**For File Arrival Trigger, use:**
```python
CONFIG = {
    "trigger_mode": "availableNow",  # ✅ Recommended for cost efficiency
    # When file arrives → job starts → processes all files → stops
}
```

### Mode 2: Always-On Streaming
```python
CONFIG = {
    "trigger_mode": "processingTime",
    "processing_time": "1 minute",
    # Cluster stays running, checks every minute
}
```

## 📊 Comparison: Batch vs Streaming with File Arrival

| Approach | Trigger | Processing | Checkpoints | Duplicates | Cost |
|----------|---------|------------|-------------|------------|------|
| **Batch (read + merge)** | Manual/Orchestrated | Each file separately | No | Possible | Lower if infrequent |
| **Streaming + File Arrival** ✅ | Automatic on file | Incremental with checkpoints | Yes | Prevented | Optimal with availableNow |
| **Continuous Streaming** | Always running | Continuous micro-batches | Yes | Prevented | Higher (always on) |

## ✅ Your Code is Already Correct!

The only actual modifications needed:

### 1. Change One Option (Critical)
```python
.option("cloudFiles.useNotifications", "true")  # Changed from "false"
```

### 2. Optionally Add Queue Name (For Multiple Jobs)
```python
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")  # Optional but recommended
```

### 3. Recommended: Use availableNow Trigger
```python
CONFIG = {
    "trigger_mode": "availableNow",  # Process files and stop (cost-efficient)
    # ... rest of config unchanged
}
```

## 🚀 Setup Steps

### 1. Create SQS Queue
```bash
aws sqs create-queue \
  --queue-name databricks-auto-ingest-chargeminder \
  --attributes MessageRetentionPeriod=86400
```

### 2. Configure S3 Event Notifications
```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://s3-notification.json
```

### 3. Update Your Code
```python
# In read_stream() function:
.option("cloudFiles.useNotifications", "true")
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

### 4. Create Databricks Job
- **No File Arrival Trigger needed in Databricks UI!**
- Just create a regular scheduled job or run it manually first
- Auto Loader will automatically poll the SQS queue
- When files arrive → Auto Loader processes them automatically

## 🎓 Key Takeaways

1. ✅ **File Arrival = Streaming, not batch**
2. ✅ **Auto Loader with useNotifications=true handles everything**
3. ✅ **checkpointLocation is required**
4. ✅ **schemaLocation is required**
5. ✅ **Your original code is correct**, just change one option
6. ✅ **availableNow trigger is recommended** for cost efficiency

 
## Another opinion on IAM permisiions for File arrive Trigger


🔐 AWS IAM Permissions Required
Option A: Using S3 Event Notifications + SQS (Recommended)
This is the standard approach for File Arrival triggers.

1. IAM Policy for Databricks Instance Profile/Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "S3WriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2/archived/*",
        "arn:aws:s3:::chargeminder-2/quarantine/*"
      ]
    },
    {
      "Sid": "SQSAccess",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue"
    }
  ]
}
```
2. S3 Bucket Notification Configuration
   
```json
{
  "QueueConfigurations": [
    {
      "Id": "DatabricksFileArrivalNotification",
      "QueueArn": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "raw/dynamodb/chargeminder-car-telemetry/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
```
3. SQS Queue Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-queue",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:s3:::chargeminder-2"
        }
      }
    }
  ]
}
```

## Option B: Using S3 Event Notifications + SNS
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/*"
      ]
    },
    {
      "Sid": "SNSAccess",
      "Effect": "Allow",
      "Action": [
        "sns:Subscribe",
        "sns:Unsubscribe",
        "sns:GetTopicAttributes"
      ],
      "Resource": "arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:databricks-file-arrival-topic"
    }
  ]
}
```

📋 Setup Steps for File Arrival Trigger
### Option B: Step 1: Create SQS Queue

```bash
aws sqs create-queue \
  --queue-name databricks-file-arrival-queue \
  --attributes '{
    "MessageRetentionPeriod": "86400",
    "VisibilityTimeout": "300"
  }'

```

### Option B: Step 2: Configure S3 Event Notifications

```bash
aws s3api put-bucket-notification-configuration \
  --bucket chargeminder-2 \
  --notification-configuration file://notification-config.json
```

###   Option B: Step 3: Create Databricks Job with File Arrival Trigger

In Databricks UI:
```
1. **Create Job**
2. **Add Task:**
   - Task name: `process_telemetry`
   - Type: `Python script` or `Notebook`
   - Source: Your modified script
   - Cluster: Select appropriate cluster

3. **Configure Trigger:**
   - Click **Add trigger**
   - Select **File arrival**
   - Configure:


File notification service: SQS (or SNS)
Queue/Topic URL:
https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
#### Advanced Options:
```
Wait for all tasks: ✓
Max concurrent runs: 1 (or higher for parallel processing)
Timeout: 60 minutes
```


###  Test the Setup - Upload a test file to S3
 
```bash
aws s3 cp test-file.json s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/
```
### Check SQS queue for message
```
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue
```
### Monitor Databricks job runs
  The job should trigger automatically within a few seconds




