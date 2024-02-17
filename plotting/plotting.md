https://towardsdatascience.com/the-most-advanced-libraries-for-data-visualization-and-analysis-on-the-web-e823535e0eb1

https://pypi.org/project/canvasxpress/

https://www.highcharts.com/

### Scatter plot
https://python.plainenglish.io/boost-your-scatter-plots-with-this-function-ed3e51ca1e7d
```
sns.scatterplot(data=diamonds_sample,
                x='price',
                y='carat')
plt.show()

sns.regplot(data=diamond_sample,
            x='price',
            y='carat',
            order=2)
plt.show()

sns.regplot(data=diamond_sample,
            x='price',
            y='carat')
plt.show()
```

### Python advanced plots:
https://towardsdatascience.com/practical-tips-for-improving-exploratory-data-analysis-1c43b3484577

### Heatmap
```
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


### scatterplot matrix
```
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
### PyGWalker
https://medium.datadriveninvestor.com/python-pygwalker-simplifying-data-exploration-and-visualization-for-everyone-ed84cc7b7db4
