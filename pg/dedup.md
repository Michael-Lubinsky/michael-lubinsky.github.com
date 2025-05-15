### identify duplicate or near-duplicate records 
(e.g., names and addresses with typos), 
exact matching won’t work — instead, you need fuzzy matching techniques.

✅ Approaches to Detect Duplicates with Typos in SQL
🔹 1. Use LOWER() and TRIM() for normalization
Start by cleaning up formatting differences.

```sql
SELECT 
  LOWER(TRIM(name)) AS clean_name,
  LOWER(TRIM(address)) AS clean_address,
  COUNT(*) 
FROM users
GROUP BY clean_name, clean_address
HAVING COUNT(*) > 1;
```
This finds exact duplicates ignoring case and extra spaces.

🔹 2. Use LEVENSHTEIN() or EDITDISTANCE() for fuzzy matching
Many SQL dialects (e.g., PostgreSQL, SQL Server via CLR, MySQL with plugins, or using UDFs in BigQuery/Snowflake/Databricks) support Levenshtein distance.

Example in PostgreSQL (using fuzzystrmatch extension):
```sql
SELECT u1.id, u1.name, u2.id, u2.name
FROM users u1
JOIN users u2 ON u1.id < u2.id
WHERE levenshtein(u1.name, u2.name) <= 2
  AND levenshtein(u1.address, u2.address) <= 3;
```
This finds names and addresses that are similar (within a certain distance).

🔹 3. Use SOUNDEX() or METAPHONE() for phonetic matching
This works well when names are spelled differently but sound similar.

```sql
SELECT u1.id, u1.name, u2.id, u2.name
FROM users u1
JOIN users u2 ON u1.id < u2.id
WHERE SOUNDEX(u1.name) = SOUNDEX(u2.name)
  AND SOUNDEX(u1.address) = SOUNDEX(u2.address);
```
🔹 4. Token similarity for addresses
Split address into tokens and use Jaccard similarity or set-based matching 
(harder to do in raw SQL; better with Python or Spark).

🚀 Best Practices for Production-Grade Deduplication
Pre-clean data (lowercase, trim, normalize abbreviations like “St.” vs “Street”).

Combine exact match on postal codes + fuzzy match on street names.

Use a data quality tool like:

Apache Spark with fuzzywuzzy or rapidfuzz

Dedupe.io or DataMatch Enterprise

dbt with fuzzy matching extensions

### In Databricks / Spark SQL
```
SELECT *
FROM users u1
JOIN users u2
  ON u1.id < u2.id
WHERE levenshtein(u1.name, u2.name) < 3
  AND levenshtein(u1.address, u2.address) < 5;
```
