### SQLite
<https://sqlitebrowser.org/> <https://sqlitestudio.pl/> <https://menial.co.uk/base/>  
<https://visualdb.com/sqlite/>   <https://github.com/Maxteabag/sqlit>

###	Prefer strict tables in SQLite
<https://evanhahn.com/prefer-strict-tables-in-sqlite/>
<https://news.ycombinator.com/item?id=48873940>

<https://jvns.ca/blog/2026/07/17/learning-about-running-sqlite/>

<https://sqlite-utils.datasette.io/en/latest/>
sqlite-utils is   Python library and CLI tool for working with SQLite databases.
It provides an extensive set of higher-level operations on top of Python’s default sqlite3 package, including support for complex table transformations, automatic table creation from JSON data and a whole lot more.

<https://answerdotai.github.io/apswutils/> another Python Lib for working with SQLite

**APSW** stands for **Another Python SQLite Wrapper**. It is a Python library by Roger Binns that provides an extremely thin wrapper around the **native SQLite C API**. Rather than hiding SQLite behind the standard Python DB-API abstraction, APSW exposes almost all of SQLite's functionality directly to Python. ([GitHub][1])

## Why does APSW exist?

Python already ships with the built-in `sqlite3` module:

```python
import sqlite3
```

However, `sqlite3` was designed to conform to the generic **DB-API 2.0** specification, making it look similar to drivers for PostgreSQL, MySQL, Oracle, etc.

APSW takes a different approach:

> "SQLite is unique, so Python should expose SQLite as it really is."

It maps the SQLite C API almost one-to-one into Python. ([Debian Packages][2])

---

## What does APSW provide?

Besides basic SQL execution, APSW exposes advanced SQLite features that are unavailable or limited in `sqlite3`:

| Feature               | sqlite3                   | APSW                     |
| --------------------- | ------------------------- | ------------------------ |
| Latest SQLite release | Sometimes behind          | ✅ Usually current        |
| Virtual Tables        | Limited                   | ✅ Full support           |
| FTS5                  | Partial                   | ✅ Full                   |
| JSON functions        | Depends on bundled SQLite | ✅ Current SQLite support |
| Session extension     | ❌                         | ✅                        |
| Backup API            | Limited                   | ✅                        |
| Blob streaming        | Basic                     | ✅ Full                   |
| Authorizer callbacks  | ❌                         | ✅                        |
| Progress handlers     | Limited                   | ✅                        |
| Update hooks          | ❌                         | ✅                        |
| Commit/Rollback hooks | ❌                         | ✅                        |
| Custom VFS            | ❌                         | ✅                        |
| Tracing               | Basic                     | ✅ Extensive              |

([Roger Binns][3])

---

## Example

Using `sqlite3`:

```python
import sqlite3

conn = sqlite3.connect("test.db")
conn.execute("CREATE TABLE people(name)")
conn.execute("INSERT INTO people VALUES(?)", ("Alice",))
conn.commit()
```

Using APSW:

```python
import apsw

conn = apsw.Connection("test.db")

conn.execute("CREATE TABLE IF NOT EXISTS people(name)")
conn.execute("INSERT INTO people VALUES(?)", ("Alice",))
```

Notice there is no `commit()` by default. APSW follows SQLite's own transaction semantics more closely rather than hiding them behind the DB-API interface. ([Roger Binns][3])

---

## Philosophy

The APSW project describes itself as a way to:

* expose the **complete SQLite C API**
* stay synchronized with new SQLite releases
* avoid unnecessary abstraction
* provide a better developer experience for SQLite-specific applications ([GitHub][1])

---

## When should you use APSW?

Use APSW if you're:

* building an application where SQLite is the primary database
* using modern SQLite features (FTS5, JSON, virtual tables, sessions)
* writing custom SQL functions, collations, or virtual tables
* interested in SQLite internals and performance
* developing tools like Datasette or SQLite extensions

Use the built-in `sqlite3` if you're:

* writing portable code that may switch databases later
* following tutorials or ORMs that expect DB-API
* performing straightforward CRUD operations

---

## Given your interests

