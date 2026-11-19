## Databricks

Book:
<https://github.com/bartosz25/data-engineering-design-patterns-book>

<https://www.linkedin.com/pulse/navigating-modern-data-platform-landscape-databricks-vs-tony-nguyen-oevic/>

<https://login.databricks.com/>

CDC with Databricks <https://www.youtube.com/watch?v=xN4yUAHiMA0>

### Genie one

<https://learn.microsoft.com/en-us/azure/databricks/genie-agents/concepts>

<https://medium.com/tag/genie-one>

<https://medium.com/@hiydavid/genie-one-my-daily-ai-coworker-2579b0903e57>

<https://medium.com/@abhishek.iyer327/how-do-you-connect-claude-to-enterprise-data-so-it-gets-the-numbers-right-4f7e26575ea5>

## Deploing Databricks

<https://medium.com/databrickscommunity/what-makes-up-a-databricks-project-36a695f393ee>


<img width="1280" height="645" alt="telegram-cloud-photo-size-1-4983758855351241628-y" src="https://github.com/user-attachments/assets/ffb894de-7d2d-4c65-9f64-f3b573c5977f" />


<img width="1280" height="742" alt="telegram-cloud-photo-size-1-4983758855351241630-y" src="https://github.com/user-attachments/assets/d1f1fda4-9442-4f6a-81b8-66bd804049da" />

<img width="1280" height="652" alt="telegram-cloud-photo-size-1-4983758855351241632-y" src="https://github.com/user-attachments/assets/90977162-0718-4add-9859-69fdc947c8b6" />

<https://medium.com/towards-data-engineering/databricks-data-engineering-interview-questions-expert-level-part-5-2f4724d3d607>


##   How to optimize Spark jobs for performance in Databricks?
Optimizing Apache Spark jobs in Databricks requires efficient resource allocation, data processing optimizations, and query tuning. Below are the key best practices:

### 1. Optimize Data Handling
Use Delta Lake instead of Parquet for transactional consistency and faster query performance.

Partitioning & Z-Ordering:

Partition data on high-cardinality columns.
Use Z-ORDER BY for optimizing frequently queried columns.
```
df.write.format("delta").partitionBy("year").save("/mnt/delta_table") 
OPTIMIZE delta.`/mnt/delta_table` ZORDER BY (customer_id);
```
Automatic Cleanup:
```
VACUUM delta.`/mnt/delta_table`  RETAIN 168 HOURS;
```
### 2. Computation Tuning

Use DataFrames Instead of RDDs: DataFrames leverage Catalyst optimizer for better execution plans.
Optimize Shuffle Operations:
Reduce shuffle partitions:
```
spark.conf.set("spark.sql.shuffle.partitions", "200")
```
Avoid Skewed Joins using salting:
```python
from pyspark.sql.functions 
import col, lit 

df = df.withColumn("salt", (col("id") % 10))
```
Broadcast Small Tables:
```
from pyspark.sql.functions 

import broadcast 
df_result = df_large.join(broadcast(df_small), "join_key")
```
### 3. Cluster Configuration
Enable Auto Scaling: Dynamically adjust resources based on workload.

Use Compute-Optimized Instances (c5d.2xlarge) for transformations and Memory-Optimized Instances (r5d.2xlarge) for joins.

Enable Photon Engine for SQL Processing:
```
SET spark.databricks.photon.enabled = true;
```
### 4. Optimizing Structured Streaming
Use Watermarking to Handle Late Arriving Data:
```python
df.withWatermark("event_time", "10 minutes")
Trigger-Based Execution:

df.writeStream.trigger(processingTime="1 minute").start()
```

##  How does Databricks handle schema evolution in Delta Lake?
Schema evolution in Delta Lake ensures that as data changes, tables adapt without breaking pipelines.

1. Schema Enforcement
By default, Delta Lake rejects schema mismatches to prevent accidental corruptions.
```
df.write.format("delta").mode("append").save("/mnt/delta_table")
```
If a new column is added without explicitly enabling schema evolution, Spark throws an error.

