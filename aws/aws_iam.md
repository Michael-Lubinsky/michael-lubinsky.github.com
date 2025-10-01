 **AWS IAM (Identity and Access Management)** concepts 

## 1. What is IAM?

IAM is the **security and identity management system** for AWS. It controls:

* **Who** (users, apps, services) can access AWS resources
* **What actions** they can perform
* **On which resources** they can perform them
* **Under what conditions** (e.g., from specific IPs, MFA required)

It’s all about **authentication (who you are)** and **authorization (what you can do)**.

---

## 2. Main Concepts in IAM

### **Users**

* Represent **individual people or applications** that need to access AWS.
* They have **credentials** (username/password for AWS Console or access keys for CLI/API).
* Best practice: avoid long-lived users with keys. Prefer roles.

---

### **Groups**

* A way to **organize users** and attach permissions collectively.
* Example: a “Developers” group might allow read-only access to S3 and write access to DynamoDB.

---

### **Roles**

* Think of a **role as a “temporary identity” with permissions**.
* Roles don’t have passwords or permanent keys.
* Instead, a user, AWS service, or application can **assume a role** to gain its permissions for a limited time.
* Example: An EC2 instance can assume a role to read/write to S3 without embedding access keys.

---

### **Policies**
```
Policies are JSON documents that define permissions. They specify what actions are allowed or denied on which resources. Policies are attached to users, groups, or roles to grant permissions.

 There are two main types:

- Managed policies: Standalone policies you can attach to multiple entities
- Inline policies: Policies directly embedded into a single user, group, or role
```


* JSON documents that **define permissions**.
* Attached to **users, groups, or roles**.
* Structure:

  * **Effect**: `Allow` or `Deny`
  * **Action**: Which API calls are allowed (e.g., `s3:PutObject`)
  * **Resource**: Which resources it applies to (e.g., `arn:aws:s3:::my-bucket/*`)
  * **Condition**: Optional rules (e.g., only if MFA is enabled, or request comes from a certain IP)

Example policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

---

### **Identity Providers (IdPs) & Federation**

* Allow users from outside AWS (like your company’s Active Directory, or Google/Microsoft login) to access AWS **without creating IAM users**.
* They authenticate via SSO (single sign-on), then assume roles in AWS.

---

### **Service-Linked Roles**

* Special roles that AWS services create automatically to perform actions on your behalf.
* Example: Lambda needs a service role to write logs to CloudWatch.

---

### **Trust Policy vs. Permission Policy**

* **Permission policy** → what actions/resources are allowed.
* **Trust policy** → who/what can assume the role.

