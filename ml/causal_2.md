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
## CHATGPT

Your dataset is a very good example for applying causal inference to time series, particularly for understanding how product prices affect purchases.

The important distinction is:

- Time series forecasting: If product_1 price changes tomorrow, how many purchases do we predict?
- Causal inference: If we deliberately change product_1 price tomorrow, how many additional or fewer purchases will that change cause?

These are different questions. A forecasting model can be accurate without correctly estimating causal effects.

I'll explain how to approach your dataset, which methods are appropriate, and how to implement them in Python.

## 1. Your dataset

Suppose you have daily observations:

| Date  | Visitors | P1 sales | P2 sales | P3 sales | P1 price | P2 price | P3 price |
| ----- | -------- | -------- | -------- | -------- | -------- | -------- | -------- |
| Oct 1 | 1,000    | 100      | 80       | 50       | $10      | $15      | $20      |
| Oct 2 | 1,200    | 115      | 90       | 60       | $10      | $15      | $20      |
| Oct 3 | 1,100    | 140      | 70       | 55       | $8       | $15      | $20      |
| Oct 4 | 1,300    | 160      | 75       | 58       | $8       | $15      | $20      |
| Oct 5 | 1,150    | 130      | 85       | 65       | $9       | $15      | $20      |

Illustrative data, not actual observations.

Notice that on October 3, product_1 price dropped from $10 to $8, and purchases increased.

Question: Did the price reduction cause the increase in purchases?

Not necessarily. Perhaps it was a weekend, advertising increased, or a competitor ran out of stock.

Causal inference attempts to separate these explanations.

## 2. Define the causal questions

With your dataset, we can investigate several causal relationships.

| Question                                                | Business value          |
| ------------------------------------------------------- | ----------------------- |
| Does reducing P1 price increase P1 purchases?           | Price elasticity        |
| Does reducing P1 price decrease P2 purchases?           | Product cannibalization |
| Does P1 price affect P3 purchases?                      | Cross-price effects     |
| Do price changes affect purchases several days later?   | Delayed effects         |
| Do visitors influence purchases independently of price? | Conversion analysis     |
| Which price combination maximizes revenue?              | Pricing optimization    |

The last question is particularly interesting because the optimal price for one product may depend on prices of other products.

## 3. Construct a causal graph

Before selecting statistical methods, specify how you believe the variables influence one another.

Illustrative causal graph (DAG). Actual arrows depend on how the store sets prices and runs promotions. Other factors such as inventory and competitor prices may also matter.

For example:

- Seasonality affects visitors, prices, and purchases.
- Promotions may affect prices, visitor traffic, and purchases.
- Prices affect purchases.
- Visitors affect the number of purchases.

A critical question is whether visitor traffic is independent of price changes. If promotions attract visitors, controlling for visitors may remove part of the total promotional effect. The correct adjustment depends on the causal effect you want to estimate.

## 4. Which causal methods should you use?

There are several approaches, with different assumptions and goals.

| Method                      | What it tells you                                                   | Suitability                |
| --------------------------- | ------------------------------------------------------------------- | -------------------------- |
| Granger causality           | Whether past prices improve prediction of purchases                 | Exploratory                |
| VAR / VARX                  | Dynamic relationships between prices, visitors, and sales           | Useful for modeling        |
| Distributed-lag regression  | Immediate and delayed effects of prices                             | Good starting point        |
| Difference-in-Differences   | Effect of a price intervention compared with an appropriate control | Strong if assumptions hold |
| CausalImpact / BSTS         | Effect of a known intervention using a counterfactual forecast      | Useful for interventions   |
| Double Machine Learning     | Price effects while flexibly adjusting for confounders              | Advanced                   |
| Randomized price experiment | Effect of assigned price changes                                    | Strongest evidence         |

My suggested starting point is distributed-lag regression, followed by intervention analysis if you know when and why prices changed.

One caution: neither Granger causality nor ordinary VAR coefficients establish true causation by themselves.

## 5. Example: estimate price elasticity

Let's start with product_1.

A simple model is:

\\[ \log(Q\_{1,t})=\alpha+\beta\log(P\_{1,t})+ \gamma\log(V_t)+\epsilon_t \\]

Where:

- \\(Q\_{1,t}\\): product_1 purchases on day \\(t\\)
- \\(P\_{1,t}\\): product_1 price
- \\(V_t\\): visitors
- \\(\beta\\): estimated price elasticity

Suppose the fitted coefficient is:

