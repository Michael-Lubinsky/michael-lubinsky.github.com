### SQLite
PRAGMA synchronous=FULL

#### How to run a SQL query  against a CSV file using the sqlite3

```sql
sqlite3 :memory: -cmd '.import -csv taxi.csv taxi' \
  'SELECT passenger_count, COUNT(*), AVG(total_amount) FROM taxi GROUP BY passenger_count'
```

Add -cmd '.mode column' to output in columns instead:
```sql
 sqlite3 :memory: -cmd '.mode csv' -cmd '.import taxi.csv taxi' -cmd '.mode column' \
    'SELECT passenger_count, COUNT(*), AVG(total_amount) FROM taxi GROUP BY passenger_count'
```
