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

