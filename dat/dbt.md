### DBT **data build tool**

It is a tool for transforming data inside a data warehouse using SQL.


[dbt Labs](https://www.getdbt.com/?utm_source=chatgpt.com)

Documentation:

[dbt Documentation](https://docs.getdbt.com/?utm_source=chatgpt.com)

GitHub:

[dbt Core GitHub](https://github.com/dbt-labs/dbt-core?utm_source=chatgpt.com)

---

### Main idea

Suppose raw data already exists in:

* Snowflake
* Databricks
* BigQuery
* Redshift
* Postgres

dbt does **not** ingest data.

Instead, dbt transforms existing tables into cleaner analytics tables.

Typical pipeline:

```text
Raw tables  ->  dbt SQL models  ->  analytics tables/marts
```

---

### Example

Suppose you have raw events table:

```sql
raw.events
```

You want daily aggregates:

```sql
SELECT
    user_id,
    COUNT(*) AS events_count
FROM raw.events
GROUP BY user_id
```

In dbt, you place this SQL into a file:

```text
models/user_events.sql
```

Contents:

```sql
SELECT
    user_id,
    COUNT(*) AS events_count
FROM raw.events
GROUP BY user_id
```

Then run:

```bash
dbt run
```

dbt creates table/view automatically.

---

### Why dbt became popular

Before dbt:

* lots of huge ETL scripts
* hidden business logic
* difficult dependencies
* no testing
* no documentation

dbt introduced:

* modular SQL
* dependency graphs
* testing
* version control
* CI/CD
* documentation
* lineage visualization

---

### Core concepts

### 1. Models

A **model** is just a SQL SELECT statement.

Example:

```sql
SELECT *
FROM raw.users
WHERE active = true
```

dbt turns it into:

* table
* view
* incremental table

depending on configuration.

---

### 2. Ref()

dbt models reference each other using:

```jinja
{{ ref('model_name') }}
```

Example:

```sql
SELECT *
FROM {{ ref('users_clean') }}
```

This is extremely important.

dbt automatically:

* builds dependency graph
* orders execution
* tracks lineage

---

### 3. DAG (dependency graph)

dbt creates a directed acyclic graph.

Example:

```text
raw.events
     ↓
events_clean
     ↓
daily_metrics
```

dbt knows build order automatically.

---

### 4. Tests

dbt supports data quality tests.

Example:

```yaml
columns:
  - name: user_id
    tests:
      - not_null
      - unique
```

This automatically generates SQL checks.

---

### 5. Documentation

dbt auto-generates documentation website.

Command:

```bash
dbt docs generate
dbt docs serve
```

Produces:

* lineage graph
* column descriptions
* dependencies

---

### 6. Incremental models

Instead of rebuilding huge tables every run:

```sql
{{ config(materialized='incremental') }}
```

dbt processes only new rows.

Very important for large datasets.

---

### 7. Jinja templating

dbt SQL supports Jinja.

Example:

```sql
SELECT
    {% for col in columns %}
        {{ col }},
    {% endfor %}
FROM T
```

This allows reusable SQL generation.

---

### Typical modern architecture

Common stack:

```text
Kafka/EventHub/S3
        ↓
Raw ingestion
        ↓
Snowflake / Databricks
        ↓
dbt transformations
        ↓
BI dashboards
```

This is very common in:

* Databricks
* Snowflake
* BigQuery ecosystems

---

### dbt + Databricks

dbt works very well with:

* Delta tables
* Unity Catalog
* SQL Warehouse

Typical flow:

```text
Bronze tables
   ↓
Silver models (dbt)
   ↓
Gold analytics marts
```

dbt often implements:

* deduplication
* business rules
* aggregations
* dimensional models

---

### Example dbt model for Databricks

```sql
{{ config(materialized='table') }}

SELECT
    user_id,
    date_trunc('day', timestamp) AS day,
    COUNT(*) AS event_count
FROM {{ ref('raw_events') }}
GROUP BY 1,2
```

---

### dbt materializations

dbt can materialize models as:

| Type        | Meaning        |
| ----------- | -------------- |
| view        | SQL view       |
| table       | physical table |
| incremental | append/update  |
| ephemeral   | inline CTE     |

---

### dbt vs Airflow - Very important distinction.

#### Airflow

Orchestrates workflows.

Example:

* run Spark job
* call API
* start notebook
* execute dbt

---

### dbt - Transforms data using SQL.

dbt is not a general workflow engine.

---

### dbt vs Spark

dbt:

* mostly SQL orchestration
* analytics transformations

Spark:

* distributed computation engine

They complement each other.

---

### dbt project structure

Typical structure:

```text
dbt_project.yml
models/
tests/
macros/
snapshots/
seeds/
```

---

### dbt Core vs dbt Cloud

### dbt Core

Open-source CLI.

Run locally:

```bash
dbt run
```

---

### dbt Cloud

Hosted SaaS platform with:

* scheduler
* UI
* lineage browser
* CI/CD

---

### Why analysts love dbt

Analysts can:

* write SQL
* version control in Git
* review PRs
* build reusable transformations

without deep Spark/Java/Python knowledge.

---

### Very simplified mental model

Think of dbt as:

> “Software engineering for SQL transformations.”

It adds:

* modularity
* testing
* dependency management
* documentation
* deployment

to SQL analytics workflows.

---

# Example end-to-end flow

```text
EventHub/Kafka
    ↓
ADLS/S3
    ↓
Databricks Bronze
    ↓
dbt Silver transformations
    ↓
dbt Gold marts
    ↓
Dashboards
```

This architecture is now extremely common in modern data platforms.


<img width="550" height="404" alt="image" src="https://github.com/user-attachments/assets/bab6d06e-35bc-402f-9c4a-d5f635964cf5" />

<https://docs.getdbt.com/docs/introduction>

<https://github.com/dbt-labs>

<https://awstip.com/day-3-understanding-dbt-core-concepts-models-seeds-snapshots-and-tests-5e4d0c67922f>

<https://blog.det.life/no-data-engineers-dont-need-dbt-30573eafa15e>

 

<https://habr.com/ru/articles/821503/>

<https://habr.com/ru/articles/907540/>

<https://habr.com/ru/companies/bft/articles/858896/>

https://medium.com/apache-airflow/how-we-orchestrate-2000-dbt-models-in-apache-airflow-90901504032d

<https://www.adventofdata.com/modern-data-modeling-start-with-the-end/>

https://medium.com/datamindedbe/use-dbt-and-duckdb-instead-of-spark-in-data-pipelines-9063a31ea2b5


https://www.youtube.com/watch?v=5rNquRnNb4E

https://www.youtube.com/watch?v=5rNquRnNb4E&list=PLy4OcwImJzBLJzLYxpxaPUmCWp8j1esvT