\\[ \beta=-1.5 \\]

This means a 1% increase in price is associated with approximately a 1.5% decrease in purchases, holding visitors constant.

If the model's causal assumptions are satisfied, we can interpret this as a causal price elasticity. Otherwise, it is only a conditional association.

### Python implementation

```
import pandas as pdimport numpy as npimport statsmodels.formula.api as smfdf = pd.read_csv("store.csv", parse_dates=["date"])df = df.sort_values("date")df["log_q1"] = np.log(df["product_1_purchases"])df["log_p1"] = np.log(df["product_1_price"])df["log_visitors"] = np.log(df["visitors"])df["day_of_week"] = df["date"].dt.dayofweekmodel = smf.ols(    "log_q1 ~ log_p1 + log_visitors + C(day_of_week)",    data=df).fit(cov_type="HAC", cov_kwds={"maxlags": 7})print(model.summary())
```

The `HAC` standard errors account for some autocorrelation and heteroskedasticity. They do not eliminate confounding.

This example requires positive values for logged columns. For zero purchase counts, a Poisson model with a log link is often more appropriate.

## 6. Cross-product causal effects

Your dataset becomes more interesting because you have three products.

For example, changing the price of product_1 may influence purchases of product_2 and product_3.

We can estimate a cross-price elasticity model:

\\[ \begin{aligned} \log Q\_{1,t}={}&\alpha+ \beta\_{11}\log P\_{1,t}\\\ &+\beta\_{12}\log P\_{2,t}\\\ &+\beta\_{13}\log P\_{3,t}\\\ &+\gamma\log V_t+\epsilon_t \end{aligned} \\]

Here:

- \\(\beta\_{11}\\): own-price elasticity for product_1
- \\(\beta\_{12}\\): effect of product_2 price on product_1 demand
- \\(\beta\_{13}\\): effect of product_3 price on product_1 demand

Imagine we estimate the following coefficients:

| Purchases ↓ / Price → | P1 price | P2 price | P3 price |
| --------------------- | -------- | -------- | -------- |
| P1 purchases          | -1.5     | +0.4     | +0.1     |
| P2 purchases          | +0.6     | -1.2     | -0.2     |
| P3 purchases          | +0.1     | -0.1     | -0.9     |

Hypothetical elasticity matrix, not calculated from data.

Example: Effect of a 10% increase in P1 price

Approximate predicted percentage changes based on hypothetical elasticity coefficients.

-16%-10%-4%2%8%P1P2P3

In this example, product_1 and product_2 appear to be substitutes: increasing P1 price shifts some purchases toward P2.

This is useful for pricing decisions because maximizing revenue of one product may reduce total store revenue.

Again, the interpretation is causal only if price variation is sufficiently exogenous after appropriate adjustment.

## 7. Include time delays

Purchases may not respond immediately to price changes.

For example:

- Day 0: price reduced
- Day 1: customers notice the new price
- Day 2: customers purchase
- Day 3: effect gradually disappears

A distributed-lag model captures this:

\\[ \log Q_t=\alpha+\sum\_{k=0}^{7}\beta_k\log P\_{t-k} +\gamma\log V_t+\epsilon_t \\]

Here, \\(\beta_0\\) measures the same-day price association, and \\(\beta_1,\ldots,\beta_7\\) measure lagged associations.

Illustrative distributed-lag coefficients

Example response to a price change, not fitted data.

-0.8-0.6-0.4-0.20Day 0Day 1Day 2Day 3Day 4Day 5Day 6Day 7

The sum of the coefficients gives a cumulative lag response under the model assumptions. It does not automatically represent a permanent long-run elasticity.

## 8. The biggest problem: correlation versus causation

Imagine your store manager follows this rule:

> When sales decline, reduce prices.

Then your historical dataset may show:

- Low sales → lower prices
- High sales → higher prices

A naive regression could conclude that higher prices increase sales!

This is reverse causality, or more generally, price endogeneity.

Other important problems include unrecorded promotions, inventory shortages, holidays, and competitor pricing.

To estimate actual causal effects, you need to understand how price decisions were made.

The strongest solution is randomized price changes, where prices are assigned independently of expected demand. If experimentation is impossible, you can consider natural experiments, instrumental variables, or carefully designed quasi-experiments.

Simply adding more sophisticated machine learning does not solve this identification problem.

## 9. Practical workflow for your dataset

I would organize the analysis into these stages:

