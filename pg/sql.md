<https://dbml.dbdiagram.io/home/>


<https://dbfiddle.uk/>   <https://sqlfiddle.com/>     <https://rextester.com/>   <https://schemaspy.org/>

### Find maximum interval of consecutive dates (no gaps)
```sql
WITH date_sequence AS (
    SELECT 
        date_col,
        ROW_NUMBER() OVER (ORDER BY date_col) AS rn,
        date_col - ROW_NUMBER() OVER (ORDER BY date_col) AS group_id
    FROM my_table
    WHERE date_col IS NOT NULL
)
SELECT 
    MIN(date_col) AS start_date,
    MAX(date_col) AS end_date,
    DATEDIFF(MAX(date_col), MIN(date_col)) + 1 AS interval_days
FROM date_sequence
GROUP BY group_id
ORDER BY interval_days DESC
LIMIT 1;
```
### Find maximum gap interval
```sql
WITH ordered_dates AS (
    SELECT 
        date_col,
        LEAD(date_col) OVER (ORDER BY date_col) AS next_date
    FROM my_table
    WHERE date_col IS NOT NULL
)
SELECT 
    date_col AS gap_start,
    next_date AS gap_end,
    DATEDIFF(next_date, date_col) - 1 AS gap_days
FROM ordered_dates
WHERE next_date IS NOT NULL
ORDER BY gap_days DESC
LIMIT 1;
```

### Detect Consecutive Events

```sql
SELECT customer_id, COUNT(*) as streak
FROM (
    SELECT customer_id, event_date,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY event_date) -
    DENSE_RANK() OVER (PARTITION BY customer_id, event_date ORDER BY event_date) as grp
    FROM events
) t
GROUP BY customer_id, grp;
```

### all cities with more customers than the average number of customers per city
```sql
Copy code
SELECT city, COUNT(*) AS customer_count
FROM customers
GROUP BY city
HAVING COUNT(*) > (
    SELECT AVG(customer_count)
    FROM (
        SELECT COUNT(*) AS customer_count
        FROM customers
        GROUP BY city
    ) AS city_counts
);
```
### Handling NULL in NOT IN close

If the set of data inside the NOT IN subquery contains any values that have a NULL value, then the outer query returns no rows.
To avoid this issue, add a check for NULL to the inner query:
```sql
SELECT * FROM department
WHERE department_id NOT IN (
    SELECT department_id
    FROM employee
    WHERE department_id IS NOT NULL
);
```

### Handle NULL in aggregation using COALESCE
```sql
SELECT department_id,
AVG(COALESCE(salary, 0)) AS avg_salary,
SUM(COALESCE(salary, 0)) AS total_salary
FROM employees
GROUP BY department_id;
```
### WITH ... AS VALUES
```sql
WITH sample_data(id, name, age) AS (
    VALUES
        (1, 'Alice', 30),
        (2, 'Bob', 25),
        (3, 'Charlie', 35)
)
SELECT *
FROM sample_data
WHERE age > 28;
```

### Pivot rows to columns

```sql
SELECT 
    A,
    MAX(CASE WHEN B = 'b1' THEN B END) AS b1,
    MAX(CASE WHEN B = 'b2' THEN B END) AS b2,
    MAX(CASE WHEN B = 'b3' THEN B END) AS b3
FROM T
GROUP BY A;
```
If you want a different aggregation (e.g., COUNT of occurrences instead of the value itself),  
you could replace MAX(B) with  
```COUNT(CASE WHEN B = 'b1' THEN 1 END)```  
to count how many times b1 appears for each A.

What if we want to add one more calculated column to SQL above to be AVG(b1,b2, b3)?

