## Postgres

### FILTER
FILTER is a SQL keyword supported by PostgreSQL that allows you  
to apply a WHERE-like filter inside an aggregate function, making it easy to compute conditional aggregates.
```sql
aggregate_function(args) FILTER (WHERE condition)
```
Example:
```sql
SELECT
    SUM(amount) AS total_sales,
    SUM(amount) FILTER (WHERE region = 'West') AS west_sales
FROM sales;
```
The same as above without filter:
```sql
SELECT
    SUM(amount) AS total_sales,
    SUM(CASE WHEN region = 'West' THEN amount ELSE 0 END) AS west_sales
FROM sales;
```
| Feature                  | `FILTER` syntax                           | Equivalent without `FILTER`                        |
| ------------------------ | ----------------------------------------- | -------------------------------------------------- |
| Aggregate with condition | `SUM(col) FILTER (WHERE condition)`       | `SUM(CASE WHEN condition THEN col ELSE 0 END)`     |
| Example                  | `COUNT(*) FILTER (WHERE col IS NOT NULL)` | `SUM(CASE WHEN col IS NOT NULL THEN 1 ELSE 0 END)` |
| Readability              | High                                      | Moderate                                           |

### JSONB

```sql
-- Creating a table with a JSONB column
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    data JSONB
);

-- Inserting a document
INSERT INTO products (data) VALUES (
    '{"name": "Smartphone", "price": 699.99, "specs": {"ram": "8GB", "storage": "256GB"}, "colors": ["black", "silver", "blue"]}'
);
 
-- Create a GIN index for general JSONB queries
CREATE INDEX idx_products_data ON products USING GIN (data);

-- Create a targeted index for a specific property
CREATE INDEX idx_products_name ON products USING GIN ((data->'name'));

-- Index for containment operations (extremely fast)
CREATE INDEX idx_products_specs ON products USING GIN (data jsonb_path_ops);
```
PostgreSQL offers four different index types for JSONB data (B-tree, GIN, GiST, and hash), each optimized for different query patterns. 

 
```sql
-- Find products with 8GB RAM
SELECT * FROM products WHERE data->'specs'->>'ram' = '8GB';

-- Find products available in blue color
SELECT * FROM products WHERE data->'colors' ? 'blue';

-- Find smartphones with at least 128GB storage (using containment)
SELECT * FROM products WHERE data @> '{"specs": {"storage": "256GB"}}';
```
The @> containment operator is particularly powerful and   especially when combined with GIN indexes.

JSON Path Expressions
PostgreSQL’s implementation of SQL/JSON path expressions 
```sql
-- Find products with prices over 500
SELECT * FROM products 
WHERE jsonb_path_query_first(data, '$.price ? (@ > 500)') IS NOT NULL;

-- Extract value with path expression
SELECT jsonb_path_query(data, '$.specs.ram') FROM products;
```
These expressions offer  flexibility and power for querying complex nested JSON structures.
Schema Flexibility:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    profile JSONB
);
```
This gives you:

Schema enforcement for critical fields (ID, email, timestamps)  
Validation through check constraints  
Complete flexibility for the profile data that can evolve as your application changes
<https://medium.com/@sohail_saifi/postgres-hidden-features-that-make-mongodb-completely-obsolete-from-an-ex-nosql-evangelist-1a390233c264>

<https://www.postgresonline.com/journal/index.php?/archives/420-Converting-JSON-documents-to-relational-tables.html#jsontorelational> Converting JSON documents to relational tables

<https://habr.com/ru/companies/sigma/articles/890668/> Использование JSONB-полей вместо EAV в PostgreSQL


### WITHIN GROUP

WITHIN GROUP is used with ordered-set aggregate functions to perform aggregations  
that require order over the input data, like percentile_cont, percentile_disc, and mode.

```sql
-- Find price percentiles across product categories
SELECT 
    data->>'category' AS category,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY (data->>'price')::numeric) AS median_price,
    percentile_cont(0.9) WITHIN GROUP (ORDER BY (data->>'price')::numeric) AS p90_price
FROM products
GROUP BY data->>'category';
```

### Extensions
<https://www.postgresql.org/docs/current/contrib.html>  
<https://pgxn.org/>  
<https://www.tigerdata.com/blog/top-8-postgresql-extensions>

pg_stat_statements tracks statistics on the queries executed by a Postgres database.
```CREATE EXTENSION pg_stat_statements;```

You need superuser privileges to create extensions.
```sql
SELECT * FROM pg_available_extensions; -- List of postgres extensions:
CREATE EXTENSION hstore;
SELECT * FROM pg_extension;
```

### Table partitioning

<https://www.tigerdata.com/learn/when-to-consider-postgres-partitioning>

#### pg_partman extension
pg_partman is an extension that simplifies creating and maintaining partitions of your PostgreSQL tables.  

With pg_partman, PostgreSQL can manage partitions based on a variety of criteria such as time, serial IDs, or custom values. 
It eases the maintenance tasks associated with partitioning, such as creating new partitions in advance and purging old ones.
This automation is particularly useful for large, time-series datasets that can grow rapidly.

<https://www.tigerdata.com/learn/pg_partman-vs-hypertables-for-postgres-partitioning>

#### Example of table with constraints
```sql
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

