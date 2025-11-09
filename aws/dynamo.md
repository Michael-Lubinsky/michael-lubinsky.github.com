### Throttling
<https://vladholubiev.com/articles/five-ways-to-deal-with-aws-dynamodb-gsi-throttling>
```
Throttling occurs when requests to DynamoDB exceed the provisioned throughput capacity. 
When this happens, database performance may be affected, and the service returns HTTP 400 status codes 
with an error type of ProvisionedThroughputExceededException.

Global Secondary Indexes (GSIs) are a powerful feature allowing you to create additional access patterns for your data.
They have their own read and write capacity provisioned separately from the base table. 
DynamoDB offers two types of capacity modes: provisioned and on-demand.  
```

## Export table to file  in jsonl format (1 json line per record)
```
aws dynamodb scan --table-name chargeminder-car-telemetry --output json \
  | jq -c '.Items[]' > export.jsonl
```  

If you want to strip DynamoDB’s data-type wrappers ({"S": "value"}, {"N": "123"}), use AWS’s --projection-expression or a small Python helper (see below)

### pure JSONL output

```python
import boto3, json
from boto3.dynamodb.types import TypeDeserializer

dynamodb = boto3.client('dynamodb')
table_name = 'YourTableName'

deserializer = TypeDeserializer()
items = []
last_key = None

with open('export.jsonl', 'w') as f:
    while True:
        if last_key:
            response = dynamodb.scan(
                TableName=table_name,
                ExclusiveStartKey=last_key
            )
        else:
            response = dynamodb.scan(TableName=table_name)
        
        for item in response['Items']:
            python_item = {k: deserializer.deserialize(v) for k, v in item.items()}
            f.write(json.dumps(python_item) + '\n')
        
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
```
Add these lines at the end if you want to push it to an S3 bucket:
```
import boto3
s3 = boto3.client('s3')
s3.upload_file('export.jsonl', 'your-s3-bucket-name', 'exports/export.jsonl')
```

## Export table to file  in json  format (many lines for single json)

```python
import boto3, json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('YourTableName')

items = []
response = table.scan()
items.extend(response['Items'])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

with open('export.json', 'w') as f:
    json.dump(items, f, indent=2)

# To push to S3 directly:
#-------------------------
 
import boto3, json

s3 = boto3.client('s3')
s3.put_object(
    Bucket='your-s3-bucket',
    Key='export.json',
    Body=json.dumps(items)
)
```
## Global Secondary Index (GSI)

<https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html>

<https://dynobase.dev/dynamodb-gsi/>

```
aws dynamodb list-tables
```
Here are the AWS CLI commands to get detailed information about a specific DynamoDB table:

## 1. Get Complete Table Description
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME
```

This returns comprehensive information including:
- Primary key (partition key and sort key if exists)
- Global Secondary Indexes (GSI)
- Local Secondary Indexes (LSI)
- Table status, creation date
- Provisioned/on-demand capacity settings
- Stream settings

## 2. Get Just the Key Schema (Primary & Sort Keys)
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME --query 'Table.KeySchema'
```

Example output:
```json
[
    {
        "AttributeName": "userId",
        "KeyType": "HASH"
    },
    {
        "AttributeName": "timestamp",
        "KeyType": "RANGE"
    }
]
```
- `HASH` = Partition Key (Primary Key)
- `RANGE` = Sort Key

## 3. Get Global Secondary Indexes (GSI)
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME --query 'Table.GlobalSecondaryIndexes'
```

## 4. Get Approximate Item Count
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME --query 'Table.ItemCount'
```

**Note**: This count is updated approximately every 6 hours, so it may not be real-time accurate.

## Exact count
```bash
aws dynamodb scan \
    --table-name <your-table-name> \
    --select "COUNT" \


aws dynamodb scan \
    --table-name <your-table-name> \
    --select "COUNT" \
    --query "Count"

```
## Python approx and exact count
``` python
import boto3

def get_approx_count(table_name, region="us-east-1"):
    client = boto3.client("dynamodb", region_name=region)
    response = client.describe_table(TableName=table_name)
    return response["Table"]["ItemCount"]

if __name__ == "__main__":
    table = "chargeminder-car-telemetry"
    count = get_approx_count(table)
    print(f"Approximate item count in {table}: {count}")


import boto3

def get_exact_count(table_name, region="us-east-1"):
    dynamodb = boto3.client("dynamodb", region_name=region)
    total = 0
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = dynamodb.scan(
                TableName=table_name,
                Select="COUNT",
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = dynamodb.scan(
                TableName=table_name,
                Select="COUNT"
            )
        total += response["Count"]
        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return total

if __name__ == "__main__":
    table = "chargeminder-car-telemetry"
    count = get_exact_count(table)
    print(f"Exact item count in {table}: {count}")

```
## 5. One-Liner for Key Info
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME \
  --query '{Keys:Table.KeySchema, ItemCount:Table.ItemCount, GSI:Table.GlobalSecondaryIndexes[*].IndexName}'