1. Data exploration

   Check missing days, price-change dates, zero purchases, trends, weekday patterns, and whether products are substitutes.
2. Define the causal estimand

   For example: effect of a 10% P1 price reduction on P1 purchases over the following seven days, and on total revenue.
3. Identify confounders and price-setting rules

   Determine whether prices were randomized, scheduled, promotional, or adjusted in response to demand.
4. Estimate own-price and cross-price effects

   Start with regression including seasonality and appropriate lags. Use stronger causal identification when available.
5. Validate and perform sensitivity checks

   Examine pre-trends, placebo intervention dates, uncertainty intervals, and sensitivity to omitted confounders.
6. Simulate pricing policies

   Only after causal effects are credible, evaluate expected sales and revenue under alternative price combinations.

## 10. Three questions that determine the best causal method

1\. How much historical data do you have?

A few months of daily observations

1–2 years

3+ years

2\. How were product prices changed?

Randomly or experimentally

On a fixed schedule

In response to demand or sales

Unknown or mixed

3\. What is your main objective?

Measure causal effects of prices on purchases

Discover causal relationships between all variables

Optimize total revenue through price changes

Recommend analysis and Python code&#x20;

The second question is especially important. Knowing why and when prices changed is often more valuable for causal inference than having millions of observations.

For your situation—1–2 years of daily data, unknown price-setting mechanism, and the goal of measuring causal effects of prices on purchases—I recommend a two-stage approach:

1. Distributed-lag regression with time-series controls to estimate price elasticity and identify interesting price changes.
2. Interrupted time-series / event-study analysis around major price changes, to investigate whether the effects are consistent with a causal interpretation.

The important limitation is that, with an unknown pricing mechanism, neither method automatically identifies causality. We need evidence that price changes were not driven by unobserved changes in demand.

## 1. The model I recommend

For each product, estimate:

\\[ \begin{aligned} \log E[Q\_{i,t}] ={}& \alpha_i +\sum\_{j=1}^{3}\sum\_{k=0}^{7} \beta\_{ijk}\log P\_{j,t-k}\\\ &+\gamma_i\log V_t +f_i(t)+D_t \end{aligned} \\]

Where:

- \\(Q\_{i,t}\\): purchases of product \\(i\\) on day \\(t\\)
- \\(P\_{j,t-k}\\): price of product \\(j\\), lagged by \\(k\\) days
- \\(V_t\\): number of store visitors
- \\(f_i(t)\\): smooth time trend
- \\(D_t\\): day-of-week and month controls
- \\(\beta\_{ijk}\\): price-response coefficients

I recommend a Poisson GLM with a log link, rather than ordinary log-linear regression, because purchases are counts and may include zeros.

The sum of the price coefficients for each product gives the modeled cumulative response to a sustained price change, under the model's assumptions.

### Why this model?

It accounts for:

- Same-day price effects
- Delayed responses over the next week
- Cross-product substitution
- Visitor traffic
- Weekly and seasonal variation

However, 1–2 years provides only approximately 365–730 observations. With three products and eight lags per price, the model may become overparameterized. I would start with lags 0, 1, 3, and 7, or use a constrained lag structure.

## 2. Python implementation

Assume your CSV contains:

```
date,visitors,q1,q2,q3,p1,p2,p3
```

Here is a first practical model for product_1.

```
        raise ValueError("Prices must be positive")    df[f"log_p{i}"] = np.log(df[f"p{i}"])# Price lagslags = [0, 1, 3, 7]for i in (1, 2, 3):    for lag in lags:        df[f"p{i}_lag{lag}"] = (            df[f"log_p{i}"].shift(lag)        )# Visitors as an offset:# models purchases per visitorif (df["visitors"] <= 0).any():    raise ValueError("Visitors must be positive")df["log_visitors"] = np.log(df["visitors"])price_terms = [    f"p{i}_lag{lag}"    for i in (1, 2, 3)    for lag in lags]formula = (    "q1 ~ " +    " + ".join(price_terms) +    " + C(dow) + C(month) + trend")data = df.dropna(    subset=["q1", "log_visitors"] + price_terms)model = smf.glm(    formula=formula,    data=data,    family=sm.families.Poisson(),    offset=data["log_visitors"]).fit(cov_type="HAC", cov_kwds={"maxlags": 7})print(model.summary())# Cumulative elasticity for P1elasticity = sum(    model.params[f"p1_lag{lag}"]    for lag in lags)print("P1 cumulative elasticity:", elasticity)
```

