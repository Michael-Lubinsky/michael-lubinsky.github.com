
### Book: Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow: Concepts, Tools, and Techniques to Build Intelligent Systems 3rd Edition

https://www.amazon.com/Hands-Machine-Learning-Scikit-Learn-TensorFlow/dp/1098125975/ 

https://github.com/ageron/handson-ml3

Book with code: Understanding Deep Learning 
https://udlbook.github.io/udlbook/

https://machine-learning-with-python.readthedocs.io/

https://sebastianraschka.com/notebooks/ml-notebooks/

https://eli.thegreenplace.net/2025/notes-on-implementing-attention/

https://www.kaggle.com/discussions/getting-started/390402

ML System design 
https://github.com/alirezadir/Machine-Learning-Interviews/blob/main/src/MLSD/ml-system-design.md

https://habr.com/ru/articles/900788/  ML project setup


Ads clicks prediction

https://github.com/alirezadir/Machine-Learning-Interviews/blob/main/src/MLSD/mlsd-ads-ranking.md

### ML

Book: https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/copy.html

https://github.com/HandsOnLLM/Hands-On-Large-Language-Models

https://news.ycombinator.com/item?id=43586073

https://habr.com/ru/articles/895332/ Bayes

https://habr.com/ru/companies/alfa/articles/895002/ uplift

https://habr.com/ru/companies/wunderfund/articles/894100/

https://vectorfold.studio/blog/transformers

https://arxiv.org/abs/2206.13446 Pen and Paper Exercises in Machine Learning

https://riverml.xyz/latest/ Online machine learning in Python

https://www.kdnuggets.com/10-github-repositories-to-master-machine-learning

https://github.com/Coder-World04/Data-and-ML-Projects-

https://habr.com/ru/articles/795251/ Типичные задачи аналитика. Часть 2. А есть ли тренд?

https://habr.com/ru/articles/795785/ 

https://habr.com/ru/articles/897946/ Error backpropagation
https://eli.thegreenplace.net/2025/reproducing-word2vec-with-jax/

https://habr.com/ru/companies/yadro/articles/896362/  Свертка 


### ML
https://eli.thegreenplace.net/2024/ml-in-go-with-a-python-sidecar/


### Stat rethinking
https://xcelab.net/rm/statistical-rethinking/  
https://www.goodreads.com/book/show/26619686-statistical-rethinking  
https://github.com/rmcelreath/stat_rethinking_2024
 

### Probabilistic programming with NumPy powered by JAX for autograd and JIT compilation to GPU/TPU/CPU.
https://news.ycombinator.com/item?id=42156126  
https://num.pyro.ai/en/stable/ 
https://github.com/pyro-ppl/numpyro  

### T-test, Welch test
https://habr.com/ru/companies/X5Tech/articles/896182/

### What is desriptive measure of association

https://tracyrenee61.medium.com/statistics-interview-question-what-are-descriptive-measures-of-association-23ee9c7612b5


### Stat distributions in python
https://medium.com/data-bistrot/log-normal-distribution-with-python-7b8e384e939e
https://medium.com/data-bistrot/bernoulli-distribution-with-python-0416e196e752 
https://medium.com/data-bistrot/poisson-distribution-with-python-791d7afad014
https://medium.com/data-bistrot/bionomial-distribution-with-python-05d4a1725811
https://medium.com/data-bistrot/uniform-and-normal-statistical-distribution-in-python-6d07fd5fc552

### EDA

https://realpython.com/python-for-data-analysis/

https://www.kdnuggets.com/2021/07/single-line-exploratory-data-analysis.html

### Self-attention implementation

https://eli.thegreenplace.net/2025/notes-on-implementing-attention/

### Automatic differentiation

https://huggingface.co/blog/andmholm/what-is-automatic-differentiation

https://habr.com/ru/articles/874592/

https://eli.thegreenplace.net/2025/reverse-mode-automatic-differentiation/

MLFlow https://habr.com/ru/companies/pgk/articles/904078/

### Outliers and Anomaly  detection

https://leftjoin.ru/blog/data-analysis/outliers-detection-in-python/

https://talkpython.fm/episodes/show/497/outlier-detection-with-python

алгоритмы HBOS и ECOD,  и их реализации в библиотеке PyOD: 

https://habr.com/ru/companies/garda/articles/895148/

https://medium.com/pythoneers/hidden-gems-in-outlier-detection-3-powerful-lesser-known-methods-4386ac9ecff7 

https://www.datasciencecentral.com/11-articles-and-tutorials-about-outliers/


https://github.com/alteryx/featuretools Feature Engineering

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
