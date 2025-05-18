
### Airflow

A DAG Run is an instance of a DAG, representing a specific execution of the DAG.

The airflow.cfg file is used to configure the Airflow environment,
including database connections and executor settings.

#### Action Operators: 
Perform specific actions such as running a Python function, executing a Bash command, or triggering an API call.   
Examples: PythonOperator, BashOperator, and SimpleHttpOperator.
#### Transfer Operators:
Facilitate moving data between systems, such as S3ToGCSOperator or MySqlToPostgresOperator.

Dependencies are set using bitshift operators (>>, <<) or the set_upstream and set_downstream methods.

python start >> task_1 task_1 >> end or  
task_1.set_upstream(start) task_1.set_downstream(end)
```bash
airflow dags list

airflow connections
add my_conn --conn-type mysql --conn-host localhost --conn-login root --conn-password root

airflow dags pause example_dag
airflow dags unpause example_dag
```
### Dynamic task dependencies
Task dependencies can be set dynamically within a DAG definition based on runtime conditions.

```python
if condition: task_1 >> task_2 else: task_1 >> task_3
```

### Branch operator
```python
from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime
import random

# Define the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 10, 1),
    'retries': 1,
}

dag = DAG(
    'branching_example',
    default_args=default_args,
    description='A simple branching DAG',
    schedule_interval=None,
)

# Define the branching logic
def decide_branch():
    # Randomly choose a path
    if random.choice([True, False]):
        return 'task_a'  # Task ID to follow if True
    else:
        return 'task_b'  # Task ID to follow if False

# Branching task
branch_task = BranchPythonOperator(
    task_id='branch_task',
    python_callable=decide_branch,
    dag=dag,
)

# Tasks for different branches
task_a = DummyOperator(
    task_id='task_a',
    dag=dag,
)

task_b = DummyOperator(
    task_id='task_b',
    dag=dag,
)

# Final task after branching
final_task = DummyOperator(
    task_id='final_task',
    dag=dag,
    trigger_rule='none_failed',  # Ensures it runs regardless of which branch is taken
)

# Define task dependencies
branch_task >> [task_a, task_b]  # Branch task leads to either task_a or task_b
task_a >> final_task  # task_a leads to final_task
task_b >> final_task  # task_b leads to final_task

```
Another example of branch operator
```python
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime

def check_file():
    file_found = True # Replace with actual file check logic
    return ‘load_to_bq’ if file_found else ‘send_alert’
def load_to_bq():
    print(“Loading to BigQuery…”)
def send_alert():
    print(“File not found! Sending alert…”)

with DAG(‘conditional_execution_dag’,
  start_date=datetime(2023, 1, 1),
  schedule_interval=’@daily’,
  catchup=False) as dag:
     start = DummyOperator(task_id=’start’)
     branch = BranchPythonOperator(
     task_id=’branching’,
     python_callable=check_file
)

task_load = PythonOperator(
    task_id=’load_to_bq’,
    python_callable=load_to_bq
)
task_alert = PythonOperator(
    task_id=’send_alert’,
    python_callable=send_alert
)
end = DummyOperator(task_id=’end’, trigger_rule=’none_failed_min_one_success’)
start >> branch >> [task_load, task_alert] >> end
```

#### Sensor Operators: 
Wait for an external condition to be met before proceeding.   
Examples: FileSensor (waiting for a file) and ExternalTaskSensor (waiting for another DAG to complete).
```python
python from airflow.sensors.filesystem import FileSensor
file_sensor_task = FileSensor(task_id='wait_for_file', filepath='/path/to/file', dag=dag)
```
### Passing parameters to task
Parameters can be passed using the _op_args_ and _op_kwargs_ arguments in the task definition.
```python 
python_task = PythonOperator(
   task_id='python_example',
   python_callable=my_function,
   op_args=['arg1'],
   dag=dag
)
```

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
One task can push a result using xcom_push (or achieve by simply returning in the execute method)
and another task can retrieve that result using xcom_pull.

The way the data in XCom is stored, written, and retrieved can be controlled by the XCom backend.
The default one will store the XCom data in the metadata database.
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

### Datasets vs Sensors


