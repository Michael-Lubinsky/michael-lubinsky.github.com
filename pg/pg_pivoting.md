### Pivoting in Postgres

There is Postgres table with columns: metric, dimension, val 
the dimension column can have values A, B and C.
Write query which returns the dimensions A, B and C as columns 
 
You can pivot the dimension values (A, B, C) into columns using FILTER with SUM() or CASE WHEN.

✅ Option 1: Using FILTER (PostgreSQL-specific, cleaner)
```sql
SELECT
  metric,
  SUM(val) FILTER (WHERE dimension = 'A') AS A,
  SUM(val) FILTER (WHERE dimension = 'B') AS B,
  SUM(val) FILTER (WHERE dimension = 'C') AS C
FROM your_table
GROUP BY metric
ORDER BY metric;
```
✅ Option 2: Using CASE WHEN (portable)
```sql
SELECT
  metric,
  SUM(CASE WHEN dimension = 'A' THEN val ELSE 0 END) AS A,
  SUM(CASE WHEN dimension = 'B' THEN val ELSE 0 END) AS B,
  SUM(CASE WHEN dimension = 'C' THEN val ELSE 0 END) AS C
FROM your_table
GROUP BY metric
ORDER BY metric;
```

To include unknown or dynamic dimension values as columns, you need to dynamically pivot the data.   
PostgreSQL provides two common methods for this:

✅ Option 1: crosstab() (from tablefunc extension)

This is the most efficient way to pivot dynamically known values.

1. Enable the extension (once per database):
CREATE EXTENSION IF NOT EXISTS tablefunc;

3. Use crosstab():
SELECT * FROM crosstab(
  $$SELECT metric, dimension, val FROM your_table ORDER BY metric, dimension$$
) AS ct(metric TEXT, A INT, B INT, C INT);
Replace A INT, B INT, C INT with the list of expected dimensions.

This still requires you to know the dimensions in advance, so it’s semi-dynamic.

If you want fully dynamic column names, you must use dynamic SQL.

✅ Option 2: Fully Dynamic Pivot Using PL/pgSQL
If you don’t know the dimensions in advance, you need to:

Query all unique dimensions.

Build a pivot SQL dynamically.

Execute it.

Example: dynamic SQL in psql or PL/pgSQL
```sql
DO $$
DECLARE
    col_list TEXT;
    sql TEXT;
BEGIN
    -- Step 1: Build dynamic column list like: 
    -- "MAX(CASE WHEN dimension = 'A' THEN val END) AS A, ..."
    SELECT string_agg(
        format('MAX(CASE WHEN dimension = %L THEN val END) AS %I', dimension, dimension),
        ', '
    )
    INTO col_list
    FROM (SELECT DISTINCT dimension FROM your_table) sub;

    -- Step 2: Build and execute dynamic SQL
    sql := format('SELECT metric, %s FROM your_table GROUP BY metric ORDER BY metric;', col_list);

    RAISE NOTICE 'Query: %', sql; -- for debugging
    EXECUTE sql;
END $$;
```
This prints the result to the console but to return results to a client, you'd need to wrap it in a function that returns TABLE(...).

🟡 Note:
If you need to consume the dynamic result in Python, pandas, etc., then running the dynamic SQL and reading the result as a DataFrame is usually more practical.



When using dynamic SQL inside a DO $$ ... $$; block or a PL/pgSQL function, you can't directly return query results to the client unless you define a function that returns a TABLE (or SETOF RECORD).

Here’s how to do it properly:

✅ 1. Create a function that returns TABLE(...)
If you want to return the result of a dynamic pivot query as a regular result set, you can use RETURN QUERY EXECUTE ... inside a RETURNS TABLE(...) function.

🧩 Example: Pivot dimension values into columns dynamically
CREATE OR REPLACE FUNCTION get_pivoted_metrics()
RETURNS TABLE(metric TEXT, A INT, B INT, C INT)
LANGUAGE plpgsql AS
$$
DECLARE
    sql TEXT;
BEGIN
    -- Build dynamic SQL using known or discovered dimensions
    sql := $sql$
        SELECT
            metric,
            MAX(CASE WHEN dimension = 'A' THEN val END) AS A,
            MAX(CASE WHEN dimension = 'B' THEN val END) AS B,
            MAX(CASE WHEN dimension = 'C' THEN val END) AS C
        FROM your_table
        GROUP BY metric
        ORDER BY metric;
    $sql$;

    -- Return the result of dynamic SQL
    RETURN QUERY EXECUTE sql;
END
$$;
Now you can query it like this:

SELECT * FROM get_pivoted_metrics();
✅ To make it truly dynamic (dimensions unknown at design time):
You'd need to:

Discover dimension values with SELECT DISTINCT dimension.

Dynamically construct the column list and return type.

Use RETURNS SETOF RECORD and cast it when calling.

That looks like:

CREATE OR REPLACE FUNCTION get_dynamic_pivot()
RETURNS SETOF RECORD
LANGUAGE plpgsql AS
$$
DECLARE
    col_list TEXT;
    sql TEXT;
BEGIN
    SELECT string_agg(
        format('MAX(CASE WHEN dimension = %L THEN val END) AS %I', dimension, dimension),
        ', '
    )
    INTO col_list
    FROM (SELECT DISTINCT dimension FROM your_table) sub;

    sql := format('SELECT metric, %s FROM your_table GROUP BY metric', col_list);

    RETURN QUERY EXECUTE sql;
END
$$;
But now you must explicitly specify the expected columns and types when calling it:

SELECT * FROM get_dynamic_pivot()
AS t(metric TEXT, A INT, B INT, C INT, D INT);  -- You must provide a type signature
🔄 Summary
Approach	Returns result to client	Columns known at compile time?	Can be called like regular table?
RETURNS TABLE(...)	✅	✅	✅
RETURNS SETOF RECORD	✅ (with AS t(...))	❌	❌ (manual type declaration needed)
DO $$ BEGIN ... END $$	❌	❌	❌
Let me know if you want a version that automatically infers column names and types without needing to specify them manually at query time — it requires procedural workaround or client-side postprocessing.




No file chosenNo file chosen
ChatGPT can make mistakes. Check important info.