This implementation models purchases per visitor. The offset fixes the coefficient on log visitors to 1, so it is a conversion-rate model rather than a model of total demand.

If prices influence visitor traffic, the offset model does not capture the full effect of price on purchases. In that case, model visitor traffic separately or estimate total purchases without conditioning on visitors.

Also, the HAC covariance calculation is an approximation; I would check residual autocorrelation and compare results with a time-series block bootstrap.

## 3. Investigate major price changes

The next step is to identify price interventions.

For example:

Illustrative price change and purchase response

Indexed series (first day = 100), hypothetical data

P1 price indexP1 purchases index

75100125150Day 1Day 2Day 3Day 4Day 5Day 6Day 7Day 8

Here the price decreases by 20% on Day 4, followed by increased purchases.

To investigate this event, compare observed purchases against a counterfactual estimate of what would have happened without the price reduction.

A credible counterfactual needs an appropriate control series or assumptions about the pre-intervention demand process. Simply forecasting pre-event sales into the post-event period is not enough to rule out coincident demand shocks.

I would identify price changes of at least 5–10%, then examine each event using a window such as 14 days before and 14 days after. These thresholds are practical starting choices, not statistical requirements.

## 4. Validate the causal interpretation

This is the most important part of the project.

| Validation             | What to investigate                                                 |
| ---------------------- | ------------------------------------------------------------------- |
| Pre-trends             | Were purchases already increasing before prices fell?               |
| Placebo dates          | Does the method find effects on dates without actual price changes? |
| Other products         | Did all products experience the same demand shock?                  |
| Seasonality            | Are results stable after weekday, holiday, and trend adjustments?   |
| Lag sensitivity        | Are results similar using 3, 7, and 14 days?                        |
| Price-setting behavior | Were price reductions responses to unexpectedly weak sales?         |

I would also estimate a model predicting price changes from past purchases and visitor traffic. If previous sales strongly predict price changes, that is evidence that pricing may be endogenous.

It is not proof of endogeneity, but it tells us that naive regression estimates should not be treated as causal.

For each price elasticity estimate, report a confidence interval and compare estimates across specifications. If the estimated effect changes dramatically when adding calendar controls or lagged demand, the causal conclusion is not robust.

## 5. How to obtain stronger causal evidence

With unknown historical price-setting rules, my preferred identification strategy is to look for documented, externally determined price changes.

For example, suppose product_1 price changed because of a supplier-wide pricing update, rather than because the store anticipated lower sales. That may provide a useful natural experiment, although the supplier change could still affect demand through other channels.

If historical price changes cannot be justified as approximately exogenous, I would recommend a controlled experiment:

- Randomly assign different prices across comparable stores or customer groups, where feasible and appropriate.
- Measure purchases and revenue.
- Account for spillovers between products and customer groups.
- Estimate own-price and cross-price effects.

Randomization would give much stronger causal evidence than observational time-series regression.

## 6. What I would deliver from this analysis

The final analytical output should be a price-elasticity matrix, with uncertainty estimates.

| Effect on purchases | P1 price | P2 price | P3 price |
| ------------------- | -------- | -------- | -------- |
| P1 purchases        | -1.4     | +0.3     | +0.1     |
| P2 purchases        | +0.5     | -1.1     | 0.0      |
| P3 purchases        | +0.1     | +0.2     | -0.8     |

Illustrative coefficients only. Actual estimates must be fitted and validated using your data.

If the causal assumptions are credible, this matrix can answer questions such as:

- How much will P1 purchases change if P1 price decreases by 10%?
- Will reducing P1 price cannibalize P2 sales?
- What is the expected effect on total store revenue?

For example, with a causal elasticity of -1.4, a 10% price reduction gives an approximate 14% increase in purchases. The exact constant-elasticity calculation is:

\\[ \frac{Q\_{\text{new}}}{Q\_{\text{old}}} =(0.9)^{-1.4}\approx 1.159 \\]

That is about a 15.9% increase in purchases.

## My recommendation

Use the distributed-lag Poisson model as a baseline observational analysis, not as definitive proof of causation. Then investigate the historical price-change events and try to establish why those changes occurred.

There is one additional question that could substantially change the model design:

Are the three products substitutes (for example, three brands of milk), or unrelated products (for example, milk, bread, and shampoo)?

If they are substitutes, I would consider a joint demand model or a multinomial choice model instead of three independent purchase regressions.

## CLAUDE


