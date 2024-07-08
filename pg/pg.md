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

### Partition Pruning
SET enable_partition_pruning = on; 

#### Explain
```
EXPLAIN ANALYZE SELECT *
FROM tenk1 t1, tenk2 t2
WHERE t1.unique1 < 100 AND t1.unique2 = t2.unique2
ORDER BY t1.fivethous;
```
