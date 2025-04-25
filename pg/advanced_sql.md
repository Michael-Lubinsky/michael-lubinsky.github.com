### Given table with 3 columns: emp_id, action, time  
action can be 'in' or 'out'
Qeestion: find the emp_id who are inside 

Solution 1: Employees will be in hospital if latest in time is more than latest out time or latest out time is not known.

Solution 2: find each employees latest activity time then we will find at that time what was employees activity.

Solution 3:

generate the row number of each emp_id order by time in descending order.   
Then, we will create a CTE, and after that, we will extract that emp_id where the row number will be =1 and the activity is ‘in’.
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

Write a query to calculate the streak of consecutive days each employee has been present, where a streak is defined as a series of consecutive days with “present” status. Return the maximum streak for each employee.

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

### 3. How do you fetch all employees whose salary is greater than the average
salary?

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
6. How can you delete duplicate rows in ?

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
10. How to calculate the total salary of all employees?

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
26. How to find the second-largest value from a table?

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
30. How to convert a string to lowercase in ?

SELECT LOWER('STRING_VALUE');
31. How to find all employees who do not have any subordinates?

SELECT *
FROM employees
WHERE employee_id NOT IN (SELECT manager_id FROM employees WHERE
manager_id IS NOT NULL);
32. Write a query to calculate the total sales per customer in a sales table.

SELECT customer_id, SUM(sales_amount)
FROM sales
GROUP BY customer_id;
33. How to write a query to check if a table is empty?

SELECT CASE
 WHEN EXISTS (SELECT 1 FROM table_name)
 THEN 'Not Empty'
 ELSE 'Empty'
END;
34. How to find the second highest salary for each department?