```sql
SELECT 
    A,
    MAX(CASE WHEN B = 'b1' THEN c1 END) AS b1,
    MAX(CASE WHEN B = 'b2' THEN c2 END) AS b2,
    MAX(CASE WHEN B = 'b3' THEN c3 END) AS b3,
    (
        COALESCE(MAX(CASE WHEN B = 'b1' THEN c1 END), 0) +
        COALESCE(MAX(CASE WHEN B = 'b2' THEN c2 END), 0) +
        COALESCE(MAX(CASE WHEN B = 'b3' THEN c3 END), 0)
    ) / 
    NULLIF(
        (
            (CASE WHEN MAX(CASE WHEN B = 'b1' THEN c1 END) IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN MAX(CASE WHEN B = 'b2' THEN c2 END) IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN MAX(CASE WHEN B = 'b3' THEN c3 END) IS NOT NULL THEN 1 ELSE 0 END)
        ),
        0
    ) AS _Avg
FROM T
GROUP BY A;
```
Another way to do it:
```sql
SELECT 
    A,
    MAX(CASE WHEN B = 'b1' THEN c1 END) AS b1,
    MAX(CASE WHEN B = 'b2' THEN c2 END) AS b2,
    MAX(CASE WHEN B = 'b3' THEN c3 END) AS b3,
    (COALESCE(MAX(CASE WHEN B = 'b1' THEN c1 END), 0) + 
     COALESCE(MAX(CASE WHEN B = 'b2' THEN c2 END), 0) + 
     COALESCE(MAX(CASE WHEN B = 'b3' THEN c3 END), 0)) / 
    (CASE WHEN MAX(CASE WHEN B = 'b1' THEN c1 END) IS NULL THEN 0 ELSE 1 END +
     CASE WHEN MAX(CASE WHEN B = 'b2' THEN c2 END) IS NULL THEN 0 ELSE 1 END +
     CASE WHEN MAX(CASE WHEN B = 'b3' THEN c3 END) IS NULL THEN 0 ELSE 1 END) AS _Avg
FROM T
GROUP BY A;
```

Convert months from row to columns
```sql
SELECT 
    product_id,
    SUM(CASE WHEN MONTH(sale_date) = 1 THEN sales ELSE 0 END) as January,
    SUM(CASE WHEN MONTH(sale_date) = 2 THEN sales ELSE 0 END) as February,
    SUM(CASE WHEN MONTH(sale_date) = 3 THEN sales ELSE 0 END) as March
FROM sales
GROUP BY product_id;
```

<https://modern-sql.com/use-case/pivot>

### HAVING 

Find customers who made their first order in the last month.
```sql
SELECT customer_id, MIN(order_date) AS first_order_date 
FROM orders 
GROUP BY customer_id 
HAVING MIN(order_date) >= DATEADD(month, -1, GETDATE());
```

Identify employees assigned to more than one department.
```
SELECT employee_id 
FROM employee_departments 
GROUP BY employee_id 
HAVING COUNT(DISTINCT department_id) > 1;
```


### IN, NOT IN

if IN list is generated as sub-select then make sure it does not contains NULL!

Find Products with Zero Sales in the Last Quarter
```sql
SELECT product_id, product_name 
FROM products 
WHERE product_id NOT IN ( 
    SELECT DISTINCT product_id 
    FROM sales 
    WHERE sale_date >= DATEADD(quarter, -1, GETDATE()) 
);
```

Identify customers who have never ordered product XYZ
```sql
SELECT customer_id 
FROM customers 
WHERE customer_id NOT IN ( 
    SELECT DISTINCT customer_id 
    FROM orders 
    WHERE product_id = 'XYZ' 
);
```

#### Delete duplicates
To delete duplicates (keeping the lowest ID):
```sql
DELETE FROM employees
WHERE id NOT IN (
    SELECT MIN(id)
    FROM employees
    GROUP BY name, department_id, salary)
```
#### Remove duplicate rows but keep the most recent based on a timestamp
```sql
DELETE FROM employees
WHERE id NOT IN (
  SELECT MAX(id)
  FROM employees
  GROUP BY email
```
### GROUP_CONCAT
```
GROUP_CONCAT and STRING_AGG are both SQL functions used to concatenate (combine)
values from multiple rows into a single string, grouped by a specific column. 
The key differences between them mainly depend on which SQL database you are using,
as they are not part of the same SQL standard.
GROUP_CONCAT: MySQL, SQLite
STRING_AGG:  PostgreSQL, SQL Server, Oracle
```

There are 2 tables with 1 : M relation. The join output shall have 2 columns:  
1st column - from Parent table and  
2nd column - concatenation of all related records from the child table.  
A total number of records in output shall be # of records in the parent table.  
```sql
SELECT P.parent_name, GROUP_CONCAT(C.child_name)
FROM Parent P INNER JOIN Child C
ON P.id = C.parent_id
GROUP BY P.parent_name
```

### STRING_AGG
```
SELECT category_id, STRING_AGG(product_name, ', ') as product_list
FROM products
GROUP BY category_id;
```

