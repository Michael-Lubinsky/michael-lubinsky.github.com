## max_by

https://blog.devgenius.io/improving-spark-jobs-runtime-b128f0c29d44

How max_by Works Under the Hood
max_by(col, ord) — Returns the value from the col parameter that is associated with the maximum value from the ord parameter. The first parameter is the column name that needs to be displayed as output, and the second parameter is the column on which we check the max condition.
```
df.groupby("course").agg(max_by("year", "earnings")).show()
# SELECT max_by(x, y) FROM VALUES ('a', 10), ('b', 50), ('c', 20) AS tab(x, y);
```
Instead of collecting and sorting all rows in each partition, max_by uses an incremental aggregation approach:

For each partition, maintain only two values:

valueWithExtremumOrdering: The current "best" record
extremumOrdering: The current maximum ordering value
For each new row, do a simple comparison:

If new_ordering > current_max_ordering, update both values
Otherwise, keep the current values
No sorting required: Just O(1) comparisons per row instead of O(n log n) sorting

This means:

Memory usage: O(1) per partition instead of O(n)  
CPU complexity: O(n) instead of O(n log n)  
Less disk spilling: The intermediate state fits more easily in memory  
So the query was rewritten to leverage the MAX_BY function:  

```sql
SELECT 
  col1, col2, col3, col4,
  MAX_BY(
    STRUCT(...),
    STRUCT(col5, col6, col7)
  )
FROM table1 t1 
INNER JOIN table2 t2 ON (...)
GROUP BY col1, col2, col3, col
```
 


### Spark 4.0
https://habr.com/ru/companies/korus_consulting/articles/920766/

https://sabarevictor.medium.com/stop-learning-pandas-the-spark-4-0-features-nobodys-telling-you-about-8651b0206ee5

https://medium.com/@goyalarchana17/whats-next-for-apache-spark-4-0-a-comprehensive-overview-with-comparisons-to-spark-3-x-c2c1ba78aa5b?sk=81039bff1aadd3a8e65507a43f21ec12

https://medium.com/towards-data-engineering/how-to-migrate-to-apache-spark-4-0-in-10-steps-a-complete-guide-b25aff9454a7 

https://medium.com/towards-data-engineering/meet-variant-apache-spark-4-0s-secret-weapon-for-semi-structured-data-c087e164c241 