Example trust policy (for EC2 role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## 3. Putting It All Together

* **User**: Michael (developer at Weavix)
* **Group**: Developers (can read/write DynamoDB, read S3)
* **Role**: `DynamoDBExportRole` (allows full DynamoDB access + write to S3)
* **Policy**: Attached to the role (allow `dynamodb:ExportTableToPointInTime`, `s3:PutObject`)
* **Trust policy**: Allows Databricks service to assume `DynamoDBExportRole`

---

## 4. Best Practices

* **Least privilege**: Only give the minimum permissions needed.
* **Use roles instead of long-lived access keys**.
* **Enable MFA** for users with console access.
* **Use IAM Access Analyzer** to find risky permissions.
* **Rotate credentials** if you must use access keys.

---
Great — here’s a **diagram-style explanation** of AWS IAM concepts and how they connect. I’ll represent it in plain markdown with arrows and boxes:

```text
                +------------------+
                |   IAM User       |
                |  (person/app)    |
                +------------------+
                         |
                         | belongs to
                         v
                +------------------+
                |   IAM Group      |
                |  (optional)      |
                +------------------+
                         |
                         | has
                         v
                +------------------+
                |  Policy (JSON)   |
                | permissions list |
                +------------------+

-------------------------------------------------------

                +------------------+
                |   IAM Role       |
                |  (no password,   |
                |   assumed temp)  |
                +------------------+
                         ^
          assumes        | has trust policy
-------------------------+------------------------------
|                        |
|                        |
v                        v
+------------------+     +------------------+
|  IAM User/App    |     |  AWS Service     |
|  (via STS Assume |     |  (EC2, Lambda,   |
|   Role API)      |     |   Databricks)    |
+------------------+     +------------------+

-------------------------------------------------------

                +------------------+
                | Policy (JSON)    |
                |  - Effect        |
                |  - Action        |
                |  - Resource      |
                |  - Condition     |
                +------------------+
```

### How this flows in practice:

1. **User signs in** with their identity (console or CLI).
2. They may directly have policies or belong to a **group** with policies.
3. Sometimes, instead of permanent policies, they **assume a role** to get **temporary credentials**.
4. Roles use a **trust policy** to decide *who* can assume them.
5. Policies attached to roles define *what* they can do on resources.

---

### Example Walkthrough

* Michael logs into AWS Console as an **IAM user**.
* His user account belongs to the **Developers group**, which has a policy to read DynamoDB.
* He wants to run an export job to S3.
* He assumes the **DynamoDBExportRole**, which trusts Michael’s account and has a policy allowing full DynamoDB + `s3:PutObject`.
* AWS STS gives him **temporary keys** valid for a few hours.
* He uses those keys to run the job → DynamoDB writes to S3.

---
 let’s walk through a **real-world example** where you want to export data from **DynamoDB to S3**.
This requires a **role with two parts**:

1. **Trust policy** (who can assume the role)
2. **Permission policy** (what the role can do once assumed)

---

## 1. Trust Policy (who can assume the role)

Here we say that **DynamoDB service** is allowed to assume the role, so it can perform the export job.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "dynamodb.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

* **Principal** = who can use this role (here it’s DynamoDB service).
* **Action** = `sts:AssumeRole` → standard way to take on a role.
* This means **only DynamoDB** can use this role.

---

## 2. Permission Policy (what the role can do)

This policy allows DynamoDB to write exported data into your S3 bucket.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-export-bucket",
        "arn:aws:s3:::my-export-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abcd-efgh-1234-5678"
    }
  ]
}
```

* First block: lets DynamoDB write objects into your S3 bucket.
* Second block: if your bucket is encrypted with a **KMS key**, this grants encryption permissions.

---

## 3. How it Works in Practice

1. You create this IAM role (say `DynamoDBExportRole`).
2. DynamoDB service assumes it when you run an **Export to S3** job.
3. The trust policy confirms *DynamoDB* is allowed to assume it.
4. The permission policy confirms *what actions* it can perform (write to S3, use KMS).
5. The job runs and DynamoDB writes the exported data into your S3 bucket.

---

### Flow in diagram form:

```text
DynamoDB Service -----> [Assume Role: DynamoDBExportRole]
                              |
                              v
                  +------------------------+
                  | Permission Policy      |
                  | - s3:PutObject         |
                  | - s3:ListBucket        |
                  | - kms:Encrypt/Decrypt  |
                  +------------------------+
                              |
                              v
                         S3 Bucket
```




### AWS IAM for Databrick

There  are several ways to check which IAM role is attached to your Databricks cluster:

## Method 1: From Databricks Workspace UI (Easiest)

### Step-by-Step:

1. **Go to your Databricks workspace**
2. Click on **"Compute"** in the left sidebar
3. Find your cluster and click on its name
4. Click the **"Configuration"** tab
5. Scroll down to **"Advanced options"**
6. Expand **"Instances"** section
7. Look for **"Instance profile ARN"**

You should see something like:
```
arn:aws:iam::592210015395:instance-profile/databricks-instance-profile
```

---

## Method 2: Run Code in a Databricks Notebook

Run this in a notebook attached to your cluster:

```python
import boto3

# Get the IAM role from instance metadata
try:
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    
    print("Account ID:", identity['Account'])
    print("ARN:", identity['Arn'])
    print("User ID:", identity['UserId'])
    
    # Extract role name from ARN
    if 'assumed-role' in identity['Arn']:
        role_name = identity['Arn'].split('/')[-2]
        print(f"\n✅ IAM Role: {role_name}")
    else:
        print("\n❌ No IAM role attached to this cluster")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\nThis likely means no IAM role is attached to the cluster.")
```

---

## Method 3: Check Instance Metadata (More Detailed)

```python
import requests
import json

try:
    # Get instance profile from EC2 metadata
    metadata_url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    
    response = requests.get(metadata_url, timeout=1)
    
    if response.status_code == 200:
        role_name = response.text.strip()
        print(f"✅ IAM Role attached: {role_name}")
        
        # Get more details about the role
        role_details_url = f"{metadata_url}{role_name}"
        role_response = requests.get(role_details_url, timeout=1)
        
        if role_response.status_code == 200:
            credentials = json.loads(role_response.text)
            print(f"\nRole ARN: {credentials.get('RoleArn', 'N/A')}")
            print(f"Expiration: {credentials.get('Expiration', 'N/A')}")
    else:
        print("❌ No IAM role attached to this cluster")
        
