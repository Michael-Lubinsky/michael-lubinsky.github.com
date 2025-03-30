## Pandas

### Selecting Columns by Data Type
Filter columns based on data types (e.g., int64, float64, object).

Use Case: Isolate numerical columns for statistical analysis or machine learning preparation.

df.select_dtypes(include=['float64', 'int64'])

### Conditional Filtering with query
Use a string format for filtering rows, making conditions more readable.  
Use Case: Simplify filtering based on multiple conditions (e.g., age > 25 and city == “New York”).

df.query('age > 25 & city == "New York"')

### Chaining Operations with pipe
Apply functions sequentially in a clean, readable manner.  
Use Case: Streamline multi-step transformations like normalization or data cleaning
```python
def normalize(df):
    return (df - df.mean()) / df.std()

df.pipe(normalize)
```
### Exploding a List-Like Column
The explode function expands lists within a column into separate rows, 
aligning the rest of the DataFrame accordingly.

Use Case: When analyzing nested data like tags or categories, 
this method allows for granular analysis by breaking down lists into individual rows.

df.explode('column_with_lists')

### Using applymap for Element-Wise Operations
The applymap method applies a function to each individual element of a DataFrame.

Use Case: Perform element-wise transformations, such as formatting strings or applying mathematical computations.

df.applymap(lambda x: len(str(x)) if isinstance(x, str) else x)

### Creating New Columns with assign
The assign method simplifies adding new columns by applying functions or calculations directly to existing ones.

Use Case: Quickly compute derived metrics, such as calculating total costs from price and quantity

df.assign(total_cost=lambda x: x['price'] * x['quantity'])

### Using cut to Bin Data

The cut function devices continue variables into secrete bins or intervals.

Use Case: Segment data into categories like age group or income brackets to easier analysis.

df['age_group'] = pd.cut(df['age'], bins=[0, 18, 35, 60, 100], labels=['Teen', 'Young Adult', 'Adult', 'Senior'])

### Memory Optimization with astype
Reduce memory usage by converting column data types to more efficient formats, like category or int32.

Use Case: When working with large datasets, optimizing data types can significantly reduce memory consumption.

df['category_column'] = df['category_column'].astype('category')

### Forward and Backward Filling Missing Data
Fill missing values using the last valid observation (ffill) or the next valid one (bfill).

Use Case: Ideal for time-series data or sequences where you need to propagate known values to fill gaps.
```
df.ffill()  # Forward fill  
df.bfill()  # Backward fill
```
###  Working with MultiIndexes
Pandas supports hierarchical indexing, allowing for multi-level data organization.

Use Case: Manage and analyze data with multiple layers of categorization, such as sales by region and product.
```
df.set_index(['col1', 'col2'], inplace=True)
df.loc[('value1', 'value2')]
```
###  Aggregating Data with groupby and agg
Group data by one or more columns and apply aggregation functions like mean, sum, or custom functions.

Use Case: Summarize statistics for groups, such as total sales or average price per category.
```
df.groupby('category').agg({'price': ['mean', 'sum'], 'quantity': 'sum'})
```
###  Reshaping Data with melt
Transform wide-format data into a long format, consolidating multiple columns into key-value pairs.

Use Case: Convert monthly sales data from wide to long format for easier analysis.
```
pd.melt(df, id_vars=['id'], value_vars=['A', 'B'], var_name='variable', value_name='value')
```
### Pivoting DataFrames
The pivot function reshapes data by converting unique column values into new columns.

Use Case: Summarize data, like turning a table of sales by product and date into a pivoted format for better readability.
```
df.pivot(index='date', columns='product', values='sales')
```
### Using sample for Random Sampling
Randomly select a fraction or specific number of rows from a DataFrame.

Use Case: Create test datasets or quickly explore a representative subset of large data.
``
sampled_df = df.sample(frac=0.1, random_state=42)
```

### Time Series Aggregation with pandas

https://kapilg.hashnode.dev/time-series-aggregation-in-pandas


### Ibis amd SQLFrame

https://sqlframe.readthedocs.io/en/stable/

https://github.com/eakmanrq/sqlframe/blob/main/blogs/sqlframe_universal_dataframe_api.md

https://ibis-project.org/why

https://ibis-project.org/posts/1tbc/

https://www.youtube.com/watch?v=1ND6COslBKU

### Pandas series
```
import pandas as pd
t_list = [25, 28, 26, 30, 29, 27, 31]
t_series = pd.Series(t_list, name='Temperature')
print(t_series.mean())  # Calculate mean
```
A series mainly consists of the following three properties: index, datatype and shape

1) Index: Each element in a Series has a unique label or index that we can use to access the specific data points.
```
data = [10.2, 20.1, 30.3, 40.5]
series = pd.Series(data, index=["a", "b", "c", "d"])
print(series["b"])  # Access element by label
print(series[1])    # Access element by position

```
2) Data Type: All elements in a Series share the same data type.
   It is important for consistency and enabling smooth operations.

```
print(series.dtype)
print(series.shape)
print(series.loc["c"])  # Access by label
print(series.iloc[2])   # Access by position
```
Missing values
```
series.iloc[1] = np.nan # npy here is an object of numpy
print(series.dropna())  # Drop rows with missing values
```

#### Series Resampling
```
dates = pd.date_range(start="2024-01-01", periods=4)
temp_series = pd.Series([10, 12, 15, 18], index=dates)
# Calculate monthly avg temperature
print(temp_series.resample("M").mean())
```
### Pandas dataframe
Following code uses the .index attribute of the DataFrame to access the row labels and select the first 10 rows.
```
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
print(df.to_string(index=False))

df["A"].mean()

first_10_rows = df.loc[df.index[:10]]
print(first_10_rows)

first_10_rows = df.iloc[:10]
print(first_10_rows)

first_10_rows = df.query(‘index < 10’)
print(first_10_rows)
```

### Pandas queries
```
import pandas as pd
df = pd.DataFrame({"col1" : range(1,5), 
                   "col2" : ['A A','B B','A A','B B'],
                   "col3" : ['A A','A A','B B','B B']
                   })
newdf = df.query("col2 == 'A A'")  # hardcoded filter

myval1 = 'A A'
newdf = df.query("col2 == @myval1") # variable in filter

## pass column name to query:
myvar1 = 'col2'
newdf2 = df.query("{0} == 'A A'".format(myvar1))


## pass multiple column names to query:
myvar1 = 'col2'
myvar2 = 'col3'
newdf2 = df.query("{0} == 'A A' & {1} == 'B B'".format(myvar1, myvar2)) 


```
### Pandas and NumPy links

https://www.kdnuggets.com/visualizing-data-directly-numpy-arrays

https://realpython.com/python-for-data-analysis/

https://medium.com/@deyprakash753/14-pandas-tricks-you-must-know-aee396dde875

https://towardsdatascience.com/7-advanced-tricks-in-pandas-for-data-science-41a71632b5d9

https://github.com/DataForScience/
