https://medium.com/towards-data-engineering/are-you-a-sql-expert-try-solving-these-problems-48c1c809f1b9  
https://towardsaws.com/amazon-sql-hard-level-question-solution-in-detail-e9f3a7d1bd17  
https://medium.com/@bigtechinterviews/5-real-amazon-sql-questions-answers-d1733a2a2c4c  
https://leonwei.com/a-collection-of-amazon-sql-interview-questions-48d84d9612f7  
https://blog.devgenius.io/ace-the-data-science-interview-day-48-amazon-sql-interview-question-1cae2a8136b5  
https://www.stratascratch.com/blog/amazon-sql-interview-questions/  
https://medium.com/@bigtechinterviews/3-most-common-amazon-sql-interview-questions-and-answers-963e33ef27b1  
https://medium.com/@bigtechinterviews/10-latest-meta-facebook-sql-interview-questions-409542618599  
https://medium.com/@lozhihao/ace-the-data-science-interview-40-amazon-sql-interview-question-82164206ad03  
https://medium.com/@gunjansahu/leetcode-amazon-sql-interview-questions-list-43b034353732  

https://medium.com/towards-data-engineering/are-you-a-sql-expert-try-solving-these-problems-48c1c809f1b9  



###  "gaps and islands" problem.
```
There is Postgres table named 'accounts' with 2 columns: id and mac.
There is another table 'activities' with 3 columns: account_id, dt and type.
The column named 'type' can be 'SUCCESS' or 'ERROR'
The column 'dt' contains timestamp as a  string.
Please create a SQL which returns 
all sequences of 3 or more consecutive (by dt column)   'ERROR'  in type column ,
one sequence per row with mac, start dt, end dt
for each  mac value in accounts table.
Example: if for given mac value the sorted by dt type values are:
ERROR,ERROR, SUCCESS, ERROR 
then there are no 3 consecutive  ERRORs here, because of SUCCESS in between.

In code below CTE GroupStarts is important:
As long as the 'ERROR' events are consecutive (meaning no other activity types interrupt them), 
the difference between their overall rank (rn) and their rank within the 'ERROR' events (error_rn) 
will remain constant. 
When a non-'ERROR' event occurs, the error_rn sequence is broken, and the next 'ERROR' event will have a different group_id.
```

```sql

WITH activities(account_id, dt, type) AS (
    VALUES
        (1, '2024-01-01', 'ERROR'),
        (1, '2024-01-02', 'ERROR'),
        (1, '2024-01-03', 'SUCCESS'),
        (1, '2024-01-04', 'ERROR'),
        (2, '2024-01-01', 'ERROR'),
        (2, '2024-01-02', 'ERROR'),
        (2, '2024-01-03', 'ERROR'),
        (2, '2024-01-04', 'ERROR'),
  (1, '2024-01-06', 'ERROR'),
  (1, '2024-01-08', 'ERROR')
),
accounts (id , mac ) as (
   values
    (1, 50) ,
    (2, 20)
)
-- SELECT accounts.*, activities.* 
-- from activities join accounts on 
-- accounts.id = activities.account_id;
,   RankedActivities AS (
    SELECT
        a.mac,
        b.dt,
        b.type,
        ROW_NUMBER() OVER (PARTITION BY a.id ORDER BY b.dt) AS rn
    FROM       accounts a
    JOIN  activities b ON a.id = b.account_id
),
ErrorActivities AS (
    SELECT
        mac,
        dt,
        type,
        rn
    FROM  RankedActivities
    WHERE type = 'ERROR'
),
ConsecutiveErrorGroups AS (
    SELECT
        mac,
        dt,
        type,
        rn,
        ROW_NUMBER() OVER (PARTITION BY mac ORDER BY dt) AS error_rn
    FROM ErrorActivities
),
GroupStarts AS (
    SELECT
        mac,
        dt,
        type,
        rn,
        error_rn,
        rn - error_rn AS group_id
    FROM     ConsecutiveErrorGroups
),
ConsecutiveSequences AS (
    SELECT
        mac,
        MIN(dt) AS started_at,
        MAX(dt) AS ended_at,
        COUNT(*) AS activities
    FROM   GroupStarts
    GROUP BY      mac,  group_id
    HAVING   COUNT(*) >= 3
)
SELECT
    cs.mac,
    'ERROR' AS type,
    cs.started_at,
    cs.ended_at,
    cs.activities
FROM ConsecutiveSequences cs;
```
### Another solution for gaps and islands problem
```sql
WITH typed_rows AS (
    SELECT 
        a.mac,
        act.dt,
        act.type,
        ROW_NUMBER() OVER (PARTITION BY a.mac ORDER BY act.dt) AS rn_all,
        ROW_NUMBER() OVER (PARTITION BY a.mac, type ORDER BY act.dt) AS rn_type
    FROM activities act
    JOIN accounts a ON a.id = act.account_id
),
error_sequences AS (
    SELECT 
        mac,
        dt,
        rn_all - rn_type AS grp
    FROM typed_rows
    WHERE type = 'ERROR'
),
grouped_errors AS (
    SELECT 
        mac,
        MIN(dt) AS start_dt,
        MAX(dt) AS end_dt,
        COUNT(*) AS cnt
    FROM error_sequences
    GROUP BY mac, grp
    HAVING COUNT(*) >= 3
)
SELECT 
    mac,
    start_dt,
    end_dt
FROM grouped_errors
ORDER BY mac, start_dt;

```