<https://github.com/hapostgres/pg_auto_failover>

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

#### Explain analyze
```sql
EXPLAIN ANALYZE SELECT *
FROM tenk1 t1, tenk2 t2
WHERE t1.unique1 < 100 AND t1.unique2 = t2.unique2
ORDER BY t1.fivethous;
```

### Postgres 18
<https://medium.com/@ThreadSafeDiaries/postgresql-18-just-rewrote-the-rulebook-groundbreaking-features-you-cant-ignore-85eb81477890>

### extension: pg_repack 
pg_repack  is a PostgreSQL extension which lets you remove bloat from tables and indexes, 
and optionally restore the physical order of clustered indexes. 
Unlike CLUSTER and VACUUM FULL it works online, without holding an exclusive lock on the processed tables during processing. 
pg_repack is efficient to boot, with performance comparable to using CLUSTER directly.
<https://github.com/reorg/pg_repack>


#### CLUSTER
The CLUSTER keyword in PostgreSQL is used to:

✅ Physically reorder the table data on disk based on the index order of a specified index.

✅ This improves I/O performance for queries that frequently use the indexed column(s) because related rows are stored close together on disk, reducing page reads.

CLUSTER table_name USING index_name;

How it works:
1️⃣ You specify an index, and PostgreSQL will sort the table's rows according to that index order.
2️⃣ The table is rewritten on disk in this new order.
3️⃣ The associated table indexes are rebuilt.

Key Points:
✅ Locks:

CLUSTER requires an exclusive lock on the table during the operation.

The table is unavailable for writes and reads while clustering.

✅ Persistent clustering:

PostgreSQL remembers which index was used for clustering (pg_index.indisclustered = true).

However, future inserts/updates do not maintain physical order; you must re-run CLUSTER periodically to maintain clustering benefits.


### Postgres HA

https://stormatics.tech/blogs/checklist-is-your-postgresql-deployment-production-grade

Which PostgreSQL HA Solution Fits Your Needs: Pgpool or Patroni?

https://stormatics.tech/blogs/which-postgresql-ha-solution-fits-your-needs-pgpool-or-patroni


### Backup
<https://news.ycombinator.com/item?id=44473888>  
<https://pgmoneta.github.io/>  
<https://ossc-db.github.io/pg_bulkload/pg_bulkload.html>

```bash
#!/bin/bash

DB_NAME=${1:-mydatabase}
BACKUP_DIR=${2:-/backups}
USER_NAME=${3:-postgres}

TIMESTAMP=$(date +"%F_%T")
FILENAME="$BACKUP_DIR/${DB_NAME}_backup_$TIMESTAMP.sql"

mkdir -p "$BACKUP_DIR"

echo "💾 Backing up database '$DB_NAME' to $FILENAME"
pg_dump -U "$USER_NAME" "$DB_NAME" > "$FILENAME"

if [ $? -eq 0 ]; then
  echo "✅ Backup successful!"
else
  echo "❌ Backup failed!"
fi
```
Usage:
```bash
chmod +x pg_backup.sh
./pg_backup.sh yourdb /your/backup/folder your_pg_user
```

### Full text search

<https://blog.vectorchord.ai/postgresql-full-text-search-fast-when-done-right-debunking-the-slow-myth>

<https://news.ycombinator.com/item?id=43627646>

### Logging every change in your database

<https://medium.com/@ihcnemed/postgresql-record-every-change-in-your-database-a98a6586527c>


### Find slow queries

```sql
SELECT
  userid :: regrole,
  dbid,
  mean_exec_time / 1000 as mean_exec_time_secs,
  max_exec_time / 1000 as max_exec_time_secs,
  min_exec_time / 1000 as min_exec_time_secs,
  stddev_exec_time,
  calls,
  query
from
  pg_stat_statements
order by
  mean_exec_time DESC limit 10;

-- currently running (active) database sessions in PostgreSQL
-- that have been executing for longer than one minute.
SELECT 
  datname AS database_name, 
  usename AS user_name, 
  application_name, 
  client_addr AS client_address, 
  client_hostname, 
  query AS current_query, 
  state, 
  query_start, 
  now() - query_start AS query_duration 
FROM 
  pg_stat_activity 
WHERE 
  state = 'active' AND now() - query_start > INTERVAL '10 sec' 
ORDER BY 
  query_start DESC;

--  identify I/O-intensive queries
SELECT 
  mean_exec_time / 1000 as mean_exec_time_secs, 
  calls, 
  rows, 
  shared_blks_hit, 
  shared_blks_read, 
  shared_blks_hit /(shared_blks_hit + shared_blks_read):: NUMERIC * 100 as hit_ratio, 
  (blk_read_time + blk_write_time)/calls as average_io_time_ms, 
  query 
FROM 
  pg_stat_statements 
where 
  shared_blks_hit > 0 
ORDER BY 
  (blk_read_time + blk_write_time)/calls DESC;
```

