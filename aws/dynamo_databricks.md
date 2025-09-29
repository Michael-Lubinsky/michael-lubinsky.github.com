# Accessing DynamoDB from Databricks

You can access DynamoDB tables from Databricks using the AWS SDK for Python (boto3)  
or by reading data through Spark with appropriate connectors.

## Access Methods

### 1. **Using boto3 (Python SDK)**
This is the most straightforward approach for smaller datasets:

```python
import boto3
from pyspark.sql import SparkSession

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('your-table-name')

# Scan the table
response = table.scan()
items = response['Items']

# Convert to Spark DataFrame
spark = SparkSession.builder.getOrCreate()
df = spark.createDataFrame(items)
df.show()
```

### 2. **Using Spark with DynamoDB Connector**
For larger datasets, use the emr-dynamodb-hadoop connector:

```python
df = spark.read \
    .format("dynamodb") \
    .option("tableName", "your-table-name") \
    .option("region", "us-east-1") \
    .load()
```

You'll need to install the connector library in your Databricks cluster.

## Minimal IAM Roles Required

### **For Databricks Instance Profile (EC2 Role)**

Create an IAM role with these permissions and attach it to your Databricks workspace:

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permission Policy (minimal):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME",
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME/index/*"
      ]
    }
  ]
}
```

### **Additional Permissions (if needed)**

If you need to write back to DynamoDB:
```json
{
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME"
}
```

## Configuration Steps

1. **Create the IAM role** with the policies above
2. **Attach the role to Databricks**:
   - Go to AWS Console → Databricks workspace settings
   - Add the IAM role as an instance profile
3. **Configure in Databricks**:
   - Admin Console → Instance Profiles → Add the role ARN
4. **Assign to cluster**:
   - When creating/editing a cluster, select the instance profile under "Advanced Options"

## Best Practices

- **Use Query instead of Scan** when possible (more efficient and cost-effective)
- **Implement pagination** for large tables to avoid timeouts
- **Consider reading capacity** - DynamoDB scans consume read capacity units
- **Cache results** in Databricks if you need to access the data multiple times
- **Use Global Secondary Indexes** if available for better query performance