Causal analysis on this data comes down to a few concrete questions. 
- How much does the price of a product move its own sales (own-price elasticity)?
- Does raising the price of product 1 push buyers to product 2 (substitution) or pull product 2 down with it (complementarity)?
- And how much of the movement in purchases is just traffic, meaning more visitors bringing more of everything? 

The methods below answer those questions with different levels of rigor and different assumptions.

## 1. Draw the causal graph before touching a model

Write down what you believe causes what. A reasonable starting graph for this data:

- Visitors → purchases of every product
- price_i → purchases_i (own effect), and price_j → purchases_i (cross effects)
- Price → visitors, possibly, if price cuts are advertised
- Calendar (day of week, holidays, season) → visitors, purchases, and often prices
- **Unobserved demand shocks → prices.** This is the big one. If the store raises prices when it expects high demand, or cuts them when sales are slow, prices are **endogenous**. A naive regression can then show higher prices associated with *higher* sales. Every method below either assumes this away or works around it.
--
## The definition

In a regression like

log(Q) = α + β·log(P) + u

the error term u collects everything that affects purchases but isn't in the model: weather, a local event, a competitor's sale, a viral post, a shift in tastes. OLS gives an unbiased estimate of β only if price is uncorrelated with u. Price is **exogenous** when it varies for reasons unrelated to those unmodeled demand factors. It's **endogenous** when it's correlated with them.

When price is endogenous, OLS mixes two things: the causal effect of price on purchases, and the fact that price tends to be set high or low in situations where demand was already going to be high or low. The coefficient no longer measures the first thing alone.

In DAG terms, there's a back-door path. Something unobserved (call it D, a demand shock) affects both price and purchases:

```
        D (unobserved demand shock)
       ↙ ↘
     P  →  Q
```

The regression sees the correlation along both paths, P → Q and P ← D → Q, and can't separate them.

## How it plays out in your store

**Scenario 1: pricing anticipates demand.** Management knows the weekend before a holiday will be busy and raises prices. Sales are high anyway because of the holiday. In the data, high prices coincide with high sales. OLS sees a positive association, which pulls β toward zero or even makes it positive. You'd conclude demand is insensitive to price, or that customers like higher prices. Neither is true.

**Scenario 2: pricing reacts to weak sales.** Sales slump, so the store cuts prices to clear inventory. Sales recover partly, but stay below normal because the slump is still there. Now low prices coincide with mediocre sales. Again the true negative effect is masked, and OLS understates elasticity.

**Scenario 3: the opposite direction.** If the store runs discounts specifically during periods when demand is naturally rising (back-to-school, say), low prices coincide with high sales for reasons that have nothing to do with the discount. OLS then overstates how much the price cut drove sales.

The direction of the bias depends on how prices are actually set, which is why you need to understand the pricing process. The data alone can't tell you.

## The three classic sources of endogeneity

1. **Simultaneity or reverse causality.** Price affects demand, and demand (or expected demand) affects price. This is the scenario above and the most important one for pricing data.
2. **Omitted variables.** Something you didn't measure drives both price and purchases. Examples: a promotion that bundles a price cut with advertising (the ad lifts sales and gets credited to the price), a competitor's actions, or a supplier shortage that raises prices and also reduces stock available to sell.
3. **Measurement error in price.** If the recorded price isn't what customers actually paid (coupons, loyalty discounts, a daily average across intraday changes), the coefficient is biased toward zero.

## Why logs, more data, or better ML don't fix it

- **More data** gives you a more precise estimate of the wrong number. The bias doesn't shrink with sample size.
- **Flexible ML** (random forests, gradient boosting, neural nets) still learns the association between price and sales. It's a better predictor of sales given price as the store sets it. It is not a better estimate of what happens if you *change* the price.
- **Double ML** removes confounding only from variables you observed and fed it. It does nothing about unobserved demand shocks.

The underlying distinction is between prediction and intervention. A model that forecasts sales well can be useless for answering "what if we raise the price 10%?"

## How to deal with it

Each approach finds price variation that isn't driven by demand.

1. **Control for the demand drivers that set prices.** If prices are set based on things you can observe (day of week, holidays, season, recent sales trend), include those in the model. What's left of price variation after conditioning on them may be as good as random. This works only if you know and measure everything the pricing decision used.