2. Enabling Schema Evolution (mergeSchema)
To allow new columns dynamically:
```
df.write.option("mergeSchema", "true").mode("append").format("delta").save("/mnt/delta_table")
```
This adds new columns but does not modify existing columns.

3. Auto Schema Evolution in MERGE. 
For updates in MERGE statements, use:

```python
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

deltaTable.alias("tgt").merge(
    df_new.alias("src"), "tgt.id = src.id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

4. Handling Schema Evolution in Streaming
Use Auto-Merge for Streaming Writes:
```
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true") 

df.writeStream.format("delta").option("checkpointLocation", "/mnt/checkpoint").start("/mnt/delta_table")
```
5. Safe Schema Updates with Deep Cloning
To preserve old schema while evolving the new one:
```
CREATE TABLE delta_clone DEEP CLONE delta_table;
```
### Use of Databricks Workflows and their benefits

1. What are Databricks Workflows?
Databricks Workflows is a fully-managed orchestration service for scheduling and automating tasks within Databricks. It serves as a simplified alternative to Apache Airflow.

2. Key Benefits of Databricks Workflows
Press enter or click to view image in full size

3. Creating a Workflow

Define a workflow with two dependent tasks:
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
job = w.jobs.create(
    name="Data Pipeline Workflow",
    tasks=[
        {
            "task_key": "extract",
            "notebook_task": {"notebook_path": "/Repos/extract_data"},
            "job_cluster_key": "compute-cluster"
        },
        {
            "task_key": "transform",
            "depends_on": [{"task_key": "extract"}],
            "notebook_task": {"notebook_path": "/Repos/transform_data"}
        }
    ]
)
```
4. Handling Failures and Alerts
Automatic Retries:
```
"max_retries": 3
Email Notifications:

"email_notifications": {"on_failure": ["user@example.com"]}
```
### What are the key differences between Delta Lake and Parquet?
1. Overview
Delta Lake builds on top of Parquet but provides ACID transactions, schema enforcement, and time travel.

2. Key Differences
Press enter or click to view image in full size

3. Querying Delta Lake with Time Travel. 
df = spark.read.format("delta").option("versionAsOf", 5).load("/mnt/delta_table")

4. Converting Parquet to Delta. 
spark.read.parquet("/mnt/parquet_table").write.format("delta").save("/mnt/delta_table")

5. When to Use Parquet Over Delta?
Cold Storage: If data is archived and infrequently accessed, Parquet is more cost-effective.

Cross-Platform Interoperability: Parquet is widely supported across platforms, whereas Delta Lake requires Databricks or Delta connectors.

This concludes Part 5 of the Databricks Data Engineering Interview Series. 
<https://medium.com/towards-data-engineering/databricks-declarative-pipelines-how-databricks-dlt-saved-my-day-d95cc72db2b5>

### Databricks vs Snowflake
<https://medium.com/@hugolu87/databricks-vs-snowflake-the-final-chapter-long-read-371cf3d7e572>

## Databricks certification

https://www.databricks.com/sites/default/files/2026-04/databricks-certified-data-engineer-associate-exam-guide-may-4-2026-new.pdf

https://www.linkedin.com/feed/update/urn:li:activity:7454845458109198336/

https://www.alexcole.net/databricks-data-engineer-associate-certification-guide/

https://medium.com/@gema.correa/how-i-prepared-for-and-passed-the-databricks-certified-machine-learning-professional-exam-c741cfca259e

### Databricks 𝗗𝗮𝘁𝗮 𝗘𝗻𝗴𝗶𝗻𝗲𝗲𝗿𝗶𝗻𝗴 𝗣𝗿𝗼𝗳𝗲𝘀𝘀𝗶𝗼𝗻𝗮𝗹 𝗰𝗲𝗿𝘁𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻

it covers a wider range of concepts like Delta Live Tables (DLT), Unity Catalog, Apache Spark, Delta Lake, MLflow, Databricks CLI, and a lot more. It took me around 4 weeks to prepare.

As per the official Databricks guide, the exam consists of 60 questions,   You get 2 hours to complete it. Need to manage time, as the questions are too lengthy.  

