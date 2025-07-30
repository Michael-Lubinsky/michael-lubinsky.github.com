
## Postgres JSONB

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
<https://medium.com/@sohail_saifi/the-postgresql-index-type-that-makes-complex-queries-100x-faster-8fdd4e0474cc>
```sql
CREATE INDEX idx_event_data_gin ON user_events USING GIN (event_data);
```
PostgreSQL provides two operator classes for JSONB GIN indexes, each optimized for different query patterns:

### jsonb_ops (Default)
```sql
CREATE INDEX idx_event_data_gin ON user_events USING GIN (event_data);  
```
 Equivalent to:
```sql
CREATE INDEX idx_event_data_gin ON user_events USING GIN (event_data jsonb_ops);  
```

This creates index entries for every key and value, supporting all JSONB operators but creating larger indexes.

#### jsonb_path_ops (Optimized for Containment)
```sql
CREATE INDEX idx_event_data_gin_path ON user_events USING GIN (event_data jsonb_path_ops);
```
This creates smaller indexes (20–30% of table size vs 60–80%) but only supports the @> containment operator.

Test  the difference:
```sql
-- This query works with both operator classes
SELECT COUNT(*) 
FROM user_events 
WHERE event_data @> '{"type": "purchase", "amount": 99.99}';

-- With jsonb_ops: 280ms, index size: 850MB
-- With jsonb_path_ops: 180ms, index size: 290MB

-- This query only works with jsonb_ops
SELECT COUNT(*) 
FROM user_events 
WHERE event_data ? 'promotion_code';  -- Key existence check
```
-- With jsonb_ops: 150ms  
-- With jsonb_path_ops: Sequential scan (doesn't use index)

#### Partial GIN Indexes
Even more powerful pattern: partial GIN indexes.

Since most of our queries filtered by event type first, I created type-specific indexes:
```sql
-- Index only purchase events
CREATE INDEX idx_purchase_events_gin ON user_events 
USING GIN (event_data) 
WHERE event_data->>'type' = 'purchase';

-- Index only recent events (last 90 days)
CREATE INDEX idx_recent_events_gin ON user_events 
USING GIN (event_data) 
WHERE timestamp > NOW() - INTERVAL '90 days';
The purchase events index was tiny (5MB instead of 850MB) but blazingly fast for purchase-specific queries:

-- Find users who bought specific products
SELECT user_id, event_data->>'product_id' as product_id
FROM user_events 
WHERE event_data @> '{"type": "purchase"}'
  AND event_data @> '{"category": "electronics"}';
```
-- With full GIN index: 340ms  
-- With partial GIN index: 45ms

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




### pg_read_file
 pg_read_file is a server side function that allows you to read all of the file or a portion of the file. There are a couple of caveats for it's use.

Requires super user or being member of pg_read_server_files group role
The file you are reading must be readable by the postgres server process  
There is a limitation on read size and you are also restricted on how big of a file you can stuff in a column.   
For most files this has not been an issue.
There is a companion function called pg_read_binary_file for reading data in binary format or for reading text in a specific encoding.

To demonstrate, download: Boston Public Schools json format and put it in C:/temp folder. If you are on Linux would be a path such as /tmp and path references in this doc change C:/Temp to /tmp

Note that this is a GeoJSON file, which means if you had PostGIS installed you could do interesting things with this. But for this exercise, I'm going to treat it like any JSON file.  
This approach doesn't work for big files that can't fit into a single column.

```sql
INSERT INTO data_json(data)
SELECT pg_read_file('C:/temp/public_schools.geojson.json')::jsonb;
```

Using jsonb_array_elements to expand rows

You can combine this with the ->> and -> json operators to select properties. 
Here is how we do it with the sample dataset that is of geojson structure
```sql
CREATE TABLE boston_public_schools AS 
SELECT (je->'id')::bigint AS id, 
	(je->'geometry'->'coordinates'->>0)::float AS longitude,
	(je->'geometry'->'coordinates'->>1)::float AS latitude,
	je->'properties'->>'SCH_NAME' AS sch_name,
	je->'properties'->>'ADDRESS' AS address,
	je->'properties'->>'CITY' AS city,
	je->'properties'->>'ZIPCODE' AS zipcode
FROM data_json 
	CROSS JOIN jsonb_array_elements(data_json.data->'features') AS je;
```
There are 3 features being used in this example, first we are using the -> operator. This operator when applied to a jsonb or json returns back the property as a jsonb or json element. Note that you can burrow into a document by nesting these operator calls as we do with je->'geometry'->'coordinates'->>1

The companion to -> is the ->> operator which returns text instead of a json. You use this when you are done with your burrowing.

Both -> and ->> can take a text or an integer. The integer version is used only for json arrays and returns the nth element of the array. Counting of arrays in JavaScript and by extension JSON starts at 0.

So with these operators you pick out pieces of a json document, but before we do that, we'll want to expand a json document into it's separate rows. For geojson documents, there is always a features property which is an array with each element being a data row.

To break up these rows, you can use jsonb_array_elements, which is a set returning element that only works with jsonb formatted arrays and returns each element of the array as a jsonb object.

Your table should end up looking like this
```

SELECT * FROM boston_public_schools LIMIT 3;
id |     longitude      |     latitude      |       sch_name       |       address       |    city     | zipcode
----+--------------------+-------------------+----------------------+---------------------+-------------+---------
  1 | -71.00412000099993 | 42.38879000000003 | Guild Elementary     | 195 Leyden Street   | East Boston | 02128
  2 | -71.03047970999995 | 42.37853662100008 | Kennedy Patrick Elem | 343 Saratoga Street | East Boston | 02128
  3 | -71.03389000099997 | 42.37527000000006 | Otis Elementary      | 218 Marion Street   | East Boston | 02128
```
Using JSON_TABLE to expand rows and columns
Introduced in PostgreSQL 17 is the ISO-SQL standard JSON_TABLE function, which if you are familar with XML follows more or less the same pattern as XMLTABLE.   
It utilizes json path syntax to parse out elements.
Here is a repeat of the earlier exercise using JSON_TABLE.  

```sql
DROP TABLE IF EXISTS boston_public_schools;
CREATE TABLE boston_public_schools AS
SELECT
    je.*
FROM
    data_json
CROSS JOIN
    JSON_TABLE (
        data_json.data,
        '$.features[*]' COLUMNS (
            id integer PATH '$.id',
            longitude float PATH '$.geometry.coordinates[0]',
            latitude float PATH '$.geometry.coordinates[1]',
            NESTED PATH '$.properties' COLUMNS (
                sch_name text PATH '$.SCH_NAME',
                address text PATH '$.ADDRESS',
                city text PATH '$.CITY',
                zipcode text PATH '$.ZIPCODE'
            )
        )
    ) AS je;
```
This is a pretty rich function, so you should read the docs to appreciate it's full breath.   
The fact it's an ISO/SQL standard function means you are more likely to find it in other relational databases. 
If you have a heavily nested document, the NESTED PATH subclause comes in handy for saving some typing.



<https://medium.com/@richardhightower/jsonb-postgresqls-secret-weapon-for-flexible-data-modeling-cf2f5087168f>