2. **Instrumental variables.** Find a variable that moves price but affects purchases *only through* price. In retail, typical instruments are:
   - Wholesale or supplier cost changes. Costs push retail prices up, and customers don't see or care about costs directly.
   - Commodity input prices (coffee beans, wheat, fuel).
   - Prices of the same product in other markets, when those reflect shared cost shocks and not local demand (the Hausman instrument, which comes with its own caveats).

   Two-stage least squares then uses only the part of price variation explained by the instrument.

3. **Exploit price changes made for reasons unrelated to demand.** Examples: a chain-wide repricing decided centrally, a vendor-mandated price change, a policy change, a pricing-system migration. Event-study or interrupted-time-series designs around such changes are often the most credible evidence you can get.

4. **Run an experiment.** Randomized price tests across stores, days, or customer segments make price exogenous by construction. If the business can tolerate it, nothing beats it.

5. **Sensitivity analysis.** If you can't fix the problem, quantify how strong an unobserved confounder would need to be to overturn your conclusion. DoWhy's `add_unobserved_common_cause` refuter and the E-value approach both do this.

## A quick demonstration

This simulation generates data where the true elasticity is −2, but the store raises prices on days with high demand:

```python
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from linearmodels.iv import IV2SLS

rng = np.random.default_rng(0)
n = 1000
demand_shock = rng.normal(0, 0.3, n)           # unobserved by analyst
cost = rng.normal(0, 0.1, n)                   # observed supplier cost shock
log_p = 1.0 + 0.8*cost + 0.5*demand_shock + rng.normal(0, 0.05, n)   # pricing reacts to demand
log_q = 5.0 - 2.0*log_p + demand_shock + rng.normal(0, 0.1, n)       # true elasticity = -2

df = pd.DataFrame(dict(log_p=log_p, log_q=log_q, cost=cost))
print("OLS:", smf.ols("log_q ~ log_p", df).fit().params["log_p"])
print("IV: ", IV2SLS.from_formula("log_q ~ 1 + [log_p ~ cost]", df).fit().params["log_p"])
```

OLS returns roughly −0.2: nearly no price sensitivity, which badly understates the truth. IV, using the cost shock as an instrument, recovers a value close to the true −2. That gap is the endogeneity bias. On real data you'd see only the OLS number, with nothing to warn you it's wrong.

## For your dataset

The first practical step isn't statistical. Find out **how prices are set**. Ask whoever owns pricing:

- Are prices set centrally, or adjusted locally in response to sales?
- Do they change on a fixed schedule, or in reaction to inventory and demand?
- Are price changes bundled with promotions or advertising?
- Is there cost or supplier data that could serve as an instrument?

The answers tell you which of the five approaches is feasible, and how much to trust a plain regression on your CSV.
--

This graph tells you what to control for. 
Calendar is a **confounder**, so it goes in the model.   
Visitors is partly a **mediator** if price drives traffic, so including it changes what you're estimating.   
With visitors in the model you get the effect of price per visitor. 
Without it you get the total effect.

## 2. Prepare the series

- **Logs.** Use log(purchases) and log(price). In a log-log model, the coefficients are elasticities directly.

## What an elasticity is

Price elasticity of demand is the percentage change in quantity divided by the percentage change in price:

ε = (ΔQ / Q) / (ΔP / P)

If ε = −1.5, a 1% price increase reduces purchases by about 1.5%. Elasticities are unit-free, so you can compare them across products with very different prices and volumes. A $1 change means something very different for a $3 item than for a $300 item. A 1% change means the same thing for both.

## Why log-log gives elasticities directly

Take the model:

log(Q) = α + β · log(P) + …

Differentiate both sides. Since d log(x) = dx / x:

dQ / Q = β · dP / P

So β = (dQ/Q) / (dP/P), which is exactly the definition of elasticity. The coefficient is the elasticity without any conversion. Any small change in log(x) is approximately a percentage change in x, and the log-log model expresses everything in those terms.

Compare the other common specifications:

| Model | Coefficient means | Elasticity |
|---|---|---|
| Q = α + βP (linear) | units of Q per $1 of price | β · P/Q, which differs at every point |
| log Q = α + βP (log-linear) | % change in Q per $1 | β · P, which grows with price |
| log Q = α + β log P (log-log) | % change in Q per 1% change in P | β, constant everywhere |

## Applied to your data

```
log(purch_1) = α + β11·log(p1) + β12·log(p2) + β13·log(p3)
             + γ·log(visitors) + day-of-week + holidays + lags + ε
```

How to read each coefficient:

- **β11 (own-price elasticity).** You'd expect it to be negative. If |β11| > 1, demand is elastic: raising the price lowers revenue, because sales fall proportionally more than price rises. If |β11| < 1, demand is inelastic and a price increase raises revenue.
- **β12, β13 (cross-price elasticities).** A positive value means the products are substitutes: when p2 goes up, people switch to product 1. A negative value means they're complements, bought together. A value near 0 means the products are unrelated.
- **γ (traffic elasticity).** γ ≈ 1 means purchases scale proportionally with visitors, so the conversion rate is stable. γ < 1 means extra traffic converts at a lower rate, which is typical when added visitors are less intent on buying.

A useful equivalence: if you fix γ = 1, the model becomes log(purch_1 / visitors), which is log of the conversion rate. You can test whether γ = 1 instead of assuming it.

Fit one equation per product. Together the three equations give you a 3×3 elasticity matrix.

## A worked example

Suppose β11 = −1.8 and β12 = +0.6.

- A 10% price cut on product 1 raises its sales by about 18%.
- A 10% price increase on product 2 raises product 1's sales by about 6%, as some buyers switch.

**For large changes, use the exact form.** The "β × %change" reading is a linear approximation that holds for small changes. The exact effect of a price change by a factor k is k^β − 1:

- Cutting the price by 10%: 0.9^(−1.8) − 1 ≈ +20.9%, not +18%.
- Cutting it by 30%: 0.7^(−1.8) − 1 ≈ +90%, not +54%.

So for promotion-sized changes, compute the exact effect rather than multiplying.

## Practical issues

1. **Zero purchases.** log(0) is undefined. Options, from simplest to best:
   - Aggregate to a level with no zeros, such as weekly.
   - Use log(Q + 1). It's common, but it distorts elasticities when counts are small.
   - Use Poisson regression with a log link, also called PPML (Poisson pseudo-maximum likelihood). It models log E[Q] directly, so the coefficients on log(price) are still elasticities, and it handles zeros naturally. For count data like purchases, this is often the best choice:
     
```python
     smf.glm("purch_1 ~ np.log(p1) + np.log(p2) + np.log(p3) + np.log(visitors) + C(dow)",
             data=df, family=sm.families.Poisson()).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
```

2. **Constant-elasticity assumption.** Log-log assumes the same elasticity at every price, which is often a reasonable approximation over the range of prices you actually observed. Don't extrapolate far outside that range. To check the assumption, add a log(p1)² term, or estimate separately on low-price and high-price periods.

