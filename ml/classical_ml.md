## Classical ML (no deep learning)

<https://mlbook.dataschool.io/>

<https://habr.com/ru/articles/1037110/> ML без воды: от базы до Attention. Часть 2: Линейная регрессия

Precision, Recall, F-score, ROC-AUC
<https://habr.com/ru/articles/1038730/> ML без воды: от базы до Attention. Часть 5: Метрики качества

<https://habr.com/ru/articles/1040682/> ML без воды: от базы до Attention. Часть 6: Логистическая регрессия

<https://habr.com/ru/articles/1041488/>  ML без воды: от базы до Attention. Часть 7: SVM и SGD

<https://habr.com/ru/articles/1042260/> ML без воды: от базы до Attention. Часть 8: Kernel Trick

<https://habr.com/ru/articles/1044364/> ML без воды: от базы до Attention. Часть 9: Дерево решений

<https://habr.com/ru/articles/1045016/>  ML без воды: от базы до Attention. Часть 10: Бэггинг и случайный лес

<https://habr.com/ru/articles/1061392/> cross - entropy

scikit-learn
<https://habr.com/ru/articles/1031044/>

### XGBoost Lightgbm GatBoost Градиентный бустинг

<img width="1080" height="1386" alt="image" src="https://github.com/user-attachments/assets/e7f4b274-f4aa-469b-a908-8489ca3376e3" />


<https://habr.com/ru/articles/1047130/> ML без воды: от базы до Attention. Часть 11: Градиентный бустинг

XGBoost, LightGBM, and CatBoost are **gradient boosting algorithms**, used primarily for **supervised learning** (classification and regression), not clustering.

| Algorithm | Type | Typical use |
|---|---|---|
| XGBoost | Gradient boosted decision trees | Classification, regression, ranking |
| LightGBM | Gradient boosted decision trees | Same — optimized for speed/large datasets |
| CatBoost | Gradient boosted decision trees | Same — strong native categorical feature handling |

**Key distinction:**

- **Clustering** = unsupervised — groups data points by similarity without labels (e.g., K-Means, DBSCAN, hierarchical clustering, Gaussian Mixture Models)
- **Gradient boosting** = supervised — learns to predict a target variable (label) from features, by sequentially building an ensemble of decision trees, each correcting the errors of the previous ones

**Common applications for XGBoost/LightGBM/CatBoost:**
- Fraud detection (classification)
- Price/demand forecasting (regression)
- Click-through-rate prediction (classification)
- Risk scoring, churn prediction, ranking systems (search/recommendation)

If you need clustering, the standard options are:
- **K-Means** — fast, simple, requires specifying number of clusters
- **DBSCAN** — density-based, finds arbitrary-shaped clusters, no need to specify cluster count
- **Hierarchical clustering** — builds a tree of clusters (dendrogram)
- **Gaussian Mixture Models (GMM)** — soft/probabilistic clustering

If your use case involves vehicle telemetry  boosting algorithms could be useful for predicting things like battery degradation or failure risk (supervised), while clustering could group vehicles/drivers by usage patterns (unsupervised).
<https://kishanakbari.medium.com/xgboost-vs-catboost-vs-lightgbm-a-guide-to-boosting-algorithms-47d40d944dab>

<https://apxml.com/posts/xgboost-vs-lightgbm-vs-catboost>

## Clustering

<https://habr.com/ru/articles/1046974/>

<https://habr.com/ru/articles/1046942/>

## Gaussian Process 

<https://kelvinpaschal.com/blog/kernel-functions/>  
<https://distill.pub/2019/visual-exploration-gaussian-processes/>
<https://www.youtube.com/watch?v=zquAOOjG2iI>

<https://www.linkedin.com/pulse/how-linear-classifier-gets-993-mnist-without-learning-taras-tsugrii-1cruc/>

<https://www.youtube.com/playlist?list=PL4_hYwCyhAvZA-AvUKhB1lcV1kDaamFgY>

<https://www.youtube.com/playlist?list=PL4_hYwCyhAvYwERTJvDSNRMMN8bcdtzia>

<https://habr.com/ru/articles/1037892/>

<https://habr.com/ru/articles/804605/>

<https://habr.com/ru/articles/926398/>

<https://leanpub.com/TOBoML2>  The Orange Book of Machine Learning - Green edition  $15

<https://machine-learning-with-python.readthedocs.io>

<https://medium.com/@guyko81/stop-predicting-numbers-start-predicting-distributions-0d4975db52ae>

Book: Information Theory, Inference, and Learning Algorithms. David J.C. MacKay

<https://www.inference.org.uk/itprnn/book.pdf>


Josh Starmers books  
<https://www.youtube.com/c/joshstarmer> 
<https://statquest.org/>


<https://habr.com/ru/companies/yandex_praktikum/articles/1001402/> Linear Models

<https://habr.com/ru/articles/1015102/> linear regression

<https://news.ycombinator.com/item?id=47204964>

<https://r2d3.us/visual-intro-to-machine-learning-part-1/>

<https://r2d3.us/visual-intro-to-machine-learning-part-2/>

<https://p.migdal.pl/interactive-machine-learning-list/>

<https://visxai.io/> has a bunch more too — see the Hall of Fame section at the bottom for some of the highlights.
I also made a dozen of these a couple years ago, my two favorites:

- <https://pair.withgoogle.com/explorables/fill-in-the-blank/>

- <https://pair.withgoogle.com/explorables/grokking/>
- <https://growingswe.com/blog>

- <https://ciechanow.ski/archives/>

- <https://mlu-explain.github.io/>

- <https://seeing-theory.brown.edu/index.html>

- <https://svg-tutorial.com/>

- <https://www.lumafield.com/scan-of-the-month/health-wearables>

### Decision Trees

<https://mlu-explain.github.io/decision-tree/>

<https://github.com/mljar/supertree>

<https://www.youtube.com/playlist?list=PLgPbN3w-ia_PeT1_c5jiLW3RJdR7853b9>

### ROC

he ROC curve (Receiver Operating Characteristic) shows how well a binary classifier separates classes across different thresholds. It plots True Positive Rate (Recall) on the Y-axis, and False Positive Rate on the X-axis Each point represents a different threshold.

It helps evaluate the trade-off between sensitivity and specificity, where  
- Sensitivity = True Positive / (True Positive + False Negative) or how well model detect positive  
- Specificity = True Negative / (True Negative + False Positive) how well model detects negatives  

A model that’s closer to the top-left corner is better.

Typical Metric derived from it are - 𝐀𝐔𝐂 (𝐀𝐫𝐞𝐚 𝐔𝐧𝐝𝐞𝐫 𝐭𝐡𝐞 𝐂𝐮𝐫𝐯𝐞). 
It ranges from 0.5 (random) to 1.0 (perfect). Higher AUC means better overall classification ability.

For example, 
In a house price model predicting if a house will sell above $500k (yes/no), the ROC curve helps us choose a threshold for the predicted probability that balances catching most “yes” cases (true positives) without too many false alarms (false positives).

 
ROC is a threshold-independent way to assess classification performance

<img width="726" height="576" alt="image" src="https://github.com/user-attachments/assets/171c55f1-ad58-4d2f-95ee-487c5a546d94" />

<img width="1080" height="1424" alt="image" src="https://github.com/user-attachments/assets/26e0fb3c-23ed-4f01-b825-919caa5fb44d" />
