# Machine Learning Tools in Databricks

## Core ML Capabilities

- **MLflow (integrated)**: For experiment tracking, model packaging, model registry, and deployment.
- **Databricks AutoML**: Automatically explores and builds baseline models using best practices.
- **Databricks Feature Store**: Manages and shares ML features across teams and notebooks.
- **Databricks ML Runtime**: Pre-configured environment with popular ML/DL libraries (scikit-learn, PyTorch, TensorFlow, Spark MLlib).
- **Model Serving**: Deploy models directly as REST APIs for real-time inference.
- **Hyperparameter Tuning**: Distributed tuning with Hyperopt or custom frameworks.
- **MLflow Integration**: Works with AWS SageMaker, Azure ML, and other MLOps platforms.

### MLflow  

MLflow is an **open-source platform** for managing the end-to-end machine learning lifecycle.   
It was developed by Databricks and integrates tightly with the Databricks environment but is also standalone and cloud-agnostic.

### MLflow Core Components

### 1. **MLflow Tracking**
Tracks experiments to log and compare parameters, metrics, tags, and artifacts.

- **Logged Items**:
  - `parameters`: input values used in training (e.g., learning rate)
  - `metrics`: performance scores (e.g., accuracy, loss)
  - `artifacts`: output files (e.g., model files, plots)
  - `source`: git commit, notebook, script
- **Usage**:
  - Code-based: `mlflow.log_param()`, `mlflow.log_metric()`, `mlflow.log_artifact()`
  - UI: visualize experiment runs and comparisons
  - REST API & CLI for automation

---

### 2. **MLflow Projects**
Encapsulates ML code in a **reproducible format** using a standardized project structure.

- **Key files**:
  - `MLproject`: defines environment and entry points
  - `conda.yaml` / `requirements.txt`: declares dependencies
- **Benefits**:
  - Portable, version-controlled training
  - Can run locally, remotely, or in containers

---

### 3. **MLflow Models**
Defines a **standard format** for packaging machine learning models for diverse frameworks.

- **Supports multiple flavors**:
  - `python_function`: universal interface
  - `sklearn`, `pytorch`, `tensorflow`, `xgboost`, etc.
- **Save model**: `mlflow.sklearn.log_model()` or `mlflow.pyfunc.log_model()`
- **Load model**: `mlflow.pyfunc.load



# 🧪 Full Example of a Machine Learning Project with MLflow

This is a complete, reproducible machine learning project using **MLflow** with **Scikit-learn** on a classification task.   
The project structure, code, and logging features are fully integrated.

---

## 📁 Project Structure
```
mlflow_project_example/
├── MLproject
├── conda.yaml
├── train.py
├── data/
│ └── iris.csv
```

---

## 🧾 MLproject File

```yaml
name: iris-classifier

conda_env: conda.yaml

entry_points:
  main:
    parameters:
      n_estimators: {type: int, default: 100}
      max_depth: {type: int, default: 5}
    command: >
      python train.py
        --n_estimators {n_estimators}
        --max_depth {max_depth}
```
conda.yaml
```yaml
name: iris-env
channels:
  - defaults
dependencies:
  - python=3.10
  - scikit-learn
  - pandas
  - mlflow
```
train.py
```python
import argparse
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import mlflow
import mlflow.sklearn

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("--n_estimators", type=int, default=100)
parser.add_argument("--max_depth", type=int, default=5)
args = parser.parse_args()

# Load data
df = pd.read_csv("data/iris.csv")
X = df.drop("species", axis=1)
y = df["species"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Enable MLflow autologging
mlflow.sklearn.autolog()

with mlflow.start_run():
    clf = RandomForestClassifier(
        n_estimators=args.n_estimators, max_depth=args.max_depth
    )
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)

    mlflow.log_param("n_estimators", args.n_estimators)
    mlflow.log_param("max_depth", args.max_depth)
    mlflow.log_metric("accuracy", acc)
    mlflow.sklearn.log_model(clf, "model")
```

Generate input
```python
from sklearn.datasets import load_iris
import pandas as pd
iris = load_iris(as_frame=True)
df = iris.frame
df.to_csv("data/iris.csv", index=False)
```
Running:
```bash
mlflow run . -P n_estimators=150 -P max_depth=3
```

This command:

Sets parameters (n_estimators, max_depth)

Creates an isolated Conda environment

Executes train.py

Logs run to MLflow Tracking


🧰 What Gets Logged
params: n_estimators, max_depth

metrics: accuracy

artifacts: sklearn model, conda.yaml, source code

model: saved and versioned in MLflow model format

UI: view at http://localhost:5000 (if using local MLflow UI)



# ✅ Enhancing MLflow Project: Model Registry, REST Serving, CI/CD Integration

This guide extends the previous MLflow project by adding:

1. Model Registry integration  
2. REST-based model serving  
3. CI/CD workflow using GitHub Actions  

---

## 📌 1. Register Model in MLflow Model Registry

### 🔁 Modify `train.py` to register the model:

```python
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

...

with mlflow.start_run():
    ...
    signature = infer_signature(X_train, clf.predict(X_train))
    mlflow.sklearn.log_model(clf, "model", signature=signature, registered_model_name="IrisClassifier")


# 📊 Data Visualization Tools in Databricks

## Built-in Tools

- **display(df)**: Automatically renders Spark or Pandas DataFrames as tables or charts.
- **Built-in Visualizations**: Line, bar, scatter, pie, map charts (GUI-based in notebooks).
- **Databricks SQL Dashboards**: Interactive SQL dashboards for business and data teams.

## Python/External Libraries

- **Matplotlib / Seaborn / Plotly / Bokeh**: Full Python visualization support in notebooks.
- **Koalas + Plotly**: Plotting on Pandas-like APIs over Spark.

## BI Tool Integration

- **Power BI**
- **Tableau**
- **Qlik**
- Connect via JDBC/ODBC or native connectors.

---

# 🧩 Other Features Relevant for ML & Viz

- **Delta Lake**: ACID, versioning, schema enforcement — great for ML reproducibility.
- **Unity Catalog**: Centralized access control and governance for models and data.
- **Structured Streaming**: Real-time data pipelines combined with ML inference.

