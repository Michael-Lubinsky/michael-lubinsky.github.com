<https://github.com/Sharashchandra/s3ranger>

<https://github.com/stelviodev/stelvio>

Stelvio is a Python framework that simplifies AWS cloud infrastructure management and deployment. It lets you define your cloud infrastructure using pure Python, with smart defaults that handle complex configuration automatically.


#### Bash Script to Find Orphaned S3 Buckets


Prerequisites:

AWS CLI v2 installed and configured with proper IAM permissions (s3:ListBuckets & s3:ListObjects).  
jq (optional, for JSON parsing).


```bash
#!/usr/bin/env bash
aws s3api list-buckets --query "Buckets[].Name" --output text \
  | tr ' ' '\n' \
  | while read bucket; do aws s3api list-objects \
      --bucket "$bucket" --max-items 1 --query "length(Contents)" --output text \
      | grep -q '^0$' && echo "$bucket"; done
```      

### Boto3

Boto3 library, which is the AWS SDK for Python. Boto3 allows you to interact with all AWS services, including S3.

First, you need to install Boto3:

pip install boto3

Before running the examples, ensure you have your AWS credentials configured.  
Boto3 looks for credentials in several places, including:

Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN  
AWS credentials file: ~/.aws/credentials  
AWS config file: ~/.aws/config  
IAM roles for EC2 instances: If running on an EC2 instance, Boto3 will automatically use the associated IAM role.  
 

#### 1. Basic S3 Client and Resource
Boto3 offers two ways to interact with AWS services:

Client: A low-level service client that maps directly to the S3 API operations. This is generally preferred for granular control.
Resource: A higher-level, object-oriented interface that abstracts away some of the complexities. Useful for simpler operations.

```python

import boto3
import os

# --- Configuration (replace with your actual values or env vars) ---
# It's better to configure AWS credentials via environment variables or ~/.aws/credentials
# For demonstration purposes, you can explicitly set them here, but not recommended for production.
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_REGION = 'us-east-1' # Or your desired region

# If you have credentials configured, you can just do:
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

# If you need to specify credentials and region explicitly (less common if configured):
# s3_client = boto3.client(
#     's3',
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION
# )
# s3_resource = boto3.resource(
#     's3',
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION
# )

print("S3 client and resource initialized.")

# --- Example Bucket Name (replace with your own) ---
BUCKET_NAME = "my-unique-test-bucket-12345abcdefg"
```
#### 2. Create a Bucket
```python

try:
    # Client method
    s3_client.create_bucket(Bucket=BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' created successfully.")
except Exception as e:
    if 'BucketAlreadyOwnedByYou' in str(e):
        print(f"Bucket '{BUCKET_NAME}' already exists and is owned by you.")
    else:
        print(f"Error creating bucket: {e}")
```
#### 3. List Buckets
```python

print("\n--- Listing Buckets ---")
response = s3_client.list_buckets()
print("Existing buckets:")
for bucket in response['Buckets']:
    print(f"  - {bucket['Name']}")
```
#### 4. Upload a File
You can upload a file from your local system. Let's create a dummy file first.

```python

# Create a dummy file
dummy_file_name = "hello_s3.txt"
with open(dummy_file_name, "w") as f:
    f.write("Hello, S3! This is a test file.")

# Define the S3 object key (path within the bucket)
s3_object_key = "my_folder/hello_s3.txt"

print(f"\n--- Uploading '{dummy_file_name}' to S3 as '{s3_object_key}' ---")
try:
    # Client method: upload_file(Filename, Bucket, Key)
    s3_client.upload_file(dummy_file_name, BUCKET_NAME, s3_object_key)
    print(f"'{dummy_file_name}' uploaded successfully to '{BUCKET_NAME}/{s3_object_key}'.")

    # Resource method: bucket.upload_file(Filename, Key)
    # bucket = s3_resource.Bucket(BUCKET_NAME)
    # bucket.upload_file(dummy_file_name, s3_object_key.replace("my_folder/", "my_other_folder/"))
    # print(f"'{dummy_file_name}' uploaded successfully using resource.")

except Exception as e:
    print(f"Error uploading file: {e}")

# Clean up dummy file
os.remove(dummy_file_name)
```
Uploading content directly (not from a file):