### Interview question 2

```sql
WITH premiums AS (
  SELECT * FROM (VALUES
    ('Term Life',   100),
    ('Whole Life',  100),
    ('Health',      400),
    ('Endowment',   500)
  ) AS p(insurance_type, monthly_premium)
),
rates AS (
  SELECT * FROM (VALUES
    ('Term Life',   'Low',    0.10),
    ('Term Life',   'Medium', 0.085),
    ('Term Life',   'High',   0.07),
    ('Whole Life',  'Low',    0.10),
    ('Whole Life',  'Medium', 0.085),
    ('Whole Life',  'High',   0.07),
    ('Health',      'Low',    0.02),
    ('Health',      'Medium', 0.015),
    ('Health',      'High',   0.01),
    ('Endowment',   'Low',    0.15),
    ('Endowment',   'Medium', 0.12),
    ('Endowment',   'High',   0.10)
  ) AS r(insurance_type, risk, annual_rate)
)
SELECT
  u.user_id,
  u.insurance_type,
  u.risc AS risk,
  ROUND( (p.monthly_premium * 12) / r.annual_rate ) AS insured_amount
FROM users u
JOIN premiums p
  ON u.insurance_type = p.insurance_type
JOIN rates r
  ON u.insurance_type = r.insurance_type
 AND u.risc = r.risk
ORDER BY u.user_id;

```



### For each user, find the longest streak of consecutive days they logged in. 

Explanation :
```
min_login_date is used as a base date to find the delta with the login_date s for a user_id.
ROW_NUMBER() is used to get the ranks of each row for the user_id based on login_date in ascending order.
     diff= rn — date_int  
gives out the difference of the above two columns, which is static for consecutive login_dates.

Rest is simple logic where we get the COUNT(*) for each [user_id,diff] combination
ie. the streak_length and then get the max(streak_length) for each user_id.
```

```sql
WITH min_date AS (
  SELECT  MIN(login_date) AS min_login_date
  FROM user_logins
),
cte AS (
  SELECT
    ul.user_id,
    ul.login_date,
    DATEDIFF(ul.login_date, md.min_login_date) AS date_int,
    ROW_NUMBER() OVER (PARTITION BY ul.user_id ORDER BY ul.login_date) AS rn
  FROM  user_logins ul
    CROSS JOIN min_date md
),
cte2 AS (
  SELECT
    user_id,
    login_date,
    date_int,
    rn,
    rn - date_int AS diff
  FROM  cte
),
streaks AS (
  SELECT
    user_id,
    diff,
    COUNT(*) AS streak_length
  FROM  cte2
  GROUP BY user_id, iff
)
SELECT
  user_id,
  MAX(streak_length) AS longest_streak
FROM streaks
GROUP BY user_id
ORDER BY  user_id;
```


