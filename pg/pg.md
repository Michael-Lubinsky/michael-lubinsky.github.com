### Information schema
```
SELECT table_schema, table_name, column_name, data_type, is_nullable 
FROM information_schema.columns  
WHERE table_name = 'my_table_here'; 
```
### Config

https://tembo.io/blog/optimizing-memory-usage

https://pgtune.leopard.in.ua/

###  UUID7 as primary key

https://maciejwalkowiak.com/blog/postgres-uuid-primary-key/

https://uuid7.com/

### Features

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



### Partition Pruning
SET enable_partition_pruning = on; 

#### Explain
```
EXPLAIN ANALYZE SELECT *
FROM tenk1 t1, tenk2 t2
WHERE t1.unique1 < 100 AND t1.unique2 = t2.unique2
ORDER BY t1.fivethous;
```
