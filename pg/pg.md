## Postgres
```
brew formulae | grep postgresql@

postgresql@15
postgresql@16
postgresql@17

brew install postgresql@17
brew services start postgresql@17
brew services restart postgresql@17
brew services list
lsof -i tcp:5432

tail -100 /opt/homebrew/var/log/postgresql\@17.log

/opt/homebrew/Cellar/postgresql@17/17.5/bin/createuser

createuser -s postgres
```
This creates a superuser `postgres` role without a password.  
 Now you can connect:
```bash
psql -U postgres
```
If you want to set a password:
```sql
ALTER USER postgres WITH PASSWORD 'your_password';
```

Config file:
 /opt/homebrew/var/postgresql@17/pg_hba.conf
 
Example of tablw with constraints
```

CREATE TABLE michael.T (
    id SERIAL PRIMARY KEY,
    device_name TEXT,
    device_type TEXT,
    ts TIMESTAMP,
    action TEXT CHECK (action IN ('ON', 'OFF')),
    value FLOAT,
    UNIQUE (device_name, device_type)
);

-- Generate 100 records with realistic constraints
INSERT INTO michael.T (device_name, device_type, ts, action, value)
SELECT 
    chr(65 + (i % 26)) AS device_name, -- A-Z
    CASE WHEN (i % 2) = 0 THEN 'phone' ELSE 'computer' END AS device_type,
    timestamp '2025-01-01' + (i || ' hours')::interval AS ts,
    CASE WHEN (i % 2) = 0 THEN 'ON' ELSE 'OFF' END AS action,
    ROUND((1 + random() * 9)::NUMERIC, 2)::NUMERIC(10,2) AS value
FROM generate_series(1, 100) AS s(i);
```

<!--
<https://dbfiddle.uk/>  
<https://sqlfiddle.com/>  
<https://rextester.com/>  

https://habr.com/ru/companies/selectel/articles/913572/ Как оптимизировать PostgreSQL 

https://habr.com/ru/articles/911688/ Правильный порядок колонок в B-tree индексах PostgreSQL
Правило ESR (Equality, Sort, Range) 

https://habr.com/ru/companies/selectel/articles/912996/

<https://postgresql.leopard.in.ua/>

<https://www.shayon.dev/post/2025/40/scaling-with-postgresql-without-boiling-the-ocean/>
-->

### Information schema
```sql
SELECT table_schema, table_name, column_name, data_type, is_nullable 
FROM information_schema.columns  
WHERE table_name = 'my_table_here'; 
```
### Reading records by column name (Python)
```python
import psycopg2
from psycopg2.extras import DictCursor
conn = psycopg2.connect(
    dbname="your_database",
    user="your_username",
    password="your_password",
    host="localhost",
    port="5432"
)
cursor = conn.cursor(cursor_factory=DictCursor)
cursor.execute("SELECT id, name, age FROM your_table")
records = cursor.fetchall()

# Access columns by name
for record in records:
    print(f"ID: {record['id']}, Name: {record['name']}, Age: {record['age']}")
cursor.close()
conn.close()
```

### Values
```sql
SELECT * FROM (
    VALUES (1, 'one'), (2, 'two'), (3, 'three')
) as t (digit_number, string_number);

WITH sv(sex, value) AS (
     VALUES(0, 'man'), (1, 'woman') 
)
SELECT fullname, sv.value FROM "user" INNER JOIN sv USING(sex);
```
### UNNEST
```sql
select unnest(array[1,2,3]) as id

Output:
 id 
----
  1
  2
  3
(3 rows)
```
### Generate series

```sql
select  generate_series (1,10), generate_series(1,2);


SELECT gs.added_at, coalesce(stats.money, 0.00) as money
FROM
    generate_series('2016-04-01'::date, '2016-04-07'::date , interval '1 day') as gs(added_at) 
LEFT JOIN stats 
ON stats.added_at = gs.added_at;
```
### Find the maximum interval of consecutive dates without gaps:

