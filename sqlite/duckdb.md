### DuckDB
```python
# No need to load CSV file explicitely!
max_q2 = duckdb.execute(
    f"""
    SELECT max(Q2) FROM "{csv_file}";
    """
).fetchone()[0]

print(f"{max_q2} max quantity in csv file")
```

https://realpython.com/python-duckdb

https://realpython.com/courses/starting-duckdb-python/

https://codecut.ai/deep-dive-into-duckdb-data-scientists/

https://sqlrooms.org/ Build data-centric apps with DuckDB

https://medium.com/@shouke.wei/introducing-duckdb-local-ui-a-fast-private-and-interactive-sql-experience-53ce977fe8a9

https://medium.com/@shouke.wei/duckdb-tutorial-the-fast-embedded-analytics-database-7d5d742bb251

https://medium.com/@shouke.wei/complete-guide-to-reading-data-with-duckdb-from-local-files-to-remote-sources-ddb43bd4456f


https://github.com/turbolytics/sql-flow

https://medium.com/@egzonbaruti/getting-started-with-duckdb-and-dbt-a-simple-guide-to-modern-data-transformation-f7c6093a3693

https://towardsdev.com/python-meets-arrow-and-duckdb-for-high-performance-dataframes-21cadff7a62b

https://habr.com/ru/companies/cinimex/articles/913878/

https://medium.com/@hadiyolworld007/7-duckdb-tricks-that-make-pandas-feel-outdated-02d427eb6e66

https://medium.com/@hadiyolworld007/why-i-run-sql-in-python-now-7-duckdb-queries-that-changed-my-workflow-dea9393ca005

## Spacial features
https://duckdb.org/2025/08/08/spatial-joins.html

https://www.dbreunig.com/2025/05/03/duckdb-is-the-most-impactful-geospatial-software-in-a-decade.html

https://news.ycombinator.com/item?id=43881468

###   DuckDB pg extension

<https://motherduck.com/blog/postgres-duckdb-options/>

The pg extension in DuckDB provides PostgreSQL compatibility functions and types inside DuckDB, allowing:

Using PostgreSQL-compatible functions (e.g., unnest, array_agg, generate_series).

Using PostgreSQL-specific data types (JSON, UUID, etc.) inside DuckDB.

Easier SQL migration and compatibility testing from PostgreSQL to DuckDB.

1️⃣ Installing the pg extension in DuckDB
In your DuckDB session:

```sql

INSTALL pg;
LOAD pg;
```
or in Python DuckDB API:

```python

import duckdb
con = duckdb.connect()
con.install_extension('pg')
con.load_extension('pg')
```
✅ After this, PostgreSQL compatibility functions and types become available.

2️⃣ Example usage
Example: using generate_series
```sql

SELECT * FROM generate_series(1, 5);
```
Example: using unnest
```sql
SELECT * FROM unnest([1, 2, 3]) AS t(x);
```
Example: using array_agg
```sql

SELECT array_agg(i) FROM generate_series(1, 3) tbl(i);
```
3️⃣ Checking installed functions and types  
After loading the extension, you can explore:

```sql
SELECT * FROM duckdb_functions() WHERE name LIKE '%generate_series%';
```
or list available functions/types documented here:

<https://github.com/duckdb/duckdb/blob/master/extension/pg/README.md>


4️⃣ Use Cases
✅ Practical benefits of using pg extension:

Testing PostgreSQL queries inside DuckDB before porting to production.

Using advanced SQL functions without rewriting for DuckDB.

Enabling exploratory data analysis on local DuckDB with PostgreSQL idioms.

### GigAPI 
<https://github.com/gigapi/gigapi>

DuckDB + Parquet, чтение из локального диска или S3, запросы через FlightSQL (gRPC) и HTTP, режимы writeonly/readonly/compaction, один контейнер для старта и понятная философия «делай просто, делай быстро».   
Проект обещает суб-секундные аналитические запросы, компактизацию и дружбу с FDAP-миром (Arrow/DataFusion/Parquet/Flight) 
<https://habr.com/ru/articles/955560/>
