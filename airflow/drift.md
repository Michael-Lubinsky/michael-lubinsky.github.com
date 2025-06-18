## Types of Drift:
### Schema Drift
Structural changes in the data, such as:

New or missing columns
Changed data types
Renamed fields

### Data Drift
Statistical or distributional changes in the data, such as:
Shift in the range, mean, or variance of values
Different frequency of categories
Changing patterns over time

### Concept Drift
In ML pipelines: changes in the relationship between features and target, affecting model accuracy.

✅ Why Drift Matters:
Causes ETL/ELT jobs to fail or produce incorrect results
Impacts machine learning model accuracy
Leads to data quality degradation
Breaks dashboard metrics or downstream logic

✅ Handling Schema Drift:
Dynamic schema inference (e.g., Auto Loader in Databricks)
Flexible schema evolution in formats like Parquet, Delta Lake, or Avro
Versioned schemas using schema registry (e.g., in Kafka)
Field-level validations to detect changes
Alerts or quarantine logic for unknown fields

✅ Handling Data/Concept Drift:
Monitoring tools to track statistics and distributions
Drift detection libraries (e.g., Evidently, River, Alibi Detect)
Retraining models or recalibrating thresholds
Data validation frameworks like Great Expectations or Deequ

✅ In Practice:
Drift handling is often a combination of:
Automation (auto schema handling, alerting)
Governance (schema contracts, metadata tracking)
Observability (logs, metrics, quality checks)
Adaptability (self-healing pipelines, human-in-the-loop decisions)
