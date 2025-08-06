## Postgres
<https://postgres.ai/docs/postgres-howtos>  
<https://planet.postgresql.org/>  
<https://www.manning.com/books/postgresql-mistakes-and-how-to-avoid-them>

### 

```sql
select current_schema() 
select current_database()
show  search_path
RAISE NOTICE 'Value of x = %', x;
```

### Roles
```sql
SELECT *
FROM pg_roles
WHERE rolname = 'weavix_owner';


SELECT 
  pg1.rolname AS role,
  pg2.rolname AS member_of
FROM pg_auth_members m
JOIN pg_roles pg1 ON pg1.oid = m.roleid
JOIN pg_roles pg2 ON pg2.oid = m.member
WHERE pg2.rolname = 'weavix_admin';
```


### ON CONFLICT 

 in PostgreSQL, a conflict in INSERT ... ON CONFLICT is triggered when:  
 The INSERT tries to add a row that violates a UNIQUE constraint or a PRIMARY KEY constraint.
 
```sql
INSERT INTO products (name, price)
VALUES ('Laptop', 1000)
ON CONFLICT (name) DO NOTHING;

INSERT INTO products (name, price)
VALUES ('Laptop', 1200)
ON CONFLICT (name) DO UPDATE
SET price = EXCLUDED.price;

WITH upsert AS (
    UPDATE products
    SET price = 1500
    WHERE name = 'Laptop'
    RETURNING *
)
INSERT INTO products (name, price)
SELECT 'Laptop', 1500
WHERE NOT EXISTS (SELECT 1 FROM upsert);
```



### MATERIALIZED VIEW
```sql
CREATE MATERIALIZED VIEW city_events_per_day AS
SELECT
  city,
  date_trunc('day', timestamp) AS day,
  COUNT(*) AS event_count
FROM T
GROUP BY city, date_trunc('day', timestamp)
ORDER BY city, day;
```

To update it once
```
REFRESH MATERIALIZED VIEW my_view;
```

Run it via cron to update it periodically:
```
crontab -e
0 1 * * * psql -U your_user -d your_database -c "REFRESH MATERIALIZED VIEW city_events_per_day;"
```
If your PostgreSQL has pg_cron installed:

```sql
-- Enable extension (once per DB)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily refresh at 1:00 AM
SELECT cron.schedule(
  'refresh_city_events_view',
  '0 1 * * *',
  'REFRESH MATERIALIZED VIEW city_events_per_day'
);

-- or --
SELECT cron.schedule('daily_refresh', '0 1 * * *', 
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY my_view$$);
```

### REFRESH MATERIALIZED VIEW CONCURRENTLY

The PostgreSQL command `REFRESH MATERIALIZED VIEW CONCURRENTLY` updates a **materialized view**   
with the latest data **without locking out reads** from the view during the refresh process.

---

### 🔍 Syntax
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY view_name;
```

---

### 🧠 What It Does

- Recomputes the contents of the materialized view (`view_name`) using the underlying tables.
- **`CONCURRENTLY`** allows other sessions to **continue querying** the materialized view while it's being refreshed.
- It **avoids downtime** or blocking, which is useful in production environments.

---

### ⚠️ Requirements

- The materialized view **must have a unique index** on at least one column (typically a primary key or unique constraint).
  ```sql
  CREATE UNIQUE INDEX ON my_materialized_view (id);
  ```

- If this unique index is missing, you’ll get:
  ```
  ERROR:  cannot refresh materialized view concurrently without a unique index
  ```

---

### 🔁 Without `CONCURRENTLY`
```sql
REFRESH MATERIALIZED VIEW my_view;
```
- **Locks the view for reads and writes** during refresh.
- Quicker but **blocks all access** during the operation.

---

### ✅ Use Case Example

Suppose you have a materialized view:
```sql
CREATE MATERIALIZED VIEW sales_summary AS
SELECT date_trunc('day', created_at) AS day, sum(amount) AS total
FROM sales
GROUP BY 1;
```

You should first create a unique index:
```sql
CREATE UNIQUE INDEX ON sales_summary(day);
```

Then, refresh it without locking:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY sales_summary;
```