```python

print("\n--- Uploading string content directly ---")
content_to_upload = "This content was uploaded directly as a string."
s3_direct_upload_key = "direct_uploads/string_content.txt"

try:
    s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_direct_upload_key, Body=content_to_upload)
    print(f"String content uploaded successfully to '{BUCKET_NAME}/{s3_direct_upload_key}'.")
except Exception as e:
    print(f"Error uploading string content: {e}")
```
#### 5. List Objects in a Bucket
```python

print(f"\n--- Listing Objects in '{BUCKET_NAME}' ---")
try:
    # Client method
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

    if 'Contents' in response:
        print("Objects in bucket:")
        for obj in response['Contents']:
            print(f"  - {obj['Key']} (Size: {obj['Size']} bytes)")
    else:
        print("No objects found in the bucket.")

except Exception as e:
    print(f"Error listing objects: {e}")
```
#### 6. Download a File
```Python

# Define local path for download
downloaded_file_name = "downloaded_s3_file.txt"

print(f"\n--- Downloading '{s3_object_key}' from S3 to '{downloaded_file_name}' ---")
try:
    # Client method: download_file(Bucket, Key, Filename)
    s3_client.download_file(BUCKET_NAME, s3_object_key, downloaded_file_name)
    print(f"File downloaded successfully to '{downloaded_file_name}'.")

    # Verify content
    with open(downloaded_file_name, "r") as f:
        print(f"Content of downloaded file: {f.read()}")

    # Resource method: bucket.download_file(Key, Filename)
    # bucket = s3_resource.Bucket(BUCKET_NAME)
    # bucket.download_file(s3_object_key, "downloaded_via_resource.txt")
    # print(f"File downloaded successfully using resource.")

except Exception as e:
    print(f"Error downloading file: {e}")

# Clean up downloaded file
os.remove(downloaded_file_name)
Downloading content directly (to a string):

Python

print(f"\n--- Downloading content of '{s3_direct_upload_key}' directly ---")
try:
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_direct_upload_key)
    body = response['Body'].read().decode('utf-8')
    print(f"Content of '{s3_direct_upload_key}':")
    print(body)
except Exception as e:
    print(f"Error downloading direct content: {e}")
```
#### 7. Copy an Object
```Python

source_object_key = s3_object_key
destination_object_key = "copied_folder/copied_hello_s3.txt"
copy_source = {'Bucket': BUCKET_NAME, 'Key': source_object_key}

print(f"\n--- Copying '{source_object_key}' to '{destination_object_key}' ---")
try:
    s3_client.copy_object(CopySource=copy_source, Bucket=BUCKET_NAME, Key=destination_object_key)
    print(f"'{source_object_key}' copied successfully to '{destination_object_key}'.")
except Exception as e:
    print(f"Error copying object: {e}")
```
#### 8. Delete an Object
```Python

print(f"\n--- Deleting objects ---")
objects_to_delete = [s3_object_key, s3_direct_upload_key, destination_object_key]

for obj_key in objects_to_delete:
    try:
        # Client method
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj_key)
        print(f"Object '{obj_key}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting object '{obj_key}': {e}")
```
#### 9. Delete a Bucket (Requires Emptying First)
You must delete all objects in a bucket before you can delete the bucket itself.

```Python

print(f"\n--- Attempting to delete bucket '{BUCKET_NAME}' ---")
try:
    # First, list and delete all remaining objects in the bucket
    bucket_resource = s3_resource.Bucket(BUCKET_NAME)
    bucket_resource.objects.all().delete()
    print(f"All objects in bucket '{BUCKET_NAME}' deleted.")

    # Then delete the bucket
    s3_client.delete_bucket(Bucket=BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' deleted successfully.")
except Exception as e:
    print(f"Error deleting bucket: {e}")
```
    
Important Considerations:
Error Handling: Always include robust try-except blocks to handle potential errors from S3 API calls.

Pagination: For list_objects_v2 (and similar listing operations), if a bucket contains many objects, the response might be truncated. You'll need to use pagination to retrieve all results. Boto3's paginators simplify this.

Large Files: For very large files, consider using upload_file and download_file with the Config parameter to set transfer concurrency and part size for optimal performance. Boto3 automatically handles multipart uploads/downloads.
Presigned URLs: For granting temporary, time-limited access to objects without exposing your AWS credentials, use presigned URLs.

```Python

# Example: Generate a presigned URL to download an object
# object_key = "my_folder/hello_s3.txt" # Assuming this object still exists
# try:
#     response_url = s3_client.generate_presigned_url(
#         'get_object',
#         Params={'Bucket': BUCKET_NAME, 'Key': object_key},
#         ExpiresIn=3600 # URL valid for 1 hour
#     )
#     print(f"Presigned URL for '{object_key}': {response_url}")
# except Exception as e:
#     print(f"Error generating presigned URL: {e}")
```

Versioning: If your bucket has versioning enabled, delete_object will create a delete marker. To permanently delete specific versions, you need to provide the VersionId.

Security: Follow AWS best practices for security:

Least Privilege: Grant only the necessary IAM permissions to your S3 users/roles.

Access Keys: Avoid hardcoding access keys directly in your code. Use environment variables, IAM roles, or the ~/.aws/credentials file.

Encryption: Consider enabling server-side encryption (SSE-S3, SSE-KMS, SSE-C) for your objects.



<https://awstip.com/10-best-python-scripts-to-automate-your-daily-tasks-in-aws-85f847c66247>

<https://github.com/michaelthomasletts/boto3-refresh-session>

The issue is that **boto3 doesn't automatically use your AWS CLI SSO profile**. You need to explicitly tell boto3 which profile to use.

---

## Solution: Specify the Profile in boto3

### Option 1: Pass Profile to boto3 Session (Recommended)

```python
import boto3

# Use the same profile name from your AWS CLI
session = boto3.Session(
    profile_name='PowerUserAccess-592210015395',
    region_name='us-east-1'
)

dynamodb = session.client('dynamodb')
response = dynamodb.describe_table(TableName='t')
print(response)
```

