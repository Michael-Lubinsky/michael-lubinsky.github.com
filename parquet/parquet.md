### Parquet 

<https://habr.com/ru/articles/1013604/>

<https://medium.com/@2nick2patel2/parquet-is-the-new-csv-for-python-0c0630afb57c>

<https://github.com/raulcd/datanomy>

<https://github.com/datasetq/datasetq>

<https://habr.com/ru/articles/1013956/> Iceberg

<https://www.dremio.com/blog/exploring-the-evolving-file-format-landscape-in-ai-era-parquet-lance-nimble-and-vortex-and-what-it-means-for-apache-iceberg/>

brew install kaushiksrini/parqeye/parqeye

<https://github.com/kaushiksrini/parqeye>

<https://news.ycombinator.com/item?id=45959780>

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

## ORC

<https://habr.com/ru/companies/gnivc/articles/1017106/>
