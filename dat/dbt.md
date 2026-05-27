### DBT **data build tool**

It is a tool for transforming data inside a data warehouse using SQL.

Below is a simple **dbt pipeline** .

Assume source tables:

```text
T(d, user_id, value)
K(user_id, user_name)
```

Goal table:

```text
daily_user_value_summary(d, user_name, value_sum)
```

## 1. dbt model: `models/daily_user_value_summary.sql`

```sql
{{ config(
    materialized='incremental',
    unique_key=['d', 'user_name']
) }}

SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM {{ source('raw', 'T') }} t
JOIN {{ source('raw', 'K') }} k
    ON t.user_id = k.user_id

{% if is_incremental() %}
WHERE t.d > (
    SELECT COALESCE(MAX(d), DATE '1900-01-01')
    FROM {{ this }}
)
{% endif %}

GROUP BY
    t.d,
    k.user_name
```

This creates/updates an incremental summary table.

---

## 2. Define sources: `models/sources.yml`

```yaml
version: 2

sources:
  - name: raw
    schema: your_schema_name
    tables:
      - name: T
      - name: K
```

Replace:

```yaml
schema: your_schema_name
```

with your real schema.

---

## 3. Run dbt

```bash
dbt run --select daily_user_value_summary
```

---

## 4. If you want materialized view instead

For a simple view:

```sql
{{ config(materialized='view') }}

SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM {{ source('raw', 'T') }} t
JOIN {{ source('raw', 'K') }} k
    ON t.user_id = k.user_id
GROUP BY
    t.d,
    k.user_name
```

For most Databricks/Snowflake pipelines,   use the **incremental table** version, not a view, especially if table `T` is large.

Correct — in dbt you usually **do not write `INSERT` or `UPDATE` manually**.

You write only a `SELECT` model:

```sql
SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM T t
JOIN K k
    ON t.user_id = k.user_id
GROUP BY
    t.d,
    k.user_name
```

Then dbt generates the actual SQL behind the scenes.

For example:

```sql
{{ config(
    materialized='table'
) }}

SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM {{ source('raw', 'T') }} t
JOIN {{ source('raw', 'K') }} k
    ON t.user_id = k.user_id
GROUP BY
    t.d,
    k.user_name
```

With:

```sql
materialized='table'
```

dbt effectively does something like:

```sql
CREATE OR REPLACE TABLE daily_user_value_summary AS
SELECT ...
```

With:

```sql
materialized='incremental'
```

dbt generates warehouse-specific `INSERT` or `MERGE` logic for you.

Example:

```sql
{{ config(
    materialized='incremental',
    unique_key=['d', 'user_name']
) }}

SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM {{ source('raw', 'T') }} t
JOIN {{ source('raw', 'K') }} k
    ON t.user_id = k.user_id

{% if is_incremental() %}
WHERE t.d >= (
    SELECT COALESCE(MAX(d), DATE '1900-01-01')
    FROM {{ this }}
)
{% endif %}

GROUP BY
    t.d,
    k.user_name
```

On an incremental run, dbt may generate something conceptually like:

```sql
MERGE INTO daily_user_value_summary AS target
USING new_data AS source
ON target.d = source.d
AND target.user_name = source.user_name

WHEN MATCHED THEN UPDATE SET
    value_sum = source.value_sum

WHEN NOT MATCHED THEN INSERT (
    d,
    user_name,
    value_sum
)
VALUES (
    source.d,
    source.user_name,
    source.value_sum
);
```

So the important idea is:

```text
You write SELECT.
dbt writes CREATE / INSERT / MERGE / UPDATE depending on materialization.
```

For your case, the best dbt model is probably:

```sql
{{ config(
    materialized='incremental',
    unique_key=['d', 'user_name']
) }}

SELECT
    t.d,
    k.user_name,
    SUM(t.value) AS value_sum
FROM {{ source('raw', 'T') }} t
JOIN {{ source('raw', 'K') }} k
    ON t.user_id = k.user_id

{% if is_incremental() %}
WHERE t.d >= current_date() - INTERVAL 1 DAY
{% endif %}

GROUP BY
    t.d,
    k.user_name
```

This recalculates recent daily summaries and lets dbt merge them into the target table.

Not exactly.

In:

```bash
dbt run --select daily_user_value_summary
```

the value after `--select` is **not the destination table name**.

It is the **dbt model name**.

Usually the model name comes from the SQL filename.

Example:

```text
models/daily_user_value_summary.sql
```

Then:

```bash
dbt run --select daily_user_value_summary
```

means:

> “Run this dbt model.”

---

# How destination table is determined

The actual destination table is determined by:

* model name
* schema
* database
* alias config
* target profile

---

# Default behavior

Suppose file:

```text
models/daily_user_value_summary.sql
```

contains:

```sql
{{ config(materialized='table') }}

SELECT ...
```

dbt will typically create:

```text
<database>.<schema>.daily_user_value_summary
```

---

# Example

Suppose profile target is:

```yaml
database: analytics
schema: gold
```

Then dbt creates:

```text
analytics.gold.daily_user_value_summary
```

---

# You can override table name

Using:

```sql
{{ config(
    alias='user_daily_summary'
) }}
```

Then model:

```text
daily_user_value_summary.sql
```

creates table:

```text
user_daily_summary
```

even though command remains:

```bash
dbt run --select daily_user_value_summary
```

because selection uses model name, not final table name.

---

# Important distinction

## dbt model name

Derived from file name:

```text
daily_user_value_summary.sql
```

---

## Database table name

Derived from:

* model name
* alias
* schema
* database
* target

---

# Mental model

Think of:

```bash
dbt run --select X
```

as:

> “Execute transformation X”

NOT:

> “Insert into table X”

---

# You can see generated SQL

Useful command:

```bash
dbt compile
```

Then inspect:

```text
target/compiled/
```

to see actual generated SQL including:

* CREATE TABLE
* MERGE
* INSERT
* etc.

---

# Example full flow

File:

```text
models/summaries/daily_user_value_summary.sql
```

Command:

```bash
dbt run --select daily_user_value_summary
```

Generated target table:

```text
analytics.gold.user_daily_summary
```

if config contains:

```sql
{{ config(
    schema='gold',
    alias='user_daily_summary'
) }}
```

