## Causal Python
https://www.pywhy.org/learn/developer-resources.html

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

DoWhy's distinguishing feature is its end-to-end workflow: model the causal graph, identify the estimand, estimate the effect, then refute it. Few libraries cover all four steps, so most "competitors" overlap with DoWhy on one or two of them.

**Closest full-workflow alternatives**
- **CausalML** (from Uber) is probably the most common alternative people pick instead of DoWhy. It's estimation-centric (meta-learners, uplift trees, some refutation and sensitivity tools), but it has no graph-based identification.
- **CausalNex** (from QuantumBlack/McKinsey) combined structure learning, Bayesian networks, and do-interventions in one package. It no longer appears to be maintained, so I wouldn't start new work with it.

**Competitors on graph modeling and identification (DoWhy's core strength)**
- **Ananke** (from Johns Hopkins) handles identification with graphs that include hidden variables (ADMGs), plus semiparametric efficient estimators. It's more rigorous than DoWhy on identification when there's unobserved confounding.
- **y0** does do-calculus identification and ID algorithms. It's strong on theory and narrow in scope.
- **pgmpy** is a Bayesian network library that also includes a causal-inference module (backdoor adjustment sets, do-queries).

**Competitors on estimation**
- **DoubleML** is a cleaner and arguably more rigorous double-ML implementation than calling EconML through DoWhy.
- **EconML** technically sits in the same PyWhy family, but it's often used on its own without DoWhy.

**Competitors for quasi-experimental and time-series work (your use case)**
- **CausalPy** handles interrupted time series, synthetic control, difference-in-differences, and regression discontinuity, with Bayesian uncertainty.
- **tfp-causalimpact** does Bayesian structural time series counterfactuals.
- **tigramite** does time-series causal discovery. DoWhy has no native support for lagged or autocorrelated structure, so for your data tigramite and CausalPy are arguably more relevant than DoWhy itself.

 

For your price/purchase time series, a practical stack would be tigramite for structure, CausalPy around price changes, and DoubleML for elasticities. DoWhy is optional, mainly useful for its refuters or if you want an explicit DAG-based identification step.


## Benchmarks

Here's the same list with links. I re-checked the time-series and ACIC links just now; the others are the standard homes for each dataset as far as I know.

## Effect estimation

- **IHDP** and **Twins**. The commonly used preprocessed versions ship with the CEVAE repo: https://github.com/AMLab-Amsterdam/CEVAE
- **LaLonde / NSW Jobs**. Rajeev Dehejia's data page: https://users.nber.org/~rdehejia/nswdata2.html
- **ACIC Data Challenges**
  - 2016: data via the `aciccomp2016` R package: https://github.com/vdorie/aciccomp
  - 2017: write-up of the data-generating processes: https://arxiv.org/abs/1905.09515
  - 2019: https://mcgill.ca/epi-biostat-occh/news-events/atlantic-causal-inference-conference-2019/data-challenge
  - 2022: overview from Mathematica: https://www.mathematica.org/news/mathematica-organizes-the-american-causal-inference-conferences-2022-data-challenge (data site: https://acic2022.mathematica.org). The data contain repeated observations of patients over time, with patients grouped into primary care practices. It comprised 3,400 synthetic datasets: 200 independent realizations of each of 17 data-generating processes.
- **RealCause**: https://github.com/bradyneal/realcause
- **Criteo Uplift**: https://ailab.criteo.com/criteo-uplift-prediction-dataset/
- **Hillstrom email**: https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html

## Causal discovery

- **Tübingen cause-effect pairs**: https://webdav.tuebingen.mpg.de/cause-effect/
- **Sachs protein signaling** and the other classic networks (Asia, Alarm, etc.): https://www.bnlearn.com/bnrepository/
- **Benchpress**: https://github.com/felixleopoldo/benchpress
- **Causal Chambers**: https://github.com/juangamella/causal-chamber

## Time-series causal discovery

- **CauseMe**: https://causeme.uv.es/. It offers ground-truth benchmark datasets that are either synthetic models mimicking real-world challenges or real data whose causal structure is known with high confidence. Method developers upload predicted matrices of causal connections, and the platform scores and ranks them on several performance metrics.
- **CausalTime** (ICLR 2024)
  - Paper: https://arxiv.org/abs/2310.01753
  - Site: https://www.causaltime.cc
  - The pipeline starts from real observations in a given scenario and generates a matching benchmark dataset.
- **CausalRivers** (ICLR 2025)
  - Site: https://causalrivers.github.io
  - Code: https://github.com/CausalRivers/causalrivers
  - Paper: https://arxiv.org/abs/2503.17452
  - River-discharge data from 1,160 stations in eastern Germany and Bavaria, covering 2019–2023 at 15-minute resolution.
- **gCastle** (bundled datasets): https://github.com/huawei-noah/trustworthyAI

## Related tools

- **tigramite**: https://github.com/jakobrunge/tigramite

Sources:
- [CauseMe](https://causeme.uv.es/)
- [CausalTime — ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/0c79d6ed1788653643a1ac67b6ea32a7-Abstract-Conference.html)
- [CausalRivers — arXiv](https://arxiv.org/pdf/2503.17452)
- [CausalRivers — Jena talk abstract](https://indico.rz.uni-jena.de/event/206/contributions/1214/)
- [CausalRivers code — alphaXiv](https://alphaxiv.org/resources/2503.17452v1)
- [Mathematica — ACIC 2022 Data Challenge](https://www.mathematica.org/news/mathematica-organizes-the-american-causal-inference-conferences-2022-data-challenge)
- [BCF & ACIC 2022 — arXiv](https://arxiv.org/pdf/2211.02020)
- [ACIC 2017 DGP note — arXiv](https://arxiv.org/pdf/1905.09515)
- [ACIC 2019 Data Challenge — McGill](https://mcgill.ca/epi-biostat-occh/news-events/atlantic-causal-inference-conference-2019/data-challenge)
