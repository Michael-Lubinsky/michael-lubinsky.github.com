
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
CREATE INDEX idx_event_data_gin ON user_events USING GIN (event_data);  
-- Equivalent to:

CREATE INDEX idx_event_data_gin ON user_events USING GIN (event_data jsonb_ops);  

This creates index entries for every key and value, supporting all JSONB operators but creating larger indexes.

#### jsonb_path_ops (Optimized for Containment)

CREATE INDEX idx_event_data_gin_path ON user_events USING GIN (event_data jsonb_path_ops);

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



<https://medium.com/@richardhightower/jsonb-postgresqls-secret-weapon-for-flexible-data-modeling-cf2f5087168f>
