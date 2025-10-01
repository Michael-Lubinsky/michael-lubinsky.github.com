import boto3
from boto3.dynamodb.conditions import Key
session = boto3.Session(region_name='us-east-1')
dynamodb = session.resource("dynamodb")
chargeminder_tables = [ 
        "chargeminder-car-telemetry",
        "chargeminder-charge-events",
        "chargeminder-charge-plan-history",
        "chargeminder-charge-plans",
        "chargeminder-charge-regions",
        "chargeminder-event-log",
        "chargeminder-participant-events",
        "chargeminder-user-metadata",
        "chargeminder-user-quizzes",
        "chargeminder-user-surveys",
        ]
def get_table_info(table_name):
    """
    Get DynamoDB table information: Keys, item count, and GSI
    """
    session = boto3.Session(
        profile_name='PowerUserAccess-592210015395',
        region_name='us-east-1')

    dynamodb = session.client('dynamodb')
    
    try:
        # Get table description
        response = dynamodb.describe_table(TableName=table_name)
        table = response['Table']
        
        # Extract key schema
        keys = table['KeySchema']
        
        # Extract item count (approximate)
        item_count = table['ItemCount']
        
        # Extract Global Secondary Indexes (if exist)
        gsi = table.get('GlobalSecondaryIndexes', None)
        
        # Format the output
        result = {
            'TableName': table['TableName'],
            'Keys': keys,
            'ItemCount': item_count,
            'GSI': gsi
        }
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def print_table_info(table_name):
    """
    Print table information in a readable format
    """
    info = get_table_info(table_name)
    
    if info:
        print(f"\n=== Table: {info['TableName']} ===\n")
        
        print("Keys:")
        for key in info['Keys']:
            key_type = "Partition Key" if key['KeyType'] == 'HASH' else "Sort Key"
            print(f"  - {key['AttributeName']} ({key_type})")
        
        print(f"\nItem Count: {info['ItemCount']:,}")
        
        if info['GSI']:
            print(f"\nGlobal Secondary Indexes ({len(info['GSI'])}):")
            for gsi in info['GSI']:
                print(f"  - {gsi['IndexName']}")
                print(f"    Keys: {gsi['KeySchema']}")
        else:
            print("\nGlobal Secondary Indexes: None")


# Usage
if __name__ == "__main__":
  for table_name in chargeminder_tables:  
    print(table_name)
    print('------ print_table_info -------')
    print_table_info(table_name)
    print('------  get_table_info. -------')
    info = get_table_info(table_name)
    print(info)
    break
 