###  Monthly Percentage Difference.
```
Given a table of purchases by date, calculate the month-over-month percentage change in revenue.
The output should include the year-month date (YYYY-MM) and percentage change, rounded to the 2nd decimal point,
and sorted from the beginning of the year to the end of the year.
The percentage change column will be populated from the 2nd month forward and calculated as
((this month’s revenue — last month’s revenue) / last month’s revenue)*100.
```

```sql
select ym, round(((revenue-last_month_revenue)/last_month_revenue)*100,2) as 'month-over-month percentage'
from (
     select ym,revenue, lag(revenue) over(order by ym)  as last_month_revenue
     from (
        select date_format(created_at, '%Y-%m') as ym, sum(value) as revenue
        from sf_transactions 
        group by 1
     )
 a )
b
```


### Given table with 3 columns: emp_id, action, time  
action can be 'in' or 'out'
Qestion: find the emp_id who are inside 

Solution 1: 
Employees will be in hospital if latest in time is more than latest out time or latest out time is not known.

Solution 2: 
find each employees latest activity time then we will find at that time what was employees activity.

Solution 3:

generate the row number of each emp_id order by time in descending order.   
Then, we will create a CTE, and after that, we will extract that emp_id where 
ther row number will be =1 and the activity is ‘in’.

```sql
WITH x as (
SELECT *,ROW_NUMBER() OVER(PARTITION BY emp_id ORDER BY time DESC) AS rnk
FROM hospital
)
SELECT * FROM x
WHERE rnk=1 AND action='in';
```

## https://medium.com/@shaantanutripathi/google-advanced-sql-interview-question-walkthrough-7ed81b04ad17

Given a table employee_attendance that records the daily attendance status of employees 
(whether they are present or absent) over a period of time.  
Each record includes the employee_id, attendance_date, and status.

Write a query to calculate the streak of consecutive days each employee has been present,  
where a streak is defined as a series of consecutive days with “present” status.  
Return the maximum streak for each employee.

```sql
WITH Streaks AS (
    -- Step 1: Assign Row Numbers and Identify Streak Groups
    SELECT 
        employee_id, 
        attendance_date, 
        status,
        ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY attendance_date) AS row_num_by_date,
        ROW_NUMBER() OVER (PARTITION BY employee_id, status ORDER BY attendance_date) AS row_num_by_status,
        ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY attendance_date) - 
        ROW_NUMBER() OVER (PARTITION BY employee_id, status ORDER BY attendance_date) AS streak_group
    FROM employee_attendance
    WHERE status = 'present'
),
Grouped_Streaks AS (
    -- Step 2: Group by Streak Group and Count the Number of Consecutive "present" Days
    SELECT 
        employee_id, 
        streak_group, 
        COUNT(*) AS streak_count
    FROM Streaks
    GROUP BY employee_id, streak_group
),
Max_Streaks AS (
    -- Step 3: Find the Maximum Streak for Each Employee
    SELECT 
        employee_id, 
        MAX(streak_count) AS max_streak
    FROM Grouped_Streaks
    GROUP BY employee_id
)
SELECT * FROM Max_Streaks;
```

## Top 100 advanced SQL questions and answers 

### 1. How to retrieve the second-highest salary of an employee?

SELECT MAX(salary)  
FROM employees  
WHERE salary < (SELECT MAX(salary) FROM employees);

### 2. How to get the nth highest salary in ?

SELECT salary
FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rank
 FROM employees) AS ranked_salaries
WHERE rank = N;

### 3. How do you fetch all employees whose salary is greater than the average salary?

SELECT *  
FROM employees  
WHERE salary > (SELECT AVG(salary) FROM employees);