Here’s how the topics are distributed:
```
• Data Processing (30%)
• Databricks Tooling (20%)
• Data Modeling (20%)
• Security & Governance (10%)
• Monitoring & Logging (10%)
• Testing & Deployment (10%)
```
 

Since there’s no official practice test from Databricks, it was a bit difficult to test knowledge — but there are a few good ones available on Udemy if you want extra practice.

𝗥𝗲𝘀𝗼𝘂𝗿𝗰𝗲𝘀:

1) Databricks Learning Academy (Self-paced learning course)

2) Advanced Data Engineering course material (Databricks Notebooks + Slides): https://lnkd.in/eHtyrp9B

3) YouTube tutorials—‘𝗘𝗮𝘀𝗲 𝘄𝗶𝘁𝗵 𝗗𝗮𝘁𝗮’ by Subham Khandelwal
https://lnkd.in/eZ8bfARx


https://blog.det.life/i-passed-the-databricks-certified-associate-developer-for-apache-spark-exam-heres-how-you-can-too-6c2f9b66fdb5

 
Derar Alhussein for his well-structured Udemy course:
 🔗 Databricks Certification Course
https://lnkd.in/gr4-YHMH  

Ansh Lamba for his free and practical YouTube series :
 🔗 YouTube Course
https://lnkd.in/gs-JGDNz

4 Certifications Completed on My Data Journey ✨
▸ Databricks Data Engineer Professional
▸ Microsoft DP-700: Data Analyst Associate
▸ Microsoft DP-600: Fabric Analytics Solution Expert
▸ Databricks Data Engineer Associate


## In Databricks GUI under given schema there are following tables:

- Tables
- Flows
- Volumes
- Software Artifacts
- Models
- Functions
- Secrets
- Services
- Skills
- Connections

 
Those tabs group the different **data, software, and AI assets associated with a schema**. A Databricks schema can contain much more than tables; Unity Catalog controls access to these assets. See the [Unity Catalog object reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/securable-objects).