```

## 6. Pretty Output with JQ (if you have jq installed)
```bash
aws dynamodb describe-table --table-name YOUR_TABLE_NAME | jq '{
  TableName: .Table.TableName,
  Keys: .Table.KeySchema,
  ItemCount: .Table.ItemCount,
  GSI: .Table.GlobalSecondaryIndexes // []
}'
```

Replace `YOUR_TABLE_NAME` with your actual table name!


### PartiQL 
In the DynamoDB console’s left navigation, select PartiQL editor.

PartiQL lets you run SQL-like statements such as:

SELECT * FROM "MyTable" WHERE id = '123';

Here are quick PartiQL patterns you can paste into the **PartiQL editor** in the DynamoDB console to get distinct values—both for top-level attributes and JSON (map/list) fields.

### 1) Top-level attribute

```sql
-- Distinct values of a top-level string/number attribute
SELECT DISTINCT "status"
FROM "Orders";
```

Optionally scope it (recommended) so you don’t scan the whole table:

```sql
SELECT DISTINCT "status"
FROM "Orders"
WHERE "pk" = 'CUSTOMER#123';
```

### 2) Nested JSON (map) attribute using dot path

```sql
-- Distinct values of a nested map attribute: product.info.category
SELECT DISTINCT product.info.category
FROM "Products" AS product
WHERE attribute_exists(product.info.category);
```

### 3) Nested map when the key has spaces/special chars (bracket access)

```sql
-- If the map key needs quoting (e.g., "sub category")
SELECT DISTINCT details['sub category']
FROM "Products" AS p
WHERE attribute_exists(p.details['sub category']);
```

### 4) Distinct elements from a list (UNNEST)

```sql
-- Each item has a list attribute tags: ["red","sale","outdoor"]
-- Get distinct tag values across matching items
SELECT DISTINCT tag
FROM "Products" AS p
UNNEST p.tags AS tag
WHERE attribute_exists(p.tags);
```

### 5) Clean up missing/NULLs and limit results

```sql
SELECT DISTINCT p.info.category
FROM "Products" AS p
WHERE attribute_exists(p.info.category)
LIMIT 100;
```

## Notes & tips

* **DISTINCT** removes duplicates in the projection; there’s no need for `GROUP BY` (and DynamoDB PartiQL doesn’t support full SQL aggregation/grouping like a relational DB).
* Use **dot paths** (`a.b.c`) for simple map keys; use **bracket paths** (`a['weird key']`) for keys with spaces/special characters.
* Prefer adding a **key condition** (e.g., `WHERE pk = ...`) to avoid a full table scan whenever possible.
* `attribute_exists(path)` helps exclude items where the field is missing.

If you show me your table/attribute shape (top-level vs nested, map vs list), I’ll tailor the exact PartiQL for your case.




## Clean DynamoDB JSON records and remove the type qualifiers while maintaining valid JSON, you have several options:

### Method 1: AWS SDK Unmarshalling (Recommended)

Most AWS SDKs provide built-in methods to convert DynamoDB JSON to standard JSON:

**JavaScript/Node.js:**
```javascript
const AWS = require('aws-sdk');
const dynamoDbClient = new AWS.DynamoDB();

// Using unmarshall from DynamoDB DocumentClient utils
const { unmarshall } = AWS.DynamoDB.Converter;

const dynamoDbRecord = {
  "name": {"S": "John Doe"},
  "age": {"N": "30"},
  "active": {"BOOL": true},
  "tags": {"SS": ["developer", "manager"]}
};

const cleanJson = unmarshall(dynamoDbRecord);
console.log(cleanJson);
// Output: { name: "John Doe", age: 30, active: true, tags: ["developer", "manager"] }
```

**Python (boto3):**
```python
import boto3
from boto3.dynamodb.types import TypeDeserializer

deserializer = TypeDeserializer()

dynamodb_record = {
    "name": {"S": "John Doe"},
    "age": {"N": "30"},
    "active": {"BOOL": True}
}

clean_json = {k: deserializer.deserialize(v) for k, v in dynamodb_record.items()}
print(clean_json)
# Output: {'name': 'John Doe', 'age': 30, 'active': True}
```

### Method 2: Custom Parsing Function

If you need a custom solution:

**JavaScript:**
```javascript
function cleanDynamoDbJson(obj) {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(cleanDynamoDbJson);
  }
  
  // Check if this is a DynamoDB attribute type
  const keys = Object.keys(obj);
  if (keys.length === 1) {
    const typeKey = keys[0];
    const value = obj[typeKey];
    
    switch (typeKey) {
      case 'S': return value; // String
      case 'N': return Number(value); // Number
      case 'BOOL': return value; // Boolean
      case 'NULL': return null;
      case 'SS': return value; // String Set
      case 'NS': return value.map(Number); // Number Set
      case 'BS': return value; // Binary Set
      case 'M': return cleanDynamoDbJson(value); // Map
      case 'L': return value.map(cleanDynamoDbJson); // List
      default: 
        // Not a DynamoDB type, process as regular object
        break;
    }
  }
  
  // Regular object - process all properties
  const result = {};
  for (const key in obj) {
    result[key] = cleanDynamoDbJson(obj[key]);
  }
  return result;
}

// Usage
const dynamoRecord = {
  "user": {
    "M": {
      "name": {"S": "Alice"},
      "age": {"N": "25"},
      "preferences": {
        "M": {
          "theme": {"S": "dark"},
          "notifications": {"BOOL": true}
        }
      }
    }
  }
};

const cleaned = cleanDynamoDbJson(dynamoRecord);
console.log(JSON.stringify(cleaned, null, 2));
```

### Method 3: Using jq (Command Line)

For processing JSON files with jq:

```bash
# Simple transformation for common types
jq 'walk(if type == "object" and has("S") then .S 
         elif type == "object" and has("N") then (.N | tonumber)
         elif type == "object" and has("BOOL") then .BOOL
         elif type == "object" and has("NULL") then null
         else . end)' input.json
```

The AWS SDK unmarshalling approach is generally recommended as it handles all DynamoDB data types correctly and is well-tested. The custom parsing approach gives you more control but requires handling all the DynamoDB type mappings yourself.
