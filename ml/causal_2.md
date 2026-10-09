## There is  file in csv format with time series data
```
First column is time stamp in format YYYY-MM-DD
Other columns are:

number of store visitors
number of product_1 purchases
number of product_2 purchases
number of product_3 purchases
price of product_1
price of product_2
price of product_3

There is discipline:  causal analysis in time series.
How to apply it to this  data?
```
Causal analysis on this data comes down to a few concrete questions. How much does the price of a product move its own sales (own-price elasticity)? Does raising the price of product 1 push buyers to product 2 (substitution) or pull product 2 down with it (complementarity)? And how much of the movement in purchases is just traffic, meaning more visitors bringing more of everything? The methods below answer those questions with different levels of rigor and different assumptions.

## 1. Draw the causal graph before touching a model

Write down what you believe causes what. A reasonable starting graph for this data:

- Visitors → purchases of every product
- price_i → purchases_i (own effect), and price_j → purchases_i (cross effects)
- Price → visitors, possibly, if price cuts are advertised
- Calendar (day of week, holidays, season) → visitors, purchases, and often prices
- **Unobserved demand shocks → prices.** This is the big one. If the store raises prices when it expects high demand, or cuts them when sales are slow, prices are *endogenous*. A naive regression can then show higher prices associated with *higher* sales. Every method below either assumes this away or works around it.

This graph tells you what to control for. Calendar is a confounder, so it goes in the model. Visitors is partly a mediator if price drives traffic, so including it changes what you're estimating. With visitors in the model you get the effect of price per visitor. Without it you get the total effect.

## 2. Prepare the series

- **Logs.** Use log(purchases) and log(price). In a log-log model, the coefficients are elasticities directly.
- **Derived series.** Conversion rate (purchases_i / visitors) separates "fewer people came" from "people came but didn't buy."
- **Stationarity.** Run ADF and KPSS tests on each series. Difference the series or detrend them if needed. Most of the methods below assume stationarity, and two trending series will look causally linked even when they aren't.
- **Seasonality.** Daily retail data almost always has a 7-day cycle. Add day-of-week dummies or deseasonalize, and add holiday flags.
- **Price variation.** Check how often each price actually changes. If product 1's price changed only three times in two years, no method can extract a reliable elasticity. In that case the analysis becomes event-based (see method D).

## 3. Methods, from exploratory to more causal

**A. Granger causality and VAR (exploratory).**
Fit a vector autoregression on the system and test whether past price_1 improves the forecast of purchases_1 beyond purchases_1's own past. Impulse response functions then show how a shock to price_1 propagates through all the series over the following days.
- Caveat: Granger causality means "predictive precedence," not true causation. It also misses same-day effects, which is where most of the action is with daily data and price changes.

**B. Regression with lags and controls (the workhorse).**

```
log(purch_1) ~ log(p1) + log(p2) + log(p3) + log(visitors)
             + lags of the above + day-of-week + holidays
```

- The coefficient on log(p1) is the own-price elasticity.
- The coefficients on log(p2) and log(p3) are cross elasticities. A positive sign means the products are substitutes; a negative sign means complements.
- Use HAC (Newey-West) standard errors, because the residuals will be autocorrelated.
- This estimate is causal only if prices aren't reacting to demand shocks that the controls miss.

**C. Handling price endogeneity.**
- **Instrumental variables.** If you have supplier cost or wholesale price, it moves the retail price without directly moving demand. Use it as an instrument with 2SLS.
- **Double machine learning.** EconML or DoubleML let you flexibly partial out calendar effects and lagged dynamics before estimating the price effect. Use time-blocked cross-fitting, not random folds, to avoid leakage across time.

**D. Event-based designs (often the most convincing).**
If prices change in discrete steps, such as promotions or repricings, treat each change as an intervention.
- **Interrupted time series.** Compare the level and slope of purchases before and after the price change.
- **CausalImpact (Bayesian structural time series).** Forecast the counterfactual "no price change" path from the pre-period, using covariates that weren't affected by the change, such as visitors. Then compare that forecast with what actually happened.
- Watch the cross effects here. If product 2 is a substitute, you can't use it as a control series when product 1's price changes, because it was treated too.
- **Synthetic control or difference-in-differences.** If you have several stores and only some changed prices, these designs become possible and are much stronger than single-series methods.