### COALESCE - returns 1st not null value
```sql
SELECT COALESCE(column1, column2, 'default_value') AS result
FROM table_name;
```

### GREATEST and LEAST
```sql
SELECT
GREATEST(5, 18, 21, 3, 65) AS GREATEST_CHECK,
LEAST(5, 18, 21, 3, 65) AS LEAST_CHECK;
```


### SELECT Top N Rows For Each Group
```sql
WITH CTE AS (
  SELECT
    <group_column>,
    <value_column>,
    ROW_NUMBER() OVER (PARTITION BY <group_column> ORDER BY <value_column> DESC) AS row_num
  FROM T
)
SELECT * FROM CTE WHERE row_num <= N;

-- Retrieve top 2 salespersons per region
WITH  CTE  AS (
  SELECT *, ROW_NUMBER()  OVER (PARTITION BY  Region  ORDER BY  Revenue DESC)  AS  row_num
  FROM Sales
)
SELECT * FROM CTE WHERE row_num <= 2;
```

### Find 3 top payed employees per department
```sql
SELECT emp_id, dep_id, salary
FROM (
  SELECT 
    emp_id,
    dep_id,
    salary,
    ROW_NUMBER() OVER (PARTITION BY dep_id ORDER BY salary DESC) AS rn
  FROM employees
) ranked
WHERE rn <= 3;
```
RANK() assigns the same rank to employees with equal salary.

If the third-highest salary is shared by multiple employees, all of them will be included.

The outer WHERE rk <= 3 filters by rank, not row count, so ties are respected.

### correlated subquery usually slow
Second highest salary per department
```sql
SELECT department_id, MAX(salary) AS second_highest_salary 
FROM employees 
WHERE salary < ( 
    SELECT MAX(salary) 
    FROM employees e 
    WHERE e.department_id = employees.department_id 
) 
GROUP BY department_id;
```

### recursive SQL
```sql
WITH RECURSIVE EmployeeHierarchy AS (
    SELECT employee_id, manager_id, 1 as level
    FROM employees
    WHERE manager_id IS NULL -- Starting point, top manager
    
    UNION ALL
    
    SELECT e.employee_id, e.manager_id, eh.level + 1
    FROM employees e
    JOIN EmployeeHierarchy eh ON e.manager_id = eh.employee_id
)
SELECT * FROM EmployeeHierarchy;
```
Generate dates with recursive SQL
```sql
WITH RECURSIVE dates AS (
    SELECT DATE '2025-01-01' AS dt
    UNION ALL
    SELECT dt + INTERVAL '1 day'
    FROM dates
    WHERE dt < DATE '2025-01-07'
)
SELECT dt
FROM dates;
```

### JSON
```sql
SELECT JSON_VALUE(customer_data, '$.name') AS name, 
JSON_VALUE(customer_data, '$.age') AS age
FROM support_logs;
```

### REGEX
```sql
SELECT column_name
FROM table_name
WHERE column_name REGEXP 'pattern';


SELECT column_name
FROM users
WHERE column_name REGEXP '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}';
```

### INTERSECT EXCEPT
```sql
SELECT country FROM people
INTERSECT
SELECT country FROM customers;

SELECT country FROM people
EXCEPT
SELECT country FROM customers;
```

### SUBSTRING , SUBSTRING_INDEX, POSITION and REPLACE
```sql
SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(column_name, 'key=', -1), ';', 1) AS value
FROM table_name;
```
### ESCAPE
```sql
SELECT *
FROM employees
WHERE name LIKE 'A\_%' ESCAPE '\';
```

### Find gaps in numeric column
```sql
SELECT (t1.id + 1) AS start_gap
FROM employees t1
LEFT JOIN employees t2 ON t1.id + 1 = t2.id
WHERE t2.id IS NULL;
```
## Window functions

### Running total and avg


For SUM(), AVG(), COUNT() (aggregates), the default frame is:

RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW

This means:

It will include all rows in the partition up to the current row, based on the ORDER BY clause.

If ORDER BY is missing → the entire partition is used.

✅ So yes: PARTITION BY defines the "window" (grouping), but ORDER BY defines how that group is processed and what the "frame" is by default.

 Example:

SUM(salary) OVER (PARTITION BY emp_id ORDER BY month)  
Means: Partition: All rows with the same emp_id
Order: By month  