SELECT department_id, salary
FROM (SELECT department_id, salary,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_salaries
WHERE rank = 2;
35. Write a query to fetch employees whose salary is a multiple of 10,000.

SELECT *
FROM employees
WHERE salary % 10000 = 0;
36. How to fetch records where a column has null values?

SELECT *
FROM employees
WHERE column_name IS NULL;
37. How to write a query to find the total number of employees in each job
title?

SELECT job_title, COUNT(*)
FROM employees
GROUP BY job_title;
38. Write a query to fetch all employees whose names end with ‘n’.

SELECT *
FROM employees
WHERE name LIKE '%n';
39. How to find all employees who work in both departments 101 and 102?

SELECT employee_id
FROM employees
WHERE department_id IN (101, 102)
GROUP BY employee_id
HAVING COUNT(DISTINCT department_id) = 2;
40. Write a query to fetch the details of employees with the same salary.

SELECT *
FROM employees
WHERE salary IN (SELECT salary
 FROM employees
 GROUP BY salary
 HAVING COUNT(*) > 1);
41. How to update salaries of employees based on their department?
 
UPDATE employees
SET salary = CASE
 WHEN department_id = 101 THEN salary * 1.10
 WHEN department_id = 102 THEN salary * 1.05
 ELSE salary
END;
42. How to write a query to list all employees without a department?

SELECT *
FROM employees
WHERE department_id IS NULL;
43. Write a query to find the maximum salary and minimum salary in each
department.

SELECT department_id, MAX(salary), MIN(salary)
FROM employees
GROUP BY department_id;
44. How to list all employees hired in the last 6 months?

SELECT *
FROM employees
WHERE hire_date > ADDDATE(CURDATE(), INTERVAL -6 MONTH);
45. Write a query to display department-wise total and average salary.
 
SELECT department_id, SUM(salary) AS total_salary, AVG(salary) AS avg_salary
FROM employees
GROUP BY department_id;
46. How to find employees who joined the company in the same month and
year as their manager?

SELECT e.employee_id, e.name
FROM employees e
JOIN employees m ON e.manager_id = m.employee_id
WHERE MONTH(e.join_date) = MONTH(m.join_date)
 AND YEAR(e.join_date) = YEAR(m.join_date);
47. Write a query to count the number of employees whose names start and
end with the same letter.

SELECT COUNT(*)
FROM employees
WHERE LEFT(name, 1) = RIGHT(name, 1);
48. How to retrieve employee names and salaries in a single string?

SELECT CONCAT(name, ' earns ', salary) AS employee_info
FROM employees;
49. How to find employees whose salary is higher than their manager's
salary?

SELECT e.employee_id, e.name
FROM employees e
JOIN employees m ON e.manager_id = m.employee_id
WHERE e.salary > m.salary;
50. Write a query to get employees who belong to departments with less
than 3 employees.

SELECT *
FROM employees
WHERE department_id IN (SELECT department_id
 FROM employees
 GROUP BY department_id
 HAVING COUNT(*) < 3);
51. How to write a query to find employees with the same first name?

SELECT *
FROM employees
WHERE first_name IN (SELECT first_name
 FROM employees
 GROUP BY first_name
 HAVING COUNT(*) > 1);
52. How to write a query to delete employees who have been in the company
for more than 15 years?

DELETE FROM employees
WHERE DATEDIFF(CURDATE(), join_date) > 5475;
53. Write a query to list all employees working under the same manager.

SELECT *
FROM employees
WHERE manager_id = ?;
54. How to find the top 3 highest-paid employees in each department?

SELECT *
FROM (SELECT *,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_employees
WHERE rank <= 3;
55. Write a query to list all employees with more than 5 years of experience
in each department.

SELECT *
FROM employees
WHERE DATEDIFF(CURDATE(), join_date) > 1825;
56. How to list all employees in departments that have not hired anyone in
the past 2 years?

SELECT *
FROM employees
WHERE department_id IN (SELECT department_id
 FROM employees
 GROUP BY department_id
 HAVING MAX(hire_date) < ADDDATE(CURDATE(), INTERVAL -2
YEAR));

### 57. Write a query to find all employees who earn more than the average salary of their department.

SELECT *
FROM employees e
WHERE salary > (SELECT AVG(salary)
 FROM employees
 WHERE department_id = e.department_id);

### 58. How to list all managers who have more than 5 subordinates?

SELECT *
FROM employees
WHERE employee_id IN (SELECT manager_id
 FROM employees 
 GROUP BY manager_id
 HAVING COUNT(*) > 5);

### 59. Write a query to display employee names and hire dates in the format
"Name - MM/DD/YYYY".

SELECT CONCAT(name, ' - ', DATE_FORMAT(hire_date, '%m/%d/%Y')) AS
employee_info
FROM employees;

### 60. How to find employees whose salary is in the top 10%?

SELECT *
FROM employees
WHERE salary >= (SELECT PERCENTILE_CONT(0.9)
 WITHIN GROUP (ORDER BY salary ASC)
 FROM employees);

### 61. Write a query to display employees grouped by their age brackets (e.g.,20-30, 31-40, etc.).

SELECT CASE
 WHEN age BETWEEN 20 AND 30 THEN '20-30'
 WHEN age BETWEEN 31 AND 40 THEN '31-40'
 ELSE '41+'
 END AS age_bracket,
 COUNT(*) 
FROM employees
GROUP BY age_bracket;

### 62. How to find the average salary of the top 5 highest-paid employees in
each department?

SELECT department_id, AVG(salary)
FROM (SELECT department_id, salary,
 DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary
DESC) AS rank
 FROM employees) AS ranked_employees
WHERE rank <= 5
GROUP BY department_id;

### 63. How to calculate the percentage of employees in each department?

SELECT department_id,
 (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM employees)) AS percentage
FROM employees
GROUP BY department_id;

### 64. Write a query to find all employees whose email contains the domain
'@example.com'.

SELECT *
FROM employees
WHERE email LIKE '%@example.com';

### 65. How to retrieve the year-to-date sales for each customer?

SELECT customer_id, SUM(sales_amount)
FROM sales
WHERE sale_date BETWEEN '2024-01-01' AND CURDATE()
GROUP BY customer_id;

## 66. Write a query to display the hire date and day of the week for each
employee.

SELECT name, hire_date, DAYNAME(hire_date) AS day_of_week
FROM employees;

### 67. How to find all employees who are older than 30 years?

SELECT *
FROM employees
WHERE DATEDIFF(CURDATE(), birth_date) / 365 > 30;

### 68. Write a query to display employees grouped by their salary range (e.g., 0-
20K, 20K-50K).

SELECT CASE
 WHEN salary BETWEEN 0 AND 20000 THEN '0-20K'
 WHEN salary BETWEEN 20001 AND 50000 THEN '20K-50K'
 ELSE '50K+' 
 END AS salary_range,
 COUNT(*)
FROM employees
GROUP BY salary_range;

### 69. How to list all employees who do not have a bonus?

SELECT *
FROM employees
WHERE bonus IS NULL;

### 70. Write a query to display the highest, lowest, and average salary for each job role.
SELECT job_role, MAX(salary) AS highest_salary, MIN(salary) AS lowest_salary,
AVG(salary) AS avg_salary
FROM employees
GROUP BY job_role;
