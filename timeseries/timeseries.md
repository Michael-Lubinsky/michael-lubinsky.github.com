## Time Series

Time-series forecasting.
Starting with the statistical foundations.

Before transformers and pretrained models, people already had a lot of algorithms for forecasting.

Start with simple forecasts:
→ historical average
→ last observed value
→ last value from the same season

These are still stroing baselines. A complicated model needs to justify why we need it.

1927–1938: autoregression and innovations.

Yule modelled observations using previous values and a random disturbance.

Wold later provided a theoretical representation of stationary processes using a deterministic component and accumulated innovations.

Not the same contribution. One is a modelling approach, the other is a theoretical foundation.

1950s–1960: exponential smoothing.

Estimate the current level, giving more weight to recent observations.

Then extend what we track:
→ SES: level
→ Holt: level + trend
→ Holt-Winters: level + trend + seasonality

For monthly demand, “what is the current level?” and “what usually happens in December?” are different questions.

1960: Kalman filter.

The underlying state is not directly observed. We estimate it from noisy measurements.
Predict the state → receive an observation → correct the estimate → repeat.

1970: Box–Jenkins.

ARIMA becomes part of a systematic workflow:
→ identify a model
→ estimate it
→ check residuals
→ revise when needed

Difference the series if needed, then model dependence through lagged values and innovations.

And MA here does not mean taking a rolling average of the observations.

1980: VAR in macroeconomics.

Instead of modelling one series alone, let several variables depend on their own and each other’s past values.

But predictive dependence does not automatically establish causality.

1982 / 1986: ARCH and GARCH.

A different target: changing conditional variance.

The expected value can stay similar while uncertainty changes a lot. Predicting the level and predicting volatility are not the same task.

1985: damped trend.

A rising trend does not need to continue at the same rate forever.

Reduce its contribution as the forecast horizon grows.

1990: STL.

Separate trend, seasonality and remainder using local smoothing.

But decomposition is not yet a forecast. We still need to decide how to project those components forward.


Its to ask what each method assumes:
```
→ does the recent past matter more?
→ is there a changing trend?
→ does a seasonal pattern repeat?
→ do other variables help?
→ is uncertainty itself changing?
```

Later neural models change how we learn these patterns. They do not make these questions disappear.

### Summary:
```
smoothing: update components.
ARIMA: model temporal dependence.
state space: estimate hidden states.
VAR: model several series together.
ARCH/GARCH: model changing variance.
STL: separate components before forecasting.
```
<img width="800" height="999" alt="image" src="https://github.com/user-attachments/assets/6df27388-eb78-4bf4-8d0d-dac4ba229b03" />

Book: <https://www.amazon.com/Advanced-Forecasting-Python-Mastering-Techniques-ebook/dp/B0G3VGKWHJ> 

<https://leanpub.com/mastering_modern_time_series_forecasting>

<https://tabicl.readthedocs.io/en/latest/tutorials/time_series_forecasting.html>

<https://suzyahyah.github.io/machine%20learning/2026/06/27/trouble-with-time-series.html>

<https://machinelearningmastery.com/the-2026-time-series-toolkit-5-foundation-models-for-autonomous-forecasting/>

<https://habr.com/ru/articles/1078544/> TimesFM-3 (Time Series Foundational Model).

<https://github.com/RussellSB/pytrendy>


<https://habr.com/ru/companies/alfa/articles/1085676/>

<https://habr.com/ru/articles/1066070/> Anomaly in time series - WhyTrend

<https://habr.com/ru/articles/1066000/> Anomaly in time series - WhyTrend

<https://machinelearningmastery.com/transformer-vs-lstm-for-time-series-which-works-better/>

<https://github.com/predict-idlab/plotly-resampler>

<https://habr.com/ru/companies/garage8/articles/920226/> Anomaly detection, Z-score with SQL

<https://machinelearningmastery.com/time-series-forecasting-methods-in-python-cheat-sheet>