Frame (implicitly): From the first month to the current month (RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

```sql
SELECT id,month
 , salary
 , SUM(salary) OVER (ORDER BY id) as running_sum
FROM bill
```

#### running avg : ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
```sql
SELECT
  name,
  salary,
  AVG(salary) OVER (
    ORDER BY salary
    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
  ) AS running_avg
FROM employees;
```

#### running total

```
SELECT
  name,
  salary,
  SUM(salary) OVER (
    ORDER BY salary
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS running_total
FROM employees;
```

```sql

SELECT
  month,
  emp_id,
  SUM(salary) OVER (
    PARTITION BY emp_id
    ORDER BY month
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS total_salary
FROM employees;
```

###  What happens if you omit PARTITION BY in the OVER() clause?
Answer:
The function treats the entire dataset as a single partition, applying the calculation to all rows.

### example:
```sql
SELECT
    transaction_id,
    change,
    sum(change) OVER (ORDER BY transaction_id) as balance,
    sum(change) OVER () as result_balance,
    round(
        100.0 * sum(change) OVER (ORDER BY transaction_id)  /  sum(change) OVER (),
        2
    ) AS percent_of_result,
    count(*) OVER () as transactions_count
FROM balance_change
ORDER BY transaction_id;
```

### LAG and LEAD
LAG(column, skip=1, default_val): Retrieves data from a previous row  
for very 1st row LAG(col) returns NULL, if we donot want NULL then provide default_val

```sql
SELECT 
  user_id,  event_date,
  LAG(event_date) OVER (PARTITION BY user_id ORDER BY event_date) AS prev_event
FROM events;
```
LEAD(): Retrieves data from a next row  

Example: calculate sales difference between consecutive days
```sql
SELECT product_id, sale_date, sales,
  sales - LAG(sales)
  OVER (PARTITION BY product_id ORDER BY sale_date) AS sales_diff
FROM daily_sales;
```

```sql
SELECT 
    game_name,
    platform,
    year_of_release,
    global_sales,
    LAG(global_sales, 1) OVER (ORDER BY year_of_release) AS previous_sales,
    LEAD(global_sales, 1) OVER (ORDER BY year_of_release) AS next_sales
FROM 
    video_games;


SELECT
    id,
    section,
    header,
    score,
    row_number() OVER w        AS rating,
    lag(score) OVER w - score  AS score_lag
FROM news
WINDOW w AS (ORDER BY score DESC)
ORDER BY score desc;

```

Compute the average number of days between orders for each customer.
```sql
SELECT customer_id, 
  AVG(DATEDIFF(day, LAG(order_date) OVER
  (PARTITION BY customer_id ORDER BY order_date), order_date))
  AS avg_days_between_orders 
FROM orders;
```
### FIRST_VALUE, LAST_VALUE
```sql
SELECT 
    game_name,
    platform,
    year_of_release,
    global_sales,
    FIRST_VALUE(year_of_release) OVER (PARTITION BY platform ORDER BY year_of_release)
    AS first_sales,
    LAST_VALUE(year_of_release) OVER
    (PARTITION BY platform
    ORDER BY year_of_release RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
AS last_sales
FROM 
    video_games;
```

### RANK()
Assigns the same rank to rows with identical values but leaves gaps in the ranking sequence.  
For example, if 5 rows are tied for rank 1,    
the next rank assigned will be 6 (skipping rank 2,3,4 and 5).

Identify the highest revenue month per year:
```sql
SELECT year, month, revenue 
FROM ( 
    SELECT year, month, revenue, 
           RANK() OVER (PARTITION BY year ORDER BY revenue DESC) AS rank 
    FROM monthly_revenue 
) AS yearly_revenue 
WHERE rank = 1;
```

### DENSE_RANK() 
Assigns the same rank to rows with identical values but does not leave gaps in the ranking sequence.   
For example, if 5 rows are tied for rank 1, the next rank assigned will be 2 (no gap).

### NTILE
To divide data into "n" equally distributed groups (buckets).
```sql
SELECT employee_id, salary,
       NTILE(4) OVER (ORDER BY salary DESC) AS quartile
FROM employees;
```

### PERCENT_RANK() and CUME_DIST()

PERCENT_RANK() Gives the relative rank of a row within its partition as a percentage of the total number of rows.

Output range: 0.0 - 1.0

Formula:

PERCENT_RANK = (RANK() - 1) / (total_rows_in_partition - 1)


CUME_DIST (Cumulative Distribution)

Shows the proportion of rows that have a value less than or equal to the current row’s value.

Output range: > 0.0 to 1.0

Formula:

CUME_DIST = number_of_rows_with_value_≤_current / total_rows


```sql
SELECT employee_id, salary,
       PERCENT_RANK() OVER (ORDER BY salary) AS percent_rank,
       CUME_DIST() OVER (ORDER BY salary) AS cumulative_dist
FROM employees;
```

### Multiple columns in PARTITION BY

```sql
SELECT employee_id, department_id, job_id, salary,
       AVG(salary) OVER (PARTITION BY department_id, job_id) AS avg_salary
FROM employees;
```

### (ROWS / RANGE)  BETWEEN in window frames

| Aspect              | `ROWS BETWEEN`                      | `RANGE BETWEEN`                            |
| ------------------- | ----------------------------------- | ------------------------------------------ |
| Basis               | Physical row offset                 | Value-based range                          |
| Handles duplicates? | No special handling                 | Includes all **peer** rows with same value |
| Common with...      | RANK-like use cases, running totals | Percentiles, cumulative metrics by value   |
| Requires ordering?  | Yes                                 | Yes                                        |


Sums sales from rows where the date is within 2 days of the current row’s date.
```sql
SUM(sales) OVER (ORDER BY date RANGE BETWEEN INTERVAL '2' DAY PRECEDING AND CURRENT ROW)
```

 Includes all rows with salary less than or equal to the current row's salary:
```sql 
SUM(sales) OVER (ORDER BY salary RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
```

```sql
SELECT sale_date, sales,
       AVG(sales) OVER (ORDER BY sale_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS avg_rows,
       AVG(sales) OVER (ORDER BY sale_date RANGE BETWEEN INTERVAL '2 day' PRECEDING AND CURRENT ROW) AS avg_range
FROM daily_sales;
```
### RANGE BETWEEN CURRENT FOLLOWING UNBOUNDED PRECEDING

x PRECEDING: x rows before the current row  
y FOLLOWING: y rows after the current row  
ROWS UNBOUNDED PRECEDING means: the frame's lower bound is simply infinite. 
UNBOUNDED FOLLOWING means: all rows after the current row  

This is useful when calculating sums (i.e. "running totals"), for instance:
```sql
WITH data (t, a) AS (
  VALUES(1, 1),
        (2, 5),
        (3, 3),
        (4, 5),
        (5, 4),
        (6, 11)
)
SELECT t, a, sum(a) OVER (ORDER BY t ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
FROM data
ORDER BY t
```
 
#### rolling average sales for each day over the past 7 days.
```sql
SELECT 
    sale_date, sales_amount, 
    AVG(sales_amount) OVER
   (ORDER BY sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_avg_7_days 
FROM daily_sales;
```
#### calculate the average amount in a frame of three days

```sql
-- previous row (1 preceding) and the subsequent row (1 following).
WITH data (t, a) AS (
  VALUES(1, 1),
        (2, 5),
        (3, 3),
        (4, 5),
        (5, 4),
        (6, 11)
)
SELECT t, a, avg(a) OVER (ORDER BY t ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING)
FROM data
ORDER BY t
;

with data as (
    select 3 val from dual union all
    select 6 val from dual union all
    select 3 val from dual union all
    select 5 val from dual union all
    select 4 val from dual
)
select n, val, avg(val)
over(order by n rows between current row and 1 following) avg
from (select rownum n, val from data) t;

```
### find people with 3 or more consequtive ERROR types
```sql
WITH error_ranks AS (
  SELECT 
    a.mac,
    act.type,
    act.dt,
    act.account_id,
    ROW_NUMBER() OVER (PARTITION BY a.mac ORDER BY act.dt) AS rn_all,
    ROW_NUMBER() OVER (PARTITION BY a.mac, act.type ORDER BY act.dt) AS rn_type
  FROM accounts a
  JOIN activities act ON a.id = act.account_id
  WHERE act.type = 'ERROR'
),
sequence_groups AS (
  SELECT 
    mac,
    type,
    dt,
    rn_all - rn_type AS seq_group
  FROM error_ranks
),
grouped_sequences AS (
  SELECT 
    mac,
    type,
    MIN(dt) AS started_at,
    MAX(dt) AS ended_at,
    COUNT(*) AS activities
  FROM sequence_groups
  GROUP BY mac, type, seq_group
  HAVING COUNT(*) >= 3
)
SELECT 
  mac,
  type,
  started_at,
  ended_at,
  activities
FROM grouped_sequences
ORDER BY mac, started_at;
```


 
### Query to find out the third-highest mountain name for each country;  order the country in ASC order.

Table: mountains


|name                 |height|country      |
|---------------------|------|-------------|
|Denalli              |20310 |United States|
|Saint Elias          |18008 |United States|
|Foraker              |17402 |United States|
|Pico de Orizab       |18491 |Mexico       |
|Popocatépetl         |17820 |Mexico       |
|Iztaccihuatl         |17160 |Mexico       |

 
```sql
SELECT country, name
FROM (
  SELECT "country", "name",
          RANK() OVER (PARTITION BY "country" ORDER BY "height" DESC) as "rank"
  FROM mountains
  ) as m
WHERE "rank" = 3
ORDER BY country ASC
```
### Find the number of pages that are currently on with latest_event
Prompt: Given the following table with information about when the status of a page was changed.   
Write a query to find the number of pages that are currently on with the latest_event.

Hint: The page_flag column will be used to identify whether or not a page is “OFF” or “ON”.

Table: pages_info

|page_id|event_time                            |page_flag |
|-------|-------------------------------------------------|
|1      |current_timestamp - interval '6 hours'|ON        |
|1      |current_timestamp - interval '3 hours'|OFF       |
|1      |current_timestamp - interval '1 hours'|ON        |
|2      |current_timestamp - interval '3 hours'|ON        |
|2      |current_timestamp - interval '1 hours'|OFF       |
|3      |current_timestamp                     |ON        |

Solution

First, for each page id, let’s select the latest record (based on the event time column):
```sql
select
   page_id,
   max(event_time) as latest_event
from pages_info
group by page_id
```
Now, we need to join the previous query with the original table,  
and check how many of them have their flagged pages is equals to ON.   
```sql
with latest_event as (
select
   page_id,
   max(event_time) as latest_event
from pages_info
group by page_id
)
select
  sum(
      case
      when page_flag = 'ON' then 1
      else 0
      end
     ) as result
from pages_info pi
join latest_event le on pi.page_id = le.page_id and pi.event_time = le.latest_event;
```
###  Given a table with information about the visits of users to a web page. 
Write a query to return the 3 users with the longest continuous streak of visiting the page.
Order the 3 users from longest to shortest streak.

Table: visits

|user_id |date                        | 
|--------|----------------------------|
|1       |current_timestamp::DATE - 0 |
|1       |current_timestamp::DATE - 1 |
|1       |current_timestamp::DATE - 2 |
|1       |current_timestamp::DATE - 3 |
|1       |current_timestamp::DATE - 4 |
|2       |current_timestamp::DATE - 1 |
|4       |current_timestamp::DATE - 0 |
|4       |current_timestamp::DATE - 1 |
|4       |current_timestamp::DATE - 3 |
|4       |current_timestamp::DATE - 4 |
|4       |current_timestamp::DATE - 62|   

Solution

First, let’s add a new column whose value is the next visit (different from the current date) for each user. We are gonna use the lead function to do so:
```sql
select distinct
user_id,
date,
lead(date) over (partition by user_id order by date) as next_date
from (select distinct * from visits) as t;
```
Once we have this, let’s create another column whose purpose will be to let us know then a streak stops. This basically consists in checking when the next date is different from the current date + 1. Like this
```sql
with next_dates as (
select distinct
user_id,
date,
lead(date) over (partition by user_id order by date) as next_date
from (select distinct * from visits) as t -- remove duplicates
)
select
user_id,
date,
next_date,
case
when next_date is null or next_date = date + 1 then 1
else null
end as streak
from next_dates;
```
Once we have this, we are gonna create a partition for each user, where each partition represents a continuous streak. 
Conceptually, what we are going to do is, for each user,   take the most recent record (based on date) and assign 0, 
then look for the following record and assign 0 if the streak hasn’t stopped,   
or 1 if the streak stopped (if the streak column is null),  
and then continuing doing this until each streak is represented by a different partition.  
The code that does this logic is the following:
```sql
with next_dates as (
select distinct
user_id,
date,
lead(date) over (partition by user_id order by date) as next_date
from (select distinct * from visits)
),
streaks as (
select
user_id,
date,
next_date,
case
when next_date is null or next_date = date + 1 then 1
else null
end as streak
from next_dates
)
select
*,
sum(
case
when streak is null then 1
else 0
end
) over (partition by user_id order by date) as partition
from streaks;
```
Once we have this partition the problem is easier, now we only need to calculate the number of records per user and partition, and find the users with the greatest count. The complete query will look like this:
```sql
with next_dates as (
select distinct
user_id,
date,
lead(date) over (partition by user_id order by date) as next_date
from visits
),
streaks as (
select
user_id,
date,
next_date,
case
when next_date is null or next_date = date + 1 then 1
else null
end as streak
from next_dates
),
partitions as (
select
*,
sum(
case
when streak is null then 1
else 0
end
) over (partition by user_id order by date) as partition
from streaks
),
count_partitions as (
select user_id, partition, count(1) as streak_days
from partitions
group by user_id, partition
)
select
user_id,
max(streak_days) as longest_streak
from count_partitions
group by user_id
order by 2 desc
limit 3;
```


### Cohort Analysis — New, Active, and Churned Customers
Problem Statement:
Given the table Orders(OrderId, CustID, Date, Category, Value), write a SQL query to output the DATE, COHORT,   
and the NUMBER OF CUSTOMERS categorized as new, active (<90 days), and churn (>90 days).

Approach:
The challenge here was to identify customer activity based on the order date and categorize them as ‘New,’ ‘Active,’ or ‘Churned’ based on the last order date.  
The query used a combination of lag and DATEDIFF to calculate the time difference between the current and the last order date.

```sql

WITH LastActivity AS (
    SELECT 
        CUSTID, 
        DATE AS CURR_DATE,
        LAG(DATE) OVER (
            PARTITION BY CUSTID 
            ORDER BY DATE
        ) AS LAST_ORDER_DATE
    FROM ORDERS
),
ClassifiedActivity AS (
    SELECT 
        CUSTID,
        CURR_DATE,
        LAST_ORDER_DATE,
        DATEDIFF(CURR_DATE, LAST_ORDER_DATE) AS DATEDIFFE
    FROM LastActivity
)
SELECT 
    CURR_DATE AS DATE,
    CASE
        WHEN LAST_ORDER_DATE IS NULL THEN 'NEW'
        WHEN DATEDIFFE <= 90 THEN 'ACTIVE'
        ELSE 'CHURN'
    END AS COHORT,
    COUNT(DISTINCT CUSTID) AS NUMBER_OF_CUSTOMERS
FROM ClassifiedActivity
GROUP BY CURR_DATE, COHORT
ORDER BY CURR_DATE, COHORT;
```


<!--
<https://github.com/Michael-Lubinsky/michael-lubinsky.github.com/blob/main/pg/Window_Functions_Cheat_Sheet_Letter.pdf>  

https://mayursurani.medium.com/mastering-advanced-sql-20-interview-questions-that-separate-senior-data-engineers-from-the-rest-cf41e9162e73

https://leonwei.com/a-collection-of-google-sql-coding-interview-questions-8dd19b060abe
https://blog.devgenius.io/my-tough-sql-interview-experience-at-paytm-what-i-was-asked-and-what-i-learned-e987f88de733
<https://medium.com/h7w/sql-interview-at-microsoft-apple-ibm-b5d94f0194eb>
<https://medium.com/ai-ml-interview-playbook/top-10-sql-interview-questions-youll-actually-be-asked-d8ca55930d68>
<https://blog.devgenius.io/advanced-sql-interview-quesiton-top-3-product-combinations-245ce6e9c068>
<https://medium.com/@shaloomathew/sql-window-functions-part-1-40aff4421077>  
<https://medium.com/@mariusz_kujawski/advanced-sql-for-data-professionals-875ab725730c>  
<https://medium.com/@esrasoylu/advanced-sql-techniques-7016163019eb>  
<https://skphd.medium.com/sql-scenario-based-interview-questions-and-answers-08d6ca4bcabf>

data modeling
https://medium.com/projectpro/4-advanced-data-modelling-techniques-every-data-engineer-must-learn-1113bcf7f5e9
-->
