## Get single row jsonb column named properties  for all tables and format it as table, attr_name, attr_value
```sql
-- Main procedure to extract properties for Confluence
CREATE OR REPLACE FUNCTION events.extract_properties_for_confluence()
RETURNS TABLE (
    table_name text, 
    attribute_name text, 
    attribute_value text
)
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
    prop_record RECORD;
    query text;
    table_full_name text;
BEGIN
    -- Loop through all tables in events schema that have properties column
    FOR r IN
        SELECT n.nspname AS schema_name,
               c.relname AS tbl
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE n.nspname = 'events'
          AND c.relkind = 'r'
          AND a.attname = 'properties'
          AND a.atttypid = 'jsonb'::regtype
          AND c.relname NOT SIMILAR TO '%[0-9]%'
        ORDER BY c.relname
    LOOP
        table_full_name := r.schema_name || '.' || r.tbl;
        
        BEGIN
            -- Build dynamic query to extract key-value pairs from properties
            query := format($query$
                SELECT key as attr_name, 
                       COALESCE(value, 'null') as attr_value
                FROM %I.%I,
                     jsonb_each_text(properties)
                WHERE properties IS NOT NULL 
                  AND jsonb_typeof(properties) = 'object'
                ORDER BY key
                LIMIT 1000
            $query$, r.schema_name, r.tbl);
            
            -- Execute query and return each key-value pair as a separate row
            FOR prop_record IN EXECUTE query
            LOOP
                table_name := table_full_name;
                attribute_name := prop_record.attr_name;
                attribute_value := prop_record.attr_value;
                RETURN NEXT;
            END LOOP;
            
        EXCEPTION 
            WHEN NO_DATA_FOUND THEN
                -- Table has no rows with properties
                table_name := table_full_name;
                attribute_name := '(no data)';
                attribute_value := '(table is empty)';
                RETURN NEXT;
            WHEN OTHERS THEN
                -- Handle any other errors
                table_name := table_full_name;
                attribute_name := '(error)';
                attribute_value := 'Error: ' || SQLERRM;
                RETURN NEXT;
        END;
    END LOOP;
END;
$$;

-- Helper function to generate Confluence table format
CREATE OR REPLACE FUNCTION events.generate_confluence_table()
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    result_text text := '';
    r RECORD;
    is_first_row boolean := true;
BEGIN
    -- Add Confluence table header
    result_text := result_text || '||Table||Attribute Name||Attribute Value||' || E'\n';
    
    -- Get data and format for Confluence
    FOR r IN 
        SELECT table_name, attribute_name, attribute_value 
        FROM events.extract_properties_for_confluence()
        ORDER BY table_name, attribute_name
    LOOP
        result_text := result_text || '|' || r.table_name || '|' || r.attribute_name || '|' || r.attribute_value || '|' || E'\n';
    END LOOP;
    
    RETURN result_text;
END;
$$;

-- Alternative: Generate as simple CSV without quotes
CREATE OR REPLACE FUNCTION events.generate_properties_csv()
RETURNS text
LANGUAGE plpgsql
AS $
DECLARE
    result_text text := '';
    r RECORD;
BEGIN
    -- Add CSV header
    result_text := result_text || 'Table,Attribute Name,Attribute Value' || E'\n';
    
    -- Get data and format as simple CSV (no quotes unless necessary)
    FOR r IN 
        SELECT table_name, attribute_name, attribute_value 
        FROM events.extract_properties_for_confluence()
        ORDER BY table_name, attribute_name
    LOOP
        -- Simple comma-separated format without quotes
        result_text := result_text || 
            r.table_name || ',' ||
            r.attribute_name || ',' ||
            r.attribute_value || E'\n';
    END LOOP;
    
    RETURN result_text;
END;
$;

-- Simple query version for direct copy-paste
CREATE OR REPLACE VIEW events.properties_confluence_view AS
SELECT 
    table_name,
    attribute_name,
    attribute_value
FROM events.extract_properties_for_confluence()
ORDER BY table_name, attribute_name;
```
## Clean Output (No Quotes):

### 1. **Direct Query (Clean Results)**
```sql
SELECT * FROM events.properties_confluence_view;
```
**Output:**
```
table_name                | attribute_name | attribute_value
events.user_login        | user_id        | 12345
events.user_login        | timestamp      | 2024-01-15
events.page_view         | page_url       | /dashboard
```

### 2. **Clean CSV Format**
```sql
SELECT events.generate_properties_csv();
```
**Output:**
```
Table,Attribute Name,Attribute Value
events.user_login,user_id,12345
events.user_login,timestamp,2024-01-15
events.page_view,page_url,/dashboard
```

### 3. **Tab-Separated for Easy Copy-Paste**
If you want even cleaner formatting for Confluence, here's a tab-separated version:

```sql
-- Create tab-separated version for easy copy-paste
CREATE OR REPLACE FUNCTION events.generate_properties_tsv()
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    result_text text := '';
    r RECORD;
BEGIN
    -- Add tab-separated header
    result_text := result_text || 'Table' || E'\t' || 'Attribute Name' || E'\t' || 'Attribute Value' || E'\n';
    
    -- Get data and format as tab-separated
    FOR r IN 
        SELECT table_name, attribute_name, attribute_value 
        FROM events.extract_properties_for_confluence()
        ORDER BY table_name, attribute_name
    LOOP
        result_text := result_text || 
            r.table_name || E'\t' ||
            r.attribute_name || E'\t' ||
            r.attribute_value || E'\n';
    END LOOP;
    
    RETURN result_text;
END;
$$;
```

## Recommended Usage:

**For cleanest copy-paste into Confluence:**
```sql
SELECT * FROM events.properties_confluence_view;
```

This will give you clean results without any quotes that you can directly copy and paste into Confluence as a table. The view returns the raw data in three columns that Confluence can easily format into a table.