except Exception as e:
    print(f"❌ Error accessing metadata: {str(e)}")
    print("This cluster might not have an IAM role attached.")
```

---

## Method 4: Using AWS CLI (If You Have Cluster ID)

If you know your cluster ID:

```bash
# Get cluster details
databricks clusters get --cluster-id YOUR_CLUSTER_ID

# Look for "aws_attributes" -> "instance_profile_arn"
```

Or if you have access to AWS:

```bash
# List all instance profiles
aws iam list-instance-profiles

# Get specific instance profile details
aws iam get-instance-profile --instance-profile-name databricks-instance-profile
```

---

## Method 5: Check Permissions (Test if Role Works)

Test what permissions the role has:

```python
import boto3

def test_iam_permissions():
    """Test various AWS permissions to see what the role can do"""
    
    tests = []
    
    # Test DynamoDB
    try:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        dynamodb.list_tables(Limit=1)
        tests.append(("✅ DynamoDB", "Can list tables"))
    except Exception as e:
        tests.append(("❌ DynamoDB", str(e)))
    
    # Test S3
    try:
        s3 = boto3.client('s3')
        s3.list_buckets()
        tests.append(("✅ S3", "Can list buckets"))
    except Exception as e:
        tests.append(("❌ S3", str(e)))
    
    # Test STS (always works if role exists)
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        tests.append(("✅ STS", f"Identity: {identity['Arn']}"))
    except Exception as e:
        tests.append(("❌ STS", str(e)))
    
    # Print results
    print("IAM Role Permission Tests:")
    print("=" * 60)
    for service, result in tests:
        print(f"{service}: {result}")

test_iam_permissions()
```

---

## What to Look For

The IAM role will be in one of these formats:

**Instance Profile ARN:**
```
arn:aws:iam::592210015395:instance-profile/databricks-instance-profile
```

**Role ARN (from get_caller_identity):**
```
arn:aws:sts::592210015395:assumed-role/databricks-ec2-role/i-1234567890abcdef0
```

---

## If No IAM Role is Attached

If you find that **no IAM role is attached**, you'll see errors like:

```
❌ Unable to locate credentials
❌ No IAM role attached to this cluster
```

**To fix this, you need to:**

1. **Create an IAM role** (we did this earlier with the trust policy)
2. **Create an instance profile** that wraps the role
3. **Attach it to your Databricks cluster**

### Quick Fix - Attach IAM Role:

**In Databricks UI:**
1. Go to **Compute** → Your cluster
2. Click **Edit**
3. Expand **Advanced options** → **Instances**
4. In **Instance profile ARN**, enter:
   ```
   arn:aws:iam::592210015395:instance-profile/YOUR-INSTANCE-PROFILE-NAME
   ```
5. Click **Confirm** and restart the cluster

**Using AWS CLI to create instance profile:**

```bash
# Get your role name (from earlier setup)
ROLE_NAME="dynamodb-to-s3-lambda-role"

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name databricks-dynamodb-profile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name databricks-dynamodb-profile \
  --role-name ${ROLE_NAME}

# Get the ARN to use in Databricks
aws iam get-instance-profile \
  --instance-profile-name databricks-dynamodb-profile \
  --query 'InstanceProfile.Arn' \
  --output text
```

---

## Complete Verification Script

Run this in your Databricks notebook:

```python
import boto3
import requests

print("🔍 Checking IAM Role Configuration...\n")

# Method 1: Check via STS
try:
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print("✅ IAM Role is attached!")
    print(f"   ARN: {identity['Arn']}")
    print(f"   Account: {identity['Account']}")
except Exception as e:
    print(f"❌ No IAM role detected: {str(e)}")

# Method 2: Check via metadata
try:
    metadata_url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    response = requests.get(metadata_url, timeout=1)
    if response.status_code == 200:
        role_name = response.text.strip()
        print(f"\n✅ Instance Profile Role: {role_name}")
except Exception as e:
    print(f"\n❌ Cannot access metadata: {str(e)}")

# Method 3: Test DynamoDB access
try:
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    tables = dynamodb.list_tables(Limit=1)
    print(f"\n✅ DynamoDB access working!")
except Exception as e:
    print(f"\n❌ Cannot access DynamoDB: {str(e)}")
    print("   The IAM role may be missing DynamoDB permissions")
```

---

Does your cluster have an IAM role attached? If not, let me know and I'll help you set it up!
