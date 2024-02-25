### EDA

https://realpython.com/python-for-data-analysis/

https://www.kdnuggets.com/2021/07/single-line-exploratory-data-analysis.html

### ML
https://www.kdnuggets.com/10-github-repositories-to-master-machine-learning

https://github.com/Coder-World04/Data-and-ML-Projects-

https://habr.com/ru/articles/795251/

https://habr.com/ru/articles/795785/

### Outliers detection
https://www.datasciencecentral.com/11-articles-and-tutorials-about-outliers/

### Mamba
https://habr.com/ru/articles/786278/

### Multimodal LLM
https://arxiv.org/abs/2306.13549

Multimodal deep learning
https://arxiv.org/abs/2301.04856 
```
What is AIC and BIC? How these helps in ML Model Selection? 
The AIC can be used to select between the additive and multiplicative Holt-Winters models.
 Bayesian information criterion (BIC) (Stone, 1979) is another criteria for model selection
that measures the trade-off between model fit and complexity of the model.
A lower AIC or BIC value indicates a better fit.

AIC criterion often risk choosing too large a model, whereas BIC often risk choosing too small a model.
In modelling, there's always a risk of either under-fitting, for small n or over-fitting for large n.

Have you chosen the best model?

You may want to check AIC and BIC.
Let's explore what they are and how they can help in finding the optimal ARIMA model 🧵👇
AIC and BIC are both model selection criteria used to compare and rank different models.
They help you choose the best model for your data by evaluating
the trade-off between the fit of the model and its complexity.
1️⃣ AIC (Akaike Information Criterion):
It is used to evaluate the quality of a model by penalizing the number of parameters in the model.
The AIC score is calculated as the negative log-likelihood of the observed data, a
djusted by the number of parameters in the model.
The model with the lowest AIC score is generally considered to be the best model for the given data.
⭐ This score is a good balance between the fit of the model and its complexity,
making it a popular choice for model selection.
2️⃣ BIC (Bayesian Information Criterion):
It's similar to AIC, but it penalizes the number of parameters in the model more heavily.
BIC score is calculated as the negative log-likelihood of the observed data,
adjusted by the number of parameters in the model and the sample size.
The BIC score is intended to balance the fit of the model to the data with the complexity of the model.
⭐ It's often used when the sample size is large, and you want to avoid overfitting.
So, when choosing between models, you can use either AIC or BIC to help you find the best one.
```
