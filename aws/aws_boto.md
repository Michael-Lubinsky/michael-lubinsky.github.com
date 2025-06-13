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
