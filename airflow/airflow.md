
### Airflow

#### Communtication between tasks (instead of XCOM)

Apache Airflow (starting from version 2.4), a new feature called TaskFlow-decorated functions
with direct task-to-task communication has been introduced.
This mechanism allows tasks to pass data to each other directly without relying on XComs. 

TaskFlow API with Direct Communication
--------------------------------------
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
#### Links

https://medium.com/apache-airflow/apache-airflow-2-0-tutorial-41329bbf7211

https://medium.com/indiciumtech/apache-airflow-best-practices-bc0dd0f65e3f

https://medium.com/datavidhya/understand-apache-airflow-like-never-before-311c00ef0e5a 

https://medium.com/data-science/stop-creating-bad-dags-optimize-your-airflow-environment-by-improving-your-python-code-146fcf4d27f7

https://medium.com/plum-fintech/dbt-airflow-50b2c93f91cc

https://medium.com/dev-genius/airflow-interview-questions-iv-cef5100d44c5 