From our previous discussions, you've been exploring advanced SQL features, ETL pipelines, and modern SQLite utilities. APSW is a strong fit because it gives you access to nearly everything SQLite can do, including:

* custom SQL functions and aggregates (similar to UDFs in other databases),
* virtual tables,
* FTS5 full-text search,
* JSON capabilities,
* tracing and profiling,
* incremental BLOB I/O,
* and extensions such as Sessions and CARRAY.

Those capabilities are particularly valuable if you're treating SQLite as an embedded analytical database rather than just a lightweight file-based store.

[1]: https://github.com/rogerbinns/apsw?utm_source=chatgpt.com "rogerbinns/apsw: Another Python SQLite wrapper"
[2]: https://packages.debian.org/sid/python-apsw-doc?utm_source=chatgpt.com "Details of package python-apsw-doc in sid"
[3]: https://rogerbinns.github.io/apsw/index.html?utm_source=chatgpt.com "APSW 3.53.2.0 documentation"



Although the names are similar, these libraries have different goals and different foundations.

| Feature                  | `sqlite-utils`                      | `apswutils`                            |
| ------------------------ | ----------------------------------- | -------------------------------------- |
| SQLite driver            | Python's built-in `sqlite3`         | APSW (Another Python SQLite Wrapper)   |
| Primary goal             | High-level SQLite utilities and CLI | Same high-level API, but built on APSW |
| CLI included             | ✅ Extensive                         | ❌ Primarily Python library             |
| Datasette integration    | Excellent                           | Not specifically                       |
| Latest SQLite features   | Limited by `sqlite3` version        | Full SQLite API via APSW               |
| Performance              | Good                                | Usually slightly better                |
| Advanced SQLite features | Some                                | Nearly all SQLite capabilities         |

## sqlite-utils

`sqlite-utils` is Simon Willison's mature library. It is intended to make SQLite pleasant to use from Python and from the command line. It is **not an ORM**—instead it focuses on manipulating databases with very little code. ([SQLite Utils][1])

Example:

```python
from sqlite_utils import Database

db = Database("movies.db")

db["movies"].insert({
    "title": "Alien",
    "year": 1979
})
```

Features include:

* automatic table creation
* automatic schema evolution
* upsert
* bulk inserts
* JSON support
* table transformations
* migrations (added in the 4.x series)
* excellent CLI
* plugin ecosystem ([Simon Willison’s Weblog][2])

This library is ideal for:

* ETL
* data science
* importing CSV/JSON
* quick scripts
* Datasette projects

---

## apswutils

`apswutils` is **Answer.AI's fork** of `sqlite-minutils` (a smaller sibling of `sqlite-utils`), rewritten to use **APSW** instead of the standard `sqlite3` module. ([GitHub][3])

The philosophy is:

> Keep the convenient high-level API while replacing the underlying driver with APSW.

Notable differences include:

* WAL enabled by default
* APSW exceptions instead of DB-API exceptions
* better transaction handling
* more correct handling of SQLite defaults
* access to all APSW capabilities ([GitHub][3])

Example:

```python
from apswutils import Database

db = Database("example.db")
```

The API intentionally resembles the original library.

---

# The real difference is APSW vs sqlite3

The biggest distinction is not the utility layer—it's the database driver underneath.

### sqlite3

Python's standard library wrapper:

* DB-API 2.0 compliant
* hides many SQLite-specific details
* limited to what the bundled SQLite version supports
* thread restrictions
* fewer advanced SQLite APIs

### APSW

APSW is almost a one-to-one wrapper around SQLite's C API.

Advantages include:

* newest SQLite releases
* virtual tables
* VFS
* FTS5
* sessions
* incremental BLOB I/O
* tracing
* backup API
* custom VFS
* busy handlers
* authorizers
* complete SQLite extension support
* better diagnostics and error reporting ([Roger Binns][4])

Roger Binns (the APSW author) recommends APSW when you want direct access to SQLite's full functionality, while `sqlite3` is appropriate for simpler, database-agnostic code. ([Roger Binns][4])

---

# Which should you choose?