```SQL

WITH DateDiff AS (
    SELECT
        your_date_column,
        LAG(your_date_column, 1, your_date_column - INTERVAL '1 day') OVER (ORDER BY your_date_column) AS prev_date
    FROM
        your_table
),
ConsecutiveGroups AS (
    SELECT
        your_date_column,
        CASE
            WHEN your_date_column = prev_date + INTERVAL '1 day' THEN 0
            ELSE 1
        END AS is_new_group,
        ROW_NUMBER() OVER (ORDER BY your_date_column) AS rn
    FROM
        DateDiff
),
GroupStarts AS (
    SELECT
        your_date_column,
        SUM(is_new_group) OVER (ORDER BY rn) AS group_id
    FROM
        ConsecutiveGroups
)
SELECT
    MIN(your_date_column) AS start_date,
    MAX(your_date_column) AS end_date,
    MAX(your_date_column) - MIN(your_date_column) AS max_consecutive_interval
FROM
    GroupStarts
GROUP BY
    group_id
ORDER BY
    max_consecutive_interval DESC
LIMIT 1;
```

### find the maximum gap between consecutive dates:

```SQL
WITH DateDiff AS (
    SELECT
        your_date_column,
        LAG(your_date_column) OVER (ORDER BY your_date_column) AS prev_date
    FROM
        your_table
),
Gaps AS (
    SELECT
        your_date_column,
        prev_date,
        your_date_column - prev_date AS date_difference
    FROM
        DateDiff
    WHERE
        prev_date IS NOT NULL
)
SELECT
    MAX(date_difference) AS max_gap_interval
FROM
    Gaps;
```


### Find gaps in date column
```sql
WITH calendar AS (
  SELECT gs::date AS d
  FROM   generate_series('2025-04-01','2025-04-30','1 day') AS gs
), gaps AS (
  SELECT c.d
  FROM   calendar c
  LEFT   JOIN daily_balance b ON b.trn_date = c.d
  WHERE  b.balance_date IS NULL
)
SELECT d FROM gaps ORDER BY d;

```


### Issue with LAG, LEAD, ROW_NUMBER, RAND with NULLS 
<https://habr.com/ru/companies/otus/articles/905062/>
```sql
WITH daily_balance AS (
  SELECT * FROM (VALUES
    ('2025-04-20'::date, 100),
    ('2025-04-22',        150) -- no record for  04-21 
  ) AS t(trn_date, balance)
)
SELECT
  trn_date,
  balance,
  balance - LAG(balance) OVER (ORDER BY trn_date) AS diff    -- will be NULL ?! because no record for  04-21 
FROM daily_balance;
```


### JSON_TABLE() function (Postgres 17)
```sql
SELECT *
FROM JSON_TABLE(
  '[{"name":"Alice","age":30},{"name":"Bob","age":25}]',
  '$[*]'
  COLUMNS(name TEXT PATH '$.name', age INT PATH '$.age')
) AS jt;
```
### MERGE with RETURN (Postgres 17)
```sql
MERGE INTO employees AS e
USING new_data AS d
ON e.id = d.id
WHEN MATCHED THEN
  UPDATE SET salary = d.salary
WHEN NOT MATCHED THEN
  INSERT (id, salary) VALUES (d.id, d.salary)
RETURNING *;
```
### Lateral JOIN
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    order_date TIMESTAMP
);
```
Task: fetch the latest order per customer using Partition and ROW_NUMBER()
```sql
WITH ranked_orders AS (
    SELECT o.id, o.order_date, o.customer_id, 
           ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC) AS row_num
    FROM orders o
)
SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    ro.id AS latest_order_id,
    ro.order_date AS latest_order_date
FROM customers c
JOIN ranked_orders ro ON ro.customer_id = c.id
WHERE ro.row_num = 1;
```
Now let do the same using LATERAL JOIN
```sql
SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    o.id AS latest_order_id,
    o.order_date AS latest_order_date
FROM 
    customers c
