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

Or use -cmd '.mode markdown' to get a Markdown table.

A full list of output modes can be seen like this:
```
% sqlite3 -cmd '.help mode'
.mode MODE ?TABLE?       Set output mode
   MODE is one of:
     ascii     Columns/rows delimited by 0x1F and 0x1E
     box       Tables using unicode box-drawing characters
     csv       Comma-separated values
     column    Output in columns.  (See .width)
     html      HTML <table> code
     insert    SQL insert statements for TABLE
     json      Results in a JSON array
     line      One value per line
     list      Values delimited by "|"
     markdown  Markdown table format
     quote     Escape answers as for SQL
     table     ASCII-art table
     tabs      Tab-separated values
     tcl       TCL list elements
```
<https://til.simonwillison.net/sqlite/one-line-csv-operations>
