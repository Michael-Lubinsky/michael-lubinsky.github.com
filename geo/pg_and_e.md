## Geospatial Data
There are two main types of geospatial data: raster and vector.
<https://www.palantir.com/docs/foundry/geospatial/types-of-geospatial-and-geotemporal-data#raster-data>

### Vector data 
is used for storing data that has discrete boundaries and represents these data as points, lines, and polygons. Examples of vector data include points representing cities on a map of the United States, lines representing roads in a state, and polygons representing electoral district boundaries.

### Raster data 
consists of a matrix of cells organized into rows and columns, in which each cell represents specific information. Examples of raster data include satellite imagery sources, scanned maps, and digital elevation models (DEMs).

For example, a raster dataset can represent temperature, elevation, vegetation density, soil moisture, or wind speed across California.

Geospatial data with a temporal component is known as geotemporal data.

#### Geometry comparisons
```
Intersection. 
Difference  
Symmetric difference   
Union (column-wise and aggregate)  
```
Apache Sedona Example
```python
from sedona.spark import SedonaContext

# Assumes SparkSession has compatible Sedona
# dependencies configured.
sedona = SedonaContext.create(spark)

result = spark.sql("""
    SELECT ST_Contains(
        ST_GeomFromWKT(
            'POLYGON((
                0 0,
                10 0,
                10 10,
                0 10,
                0 0
            ))'
        ),
        ST_Point(5.0, 5.0)
    ) AS is_inside
""")

result.show()
```
In Palantir Foundry, the equivalent of Apache Sedona's `ST_Contains(polygon, point)` depends on whether you use a SQL transform or a PySpark Code Repository.

For the same PG&E example—finding utility poles inside wildfire risk polygons—the SQL logic is:

```sql
SELECT
    p.pole_id,
    z.zone_id
FROM poles p
JOIN zones z
    ON ST_Contains(
        z.geometry,
        p.geometry
    )
```

However, this is Sedona SQL syntax, and you should not assume `ST_Contains` is available directly in every Foundry SQL environment.

## 1. Foundry SQL Studio — direct equivalent

Palantir's current Furnace SQL engine supports `st_contains()`, so you can write the following query directly in SQL Studio.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir



```sql
SELECT
    p.pole_id,
    z.zone_id
FROM poles p
JOIN wildfire_zones z
    ON st_contains(
        st_geomfromgeojson(z.geometry),
        st_point(p.longitude, p.latitude)
    )
```

This assumes `z.geometry` contains a GeoJSON polygon string and `poles` has numeric longitude and latitude columns.

If both columns are already geometry-typed, use:

```sql
SELECT
    p.pole_id,
    z.zone_id
FROM poles p
JOIN wildfire_zones z
    ON st_contains(z.geometry, p.geometry)
```

These queries target Furnace SQL, not Ontology SQL or the older Spark SQL transform engine. The function is documented for Furnace, but not Ontology SQL.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir



## 2. Foundry Pipeline Builder

You can also implement the operation without SQL:

1. Load the `poles` and `wildfire_zones` datasets.
2. Convert coordinates and polygon data into Foundry Geometry types.
3. Use a Geometry intersection join to find candidate pole-zone pairs.
4. Apply the Geometry contains expression, with the polygon as Geometry A and the point as Geometry B.
5. Filter where the expression returns `true`.

The containment expression excludes points on polygon boundaries, matching Sedona's `ST_Contains` behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir

+1



## 3. Foundry Python Code Repository

For a PySpark transform using Foundry's legacy geospatial library:

```
from transforms.api import transform_df, Input, Outputfrom geospatial_tools import geospatialfrom geospatial_tools.functions import contains@geospatial()@transform_df(    Output("/my/output/poles_in_zones"),    df=Input("/my/input/pole_zone_candidates"))def compute(df):    return (        df.withColumn(            "is_inside",            contains("zone_geometry", "pole_geometry")        )        .filter("is_inside")    )
```

Here, the input is a dataset of candidate pole-zone pairs with GeoJSON geometry columns. This API is documented under Foundry's legacy geospatial transforms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir



Recommendation: For your PG&E wildfire project, I would use Furnace SQL for straightforward point-in-polygon queries, and Pipeline Builder for a managed geospatial ETL workflow. For more complex spatial processing, including large proximity joins and custom geometry algorithms, a PySpark Code Repository with appropriate geospatial libraries provides more flexibility.

