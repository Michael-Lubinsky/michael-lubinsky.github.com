
## How to test whether two variables have a monotonic relationship 
meaning they tend to increase or decrease together, 
without necessarily being linearly related — 
the most appropriate statistical test is:

### Spearman's rank correlation coefficient
 Spearman's rank correlation  measures the strength and direction of a monotonic relationship between two variables.

It’s non-parametric (does not assume a specific distribution).

It’s based on ranked values, not raw data — so it captures monotonic trends, even if nonlinear.

🧪 Hypothesis tested:
H₀ (null hypothesis): The variables are not monotonically related.

H₁ (alternative): There is a monotonic relationship.

✅ Use Spearman when:
You want to test for monotonic association, not just linear (like Pearson does).

Your data may have nonlinear but ordered trends.  
Your variables are ordinal, or not normally distributed.  
Example in Python:  
```python

from scipy.stats import spearmanr
x = [1, 2, 3, 4, 5]
y = [10, 20, 30, 40, 50]

corr, p_value = spearmanr(x, y)
print(f"Spearman correlation: {corr:.3f}, p-value: {p_value:.3f}")
```

### Mann-Kendall trend test and Kendall's Tau correlation test 

They are related but distinct.
✅ Kendall's Tau:
A correlation coefficient that measures the strength of monotonic association between two variables.

It gives a value between -1 and 1 like Spearman’s rho or Pearson’s r.  
Typically used to assess how well one variable monotonically relates to another.  

➡️ Example use:

"Is there a monotonic relationship between income and education level?"

✅ Mann-Kendall Trend Test:
A non-parametric test specifically designed to detect monotonic trends over time in a single variable.

Used in time series analysis to determine whether a variable tends to increase or decrease over time.

It also uses a statistic derived from Kendall’s rank correlation, but it is applied over time, not between two variables.

➡️ Example use:

"Is temperature showing a consistent upward or downward trend over the past 50 years?"

| Feature  | Kendall's Tau           | Mann-Kendall Trend Test     |
| -------- | ----------------------- | --------------------------- |
| Purpose  | Measure correlation     | Detect trend in time series |
| Data     | Two variables           | One variable over time      |
| Output   | Correlation coefficient | Trend direction + p-value   |
| Use case | Association strength    | Trend detection             |



pip install pymannkendall

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import kendalltau
import pymannkendall as mk

# Create synthetic time series data with a trend
np.random.seed(42)
time = np.arange(2000, 2020)
values = np.linspace(10, 20, len(time)) + np.random.normal(0, 1, len(time))

# 1. Kendall's Tau Correlation
tau_corr, tau_p = kendalltau(time, values)
print(f"Kendall's Tau correlation: {tau_corr:.3f}, p-value: {tau_p:.3f}")

# 2. Mann-Kendall Trend Test
mk_result = mk.original_test(values)
print(f"\nMann-Kendall Test:")
print(f"  Trend: {mk_result.trend}")
print(f"  Tau: {mk_result.Tau:.3f}")
print(f"  S: {mk_result.S}")
print(f"  p-value: {mk_result.p:.3f}")
print(f"  h (significant?): {mk_result.h}")

# Plot
plt.plot(time, values, marker='o')
plt.title('Synthetic Time Series with Trend')
plt.xlabel('Year')
plt.ylabel('Value')
plt.grid(True)
plt.show()

```

 
### Find the sum of 2 uniform distributions
- Two independent uniform distributions X ~ U[a,b], Y ~ U[c,d].
- They have the same mean and same standard deviation.


### 1) Determining the ranges:
For a uniform U[p,q]:
- Mean: mu = (p+q)/2
- Standard deviation: sigma = (q-p)/sqrt(12)

Having same mean and standard deviation implies:
b - a = d - c
and
(a + b)/2 = (c + d)/2  
which means:  
a = c, b = d

Thus: X and Y are identically distributed on the same interval [a,b].

 

### 2) Distribution of Z = X + Y

If X and Y are independent and uniform on the same interval [a,b], then:  
- The distribution of Z = X + Y will be the Irwin-Hall distribution of order 2  
  (the convolution of two uniform distributions).

Specifically:
- The support will be: [2a, 2b]  
- The probability density function (PDF) of Z will be:

f_Z(z) =
    (z - 2a) / (b - a)^2 ,      for 2a <= z < a + b  
    (2b - z) / (b - a)^2 ,      for a + b <= z <= 2b  
    0 ,                         otherwise  

---

### 3) Properties of Z
- Shape: Triangular distribution (tent shape).
- Mean:
E[Z] = E[X] + E[Y] = 2 * E[X] = 2 * mu
- Variance:
Var[Z] = Var[X] + Var[Y] = 2 * sigma^2
- Standard deviation:
sigma_Z = sqrt(2) * sigma


### Summary

The distribution of X + Y where X, Y are independent uniform distributions   
with the same mean and standard deviation is a triangular distribution on [2a, 2b] with a peak at a + b.  

The PDF is explicitly:
f_Z(z) =
    (z - 2a) / (b - a)^2 ,      for 2a <= z < a + b  
    (2b - z) / (b - a)^2 ,      for a + b <= z <= 2b  
    0 ,                         otherwise  



<https://habr.com/ru/articles/924770/>


### How to find the right distribution for your data

<https://medium.com/data-science-collective/how-to-find-the-right-distribution-for-your-data-a-practical-guide-for-non-statistician-with-two-dc2aa0ed707f>

https://habr.com/ru/companies/tbank/articles/911900/ к какому классу распределения отнести нашу выборку?



#### Gini index 
https://medium.com/data-science-collective/what-the-gini-index-really-tells-us-3624cf4189ac

### reservoir sampling
https://samwho.dev/reservoir-sampling/

#### Monte Carlo 
https://thenumb.at/Sampling/

### Stat rethinking
https://xcelab.net/rm/statistical-rethinking/  
https://www.goodreads.com/book/show/26619686-statistical-rethinking  
https://github.com/rmcelreath/stat_rethinking_2024

### T-test, Welch test
https://habr.com/ru/companies/X5Tech/articles/896182/

### What is desriptive measure of association

https://tracyrenee61.medium.com/statistics-interview-question-what-are-descriptive-measures-of-association-23ee9c7612b5


### Stat distributions in python
https://medium.com/data-bistrot/log-normal-distribution-with-python-7b8e384e939e  
https://medium.com/data-bistrot/bernoulli-distribution-with-python-0416e196e752  

https://medium.com/data-bistrot/bionomial-distribution-with-python-05d4a1725811  
https://medium.com/data-bistrot/uniform-and-normal-statistical-distribution-in-python-6d07fd5fc552


<https://medium.com/pythoneers/5-underrated-statistical-tests-you-didnt-know-you-needed-4224095233e8>

<https://www.statology.org/understanding-the-difference-between-parametric-and-nonparametric-tests/>


#### Poisson distrib   

https://medium.com/data-bistrot/poisson-distribution-with-python-791d7afad014

https://tracyrenee61.medium.com/use-python-to-understand-the-poisson-distribution-and-the-functions-associated-with-it-605a0bc31375


### EDA

https://github.com/ydataai/ydata-profiling

https://realpython.com/python-for-data-analysis/

https://www.kdnuggets.com/2021/07/single-line-exploratory-data-analysis.html

https://habr.com/ru/articles/922454/ кросс-энтропия позволяет оценить разницу между двумя распределениями
