

## Critical Differences in the Working Policy:

### 1. **Region Specificity** 🎯
```json
// ❌ Didn't work - wildcard region
"arn:aws:dynamodb:*:447759255101:table/chargeminder*"

// ✅ Works - specific region
"arn:aws:dynamodb:us-east-1:447759255101:table/chargeminder*"
```

### 2. **Role Assumption Chain** 🔑 **Most Important**
```json
{
  "Action": ["sts:AssumeRole"],
  "Resource": ["arn:aws:iam::447759255101:role/databricks_dynamodb_service_role"]
}
```

Databricks likely needs to **assume this service role** to actually access DynamoDB. The other policies didn't have this permission.

### 3. **Glue Catalog Permissions** 📚
```json
"glue:GetDatabase", "glue:GetTable", "glue:GetPartitions", ...
```

Databricks often uses **AWS Glue Data Catalog** to discover and access DynamoDB tables as external tables. Without Glue permissions, Databricks can't "see" the DynamoDB tables in its catalog.

### 4. **Broader S3 Permissions**
```json
"Resource": "*"  // vs specific bucket patterns
```

## Why the Original Policies Failed:

The original policies had the DynamoDB permissions but were **missing**:
- ✗ The ability to assume the service role that Databricks actually uses
- ✗ Glue catalog permissions to discover the tables
- ✗ Possibly the correct regional specificity

## Architecture:
```
Databricks → Assume databricks_dynamodb_service_role → Access DynamoDB via Glue Catalog
```

**Bottom line**: The DynamoDB permissions alone aren't enough - you need the **role assumption** and **Glue permissions** for Databricks to actually connect.


Now I can see the **full scope of duplication and security concerns**:

## Analysis of `databricks_dynamodb_s3_glue_access.json`:

### ✅ **Unique/Additional Capabilities** (compared to the other policies):
1. **AWS Glue Catalog** read access - for data catalog/metastore
2. **DynamoDB Export/Backup** operations (`ExportTableToPointInTime`, `CreateBackup`, `DescribeBackup`)
3. **More DynamoDB read actions** (`ConditionCheckItem`, `DescribeContinuousBackups`, `DescribeExport`)
4. **Region-specific**: `us-east-1` only (vs wildcard `*` in other policies)

### 🔴 **Security Concerns**:

#### 1. **Overly Permissive S3 Access**
```json
"Resource": "*"  // Allows access to ALL S3 buckets in the account!
```
This is **dangerous** - should be scoped to specific buckets like `chargeminder*` or `databricks*`.

#### 2. **Circular AssumeRole**
```json
"Resource": ["arn:aws:iam::447759255101:role/databricks_dynamodb_service_role"]
```
The role can assume itself - this is unusual and typically not needed.

### 📊 **Comparison of DynamoDB Permissions Across All Three Policies**:

| Policy | DynamoDB Tables | Region | Extra DynamoDB Actions |
|--------|----------------|--------|----------------------|
| `chargeminder-databricks-s3-access.json` | `chargeminder*` | `*` | Streams |
| `chargeminder-lambda-dynamodb-s3-prod-policy.json` | `chargeminder*` | `*` | Streams |
| `databricks_dynamodb_s3_glue_access.json` | `chargeminder*` | `us-east-1` | Streams + Backup + Export |

### 🎯 **Key Differences Between the Two Databricks Roles**:

| Feature | chargeminder-databricks-s3-access-prod | databricks_dynamodb_service_role |
|---------|----------------------------------------|----------------------------------|
| S3 Access | `chargeminder-2*` only | **ALL buckets** (`*`) ⚠️ |
| Glue Catalog | ❌ No | ✅ Yes |
| DynamoDB Region | All regions (`*`) | `us-east-1` only |
| DynamoDB Export | ❌ No | ✅ Yes |
| Number of Policies | 3 (with duplication) | 1 |

## 🔧 **Recommendations**:

### 1. **Consolidate Roles** (if possible)
Do you need two separate Databricks roles? Consider:
- Are they used by different Databricks workspaces?
- Different teams/environments?
- Different access patterns?

### 2. **Fix S3 Permissions** 🚨 **HIGH PRIORITY**
```json
// Change from:
"Resource": "*"

// To:
"Resource": [
  "arn:aws:s3:::chargeminder-2*",
  "arn:aws:s3:::chargeminder-2*/*",
  "arn:aws:s3:::databricks-*",  // if needed
  "arn:aws:s3:::databricks-*/*"
]
```

### 3. **Remove Circular AssumeRole**
Unless there's a specific reason, remove the self-referencing AssumeRole statement.

### 4. **Remove Duplicate Policies**
From `chargeminder-databricks-s3-access-prod`, keep only ONE policy with DynamoDB permissions.

**Would you like me to provide a consolidated, secure version of these policies?**
