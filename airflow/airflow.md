
### Airflow
#### Action Operators: 
Perform specific actions such as running a Python function, executing a Bash command, or triggering an API call. 
Examples: PythonOperator, BashOperator, and SimpleHttpOperator.
#### Transfer Operators:
Facilitate moving data between systems, such as S3ToGCSOperator or MySqlToPostgresOperator.
#### Sensor Operators: 
Wait for an external condition to be met before proceeding. 
Examples: FileSensor (waiting for a file) and ExternalTaskSensor (waiting for another DAG to complete).

### Hooks
We use Hooks to define interfaces that manage connections to external systems. 
They handle authentication, session management, and other connection-related tasks. 
Hooks are often used within Operators to simplify integration with services like databases or APIs.

#### Database Hooks:
PostgresHook, MySqlHook, and MongoHook for interacting with different database systems.
#### Cloud Service Hooks: 
S3Hook, GCSHook, and AzureBlobStorageHook for connecting to cloud storage.
#### API Hooks: HttpHook: 
For making HTTP requests or interacting with REST APIs.

### Executors
 
Different executors offer varying levels of scalability, concurrency, and complexity 

#### SequentialExecutor
Ideal for testing and development, this executor runs tasks sequentially in a single process. 
It’s simple but unsuitable for production due to its lack of parallelism.
#### LocalExecutor 
supports parallel execution on a single machine using multiple processes. 
It is suitable for small — to medium-sized workflows that require concurrency but don’t need distributed execution.
#### CeleryExecutor 
A distributed task execution framework that uses a message broker (e.g., RabbitMQ or Redis) to distribute tasks across multiple worker nodes. 
It is highly scalable and a common choice for production environments.
#### KubernetesExecutor  
Designed for cloud-native and containerized environments, this executor dynamically creates Kubernetes pods for each task.
It provides excellent resource isolation, scalability, and fault tolerance, making it ideal for large-scale workflows.
#### DebugExecutor 
This executor is primarily used for debugging. 
It runs tasks locally using the same process as the Airflow Scheduler, 
simplifying troubleshooting during DAG development.


#### Generate similar tasks using expand()
```python
from airflow import DAG
from airflow.decorators import task
from datetime import datetime

cities = ['Warsaw', 'London', 'New York', 'Tokyo']
with DAG('weather_check',
         start_date=datetime(2024, 1, 1),
         schedule_interval='@daily'
) as dag:
    @task
    def check_weather(city):
        # In reality, you'd use a weather API here
        print(f"Checking weather for {city}")
    check_weather.expand(city=cities)
```

#### XCOM
<https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html>
```
XCom allows tasks to push and pull small amounts of data during execution.
One task can push a result using xcom_push (or achieve by simply returning in the execute method ) and another task can retrieve that result using xcom_pull.

The way the data in XCom is stored, written, and retrieved can be controlled by the XCom backend. The default one will store the XCom data in the metadata database.
 In addition, we can configure Xcom to be stored in Object Storage or desired custom backend.
```
 
#### TaskFlow API with Direct Communication (instead of Xcom)

Apache Airflow (starting from version 2.4), a new feature called TaskFlow-decorated functions
with direct task-to-task communication has been introduced.
This mechanism allows tasks to pass data to each other directly without relying on XComs. 

Using the TaskFlow API, you can define tasks as Python functions and pass outputs from one task as inputs to another. 
Airflow handles the passing of data internally, bypassing the need to explicitly push and pull XComs.

Example:
```python
from airflow.decorators import dag, task
from datetime import datetime

@dag(schedule=None, start_date=datetime(2023, 1, 1), catchup=False)
def taskflow_direct_communication():
    @task
    def generate_data():
        return {"key": "value", "number": 42}

    @task
    def process_data(data):
        print(f"Processing data: {data}")

    # Direct communication: output of `generate_data` becomes input of `process_data`
    data = generate_data()
    process_data(data)

dag_instance = taskflow_direct_communication()
```
#### TriggerDagRunOperator 
DAG 1
```python
@dag(start_date=datetime(2025, 3, 6), schedule_interval=None)
def data_cleaning_dag():

    @task()
    def extract_data():
        # Code to extract data
        return "Raw data extracted"

    @task()
    def clean_data():
        # Code to clean the extracted data
        return "Data cleaned"

    @task()
    def trigger_next_dag():
        # Trigger DAG 2 (Data Processing)
        trigger = TriggerDagRunOperator(
            task_id='trigger_data_processing',
            trigger_dag_id='data_processing_dag',
            conf={"clean_data": "processed"},
            dag=data_cleaning_dag
        )
        return trigger

    extract = extract_data()
    clean = clean_data()
    trigger = trigger_next_dag()

    extract >> clean >> trigger

data_cleaning_instance = data_cleaning_dag()
```
### Task Groups and Pools

<https://medium.com/@mcgeehan/task-groups-and-pools-in-apache-airflow-872ee02da3bd>

#### Links

https://blog.det.life/stop-creating-multiple-airflow-dags-for-reloads-and-parallel-processing-3912974b5866

https://medium.com/codex/notifications-in-airflow-using-callbacks-725d009423e2

https://blog.devgenius.io/managing-cluster-termination-in-apache-airflow-dags-00626dd945a3

https://medium.com/@swathireddythokala16/youtube-trend-analysis-pipeline-etl-with-airflow-spark-s3-and-docker-85a7d76992eb

https://medium.com/apache-airflow/apache-airflow-2-0-tutorial-41329bbf7211

https://medium.com/indiciumtech/apache-airflow-best-practices-bc0dd0f65e3f

https://medium.com/datavidhya/understand-apache-airflow-like-never-before-311c00ef0e5a 

https://medium.com/data-science/stop-creating-bad-dags-optimize-your-airflow-environment-by-improving-your-python-code-146fcf4d27f7

https://medium.com/plum-fintech/dbt-airflow-50b2c93f91cc

https://medium.com/dev-genius/airflow-interview-questions-iv-cef5100d44c5 
