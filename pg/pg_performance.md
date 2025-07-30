## Postgres performance

### Find unused indexes



```sql
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE idx_tup_read = 0;
```


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




### 1 · Spot Sequential Scans at Scale  
```sql
SELECT relname              AS table,
       seq_scan             AS seq_scans,
       idx_scan             AS idx_scans,
       round(100*seq_scan/NULLIF(seq_scan+idx_scan,0),2) AS seq_pct,
       n_live_tup           AS rows
FROM   pg_stat_user_tables
WHERE  n_live_tup > 10000          -- big enough to matter
ORDER  BY seq_scan DESC
LIMIT 15;
```
seq_pct > 10 % on tables > 10 k rows → likely missing or unused indexes.  
Small tables can live with seq scans; indexes add overhead.

### 2 · Pinpoint Offending Columns with EXPLAIN 

Get top queries for the table:
```sql
SELECT query
FROM   pg_stat_statements
WHERE  query LIKE '%big_table%'
ORDER  BY total_exec_time DESC
LIMIT 5;
```
Run EXPLAIN (ANALYZE, BUFFERS) on the slowest query.  
Look for:

- Seq Scan with a filter → add normal / partial index  
- Bitmap Heap Scan removing many rows → covering index  
- Joins lacking Index Scan on FK side → index the FK column  
- Need help reading plans? See EXPLAIN ANALYZE Demystified.  

### 3 · Automatic Foreign‑Key Audit 

Find FK columns missing indexes:
```sql
WITH fks AS (
  SELECT conrelid, conname, conkey
  FROM   pg_constraint
  WHERE  contype = 'f'
), ix AS (
  SELECT indrelid, indkey
  FROM   pg_index
  WHERE  indisvalid AND indpred IS NULL
)
SELECT  n.nspname || '.' || c.relname AS table,
        f.conname                    AS fk_name,
        array_to_string(ARRAY(
          SELECT a.attname
          FROM   pg_attribute a
          WHERE  a.attrelid = f.conrelid
             AND  a.attnum   = ANY(f.conkey)
          ORDER  BY array_position(f.conkey, a.attnum)
        ), ',') AS fk_cols
FROM    fks f
JOIN    pg_class c ON c.oid = f.conrelid
JOIN    pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN ix ON ix.indrelid = f.conrelid
           AND f.conkey   = ix.indkey[0:array_length(f.conkey,1)-1]
WHERE   ix.indrelid IS NULL   -- no supporting index
ORDER BY table;
```

Result lists FK constraints that need indexes.

### 4 · Generate Index DDL 
Auto‑craft index statements:
```sql
SELECT format(
  'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_%I_%s ON %s USING btree (%s);',
  relname,               -- table name
  string_agg(col, '_'),  -- suffix
  relid::regclass,       -- schema.table
  string_agg(col, ', ')  -- column list
) AS ddl
FROM   your_fk_missing_index_query
GROUP  BY relid, relname;
```
Run the generated CREATE INDEX CONCURRENTLY outside a transaction block.

### 5 · Partial & Covering Index Patterns 

| Scenario                                   | Index Recipe                                    | Why
|-------------------------------------------|--------------------------------------------------|-----------------------------------------
|Soft deletes (WHERE deleted_at IS NULL)    | CREATE INDEX … WHERE deleted_at IS NULL         | Smaller, faster scans
|Recent rows (created_at > NOW()-30d)       | CREATE INDEX … ON … (created_at) WHERE created_at > … | Keeps old data out of index
|Filter + sort (status='paid' ORDER BY date)| CREATE INDEX … (status, created_at DESC)        | Supports filter *and* order by
|Covering lookup (select few cols)          | CREATE INDEX … (id) INCLUDE (col1, col2)        | Enables index‑only scan

Use pg_size_pretty(pg_relation_size('index_name')) to verify size savings.

### 6 · Validate Impact 

EXPLAIN (ANALYZE, BUFFERS) <your query again>;


Seq Scan should disappear and time should drop. Monitor:
```sql
SELECT idx_scan, seq_scan
FROM   pg_stat_user_tables
WHERE  relname = 'big_table';
Expect idx_scan to climb after deployment.
```

### 7 · Gotchas & Best Practices
Don’t over‑index — writes pay the price; review idx_scan = 0 quarterly.
```sql
CREATE INDEX CONCURRENTLY in prod to avoid write locks.
-- Drop unused indexes:
SELECT relname
FROM   pg_stat_user_indexes
WHERE  idx_scan = 0
  AND  pg_relation_size(indexrelid) > 10*8192;
```
Avoid duplicates (compare pg_index.indkey).

Use fillfactor for hot rows (ALTER INDEX … SET (fillfactor=90)).


### EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) helpers
<https://explain.tensor.ru/>  
<https://explain.depesz.com/>  
<https://explain-postgresql.com/>  
<https://explain.dalibo.com/>  

### Links

<https://blog.devgenius.io/debugging-postgres-with-explain-0c79af693857>


<https://medium.com/dev-genius/sql-optimization-beyond-commons-81b37d224a49>

<https://medium.com/@rizqimulkisrc/postgres-performance-tuning-like-a-pro-2dd7f58d82d2>

<https://habr.com/ru/companies/selectel/articles/913572/> Как оптимизировать PostgreSQL 

<https://www.youtube.com/@ScalingPostgres/videos> Scaling Postgres

<https://dataegret.com/2025/05/data-archiving-and-retention-in-postgresql-best-practices-for-large-datasets/>

<https://dataegret.com/2025/07/operating-postgresql-as-a-data-source-for-analytics-pipelines-recap-from-the-stuttgart-meetup/>


