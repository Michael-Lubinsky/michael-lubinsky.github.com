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
### GREATEST and LEAST
```sql
SELECT
GREATEST(5, 18, 21, 3, 65) AS GREATEST_CHECK,
LEAST(5, 18, 21, 3, 65) AS LEAST_CHECK;
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
    (PARTITION BY platform ORDER BY year_of_release RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
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

<https://medium.com/@mariusz_kujawski/advanced-sql-for-data-professionals-875ab725730c>

<https://medium.com/@esrasoylu/advanced-sql-techniques-7016163019eb>
