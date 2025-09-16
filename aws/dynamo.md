To clean DynamoDB JSON records and remove the type qualifiers while maintaining valid JSON, you have several options:

## Method 1: AWS SDK Unmarshalling (Recommended)

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

## Method 2: Custom Parsing Function

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

## Method 3: Using jq (Command Line)

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