<https://www.peterbe.com/plog/3-queries-with-pg_stat_statements>

<https://medium.com/timescale/how-to-monitor-postgresql-like-a-pro-5-techniques-every-developer-should-know-68581c49a4a4>

### DB diagrams

<https://news.ycombinator.com/item?id=43808803>


#### Installing Postgres on Mac

```bash
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
 
### How to enforce constraint that every city can be associated with a single state  only?
There is Postgres table with columns:   
first_name, last_name, city, state.

How to enforce constraint that every city can be associated with a single state  only?
Example:  
if there is record with city='Los Angeles' and state='CA'  
then it is not possible to have record with   city='Los Angeles' and state='Oregon' 

You can use a partial functional unique index or a unique index on an expression.  

However, since PostgreSQL does not support directly enforcing “for a given city, allow only one state”   
(while allowing multiple rows with the same city and state), the cleanest and standard way is:

1️⃣ Create a unique index on (city, state)  
This ensures that you cannot have the *same (city, state) pair multiple times,   
but it does not enforce your desired constraint alone.

2️⃣ Enforce city → state functional dependency using a UNIQUE constraint on city plus a trigger:  
PostgreSQL does not support functional dependencies directly,   
so use a BEFORE INSERT OR UPDATE trigger to enforce it.

Example:

```sql

CREATE OR REPLACE FUNCTION enforce_city_state_consistency()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM your_table
        WHERE city = NEW.city AND state <> NEW.state
    ) THEN
        RAISE EXCEPTION 'City "%" is already associated with a different state', NEW.city;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_city_state
BEFORE INSERT OR UPDATE ON your_table
FOR EACH ROW
EXECUTE FUNCTION enforce_city_state_consistency();
```
✅ What this does:

Allows multiple rows with the same (city, state).

Prevents inserting/updating a row with a (city, different_state) if that city already exists with another state.

Example demonstrating it:
```sql

INSERT INTO your_table (first_name, last_name, city, state)
VALUES ('John', 'Doe', 'Los Angeles', 'CA'); -- ✅ succeeds

INSERT INTO your_table (first_name, last_name, city, state)
VALUES ('Jane', 'Smith', 'Los Angeles', 'CA'); -- ✅ succeeds

INSERT INTO your_table (first_name, last_name, city, state)
VALUES ('Alice', 'Walker', 'Los Angeles', 'OR'); -- ❌ raises exception
```

PostgreSQL does not support this constraint natively, so the recommended method is:  
Add a trigger that raises an exception if an insert or update would create a (city, state) inconsistency.


<!--
<https://dbfiddle.uk/>  
<https://sqlfiddle.com/>  
<https://rextester.com/>  

https://habr.com/ru/companies/selectel/articles/913572/ Как оптимизировать PostgreSQL 

https://www.youtube.com/@ScalingPostgres/videos Scaling Postgres

https://dataegret.com/2025/05/data-archiving-and-retention-in-postgresql-best-practices-for-large-datasets/

https://dataegret.com/2025/07/operating-postgresql-as-a-data-source-for-analytics-pipelines-recap-from-the-stuttgart-meetup/

https://github.com/BemiHQ/BemiDB Single-binary Postgres read replica optimized for analytics

https://habr.com/ru/articles/911688/ Правильный порядок колонок в B-tree индексах PostgreSQL
Правило ESR (Equality, Sort, Range) 

https://pgmodeler.io/

https://clickhouse.com/blog/postgres-to-clickhouse-data-modeling-tips-v2  Postgres - Clickhouse

https://habr.com/ru/companies/selectel/articles/912996/ Все, что нужно PostgreSQL: быстрые диски, дорогой процессор и терабайты RAM

https://kmoppel.github.io/2025-04-10-postgres-scaling-roadmap/

<https://postgresql.leopard.in.ua/>

<https://www.shayon.dev/post/2025/40/scaling-with-postgresql-without-boiling-the-ocean/>

<https://mccue.dev/pages/3-11-25-life-altering-postgresql-patterns>

<https://medium.com/@pesarakex/how-we-migrated-a-100m-row-postgresql-table-with-zero-downtime-and-survived-5b908de243e0>
-->