<https://github.com/business-science/pytimetk>

<https://habr.com/ru/companies/otus/articles/1003098/>  Darts

<https://timecopilot.dev/>

<https://habr.com/ru/articles/953154/>  Как ИИ-агенты учатся работать с временными рядами

<https://habr.com/ru/companies/magnit/articles/985864/>  делаем прогноз для 200+ рядов с библиотекой Etna

https://habr.com/ru/articles/949062/ Chronos и AutoGluon-TimeSeries — мощный инструмент прогнозирования временных рядов

diff-in-diff

https://autognosi.medium.com/advanced-techniques-and-practical-aspects-in-anomaly-detection-for-time-series-f9b30e4e8760

https://habr.com/ru/companies/otus/articles/919156/

https://habr.com/ru/companies/otus/articles/918832/

https://habr.com/ru/companies/sberbank/articles/954636/

https://habr.com/ru/companies/otus/articles/894754/  TSFresh

https://github.com/MatthewK84/Time-Series-Textbooks

Monte Carlo
https://medium.com/dataman-in-ai/monte-carlo-simulation-for-time-series-probabilistic-forecasts-e04a7d29c9b3

https://medium.com/the-forecaster/the-complete-introduction-to-time-series-classification-in-python-6af967b16dc9

https://medium.com/data-science/5-must-know-techniques-for-mastering-time-series-analysis-a23ccf4d053a

https://python.plainenglish.io/feature-engineering-for-time-series-forecasting-in-python-7c469f69e260

https://habr.com/ru/articles/899408/  Gaps in TS

### Outliers and Anomaly  Detections

<https://habr.com/ru/companies/yandex/articles/1035520/>

<https://habr.com/ru/companies/otus/articles/918832/>

https://medium.com/top-python-libraries/how-to-identify-outliers-of-your-data-with-python-codes-e9e53e912f8c

https://talkpython.fm/episodes/show/497/outlier-detection-with-python

https://medium.com/data-science/the-ultimate-guide-to-finding-outliers-in-your-time-series-data-part-1-1bf81e09ade4

https://towardsdatascience.com/the-ultimate-guide-to-finding-outliers-in-your-time-series-data-part-2-674c25837f29 

https://towardsdatascience.com/hands-on-time-series-anomaly-detection-using-autoencoders-with-python-7cd893bbc122/

https://levelup.gitconnected.com/anomaly-detection-in-time-series-data-with-python-5a15089636db

https://medium.com/chat-gpt-now-writes-all-my-articles/anomaly-detection-on-time-series-with-mset-sprt-in-python-30a8ae039ce9

### Matrix profile
<https://github.com/TDAmeritrade/stumpy>  Matrix profile

<https://aneksteind.github.io/posts/2025-03-26.html> Matrix profile

Time Series Aggregation with pandas

<https://kapilg.hashnode.dev/time-series-aggregation-in-pandas>

https://towardsdatascience.com/comprehensive-time-series-exploratory-analysis-78bf40d16083

https://medium.com/data-science/how-reliable-are-your-time-series-forecasts-really-18a1106d8ee1

https://towardsdatascience.com/handling-gaps-in-time-series-dc47ae883990

https://medium.com/data-science-collective/hands-on-irregular-time-series-for-predictive-modeling-part-ii-e5070e721bd6

https://news.ycombinator.com/item?id=39350866

https://www.youtube.com/watch?v=XhptIhtfq2w

https://medium.com/data-science-collective/18-libraries-for-time-series-feature-extraction-f12fd1bae738

https://medium.com/data-science-collective/enhancing-time-series-forecasting-with-dynamic-weighted-trees-8dad9aeae112

### Merlion 
https://github.com/salesforce/Merlion#comparison-with-related-libraries

https://habr.com/ru/companies/sportmaster_lab/articles/792318/


https://www.youtube.com/watch?v=jo12CWZ00Lo&list=PLGVZCDnMOq0rLLb519Ah3EntCUAAHPnfU
