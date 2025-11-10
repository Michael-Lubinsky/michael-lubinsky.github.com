

## Trigger Type: File Arrival

S3 (event) → SNS topic → SQS queue → Databricks Auto Loader

AWS IAM you need:

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

 
