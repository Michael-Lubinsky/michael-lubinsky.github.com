
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

### Python advanced plots

<https://towardsdatascience.com/practical-tips-for-improving-exploratory-data-analysis-1c43b3484577>

<https://blog.devgenius.io/data-profiling-in-python-common-ways-to-explore-your-data-part-2-396384522e91>

<https://medium.com/top-python-libraries/7-stunning-scientific-charts-i-created-with-matplotlib-that-you-shouldnt-miss-2de2ed91b164>

<https://posit-dev.github.io/gt-extras/articles/intro.html>

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
### PyGWalker
<https://medium.datadriveninvestor.com/python-pygwalker-simplifying-data-exploration-and-visualization-for-everyone-ed84cc7b7db4>

<https://towardsdatascience.com/the-most-advanced-libraries-for-data-visualization-and-analysis-on-the-web-e823535e0eb1>



https://github.com/rilldata/rill

### minimalytics
GO standalone minimalist analytics tool built on SQLite.  
Designed for resource-constrained environments, 
It provides a lightweight solution for tracking and visualizing event data with a minimal footprint.

<https://github.com/nafey/minimalytics>

### Plotting Libs

https://github.com/d3blocks/d3blocks

https://medium.com/data-science-collective/d3blocks-the-python-library-to-create-interactive-standalone-and-beautiful-d3-js-charts-ef8c65286e86

<https://lets-plot.org/>

<https://pypi.org/project/canvasxpress/>

<https://panel.holoviz.org/>

https://datashader.org/

https://www.pyqtgraph.org/



<https://gnuplot.sourceforge.net/>

<https://huijzer.xyz/posts/cetz-plot-speed/>

<https://www.reddit.com/r/Python/comments/1kpivim/best_gui_library_with_fast_rendering_times_for/>

<https://habr.com/ru/companies/ru_mts/articles/903142/>

### HighCharts

https://www.highcharts.com/

https://pypi.org/project/highcharts-excentis/

https://pypi.org/project/highcharts-core/

### Apache Echarts

https://github.com/ecomfe/awesome-echarts

https://news.ycombinator.com/item?id=43624220

https://echarts-python.readthedocs.io/en/latest/

https://panel.holoviz.org/reference/panes/ECharts.html

https://tech.marksblogg.com/python-data-visualisation-echarts-graphs-plots.html 

https://airbnb.io/visx/ VisX

### Apps

https://mathgl.sourceforge.net/

https://labplot.org/

https://alphaplot.sourceforge.io/

https://veusz.github.io/

gnuplot



