## Graph  Databases and Visualization

### Graphology <https://graphology.github.io/> JS graph 
Along with this Graph object, one will also find a comprehensive standard library full of graph theory algorithms and common utilities such as graph generators, layouts, traversals etc.

Finally, graphology graphs are able to emit a wide variety of events, which makes them ideal to build interactive renderers for the browser. It is for instance used by sigma.js as its data backend.


<https://www.sigmajs.org/> JS graph visualisation

### Boost Graph Library

<https://491.graph.prtest3.cppalliance.org/graph/index.html>

### Graph Databases

<https://gdb-engines.com/>

<https://habr.com/ru/companies/yandex/articles/1046483/>

<https://ladybugdb.com/> Graph DB

<https://theconsensus.dev/p/2026/05/29/ladybug-duckdb-and-postgresql.html>

### Postgres Graph
<https://www.postgresql.org/docs/19/ddl-property-graphs.html> Postgres 19 Graph


SQL/PGQ: графовые запросы без отдельной графовой БД

 нативные property-graph запросы по стандарту SQL/PGQ (часть SQL:2023, GRAPH_TABLE).   
 Ключевое, что многие пропускают: это не новое хранилище. Граф описывается как метаданные поверх таблиц, которые у вас уже есть — фактически view.   
 Данные не дублируются и не синхронизируются, Postgres переписывает graph-паттерн в обычные джойны на этапе планирования.

-- граф — это метаданные над существующими users/posts/follows
```sql
CREATE PROPERTY GRAPH social_graph
  VERTEX TABLES (
    users LABEL person PROPERTIES (id, name),
    posts LABEL post   PROPERTIES (id, title)
  )
  EDGE TABLES (
    follows
      SOURCE KEY (follower_id) REFERENCES users (id)
      DESTINATION KEY (followed_id) REFERENCES users (id)
      LABEL follows
  );

-- на кого подписана Alice
SELECT followed_name
FROM GRAPH_TABLE (social_graph
  MATCH (a IS person WHERE a.name = 'Alice')
        -[IS follows]->
        (b IS person)
  COLUMNS (b.name AS followed_name)
);
```

То, что раньше было лесенкой из самоджойнов или рекурсивного CTE, становится читаемым паттерном (a)-[follows]->(b).   
Для follower-графов, деревьев зависимостей, тегов и прочих связей средней глубины это снимает реальную боль — и убирает из стека отдельный Neo4j, который держали только ради двух графовых запросов.  


Но честная граница Beta 1: переменной длины пути пока нет. Т
о есть «найди всех, до кого можно дойти за 1…N переходов» (классический обход графа неизвестной глубины) этим синтаксисом ещё не выразить — это всё ещё территория рекурсивных CTE или специализированных графовых движков. 
Так что SQL/PGQ закрывает паттерны фиксированной глубины, а не заменяет графовую БД целиком.

<https://www.puppygraph.com/>

<https://www.helix-db.com/> HelixDB is an OLTP graph-vector database built in Rust.

<https://github.com/HelixDB/helix-db/tree/main> HelixDB is an OLTP graph-vector database built in Rust.

<https://habr.com/ru/articles/1044164/> AlloyDB

 <https://github.com/ontograph/ontoindex>


 

## What is LadybugDB?

LadybugDB (formerly known as Kuzu) is an embedded graph database built for query speed and scalability, optimized for complex analytical workloads on very large graphs. It provides full-text search, vector indices, a property graph data model, and uses the Cypher query language.

It uses columnar storage with vectorized execution for fast analytical queries, has zero external dependencies, and is designed to run anywhere — edge, embedded, or cloud — making it well-suited for agentic applications.

---

## Comparison with Other Graph Databases

| Feature | **LadybugDB** | **Neo4j** | **ArangoDB** | **DuckDB+graph** | **Amazon Neptune** |
|---|---|---|---|---|---|
| Architecture | Embedded, serverless | Client-server | Client-server | Embedded | Managed cloud |
| Query language | Cypher | Cypher | AQL | SQL | SPARQL / Gremlin / openCypher |
| Storage model | Columnar | Row-based | Multi-model | Columnar | Row-based |
| Workload focus | Analytics (OLAP) | Transactional (OLTP) | Mixed | Analytics | Transactional |
| Schema | Strongly typed, enforced | Flexible | Flexible | N/A | Flexible |
| Vector search | Yes | Yes (enterprise) | Yes | No native | No |
| Open source | Yes (Apache 2) | Community + Enterprise | Yes (Apache 2) | Yes | No |
| AI/agent use | Primary focus | Secondary | Secondary | No | No |
| Interop | Parquet, Arrow, DuckDB | Limited | Limited | Native | S3 |

---

## Key differentiators

**LadybugDB's strengths:**
- Optimized for object storage and edge-device deployment; runs embedded inside your agent process, eliminating round-trip latency and allowing the graph to travel with the agent — even fitting on a phone.
- Supports both on-disk and in-memory modes; in on-disk mode, all transactions are logged to a WAL with periodic checkpoints, enabling larger-than-memory workloads with transactional guarantees.
- Strong interop with the Python data ecosystem — results can be returned directly as Pandas or Polars DataFrames.

**Where Neo4j wins:** Mature ecosystem, massive community, better OLTP/transactional use cases, more enterprise tooling.

**Where ArangoDB wins:** True multi-model (graph + document + key-value in one), more flexible schema.

**Where Neptune wins:** Fully managed, integrates with the AWS ecosystem  

---

## Bottom line

LadybugDB is essentially **DuckDB for graphs** — embedded, columnar, analytically fast, and Pythonic. It's particularly well-positioned for **AI agent memory** and **graph analytics pipelines** rather than transactional graph applications. Given your Databricks/Arrow/Parquet-heavy work, the interop story is compelling if you ever need graph traversal on top of your Delta Lake data.
