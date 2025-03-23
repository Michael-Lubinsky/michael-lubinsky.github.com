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

<https://modern-sql.com/use-case/pivot>

### HAVING 

Find customers who made their first order in the last month.
```sql
SELECT customer_id, MIN(order_date) AS first_order_date 
FROM orders 
GROUP BY customer_id 
HAVING MIN(order_date) >= DATEADD(month, -1, GETDATE());
```

### GROUP_CONCAT
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
```
SELECT country FROM people
INTERSECT
SELECT country FROM customers;

SELECT country FROM people
EXCEPT
SELECT country FROM customers;
```

### SUBSTRING , SUBSTRING_INDEX, POSITION and REPLACE
```
SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(column_name, 'key=', -1), ';', 1) AS value
FROM table_name;
```
## Window functions

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
```
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

### RANK ():
Assigns the same rank to rows with identical values but leaves gaps in the ranking sequence.  
For example, if 5 rows are tied for rank 1,    
the next rank assigned will be 6 (skipping rank 2,3,4 and 5).

### DENSE_RANK (): 
Assigns the same rank to rows with identical values but does not leave gaps in the ranking sequence.   
For example, if 5 rows are tied for rank 1, the next rank assigned will be 2 (no gap).


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
    sale_date, 
    sales_amount, 
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
<https://github.com/Michael-Lubinsky/michael-lubinsky.github.com/blob/main/pg/Window_Functions_Cheat_Sheet_Letter.pdf>  

<https://medium.com/@mariusz_kujawski/advanced-sql-for-data-professionals-875ab725730c>  
<https://medium.com/@esrasoylu/advanced-sql-techniques-7016163019eb>
