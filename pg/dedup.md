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
```sql
SELECT *
FROM users u1
JOIN users u2
  ON u1.id < u2.id
WHERE levenshtein(u1.name, u2.name) < 3
  AND levenshtein(u1.address, u2.address) < 5;
```



### Jaccard Similarity

The Jaccard similarity between two sets A and B is:
```
J(A,B)= ∣A∪B∣ / ∣A∩B∣
​```
 Implementing Jaccard Similarity in Apache Spark is a great way to find near-duplicate text records — like user names or addresses — especially when typos or word-order differences exist.
In the context of text, we typically tokenize the string into words or character shingles, then compute similarity between those sets.

✅ Step-by-Step: Implement Jaccard Similarity in PySpark
Assuming a DataFrame df with columns id, name, and address:

🔹 Step 1: Tokenize the strings
You can split into sets of words or n-grams.

```python
from pyspark.sql.functions import split, col, array_distinct

df = df.withColumn("name_tokens", array_distinct(split(col("name"), "\\s+")))
```
🔹 Step 2: Self-join the table
We'll compare each row to every other row using a cross join or cartesian product (careful with large datasets).

```python
df1 = df.alias("a")
df2 = df.alias("b")

pairs = df1.join(df2, col("a.id") < col("b.id"))
```
🔹 Step 3: Define Jaccard similarity UDF
```python

from pyspark.sql.types import DoubleType
from pyspark.sql.functions import udf

def jaccard_similarity(tokens1, tokens2):
    set1, set2 = set(tokens1), set(tokens2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return float(intersection) / union if union else 0.0

jaccard_udf = udf(jaccard_similarity, DoubleType())
```
🔹 Step 4: Apply the UDF to compute similarity
```python
result = pairs.withColumn(
    "jaccard_score",
    jaccard_udf(col("a.name_tokens"), col("b.name_tokens"))
).filter(col("jaccard_score") > 0.5)  # threshold can be tuned
```
🔹 Optional: Apply to address as well
Just repeat the tokenization and Jaccard computation for the address field too.

⚠️ Performance Note
Cross joins are expensive: For large datasets, consider LSH (Locality Sensitive Hashing) or use MinHash for approximate Jaccard in Spark MLlib.

Use broadcast() if one side of the join is small.

🔸 Bonus: Approximate Jaccard via MinHash (Spark MLlib)
```python

from pyspark.ml.feature import Tokenizer, HashingTF, MinHashLSH

tokenizer = Tokenizer(inputCol="name", outputCol="name_tokens")
tokenized = tokenizer.transform(df)

hashingTF = HashingTF(inputCol="name_tokens", outputCol="features", numFeatures=1000)
featurized = hashingTF.transform(tokenized)

mh = MinHashLSH(inputCol="features", outputCol="hashes", numHashTables=3)
model = mh.fit(featurized)

# Find similar pairs
similar_pairs = model.approxSimilarityJoin(featurized, featurized, threshold=0.7, distCol="JaccardDistance")
similar_pairs.select("datasetA.id", "datasetB.id", "JaccardDistance").show()
```
