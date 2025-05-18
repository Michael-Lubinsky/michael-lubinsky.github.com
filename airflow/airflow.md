
### Airflow

A DAG Run is an instance of a DAG, representing a specific execution of the DAG.

DagBag is a collection of DAGs, typically from a directory on the file system. It parses and loads DAGs for the scheduler to manage.

The scheduler is responsible for scheduling jobs, monitoring DAGs, and triggering tasks.

### airflow.cfg
The airflow.cfg file is used to configure the Airflow environment,  
including database connections and executor settings.

Airflow logs ang global variables
can be configured in the airflow.cfg file, specifying the logging level and log location.
```
[logging]
base_log_folder = /path/to/logs
remote_logging = True
remote_log_conn_id = my_s3_conn

[variables]
key = value
```
### Variables
```bash 
airflow variables set key value
```

```python
my_var = Variable.get("my_variable")
```

### Task priorities
Task priorities can be set using the priority_weight parameter in the task definition.
```python 
  task = BashOperator(
       task_id='bash_example',
       bash_command='echo "Hello World"',
       priority_weight=10,
       dag=dag)
```

### How to skip task
Tasks can be skipped using the SkipMixin class or by setting conditions within a task.
```python 
from airflow.models import SkipMixin
class MyTask(SkipMixin, BaseOperator):
    def execute(self, context):
       if condition:
          self.skip(
               context['dag_run'],
               context['ti'].task_id,
               context['execution_date']
          )
```

### Task failures

Task failures can be handled by setting up retries, using the _on_failure_callback_, or configuring alerts.
```python 
def failure_callback(context):
   print("Task failed")

task = BashOperator(
    task_id='bash_example',
    bash_command='exit 1',
    on_failure_callback=failure_callback,
    dag=dag)
```


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

### Managing tasks dependencies dynamically

| Use Case                                                   | Best Option                                      |
| ---------------------------------------------------------- | ------------------------------------------------ |
| Logic based on code at DAG parse time (static)             | Regular Python (`if`, loops)                     |
| Fan-out/fan-in pattern with predictable structure          | `TaskGroup`, Python loops                        |
| Condition at runtime that chooses a path                   | ✅ `BranchPythonOperator`                         |
| Conditional continuation based on upstream success/failure | `TriggerRule`                                    |
| Bypass certain tasks entirely                              | `ShortCircuitOperator` or `BranchPythonOperator` |


1. Use plain Python control flow (e.g., if statements) in DAG definition
You can build task dependencies dynamically using regular Python logic—this is done at DAG parsing time, not at execution time.

```python
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from datetime import datetime

dag = DAG('dynamic_deps_example', start_date=datetime(2023, 1, 1), schedule_interval=None)

start = DummyOperator(task_id='start', dag=dag)
end = DummyOperator(task_id='end', dag=dag)

# Dynamically decide which tasks to run
some_flag = True  # this is evaluated at DAG parse time!

if some_flag:
    task_a = DummyOperator(task_id='task_a', dag=dag)
    start >> task_a >> end
else:
    task_b = DummyOperator(task_id='task_b', dag=dag)
    start >> task_b >> end
```

 2. Use TaskGroup or loops for dynamic fan-out/fan-in patterns
You can dynamically generate tasks and assign dependencies in a loop:

```python
from airflow.operators.dummy import DummyOperator
from airflow.utils.task_group import TaskGroup

with DAG('loop_deps_dag', start_date=datetime(2023, 1, 1), schedule_interval=None) as dag:
    start = DummyOperator(task_id='start')
    end = DummyOperator(task_id='end')

    with TaskGroup("dynamic_tasks") as dynamic_group:
        for i in range(3):
            t = DummyOperator(task_id=f'task_{i}')
            start >> t >> end

```

3. Use TriggerRule for conditional downstream execution
If you don't want to branch but want some tasks to run conditionally, you can use TriggerRule:
```python
from airflow.operators.dummy import DummyOperator
from airflow.utils.trigger_rule import TriggerRule

t1 = DummyOperator(task_id='t1', dag=dag)
t2 = DummyOperator(task_id='t2', dag=dag)
t3 = DummyOperator(task_id='t3', dag=dag, trigger_rule=TriggerRule.ONE_SUCCESS)

# even if only t1 or t2 succeeds, t3 will run
[t1, t2] >> t3
```



