## How to read MS Excel into PySpark

If your Databricks Runtime is **17.1 or newer**, Databricks now has **built-in Excel support**, so you do not need `pandas`, `openpyxl`, or the old `com.crealytics.spark.excel` library. It can read `.xlsx` directly from S3, and it can list workbook sheets first. ([Databricks Documentation][1])

Suppose your file is:

```python
path = "s3://my-bucket/input/report.xlsx"
```

First, get the sheet names:

```python
sheets_df = (
    spark.read
         .format("excel")
         .option("operation", "listSheets")
         .load(path)
)

sheets_df.show()
```

You may get:

```text
+----------+-------------+
|sheetIndex|sheetName    |
+----------+-------------+
|0         |Customers    |
|1         |Orders       |
|2         |Products     |
+----------+-------------+
```

Databricks reads **one sheet at a time**, so then create one PySpark DataFrame per sheet. ([Databricks Documentation][1])

For known sheet names:

```python
customers_df = (
    spark.read
         .option("headerRows", 1)
         .option("dataAddress", "Customers")
         .excel(path)
)

orders_df = (
    spark.read
         .option("headerRows", 1)
         .option("dataAddress", "Orders")
         .excel(path)
)

products_df = (
    spark.read
         .option("headerRows", 1)
         .option("dataAddress", "Products")
         .excel(path)
)
```

Here:

```python
.option("headerRows", 1)
```

means the first row contains column names.

And:

```python
.option("dataAddress", "Orders")
```

means read the whole `Orders` sheet. You can also specify a range such as:

```python
.option("dataAddress", "Orders!A1:H5000")
```

Databricks supports either a sheet name or normal Excel-style ranges in `dataAddress`. ([Databricks Documentation][2])

### Dynamically load all sheets

A useful pattern is to put all the DataFrames into a Python dictionary:

```python
path = "s3://my-bucket/input/report.xlsx"

sheets_df = (
    spark.read
         .format("excel")
         .option("operation", "listSheets")
         .load(path)
)

sheet_names = [
    row.sheetName
    for row in sheets_df.collect()
]

dfs = {}

for sheet in sheet_names:
    dfs[sheet] = (
        spark.read
             .option("headerRows", 1)
             .option("dataAddress", sheet)
             .excel(path)
    )
```

Now:

```python
dfs.keys()
```

might return:

```text
dict_keys(['Customers', 'Orders', 'Products'])
```

and you access them as:

```python
dfs["Customers"].show()

dfs["Orders"].show()

dfs["Products"].show()
```

I prefer this over dynamically creating Python variables such as `df_Customers`, `df_Orders`, etc.

### Full example

```python
xlsx_path = "s3://my-bucket/data/source.xlsx"

# Get all workbook sheets
sheet_names = [
    row.sheetName
    for row in (
        spark.read
             .format("excel")
             .option("operation", "listSheets")
             .load(xlsx_path)
             .collect()
    )
]

# Load each sheet as its own PySpark DataFrame
sheet_dfs = {
    sheet: (
        spark.read
             .option("headerRows", 1)
             .option("dataAddress", sheet)
             .excel(xlsx_path)
    )
    for sheet in sheet_names
}

for sheet, df in sheet_dfs.items():
    print(f"{sheet}: {df.count()} rows")
    df.printSchema()
```

For example:

```text
Customers: 1500 rows
Orders: 18732 rows
Products: 428 rows
```

### If you know the sheets beforehand

I would actually use explicit names in a production pipeline:

```python
customers_df = spark.read.excel(
    xlsx_path,
    dataAddress="Customers",
    headerRows=1
)

orders_df = spark.read.excel(
    xlsx_path,
    dataAddress="Orders",
    headerRows=1
)

products_df = spark.read.excel(
    xlsx_path,
    dataAddress="Products",
    headerRows=1
)
```

This is clearer and lets you apply a different schema to every sheet.

For example, your `Customers` and `Orders` sheets probably have completely different schemas, so in production I would avoid relying only on inferred types.

One important requirement: this built-in API requires **Databricks Runtime 17.1+**. ([Databricks Documentation][1]) If you tell me your Databricks Runtime version, I can also show you the correct solution for an older cluster, where the approach is different.

[1]: https://docs.databricks.com/aws/en/query/formats/excel?utm_source=chatgpt.com "Read and stream Excel files | Databricks on AWS"
[2]: https://docs.databricks.com/gcp/en/spark/api-options?utm_source=chatgpt.com "Spark API options reference | Databricks on Google Cloud"