Documentation: [Palantir Foundry SQL geospatial functions](https://www.palantir.com/docs/foundry/sql-warehousing/sql-dialect?utm_source=chatgpt.com).





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

## GeoSpatial Data Processing

# Geospatial data engineering for PG&E wildfire risk management

For a PG&E wildfire risk management project, I would use PySpark + Apache Sedona for large-scale geospatial processing, or Palantir Foundry for integrating geospatial analytics with operational workflows.

The central challenge is combining four different types of data:

- Electric utility: Power lines, circuits, faults, outages, and electrical loads.
- Assets: Utility poles, transformers, conductor types, equipment age, and maintenance.
- Vegetation: Trees, canopy coverage, LiDAR point clouds, and distance to power lines.
- Meteorological: Wind, humidity, temperature, precipitation, and fire weather conditions.

The most important operations are spatial joins, proximity calculations, raster processing, and spatiotemporal joins.

I'll show a practical implementation, including PySpark code, data sources, Foundry integration, and how to build features for wildfire prediction and causal inference.

## 1. Understanding the geospatial datasets

Geospatial data is different from ordinary tabular data because each record has a location or geometry.

[Access, Awareness, and Analysis—All in One Location Platform](https://images.openai.com/static-rsc-4/e8-mrL1xFGEbtAnQ_Sltqz4ubmWqOm9SYkjeEspD24a10PmQ0rGR8n-cwTdAolBy8U4mIGwLVEb4bMQU9AFqn8R7A_SlppLC4gnOZ_9bYUVHNH4mZB-gZFHbqCB_FGQACsqdeWGhgaVAXhuWZbXZHEnmC_09yhpxgQxou4UKWSY?purpose=inline)

Vector data

Points, lines, polygons representing physical infrastructure

[Ladder fuels rather than canopy volumes consistently predict wildfire severity even in extreme topographic-weather conditions | Communications Earth & Environment](https://images.openai.com/static-rsc-4/HOI0zI-Y23x0Hu5TO7B5WQTKfziKudVbPb_-DwC8aTdKYR0B10CKpQb7y0cfEZC9oYE-5784PVzmJz_pFG3Es8iAbm304WOTRENYX3BOvb0hG0wxPZo_TtdrCBh8by4-YYqhvT4eFIGlXWWgMnw8oUg_XTcXE_zSo9LtOLJ3XaM?purpose=inline)

Raster data

Grid cells representing vegetation, elevation, temperature, and fuel conditions

| Dataset           | Geometry        | Typical format         |
| ----------------- | --------------- | ---------------------- |
| Utility poles     | Point           | GeoJSON, GeoParquet    |
| Power lines       | LineString      | Shapefile, GeoParquet  |
| Vegetation areas  | Polygon         | GeoJSON, GeoParquet    |
| Individual trees  | Point / Polygon | LiDAR-derived features |
| Fire perimeters   | Polygon         | GeoJSON, Shapefile     |
| Weather stations  | Point           | CSV, Parquet           |
| Weather forecasts | Raster grid     | NetCDF, GRIB2          |
| Elevation / slope | Raster grid     | GeoTIFF                |

A power-line segment might look like:

```
{
  "segment_id": "PG&E_12345",
  "voltage_kv": 12,
  "conductor_type": "overhead",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [-121.850, 37.300],
      [-121.845, 37.305]
    ]
  }
}
```

GeoJSON coordinates use longitude, latitude ordering. The geometry above is in WGS84 (EPSG:4326).

For measuring distances in meters, we should transform geometries into an appropriate projected coordinate reference system rather than calculate Euclidean distances directly from longitude and latitude.

## 2. Suggested architecture

Geospatial data sources

PG&E GIS / SCADA / Assets

LiDAR / Satellite / Vegetation

NOAA / Weather forecasts

CAL FIRE / Ignition history

Bronze: S3 / Delta Lake

Original files, imagery, sensor records and geometry

Silver: PySpark + Apache Sedona

CRS conversion, spatial joins, buffering, geometry validation, temporal alignment

Gold: Segment-day features

One row per power-line segment per day

Predictive modeling

XGBoost, risk scoring, ignition probability

Causal inference

Vegetation treatment effects, DiD, causal forests

Map dashboard / Palantir Ontology

Prioritize inspections and evaluate mitigations

## 3. PySpark: Load geospatial data

For distributed spatial processing, I recommend Apache Sedona.

Sedona extends Spark SQL with functions such as:

| Function         | Purpose                                  |
| ---------------- | ---------------------------------------- |
| `ST_Point`       | Create a geographic point                |
| `ST_GeomFromWKT` | Convert WKT text into geometry           |
| `ST_Transform`   | Change coordinate reference systems      |
| `ST_Distance`    | Calculate distance between geometries    |
| `ST_DWithin`     | Find geometries within a distance        |
| `ST_Intersects`  | Find intersecting geometries             |
| `ST_Buffer`      | Create an area around a geometry         |
| `ST_Contains`    | Test whether a geometry contains another |

Sedona supports distributed spatial joins and GeoParquet.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### Step A: Load power-line geometry

Assume you have a CSV with `segment_id`, `voltage_kv`, and `geometry_wkt`.

```
from sedona.spark import SedonaContextfrom pyspark.sql import functions as F# SparkSession must be configured with# compatible Sedona dependencies first.sedona = SedonaContext.create(spark)lines = spark.read.csv(    "s3://wildfire/bronze/power_lines/",    header=True,    inferSchema=True)lines = lines.withColumn(    "geometry",    F.expr("ST_GeomFromWKT(geometry_wkt)"))lines.createOrReplaceTempView("power_lines")
```

Example WKT geometry:

```
LINESTRING (
  -121.850 37.300,
  -121.845 37.305
)
```

Alternatively, read GeoParquet directly using Sedona's `geoparquet` data source.

### Step B: Load tree locations

Assume each tree has GPS coordinates and a measured height.

```
trees = spark.read.parquet(    "s3://wildfire/bronze/trees/")trees = trees.withColumn(    "geometry",    F.expr("ST_Point(longitude, latitude)"))trees.createOrReplaceTempView("trees")
```

## 4. Spatial join: Find trees near power lines

This is one of the most useful geospatial operations for wildfire risk management.

Question: Which trees are within 10 meters of a power-line segment?

Schematic illustration, not a real PG&E location or clearance requirement.

### PySpark SQL implementation

```
result = spark.sql("""    WITH lines_m AS (        SELECT            segment_id,            ST_Transform(                geometry, 'EPSG:4326', 'EPSG:3310'            ) AS geom_m        FROM power_lines    ),    trees_m AS (        SELECT            tree_id,            tree_height,            ST_Transform(                geometry, 'EPSG:4326', 'EPSG:3310'            ) AS geom_m        FROM trees    )    SELECT        l.segment_id,        t.tree_id,        t.tree_height,        ST_Distance(            l.geom_m, t.geom_m        ) AS distance_m    FROM lines_m l    JOIN trees_m t      ON ST_DWithin(          l.geom_m, t.geom_m, 10.0      )""")
```

Here, EPSG:3310 is California Albers, a projected CRS with meter units. For precise engineering clearances, choose an appropriate local projection and use 3D conductor and vegetation geometry rather than a 2D approximation.

We can aggregate the results into features:

```
vegetation_features = (    result.groupBy("segment_id")    .agg(        F.count("*").alias("trees_within_10m"),        F.min("distance_m").alias("nearest_tree_m"),        F.max("tree_height").alias("max_tree_height")    ))
```

These features can feed directly into an ignition-risk model.

## 5. Meteorological data: Join weather to power lines

Weather data is often provided as a grid rather than as observations at every utility pole.

For example, a forecast grid might have wind speed, humidity, and temperature at each grid cell.

[California weather: Inside-slider system to bring strong winds](https://images.openai.com/static-rsc-4/ZXf_hxl19XRopK1u3r48XsaEMGsWDW-0-a5TuPsAPYRMCkEhdOR-zNdM8F0K05CWUZf7GRtaX2cCadmON8FoWda38w5iQSSm8x3U2Ir5t4WFJNt1_ZPfZEGkk1aLp3cQWwTqfEstaBJXrjTz8nouV2ICpQD_xFZB_624rjioug8?purpose=inline)

[sfchronicle.com](https://www.sfchronicle.com/weather-forecast/article/california-winds-18450012.php?utm_source=chatgpt.com)

Illustrative weather-grid visualization. Each power-line segment may intersect multiple forecast cells.

A scalable method is:

1. Ingest forecast data from GRIB2 or NetCDF.
2. Extract the relevant forecast variables using tools such as `xarray` and `cfgrib`.
3. Convert grid cells into spatial features with geometry and timestamps.
4. Join grid cells to power-line segments using spatial intersection.
5. Aggregate values such as maximum wind gust or minimum humidity per segment.

For example, after weather grid cells have been converted to polygons:

```
SELECT
    l.segment_id,
    w.forecast_time,
    MAX(w.wind_gust_mph) AS max_wind_gust,
    MIN(w.humidity_pct) AS min_humidity
FROM power_lines l
JOIN weather_cells w
  ON ST_Intersects(
       l.geometry,
       w.geometry
     )
GROUP BY
    l.segment_id,
    w.forecast_time
```

Both geometry columns must use the same CRS.

For large grids, optimize by filtering to PG&E's service territory first, partitioning by forecast time and region, and using Sedona's spatial join optimization.

For long power lines, a segment can intersect several grid cells. That is why `MAX` wind gust may be more useful than simply taking the nearest weather station.

## 6. Raster data: Vegetation and fuel conditions

Raster processing needs a slightly different approach.

For example, LANDFIRE provides vegetation and fuel characteristics as gridded datasets.

A practical workflow:

```
import rasteriofrom rasterio.mask import mask
```

For each geographic tile:

- Read the relevant raster bands.
- Clip to a corridor around the utility network.
- Compute statistics such as mean vegetation density, dominant fuel type, and maximum slope.
- Write the resulting features to Parquet or Delta.

Avoid loading an entire statewide raster into the Spark driver. Process raster tiles in parallel, using appropriately sized partitions or distributed geospatial tools.

For large-scale production workloads, I would often use dedicated raster processing to create segment-level features, then use Spark to join those features with utility and weather records.

## 7. How to implement the same project in Palantir Foundry

Foundry supports native geospatial transformations through Pipeline Builder, including geometry processing and integration with Ontology objects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir

+1



The main difference is that Foundry can connect the resulting data directly to operational applications.

### Step A: Ingest geospatial datasets

Create datasets in Foundry for:

| Foundry dataset         | Source                       |
| ----------------------- | ---------------------------- |
| `power_lines`           | Utility GIS / asset registry |
| `utility_poles`         | Asset management system      |
| `vegetation`            | LiDAR / tree inspection data |
| `weather_hourly`        | Weather forecasts            |
| `ignition_events`       | Incident management system   |
| `vegetation_treatments` | Maintenance work orders      |

### Step B: Perform spatial transformations

In Pipeline Builder, you can:

1. Parse GeoJSON or shapefiles.
2. Normalize geometry and coordinate systems.
3. Apply geospatial transformations and spatial joins.
4. Calculate proximity and intersection features.
5. Aggregate results into one row per segment and date.

Foundry also supports H3 indexing, which can help organize geographic data into spatial cells.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir



### Step C: Create an Ontology

I would define these objects:

| Object type           | Key properties                            |
| --------------------- | ----------------------------------------- |
| `PowerLineSegment`    | Segment ID, geometry, voltage, risk score |
| `UtilityPole`         | Pole ID, location, age, condition         |
| `VegetationArea`      | Geometry, density, clearance              |
| `WeatherObservation`  | Location, time, wind, humidity            |
| `Inspection`          | Date, condition, findings                 |
| `MitigationWorkOrder` | Segment, action, status, cost             |

Then establish links such as:

`PowerLineSegment → hasPole → UtilityPole`

`PowerLineSegment → nearVegetation → VegetationArea`

`PowerLineSegment → hasWorkOrder → MitigationWorkOrder`

Foundry's Ontology supports `geopoint` for point locations and `geoshape` for lines and polygons. The geoshape value is a valid GeoJSON geometry string in WGS84.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir



### Step D: Build a map application

[Palantir Utility Solutions](https://images.openai.com/static-rsc-4/iDhAngHswSfYoa9XBtbBRTSTv57kzXl7to8FjYlf8xr4POibwN2ujhnp_a9Gu1wl3RDyBiHW-P80y_ZUpkbOODJRaxUyK4o3MGuSkW2LOsbUphVMVSFqeqb_dCgXDbP-0lkL888SKfPd-3AiC7Xi1X1Szb8ItAw2DRsLO0uxSz8?purpose=inline)

[palantir.com](https://www.palantir.com/offerings/utilities/?utm_source=chatgpt.com)

Foundry Map can visualize spatial objects, time-series overlays, and linked network entities. Workshop can be used to build an operational application around these objects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.palantir.com\&sz=32)

Palantir

+1



An analyst could select a high-risk segment and see its equipment condition, nearby vegetation, forecast winds, recent faults, and pending maintenance.

## 8. Build a unified ML feature table

Whether you use PySpark or Foundry, the final dataset should look similar to this:

| Column               | Type    |
| -------------------- | ------- |
| `segment_id`         | STRING  |
| `date`               | DATE    |
| `pole_age_years`     | INT     |
| `conductor_type`     | STRING  |
| `trees_within_10m`   | INT     |
| `nearest_tree_m`     | DOUBLE  |
| `vegetation_density` | DOUBLE  |
| `max_wind_gust_mph`  | DOUBLE  |
| `min_humidity_pct`   | DOUBLE  |
| `fuel_moisture_pct`  | DOUBLE  |
| `faults_last_30d`    | INT     |
| `trimmed_last_90d`   | BOOLEAN |
| `energized_hours`    | DOUBLE  |
| `ignition_next_24h`  | INT     |

One row represents one power-line segment at one prediction date.

For predictive modeling, features must reflect only information available at prediction time. For causal inference, preserve the full history of interventions and pre-treatment conditions.

## 9. How geospatial data supports causal inference

Spatial information is particularly valuable for causal analysis because nearby segments may share weather, terrain, vegetation, and fire exposure.

Suppose we want to measure the effect of tree trimming.

We can construct comparison groups of segments with similar pre-treatment characteristics:

- Similar vegetation density
- Similar wind exposure
- Similar equipment age
- Similar terrain and elevation
- Similar historical ignition risk

Then estimate the effect of trimming using Difference-in-Differences or another suitable quasi-experimental design.

One important complication is spatial interference: trimming one segment may also reduce risk on a nearby segment. A credible causal study should account for neighboring treatments and spatially correlated outcomes.

Another complication is that extreme-weather shutdowns (PSPS) affect energized exposure. Whether to adjust for them depends on the causal estimand and whether they occurred before or after the treatment decision.

## 10. PySpark vs Foundry: Which would I choose?

| Requirement                  | PySpark + Sedona                   | Palantir Foundry                      |
| ---------------------------- | ---------------------------------- | ------------------------------------- |
| Large-scale spatial joins    | Excellent                          | Supported                             |
| Custom geospatial algorithms | Very flexible                      | Possible, with platform constraints   |
| Raster and LiDAR processing  | Strong ecosystem of external tools | May require specialized preprocessing |
| ML training                  | Flexible                           | Integrated                            |
| Causal inference             | Python libraries                   | Python-based implementation           |
| Data lineage                 | Requires platform integration      | Built in                              |
| Business object modeling     | Custom implementation              | Native Ontology                       |
| Operational applications     | Requires additional development    | Strong integrated tooling             |
| Portability                  | Relatively high                    | More platform-dependent               |

My recommendation: For learning or building a prototype, start with PySpark, Apache Sedona, and Delta Lake. It gives you control over the spatial algorithms and the ability to inspect each transformation.

If the organization already uses Palantir Foundry, use Pipeline Builder and Ontology to integrate the data, then build operational applications around the resulting risk models.

### Useful documentation

- [Apache Sedona — Spatial SQL and GeoParquet](https://sedona.apache.org/latest/tutorial/sql/?utm_source=chatgpt.com)
- [Palantir — Geospatial transformations](https://www.palantir.com/docs/foundry/pipeline-builder/transforms-geospatial?utm_source=chatgpt.com)
- [Palantir — Geospatial Ontology](https://www.palantir.com/docs/foundry/geospatial/ontology?utm_source=chatgpt.com)
- [LANDFIRE — Vegetation and fuel datasets](https://www.landfire.gov/?utm_source=chatgpt.com)

For a practical first project, I would implement power-line proximity to vegetation, weather-grid spatial joins, and a segment-day risk feature table. These three components provide a solid foundation for both wildfire prediction and later causal analysis of vegetation management.



# What is raster data?

Raster data is a geospatial data format that represents geographic information as a grid of cells (pixels). Each cell contains a value describing a property of the corresponding geographic area.

For example, a raster dataset can represent temperature, elevation, vegetation density, soil moisture, or wind speed across California.

## 1. Example of raster data

[Digital Elevation Models - February 2, 2026](https://images.openai.com/static-rsc-4/upaNQ-TrG8So171tk3wXDe_6ZDGLS7ZDYlI9_VJtcgqytlqpBzbyNhl3f2QfChkW5LCIsLKfRy68HmcoGRFfykOZa29fdAXhoSpsXFBp6i_vT_BQAvNFvkDeI_7hrvS_FDUiNA5nJ8a1I2mopmrdgQA6rMMCnKBXLg7jfFbQpks?purpose=inline)

[Lesson 5: Raster data analysis – Geospatial Analysis with Python and R](https://images.openai.com/static-rsc-4/1OoPr7HS9rA4c6OwbtrxcosYk2yyAqTID3rwKZNw3TL2nFrPrJ9cFbpdBH0kOYP0vDDk3n074M_4watJvPstaAua2d7bIgM_L_UcrEdKclRTiRpxHAkZCG28EPWEfgr-iXOoUzGXejmp57q41ML-U08ZC-gBtpdm9a7YuFMmJVg?purpose=inline)

[Fintech's Wildfire Fighter: This Reinsurer Is Using A.I. To Make California Insurance Affordable](https://images.openai.com/static-rsc-4/Gz_y1aBBVJraqzr2VbAXrH2m5mYLWlRARfi2KKwd4Qk8MGQkjQBtEG8GQltUq3-52wI6I7E-oFu0fzk3ffJi6gNCv7qjedNzCvN94TMeZuRlZ7Sdm56eXdyLhAZTCNG8xF182YzKrARL-02x6KNDXR633xxZ3DltyaU5xoQGPlA?purpose=inline)

7

Each image represents a geographic area divided into many cells, with values associated with those cells.



A real raster file also contains geographic metadata describing where the grid is located.

## 2. Raster vs vector data

These are the two major geospatial data representations.

| Feature            | Raster                               | Vector                            |
| ------------------ | ------------------------------------ | --------------------------------- |
| Structure          | Grid of pixels                       | Points, lines, polygons           |
| Typical use        | Temperature, elevation, vegetation   | Power lines, poles, roads         |
| Resolution         | Cell size, e.g. 10 × 10 meters       | Geometry coordinates              |
| Data formats       | GeoTIFF, NetCDF, GRIB2               | GeoJSON, Shapefile, GeoParquet    |
| Typical processing | Pixel calculations, zonal statistics | Spatial joins, buffers, distances |

For a PG&E wildfire project, power lines are usually vector data, while vegetation density and weather fields are often raster data.

## 3. Raster resolution

Suppose a vegetation raster has a resolution of 30 meters.

Each pixel represents a geographic area approximately:

\\[ 30 \times 30 = 900\ \text{m}^2 \\]

A 1,000 × 1,000 pixel raster therefore covers approximately 30 × 30 kilometers, assuming square cells in a suitable projected coordinate system.

Smaller pixels provide finer spatial detail but increase storage and processing costs.

## 4. How to read raster data in Python

A popular Python library is `rasterio`.

```
import rasteriowith rasterio.open("vegetation.tif") as src:    data = src.read(1)    print("Width:", src.width)    print("Height:", src.height)    print("CRS:", src.crs)    print("Resolution:", src.res)    print("Shape:", data.shape)
```

The raster is loaded as a NumPy array:

```
print(data[100, 200])
```

This returns the value of a particular pixel (row 100, column 200).

To retrieve the value at a geographic coordinate:

```
with rasterio.open("vegetation.tif") as src:    longitude = -121.85    latitude = 37.30    # Assumes raster CRS is EPSG:4326    value = next(        src.sample([(longitude, latitude)])    )[0]    print(value)
```

If the raster uses another coordinate reference system, transform the longitude and latitude before sampling.

## 5. How raster data is used for PG&E wildfire prediction

Imagine we have:

- A power-line segment represented by a vector `LineString`.
- A vegetation-density raster.
- A wind-speed raster.
- A soil-moisture raster.

We want to calculate the environmental conditions surrounding each power line.

Vegetation density cells

Power line

Analysis corridor

Illustrative raster grid with a power-line corridor crossing multiple cells.

A typical algorithm is:

1. Create a 30-meter buffer around each power-line segment.
2. Find all raster pixels intersecting that buffer.
3. Calculate average vegetation density, maximum wind speed, and minimum soil moisture.
4. Store the results as features for a machine learning model.

For example:

| Segment | Avg. vegetation density | Max wind (mph) | Soil moisture (%) |
| ------- | ----------------------- | -------------- | ----------------- |
| A101    | 0.85                    | 65             | 8                 |
| A102    | 0.30                    | 25             | 35                |
| A103    | 0.72                    | 55             | 12                |

These are illustrative values.

The process of computing raster statistics inside vector geometries is called zonal statistics.

## 6. Can PySpark process raster data?

Yes, but standard PySpark DataFrames are primarily designed for tabular data.

For raster processing, common approaches include:

- Rasterio + NumPy: Useful for small or medium datasets and individual raster tiles.
- Xarray + Dask: Useful for large multidimensional weather and climate datasets.
- Apache Sedona: Distributed geospatial processing, including raster functionality where supported by the installed version.
- PySpark: Distributed joins and aggregation after converting raster information into segment-level features.

For the PG&E wildfire project, I would generally process large raster files into geographic features using Rasterio/Xarray and distributed processing where necessary, then store the extracted features in Delta tables for PySpark analytics.

Key idea: Raster data describes conditions across geographic space, while vector data describes the locations and shapes of objects. Combining them lets you answer questions such as: "What are the vegetation and weather conditions within 30 meters of this power line?"


Wind direction in meteorological datasets is usually stored in one of two ways:

1. As an angle in degrees (0–360°).
2. As two vector components: U (east–west) and V (north–south).

For wildfire modeling, the second representation is especially useful.

## 1. Wind direction as an angle

Meteorological wind direction indicates where the wind comes FROM, not where it is going.

A 45° wind comes from the northeast and blows toward the southwest.

| Direction | Degrees | Wind blows toward |
| --------- | ------- | ----------------- |
| North     | 0°      | South             |
| East      | 90°     | West              |
| South     | 180°    | North             |
| West      | 270°    | East              |
| Northeast | 45°     | Southwest         |

For example, a weather record might be:

```
{
  "timestamp": "2026-10-18T12:00:00Z",
  "latitude": 37.3,
  "longitude": -121.85,
  "wind_speed_mps": 12.5,
  "wind_direction_deg": 270
}
```

This means wind is blowing from the west toward the east at 12.5 m/s.

## 2. Wind direction as U and V components

Numerical weather models commonly store wind as two components:

- `u`: East–west component. Positive means toward east.
- `v`: North–south component. Positive means toward north.

For example:

```
u = 10.0   # m/s toward eastv = -5.0   # m/s toward south
```

The wind is blowing toward the southeast.

The speed is:

\\[ \text{speed}=\sqrt{u^2+v^2} \\]

And the meteorological direction is:

\\[ \theta = \left( \operatorname{atan2}(-u,-v)\frac{180}{\pi}+360 \right)\bmod 360 \\]

### Python example

```
import numpy as npu = 10.0v = -5.0speed = np.hypot(u, v)direction = (    np.degrees(np.arctan2(-u, -v)) + 360) % 360print(f"Speed: {speed:.2f} m/s")print(f"Direction: {direction:.1f}°")
```

Output:

```
Speed: 11.18 m/s
Direction: 296.6°
```

That is a wind from west-northwest, blowing toward east-southeast.

For calm wind (`u = v = 0`), direction is undefined and should normally be stored as null rather than 0°.

## 3. How wind is stored in raster datasets

In a weather forecast such as NOAA HRRR, wind components can be stored as two separate raster grids:

U-component raster (m/s)

5

8

10

6

9

12

4

7

11

V-component raster (m/s)

-2

-4

-5

-3

-5

-6

-1

-3

-4

Each geographic cell has both U and V values. Together they describe the wind vector at that location and forecast time.

Some GRIB2 products store grid-relative rather than earth-relative wind components, so check the metadata and rotate components when necessary.

## 4. Why wind direction matters for PG&E wildfire modeling

Wind direction can be important in two ways.

A. Vegetation contact with power lines

If a tree is located west of a power line and strong winds blow toward the east, the tree may be pushed toward the line.

B. Wildfire spread

Wind direction influences the direction and speed of fire spread after ignition, along with fuel, terrain, and atmospheric conditions.

For predictive modeling, I would preserve the original `u` and `v` components instead of using only the wind direction angle.

This avoids the discontinuity between 359° and 0°, which are almost identical directions but numerically very different.

A useful feature table might contain:

| segment_id | wind_u | wind_v | wind_speed | wind_direction |
| ---------- | ------ | ------ | ---------- | -------------- |
| A101       | 10.0   | -5.0   | 11.18      | 296.6°         |
| A102       | -4.0   | 3.0    | 5.00       | 126.9°         |

An even more useful feature for PG&E would be the wind component perpendicular to a power line. This measures how strongly the wind blows across the line rather than along it.

If a line has unit tangent vector \\((t_x,t_y)\\), the signed cross-line wind component is:

\\[ w\_{\perp}=u(-t_y)+v t_x \\]

Its absolute value, \\(|w\_{\perp}|\\), measures the cross-line wind speed. Combined with tree locations, conductor geometry, and vegetation characteristics, it can help model the risk of vegetation contacting electrical infrastructure.


# GeoJSON, Shapefiles, and H3 Spatial Index

All three are used in geospatial data engineering, but they serve different purposes:

- GeoJSON — stores geographic objects in JSON format.
- Shapefile — a traditional GIS file format for storing geographic objects and their attributes.
- H3 — a hierarchical spatial indexing system that divides the Earth's surface into hexagonal cells.

For a PG&E wildfire risk project, you might use GeoJSON or Shapefiles to store power-line geometry and vegetation boundaries, and H3 to efficiently combine those datasets with weather and wildfire information.

## 1. GeoJSON

GeoJSON is a JSON-based format for representing geographic objects.

It supports three fundamental geometry types:

Point - Utility pole

LineString - Power line

Polygon - Vegetation area

### Example: A power line stored in GeoJSON

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [-121.85, 37.30],
      [-121.84, 37.31]
    ]
  },
  "properties": {
    "segment_id": "PG001",
    "voltage_kv": 12,
    "conductor": "overhead",
    "installation_year": 1995
  }
}
```

Notice the separation between:

- `geometry`: The geographic shape.
- `properties`: Attributes describing that shape.

GeoJSON uses longitude, latitude coordinate order, normally in WGS84 (EPSG:4326).

### Python example

```
import geopandas as gpd
gdf = gpd.read_file("power_lines.geojson")
print(gdf.head())
print(gdf.crs)
```

GeoPandas creates a DataFrame containing regular columns plus a special `geometry` column.

Advantages: Human-readable, easy to exchange through APIs, and well supported by Python and GIS software.

Disadvantages: Verbose, relatively large, and not particularly efficient for processing millions of geographic features.

## 2. Shapefile

A Shapefile is a widely used GIS format developed by Esri.

Despite its name, a Shapefile is actually a collection of files.

For example:

```
power_lines.shp
power_lines.shx
power_lines.dbf
power_lines.prj
```

| File   | Purpose                                |
| ------ | -------------------------------------- |
| `.shp` | Stores geometry                        |
| `.shx` | Index of geometry records              |
| `.dbf` | Attribute table                        |
| `.prj` | Coordinate reference system definition |

The `.prj` file is important for interpreting coordinates correctly, although it is not mandatory in every Shapefile dataset.

### Example data

A Shapefile representing power lines might contain:

| segment_id | voltage | geometry   |
| ---------- | ------- | ---------- |
| PG001      | 12      | LineString |
| PG002      | 21      | LineString |
| PG003      | 12      | LineString |

The actual geometry is stored in binary form rather than JSON text.

### Python example

```python
import geopandas as gpd

gdf = gpd.read_file("power_lines.shp")

print(gdf.head())

# Convert Shapefile to GeoJSON
gdf.to_file(
    "power_lines.geojson",
    driver="GeoJSON"
)
```

Shapefiles are still common in government GIS datasets, but they have limitations such as short attribute field names, restricted attribute types, and legacy file-size constraints.

For a new large-scale PySpark project, I would generally convert Shapefiles into GeoParquet, which is more suitable for analytical pipelines.

## 3. H3 spatial index

H3 was originally developed by Uber.

Unlike GeoJSON or Shapefiles, H3 is not primarily a geometry storage format.

It is a hierarchical spatial indexing system.

H3 divides the Earth into cells at different resolutions. Most cells are hexagons, although a small number are pentagons.

Conceptual illustration of H3 cells covering a geographic region. Actual H3 cell shapes and alignment vary across the Earth.

Each H3 cell has a unique identifier, such as:

```
8928308280fffff
```

An H3 index encodes the cell's location and resolution.

### H3 resolutions

H3 supports resolutions from 0 (coarsest) to 15 (finest).

| Resolution | Average cell area (approx.) | Example use                                   |
| ---------- | --------------------------- | --------------------------------------------- |
| 5          | 253 km²                     | Regional analysis                             |
| 7          | 5.16 km²                    | Broad wildfire risk mapping                   |
| 9          | 0.105 km²                   | Local vegetation and weather analysis         |
| 11         | 2,150 m²                    | Detailed infrastructure neighborhood analysis |
| 13         | 43.9 m²                     | Very fine spatial aggregation                 |

These are average areas, not exact sizes for every cell.

### Python example

Install the H3 library:

```
pip install h3
```

Convert GPS coordinates into an H3 cell:

```python
import h3

lat = 37.30
lon = -121.85

cell = h3.latlng_to_cell(lat, lon, 9)

print(cell)

# Get the hexagon boundary
boundary = h3.cell_to_boundary(cell)
```

Notice that the H3 function accepts latitude first, longitude second, unlike GeoJSON coordinate arrays.

## 4. Why H3 is useful for PySpark

Suppose we have:

- 10 million vegetation observations.
- 1 million power-line segment records.
- Hourly weather observations across California.

A direct spatial join may require expensive geometry calculations.

One optimization is to assign geographic objects to H3 cells.

For example:

| H3 cell | Tree count | Wind speed | Power-line length |
| ------- | ---------- | ---------- | ----------------- |
| Cell A  | 125        | 45 mph     | 1,200 m           |
| Cell B  | 38         | 25 mph     | 800 m             |
| Cell C  | 210        | 65 mph     | 1,500 m           |

Then Spark can perform ordinary equality joins on the H3 cell ID.

```python
joined = (
    vegetation_h3
    .join(weather_h3, on="h3_cell")
    .join(powerlines_h3, on="h3_cell")
)
```

This is much cheaper than performing millions of exact geometric comparisons in many cases.

However, there is an important limitation: H3 cell membership is an approximation of geographic relationships.

Two objects can be very close but belong to adjacent cells. A long power line can also cross many cells.

For exact distance or intersection analysis, use H3 to identify candidate objects, then apply a precise spatial predicate such as `ST_DWithin` or `ST_Intersects`.

## 5. H3 and power lines: An important detail

For points, assigning an H3 index is straightforward.

For a LineString, using only its midpoint is often incorrect.

A power line might cross many H3 cells.

The correct approach is to find all cells intersected by the line, or by a buffer around it, using an appropriate geometry-to-cell covering method. Then explode the cell IDs into multiple rows.

Conceptually:

```
segment_id    h3_cell
----------    -------
PG001         Cell_A
PG001         Cell_B
PG001         Cell_C
PG002         Cell_C
PG002         Cell_D
```

This creates a many-to-many relationship between power lines and H3 cells.

When using polygon-based H3 covering functions, check whether they use cell-center containment or geometric intersection; these have different boundary behavior.

## 6. Which format should you use for PG&E wildfire risk modeling?

| Requirement                                  | Recommended technology |
| -------------------------------------------- | ---------------------- |
| Exchange geospatial data with APIs           | GeoJSON                |
| Read legacy GIS datasets                     | Shapefile              |
| Store millions of spatial features           | GeoParquet             |
| Fast geographic grouping and candidate joins | H3                     |
| Exact proximity between trees and lines      | Apache Sedona          |
| Process satellite and weather grids          | Rasterio / Xarray      |
| Distributed feature engineering              | PySpark + Sedona + H3  |

For a production-style architecture, I would use:

Shapefile / GeoJSON / GeoTIFF → GeoParquet / Delta → H3 candidate joins + Sedona exact geometry → Segment-level ML features.

The key distinction is that GeoJSON and Shapefiles represent the actual geometry of objects, whereas H3 provides a geographic indexing system that makes it easier to group and join large spatial datasets.

For wildfire risk management, they are complementary rather than competing technologies.
