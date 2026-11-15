## Correlation Analysis

### What is desriptive measure of association

<https://tracyrenee61.medium.com/statistics-interview-question-what-are-descriptive-measures-of-association-23ee9c7612b5>

<http://www.machinelearning.ru/wiki/index.php?title=%D0%9A%D0%B0%D1%82%D0%B5%D0%B3%D0%BE%D1%80%D0%B8%D1%8F:%D0%9A%D0%BE%D1%80%D1%80%D0%B5%D0%BB%D1%8F%D1%86%D0%B8%D0%BE%D0%BD%D0%BD%D1%8B%D0%B9_%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7>


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

## Fechner’s coefficient 

is useful when your question is specifically: “Do these two variables tend to be above—or below—their respective averages together?”** It measures agreement of those signs, ignoring the size of the deviations.

For example, across stores, you might ask whether **above-average advertising spending tends to accompany above-average sales**. Fechner’s coefficient gives a simple summary of that agreement. This is the comparison described in these [university teaching materials](https://spmi.ru/sites/default/files/imci_images/univer/svedenia_jb_organizacii/metrek_baki/38.03.01-statistika-samotsoyatelnaya-rabota.pdf).

Choose the coefficient according to your actual question:

| Your goal | Usually choose |
|---|---|
| Measure a **linear relationship**, using actual numerical values | **Pearson** |
| Measure a **monotonic relationship**—as one variable increases, the other generally increases or decreases | **Spearman** |
| Measure agreement in the **ordering of pairs**, particularly for ordinal data | **Kendall’s tau** |
| Measure agreement in being **above or below the mean** | **Fechner** |

**In most analyses, Fechner should not replace Pearson, Spearman, or Kendall.** It discards substantial information: a value barely above the mean counts exactly the same as one far above it. Two datasets with very different scatterplots can therefore have the same Fechner coefficient.

Also, **it is not automatically resistant to outliers**. Although it uses only signs, those signs depend on the means, and an extreme observation can shift a mean considerably.

Use it when above/below-average agreement is itself meaningful, or for a simple descriptive demonstration. For general correlation analysis, inspect a scatterplot and usually choose Pearson, Spearman, or Kendall.

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

 
## Matthews Correlation Coefficient
<https://koshurai.medium.com/understanding-the-matthews-correlation-coefficient-mcc-in-machine-learning-26e8049f8572>
```
The Matthews Correlation Coefficient (MCC) is a measure of the quality of binary classifications.
It takes into account all four elements of a confusion matrix:
true positives (TP), true negatives (TN), false positives (FP), and false negatives (FN).
The MCC can be understood as a correlation coefficient between the predicted and actual classifications, ranging from -1 to +1.
An MCC of +1 indicates perfect predictions,
0 indicates no better than random guessing,
and -1 indicates total disagreement between predictions and true outcomes.
```
Mathematically, MCC is defined as:
<img width="663" height="103" alt="image" src="https://github.com/user-attachments/assets/dd7bcf53-528e-4270-a4a3-8a942ef74b0b" />
The Matthews Correlation Coefficient (MCC) is a measure of how well a binary classification model performs, and it’s based on the four outcomes of a confusion matrix:

True Positives (TP): These are instances where the model correctly predicted the positive class (i.e., both the actual and predicted labels are positive).

True Negatives (TN): These are instances where the model correctly predicted the negative class (i.e., both the actual and predicted labels are negative).

False Positives (FP): These occur when the model incorrectly predicts the positive class (i.e., the actual label is negative, but the model predicted positive).

False Negatives (FN): These occur when the model incorrectly predicts the negative class (i.e., the actual label is positive, but the model predicted negative).

Breakdown of the Formula:

Numerator: (TP×TN)−(FP×FN) — this part rewards cases where the model gets both true positives and 
true negatives correct, while penalizing false positives and false negatives.

Denominator: sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN)) this ensures that the MCC score is normalized between -1 and +1, making the MCC more interpretable. If all predictions are correct (both positives and negatives), the denominator scales accordingly, ensuring a perfect score.

MCC Value Ranges:
+1: Perfect prediction, meaning the model is in complete agreement with the actual labels.
0: The model is performing no better than random guessing.
-1: Total disagreement between the model’s predictions and the actual labels (worst possible prediction).

This formula essentially balances both the correct and incorrect classifications for both classes.

#### Why Use MCC?
Many traditional metrics, such as accuracy, can be misleading when working with imbalanced datasets, where one class heavily outweighs the other.   
For instance, if you’re building a model to detect rare diseases,   
the accuracy might be high even if the model predicts the majority class (negative cases) most of the time.

MCC solves this issue by considering the balance between the positive and negative classes, offering a more insightful evaluation.   
Unlike accuracy, which can give inflated results for imbalanced data,   
MCC remains a reliable metric regardless of class distribution.

#### Key Benefits of MCC:
Handles imbalanced datasets well: Even with skewed distributions, MCC gives a fair evaluation.
Comprehensive: It considers all elements of the confusion matrix.  
Unbiased: It is not influenced by class imbalance, unlike metrics like precision or accuracy.
#### MCC vs Other Metrics
Accuracy: Accuracy gives the overall correct predictions but doesn’t provide insights when one class dominates. 
MCC, in contrast, reflects both correct and incorrect predictions across all classes.

Precision & Recall: Precision focuses on the positive predictive value, while recall emphasizes sensitivity.   
MCC incorporates both, along with the balance between positives and negatives.
F1-Score: F1-score averages precision and recall, but it does not consider true negatives. 
MCC, however, takes into account the entire confusion matrix, offering a more holistic measure.

#### When Should You Use MCC?
MCC is especially useful in the following scenarios:

1) Imbalanced datasets: When one class dominates, MCC gives a more realistic picture of model performance than accuracy.  
2) Binary classification: While MCC can be extended to multi-class problems, it shines in binary classification tasks.

Real-world problems: Use MCC when you are dealing with real-world issues like fraud detection, disease diagnosis, or spam filtering, where class imbalance is common.
```python
from sklearn.metrics import matthews_corrcoef

# True and predicted labels
y_true = [1, 0, 1, 1, 0, 0, 1, 0, 0, 0]
y_pred = [1, 0, 1, 1, 0, 1, 0, 0, 0, 0]

# Calculate MCC
mcc = matthews_corrcoef(y_true, y_pred)
print(f'Matthews Correlation Coefficient: {mcc}')
```

<https://leimao.github.io/blog/Matthews-Correlation-Coefficient/>
```
Matthews Correlation Coefficient is nothing special but applying 
Pearson Correlation Coefficient to binary classification problems 
where two random variables are prediction and label. 
That is to say, Matthews Correlation Coefficient is a discrete case 
for Pearson Correlation Coefficient.

When Pearson Correlation Coefficient or Matthews Correlation Coefficient 
is more close to 1.0, this means that more predictions match labels; 
When Pearson Correlation Coefficient is more close to -1.0, 
this means that more predictions disagree with labels; 
When Pearson Correlation Coefficient is more close to 0, 
this means that more predictions and labels do not have strong correlations, 
i.e., the predictions seem to be random.
```
<http://www.machinelearning.ru/wiki/index.php?title=%D0%9A%D0%BE%D1%80%D1%80%D0%B5%D0%BB%D1%8F%D1%86%D0%B8%D1%8F_%D0%9C%D1%8D%D1%82%D1%8C%D1%8E%D1%81%D0%B0>
