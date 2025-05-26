
To test whether two variables have a monotonic relationship — 
meaning they tend to increase or decrease together, without necessarily being linearly related — 
the most appropriate statistical test is:

### Spearman's rank correlation coefficient
🔍 What is Spearman's rank correlation?
It measures the strength and direction of a monotonic relationship between two variables.

It’s non-parametric (does not assume a specific distribution).

It’s based on ranked values, not raw data — so it captures monotonic trends, even if nonlinear.

🧪 Hypothesis tested:
H₀ (null hypothesis): The variables are not monotonically related.

H₁ (alternative): There is a monotonic relationship.

✅ Use Spearman when:
You want to test for monotonic association, not just linear (like Pearson does).

Your data may have nonlinear but ordered trends.

Your variables are ordinal, or not normally distributed.

📊 Example in Python:
```python

from scipy.stats import spearmanr
x = [1, 2, 3, 4, 5]
y = [10, 20, 30, 40, 50]

corr, p_value = spearmanr(x, y)
print(f"Spearman correlation: {corr:.3f}, p-value: {p_value:.3f}")
```

<https://medium.com/pythoneers/5-underrated-statistical-tests-you-didnt-know-you-needed-4224095233e8>

Kendall’s Tau is another non-parametric test for monotonicity, 
often more robust in small datasets or with many tied ranks.