### BranchPythonOperator

Use BranchPythonOperator when you need to dynamically choose the execution path at runtime,   
based on conditions that are only known during execution (like values from dag_run.conf, external system state, or task output)

When to Prefer BranchPythonOperator:
1. You need runtime decision-making:
```python
def choose_branch(**kwargs):
    if kwargs['dag_run'].conf.get('use_path_a') == True:
        return 'task_a'
    else:
        return 'task_b'
```
2.   **Different branches require different tasks or flows**
    
    -   E.g., for conditional workflows like:
        
        -   Process full dataset vs. just metadata
            
        -   Daily vs. weekly logic
            
        -   Run different pipelines based on input type or date
            
3.   **You want downstream tasks to be skipped automatically**
    
    -   Airflow will **skip non-selected branches** and their downstream tasks.
        
    -   This integrates cleanly with the DAG state view and helps avoid confusion about which path was taken.


If you return more than one task ID from a BranchPythonOperator, it must be a list of task IDs:
```python
return ['task_a', 'task_b']
```
And downstream tasks not returned will be skipped unless you use TriggerRule=ALL_DONE or similar.

Example:
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
    'retries': 3
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
    retries=3,
    retry_delay=timedelta(minutes=5),
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

### TriggerRule

TriggerRule defines how a task decides whether it should run, based on the state of its upstream tasks. This is especially important for tasks with multiple upstream dependencies or tasks that follow conditional branches (like with BranchPythonOperator).

✅ Default Behavior
By default, tasks in Airflow use:

trigger_rule='all_success'  
Which means: "Run this task only if all upstream tasks succeeded."

| TriggerRule             | Description                                                                         |
| ----------------------- | ----------------------------------------------------------------------------------- |
| `all_success` (default) | Runs if **all upstream** tasks succeeded                                            |
| `all_failed`            | Runs if **all upstream** tasks failed                                               |
| `all_done`              | Runs if **all upstream** tasks are in any terminal state (success, failed, skipped) |
| `one_success`           | Runs if **any one** upstream task succeeded                                         |
| `one_failed`            | Runs if **any one** upstream task failed                                            |
| `none_failed`           | Runs if **no upstream tasks failed** (skipped is allowed)                           |
| `none_skipped`          | Runs if **no upstream tasks were skipped**                                          |
| `always`                | Always runs, regardless of upstream states                                          |



#### Sensor Operators: 
Wait for an external condition to be met before proceeding.   
Examples: FileSensor (waiting for a file) and ExternalTaskSensor (waiting for another DAG to complete).
```python
from airflow.sensors.filesystem import FileSensor
file_sensor_task = FileSensor(
    task_id='wait_for_file',
    filepath='/path/to/file',
    dag=dag)


file_sensor = FileSensor(
    task_id='wait_for_file',
    filepath='/path/to/your/file.txt',
    fs_conn_id='fs_default',  # or another connection ID if needed
    poke_interval=30,         # check every 30 seconds
    timeout=600,              # timeout after 10 minutes
    retries=2,                # retry 2 times if the task fails
    mode='poke',              # or 'reschedule' for more efficient resource usage
    dag=dag
)
```
### Passing parameters to task
Parameters can be passed using the _op_args_ and _op_kwargs_ arguments in the task definition.
```python

def my_function(arg1, arg2, kwarg1=None):
    print(f"arg1: {arg1}")
    print(f"arg2: {arg2}")
    print(f"kwarg1: {kwarg1}")

python_task = PythonOperator(
   task_id='python_example',
   python_callable=my_function,
   op_args=['hello', 'world'],          # Positional arguments
   op_kwargs={'kwarg1': 'Airflow'},     # Keyword arguments

   dag=dag
)
```

### dug_run.conf

### What is stored in `dag_run.conf`?

It stores **custom user-defined parameters**, like:
```json
{
  "source": "s3://my-bucket/data.csv",
  "run_mode": "full",
  "threshold": 0.9
}
```

