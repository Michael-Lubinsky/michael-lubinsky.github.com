## Apache Doris

StarRocks is a fork of Apache Doris. Both are open-source, distributed OLAP databases designed for fast analytical SQL queries.

They share a common origin and many architectural concepts, but have evolved into separate database systems.

## 1. Historical relationship

Baidu Palo

Original analytical database developed at Baidu

Apache Doris

Open-source Apache project

Apache Doris

Continued development under Apache Software Foundation

StarRocks

Forked in 2021; independent development

The important milestones:

- 2017: Baidu open-sourced Palo, the technology that became Apache Doris.
- 2018: Doris entered the Apache incubator.
- 2021: StarRocks emerged as a fork of Doris.
- 2022: Apache Doris became an Apache top-level project.
- 2023: StarRocks joined the Linux Foundation.

Both projects continue to be actively developed.

## 2. What do they have in common?

Both databases support:

- Distributed MPP (Massively Parallel Processing) architecture.
- C++ backend and Java frontend.
- Columnar storage and vectorized query execution.
- Cost-based query optimization.
- Real-time data ingestion.
- Materialized views.
- Primary-key or unique-key updates.
- SQL queries against external data lakes.
- Self-hosted deployment and commercial managed services.

The similarities are substantial.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://doris.apache.org\&sz=32)

Apache Doris+1



## 3. How are they different today?

| Feature                     | Apache Doris                 | StarRocks                                      |
| --------------------------- | ---------------------------- | ---------------------------------------------- |
| Governance                  | Apache Software Foundation   | Linux Foundation                               |
| Original codebase           | Baidu Palo                   | Fork of Doris                                  |
| Query engine                | Modern vectorized MPP engine | Independently rewritten vectorized MPP engine  |
| Lakehouse integration       | Yes                          | Yes, major area of focus                       |
| Materialized views          | Yes                          | Yes, with strong emphasis on query rewrite     |
| Real-time updates           | Yes                          | Yes                                            |
| Shared-storage architecture | Yes                          | Yes                                            |
| Search capabilities         | Inverted and vector indexes  | Search and vector capabilities vary by version |
| License                     | Apache 2.0                   | Apache 2.0                                     |
| Commercial ecosystem        | VeloDB and others            | CelerData                                      |

StarRocks substantially rewrote its original query engine after the fork, introducing its own optimizer and execution pipeline. Doris has also modernized its engine, so the old distinction that only StarRocks has advanced vectorized execution is no longer accurate.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://medium.com\&sz=32)

Medium+1



## 4. Which one should you choose?

For your interest in Databricks, Snowflake, and real-time telemetry analytics, I would evaluate both using the same workload.

StarRocks is particularly interesting if you want to accelerate queries over Iceberg or Delta Lake and serve interactive analytics using materialized views.

Apache Doris is particularly interesting if you need a unified analytical database with real-time ingestion, flexible indexing, and integrated search-oriented features.

Neither database is universally faster. The winner depends on the SQL queries, table design, ingestion rate, concurrency, and deployment configuration.

## 5. Source code

[Doris 配置参数 - WeaveHan](https://images.openai.com/static-rsc-4/XViZTZK_95Yau2Dh5njHacFCOU26Olg8S1kRe7O3ObwDjhueCewbB2PTYnHwAq0Fcq0TJ0WiHJUwyuVoUi4oP_aRdm9_xFwM0KoLXBNvY7WtzVlwGx4L5ssigZOttOToFNHYZygotrYD8xS05RFDf7Kmii3JtjFdyuYU3Ur7Czc?purpose=inline)

Apache Doris

[github.com/apache/doris](https://github.com/apache/doris?utm_source=chatgpt.com)

StarRocks

[github.com/StarRocks/starrocks](https://github.com/StarRocks/starrocks?utm_source=chatgpt.com)

One useful technical exercise would be to compare their C++ query execution engines. Because StarRocks originated from Doris but subsequently rewrote substantial portions of its engine, the two projects provide an interesting case study in how different architectural choices affect analytical database performance.

<https://habr.com/ru/articles/950214/>

<https://www.velodb.io/blogs>

<https://www.velodb.io/ebooks-slides>
