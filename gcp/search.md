## Search 
No Databricks neither BigQuery platform is a search engine in the Elasticsearch sense. 
Both can serve as the **retrieval layer for enterprise search**, though: semantic (vector) search over chunked documents, 
keyword search, and governed access. 
In practice that means RAG or "chat with company knowledge." 
Both platforms build it the same way; only the components differ.

## The common architecture

```
Sources (Confluence, SharePoint, Drive, Jira, PDFs, DB tables, tickets)
   │  ingest + capture ACLs
   ▼
Raw docs in object storage  ──►  Parse / OCR  ──►  Chunk  ──►  Embed
                                                                │
                                         Chunks table (text, metadata, ACL, embedding)
                                                                │
                                                     Vector index + keyword index
                                                                │
User query ──► embed ──► hybrid retrieve (vector + keyword, filtered by user's ACL)
                         ──► rerank ──► (optional) LLM answer with citations
```

The hard parts aren't the vector math. They are:
1. **Permissions:** a user must only retrieve what they're allowed to see.
2. **Freshness:** keeping incremental sync and deletes up to date.
3. **Hybrid relevance:** combining exact terms like part numbers, error codes, and names with semantic matches.
4. **Evaluation:** knowing whether retrieval is actually good.

## Implementation on Databricks

| Step | Component |
|---|---|
| Ingest | Lakeflow Connect (SharePoint, Confluence, Google Drive, Salesforce…), Auto Loader for files into a **UC Volume** |
| Parse | `ai_parse_document()` (PDF, DOCX, images, with OCR and layout), or `unstructured` in a Python job |
| Chunk + metadata | PySpark/SQL into a Delta table: `doc_id, chunk_id, text, title, url, source, updated_at, allowed_groups ARRAY<STRING>` |
| Embed + index | **Mosaic AI Vector Search** with a *Delta Sync index*: point it at the chunks table and an embedding endpoint (e.g. `databricks-gte-large-en`), and it re-embeds changed rows automatically. Enable Change Data Feed on the source table. |
| Query | Vector Search endpoint: `query_type="HYBRID"` (vector + keyword), `filters={"allowed_groups": user_groups}`, plus an optional reranker |
| Answer | Agent Framework / Agent Bricks (Knowledge Assistant), served on Model Serving, with MLflow tracing and evaluation |
| Governance | Unity Catalog lineage from source doc to chunk to index; the index itself is a UC securable |

```python
from databricks.vector_search.client import VectorSearchClient
vsc = VectorSearchClient()
vsc.create_delta_sync_index(
    endpoint_name="search_ep",
    index_name="kb.search.chunks_idx",
    source_table_name="kb.search.chunks",
    primary_key="chunk_id",
    embedding_source_column="text",
    embedding_model_endpoint_name="databricks-gte-large-en",
    pipeline_type="TRIGGERED",          # or CONTINUOUS
)

idx = vsc.get_index("search_ep", "kb.search.chunks_idx")
hits = idx.similarity_search(
    query_text="how do I rotate the charger API key?",
    columns=["chunk_id", "title", "url", "text"],
    filters={"allowed_groups": ["eng-platform", "all-employees"]},
    query_type="HYBRID",
    num_results=10,
)
```

**Strengths:** Delta Sync indexes take care of re-embedding for you, and Spark handles large-scale parsing. The agent and evaluation tooling is built in, and governance runs through Unity Catalog. The serving endpoint gives low query latency.

## Implementation on BigQuery

| Step | Component |
|---|---|
| Ingest | Data Transfer Service or connectors into GCS, then an **Object Table** over the files |
| Parse + chunk | `AI.GENERATE` / Document AI over the Object Table, then `AI.CHUNK_DOCUMENT` (new in Oct 2026) into a chunks table |
| Embed | `AI.GENERATE_EMBEDDING` / `AI.EMBED`, or **autonomous embeddings** on the table so BigQuery maintains the embedding column itself |
| Vector index | `CREATE VECTOR INDEX ... OPTIONS(index_type='TREE_AH')` (ScaNN-based) |
| Keyword index | `CREATE SEARCH INDEX` plus the `SEARCH()` function for full-text/token lookups |
| Query | `VECTOR_SEARCH()` with a pre-filter on ACL columns, then merge with `SEARCH()` results |
| Answer | `AI.GENERATE` in SQL, or Vertex AI / ADK agents that call BigQuery |
| Governance | Row-level access policies on the chunks table, so ACL filtering is enforced by the warehouse instead of being trusted to the app |