### 4. Write a query to display the current date and time in .

SELECT CURRENT_TIMESTAMP;

### 5. How to find duplicate records in a table?

SELECT column_name, COUNT(*)
FROM table_name
GROUP BY column_name
HAVING COUNT(*) > 1;

### 6. How can you delete duplicate rows in ?

WITH CTE AS (
 SELECT column_name,
 ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY
column_name) AS row_num
 FROM table_name
)
DELETE FROM CTE WHERE row_num > 1;

### 7. How to get the common records from two tables?

SELECT *
FROM table1
INTERSECT
SELECT *
FROM table2;

### 8. How to retrieve the last 10 records from a table?
 
SELECT *
FROM employees
ORDER BY employee_id DESC
LIMIT 10;

### 9. How do you fetch the top 5 employees with the highest salaries?

SELECT *
FROM employees
ORDER BY salary DESC
LIMIT 5;

### 10. How to calculate the total salary of all employees?

SELECT SUM(salary)
FROM employees;

### 11. How to write a query to find all employees who joined in the year 2020?

SELECT *
FROM employees
WHERE YEAR(join_date) = 2020;

### 12. Write a query to find employees whose name starts with 'A'.

SELECT * 
FROM employees
WHERE name LIKE 'A%';

### 13. How can you find the employees who do not have a manager?

SELECT *
FROM employees
WHERE manager_id IS NULL;

### 14. How to find the department with the highest number of employees?

SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id
ORDER BY COUNT(*) DESC
LIMIT 1;

### 15. How to get the count of employees in each department?

SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;

### 16. Write a query to fetch employees having the highest salary in each department.

SELECT department_id, employee_id, salary 
FROM employees AS e
WHERE salary = (SELECT MAX(salary)
 FROM employees
 WHERE department_id = e.department_id);
 
### 17. How to write a query to update the salary of all employees by 10%?

UPDATE employees
SET salary = salary * 1.1;

### 18. How can you find employees whose salary is between 50,000 and1,00,000?

SELECT *
FROM employees
WHERE salary BETWEEN 50000 AND 100000;

### 19. How to find the youngest employee in the organization?

SELECT *
FROM employees
ORDER BY birth_date DESC
LIMIT 1;

### 20. How to fetch the first and last record from a table?

(SELECT * FROM employees ORDER BY employee_id ASC LIMIT 1)
UNION ALL
(SELECT * FROM employees ORDER BY employee_id DESC LIMIT 1);

### 21. Write a query to find all employees who report to a specific manager.

SELECT *
FROM employees
WHERE manager_id = ?;

### 22. How can you find the total number of departments in the company?

SELECT COUNT(DISTINCT department_id)
FROM employees;

### 23. How to find the department with the lowest average salary?

SELECT department_id, AVG(salary)
FROM employees
GROUP BY department_id
ORDER BY AVG(salary) ASC
LIMIT 1;

### 24. How to delete all employees from a department in one query?

DELETE FROM employees
WHERE department_id = ?;

### 25. How to display all employees who have been in the company for more
than 5 years?

SELECT *
FROM employees
WHERE DATEDIFF(CURDATE(), join_date) > 1825;

### 26. How to find the second-largest value from a table?

SELECT MAX(column_name)
FROM table_name
WHERE column_name < (SELECT MAX(column_name) FROM table_name);

### 27. How to write a query to remove all records from a table but keep the
table structure?

TRUNCATE TABLE table_name;

### 28. Write a query to get all employee records in XML format.

SELECT employee_id, name, department_id
FROM employees
FOR XML AUTO;
29. How to get the current month’s name from ?
 
SELECT MONTHNAME(CURDATE());

### 30. How to convert a string to lowercase in ?

SELECT LOWER('STRING_VALUE');

### 31. How to find all employees who do not have any subordinates?

SELECT *
FROM employees
WHERE employee_id NOT IN (SELECT manager_id FROM employees WHERE
manager_id IS NOT NULL);

### 32. Write a query to calculate the total sales per customer in a sales table.

