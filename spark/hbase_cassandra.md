| Feature      | HBase                          | Cassandra                       |
| ------------ | ------------------------------ | ------------------------------- |
| Type         | Wide-column store (on Hadoop)  | Wide-column store (independent) |
| Consistency  | Strong consistency             | Tunable (eventual by default)   |
| Architecture | Master-slave (HDFS, Zookeeper) | Peer-to-peer                    |

### Apache Cassandra
Inspired by Google Bigtable

Each row is identified by a primary key and can contain thousands to millions of columns
Columns are sorted by clustering keys
Data model: Partition key → clustering columns → column values


UserID | Timestamp1 | Timestamp2 | Timestamp3 ...
-------|------------|------------|------------
  A123 |  "login"   | "purchase" | "logout"


Row key: A123 
Columns: dynamic timestamps with actions 
Perfect for time-series or sensor data 

### HBase (Apache HBase)
Built on top of Hadoop HDFS
Data is organized into:
- Row keys
- Column families (predefined groups)
- Columns (added dynamically)
- Timestamps (for versioning)

HBase Logical Structure:

RowKey: user123
Column Family: activity
    - login: "2025-01-01"
    - purchase: "2025-01-02"
    - logout: "2025-01-03"

### Summary: Why "Wide-Column"?
Each row can have many columns (wide).  
Columns can differ across rows.  
Data is stored in a sparse, column-oriented fashion.  
Optimized for fast reads/writes with large volumes of data.

| Use Case                     | Wide-Column Store Advantage |
| ---------------------------- | --------------------------- |
| Time-series data             | Easy column-based modeling  |
| User activity/event tracking | Flexible schema             |
| IoT sensor logs              | Millions of columns per row |
| Real-time analytics at scale | High write throughput       |

🔷 Apache Cassandra – CQL Examples
Cassandra uses CQL, a SQL-like language designed for ease of use with Cassandra’s architecture.

1. Create Keyspace (like a database)

CREATE KEYSPACE IF NOT EXISTS my_keyspace
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};
2. Create Table

USE my_keyspace;

CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    name TEXT,
    email TEXT,
    age INT
);

3. Insert Data

INSERT INTO users (user_id, name, email, age)
VALUES (uuid(), 'Alice', 'alice@example.com', 30);

4. Query Data

SELECT * FROM users WHERE user_id = 123e4567-e89b-12d3-a456-426614174000;

5. Update and Delete

UPDATE users SET age = 31 WHERE user_id = 123e4567-e89b-12d3-a456-426614174000;

DELETE FROM users WHERE user_id = 123e4567-e89b-12d3-a456-426614174000;
🔶 Apache HBase – Shell Commands
HBase uses a command-line shell with its own DSL (not SQL-like). It’s more low-level.

1. Create Table

create 'users', 'info'
users: table name

info: column family

2. Insert Data (Put)
 
put 'users', 'user1', 'info:name', 'Alice'
put 'users', 'user1', 'info:email', 'alice@example.com'
put 'users', 'user1', 'info:age', '30'
'user1' is the row key

3. Get Row
 
get 'users', 'user1'
4. Scan Table
 
scan 'users'

5. Delete Data

delete 'users', 'user1', 'info:email'

6. Drop Table

disable 'users'
drop 'users'


🔷 PART 1: HBase
🔹 Key Concepts: Tables have row keys, column families, and columns.

Columns are sparse and dynamic.

HBase does not support SQL natively, but can be queried with Apache Phoenix (a SQL layer on top of HBase).

✅ HBase Schema Design Example
Suppose you want to store user profiles and user purchases:

🔸 Table: user_profile

Row key: user_id  
Column family: info  
Columns: name, email, city  

🔸 Table: user_purchase
Row key: user_id#timestamp (to store purchases chronologically per user)  
Column family: purchase  
Columns: item, price  

📘 HBase Query Example (via Apache Phoenix)
```sql
CREATE TABLE user_profile (
  user_id VARCHAR PRIMARY KEY,
  info.name VARCHAR,
  info.email VARCHAR,
  info.city VARCHAR
);

CREATE TABLE user_purchase (
  rowkey VARCHAR PRIMARY KEY,
  purchase.item VARCHAR,
  purchase.price DOUBLE
);

-- Filter users from a city
SELECT user_id, info.name
FROM user_profile
WHERE info.city = 'New York';

-- Join purchases with user info
SELECT u.user_id, u.info.name, p.purchase.item, p.purchase.price
FROM user_profile u
JOIN user_purchase p ON p.rowkey LIKE u.user_id || '%'
WHERE p.purchase.price > 50;
```
Joins are only possible in HBase when using Apache Phoenix or through manual joins in application logic.

🔷 PART 2: Cassandra
🔹 Key Concepts:
Tables have partition keys and optional clustering columns.  
Query model is based on the primary key, and joins are not supported natively.  
Queries must align with how data is partitioned.  
Supports CQL (Cassandra Query Language), similar to SQL.  

✅ Cassandra Schema Design Example
Suppose you have user data and purchases, similar to the HBase case.

🔸 Table: user_profile
```sql

CREATE TABLE user_profile (
  user_id UUID PRIMARY KEY,
  name TEXT,
  email TEXT,
  city TEXT
);
🔸 Table: user_purchase

CREATE TABLE user_purchase (
  user_id UUID,
  purchase_time TIMESTAMP,
  item TEXT,
  price DOUBLE,
  PRIMARY KEY (user_id, purchase_time)
) WITH CLUSTERING ORDER BY (purchase_time DESC);
```
This model stores purchases per user, ordered by time (descending).

📘 Cassandra Query Examples
🔹 Filter: Get user by city (Not allowed directly unless indexed or denormalized)

```sql

-- Option 1: Use a secondary index
CREATE INDEX ON user_profile(city);

SELECT * FROM user_profile WHERE city = 'New York';
🔹 Filter: Get all purchases for a user

SELECT * FROM user_purchase WHERE user_id = 123e4567-e89b-12d3-a456-426614174000;
```
🔹 “Join” user info with purchases
Joins aren't allowed — you’d denormalize and store user info in the user_purchase table at write time.

Or do the join in application logic:

```python

# Pseudocode in Python
profile = session.execute("SELECT * FROM user_profile WHERE user_id = ?", [uid])
purchases = session.execute("SELECT * FROM user_purchase WHERE user_id = ?", [uid])
```
🔚 Summary: HBase vs Cassandra Schema & Query
| Feature         | HBase                                 | Cassandra                                 |
| --------------- | ------------------------------------- | ----------------------------------------- |
| Schema model    | Row key + column families             | Partition key + clustering key            |
| Joins           | Not supported natively, Phoenix helps | Not supported, denormalize or join in app |
| Filters         | By row key or Phoenix for SQL         | By partition key (or indexed fields)      |
| SQL support     | Yes (via Apache Phoenix)              | Yes (CQL, SQL-like syntax)                |
| Denormalization | Often required                        | Almost always required                    |


