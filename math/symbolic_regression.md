## Python Symbolic Regression

## pge-jax
JAX implementation of the Prioritized Grammar Enumeration (PGE) algorithm for symbolic regression.
<https://github.com/verdverm/pge-jax>


## PySR (Python Symbolic Regression) 

is an open-source machine learning library that automatically discovers mathematical equations from data.

<https://pysr.ai/>

Unlike traditional machine learning, which often produces a black-box model, PySR attempts to find a human-readable mathematical formula describing the relationship between input variables and outputs.

For example, suppose you have experimental data:

| x | y  |
| - | -- |
| 1 | 3  |
| 2 | 8  |
| 3 | 15 |
| 4 | 24 |
| 5 | 35 |

PySR might discover:

$$ \boxed{y=x^2+2x} $$

without being told that the relationship is quadratic.

This is particularly interesting for physics, scientific research, and discovering mathematical relationships in complex datasets.

## 1. Main use cases

| Domain              | Example of what PySR can discover                           |
| ------------------- | ----------------------------------------------------------- |
| Physics             | Equations relating force, mass, velocity, and energy        |
| Engineering         | Relationships between temperature, pressure, and efficiency |
| Finance             | Compact mathematical models of financial variables          |
| Retail analytics    | Relationships between prices, demand, and sales             |
| Biology             | Equations describing population growth                      |
| Machine learning    | Simple formulas approximating complex ML models             |
| Scientific research | Candidate mathematical laws from experimental observations  |

PySR is particularly valuable when you care about understanding the relationship, not just making accurate predictions.

## 2. How PySR works

Unlike ordinary linear regression, where you choose a model such as

$$ y=a+bx $$

PySR searches through many possible mathematical expressions.

Input data: \\(X,y\\)

Evolutionary symbolic search

Generate, mutate, combine and evaluate candidate equations

y = ax + b

y = ax² + b

y = sin(ax)

y = a / (x+b)

Candidate equations

Trade off prediction error against equation complexity

The underlying engine is written in Julia, with a Python interface. It uses evolutionary search and numerical optimization to discover expressions, rather than requiring you to specify the equation structure in advance.&#x20;

 



## 3. Python example: Discovering an equation

Suppose we generate data from:

$$ y=3x^2+2\sin(x)+5 $$

We then ask PySR to rediscover the equation without providing its structure.

```python

import numpy as np
from pysr import PySRRegressor

rng = np.random.default_rng(42)

# Generate synthetic data
X = rng.uniform(-5, 5, size=(1000, 1))
x = X[:, 0]

y = 3*x**2 + 2*np.sin(x) + 5

# Add measurement noise
y += rng.normal(0, 0.1, len(y))

# Configure symbolic regression
model = PySRRegressor(
    niterations=100,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sin", "cos"],
    maxsize=20,
)

model.fit(X, y)

# Show discovered equations
print(model.equations_)

# Best equation in symbolic form
print(model.sympy())

```

PySR may discover something close to:

$$ \boxed{y\approx3x^2+2\sin(x)+5} $$

The exact expression is not guaranteed. It depends on the data, noise, search configuration, and computation time.

PySR can also export discovered expressions to SymPy, making them useful for subsequent mathematical analysis.&#x20;

 


## 4. Interesting application: Your price–demand analysis

Consider your store dataset with daily prices, visitor counts, and product purchases.

Suppose the true data-generating process is:

$$ Q=100-5P+0.02V+0.1P^2 $$

where \\(P\\) is price, \\(V\\) is visitor count, and \\(Q\\) is sales.

You could use PySR to discover a nonlinear relationship without specifying a quadratic model beforehand.

For example:

```python
X = df[["price", "visitors"]]
y = df["sales"]
model.fit(X, y)
print(model.sympy())
```

PySR might find a formula similar to the generating equation.

But there is an important limitation:

PySR discovers statistical relationships, not necessarily causal relationships.

If retailers raise prices when demand is high, PySR may discover a positive price–sales relationship even though raising prices actually reduces sales.

For causal analysis, you still need a valid identification strategy, such as randomized prices or an appropriate instrumental variable.

## 5. PySR vs. other machine learning approaches

| Method                | Model structure                        | Interpretability      |
| --------------------- | -------------------------------------- | --------------------- |
| Linear regression     | Linear, specified beforehand           | Excellent             |
| Polynomial regression | Polynomial, degree selected beforehand | Good                  |
| Random Forest         | Ensemble of decision trees             | Limited               |
| Neural networks       | Learned nonlinear function             | Usually low           |
| PySR                  | Automatically searches for formulas    | Potentially excellent |

PySR's advantage is not necessarily prediction accuracy. A neural network or gradient-boosted tree may predict better.

Its distinctive advantage is finding a compact mathematical expression that can be inspected, tested, and potentially interpreted scientifically.

## 6. Where PySR is especially useful—and where it is not

PySR is a strong choice when you have a relatively small number of meaningful numeric variables, suspect a compact mathematical relationship, and want to discover its structure.

It is less suitable when your data has hundreds of unrelated features, is dominated by noise, or requires complicated categorical and temporal relationships. The search can also become computationally expensive as the space of possible expressions grows.

For time-series data, you must explicitly construct lagged features such as \\(P\_{t-1}\\) or \\(Q\_{t-1}\\). PySR does not automatically turn a table into a causal time-series model.

One especially interesting advanced capability is that PySR supports constrained expression structures, physical units, and even discovering differential equations from sampled data.&#x20;




You can explore the official [PySR documentation](https://pysr.ai/?utm_source=chatgpt.com) and [GitHub repository](https://github.com/MilesCranmer/PySR?utm_source=chatgpt.com).

My recommendation for your causal-analysis experiments: Use PySR as a complementary tool. First generate synthetic data with known equations, then compare ordinary regression, PySR, and causal estimation methods. 
That will reveal when symbolic regression successfully reconstructs a mathematical relationship—and when a correct-looking equation still gives the wrong causal interpretation.