3. **Converting predictions back to units.** exp(predicted log Q) underestimates the expected Q, because E[exp(x)] > exp(E[x]). If you need unit forecasts and not just elasticities, apply a smearing correction (Duan's estimator), or use the Poisson model, which predicts E[Q] directly.

4. **Prices that barely move.** If log(p1) has little variation, β11 will be noisy no matter how you transform the data. The log transform doesn't create information. Check the standard deviation of log(p1) and count how many distinct price changes there were.

5. **Endogeneity still applies.** Logs don't fix the problem that prices may respond to demand. The causal reading of β depends on the identification strategy discussed earlier (controls, instruments, or event designs). The log-log form only makes the estimate interpretable.

## Minimal code

```python
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

df = pd.read_csv("data.csv", parse_dates=["date"])
df["dow"] = df["date"].dt.dayofweek

m = smf.ols(
    "np.log(purch_1) ~ np.log(p1) + np.log(p2) + np.log(p3) + np.log(visitors) + C(dow)",
    data=df,
).fit(cov_type="HAC", cov_kwds={"maxlags": 7})   # Newey-West for autocorrelation

print(m.params.filter(like="np.log"))   # own, cross, and traffic elasticities
print(m.t_test("np.log(visitors) = 1")) # is conversion rate stable w.r.t. traffic?
```

If you share the CSV, I can fit both the OLS and Poisson versions for all three products and give you the full elasticity matrix with confidence intervals.

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


## Data Generators for Causal Modeling

Yes. Several causal libraries include their own data generators, and a few projects exist only to generate benchmark data. Here they are grouped by the kind of data they produce, with the parts most relevant to your retail series called out.

## Time series with a known causal graph (closest to your data)

- **tigramite** (`tigramite.toymodels.structural_causal_processes`). You specify lagged and same-day links, coefficients, and functional forms, and it simulates a multivariate time series with that exact graph. You can also generate random time-series graphs. This is the most direct fit for your case.
  https://github.com/jakobrunge/tigramite
- **CausalTime**. Fits neural models to *real* time series and generates realistic synthetic versions with a derived ground-truth graph. You could feed it your own CSV.
  https://www.causaltime.cc
- **gCastle** (`castle.datasets`). Covers i.i.d. DAG simulation plus a topological Hawkes process simulator for event or alarm sequences.
  https://github.com/huawei-noah/trustworthyAI
- **Lawrence et al., "Data Generating Process to Evaluate Causal Discovery Techniques for Time Series Data."** A framework for generating many time-series datasets with controllable properties (number of variables, length, nonlinearity, confounding) to avoid overfitting to one static benchmark.
  https://arxiv.org/abs/2104.08043

## Treatment-effect estimation (known true effects)

- **DoubleML** (`doubleml.datasets`). Generators from the methods papers: a partially linear model, an interactive (binary treatment) model, a partially linear IV model, and difference-in-differences data. The IV generator is useful for testing endogeneity fixes.
  https://docs.doubleml.org/stable/api/datasets.html
- **DoWhy** (`dowhy.datasets`). `linear_dataset` and related functions generate data with a known effect, common causes, instruments, and effect modifiers, and they return the matching graph. `dowhy.gcm` can also fit a causal model to your data and then sample new data from it.
  https://github.com/py-why/dowhy
- **CausalML** (`causalml.dataset`). Synthetic uplift and heterogeneous-effect generators (the Nie & Wager setups and others).
  https://github.com/uber/causalml
- **RealCause**. Fits generative models to real datasets so simulated outcomes have realistic marginals while the true effect stays known.
  https://github.com/bradyneal/realcause

## Static causal discovery (random DAGs to data)

- **Causal Discovery Toolbox** (`cdt.data.AcyclicGraphGenerator`). Random DAGs with linear, polynomial, sigmoid, or neural-network mechanisms. It's older and less maintained, but still used.
  https://github.com/FenTechSolutions/CausalDiscoveryToolbox
- **pgmpy**. Samples from Bayesian networks, including the classic example networks.
  https://github.com/pgmpy/pgmpy
- **causalAssembly** (Bosch Research). Semi-synthetic manufacturing-line data with a ground-truth graph, built to be more realistic than random DAGs.
  https://github.com/boschresearch/causalAssembly

## What I'd use for your problem

No off-the-shelf generator knows about retail pricing. A small custom simulator built on the tigramite approach, or plain NumPy, is usually best, because you control exactly the properties that make your problem hard:

```python
import numpy as np, pandas as pd

rng = np.random.default_rng(42)
T = 730
t = np.arange(T)
dow = t % 7
season = 0.15*np.sin(2*np.pi*t/365) + 0.10*(dow >= 5)   # yearly + weekend effect
demand = np.zeros(T)                                   # unobserved, autocorrelated demand shock
for i in range(1, T):
    demand[i] = 0.7*demand[i-1] + rng.normal(0, 0.08)

cost = rng.normal(0, 0.05, (T, 3))                     # observable instrument
endog = 0.4                                            # how strongly pricing reacts to demand
log_p = np.log([4.0, 6.0, 9.0]) + cost + endog*demand[:, None] + rng.normal(0, 0.03, (T, 3))

log_visitors = 6.0 + season + 0.8*demand + rng.normal(0, 0.05, T)

E = np.array([[-1.8,  0.5,  0.1],                      # TRUE elasticity matrix (ground truth)
              [ 0.4, -1.2,  0.0],
              [ 0.1,  0.0, -0.9]])
base = np.log([0.05, 0.03, 0.02])                      # baseline conversion rates

rate = np.exp(base + log_p @ E.T + 0.5*demand[:, None])
purch = rng.poisson(np.exp(log_visitors)[:, None] * rate)

df = pd.DataFrame({
    "date": pd.date_range("2024-01-01", periods=T),
    "visitors": np.round(np.exp(log_visitors)).astype(int),
    **{f"purch_{k+1}": purch[:, k] for k in range(3)},
    **{f"price_{k+1}": np.exp(log_p[:, k]).round(2) for k in range(3)},
    **{f"cost_{k+1}": cost[:, k] for k in range(3)},
})
```

The output has the same shape as your CSV, but with a known elasticity matrix `E`. The `endog` knob controls how much pricing chases demand, and the cost columns can serve as instruments. Run OLS, Poisson, IV, DoubleML, and tigramite on it and see which recover `E`. Then increase `endog`, shorten `T`, or reduce the price variation, and watch where each method breaks. That tells you how far to trust the same methods on your real data.
