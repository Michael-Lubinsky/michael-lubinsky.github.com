
<https://kafka-python.readthedocs.io/en/master/>
#### Kafka Producer:
```python

from kafka import KafkaProducer
import json
from time import sleep
from json import dumps
kafka_servers = ["localhost:9092"]
try:
    topic_name = 'incremental_updates'
    myproducer = KafkaProducer(bootstrap_servers=kafka_servers, value_serializer=lambda x: dumps(x).encode('utf-8'))
    #open file , read and send the data
    f = open("test_file.csv", 'r')
    for msg in f:
    #for e in range(100):
        csv_data = msg
        print(csv_data)
        #data = {'data' : csv_data}
        #myproducer.send('incremental_updates_test', value=data)
        # sleep(300)
        #myproducer.flush()
        future = myproducer.send('incremental_updates_test',value=csv_data)
        # Block for 'synchronous' sends
        try:
            record_metadata = future.get(timeout=10)
        except KafkaError as e:
            # Decide what to do if produce request failed...
            print("kafka producer exception occured\n")
            print(e)
            log.exception()
            pass
# Successful result returns assigned partition and offset
        # print (record_metadata.topic)
        # print (record_metadata.partition)
        # print (record_metadata.offset)
print("total msg sent")
except Exception as e:
    print("kafka producer exception . occured outside\n")
    print(e)
```
#### Kafka Cconsumer:
```python
import kafka
from kafka import KafkaConsumer
from json import loads
# Import sys module
import sys
try:
    # Define server with port
    kafka_servers = ["localhost:9092"]
    # Define topic name from where the message will recieve
    #topicName = 'incremental_updates'
    # Initialize consumer variable
    consumer = KafkaConsumer('incremental_updates_test' ,bootstrap_servers = kafka_servers, enable_auto_commit=True,
                                group_id='my-group1-amit', value_deserializer=lambda x: loads(x.decode('utf-8')))
    #consumer.topics()
    print("list kafka topics")
    #list all the topic_list
    admin_client = kafka.KafkaAdminClient(bootstrap_servers=kafka_servers)
    print(admin_client.list_topics())
    #print(admin_client.describe_topics())

    # Read and print message from consumer
    for msg in consumer:
        #print(msg.value)
        #print("recving data")
        recv_data = msg.value
        #r = recv_data.replace('"', '')
        #record = recv_data.strip('\\n')
        print(recv_data)
except Exception as e:
    print("exception occured in kafka consumer")
    print(e)
sys.exit()
```
#### Create Kafka Topic:
```python
from kafka.admin import KafkaAdminClient, NewTopic
kafka_servers = ["localhost:9092"]
admin_client = KafkaAdminClient(
    bootstrap_servers=kafka_servers,
    client_id='test'
)
topic_list = []
topic_list.append(NewTopic(name="incremental_updates", num_partitions=1, replication_factor=1))
admin_client.create_topics(new_topics=topic_list, validate_only=False)
```

<https://habr.com/en/articles/872976/>
<https://medium.com/@cobch7/kafka-architecture-43333849e0f4>