**E. Causal discovery (when you don't trust your graph).**
- **PCMCI (`tigramite`).** Designed for autocorrelated time series. It finds both lagged and same-day links.
- **VARLiNGAM (`lingam`).** Can orient contemporaneous edges under a non-Gaussian noise assumption.

Use these methods to generate or check hypotheses, not as final answers.

## 4. Validate and stress-test

- **Placebo tests.** Fake the intervention date or shuffle the price series. A real effect should disappear when you do.
- **Refutation checks.** DoWhy supports refuters such as adding a random common cause or using data subsets.
- **Sensitivity to lag choice, differencing, and the control set.** If an elasticity flips sign when you add day-of-week dummies, it wasn't identified.
- **Known pitfalls:**
  - **Stockouts.** Low purchases might be caused by no supply, not a high price.
  - **Promotions or ads absent from the data.** These are unobserved confounders.
  - **Multiple testing.** Testing 7 series × several lags inflates false positives.

## Suggested order

1. Plot everything and check how much price variation exists.
2. Write down the causal graph.
3. Log-transform the series, add calendar controls, and check stationarity.
4. Run VAR and Granger tests for a first look.
5. Fit the log-log regression with HAC errors to get elasticity estimates.
6. If prices change in discrete steps, run CausalImpact or interrupted time series around the changes as the stronger causal check.
7. Run placebo and sensitivity tests.

## PyWhy and others libs
Beyond the PyWhy ecosystem, these are the libraries I'd recommend, grouped by what they do.

PyWhy  includes EconML (heterogeneous effects, double ML, instrumental-variable estimators) and causal-learn (causal discovery: PC, FCI, GES, and Granger tests).

## Time-series-specific Python libraries

- **tigramite** is the reference implementation of PCMCI and related algorithms. It does causal discovery on autocorrelated time series and finds both lagged and same-day links. It's the strongest dedicated tool for "which of my 7 series drives which."
- **lingam** includes VARLiNGAM, which can orient contemporaneous edges. That matters for daily data, where a price change and the sales response often land on the same day.
- **CausalPy** (from PyMC Labs) does Bayesian quasi-experiments: interrupted time series, synthetic control, difference-in-differences, and regression discontinuity. It's a very good fit if your prices change in discrete steps.
- **tfp-causalimpact** is Google's official Python port of CausalImpact (Bayesian structural time series). **tfcausalimpact** is a community alternative. Avoid the older `pycausalimpact`, which is no longer maintained.
- **pysyncon** implements synthetic control methods. Use it if you have several stores and only some of them changed prices.
- **statsmodels** handles the basics: VAR, Granger tests, impulse response functions, ADF/KPSS stationarity tests, and HAC standard errors.

## Effect estimation and econometrics

- **DoubleML** is a clean implementation of double/debiased machine learning, with good documentation on identification assumptions.
- **CausalML** (from Uber) focuses on uplift modeling and meta-learners (S, T, X, and R learners). It's oriented toward treatment-effect heterogeneity, so it's less directly useful for time series.
- **linearmodels** provides 2SLS, IV-GMM, and panel models. You'd use it if you find an instrument for price, such as supplier cost.

## Causal discovery and graphical models

- **gCastle** (from Huawei) is a large collection of discovery algorithms, some of them for time series.
- **pgmpy** covers Bayesian networks: DAG specification, d-separation checks, and do-calculus inference.

## Marketing and demand modeling (adjacent, but relevant here)

- **PyMC-Marketing** and **Meridian** (from Google) are media mix modeling frameworks. With visitors, purchases, and prices in your data, their adstock and saturation ideas transfer well. You'd treat price as a driver with lagged effects.

## What I'd use for your dataset

1. statsmodels for preprocessing and a VAR/Granger first look.
2. tigramite (PCMCI) to discover the link structure among visitors, prices, and purchases.
3. DoubleML or EconML for elasticity estimates with flexible controls.
4. CausalPy or tfp-causalimpact around discrete price changes as the strongest causal check.
5. DoWhy's refuters for placebo and sensitivity tests.

Maintenance status changes over time. CausalNex, for example, has gone quiet. Check recent commit activity before adopting any of these libraries for production work.
