## Electric utility, asset, vegetation, and meteorological data
are four categories of data commonly used by electric power companies to manage electricity networks, predict outages, prevent wildfires, and optimize maintenance.

These datasets are often combined for data engineering, geospatial analytics, machine learning, and predictive maintenance.

## 1. Electric utility data

Data describing electricity generation, transmission, distribution, and consumption.

| Data                    | Examples                                  |
| ----------------------- | ----------------------------------------- |
| Electricity consumption | kWh usage by customer, hourly demand      |
| Power generation        | Solar, wind, hydroelectric generation     |
| Grid operations         | Voltage, current, frequency               |
| Outages                 | Outage start/end time, affected customers |
| Smart meters            | 15-minute or hourly electricity readings  |
| Network topology        | Substations, feeders, power lines         |
| Energy prices           | Electricity rates, peak/off-peak pricing  |

Example: Analyze historical electricity demand to predict peak loads and prevent transformer overloads.

## 2. Asset data

Information about physical equipment owned and operated by an electric utility.

| Asset           | Typical attributes                     |
| --------------- | -------------------------------------- |
| Transformer     | ID, capacity, age, location, condition |
| Power line      | Length, voltage, conductor material    |
| Utility pole    | Material, height, installation date    |
| Substation      | Capacity, equipment, GPS coordinates   |
| Circuit breaker | Manufacturer, maintenance history      |
| Sensor          | Device ID, measurements, health status |

Example: Predict transformer failures based on equipment age, historical load, temperature, and maintenance records.

## 3. Vegetation data

Information about trees, shrubs, and other vegetation located near electrical infrastructure.

This is especially important for preventing power outages and wildfires.

| Data                    | Examples                         |
| ----------------------- | -------------------------------- |
| Tree location           | GPS coordinates                  |
| Tree characteristics    | Species, height, canopy diameter |
| Distance to power lines | Clearance in meters              |
| Vegetation density      | Trees per square kilometer       |
| Growth rate             | Estimated annual growth          |
| Inspection history      | Last inspection, trimming date   |
| Satellite imagery       | Vegetation coverage, health      |

Example: Identify trees likely to contact overhead power lines during strong winds.

Vegetation data may come from satellite imagery, drones, LiDAR scans, or field inspections.

## 4. Meteorological data

Weather and atmospheric measurements that influence electric grid operations.

| Data                 | Examples                       |
| -------------------- | ------------------------------ |
| Temperature          | Air temperature, daily maximum |
| Wind                 | Speed, direction, gusts        |
| Humidity             | Relative humidity              |
| Precipitation        | Rainfall, snowfall             |
| Lightning            | Strike locations, frequency    |
| Soil moisture        | Soil dryness                   |
| Weather forecasts    | Hourly or daily forecasts      |
| Fire weather indices | Fire danger ratings            |

Example: Predict the probability of power-line damage during high-wind events.

## 5. How these datasets work together

Consider a utility company that wants to predict wildfire risk caused by power lines.

For example:

- Utility data: A particular power line experienced multiple outages.
- Asset data: The line is supported by 40-year-old wooden poles.
- Vegetation data: Several trees are within 2 meters of the line.
- Meteorological data: Tomorrow's forecast predicts 70 mph winds and very low humidity.

A machine learning model could combine these features to identify high-risk sections of the network.

## 6. Data engineering perspective

These four data domains have different characteristics:

| Dataset        | Typical format                    | Update frequency |
| -------------- | --------------------------------- | ---------------- |
| Utility        | Time series, relational           | Seconds to hours |
| Asset          | Relational, GIS                   | Days to months   |
| Vegetation     | GIS, LiDAR, imagery               | Weeks to years   |
| Meteorological | Time series, gridded spatial data | Minutes to hours |

A typical architecture might be:

Sources → S3 → Databricks (Bronze/Silver/Gold) → ML models → Dashboards

The main engineering challenge is combining these datasets using both location and time. For example, joining weather observations, nearby trees, and equipment characteristics to a particular power-line segment at the time of an outage.

