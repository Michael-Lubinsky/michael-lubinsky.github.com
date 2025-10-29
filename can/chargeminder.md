```python
import boto3
boto3_session = boto3.Session(
    botocore_session=dbutils.credentials.getServiceCredentialsProvider("chargeminder-dynamodb-creds"),
    region_name="us-east-1"
)
dynamodb = boto3_session.resource('dynamodb')

response = dynamodb_client.list_tables()
table_names = response['TableNames']

print("DynamoDB ChargeMinder Tables:")
for table_name in table_names:
  if table_name.startswith('chargeminder')  :
    table = dynamodb.Table(table_name)
    print(f"TABLE  - {table_name}")
    print(f"Item count: {table.item_count}")
    print(f"Key schema: {table.key_schema}")
    print()

table = dynamodb.Table('chargeminder-car-telemetry')
# Replace with your table name
 

# Scan all items
response = table.scan()
items = response['Items']

print(f"Found {len(items)} items")
for i, item in enumerate(items):
    print("item number", i)
    print(item)
    print()
    print()
```



```json
{'signals': [
        {'name': 'PreciseLocation', 'code': 'location-preciselocation', 'group': 'Location', 'status': {'error': {'type': 'PERMISSION', 'code': None
                }, 'value': 'ERROR'
            }
        },
        {'name': 'TimeToComplete', 'code': 'charge-timetocomplete', 'body': {'value': Decimal('40')
            }, 'meta': {'retrievedAt': Decimal('1761681348999'), 'oemUpdatedAt': Decimal('1761679903000')
            }, 'group': 'Charge', 'status': {'error': {'type': 'COMPATIBILITY', 'code': 'VEHICLE_NOT_CAPABLE'
                }, 'value': 'ERROR'
            }
        },
        {'name': 'IsCharging', 'code': 'charge-ischarging', 'body': {'value': False
            }, 'meta': {'retrievedAt': Decimal('1761682265645'), 'oemUpdatedAt': Decimal('1761681895000')
            }, 'group': 'Charge'
        },
        {'name': 'TraveledDistance', 'code': 'odometer-traveleddistance', 'body': {'value': Decimal('7581.62'), 'unit': 'km'
            }, 'meta': {'retrievedAt': Decimal('1761682262695'), 'oemUpdatedAt': Decimal('1761682084000')
            }, 'group': 'Odometer'
        }
    ], 'recorded_at': '2025-10-28 20: 11: 06', 'meta': {'mode': 'LIVE', 'deliveryId': '15067a78-baea-4fcd-bf4c-03d7cc7c571f', 'webhookId': 'ee75b19a-615c-4382-9a6d-c4b733fa84b9', 'signalCount': Decimal('4'), 'webhookName': 'Webhook', 'version': '4.0', 'deliveredAt': Decimal('1761682265846')
    }, 'triggers': [
        {'type': 'SIGNAL_UPDATED', 'signal': {'name': 'IsCharging', 'code': 'charge-ischarging', 'group': 'Charge'
            }
        }
    ], 'event_id': '6f5b2960-c53e-4d1b-9543-777db7b65f03', 'user': {'id': 'e01616a9-e113-42b1-a903-048a71012a66'
    }, 'smartcar_user_id': 'e01616a9-e113-42b1-a903-048a71012a66', 'record_type': 'ALL', 'vehicle': {'model': 'RAV4 PRIME XSE AWD SUV', 'id': '8c33efaf-f042-4e13-8533-32e23ca916f3', 'make': 'TOYOTA', 'year': Decimal('2023')
    }
}
```
  
