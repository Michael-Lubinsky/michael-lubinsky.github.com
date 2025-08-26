### SQLite
<https://sqlitebrowser.org/> <https://sqlitestudio.pl/> <https://menial.co.uk/base/>

<https://docs.python.org/3/library/sqlite3.html>

#### Reading records by the column name (Python)
Dictionary-like Object: sqlite3.Row allows both index-based and name-based access to columns.
```python
import sqlite3
conn = sqlite3.connect("your_database.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT id, name, age FROM your_table")
records = cursor.fetchall()
for record in records:
    print(f"ID: {record['id']}, Name: {record['name']}, Age: {record['age']}")
conn.close()
```

### This script extracts data from a CSV file, transforms it, and loads it into a SQLite database.

```python
import csv
import sqlite3
import logging
from functools import wraps

# Decorator for error handling
def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

@error_handler
def extract(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    return data

@error_handler
def transform(data):
    for row in data:
        row['age'] = int(row['age'])
    return data

@error_handler
def load(data, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    ''')
    for row in data:
        cursor.execute('''
            INSERT INTO users (id, name, age) VALUES (?, ?, ?)
        ''', (row['id'], row['name'], row['age']))
    conn.commit()
    conn.close()

def main():
    data = extract('sample.csv')
    transformed_data = transform(data)
    load(transformed_data, 'database.db')

if __name__ == "__main__":
    main()
```

### CTE as lookup table

```sql
WITH countries (code, name) AS (
     SELECT * FROM (VALUES
    ('us', 'United States'), ('fr', 'France'), ('in', 'India')
    ) AS codes
)
SELECT data.code, name FROM data LEFT JOIN countries ON countries.code = data.code;
```

#### Virtual tables

SQLite’s virtual tables let you expose external data sources as if they were normal tables.



#### 1. General PRAGMA Commands
   PRAGMA statements can be executed like SQL commands
```
1.1. PRAGMA database_list
Lists all attached databases and their file paths.
PRAGMA database_list;

1.2. PRAGMA schema_version
Returns the schema version of the database.
PRAGMA schema_version;

1.3. PRAGMA user_version
Used to store an application-defined version number for the database schema.

-- Set the version
PRAGMA user_version = 1;

-- Retrieve the version
PRAGMA user_version;
```
#### 2. Optimization and Performance
```
2.1. PRAGMA cache_size
Sets or queries the number of database pages SQLite will keep in memory.

-- Set cache size to 2000 pages
PRAGMA cache_size = 2000;
-- Query current cache size
PRAGMA cache_size;

2.2. PRAGMA synchronous
Controls how often SQLite writes changes to disk, balancing performance and durability.

Modes:

OFF: Fast but risks data loss in case of a crash.

NORMAL: Default mode; writes are flushed at key points.

FULL: Ensures all changes are fully written to disk, safest but slower.
-- Set synchronous mode to NORMAL
PRAGMA synchronous = NORMAL;

2.3. PRAGMA temp_store

Specifies where temporary tables and indices are stored.
Options: DEFAULT, FILE, MEMORY

-- Store temporary tables in memory
PRAGMA temp_store = MEMORY;
```
#### 3. Foreign Key Constraints
```
3.1. PRAGMA foreign_keys
Enables or disables foreign key constraints.
Default is OFF, so it must be explicitly enabled.

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Check if foreign keys are enabled
PRAGMA foreign_keys;
```
#### 4. Security
```
4.1. PRAGMA case_sensitive_like
Controls whether the LIKE operator is case-sensitive.

Default is OFF (case-insensitive).
-- Make LIKE case-sensitive
PRAGMA case_sensitive_like = ON;

4.2. PRAGMA cipher (for encrypted databases)
If you use an encryption extension (like SQLCipher),
this is used to configure encryption settings.

-- Set database encryption key (if supported)
PRAGMA key = 'my_secret_key';
```
#### 5. Database Integrity and Maintenance
```
5.1. PRAGMA integrity_check
Runs a consistency check on the database to detect corruption.

PRAGMA integrity_check;
5.2. PRAGMA quick_check
A faster, less thorough integrity check.

PRAGMA quick_check;

5.3. PRAGMA wal_checkpoint
For databases using Write-Ahead Logging (WAL),
this command runs a checkpoint to write WAL data back to the main database.

PRAGMA wal_checkpoint;

5.4. PRAGMA optimize
Optimizes the database by updating query plans and rebuilding indices.
 PRAGMA optimize;
```

#### 6. Write-Ahead Logging (WAL)
```
6.1. PRAGMA journal_mode
Controls the journaling mode for transactions.
Options: DELETE, TRUNCATE, PERSIST, MEMORY, WAL, OFF
Write-Ahead Logging (WAL): Improves concurrency and performance.

-- Set journal mode to WAL
PRAGMA journal_mode = WAL;
-- Check current journal mode
PRAGMA journal_mode;

6.2. PRAGMA wal_autocheckpoint
Sets the number of pages before an automatic checkpoint occurs in WAL mode.

-- Set checkpoint to occur every 1000 pages
PRAGMA wal_autocheckpoint = 1000;
```
#### 7. Miscellaneous
```
7.1. PRAGMA encoding
Specifies the text encoding for the database.
Common values: UTF-8, UTF-16

PRAGMA encoding = "UTF-8";

7.2. PRAGMA page_size
Returns or sets the size of a single page in bytes. Impacts database performance.

-- Set page size to 4096 bytes
PRAGMA page_size = 4096;

-- Get current page size
PRAGMA page_size;

7.3. PRAGMA locking_mode
Controls how the database locking mechanism operates.

Modes: NORMAL, EXCLUSIVE

PRAGMA locking_mode = EXCLUSIVE;
```
#### Using PRAGMA in Python
You can execute PRAGMA commands in Python using sqlite3 like this:

```python
import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("example.db")
cursor = conn.cursor()

# Enable foreign key constraints
cursor.execute("PRAGMA foreign_keys = ON;")

# Set cache size
cursor.execute("PRAGMA cache_size = 1000;")

# Query PRAGMA settings
cursor.execute("PRAGMA journal_mode;")
print(cursor.fetchone())

# Close the connection
conn.close()
```

#### Upload parquet file to SQLite

```python
import pandas as pd 
import sqlite3

parquet_path = 'my-data.parquet'
db_conn = sqlite3.connect(database='/tmp/my.db')

df_parquet = pd.read_parquet(parquet_path)
table_name = 'my_data_table'
num_rows_inserted = df_parquet.to_sql(table_name, db_conn, if_exists="replace", index=False)

query = f"SELECT * from {table_name}"
cursor = db_conn.execute(query)
db_conn.close()
```

#### Run SQL query against CSV file using SQLite

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

<https://antonz.org/install-sqlite-extension/> sqlite extensions

<https://sqlpkg.org/>  sqlite extensions

<https://github.com/tursodatabase/libsql>

<https://habr.com/ru/companies/ruvds/articles/924338/>
