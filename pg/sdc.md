
## SCD (SLOWLY CHANGING DIMENSION)  


### SCD Type 1 – Overwrite (No History Tracking)
```sql
MERGE INTO customers AS target
USING updates AS source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN
UPDATE SET target.email = source.email;
 ```

### SCD Type 2 – History Tracking
In SCD Type 2, a new row is added for each change, maintaining the complete history.  
Use Case: Tracking customer address changes over time.  
Example:
```sql
MERGE INTO customers_history AS target
USING updates AS source
ON target.customer_id = source.customer_id AND target.end_date IS NULL
-- If a matching record is found and attributes have changed, end the old record
WHEN MATCHED AND (target.name <> source.name OR target.address <> source.address)
THEN
UPDATE SET target.end_date = GETDATE()
-- Insert a new record after ending the previous one
WHEN MATCHED AND (target.name <> source.name OR target.address <> source.address)
THEN
INSERT (customer_id, name, address, start_date, end_date)
VALUES (source.customer_id, source.name, source.address, GETDATE(), NULL)
-- If no matching record exists in the target table, insert the new record
WHEN NOT MATCHED BY TARGET THEN
INSERT (customer_id, name, address, start_date, end_date)
VALUES (source.customer_id, source.name, source.address, GETDATE(), NULL);
```

#### How to implement SCD Type 2 in Databricks?
```
1. Read Source and Target Tables

source_df = spark.read.table("source_data")
target_df = spark.read.table("dim_customer")

2. Identify Changed Records

Join source and target on customer_id, and filter where relevant fields have changed and is_current = true.

3. Expire Old Records (Mark as Inactive)

Use Delta Lake’s MERGE to set is_current = false and update end_date.

MERGE INTO dim_customer AS tgt
USING changed_records AS src
ON tgt.customer_id = src.customer_id AND tgt.is_current = true
WHEN MATCHED THEN 
UPDATE SET tgt.is_current = false, tgt.end_date = current_date()

4. Insert New Versions of Updated Records

Add new rows with is_current = true, start_date = today, and end_date = null.

5. Insert Completely New Records

Detect records that don’t exist in the target (left_anti join), and insert them with the same structure.

Result?
 • You preserve full history
 • The latest record is always marked as is_current = true
 • Queries can filter on date ranges or just the active row
```
 
### SCD Type 3 – Limited History
 In SCD Type 3, only the previous value is kept in an additional column.
Use Case: Tracking a customer’s previous job title.
```sql
MERGE INTO employees AS target
USING updates AS source
ON target.employee_id = source.employee_id
WHEN MATCHED THEN
UPDATE SET target.previous_job_title = target.current_job_title,
target.current_job_title = source.job_title
WHEN NOT MATCHED THEN
INSERT (employee_id, name, current_job_title, previous_job_title)
VALUES (source.employee_id, source.name, source.job_title, NULL);
 ```

### SCD Type 4 – Separate History
In SCD Type 4, historical data is stored in a separate table.  
Use Case: Maintaining a customer’s address history in a dedicated table.
```sql
-- Insert current data into the main table
MERGE INTO customers AS target
USING updates AS source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN
UPDATE SET target.address = source.address;
-- Insert historical data into the history table
INSERT INTO customers_history (customer_id, name, address, change_date)
SELECT customer_id, name, address, current_date()
FROM updates;
 ```

### SCD Type 6 – Hybrid (1+2+3)

Definition: Type 6 is a hybrid approach that combines SCD  
Types 1, 2, and 3 to track both current and historical values.  
Use Case: Tracking both the current address and the previous address of a customer while keeping a full history.
```sql
MERGE INTO customers AS target
USING updates AS source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN
UPDATE SET target.previous_address = target.current_address,
target.current_address = source.address,
target.end_date = current_date()
WHEN NOT MATCHED THEN
INSERT (customer_id, name, current_address, previous_address, start_date, end_date)
VALUES (source.customer_id, source.name, source.address, NULL, current_date(), NULL);
 ```
<https://github.com/bartosz25/data-engineering-design-patterns-book/tree/master/chapter-05/01-data-enrichment/01-static-joiner-data-at-rest>