SELECT customer_id, SUM(sales_amount)
FROM sales
GROUP BY customer_id;

### 33. How to write a query to check if a table is empty?

SELECT CASE
 WHEN EXISTS (SELECT 1 FROM table_name)
 THEN 'Not Empty'
 ELSE 'Empty'
END;

### 34. How to find the second highest salary for each department?

SELECT department_id, salary
FROM (SELECT department_id, salary,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_salaries
WHERE rank = 2;

### 35. Write a query to fetch employees whose salary is a multiple of 10,000.

SELECT *
FROM employees
WHERE salary % 10000 = 0;

### 36. How to fetch records where a column has null values?

SELECT *
FROM employees
WHERE column_name IS NULL;

### 37. How to write a query to find the total number of employees in each job title?

SELECT job_title, COUNT(*)
FROM employees
GROUP BY job_title;

### 38. Write a query to fetch all employees whose names end with ‘n’.

SELECT *
FROM employees
WHERE name LIKE '%n';

### 39. How to find all employees who work in both departments 101 and 102?

SELECT employee_id
FROM employees
WHERE department_id IN (101, 102)
GROUP BY employee_id
HAVING COUNT(DISTINCT department_id) = 2;

### 40. Write a query to fetch the details of employees with the same salary.

SELECT *
FROM employees
WHERE salary IN (SELECT salary
 FROM employees
 GROUP BY salary
 HAVING COUNT(*) > 1);
 
### 41. How to update salaries of employees based on their department?
 
UPDATE employees
SET salary = CASE
 WHEN department_id = 101 THEN salary * 1.10
 WHEN department_id = 102 THEN salary * 1.05
 ELSE salary
END;

### 42. How to write a query to list all employees without a department?

SELECT *
FROM employees
WHERE department_id IS NULL;

### 43. Write a query to find the maximum salary and minimum salary in each
department.

SELECT department_id, MAX(salary), MIN(salary)
FROM employees
GROUP BY department_id;

### 44. How to list all employees hired in the last 6 months?

SELECT *
FROM employees
WHERE hire_date > ADDDATE(CURDATE(), INTERVAL -6 MONTH);

### 45. Write a query to display department-wise total and average salary.
 
SELECT department_id, SUM(salary) AS total_salary, AVG(salary) AS avg_salary
FROM employees
GROUP BY department_id;

### 46. How to find employees who joined the company in the same month and year as their manager?

SELECT e.employee_id, e.name
FROM employees e
JOIN employees m ON e.manager_id = m.employee_id
WHERE MONTH(e.join_date) = MONTH(m.join_date)
 AND YEAR(e.join_date) = YEAR(m.join_date);

### 47. Write a query to count the number of employees whose names start and
end with the same letter.

SELECT COUNT(*)
FROM employees
WHERE LEFT(name, 1) = RIGHT(name, 1);

### 48. How to retrieve employee names and salaries in a single string?

SELECT CONCAT(name, ' earns ', salary) AS employee_info
FROM employees;

### 49. How to find employees whose salary is higher than their manager's salary?

SELECT e.employee_id, e.name
FROM employees e
JOIN employees m ON e.manager_id = m.employee_id
WHERE e.salary > m.salary;

### 50. Write a query to get employees who belong to departments with less than 3 employees.

SELECT *
FROM employees
WHERE department_id IN (SELECT department_id
 FROM employees
 GROUP BY department_id
 HAVING COUNT(*) < 3);
 
### 51. How to write a query to find employees with the same first name?

SELECT *
FROM employees
WHERE first_name IN (SELECT first_name
 FROM employees
 GROUP BY first_name
 HAVING COUNT(*) > 1);
 
### 52. How to write a query to delete employees who have been in the company
for more than 15 years?

DELETE FROM employees
WHERE DATEDIFF(CURDATE(), join_date) > 5475;

### 53. Write a query to list all employees working under the same manager.

SELECT *
FROM employees
WHERE manager_id = ?;

### 54. How to find the top 3 highest-paid employees in each department?

```sql
SELECT *
FROM (SELECT *,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_employees
WHERE rank <= 3;
```
### 55. Write a query to list all employees with more than 5 years of experience in each department.
```
SELECT *
FROM employees
WHERE DATEDIFF(CURDATE(), join_date) > 1825;
```
### 56. How to list all employees in departments that have not hired anyone in the past 2 years?
```
SELECT *
FROM employees
WHERE department_id IN (SELECT department_id
 FROM employees
 GROUP BY department_id
 HAVING MAX(hire_date) < ADDDATE(CURDATE(), INTERVAL -2 YEAR));
```
### 57. Write a query to find all employees who earn more than the average salary of their department.

SELECT *
FROM employees e
WHERE salary > (SELECT AVG(salary)
 FROM employees
 WHERE department_id = e.department_id);

### 58. How to list all managers who have more than 5 subordinates?
```sql
SELECT *
FROM employees
WHERE employee_id IN (SELECT manager_id
 FROM employees 
 GROUP BY manager_id
 HAVING COUNT(*) > 5);
```
### 59. Write a query to display employee names and hire dates in the format "Name - MM/DD/YYYY".
```sql
SELECT CONCAT(name, ' - ', DATE_FORMAT(hire_date, '%m/%d/%Y')) AS
employee_info
FROM employees;
```
### 60. How to find employees whose salary is in the top 10%?
```sql
SELECT *
FROM employees
WHERE salary >= (SELECT PERCENTILE_CONT(0.9)
 WITHIN GROUP (ORDER BY salary ASC)
 FROM employees);
```
### 61. Write a query to display employees grouped by their age brackets (e.g.,20-30, 31-40, etc.).
```sql
SELECT CASE
 WHEN age BETWEEN 20 AND 30 THEN '20-30'
 WHEN age BETWEEN 31 AND 40 THEN '31-40'
 ELSE '41+'
 END AS age_bracket,
 COUNT(*) 
FROM employees
GROUP BY age_bracket;
```
### 62. How to find the average salary of the top 5 highest-paid employees in each department?
```sql
SELECT department_id, AVG(salary)
FROM (SELECT department_id, salary,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_employees
WHERE rank <= 5
GROUP BY department_id;
```
### 63. How to calculate the percentage of employees in each department?
```sql
SELECT department_id,
 (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM employees)) AS percentage
FROM employees
GROUP BY department_id;
```
### 64. Write a query to find all employees whose email contains the domain '@example.com'.

SELECT *
FROM employees
WHERE email LIKE '%@example.com';

### 65. How to retrieve the year-to-date sales for each customer?
```
SELECT customer_id, SUM(sales_amount)
FROM sales
WHERE sale_date BETWEEN '2024-01-01' AND CURDATE()
GROUP BY customer_id;
```
## 66. Write a query to display the hire date and day of the week for each employee.

SELECT name, hire_date, DAYNAME(hire_date) AS day_of_week
FROM employees;

### 67. How to find all employees who are older than 30 years?

SELECT *
FROM employees
WHERE DATEDIFF(CURDATE(), birth_date) / 365 > 30;

### 68. Write a query to display employees grouped by their salary range (e.g., 0-20K, 20K-50K).
```sql
SELECT CASE
 WHEN salary BETWEEN 0 AND 20000 THEN '0-20K'
 WHEN salary BETWEEN 20001 AND 50000 THEN '20K-50K'
 ELSE '50K+' 
 END AS salary_range,
 COUNT(*)
FROM employees
GROUP BY salary_range;
```
### 69. How to list all employees who do not have a bonus?
```
SELECT *
FROM employees
WHERE bonus IS NULL;
```
### 70. Write a query to display the highest, lowest, and average salary for each job role.
```
SELECT job_role, MAX(salary) AS highest_salary, MIN(salary) AS lowest_salary,
AVG(salary) AS avg_salary
FROM employees
GROUP BY job_role;
```