### Incremental MATERIALIZED VIEW
```
To make the materialized view incremental
(i.e., only update data for yesterday, not re-aggregate the full table), you’ll need to:

1. Use a real table instead of a materialized view
Because materialized views in PostgreSQL do not support partial refresh,
 we'll simulate it with a regular table and manage it manually.
```
2. Create the target table
```sql
CREATE TABLE city_events_per_day (
  city TEXT,
  day DATE,
  event_count INTEGER,
  PRIMARY KEY (city, day)
);
```
 3. Create a SQL to insert/update only yesterday’s data
```sql
INSERT INTO city_events_per_day (city, day, event_count)
SELECT
  city,
  date_trunc('day', timestamp)::date AS day,
  COUNT(*) AS event_count
FROM T
WHERE timestamp >= current_date - INTERVAL '1 day'
  AND timestamp < current_date
GROUP BY city, date_trunc('day', timestamp)
ON CONFLICT (city, day)
DO UPDATE SET event_count = EXCLUDED.event_count;
```
This query aggregates events for yesterday only, and either inserts or updates the table.

It uses ON CONFLICT to handle upserts.

Example of monthly update:

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'monthly_city_event_update', -- job name
  '0 0 1 * *',                 -- cron expression: midnight on the 1st
  $$                                          
  INSERT INTO city_events_per_day (city, day, event_count)
  SELECT
    city,
    date_trunc('day', timestamp)::date AS day,
    COUNT(*) AS event_count
  FROM T
  WHERE timestamp >= date_trunc('month', current_date - INTERVAL '1 month')
    AND timestamp < date_trunc('month', current_date)
  GROUP BY city, date_trunc('day', timestamp)
  ON CONFLICT (city, day)
  DO UPDATE SET event_count = EXCLUDED.event_count;
  $$
);
```



### Postgres Parameters

```sql
SELECT 
    name,
    setting,
    unit,
    vartype,
    context,
    short_desc
FROM  pg_settings
WHERE 
    name IN (
        -- Memory settings
        'shared_buffers',
        'work_mem',
        'maintenance_work_mem',
        'temp_buffers',
        'effective_cache_size',

        -- Planner cost constants
        'random_page_cost',
        'seq_page_cost',
        'cpu_tuple_cost',
        'cpu_index_tuple_cost',
        'cpu_operator_cost',

        -- Parallelism
        'max_parallel_workers',
        'max_parallel_workers_per_gather',
        'parallel_setup_cost',
        'parallel_tuple_cost',

        -- Autovacuum
        'autovacuum_vacuum_cost_limit',
        'autovacuum_vacuum_threshold',
        'autovacuum_vacuum_scale_factor',
        'autovacuum_naptime',
        'autovacuum_max_workers',

        -- WAL & Checkpoints
        'wal_buffers',
        'wal_compression',
        'wal_writer_delay',
        'commit_delay',
        'synchronous_commit',
        'checkpoint_timeout',
        'max_wal_size',
        'checkpoint_completion_target',

        -- Connections & Statistics
        'max_connections',
        'default_statistics_target'
    )
ORDER BY name;
```

| Parameter              | Description                                               | Example Value       |
| ---------------------- | --------------------------------------------------------- | ------------------- |
| `shared_buffers`       | Amount of memory dedicated to PostgreSQL for caching data | 25–40% of total RAM |
| `work_mem`             | Memory used per sort/hash/join operation (not per query!) | 4MB – 64MB          |
| `maintenance_work_mem` | Memory for vacuuming, indexing, etc.                      | 64MB – 1GB          |
| `temp_buffers`         | Buffers for temporary tables per session                  | 8MB – 64MB          |
| `effective_cache_size` | Estimate of OS-level cache available to Postgres          | \~75% of total RAM  |



Book
<https://www.manning.com/books/postgresql-mistakes-and-how-to-avoid-them>



### USING
```sql
SELECT * FROM employees
JOIN departments USING (department_id);
```
This is shorthand for:

```sql
SELECT * FROM employees
JOIN departments ON employees.department_id = departments.department_id;
```

| Context            | Purpose                 | Notes                                 |
|------------------|-----------------------|-------------------------------------|
|  JOIN USING        | Simplify join condition | Column must exist in both tables      |
|  DELETE USING      | Delete with join        | Equivalent to  DELETE FROM ... USING  |
|  MERGE USING    | Define source for merge | PostgreSQL 15+                        |

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

| Feature                  | FILTER syntax                           | Equivalent without FILTER                      |
| ------------------------ |-----------------------------------------|--------------------------------------------------|
| Aggregate with condition | SUM(col) FILTER (WHERE condition)       | SUM(CASE WHEN condition THEN col ELSE 0 END)     |
| Example                  | COUNT(*) FILTER (WHERE col IS NOT NULL) | SUM(CASE WHEN col IS NOT NULL THEN 1 ELSE 0 END) |
| Readability              | High                                    | Moderate                                         |


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


You need superuser privileges to create extensions.
```sql
SELECT * FROM pg_available_extensions; -- List of postgres extensions:
CREATE EXTENSION hstore;

