## Recommendation systems

<https://testmysearch.com/my-books.html>

<https://www.youtube.com/watch?v=bIc58LpxLrs&list=PL5J4s9eyVap9qX1CePqEPGT_aGX0MvpnI>


<https://habr.com/ru/companies/ru_mts/articles/947710/>

<https://habr.com/ru/companies/odnoklassniki/articles/532388/>

<https://pll.harvard.edu/course/data-science-building-machine-learning-models>

<https://habr.com/ru/articles/974598/> recsys and search books

<https://www.vorillaz.com/netflix-but-better>

<https://habr.com/ru/companies/otus/articles/950650/>

<https://habr.com/ru/articles/951694/>

<https://habr.com/ru/articles/951428/>

**LightFM** is a **Python library** for building **hybrid recommendation systems**. It combines:

- **Collaborative filtering** (e.g., matrix factorization)
- **Content-based filtering** (e.g., user and item metadata)
- Into one **flexible model** using **latent factor models** and **stochastic gradient descent**.

---

## 🔍 Key Features of LightFM

| Feature | Description |
|--------|-------------|
| ✅ **Hybrid modeling** | Uses both interaction data and metadata (user/item features) |
| 🧠 **Latent factor model** | Learns embeddings for users and items |
| ⚙️ **Loss functions** | Supports **ranking** (e.g., BPR), **classification** (e.g., logistic), and **regression** |
| 🚀 **Fast** | Optimized Cython backend, fast for moderate-scale datasets |
| 🧩 **Flexible input** | Accepts sparse matrices (e.g., CSR) for interactions and features |

---

## 📦 Installation

```bash
pip install lightfm
```


Perfect for situations where:
- You have implicit feedback (e.g., clicks, watches, likes)
- You want to leverage metadata (e.g., genres, age group, device type)
- You want ranking-focused recommendations

📌 Example Code
```python
from lightfm import LightFM
from lightfm.data import Dataset

# Create dataset
dataset = Dataset()
dataset.fit(users, items)
dataset.fit_partial(users, items, user_features=user_features, item_features=item_features)

# Build interaction matrix (sparse)
(interactions, weights) = dataset.build_interactions(train_data)

# Build feature matrices (optional)
user_features_matrix = dataset.build_user_features(user_features)
item_features_matrix = dataset.build_item_features(item_features)

# Train model
model = LightFM(loss='warp')  # 'warp' = Weighted Approximate-Rank Pairwise loss
model.fit(interactions, user_features=user_features_matrix,
          item_features=item_features_matrix, epochs=10, num_threads=4)
```
🔬 Loss Function Options
| Loss         | Purpose                                               |
| ------------ | ----------------------------------------------------- |
| `'logistic'` | For binary classification                             |
| `'bpr'`      | Bayesian Personalized Ranking                         |
| `'warp'`     | Weighted Approximate-Rank Pairwise (best for ranking) |
| `'warp-kos'` | Variant of WARP that reduces sampling bias            |

🤔 When to Use LightFM
Use it if you:
- Want to combine collaborative filtering and content-based filtering
- Have sparse implicit data (e.g., movie watches, clicks)
- Need fast prototyping for recommender systems

Avoid it for:

Large-scale production systems (>10M users/items): prefer TensorFlow Recommenders or PyTorch
Complex sequential or context-aware models


## 🔄 Comparison: LightFM vs TensorFlow Recommenders vs PyTorch Recommender Systems

| Feature                         | LightFM                            | TensorFlow Recommenders (TFRS)        | PyTorch-based Recommenders (e.g., RecBole, TorchRec)     |
|---------------------------------|------------------------------------|----------------------------------------|-----------------------------------------------------------|
| 🚀 Core Technology              | Python + Cython                    | TensorFlow / Keras                     | PyTorch                                                   |
| 📦 Installation Size            | Small (~lightweight)              | Heavy (TensorFlow required)           | Heavy (PyTorch + extra libs)                              |
| 🧠 Model Type                   | Matrix factorization (hybrid)      | Any deep model (e.g., DNN, two-tower) | Any deep model (DNN, GNN, attention, etc.)                |
| 🔍 Use Case Focus               | Quick hybrid recommendations       | Large-scale production ML pipelines   | Custom deep architectures, research                       |
| 🧩 Feature Handling             | Item/user metadata supported       | Full flexibility with features        | Full flexibility, incl. session-based, context-aware      |
| 📈 Loss Functions               | Logistic, BPR, WARP, WARP-kos      | Any TF loss (e.g., cross-entropy, MSE)| Any PyTorch loss (triplet, margin ranking, etc.)          |
| 🛠 Custom Model Architecture    | ❌ (Fixed model structure)         | ✅ (Fully customizable)               | ✅ (Fully customizable)                                   |
| 🧪 Evaluation Tools             | Basic ranking metrics              | Extensive support via TF pipelines    | Depends on framework (e.g., RecBole has good tools)       |
| 💻 Scalability                 | Medium (~10M users/items)         | High (GPU, distributed TF supported)  | High (GPU, distributed training via PyTorch)              |
| ⚙️ Training Speed              | Fast (single machine)              | Slower, needs tuning                  | Depends on model complexity                               |
| 📚 Documentation               | Good, simple examples              | Extensive, with Colab notebooks       | Varies by framework (RecBole, TorchRec, etc.)             |

---

 

### When to Use LightFM:
- You want quick hybrid recommendations with minimal setup.
- Data fits in memory and you prefer simple pipelines.
- No need for complex model customization.