## Option 1 — Databricks: `spark-excel` / native Excel data source (recommended in your environment)

Databricks Runtime has built-in support for Excel via the `com.crealytics.spark.excel` format (or the newer native `excel` reader in recent DBR versions). It reads straight from S3 without pulling the file to driver memory manually — Spark handles the S3 read.

```python
# One sheet per DataFrame — repeat per sheet
df_sheet1 = (
    spark.read.format("com.crealytics.spark.excel")
    .option("header", "true")
    .option("dataAddress", "'Sheet1'!A1")       # sheet name + starting cell
    .option("inferSchema", "true")
    .load("s3://your-bucket/path/workbook.xlsx")
)

df_sheet2 = (
    spark.read.format("com.crealytics.spark.excel")
    .option("header", "true")
    .option("dataAddress", "'Sheet2'!A1")
    .option("inferSchema", "true")
    .load("s3://your-bucket/path/workbook.xlsx")
)
```

If you don't know the sheet names ahead of time, discover them first with `openpyxl` (see Option 2's inspection step below) and loop:

```python
sheet_names = ["Sheet1", "Sheet2", "Sheet3"]  # from inspection
dfs = {}
for name in sheet_names:
    dfs[name] = (
        spark.read.format("com.crealytics.spark.excel")
        .option("header", "true")
        .option("dataAddress", f"'{name}'!A1")
        .option("inferSchema", "true")
        .load("s3://your-bucket/path/workbook.xlsx")
    )
# dfs["Sheet1"], dfs["Sheet2"], ...
```

Make sure the library is attached to the cluster — on older DBR versions you install it as a Maven library (`com.crealytics:spark-excel_2.12:<version>`); recent DBR releases (14.x+) bundle native Excel support so you can often just use `.format("excel")` directly. Worth checking your specific runtime's release notes since this has shifted across DBR versions.

## Option 2 — Vanilla PySpark (no spark-excel, or you want more control): pandas/openpyxl → Spark

If you're not on Databricks or don't have the connector, read via pandas (which handles Excel natively through `openpyxl`) and convert:

```python
import pandas as pd
import boto3
from io import BytesIO

s3 = boto3.client("s3")
obj = s3.get_object(Bucket="your-bucket", Key="path/workbook.xlsx")
excel_bytes = BytesIO(obj["Body"].read())

# Discover sheet names first
xls = pd.ExcelFile(excel_bytes, engine="openpyxl")
print(xls.sheet_names)   # e.g. ['Sheet1', 'Sheet2', 'Sheet3']

# Load each sheet into a pandas DF, then convert to Spark
spark_dfs = {}
for sheet in xls.sheet_names:
    pdf = pd.read_excel(xls, sheet_name=sheet)
    spark_dfs[sheet] = spark.createDataFrame(pdf)
```

**Caveat**: this pulls the entire file (and each sheet as pandas) through the driver's memory — fine for typical Excel-sized files (tens of MB, tens of thousands of rows), but not viable for anything approaching Spark-scale data. Excel itself caps at ~1,048,576 rows/sheet, so this is inherently a "small/medium reference data" pattern, not a big-data ingestion pattern — which is usually the right mental model for Excel sources anyway.

## A few practical notes given your stack

- **Schema drift across sheets**: if sheets have inconsistent headers/types (common in hand-maintained Excel files), `inferSchema` can guess wrong — worth explicitly passing a `StructType` schema per sheet once you know the shape, rather than trusting inference in a pipeline you'll run repeatedly.
- **Merged cells / multi-row headers**: both approaches struggle here — `dataAddress` lets you point past a messy header region (e.g., `'Sheet1'!A3` to skip title rows), and pandas' `skiprows`/`header` params do the same.
- **S3 access**: for Option 1, your cluster's instance profile/IAM role needs S3 read access to the bucket, same as any other Spark S3 read — no special credential handling needed since Spark's Hadoop S3 connector handles it. For Option 2, `boto3` picks up credentials the same way (instance profile, env vars, or `~/.aws/credentials`).
- **If this becomes a recurring pipeline** (not one-off): writing each sheet straight to a Delta table (`spark_dfs[sheet].write.format("delta").mode("overwrite").saveAsTable(...)`) right after load is usually worth doing immediately, so downstream jobs don't re-parse Excel on every run.

Given you're already Unity-Catalog-centric, Option 1 with spark-excel is almost certainly the cleaner path if it's available on your cluster — it keeps everything in Spark's normal read/write model rather than round-tripping through pandas.