JOIN LATERAL (
    SELECT id, order_date
    FROM orders o
    WHERE o.customer_id = c.id
    ORDER BY o.order_date DESC
    LIMIT 1
) o ON true;
```
### Foreign key constraint - always mark it with on update restrict on delete restrict.

This makes it so that if you try and delete the referenced row you will get an error. 

```sql
CREATE TABLE person(
    id uuid not null default gen_random_uuid() primary key,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    name text not null
);

CREATE TABLE pet(
    id uuid not null default gen_random_uuid() primary key,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    name text not null,
    owner_id uuid not null references person(id)
                on update restrict
                on delete restrict
);
```

### Constraints
<https://www.postgresql.org/docs/current/ddl-constraints.html>
```
Check constraint is satisfied if the check expression evaluates to true or the null value.
Since most expressions will evaluate to the null value if any operand is null,
they will not prevent null values in the constrained columns.
To ensure that a column does not contain null values,
the not-null constraint can be used.

Check constraint can also refer to several columns.
Names can be assigned to table constraints in the same way as column constraints:
```

```sql
CREATE TABLE products (
    product_no integer,
    name text,
    price numeric CHECK (price > 0),
    discounted_price numeric,,
    CHECK (price > discounted_price)
);


CREATE TABLE products (
    product_no integer,
    name text,
    price numeric,
    CHECK (price > 0),
    discounted_price numeric,
    CHECK (discounted_price > 0),
    CONSTRAINT valid_discount CHECK (price > discounted_price)
);
```

### SQL EXCEPT

<https://www.postgresql.org/docs/current/sql-select.html#SQL-EXCEPT>

### Config

<https://tembo.io/blog/optimizing-memory-usage>

<https://pgtune.leopard.in.ua/>

###  UUID7 as primary key

<https://maciejwalkowiak.com/blog/postgres-uuid-primary-key/>

<https://uuid7.com/>

### Postgres HA

<https://www.binwang.me/2024-12-02-PostgreSQL-High-Availability-Solutions-Part-1.html>

<https://proxysql.com/>

<https://news.ycombinator.com/item?id=42293937>

### Features
```
✅ Caching: Use UNLOGGED tables and TEXT as a JSON data type in Postgres instead of Redis.
✅ Message Queue: Replace Kafka with Postgres using SKIP LOCKED for simple message queue needs.
✅ Job Queue: Use Postgres with tools like River in Go for job queuing.
Data Warehouse: Implement TimescaleDB on top of Postgres for data warehousing needs.
✅ In-Memory OLAP: Combine Postgres with pg_analytics and Apache Datafusion for OLAP functionalities.
✅ JSON Storage: Store, search, and index JSON documents with JSONB in Postgres instead of MongoDB.
✅ Cron Jobs: Use pg_cron in Postgres for scheduling tasks, like sending emails.
✅ Geospatial Queries: Utilize Postgres's geospatial querying capabilities.
✅ Full-Text Search: Implement full-text search directly in Postgres instead of using Elasticsearch.
✅ JSON Generation: Generate JSON directly in the database, eliminating the need for server-side code.
✅ Auditing: Use pgaudit for auditing purposes.
✅ GraphQL Adapter: Integrate Postgres with a GraphQL adapter if GraphQL is needed.

```

### Partition Pruning
SET enable_partition_pruning = on; 

#### Explain
```sql
EXPLAIN ANALYZE SELECT *
FROM tenk1 t1, tenk2 t2
WHERE t1.unique1 < 100 AND t1.unique2 = t2.unique2
ORDER BY t1.fivethous;
```
### JSONB

<https://habr.com/ru/companies/sigma/articles/890668/>

### Full text search

<https://blog.vectorchord.ai/postgresql-full-text-search-fast-when-done-right-debunking-the-slow-myth>

<https://news.ycombinator.com/item?id=43627646>

### Logging every change in your database

<https://medium.com/@ihcnemed/postgresql-record-every-change-in-your-database-a98a6586527c>


### Find slow queries

<https://www.peterbe.com/plog/3-queries-with-pg_stat_statements>

### DB diagrams

<https://news.ycombinator.com/item?id=43808803>