### When to Use TensorFlow Recommenders:
- You already use TensorFlow.
- You want end-to-end pipelines (data → training → serving).
- You need GPU acceleration or scalable deployment.

### When to Use Recommenders:
- You prefer PyTorch ecosystem.
- You're doing research or experimenting with cutting-edge models (GNNs, attention).
- You need full flexibility in architecture.

## Clickstream analysis

Clickstream data (e.g., `user_id`, `item_id`, `timestamp`, `event_type`) offers rich insights into user behavior. Here are the key types of analysis:

---

### 1. 🎬 Content Engagement Analysis
- **Watch duration vs. content length** → Are users completing content?
- **Drop-off time** → When do users stop watching or interacting?
- **Skimming behavior** → Multiple short sessions on the same content.


### 2. 🧭 Navigation Patterns
- **Page path sequences** → What path users take through a product or site.
- **Session flow modeling** → Sequence modeling using Markov Chains, LSTMs.
- **Backtracking** → Clicking back and forth might indicate confusion.

---

### 3. 🔁 Repetition and Rewatching
- Rewatch frequency → Users repeating the same video/article.
- Re-engagement windows → How often users return to the platform.
- Binge-watching detection → Sessions with many back-to-back views.

---

### 4. ⏱ Temporal Behavior
- **Time-of-day usage** → Morning vs. evening behavior.
- **Day-of-week effects** → Weekday vs. weekend habits.
- **Session duration and frequency** → Correlated with engagement or churn.

---

### 5. 📊 Segment-Based Analysis
- **User cohorts** → Group users by signup date, behavior type, or features.
- **Behavioral clusters** → Using clustering (e.g., KMeans) to group users:
  - Explorers vs. loyalists
  - Skimmers vs. deep readers
  - Short vs. long session users

---

### 6. 💥 Anomaly Detection
- **Bot detection** → Rapid fire clicks, impossible navigation paths.
- **Shared accounts** → Multiple geographic locations within short intervals.
- **Content misuse** → Users skipping too fast or scraping.

---

### 7. 🧠 Predictive Modeling
- **Churn prediction** → Will a user stop using the service soon?
- **Next-item prediction** → Recommender systems.
- **Session success prediction** → Will a session lead to a conversion?

---

### 8. 🧩 User Intent Inference
- **Exploration vs. goal-directed** behavior
- **Search abandonment** → Sessions where no meaningful action followed a search
- **Intent drift** → Changing interests during a session

---

### Tools and Techniques:
- Sequence models (e.g., RNN, Transformers)
- Clustering (e.g., DBSCAN, HDBSCAN)
- Time series analysis
- Anomaly detection (e.g., Isolation Forest)
- Recommendation systems (e.g., LightFM, deep models)


### It is possible build a machine learning pipeline for several goals:
 -  behavior modeling, 
 -  recommendation, 
 -  anomaly detection, or 
 -  churn prediction.

###  ML Pipeline Components
#### 1. Data Preprocessing
Feature engineering:

watch_duration = end_watch_time - start_watch_time

hour_of_day, day_of_week (from start_watch_time)

Session-based features (e.g., # movies watched per day/user)

User/movie-level aggregations:

Average watch time per user

Popularity of movies (views/movie)

Completion rate: watch_duration / movie_duration

#### 2. Possible Labels / Targets (for supervised ML)
Depending on your goal:

Binary label: Did the user finish >80% of movie? (yes/no)

Regression: Predict expected watch time

Clustering/unsupervised: Group similar watch patterns

Anomaly detection: Detect bots or abnormal viewing behavior

#### ML Models Based on Task

| Task                        | Model                                                                      | Notes                                                 |
| --------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------- |
| 🎯 **Recommendation**       | Matrix factorization, SVD, LightFM, **Deep learning (e.g., Two-Tower NN)** | PyTorch or TensorFlow recommended if using embeddings |
| ⏳ **Watch time prediction** | RandomForest, XGBoost, LightGBM                                            | Fast and interpretable                                |
| 🚨 **Anomaly detection**    | Isolation Forest, One-Class SVM, Autoencoders                              | Isolation Forest easiest to deploy                    |
| 📊 **User segmentation**    | K-Means, DBSCAN, PCA → K-Means                                             | For marketing or personalization                      |
| 🎬 **Churn prediction**     | Logistic Regression, XGBoost                                               | Based on recent activity trends                       |

#### Deep learning vs Classical ML

| Approach                                       | When to Use                                                                      |
| ---------------------------------------------- | -------------------------------------------------------------------------------- |
| **Deep Neural Networks** (e.g., PyTorch)       | Large-scale data, many categorical variables (user/movie IDs), embeddings needed |
| **Classic ML** (XGBoost, RF, Isolation Forest) | Tabular data, faster iterations, better interpretability                         |

If you're starting and have tabular data + moderate scale, prefer:

XGBoost / LightGBM for prediction tasks

Isolation Forest for anomalies

Scikit-learn Pipelines for reproducibility

#### Use PyTorch or TensorFlow if:

You're building deep recommendations
You have many sparse IDs (users, movies, devices)
You need sequence modeling (e.g., RNN for session behavior)

#### Code example
```puython
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

num_features = ['watch_duration', 'hour_of_day']
cat_features = ['user_id', 'movie_id']

preprocessor = ColumnTransformer([
    ('num', StandardScaler(), num_features),
    ('cat', OneHotEncoder(handle_unknown='ignore'), cat_features)
])

pipeline = Pipeline([
    ('preprocess', preprocessor),
    ('model', RandomForestRegressor())
])
```
