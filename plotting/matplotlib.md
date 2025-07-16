<https://josephbarbierdarnal.github.io/dayplot> calendar heatmaps; built on matplotlib

<https://towardsdatascience.com/practical-tips-for-improving-exploratory-data-analysis-1c43b3484577/>

<https://medium.com/top-python-libraries/7-stunning-scientific-charts-i-created-with-matplotlib-that-you-shouldnt-miss-2de2ed91b164>

<https://towardsdatascience.com/from-default-python-line-chart-to-journal-quality-infographics-80e3949eacc3/>

<https://medium.com/dev-genius/data-profiling-in-python-common-ways-to-explore-your-data-part-1-0efd0dedff75>

<https://blog.devgenius.io/data-profiling-in-python-common-ways-to-explore-your-data-part-2-396384522e91>


https://github.com/garrettj403/SciencePlots

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
### Heatmap (Seaborn)
```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# read data
data = pd.read_csv('T1.csv')
print(data)

# rename columns to make their titles shorter
data.rename(columns={'LV ActivePower (kW)':'P',
                     'Wind Speed (m/s)':'Ws',
                     'Theoretical_Power_Curve (KWh)':'Power_curve',
                     'Wind Direction (°)': 'Wa'},inplace=True)
cols = ['P', 'Ws', 'Power_curve', 'Wa']

# build the matrix
correlation_matrix = np.corrcoef(data[cols].values.T)
hm = sns.heatmap(correlation_matrix,
                 cbar=True, annot=True, square=True, fmt='.3f',
                 annot_kws={'size': 15},
                 cmap='Blues',
                 yticklabels=['P', 'Ws', 'Power_curve', 'Wa'],
                 xticklabels=['P', 'Ws', 'Power_curve', 'Wa'])

# save the figure
plt.savefig('image.png', dpi=600, bbox_inches='tight')
plt.show()

```

### Scatterplot matrix (Seaborn)
```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# read data
data = pd.read_csv('T1.csv')
print(data)

# rename columns to make their titles shorter
data.rename(columns={'LV ActivePower (kW)':'P',
                     'Wind Speed (m/s)':'Ws',
                     'Theoretical_Power_Curve (KWh)':'Power_curve',
                     'Wind Direction (°)': 'Wa'},inplace=True)
cols = ['P', 'Ws', 'Power_curve', 'Wa']

# build the matrix
sns.pairplot(data[cols], height=2.5)
plt.tight_layout()

# save the figure
plt.savefig('image2.png', dpi=600, bbox_inches='tight')
plt.show()
```