This is often called a spatiotemporal data integration problem.

If you encountered these four categories in a Data Engineer job description, they likely indicate a role involving electric-grid analytics, geospatial data processing, asset management, outage prediction, or wildfire risk modeling.


# Wildfire predictive modeling and causal inference for PG&E

Let's consider a realistic Data Science / Data Engineering project for Pacific Gas and Electric Company (PG&E) in California.

Business objective: Predict which electric distribution lines are most likely to cause a wildfire and determine which preventive actions actually reduce wildfire risk.

This project has two distinct components:

1. Predictive modeling: Which power-line segments are most likely to experience a wildfire ignition tomorrow?
2. Causal inference: Does vegetation trimming, equipment replacement, or undergrounding actually reduce wildfire ignitions, and by how much?

The distinction is important. A machine learning model can identify high-risk power lines, but it cannot automatically establish whether a particular intervention will reduce that risk.

## 1. Example: A PG&E distribution network

Assume PG&E operates thousands of overhead distribution-line segments across Northern California.

We divide the network into segments, each approximately 500 meters long, and create one observation per segment per day.

[PG&E to Bury 10,000 Miles of Electric Lines Underground | KQED](https://images.openai.com/static-rsc-4/I2Nq8FQcXyEqSzrC5XkB1ZvtYEXljQmQalsq_CLXnJhsypXn1FKrNsH9_RJrHA8qpbQsP2TSrr8edvJyjUAsuT_blMT-_UwWJy8CbsioYn2agjgG1sn_3ozJsgnQEa0hnvDN-fevXbHkMt0PsTCeVmlqVydzIyOhiCN0XndU1Ac?purpose=inline)

[Home - Wilhelm Traffic Control and Tree Services](https://images.openai.com/static-rsc-4/UoFJtBPSdvWKxuFeSEwJoMyfQbqZX8ZtlQrqLX7U83xmwlLUTnhbVfHJtwA9nnu288EuhoN4Zf5ftZwymKOX_hLeyPR2uQz_ZgyTQ_05z6dcjeDezD4Kx6MH-fVcwdk_sI3YmABnFXJWBbpQjdNt9GVnFFFTU56iDN5ozlIt20k?purpose=inline)

[Lighting-Gallery.net - Power Lines, Utility Poles, and Equipment/SCE Power Line Utility Pole, Ojai CA (14KV)](https://images.openai.com/static-rsc-4/y_VA7d6NW0-hONtkX5c_hrf_wYJ07N0dN10Ozk0iZeTBrM-xiSqa6-oTwmIQi_6kyulhg73vmezuetUMo4PuiGqf55QyOgHqCjQ2BTcmFcUTTJotHOl-VneBjOgdBTZv8RPcqvPFlYQzqTyfwfBz3cutcaR01ucj2kGSLmqavNI?purpose=inline)

10

Illustrative infrastructure and vegetation conditions that may contribute to wildfire ignition risk.

For each segment, we collect four categories of data:

| Category         | Example features                                |
| ---------------- | ----------------------------------------------- |
| Electric utility | Current, voltage, outage history, fault events  |
| Asset            | Pole age, conductor type, transformer condition |
| Vegetation       | Tree distance, canopy density, fuel moisture    |
| Meteorological   | Wind speed, humidity, temperature, drought      |

Our target variable is:

\\[ Y\_{i,t} = \begin{cases} 1 & \text{if segment }i\text{ causes an ignition on day }t\\\ 0 & \text{otherwise} \end{cases} \\]

In practice, we need verified incident records linking an ignition to utility equipment and its location, not just wildfire perimeter data.

The prediction model estimates:

\\[ P(Y\_{i,t}=1\mid X\_{i,t}) \\]

where \\(X\_{i,t}\\) contains information available before the prediction is made.

## 2. Predictive modeling: Identify high-risk segments

PG&E's actual 2026–2028 Wildfire Mitigation Plan describes asset-level wildfire risk modeling, including its Wildfire Distribution Risk Model (WDRM) and Wildfire Transmission Risk Model (WTRM). Its risk framework includes equipment, vegetation, weather, topography, and potential consequences.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pge.com\&sz=32)

PG&E

+1



Our example is a simplified model inspired by these practices, not PG&E's proprietary implementation.

### Example training dataset

All numbers below are synthetic.

| Segment | Pole age | Tree clearance | Wind   | Humidity | Ignition |
| ------- | -------- | -------------- | ------ | -------- | -------- |
| A101    | 45 years | 1.2 m          | 65 mph | 12%      | 1        |
| A102    | 12 years | 8.5 m          | 20 mph | 45%      | 0        |
| A103    | 38 years | 2.0 m          | 55 mph | 15%      | 1        |
| A104    | 25 years | 5.0 m          | 30 mph | 35%      | 0        |
| A105    | 52 years | 0.8 m          | 70 mph | 10%      | 1        |

In a real dataset, ignition events would be extremely rare. These five rows are just illustrative; they are not representative of real ignition frequencies.

### Python implementation with XGBoost
```python
from xgboost import XGBClassifier

features = [
    "pole_age",
    "tree_clearance",
    "wind_speed",
    "humidity",
    "temperature",
    "faults_last_30d",
    "vegetation_density",
    "fuel_moisture"
]

X_train = train_df[features]
y_train = train_df["ignition"]

model = XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.03,
    eval_metric="logloss",
    random_state=42
)

model.fit(X_train, y_train)

risk = model.predict_proba(
    test_df[features]
)[:, 1]
```
 
This assumes `train_df` and `test_df` have already been prepared with a time-based split and historical feature values.

### Example prediction results

Illustrative predicted ignition probabilities

<img width="653" height="401" alt="image" src="https://github.com/user-attachments/assets/3b9560df-8221-46c2-a3c3-5d0869d23573" />

Synthetic probabilities per segment-day, not actual PG&E estimates

The model ranks A101 as the highest-risk segment. However, even a well-ranked model may produce inaccurate probabilities unless it is calibrated on representative operational data.

Validation is especially important:

- Train on earlier years and test on later years.
- Hold out entire geographic regions to measure generalization.
- Use precision-recall metrics because ignitions are rare.
- Measure probability calibration, not only ranking accuracy.
- Evaluate how many actual ignitions fall within the highest-risk 1% of segments.

A critical complication is that existing mitigation programs change the observed ignition rate. For example, a high-risk line that was de-energized during extreme winds may show zero ignitions. The model must account for operational exposure and historical mitigation actions.

## 3. Causal inference: Does vegetation trimming reduce ignitions?

Now consider a different question.

PG&E spends money on trimming trees near power lines. We want to estimate the causal effect of this intervention.

Let:

- \\(T=1\\): Segment received vegetation trimming.
- \\(T=0\\): Segment did not receive trimming.
- \\(Y=1\\): A utility-caused ignition occurred during a specified follow-up period.

We want to estimate:

\\[ ATE=E[Y(1)-Y(0)] \\]

where \\(Y(1)\\) and \\(Y(0)\\) represent potential outcomes with and without trimming.

### Why simple comparison is misleading

Suppose we observe:

| Group       | Segments | Ignitions | Ignition rate |
| ----------- | -------- | --------- | ------------- |
| Trimmed     | 10,000   | 30        | 0.30%         |
| Not trimmed | 10,000   | 10        | 0.10%         |

It appears that trimming triples wildfire risk!

But this conclusion is likely incorrect.

PG&E would generally prioritize trimming in areas already identified as dangerous. Therefore, the trimmed group may have much higher baseline risk.

This is confounding by indication, also called treatment selection bias.

### Causal diagram

We need to separate the effect of trimming from the underlying wildfire risk.

## 4. Recommended causal method: Staggered Difference-in-Differences

Imagine PG&E trims vegetation across different power-line segments in different months.

We can exploit this staggered rollout to estimate the intervention's effect, provided we have credible comparison segments.

For a simple two-group, two-period illustration:

| Group   | Before trimming                    | After trimming |
| ------- | ---------------------------------- | -------------- |
| Treated | 8 ignitions / 10,000 segment-years | 3 / 10,000     |
| Control | 4 / 10,000                         | 3 / 10,000     |

The treated group improved by 5 ignitions per 10,000 segment-years. The control group improved by 1.

The Difference-in-Differences estimate is:

\\[ \begin{aligned} DiD &= (3-8)-(3-4)\\\ &= \boxed{-4} \end{aligned} \\]

Interpretation: Under the causal assumptions, trimming prevented an estimated 4 ignitions per 10,000 segment-years in the treated population.

This is a synthetic example, not an observed PG&E effect.

### Python implementation

For the simple two-period design:

```python
import statsmodels.formula.api as smf

# One row per segment-period
# ignition: binary indicator
# treated: segment belongs to treatment group
# post: observation after treatment date

result = smf.ols(
    "ignition ~ treated * post",
    data=df
).fit(
    cov_type="cluster",
    cov_kwds={"groups": df["segment_id"]}
)

print(result.params["treated:post"])
print(result.conf_int().loc["treated:post"])
```

The interaction coefficient estimates a change in ignition probability, not a percentage reduction. Multiplying it by 10,000 expresses the effect per 10,000 segment-period observations, assuming equal exposure.

For a real staggered rollout, I would use a group-time ATT estimator (for example, Callaway–Sant'Anna), rather than ordinary two-way fixed effects, which can be biased with heterogeneous treatment effects.

### Required causal assumptions

The most important assumptions are:

- Parallel trends: Without trimming, treated and comparison segments would have followed similar ignition-rate trends.
- No anticipation: Future trimming does not change earlier outcomes.
- Comparable exposure: Differences in energized time, PSPS, and other interventions are handled appropriately.
- No uncontrolled spillovers: Trimming one segment does not substantially change the outcome of comparison segments, or the design accounts for it.

We should inspect pre-treatment event-study coefficients, match or weight segments using pre-treatment characteristics, and test alternative comparison groups.

Because ignitions are rare, uncertainty intervals may be wide even with thousands of segments. We may need multiple years of data and additional mechanistic outcomes such as vegetation contacts, while retaining actual ignitions as the primary safety outcome.

## 5. More advanced: Heterogeneous treatment effects

A useful next step is to ask:

Does vegetation trimming work equally well everywhere?

Perhaps trimming reduces ignition risk more in locations with:

- Strong winds
- Dense vegetation
- Older overhead infrastructure
- Low fuel moisture

We can estimate a Conditional Average Treatment Effect (CATE):

\\[ \tau(x)=E[Y(1)-Y(0)\mid X=x] \\]

For example, a causal forest could estimate the treatment effect separately for different environmental conditions.

| Segment type                 | Baseline risk | Estimated trimming effect |
| ---------------------------- | ------------- | ------------------------- |
| Dense vegetation, high wind  | 0.80%         | −0.35 percentage points   |
| Dense vegetation, low wind   | 0.30%         | −0.12 percentage points   |
| Sparse vegetation, high wind | 0.20%         | −0.03 percentage points   |
| Sparse vegetation, low wind  | 0.05%         | −0.01 percentage points   |

These are hypothetical results. A causal forest alone does not eliminate confounding; identification still depends on appropriate assumptions and study design.

This information is more actionable than an ordinary prediction score because it helps identify where trimming might produce the greatest risk reduction.

## 6. Data engineering architecture for PG&E

Given a Databricks/Spark environment, I would design the pipeline as follows:
Input:
```
SCADA / outage events
GIS / asset registry
LiDAR / vegetation
Weather stations / NOAA
```
#### Bronze — Raw data

S3 / Delta Lake: original events, files, spatial datasets

#### Silver — Clean and integrate

Deduplication, timestamps, geospatial joins, historical asset states

#### Gold — Segment-day feature table

segment_id, date, weather, asset condition, vegetation, treatments, ignition

#### Predictive ML

XGBoost / LightGBM

Ignition risk scores

### Causal inference

DiD / Causal Forest

Estimated intervention effects

#### Decision-support dashboard

Prioritize maintenance and vegetation work, with engineering and safety review

A particularly important transformation is the geospatial join between power-line geometry, vegetation observations, and weather grids. It must also be a point-in-time join so that future inspection findings or revised weather observations cannot leak into historical predictions.

## 7. Combining predictive and causal models for decisions

Suppose PG&E has a budget to trim only 1,000 segments.

The predictive model identifies high-risk segments. The causal model estimates how much trimming would reduce risk on each segment.

We can combine them:

\\[ \text{Expected risk reduction}\_i = P(Y_i=1\mid do(T=0),X_i) - P(Y_i=1\mid do(T=1),X_i) \\]

Then, for budget allocation:

\\[ \text{Benefit-cost ratio}\_i = \frac{\text{Expected loss reduction}\_i} {\text{Intervention cost}\_i} \\]

Expected loss can include the probability of ignition and the consequences of fire spread, injuries, property damage, and other impacts. This is better than ranking solely by ignition probability.

For a safety-critical application, such rankings would support—not replace—utility engineering decisions, regulatory requirements, and mandatory vegetation-clearance standards.

## 8. Where to get real data

PG&E's wildfire mitigation documentation is a useful starting point. The company has described work involving undergrounding, targeted vegetation management, enhanced safety settings, drone inspections, and weather forecasting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pge.com\&sz=32)

PG&E

+1



For a prototype, you can combine publicly available weather, fire, and vegetation datasets with synthetic utility asset records.

| Source                                                                                                                                 | Data                                            |
| -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [NOAA NCEI](https://www.ncei.noaa.gov/?utm_source=chatgpt.com)                                                                         | Historical weather observations                 |
| [CAL FIRE](https://www.fire.ca.gov/?utm_source=chatgpt.com)                                                                            | Wildfire incidents and fire perimeters          |
| [USGS](https://www.usgs.gov/?utm_source=chatgpt.com)                                                                                   | Elevation, land cover, environmental data       |
| [LANDFIRE](https://www.landfire.gov/?utm_source=chatgpt.com)                                                                           | Vegetation and wildland fuel characteristics    |
| [California Energy Safety](https://energysafety.ca.gov/?utm_source=chatgpt.com)                                                        | Utility wildfire mitigation plans and reports   |
| [PG&E Wildfire Safety](https://www.pge.com/en/outages-and-safety/safety/community-wildfire-safety-program.html?utm_source=chatgpt.com) | PG&E mitigation plans and program documentation |

Public wildfire datasets generally do not provide a complete, verified segment-level record of utility-caused ignitions, and detailed asset and treatment histories may be unavailable. Those are significant limitations for causal identification.

## My suggested project

I would start with a focused research question:

"What is the causal effect of vegetation clearance on utility-related wildfire ignition probability under extreme wind conditions?"

Build two models on the same dataset: XGBoost for risk prediction and a staggered Difference-in-Differences estimator for causal analysis. Later, add causal forests to investigate which locations benefit most from trimming.

This gives you a concrete project combining PySpark data engineering, geospatial joins, time-series modeling, machine learning, and causal inference, while keeping the important distinction between predicting risk and estimating the impact of an intervention.


# Palantir Foundry

Palantir Foundry is an enterprise data platform developed by Palantir Technologies. It combines data engineering, data integration, analytics, machine learning, and operational applications in one environment.

It is used by organizations that need to integrate data from many systems and turn it into operational decisions.

## 1. What does Foundry do?

Foundry provides capabilities across the data lifecycle:

| Capability               | Description                                            | Similar technology            |
| ------------------------ | ------------------------------------------------------ | ----------------------------- |
| Data ingestion           | Connect to databases, APIs, files, streaming sources   | Fivetran, Kafka               |
| Data transformation      | Clean, join, and process data using SQL, Python, Spark | Databricks, dbt               |
| Data storage             | Manage datasets and their versions                     | Delta Lake, data warehouses   |
| Data pipelines           | Schedule and monitor transformations                   | Airflow, Databricks Workflows |
| Data modeling            | Represent business objects and relationships           | Semantic layers, graph models |
| Analytics                | Explore data and build dashboards                      | Power BI, Tableau             |
| Machine learning         | Develop and operationalize models                      | Databricks ML, SageMaker      |
| Operational applications | Build applications for business decisions              | Custom web applications       |

## 2. Foundry architecture

A simplified architecture looks like this:

Data Sources

Databases

APIs / Kafka

S3 / Files

Foundry Data Integration

Ingestion, transformations, pipelines, lineage

Foundry Ontology

Business objects, relationships, actions

Analytics

Dashboards

AI / ML

Predictions

Applications

Decisions

## 3. What makes Foundry different?

One of Foundry's most distinctive features is the Ontology.

An Ontology represents real business entities, their relationships, and the operations users can perform on them.

For example, in an electric utility company:

- Objects: PowerLine, Transformer, UtilityPole, Tree, WeatherStation
- Relationships: PowerLine connects to Transformer; Tree is near PowerLine
- Properties: Age, location, voltage, vegetation clearance
- Actions: Schedule inspection, request tree trimming, update maintenance status

Rather than simply querying tables, an application can work with business objects and trigger governed operational workflows.

## 4. Example: Foundry for PG&E wildfire risk

Suppose PG&E wants to predict wildfire ignition risk.

Foundry could integrate electric utility, asset, vegetation, and meteorological data into one operational environment.

A workflow might be:

1. Ingest SCADA events, equipment records, vegetation surveys, and weather forecasts.
2. Build transformations joining these datasets by location and time.
3. Train or integrate a wildfire risk prediction model.
4. Expose risk scores as properties of `PowerLine` objects in the Ontology.
5. Display high-risk segments in a geospatial application.
6. Allow authorized personnel to create inspection or vegetation-management work orders.

This is a hypothetical implementation, not a claim about PG&E's actual Foundry deployment.

## 5. Palantir Foundry vs Databricks vs Snowflake

| Feature                  | Palantir Foundry            | Databricks                          | Snowflake                           |
| ------------------------ | --------------------------- | ----------------------------------- | ----------------------------------- |
| Primary focus            | Data-to-operations platform | Data engineering, analytics, AI/ML  | Cloud data platform and analytics   |
| Spark support            | Yes                         | Native/core                         | Available through integrations      |
| Python and SQL           | Yes                         | Yes                                 | Yes                                 |
| ML capabilities          | Yes                         | Extensive                           | Yes                                 |
| Business object model    | Strong Ontology             | Typically custom or external        | Typically custom or external        |
| Operational applications | Major strength              | Possible with apps and integrations | Possible with apps and integrations |
| Data governance          | Integrated                  | Unity Catalog                       | Native governance features          |

The biggest difference is that Foundry focuses on connecting data and analytics to operational decisions, while Databricks traditionally focuses more on engineering and AI workloads, and Snowflake on managed data and analytics.

These platforms increasingly overlap, so the boundaries are not absolute.

## 6. Is Foundry relevant for a Data Engineer?

Yes. If you already know PySpark, SQL, Databricks, ETL pipelines, and data modeling, many concepts will be familiar.

Important Foundry concepts to learn include:

- Pipeline Builder: Visual data transformations.
- Code Repositories: Code-based transformations using Python, SQL, and Spark.
- Datasets and lineage: Versioned data and transformation dependencies.
- Ontology: Business objects, links, and actions.
- Workshop: Building operational user interfaces.
- AIP: Palantir's Artificial Intelligence Platform, which integrates AI capabilities with enterprise data and workflows.

Official documentation: [Palantir Foundry documentation](https://www.palantir.com/docs/foundry/?utm_source=chatgpt.com).

For your data engineering background, the most important new concept is the Ontology. Most ETL and Spark concepts transfer naturally from Databricks, but Foundry's approach to modeling business objects and connecting them to operational applications is worth studying in detail.
