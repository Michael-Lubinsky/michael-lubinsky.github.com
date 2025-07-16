https://josephbarbierdarnal.github.io/dayplot



### Seaborn
<https://seaborn.pydata.org/>

Seaborn Datasets For Data Science
<https://www.geeksforgeeks.org/seaborn-datasets-for-data-science/>

### Scatter plot (Seabon)

<https://python.plainenglish.io/boost-your-scatter-plots-with-this-function-ed3e51ca1e7d>  
<https://medium.com/@deepak.engg.phd/pythons-seaborn-library-data-visualization-on-dataset-diamond-920c8d7b798b>


```python
import matplotlib.pyplot as plt
import seaborn as sns
print (sns.get_dataset_names())
diamond=sns.load_dataset('diamonds', cache=True, data_home=None)

# Scatterplot
sns.scatterplot(data=diamond, x='price', y='carat')
plt.show()

sns.scatterplot(x='carat', y='price', hue='cut', size='depth', data=diamond)
plt.xlabel('Carat Weight')
plt.ylabel('Price')
plt.title('Scatter Plot: Carat Vs Price (Based on Cut)')

# Regplot
sns.regplot(data=diamond, x='price', y='carat', order=2)
plt.show()

sns.regplot(data=diamond, x='price', y='carat')
plt.show()
```