[dbt Labs](https://www.getdbt.com/)

Documentation:

[dbt Documentation](https://docs.getdbt.com/)

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
dbt has many built-in Jinja functions, macros, configurations, and special keywords.
They are not all the same category, but people often loosely call all of them “dbt keywords”.

The most important groups are:

* Jinja functions/macros (`ref`, `source`, `config`)
* Materializations (`table`, `view`, `incremental`)
* Config keys (`materialized`, `schema`, `tags`)
* Special variables (`this`, `target`)
* Control structures (`is_incremental`)
* YAML resource properties

Official reference:

[dbt Jinja Reference](https://docs.getdbt.com/reference/dbt-jinja-functions?utm_source=chatgpt.com)

---

### 1. Most important dbt functions/macros

| Keyword                             | Purpose                         |
| ----------------------------------- | ------------------------------- |
| `ref()`                             | Reference another model         |
| `source()`                          | Reference source table          |
| `config()`                          | Configure model                 |
| `var()`                             | Read project variable           |
| `env_var()`                         | Read environment variable       |
| `run_query()`                       | Execute SQL during compilation  |
| `log()`                             | Write to logs                   |
| `exceptions.raise_compiler_error()` | Throw compilation error         |
| `adapter.dispatch()`                | Adapter-specific macro dispatch |
| `return()`                          | Return value from macro         |
| `print()`                           | Print debug output              |
| `doc()`                             | Reference documentation block   |
| `fromjson()`                        | Parse JSON                      |
| `tojson()`                          | Convert to JSON                 |
| `fromyaml()`                        | Parse YAML                      |
| `toyaml()`                          | Convert YAML                    |
| `as_bool()`                         | Cast to boolean                 |
| `as_number()`                       | Cast to number                  |
| `as_native()`                       | Native Python conversion        |

---

### 2. Most important special objects

| Keyword          | Meaning                    |
| ---------------- | -------------------------- |
| `this`           | Current model relation     |
| `target`         | Current target profile     |
| `model`          | Current model metadata     |
| `graph`          | DAG graph                  |
| `project_name`   | dbt project name           |
| `schema`         | Current schema             |
| `execute`        | Whether actually executing |
| `flags`          | CLI flags                  |
| `invocation_id`  | Current run UUID           |
| `run_started_at` | Run timestamp              |
| `adapter`        | Current warehouse adapter  |

---

### 3. Most important config keywords

Usually used inside:

```jinja
{{ config(...) }}
```

---

## Materialization

| Keyword                | Meaning                    |
| ---------------------- | -------------------------- |
| `materialized`         | view/table/incremental/etc |
| `incremental_strategy` | merge/append/etc           |
| `unique_key`           | incremental merge key      |

Example:

```sql
{{ config(
    materialized='incremental',
    unique_key='user_id'
) }}
```

---

## Storage/layout configs

| Keyword         | Meaning             |
| --------------- | ------------------- |
| `schema`        | Target schema       |
| `database`      | Target database     |
| `alias`         | Override table name |
| `partition_by`  | Partition columns   |
| `cluster_by`    | Clustering columns  |
| `file_format`   | Delta/Parquet/etc   |
| `location_root` | External location   |

Databricks-specific configs exist too.

---

## Metadata configs

| Keyword        | Meaning               |
| -------------- | --------------------- |
| `tags`         | Tag models            |
| `meta`         | Custom metadata       |
| `persist_docs` | Persist comments/docs |

---

### 4. Materialization keywords

| Keyword       | Meaning                 |
| ------------- | ----------------------- |
| `table`       | Physical table          |
| `view`        | SQL view                |
| `incremental` | Incremental processing  |
| `ephemeral`   | Inline CTE              |
| `snapshot`    | Slowly changing history |
| `seed`        | CSV-loaded table        |

---

### 5. Incremental keywords

| Keyword              | Meaning                     |
| -------------------- | --------------------------- |
| `is_incremental()`   | True during incremental run |
| `unique_key`         | Merge key                   |
| `_dbt_max_partition` | Internal partition tracking |

Example:

```sql
{% if is_incremental() %}
WHERE updated_at > (
    SELECT max(updated_at)
    FROM {{ this }}
)
{% endif %}
```

---

### 6. Source-related keywords

| Keyword           | Meaning             |
| ----------------- | ------------------- |
| `source()`        | Reference source    |
| `freshness`       | Freshness checks    |
| `loaded_at_field` | Freshness timestamp |

Example:

```sql
SELECT *
FROM {{ source('raw', 'events') }}
```

---

### 7. Testing keywords

In YAML:

| Keyword           | Meaning                  |
| ----------------- | ------------------------ |
| `tests`           | Attach tests             |
| `unique`          | Built-in uniqueness test |
| `not_null`        | Null check               |
| `accepted_values` | Allowed values           |
| `relationships`   | FK relationship test     |

Example:

```yaml
columns:
  - name: user_id
    tests:
      - unique
      - not_null
```

---

### 8. Snapshot keywords

| Keyword                   | Meaning            |
| ------------------------- | ------------------ |
| `strategy`                | timestamp/check    |
| `updated_at`              | Timestamp column   |
| `check_cols`              | Columns to compare |
| `invalidate_hard_deletes` | Track deletes      |

---

### 9. Macro keywords

| Keyword    | Meaning             |
| ---------- | ------------------- |
| `macro`    | Define macro        |
| `endmacro` | End macro           |
| `call`     | Call block macro    |
| `set`      | Variable assignment |
| `do`       | Execute expression  |

Example:

```jinja
{% macro hello(name) %}
    hello {{ name }}
{% endmacro %}
```

---

### 10. Jinja control flow keywords

These come from Jinja itself:

| Keyword   | Meaning          |
| --------- | ---------------- |
| `if`      | Conditional      |
| `elif`    | Else-if          |
| `else`    | Else             |
| `for`     | Loop             |
| `endfor`  | End loop         |
| `endif`   | End if           |
| `set`     | Variable         |
| `include` | Include template |

Example:

```jinja
{% for col in cols %}
    {{ col }}
{% endfor %}
```

---

### 11. Common CLI commands

Not keywords, but very important.

| Command             | Meaning          |
| ------------------- | ---------------- |
| `dbt run`           | Build models     |
| `dbt test`          | Run tests        |
| `dbt seed`          | Load CSVs        |
| `dbt snapshot`      | Run snapshots    |
| `dbt docs generate` | Generate docs    |
| `dbt docs serve`    | Serve docs       |
| `dbt compile`       | Compile SQL      |
| `dbt debug`         | Validate setup   |
| `dbt clean`         | Remove artifacts |
| `dbt deps`          | Install packages |

---

### 12. Databricks-specific dbt configs

Very relevant for your environment.

| Keyword               | Meaning            |
| --------------------- | ------------------ |
| `file_format='delta'` | Delta Lake         |
| `partition_by`        | Delta partitioning |
| `cluster_by`          | Clustering         |
| `tblproperties`       | Delta table props  |
| `liquid_clustered_by` | Liquid clustering  |

Example:

```sql
{{ config(
    materialized='table',
    file_format='delta',
    partition_by=['date']
) }}
```

---

### Most commonly used in real projects

These are the ones you will constantly see:

```jinja
ref()
source()
config()
var()
this
target
is_incremental()
```

and:

```jinja
materialized='table'
materialized='incremental'
unique_key=
partition_by=
tags=
```

---

### Small realistic example

```sql
{{ config(
    materialized='incremental',
    unique_key='event_id',
    partition_by=['date']
) }}

SELECT
    *
FROM {{ source('raw', 'events') }}

{% if is_incremental() %}
WHERE updated_at >
(
    SELECT max(updated_at)
    FROM {{ this }}
)
{% endif %}
```

This single file already demonstrates many core dbt concepts.


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