```sql
CREATE VECTOR INDEX chunks_vidx ON kb.chunks(embedding)
OPTIONS (index_type = 'TREE_AH', distance_type = 'COSINE');

CREATE SEARCH INDEX chunks_sidx ON kb.chunks(text, title);

-- Semantic leg
WITH q AS (SELECT embedding FROM AI.GENERATE_EMBEDDING(
             MODEL kb.embed_model, (SELECT 'rotate charger API key' AS content)))
SELECT base.chunk_id, base.title, base.url, distance
FROM VECTOR_SEARCH(
  (SELECT * FROM kb.chunks WHERE source IN ('confluence','runbooks')),  -- pre-filter
  'embedding', TABLE q, top_k => 20);

-- Keyword leg
SELECT chunk_id, title, url FROM kb.chunks
WHERE SEARCH(text, 'charger API key rotate');
```

You then merge the two result lists with **Reciprocal Rank Fusion** (in SQL or in the app) and optionally rerank.

**Strengths:** the whole pipeline is SQL with no separate serving infrastructure, and there are native full-text search indexes. Row-level security enforces document ACLs. It scales to billions of chunks. Note that queries run as BigQuery jobs, so latency is typically sub-second to seconds rather than single-digit milliseconds. It's fine for internal search, and you'd put a cache in front for high QPS.

**Google's off-the-shelf option:** if you want enterprise search as a *product* (connectors, ACL sync, ranking, UI) rather than something you build, Google offers Vertex AI Search / Gemini Enterprise, which can use BigQuery as one of its data sources. Databricks doesn't sell that kind of packaged search UI. Agent Bricks Knowledge Assistant is the closest thing.

## Head-to-head

| | Databricks | BigQuery |
|---|---|---|
| Vector store | Separate managed Vector Search endpoint synced from Delta | In-warehouse vector index on the table |
| Hybrid search | Built into the query API | Two indexes (`VECTOR_SEARCH` + `SEARCH`), fused yourself |
| Auto re-embedding | Delta Sync index | Autonomous embeddings |
| ACL enforcement | Metadata filters at query time (app passes the user's groups) | Row-level security in the warehouse, or filters |
| Latency | Low (online serving) | Higher (query jobs) |
| Best fit | ML/agent-heavy teams, multi-cloud, Spark-scale parsing | GCP-native, SQL-first teams, very large corpora |

## Using both together

This is common in enterprises that run both platforms:
- **Databricks parses and enriches; BigQuery serves analytics on search usage.** Heavy Spark parsing and chunking produce Delta/Iceberg tables. BigQuery reads them through BigLake/Iceberg, or through the SAP BDC/Delta Sharing federation that was added this year, and joins search logs with business data.
- **Single source of chunks in Iceberg on GCS.** Both engines read the same table. You'd index in one engine and do analytics in the other, rather than paying to embed twice.
- **Search logs drive feedback loops.** Click and dwell logs land in BigQuery or Delta and feed relevance evaluation and fine-tuning of the reranker.

## Practical advice

- **Capture ACLs at ingest time** and store them on every chunk. Retrofitting permissions later is the most common enterprise-search failure.
- **Always do hybrid search.** Pure vector search misses exact identifiers like `ERR_4012`, a VIN, or a ticket number.
- **Chunk by structure** (headings, sections) and keep the title and breadcrumb in each chunk. That matters more than which embedding model you choose.
- **Handle deletes.** When a source doc is removed or its permissions change, the chunk must disappear from the index. Delta Sync handles this automatically if you delete from the source table. On BigQuery, deletes in the table propagate to the index.
- **Build an evaluation set** of real queries with known good documents, and track recall@k and MRR before tuning anything.