### Option 2: Set Environment Variable

Before running your Python code:

```bash
# In terminal
export AWS_PROFILE=PowerUserAccess-592210015395

# Then run your Python script
python your_script.py
```

In Python:
```python
import os
import boto3

# Set programmatically
os.environ['AWS_PROFILE'] = 'PowerUserAccess-592210015395'

session = boto3.Session(region_name='us-east-1')
dynamodb = session.client('dynamodb')
response = dynamodb.describe_table(TableName='t')
```

---

## For Databricks Usage

If you're running this code in **Databricks**, SSO profiles won't work because Databricks doesn't have access to your local `~/.aws/config` file.

### Solution for Databricks:

**Option A: Use IAM Role (Best Practice)**

Attach an IAM role to your Databricks cluster (the one we discussed earlier):

```python
import boto3

# No credentials needed - uses cluster's IAM role
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
response = dynamodb.describe_table(TableName='t')
```

**Option B: Use AWS Secrets in Databricks**

Store your credentials in Databricks secrets:

```bash
# In Databricks CLI or notebook
databricks secrets create-scope --scope aws-credentials
databricks secrets put --scope aws-credentials --key aws-access-key-id
databricks secrets put --scope aws-credentials --key aws-secret-access-key
```

Then in your code:
```python
import boto3

# Retrieve from Databricks secrets
aws_access_key = dbutils.secrets.get(scope="aws-credentials", key="aws-access-key-id")
aws_secret_key = dbutils.secrets.get(scope="aws-credentials", key="aws-secret-access-key")

session = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-east-1'
)

dynamodb = session.client('dynamodb')
response = dynamodb.describe_table(TableName='t')
```

**Option C: Assume Role with SSO Credentials**

If you need to assume a role from your SSO session:

```python
import boto3

# First, get temporary credentials from your SSO session
session = boto3.Session(profile_name='PowerUserAccess-592210015395')
sts = session.client('sts')

# Assume a role (if needed)
assumed_role = sts.assume_role(
    RoleArn='arn:aws:iam::592210015395:role/YourRoleName',
    RoleSessionName='databricks-session'
)

credentials = assumed_role['Credentials']

# Use temporary credentials
dynamodb = boto3.client(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['SessionToken']
)

response = dynamodb.describe_table(TableName='t')
```

---

## Complete Working Example for Local Testing

```python
import boto3

def get_dynamodb_client(profile_name='PowerUserAccess-592210015395', region='us-east-1'):
    """
    Create a DynamoDB client using AWS SSO profile
    """
    try:
        session = boto3.Session(
            profile_name=profile_name,
            region_name=region
        )
        dynamodb = session.client('dynamodb')
        
        # Test connection
        dynamodb.list_tables(Limit=1)
        print(f"✅ Successfully connected using profile: {profile_name}")
        
        return dynamodb
        
    except Exception as e:
        print(f"❌ Error connecting to DynamoDB: {str(e)}")
        print("\nTroubleshooting:")
        print(f"1. Ensure your SSO session is active: aws sso login --profile {profile_name}")
        print(f"2. Check your profile exists: aws configure list-profiles")
        raise

# Usage
dynamodb = get_dynamodb_client()
response = dynamodb.describe_table(TableName='t')
print(f"\nTable name: {response['Table']['TableName']}")
print(f"Item count: {response['Table']['ItemCount']}")
```

---

## Quick Checklist

Before running your code, verify:

```bash
# 1. Check your SSO session is active
aws sso login --profile PowerUserAccess-592210015395

# 2. Verify profile works
aws sts get-caller-identity --profile PowerUserAccess-592210015395

# 3. List your profiles
aws configure list-profiles

# 4. Test DynamoDB access
aws dynamodb list-tables --profile PowerUserAccess-592210015395
```

---

## For Your Databricks Code

Update your incremental load function:

```python
from datetime import datetime
from pyspark.sql import SparkSession
import boto3

def incremental_load_dynamodb(table_name, profile_name=None):
    """
    Load incremental data from DynamoDB to Delta Lake
    
    Args:
        table_name: DynamoDB table name
        profile_name: AWS profile name (only for local testing)
    """
    # For Databricks: uses cluster IAM role
    # For local: uses specified profile
    if profile_name:
        session = boto3.Session(
            profile_name=profile_name,
            region_name='us-east-1'
        )
        dynamodb = session.resource('dynamodb')
    else:
        # Databricks will use cluster's IAM role
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    table = dynamodb.Table(table_name)
    
    # ... rest of your code
```

**Usage:**
```python
# Local testing
incremental_load_dynamodb('t', profile_name='PowerUserAccess-592210015395')

# In Databricks (with IAM role)
incremental_load_dynamodb('t')
```

---

## Summary

**For local development:**
```python
session = boto3.Session(
    profile_name='PowerUserAccess-592210015395',
    region_name='us-east-1'
)
dynamodb = session.client('dynamodb')
```

**For Databricks:**
Use IAM role attached to cluster (no profile needed):
```python
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
```

Does this solve your issue?