#### Datasets:
Datasets were introduced in Apache Airflow 2.4, released in August 2022  
Focus on data dependencies, triggering downstream DAGs when a dataset is updated by a producer task. 
They abstract the scheduling logic to react to data changes,  
such as a file being written or a database table being updated.  
Operate at the DAG level, using a passive, event-driven model.  
A producer task marks a dataset as updated upon successful completion,    
and Airflow’s scheduler triggers dependent DAGs automatically. No active polling is required.
Ideal for orchestrating complex, data-dependent pipelines where DAGs should run only after specific data is available or updated,   
e.g., triggering a reporting DAG after a data ingestion DAG updates a table.

Datasets: Enable cross-DAG dependencies natively, simplifying data lineage and visualization in the Airflow UI. 
They support one-to-many or many-to-one relationships between DAGs and datasets.

Failure Handling:
Datasets: A dataset is marked as updated only if the producer task succeeds,
ensuring downstream DAGs don’t run on failed or incomplete data.

```python
from airflow import Dataset
from airflow.decorators import dag, task
example_dataset = Dataset("s3://bucket/example.csv")

@dag(schedule=None)
def producer():
    @task(outlets=[example_dataset])
    def update_data():
        # Write to dataset
        pass
    update_data()

@dag(schedule=[example_dataset])
def consumer():
    @task
    def process_data():
        # Read from dataset
        pass
    process_data()
```
#### Sensors: 
Actively poll for specific conditions or events, such as the presence of a file, a database row, or an API response. 
They are tasks within a DAG that pause execution until a criterion is met.  
Run as tasks within a DAG, actively checking (or "poking") for a condition at set intervals (e.g., every 60 seconds). 
This can consume resources, especially for long-running checks.  
Suited for waiting on external events or conditions within a single DAG,  
e.g., checking if a file exists in an S3 bucket before processing it.

Typically manage dependencies within a DAG or require specific implementations 
(e.g., ExternalTaskSensor) for cross-DAG coordination, which can be less intuitive and harder to maintain.

Failure Handling:  
Can be configured to handle exceptions (e.g., soft_fail or silent_fail),  
but their success depends on the condition being met, regardless of data integrity unless explicitly coded.

```python
from airflow import DAG
from airflow.sensors.s3_key_sensor import S3KeySensor
from airflow.operators.python import PythonOperator
from datetime import datetime

def process_data():
    # Process file
    pass

with DAG(dag_id="sensor_example", start_date=datetime(2025, 1, 1)) as dag:
    check_file = S3KeySensor(
        task_id="check_s3_file",
        bucket_key="s3://bucket/example.csv",
        poke_interval=60,
        timeout=3600
    )
    process_task = PythonOperator(
        task_id="process_data",
        python_callable=process_data
    )
    check_file >> process_task
```

### Backfill
bash airflow dags backfill -s 2021-01-01 - e 2021-01-07 example_dag

### Pools
Pools are used to limit the execution parallelism on resources like database connections.
```
bash airflow pools set my_pool 5 "Description of the pool"
```
### SLA
SLAs are used to set time limits for tasks, with alerts triggered if the time is exceeded.
```python 
task = BashOperator(
    task_id='bash_example',
    bash_command='echo "Hello World"',
    dag=dag,
    sla=timedelta(minutes=30)
)
```

{% comment %}
#### Links

https://blog.det.life/stop-creating-multiple-airflow-dags-for-reloads-and-parallel-processing-3912974b5866

https://medium.com/codex/notifications-in-airflow-using-callbacks-725d009423e2

https://blog.devgenius.io/managing-cluster-termination-in-apache-airflow-dags-00626dd945a3

https://medium.com/@swathireddythokala16/youtube-trend-analysis-pipeline-etl-with-airflow-spark-s3-and-docker-85a7d76992eb

https://medium.com/apache-airflow/apache-airflow-2-0-tutorial-41329bbf7211

https://medium.com/@databy-uav/dbt-and-bashcommand-effectively-utilizing-dbt-core-functionality-with-airflow-f369375c6ef1

https://medium.com/indiciumtech/apache-airflow-best-practices-bc0dd0f65e3f

https://medium.com/datavidhya/understand-apache-airflow-like-never-before-311c00ef0e5a 

https://medium.com/data-science/stop-creating-bad-dags-optimize-your-airflow-environment-by-improving-your-python-code-146fcf4d27f7

https://medium.com/@vmpavan/airflow-interview-question-conditional-task-execution-with-branchpythonoperator-hey-folks-3e2f8fc09a64

https://medium.com/plum-fintech/dbt-airflow-50b2c93f91cc

https://medium.com/dev-genius/airflow-interview-questions-iv-cef5100d44c5 

{% endcomment %}