| Tab | What it contains and when you use it | Official documentation |
|---|---|---|
| **Tables** | Structured datasets organized into rows and columns, queried using SQL or Spark. Examples: customers, orders, transactions. Tables can be **managed** by Databricks, **external**, or **foreign** tables referencing another system. | [Tables overview](https://docs.databricks.com/aws/en/tables/table-overview) |
| **Flows** | Pipeline queries that incrementally load and transform data into a target streaming table or materialized view. Examples: append new events or apply change data capture (CDC). A flow belongs to a Lakeflow pipeline; Unity Catalog lets you grant permissions on individual flows. **Beta.** | [Flows in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/flows) |
| **Volumes** | Governed storage for **files**: CSVs, JSON, PDFs, images, libraries, and other files. Use a volume when you need file access, such as `/Volumes/catalog/schema/volume/file.csv`. Volumes can be managed or external. | [Volumes overview](https://docs.databricks.com/aws/en/files/volumes) |
| **Software Artifacts** | Container images stored in **Artifact Registry**, with versions identified by tags or immutable digests. For example, a Docker image containing your application and its dependencies for a supported Databricks workload. **Public Preview.** | [Artifact Registry](https://docs.databricks.com/aws/en/artifact-registry/) |
| **Models** | Registered machine learning and AI models, managed through MLflow and Unity Catalog. You can track model versions, assign aliases, manage permissions, and inspect lineage. Example: a versioned fraud detection model. | [Manage model lifecycle in Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle) |
| **Functions** | Registered, reusable functions that other queries or workloads can call. Examples: calculate a business metric, normalize a value, or mask an email address. Functions can return a single value or a set of rows. | [Unity Catalog functions](https://docs.databricks.com/aws/en/udf/unity-catalog) |
| **Secrets** | Sensitive values such as passwords, API keys, and tokens, governed individually through Unity Catalog. Applications and notebooks can retrieve authorized secrets without hardcoding them. These are separate from workspace-level secret scopes. | [Secrets in Unity Catalog](https://docs.databricks.com/aws/en/security/secrets/unity-catalog-secrets) |
| **Services** | Governed, callable AI assets: **model services**, **model provider services**, **MCP services**, and **agent services**. Use them to control who can invoke models, agents, or tools exposed through Model Context Protocol (MCP). These service types are currently **Beta**. | [Service object reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/securable-objects#service) |
| **Skills** | Published instruction packages that teach an AI agent how to perform a task. A skill contains a `SKILL.md` file and optional supporting resources. Examples: your team’s SQL conventions or an incident investigation runbook. Unity Catalog governs discovery and access. **Beta.** | [Skills support in Unity Gateway](https://docs.databricks.com/aws/en/agents/uc-skills) |
| **Connections** | Governed endpoint and authentication settings for accessing external systems. Schema-level HTTP connections, for example, let code call external REST APIs and support MCP services without embedding credentials in code. Connections can also exist at metastore level. | [External HTTP connections](https://docs.databricks.com/aws/en/query-federation/http), [Connection API and schema scope](https://docs.databricks.com/api/uc-connections/v1/connection) |

For example, one project schema could hold an **orders table**, a **flow** that updates it, a **volume** of incoming files, a prediction **model**, reusable **functions**, and the **secrets/connections** needed to access external APIs.

One documentation mismatch: although you see a **Software Artifacts** tab, the current Artifact Registry documentation still says Catalog Explorer does not provide an image interface. That tab may be ahead of the documented UI support; the documentation directs users to the Software Artifacts API for discovery. [Artifact Registry limitations](https://docs.databricks.com/aws/en/artifact-registry/#limitations)

The links above use the AWS documentation edition; availability and preview status can vary by cloud and workspace.
 
Each tab lists one kind of Unity Catalog object stored in that schema. Every object has a three-part name, `catalog.schema.object`, and its access is controlled by grants on the catalog and schema. Tables, Volumes, Models and Functions are long-standing, stable features. The other six are newer and some are still in Beta or Preview, so your workspace may not show all of them.

| Tab | What it holds | Status | Official docs |
|---|---|---|---|
| **Tables** | Tables, views, materialized views and streaming tables: your structured data, usually Delta. | Generally available | [Tables](https://docs.databricks.com/aws/en/tables/) |
| **Flows** | Lakeflow (formerly DLT) pipeline flows that load data into a target table, now managed as their own objects. Permissions are `CREATE FLOW`, `READ FLOW`, `REFRESH FLOW` and `WRITE FLOW`. | **Beta** since Nov 12, 2026. You join it through your Databricks account team. | [Pipeline flows](https://docs.databricks.com/aws/en/ldp/concepts/flows) · [Nov 2026 release notes](https://docs.databricks.com/aws/en/release-notes/product/2026/november) |
| **Volumes** | Files that aren't tables, such as images, CSVs, PDFs and wheels, at paths like `/Volumes/cat/schema/vol/...`. | Generally available | [Volumes](https://docs.databricks.com/aws/en/volumes/) |
| **Software Artifacts** | Container images from **Artifact Registry**, with tags and digests. Who can publish or pull them is controlled by Unity Catalog permissions. | Newer feature | [Artifact Registry](https://docs.databricks.com/aws/en/artifact-registry/) |
| **Models** | ML models and models registered with MLflow, with versions and aliases such as `@champion`. | Generally available | [Model lifecycle in UC](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/) |
| **Functions** | SQL and Python functions (UDFs) that you can call in queries or use as tools for AI agents. | Generally available | [UDFs in Unity Catalog](https://docs.databricks.com/aws/en/udf/unity-catalog) |
| **Secrets** | Sensitive values such as API keys and passwords, used in code without showing the value. Permissions are `READ`, `WRITE` and `REFERENCE SECRET`. A schema can also read its secrets from an outside secret manager, in which case they're read-only in Databricks. | Newer feature | [Secrets in Unity Catalog](https://docs.databricks.com/aws/en/security/secrets/unity-catalog-secrets) |
| **Services** | AI endpoints, created with `CREATE SERVICE`: model services, model provider services, **MCP services** (outside MCP servers) and **agent services**. You can't create them in SQL; use the UI or the REST API. | Some parts are Beta (Unity Gateway) | [MCP Services](https://docs.databricks.com/aws/en/ai-gateway/register-mcp-service) · [Agent Services](https://docs.databricks.com/aws/en/ai-gateway/agent-services) |
| **Skills** | Agent skills: folders with a `SKILL.md` that you publish to a schema. Agents and coding tools find them through the Databricks Skills MCP server or the `ug` CLI. | **Preview**. An admin turns it on from the Previews page. | [Skills in Unity Gateway](https://docs.databricks.com/aws/en/agents/uc-skills/) · [Create & share skills](https://docs.databricks.com/aws/en/agents/uc-skills/create-share-uc-skills) |
| **Connections** | Saved connection details (host and credentials) for outside systems, such as HTTP APIs, MCP servers and federated databases. MCP and agent services use these. Connections can now be created at the schema level, which needs `CREATE CONNECTION` on the schema. | Schema-level HTTP connections are generally available | [UC connections](https://docs.databricks.com/aws/en/connect/uc-connections) · [HTTP connections](https://docs.databricks.com/aws/en/query-federation/http) |

How the newer tabs fit together:
- A **Connection** stores how to reach an outside system.
- **Services** (MCP or agent) are built on top of that connection.
- **Functions**, **Services** and **Skills** are what AI agents use as tools.
- **Secrets** hold the credentials they all need.

For the full list of object types and their permissions, see [Securable objects reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/securable-objects) and [Privileges reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference).

**Caveats:**
- The links point to the AWS docs. Azure and GCP have matching pages; replace `/aws/` in the URL with `/azure/` or `/gcp/`.
- I couldn't find Databricks' own documentation of this exact tab layout, only of the objects behind each tab. The descriptions above come from the docs for those objects.
- The Beta and Preview pages change often, so check them before relying on specific steps.
- To get Beta or Preview features turned on, or to get permissions in TRI's workspace, ask your Databricks workspace admin or TRI IT.

### virtual-learning-festival-9-april-30-apri

https://community.databricks.com/t5/events/virtual-learning-festival-9-april-30-april/ec-p/111620#M2286

Databricks Tutorial (From Zero to Hero) | Azure Databricks Masterclass
https://lnkd.in/ejy68rEc

https://databrickster.medium.com/

https://blog.devgenius.io/14-critical-databricks-mistakes-advanced-developers-make-security-workflows-environment-7da269c46795

PySpark Tutorial | Full Course (From Zero to Pro!)
https://lnkd.in/erj2swjE

https://awstip.com/100-days-of-data-engineering-on-databricks-day-22-writing-efficient-python-code-for-data-cdde7c4b47c1


https://learn.microsoft.com/en-us/azure/databricks/languages/python

https://medium.com/dbsql-sme-engineering/databricks-sql-orchestration-patterns-with-for-each-and-dynamic-value-references-18bba1696577

https://blog.det.life/10-essential-commands-to-boost-your-productivity-in-databricks-4f3586ddb528

https://customer-academy.databricks.com/learn/signin

https://medium.com/@infinitylearnings1201

https://awstip.com/100-days-of-data-engineering-on-databricks-day-49-understanding-acid-transactions-in-delta-lake-eed18c2dc166

https://awstip.com/100-days-of-data-engineering-on-databricks-day-39-understanding-joins-in-spark-4-0-8fd80ba3655b

https://awstip.com/databricks-data-engineering-interview-question-3-can-you-explain-the-architecture-of-databricks-b9c1fef6f398

https://surajskfgi.medium.com/beginners-guide-to-databricks-file-system-dbfs-what-it-is-and-how-to-use-it-7c55952aab4c 

https://medium.com/@24chynoweth/databricks-system-tables-a-bunch-of-queries-ff9e0aa295e1

https://databrickster.medium.com/sql-parameterization-in-databricks-sql-de32a38865b9

https://medium.com/dbsql-sme-engineering

https://medium.com/dbsql-sme-engineering/query-tuning-in-dbsql-with-the-new-v2-query-profile-3cd9802cbd8c

https://ganeshchandrasekaran.com/databricks-using-python-logging-module-in-notebooks-6348bbb3ac60
