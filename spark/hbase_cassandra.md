| Feature      | HBase                          | Cassandra                       |
| ------------ | ------------------------------ | ------------------------------- |
| Type         | Wide-column store (on Hadoop)  | Wide-column store (independent) |
| Consistency  | Strong consistency             | Tunable (eventual by default)   |
| Architecture | Master-slave (HDFS, Zookeeper) | Peer-to-peer                    |

Because both databases are NoSQL wide-column stores, schema and query patterns are quite different from traditional RDBMS.

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


