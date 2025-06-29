### DuckDB
https://realpython.com/python-duckdb

https://www.dbreunig.com/2025/05/03/duckdb-is-the-most-impactful-geospatial-software-in-a-decade.html

https://news.ycombinator.com/item?id=43881468

https://github.com/turbolytics/sql-flow

https://medium.com/@egzonbaruti/getting-started-with-duckdb-and-dbt-a-simple-guide-to-modern-data-transformation-f7c6093a3693


###   DuckDB pg extension?
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

DuckDB pg extension GitHub

4️⃣ Use Cases
✅ Practical benefits of using pg extension:

Testing PostgreSQL queries inside DuckDB before porting to production.

Using advanced SQL functions without rewriting for DuckDB.

Enabling exploratory data analysis on local DuckDB with PostgreSQL idioms.

