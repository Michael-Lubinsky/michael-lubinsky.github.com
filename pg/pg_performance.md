## Postgres performance

### Find unused indexes

idx_tup_read = 0 — meaning no index entries were read (i.e., no index scans read any heap tuples via this index)



```sql
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE idx_tup_read = 0;
```

idx_scan = 0: means PostgreSQL hasn’t used the index for query plans since the last pg_stat_reset().

```sql
SELECT 
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,
    pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size
FROM 
    pg_stat_user_indexes ui
JOIN 
    pg_index i ON ui.indexrelid = i.indexrelid
WHERE 
    idx_scan <50    -- = 0   -- Never used since last stats reset
    AND NOT i.indisunique
    AND NOT i.indisprimary
ORDER BY 
    pg_relation_size(i.indexrelid) DESC;
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




# PostgreSQL 16 – Schema Metadata Queries

Notes:
- Replace `:schema_name` (and `:root_table` where applicable) with your values, or define them as psql variables, e.g. `\set schema_name your_schema`.
- All queries read from `pg_catalog` and are compatible with PostgreSQL 16.

---

## 1) Table-level overview (size, stats, vacuum/analyze, constraints, partitioning)

```sql
WITH rels AS (
  SELECT
    n.nspname AS schema,
    c.relname AS rel,
    c.oid      AS relid,
    c.relkind,
    c.relpersistence,
    c.relnamespace,
    c.relowner,
    c.reltuples,
    c.relpages,
    c.relfrozenxid,
    c.relminmxid,
    c.reloptions,
    c.reltablespace,
    pg_catalog.pg_get_userbyid(c.relowner) AS owner,
    obj_description(c.oid, 'pg_class')     AS comment
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = :schema_name
    AND c.relkind IN ('r','p','m','v','f')
),
sizes AS (
  SELECT r.relid,
         pg_total_relation_size(r.relid) AS total_bytes,
         pg_relation_size(r.relid)       AS table_bytes,
         pg_indexes_size(r.relid)        AS index_bytes,
         pg_total_relation_size(r.relid) - pg_relation_size(r.relid) - pg_indexes_size(r.relid) AS toast_bytes
  FROM rels r
),
stats AS (
  SELECT s.relid,
         s.n_live_tup, s.n_dead_tup,
         s.last_vacuum, s.last_autovacuum, s.last_analyze, s.last_autoanalyze,
         s.vacuum_count, s.autovacuum_count, s.analyze_count, s.autoanalyze_count,
         s.seq_scan, s.seq_tup_read, s.idx_scan, s.idx_tup_fetch,
         s.n_tup_ins, s.n_tup_upd, s.n_tup_del, s.n_tup_hot_upd
  FROM pg_stat_all_tables s
),
io AS (
  SELECT st.relid,
         st.heap_blks_read, st.heap_blks_hit,
         st.idx_blks_read,  st.idx_blks_hit,
         st.toast_blks_read,st.toast_blks_hit,
         st.tidx_blks_read, st.tidx_blks_hit
  FROM pg_statio_all_tables st
),
constraints AS (
  SELECT r.relid,
         COUNT(*) FILTER (WHERE con.contype = 'p') AS pk_cnt,
         COUNT(*) FILTER (WHERE con.contype = 'u') AS uq_cnt,
         COUNT(*) FILTER (WHERE con.contype = 'f') AS fk_cnt,
         COUNT(*) FILTER (WHERE con.contype = 'c') AS ck_cnt
  FROM rels r
  LEFT JOIN pg_constraint con ON con.conrelid = r.relid
  GROUP BY r.relid
),
partitioning AS (
  SELECT r.relid,
         EXISTS (SELECT 1 FROM pg_inherits i WHERE i.inhparent = r.relid) AS is_parent,
         EXISTS (SELECT 1 FROM pg_inherits i WHERE i.inhrelid = r.relid)   AS is_child,
         (SELECT COUNT(*) FROM pg_inherits i WHERE i.inhparent = r.relid)  AS child_count,
         pg_get_partkeydef(r.relid) AS partkeydef
  FROM rels r
)
SELECT
  r.schema,
  r.rel AS table,
  CASE r.relkind
    WHEN 'r' THEN 'table'
    WHEN 'p' THEN 'partitioned table'
    WHEN 'm' THEN 'materialized view'
    WHEN 'v' THEN 'view'
    WHEN 'f' THEN 'foreign table'
  END AS kind,
  r.owner,
  r.relpersistence AS persistence,
  ts.spcname       AS tablespace,
  r.reltuples      AS row_estimate,
  s.n_live_tup, s.n_dead_tup,
  pg_size_pretty(sz.total_bytes) AS total_size,
  pg_size_pretty(sz.table_bytes) AS table_size,
  pg_size_pretty(sz.index_bytes) AS index_size,
  pg_size_pretty(sz.toast_bytes) AS toast_size,
  s.seq_scan, s.idx_scan,
  s.n_tup_ins, s.n_tup_upd, s.n_tup_del, s.n_tup_hot_upd,
  s.last_vacuum, s.last_autovacuum, s.last_analyze, s.last_autoanalyze,
  s.vacuum_count, s.autovacuum_count, s.analyze_count, s.autoanalyze_count,
  io.heap_blks_read, io.heap_blks_hit,
  io.idx_blks_read,  io.idx_blks_hit,
  r.relfrozenxid, age(r.relfrozenxid) AS frozenxid_age,
  r.relminmxid,   mxid_age(r.relminmxid) AS minmxid_age,
  r.reloptions,
  c.pk_cnt, c.uq_cnt, c.fk_cnt, c.ck_cnt,
  p.is_parent, p.child_count, p.is_child, p.partkeydef,
  r.comment
FROM rels r
LEFT JOIN sizes sz          ON sz.relid = r.relid
LEFT JOIN stats s           ON s.relid = r.relid
LEFT JOIN io                ON io.relid = r.relid
LEFT JOIN constraints c     ON c.relid = r.relid
LEFT JOIN partitioning p    ON p.relid = r.relid
LEFT JOIN pg_tablespace ts  ON ts.oid = r.reltablespace
ORDER BY sz.total_bytes DESC NULLS LAST, r.schema, r.rel;
```


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


