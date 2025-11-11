## Databricks Job

It Streamining we use readStream() and writeStream(), checkpoint required
In File arrived we use  read() and merge(), sluster starts on demand

## Trigger Type: File Arrival

S3 (event) → SNS topic → SQS queue → Databricks Auto Loader
```
# Change this line:
.option("cloudFiles.useNotifications", "false")  # ❌ Current

# To this:
.option("cloudFiles.useNotifications", "true")   # ✅ For File Arrival
.option("cloudFiles.queueName", "databricks-auto-ingest-chargeminder")
```

```
1. Lambda writes file → s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/file.json                   ↓
2. S3 Event Notification → SQS Queue                       ↓
3. Databricks File Arrival Trigger monitors SQS → Detects new file                       ↓
4. Starts your Databricks Job (streaming query)                      ↓
5. Auto Loader reads from SQS notification → Processes new file(s)                      ↓
6. Checkpoint tracks processed files → No duplicates                     ↓
7. Query completes (if using availableNow) → Cluster stops
```

## IAM Requirements:

✅ S3: GetObject, ListBucket, PutObject (for archive)
✅ SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes
✅ S3 Event Notifications configured
✅ SQS Queue policy allowing S3 to send messages

### AWS IAM you need:

1. **SNS topic policy** that allows **S3** to publish to the topic
   (Principal = `s3.amazonaws.com`)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowS3ToPublish",
    "Effect": "Allow",
    "Principal": {"Service": "s3.amazonaws.com"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:us-east-1:<ACCOUNT_ID>:AutoLoaderTopic",
    "Condition": {
      "ArnLike": {"aws:SourceArn": "arn:aws:s3:::chargeminder-2"}
    }
  }]
}
```

2. **SQS queue policy** that allows **the SNS topic** to send messages to the queue
   (Principal = `sns.amazonaws.com`, Action = `SQS:SendMessage`, with SourceArn = your topic)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowSnsToSend",
    "Effect": "Allow",
    "Principal": {"Service": "sns.amazonaws.com"},
    "Action": "SQS:SendMessage",
    "Resource": "arn:aws:sqs:us-east-1:<ACCOUNT_ID>:AutoLoaderQueue",
    "Condition": {
      "ArnEquals": {"aws:SourceArn": "arn:aws:sns:us-east-1:<ACCOUNT_ID>:AutoLoaderTopic"}
    }
  }]
}
```

3. **IAM permissions for the Databricks role** (the role your job uses) so Auto Loader can poll SQS and read/write S3:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["sqs:GetQueueUrl","sqs:GetQueueAttributes","sqs:ReceiveMessage","sqs:DeleteMessage","sqs:ChangeMessageVisibility"],
      "Resource": "arn:aws:sqs:us-east-1:<ACCOUNT_ID>:AutoLoaderQueue"
    },
    { "Effect": "Allow",
      "Action": ["s3:GetBucketLocation","s3:ListBucket"],
      "Resource": "arn:aws:s3:::chargeminder-2"
    },
    { "Effect": "Allow",
      "Action": ["s3:GetObject","s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/*"
    },
    { "Effect": "Allow",
      "Action": ["s3:ListBucket","s3:GetObject","s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::chargeminder-2",
        "arn:aws:s3:::chargeminder-2/_checkpoints/fact_telemetry/*"
      ]
    }
  ]
}
```

4. **S3 bucket notification** wired to the SNS topic (in the S3 console or via IaC) for the prefixes you care about (e.g., `raw/dynamodb/chargeminder-car-telemetry/`).

 

### What to put in Databricks

For Auto Loader file-notification mode you typically set:

* `cloudFiles.useNotifications = true`
* `cloudFiles.region = "us-east-1"` (if needed)
* Optionally `cloudFiles.queueUrl = "https://sqs.us-east-1.amazonaws.com/<ACCOUNT_ID>/AutoLoaderQueue"` (if you provisioned SQS yourself)

Databricks then polls the SQS queue; as messages arrive, it reads the referenced S3 objects.

 
## Another opinoon on IAM permisiions for File arrive Trigger


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
     Queue/Topic URL: https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue

#### Advanced Options:

Wait for all tasks: ✓
Max concurrent runs: 1 (or higher for parallel processing)
Timeout: 60 minutes



### Option B:  Step 4: Test the Setup
bash# Upload a test file to S3
aws s3 cp test-file.json s3://chargeminder-2/raw/dynamodb/chargeminder-car-telemetry/

# Check SQS queue for message
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/databricks-file-arrival-queue

# Monitor Databricks job runs
# The job should trigger automatically within a few seconds