These are **not system-generated**, but values **you specify when triggering the DAG**. They're accessible inside tasks via `kwargs['dag_run'].conf` (in PythonOperators, for example).

* * *

### 🔍 Where it's used:

#### ✅ Trigger DAG with conf (CLI):
 

`airflow dags trigger my_dag_id --conf '{"source": "input.csv", "retries": 2}'`

#### ✅ Access in PythonOperator:
```python
def my_task(**kwargs):
    conf = kwargs['dag_run'].conf
    source = conf.get('source')
    print(f"Source file: {source}")

```
#### ✅ Access in templated fields (Jinja):


`bash_command="echo {{ dag_run.conf['source'] }}"`

* * *

### 🧠 Use cases:

-   Passing file paths, config flags, or parameters to control task behavior.
    
-   Dynamic branching, thresholds, or job metadata.
    
-   Triggering parameterized ETL pipelines.



### provide_context (obsolete)

The new-style PythonOperator (from airflow.operators.python) does not need provide_context=True.

You typically use context when you want to:

Access runtime info (e.g., execution_date, dag_run.conf)

Perform logic based on run-specific values

Context is always passed to the function via **kwargs.  
So this is enough in Airflow 2.x:
```python
from airflow.operators.python import PythonOperator

def my_task(**kwargs):
    print(kwargs['execution_date'])

task = PythonOperator(
    task_id='my_task',
    python_callable=my_task
)
```

_provide_context_ passes context variables to the task’s callable function,  
allowing access to metadata and other information.
```python 
def my_function(**kwargs):
    execution_date = kwargs['execution_date']

python_task = PythonOperator(
    task_id='python_example',
    python_callable=my_function,
   provide_context=True,
   dag=dag)
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

Example 1:
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
Example 2:

```python
from airflow.decorators import dag, task
@dag(
  schedule_interval='@daily',
  start_date=days_ago(2))

def example_dag():
  @task
  def extract(): return 'data'

  @task
  def process(data):
    return f'processed {data}'

data = extract()
process(data)
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
```bash 
airflow dags backfill -s 2021-01-01 - e 2021-01-07 example_dag
```
### Pools
Pools are used to limit the execution parallelism on resources like database connections.
```bash
airflow pools set my_pool 5 "Description of the pool"
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
### Timeout

```python
task = BashOperator(
   task_id='bash_example',
   bash_command='sleep 300',
   execution_timeout=timedelta(minutes = 5),
   dag=dag)
```
### SubDagOperator
The SubDagOperator is used to define a sub-DAG within a DAG.   
It is useful for organizing and reusing parts of workflows.

```python
from airflow.operators.subdag import SubDagOperator
subdag_task = SubDagOperator(task_id='subdag', subdag=subdag, dag=dag)
```
###  Task testing

airflow test example_dag my_task 2024-05-17

airflow test does:
It runs a specific task from a DAG for a given execution_date.

It bypasses the scheduler and all dependencies—upstream or downstream.

It does not trigger the DAG or mark any tasks as successful in the metadata database.

🔍 Behavior:
It loads the DAG and task definitions from your DAG files.

It runs the task’s logic as if it were executing on that date/time.

It logs output to the console (and optionally to log files).

It does not update task states in the Airflow UI unless you use --save (Airflow 2.6+).

Optional flags (in Airflow 2.6+ and 2.7+):
--save: Persists the task state in the metadata DB.

--dry-run: Only prints the task's context, without actually running the callable.

--env-vars: Passes environment variables to the test run.

🔧 Use cases:
Testing a task’s logic during development.

Debugging failures without running the full DAG.

Verifying context values (**kwargs) for a given execution_date.


airflow test <dag_id> <task_id> <execution_date>

### DAG  testing

DAGs can be tested using the airflow test command or by running them in the Airflow UI in a safe environment.
```bash 
airflow dags test example_dag 2021-01-01
```

Executes the entire DAG in the correct order of dependencies.

Uses the provided execution_date.

Does not persist state in the Airflow metadata DB.

Good for local development or debugging.

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