### Choose `sqlite-utils` if

* you want a mature, widely used library
* you use Datasette
* you need the CLI
* you mainly perform ETL or scripting
* portability is more important than advanced SQLite features

---

### Choose `apswutils` if

* you're building SQLite-heavy applications
* you want the latest SQLite features immediately
* you need virtual tables, custom extensions, or advanced SQLite APIs
* you expect high concurrency
* you already prefer APSW over `sqlite3`

---

# For your background

Based on our previous conversations (Databricks, ETL pipelines, SQL tooling, analytics, and your interest in modern SQLite features), I would lean toward **APSW** as the underlying driver.

A practical combination would be:

* **APSW** for database access.
* **apswutils** for convenient CRUD operations.
* **sqlite-utils CLI** as a separate installation if you want its excellent command-line import/export and database manipulation tools.

That gives you both the full power of modern SQLite and the productivity of higher-level utilities.

[1]: https://sqlite-utils.datasette.io/?utm_source=chatgpt.com "sqlite-utils"
[2]: https://simonwillison.net/series/sqlite-utils-features/?utm_source=chatgpt.com "New features in sqlite-utils"
[3]: https://github.com/AnswerDotAI/apswutils?utm_source=chatgpt.com "AnswerDotAI/apswutils: A fork of sqlite-minutils for apsw"
[4]: https://rogerbinns.github.io/apsw/pysqlite.html?utm_source=chatgpt.com "sqlite3 module differences — APSW 3.53.2.0 documentation"



<https://andersmurphy.com/2026/06/05/the-perils-of-uuid-primary-keys-in-sqlite.html>
```
            "PRAGMA foreign_keys=ON;"
            "PRAGMA journal_mode = WAL;"
            "PRAGMA synchronous = NORMAL;"
            "PRAGMA busy_timeout = 5000;"
            "PRAGMA temp_store = MEMORY;"
            "PRAGMA mmap_size = 134217728;"
            "PRAGMA journal_size_limit = 67108864;"
            "PRAGMA cache_size = 2000;"
also turn on immediate mode so the busy_timeout works.
```
Sources:

<https://fractaledmind.github.io/2024/04/15/sqlite-on-rails-the-how-and-why-of-optimal-performance/>
<https://kerkour.com/sqlite-for-servers>


<https://slicker.me/sqlite/features.htm>


### Strict tables and better typing

SQLite is famous (or infamous) for its flexible typing model. Modern SQLite adds STRICT tables, which enforce type constraints much more like PostgreSQL or other traditional databases.

Example: defining a strict table:
```sql
CREATE TABLE users (
  id        INTEGER PRIMARY KEY,
  email     TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
) STRICT;
```
With strict tables, invalid types are rejected at insert time, making schemas more predictable and reducing subtle bugs—especially in larger codebases.
Generated columns for derived data

### Generated columns 
let you store expressions as virtual or stored columns, keeping derived data close to the source without duplicating logic across your application.

Example: a normalized search field:
```sql
CREATE TABLE contacts (
  id          INTEGER PRIMARY KEY,
  first_name  TEXT NOT NULL,
  last_name   TEXT NOT NULL,
  full_name   TEXT GENERATED ALWAYS AS (
    trim(first_name || ' ' || last_name)
  ) STORED
);

CREATE INDEX idx_contacts_full_name ON contacts(full_name);
```

Now every insert or update keeps full_name in sync automatically, and you can index and query it efficiently.

### Write-ahead logging and concurrency

Write-ahead logging (WAL) is a journaling mode that improves concurrency and performance for many workloads. Readers don’t block writers, and writers don’t block readers in the common case.

Enabling WAL is a single pragma call:

PRAGMA journal_mode = WAL;

For desktop apps, local-first tools, and small services, WAL mode can dramatically improve perceived performance while keeping SQLite’s simplicity and reliability.



### REST API for SQLite 
<https://github.com/b4fun/sqlite-rest>

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


### JSON

https://www.dbpro.app/blog/sqlite-json-virtual-columns-indexing

https://news.ycombinator.com/item?id=46243904

