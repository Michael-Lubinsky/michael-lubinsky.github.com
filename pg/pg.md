<https://onecompiler.com/postgresql>

### Information schema
```sql
SELECT table_schema, table_name, column_name, data_type, is_nullable 
FROM information_schema.columns  
WHERE table_name = 'my_table_here'; 
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
,
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


### Config

https://tembo.io/blog/optimizing-memory-usage

https://pgtune.leopard.in.ua/

###  UUID7 as primary key

https://maciejwalkowiak.com/blog/postgres-uuid-primary-key/

https://uuid7.com/

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

https://habr.com/ru/companies/sigma/articles/890668/