SELECT * FROM pg_extension;

SELECT 
    extname AS extension_name,
    extversion AS version,
    extrelocatable AS relocatable,
    nspname AS schema_name,
    pg_catalog.obj_description(e.oid, 'pg_extension') AS description
FROM  pg_extension e
JOIN 
    pg_namespace n ON e.extnamespace = n.oid
ORDER BY  extname;
```

<https://www.postgresql.org/docs/current/contrib.html>  
<https://pgxn.org/>  
<https://www.tigerdata.com/blog/top-8-postgresql-extensions>

#### pg_anon
<https://habr.com/ru/companies/tantor/articles/913196/>    
<https://habr.com/ru/companies/rostelecom/articles/876124/>

#### pg_stat_statements 
tracks statistics on the queries executed by a Postgres database.
```CREATE EXTENSION pg_stat_statements;```

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



<https://stormatics.tech/blogs/checklist-is-your-postgresql-deployment-production-grade>

<https://medium.com/@rongalinaidu/postgresql-replication-wal-wal-decoding-and-the-journey-toward-zero-etl-8c14ec566a7d>

Which PostgreSQL HA Solution Fits Your Needs: Pgpool or Patroni?

<https://stormatics.tech/blogs/which-postgresql-ha-solution-fits-your-needs-pgpool-or-patroni>



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

<https://medium.com/@dev_tips/scaling-broke-my-stack-but-postgresql-18-showed-me-how-to-fix-it-c91cb02f4f6f>

<https://medium.com/@kanishks772/how-we-designed-a-1-billion-row-system-on-postgresql-18-and-why-its-blazing-fast-6c97aec9271b>

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

echo "Backing up database '$DB_NAME' to $FILENAME"
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

https://mathesar.org/ spreadsheet-like tool for Postgres data

https://habr.com/ru/articles/843324/ Администрирование PostgreSQL для начинающих (часть 5)

https://habr.com/ru/companies/selectel/articles/913572/ Как оптимизировать PostgreSQL 

https://www.youtube.com/@ScalingPostgres/videos Scaling Postgres

https://dataegret.com/2025/05/data-archiving-and-retention-in-postgresql-best-practices-for-large-datasets/

https://dataegret.com/2025/07/operating-postgresql-as-a-data-source-for-analytics-pipelines-recap-from-the-stuttgart-meetup/

https://github.com/BemiHQ/BemiDB Single-binary Postgres read replica optimized for analytics

https://habr.com/ru/articles/911688/ Правильный порядок колонок в B-tree индексах PostgreSQL
Правило ESR (Equality, Sort, Range) 

https://medium.com/@rizqimulkisrc/postgresql-for-real-time-apps-performance-techniques-c37a14ec2046

https://pgmodeler.io/

https://clickhouse.com/blog/postgres-to-clickhouse-data-modeling-tips-v2  Postgres - Clickhouse

https://habr.com/ru/companies/selectel/articles/912996/ Все, что нужно PostgreSQL: быстрые диски, дорогой процессор и терабайты RAM

https://kmoppel.github.io/2025-04-10-postgres-scaling-roadmap/

<https://postgresql.leopard.in.ua/>

<https://www.shayon.dev/post/2025/40/scaling-with-postgresql-without-boiling-the-ocean/>

<https://mccue.dev/pages/3-11-25-life-altering-postgresql-patterns>

<https://medium.com/@pesarakex/how-we-migrated-a-100m-row-postgresql-table-with-zero-downtime-and-survived-5b908de243e0>



-->
