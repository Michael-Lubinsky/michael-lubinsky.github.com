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
