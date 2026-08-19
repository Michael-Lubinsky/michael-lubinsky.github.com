## Claude Agent SDK 
 

1. **Overview** — <https://docs.claude.com/en/agent-sdk/overview> — explains the mental model (agent loop vs. chain-building) and when to use the Agent SDK vs. the plain Client SDK vs. Claude Code CLI vs. Managed Agents.
2. **Quickstart** — <https://docs.claude.com/en/agent-sdk/quickstart> — walks you through building a bug-finding/fixing agent in ~10 minutes, in either language.
3. **Language reference** :
   - Python: <https://docs.claude.com/en/agent-sdk/python>
   - TypeScript: <https://docs.claude.com/en/agent-sdk/typescript>
4. **Example agents repo** — https://github.com/anthropics/claude-agent-sdk-demos — real working agents (email assistant, research agent, etc.) worth reading end-to-end once the basics click.
5. **Docs index** — https://code.claude.com/docs/llms.txt — a flat list of every doc page, useful for finding the pages on hooks, subagents, MCP, permissions, and sessions once you know roughly what you're looking for.

 

- The package was renamed from **Claude Code SDK** to **Claude Agent SDK**; if you find older blog posts or Stack Overflow answers, treat identifiers and import paths as potentially stale and cross-check against the docs above.
- Python: `pip install claude-agent-sdk` (needs 3.10+). TypeScript: `npm install @anthropic-ai/claude-agent-sdk`.
- Given you work in PySpark/Databricks day-to-day, the Python SDK reference is probably your natural entry point.
- The core primitive is `query()` — an async generator that streams messages while Claude autonomously drives tool calls. Once that clicks, the rest (hooks, subagents, MCP servers, permission modes) are additive concepts layered on top.

One caution on third-party guides: search results are currently full of blog content dated into mid/late 2026 describing rapid, ongoing changes (a June 2026 credit-metering change, a separate "Managed Agents" API, etc.). Some of these third-party summaries may be unreliable or promotional — I'd treat the official docs as ground truth and use blog posts only for supplementary walkthroughs.

## There is  LangChain Expression Language (LCEL) . What is equivalent fot it in Claude Agentic SDK?


Short answer: there isn't one. The Claude Agent SDK doesn't have an LCEL-style declarative pipe/composition DSL, and that's a deliberate design difference, not a missing feature.

**Why the comparison doesn't map cleanly**

LCEL exists to let you *declaratively compose* discrete steps — retriever → prompt template → model → output parser — using the `|` operator, producing a `Runnable` graph you can invoke, stream, or batch. It's fundamentally a chain-of-transforms abstraction.

The Claude Agent SDK is built around a different model entirely: an **agent loop**, not a chain. Its entry point is `query()`, which you call with a prompt and options, and it autonomously handles the tool-call → tool-execute → next-decision loop internally rather than you wiring discrete steps together:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Find and fix the bug in auth.py",
    options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
):
    print(message)
```

Whereas in a LangChain/LCEL world you'd typically hand-compose that same "look something up, format it, call the model, parse it" pipeline as a chain, the Agent SDK's philosophy is: give Claude the tools and let the model drive the sequencing itself, using built-in tools, hooks, subagents, and MCP servers as the composition primitives instead of a pipe operator over Runnables.

**Closest analogues to LCEL's pieces, if you want a mapping:**

| LCEL concept | Agent SDK equivalent |
|---|---|
| `Runnable` / `\|` chaining | No direct equivalent — no declarative graph builder |
| Tool step in a chain | `allowed_tools`, custom `tool()` definitions, MCP servers |
| Sequential multi-agent chains | Subagents (delegation pattern) |
| Callbacks/observability hooks | Lifecycle `hooks` |
| Retriever step | You'd wire this yourself via a custom MCP tool or pre-fetch and pass into the prompt |

If you actually want declarative graph-style orchestration on top of Claude (branching, cycles, explicit state), that's closer to what **LangGraph** (LangChain's graph framework) is for — you can point LangGraph at Claude via `langchain-anthropic` and get LCEL/graph-style composition while still using Claude as the model. The Agent SDK itself is intentionally more like "Claude Code as a library" than a chain-building framework.

Both frameworks solve agent-building, but they sit at different layers — one is an opinionated agent harness, the other is a low-level orchestration runtime. That distinction drives most of the decision.

## Choose the Claude Agent SDK when...

- **You're Claude-centric and want to ship fast.** It's the same tool-use loop, permission system, and context management that powers Claude Code, exposed as a library — you call `query()`, hand it tools, and Claude drives the sequencing itself rather than you wiring a graph. The Claude Agent SDK is the Claude Code engine packaged as a library: an opinionated, batteries-included harness where Anthropic owns the agent loop and you steer it.
- **Your task is closer to "one capable worker" than a business process.** LangGraph wins when your system is closer to a durable business process with agentic components than to a single powerful worker.
- **You want hierarchical delegation without building it yourself.** The June 2026 update makes the SDK the simplest way to build agents that spawn other agents — a planning agent that delegates to research, writing, and review subagents, with each subagent just another Agent object used as a tool.
- **MCP integration and native tool use matter.** The Claude Agent SDK offers hierarchical subagents that spawn on-the-fly for complex sub-tasks, native computer use and vision, and native MCP protocol support built from the ground up.
- **Simplicity beats maximum control.** Claude Agent SDK is simpler (roughly 50 lines vs. 400 for a comparable agent) but less flexible.

## Choose LangGraph when...

- **You need explicit, durable state and human-in-the-loop control.** LangGraph is a low-level orchestration runtime where you own the loop, the state schema, and every edge in the graph — and it works with any model provider. Use it when your workflow has multiple steps with conditional branching, requires persistent state across a long-running process, needs human-in-the-loop checkpoints, or involves a supervisor coordinating specialized subagents.
- **You need model flexibility.** LangGraph works with any LLM provider — you can use Claude for reasoning, another model for classification, another for coding, another for multimodal work, routing between them within a single workflow.
- **Behavior must be deterministic, not "probably."** If a rule needs to be enforced exactly — e.g. "always escalate on a critical finding" — rather than left to the model's judgment, that favors LangGraph's explicit graph control over the SDK's model-driven sequencing.
- **You're not locked into Anthropic.** LangGraph, CrewAI, AG2, and similar frameworks cover the spectrum from minimal model-driven agents to complex stateful orchestration, backed by open-source ecosystems rather than a single model vendor.

## The common pattern: use both, at different layers

Several sources converge on the same hybrid architecture rather than treating this as either/or:

The standard architecture uses LangGraph to define the graph structure — nodes, edges, state schema, checkpointing — while Claude is called via the Anthropic SDK or langchain-anthropic inside specific nodes where LLM reasoning is required. Many high-performing teams in 2026 use LangGraph as the top-level state orchestrator for business logic and human approval gates, while embedding Claude Agent SDK subagents inside individual graph nodes for specialized reasoning tasks.

## Practical shortcut

If you're committed to Claude: Claude Agent SDK first, and reach for LangGraph only if you need its multi-agent depth. If you're model-agnostic and want the strongest multi-agent orchestration: LangGraph.

**A caveat on this whole space:** it's moving fast and full of SEO-driven comparison posts with specific numbers (star counts, token-cost figures, "50 lines vs 400") that I can't independently verify and that may be stale or promotional by the time you read them. For your actual decision — especially anything involving billing/credits, since Anthropic changed SDK metering mid-2026 — I'd verify current terms directly against docs.claude.com rather than trusting third-party blog figures.

Given what you build day to day (Databricks pipelines, PySpark, data infra), if this were, say, a Claude-driven data-pipeline agent that needs to call your existing tools and doesn't require multi-vendor model routing or heavy human-approval checkpoints, the Agent SDK alone is probably the simpler starting point — you can always front it with LangGraph later if the orchestration needs grow.

## A gentic pipeline for analytics:
human asks question :  create bar chart  with number of transaction and total amount grouped by month and by product  for last 3  months.  
Agent should be able to connect to database,  find right database tables with relevant data based on columns names description, compose the SQL and create dashboard using some dashboard tool like Tableau or Looker.


Good news: this maps naturally onto the Agent SDK's tool-use loop, and there are now first-party MCP servers for exactly the pieces you'd otherwise have to build (schema discovery, Tableau, Looker). Here's a concrete design.

## High-level architecture

```
User question
     │
     ▼
┌─────────────────────────────────────────────┐
│  Orchestrator agent (Claude Agent SDK)       │
│  query() + system prompt + tool routing      │
└─────────────────────────────────────────────┘
     │           │              │             │
     ▼           ▼              ▼             ▼
 Schema/      SQL exec      Chart/dash     Validation
 catalog      (read-only)   creation       & guardrail
 lookup       tool          tool (MCP)     tools
```

Rather than one giant prompt, structure it as a **pipeline of specialized steps**, each with a narrow tool surface — this is the difference between an agent that occasionally hallucinates a table name and one that's reliable in production.

## Step 1 — Schema/table discovery (semantic grounding)

The hardest part of "find the right tables based on column descriptions" is that an LLM can't reliably search unindexed metadata by vibes. Two solid approaches, and you can combine them:

**A. Metadata-as-a-tool (works well with your Unity Catalog stack)**
Expose a tool like `search_catalog(query: str) -> list[TableCandidate]` backed by:
- Unity Catalog's `information_schema` (table/column comments, tags)
- A vector index over table + column descriptions (embed `catalog.schema.table.column: description` rows once, query at runtime) — this scales far better than dumping your whole schema into the prompt once you have hundreds of tables.

**B. MCP-native database tools**
There are now MCP servers purpose-built for this (e.g. Google's "MCP Toolbox for Databases," used by the Looker MCP integration) that expose schema introspection as first-class tools rather than you writing a custom one. Looker's MCP Toolbox for Databases uses the open MCP standard to connect AI agents, IDEs, and applications directly to enterprise databases. Databricks has an equivalent Unity Catalog MCP server exposing catalog/schema/table search as tools — worth checking Databricks' docs directly since this is evolving fast.

Give the agent a tool contract like:

```python
@tool
def search_tables(keywords: list[str]) -> list[dict]:
    """Returns candidate tables with column names, types, and descriptions
    matching the keywords, ranked by relevance."""
```

The agent calls this with terms extracted from the question ("transaction", "amount", "product", "date/month") before ever writing SQL.

## Step 2 — SQL composition with guardrails

Once candidate tables are identified, have the agent draft SQL — but constrain it hard:

- **Read-only DB role.** The SQL execution tool should connect via a credential that can only `SELECT`. Never let the agent's DB connection have write/DDL permission — that's non-negotiable for a natural-language-driven pipeline.
- **Dry-run/EXPLAIN first.** Run `EXPLAIN` (or a Databricks equivalent) before actual execution, and cap resulting row counts and query cost — protects you from a runaway aggregation on a huge fact table.
- **Schema-verified generation.** Feed the agent only the *actual* discovered columns from step 1 back into its SQL-writing tool call — not columns it remembers/hallucinates. This is why discovery and SQL generation should be separate tool calls, not one blended step.

Example shape for your specific question:

```sql
SELECT
  date_trunc('month', t.transaction_date) AS month,
  p.product_name,
  COUNT(*) AS transaction_count,
  SUM(t.amount) AS total_amount
FROM catalog.sales.transactions t
JOIN catalog.sales.products p ON t.product_id = p.product_id
WHERE t.transaction_date >= add_months(current_date(), -3)
GROUP BY 1, 2
ORDER BY 1, 2
```

The agent should self-verify: check column existence against the discovered schema, check the WHERE clause matches "last 3 months" semantics you actually want (rolling 90 days vs. last 3 calendar months — worth disambiguating with the user or defaulting explicitly and stating the default in the response).

## Step 3 — Chart/dashboard creation

This is where you pick your BI tool's MCP server:

- **Tableau**: Tableau ships an official MCP server ("Tableau's official MCP Server. Helping agents see and understand data"), with documented Claude client integration. It runs locally via `npx @tableau/mcp-server`, config'd with your server URL, site name, and a Personal Access Token.
- **Looker**: Looker has a built-in, Google-managed MCP server that lets AI agents like Claude securely connect to a Looker instance and interact with business data and LookML models, removing the need to deploy your own middleware. Note it's in preview for Looker (Google Cloud core) and Looker (original) instances, with customer-hosted/on-prem instances not currently supported.

Given your existing SQL result, the agent's job here is: call the BI tool's "create workbook/dashboard from data" tool (or push a query definition it understands, e.g. LookML explore or a Tableau extract), then request a bar chart with month on the x-axis, grouped/colored by product, dual-axis or two chart panels for count vs. total amount (mixing very different scales in one bar chart is usually a mistake worth catching before Claude blindly complies).

If you don't want a live BI tool round-trip for every ad hoc question, a lighter alternative: have the agent render the chart itself as an artifact (e.g., using the Visualizer/chart module here, or a Python/Plotly script in your own pipeline) and only push to Tableau/Looker when the user says "save this as a dashboard." That two-tier design (fast inline chart, optional promote-to-BI-tool) avoids cluttering your Tableau site with one-off exploratory charts.

## Step 4 — Orchestration in the Agent SDK

Concretely, in Python:

```python
options = ClaudeAgentOptions(
    system_prompt=(
        "You are a data analytics agent. Always discover schema via "
        "search_tables before writing SQL. Always run SQL through "
        "execute_readonly_sql — never assume results. Confirm ambiguous "
        "date ranges with the user before running expensive queries."
    ),
    mcp_servers={
        "warehouse": {"command": "...", "args": [...]},   # your Unity Catalog / DB MCP
        "tableau": {"command": "npx", "args": ["-y", "@tableau/mcp-server@latest"],
                    "env": {"SERVER": "...", "SITE_NAME": "...", "PAT_NAME": "...", "PAT_VALUE": "..."}},
    },
    allowed_tools=["search_tables", "execute_readonly_sql", "tableau_create_view"],
    permission_mode="acceptEdits",  # or a custom permission callback for the SQL execution step
)

async for message in query(prompt=user_question, options=options):
    ...
```

Use **hooks** to log every generated SQL statement and every BI-tool write before execution — you want an audit trail for "what query did the agent actually run against production" independent of what it narrates back to the user.

## Reliability considerations specific to this use case

- **Ambiguity resolution**: "last 3 months" and "grouped by month and by product" is fairly well-specified, but real users will send vaguer asks. Have the agent state its interpretation (date range, aggregation grain) in its response rather than silently picking one — cheap insurance against wrong-answer-with-high-confidence.
- **Column-name ambiguity across tables**: if you have multiple `amount` columns (gross vs. net, pre/post refund), schema descriptions need to disambiguate this at the metadata level, not leave it to the LLM to guess — this is really a data governance investment more than an agent-engineering one.
- **Cost control**: cap query timeout and row scan limits at the DB role/session level, not just via prompt instruction — prompts are not a security boundary.
- **Testing**: build a small eval set of paraphrased versions of your target questions ("bar chart of monthly txn counts by product, past quarter" etc.) and check both SQL correctness and chart output — this is the kind of thing worth versioning like code, since a system-prompt tweak can silently break table selection.

Given your Databricks/Unity Catalog background, the schema-discovery layer is probably the piece worth building most carefully first — get `search_tables` solid and grounded in real UC comments/tags before worrying about the Tableau/Looker output layer, since a wrong table choice is a much worse failure mode than a slightly ugly chart.




### LangGraph

Same pipeline, but LangGraph forces you to make the state machine explicit instead of letting Claude's tool loop drive the sequencing implicitly. That's the main tradeoff, and for something like this — regulated data access, SQL execution, dashboard writes — the explicit-state version is often actually the better production shape, since you get deterministic gates you can't guarantee purely from a system prompt.

## Why this task fits LangGraph well

Your pipeline has exactly the shape LangGraph is designed for: distinct stages (discover → generate → validate → execute → visualize) where you want **conditional branching** (bad SQL → retry generation), **a human-in-the-loop checkpoint** before hitting production data or writing a dashboard, and **persistent state** across the whole flow instead of relying on the model to "remember" what it found in step 1 by the time it gets to step 4.

## State schema

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class AnalyticsState(TypedDict):
    question: str
    candidate_tables: list[dict]        # from schema search
    sql: str
    sql_validated: bool
    validation_errors: list[str]
    query_result: dict                   # rows/columns from execution
    chart_spec: dict
    dashboard_url: str | None
    needs_human_approval: bool
    retry_count: int
```

## Nodes

Each stage from the Agent SDK version becomes an explicit node function:

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-5")

def discover_schema(state: AnalyticsState) -> dict:
    # Calls your Unity Catalog / vector-index search tool
    keywords = extract_keywords(state["question"])  # or an LLM call
    candidates = search_tables_tool.invoke({"keywords": keywords})
    return {"candidate_tables": candidates}

def generate_sql(state: AnalyticsState) -> dict:
    prompt = build_sql_prompt(state["question"], state["candidate_tables"])
    response = llm.invoke(prompt)
    return {"sql": extract_sql(response), "retry_count": state.get("retry_count", 0)}

def validate_sql(state: AnalyticsState) -> dict:
    # EXPLAIN against the warehouse, check columns exist, check row-scan cost
    errors = run_explain_and_checks(state["sql"], state["candidate_tables"])
    return {"sql_validated": len(errors) == 0, "validation_errors": errors}

def execute_sql(state: AnalyticsState) -> dict:
    result = readonly_db_tool.invoke({"sql": state["sql"]})
    return {"query_result": result}

def build_chart_spec(state: AnalyticsState) -> dict:
    spec = derive_bar_chart_spec(state["query_result"])  # month x product, count + amount
    return {"chart_spec": spec}

def publish_dashboard(state: AnalyticsState) -> dict:
    url = tableau_mcp_tool.invoke({"chart_spec": state["chart_spec"]})
    return {"dashboard_url": url}
```

## Conditional edges — the part that's clunkier in the Agent SDK

This is the actual value-add over the SDK approach: explicit routing logic instead of hoping the model retries correctly.

```python
def route_after_validation(state: AnalyticsState) -> Literal["execute_sql", "generate_sql", "human_review"]:
    if state["sql_validated"]:
        return "execute_sql"
    if state["retry_count"] >= 2:
        return "human_review"   # stop looping, escalate
    return "generate_sql"       # retry with error feedback

def route_after_discovery(state: AnalyticsState) -> Literal["generate_sql", "human_review"]:
    if not state["candidate_tables"]:
        return "human_review"   # no matching tables — don't guess
    return "generate_sql"
```

## Human-in-the-loop before execution/publish

This is the strongest argument for LangGraph on this exact use case — you can insert a **hard interrupt** before SQL runs against production or before a dashboard gets written, without relying on the model choosing to ask:

```python
graph = StateGraph(AnalyticsState)
graph.add_node("discover_schema", discover_schema)
graph.add_node("generate_sql", generate_sql)
graph.add_node("validate_sql", validate_sql)
graph.add_node("execute_sql", execute_sql)
graph.add_node("build_chart_spec", build_chart_spec)
graph.add_node("publish_dashboard", publish_dashboard)
graph.add_node("human_review", human_review_node)

graph.add_edge(START, "discover_schema")
graph.add_conditional_edges("discover_schema", route_after_discovery)
graph.add_edge("generate_sql", "validate_sql")
graph.add_conditional_edges("validate_sql", route_after_validation)
graph.add_edge("execute_sql", "build_chart_spec")
graph.add_edge("build_chart_spec", "publish_dashboard")
graph.add_edge("publish_dashboard", END)

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer, interrupt_before=["execute_sql", "publish_dashboard"])
```

`interrupt_before` pauses the graph and persists state via the checkpointer — a human (or an approval service) reviews the generated SQL or the chart spec, then resumes with `app.invoke(None, config)`. This is genuinely harder to get right with the Agent SDK's model-driven loop, where "ask before running" is a prompt instruction rather than a structural guarantee.

## Wiring in your tools (MCP + Databricks)

LangGraph doesn't care where tools come from — you can bind the same Tableau/Looker MCP servers via `langchain-mcp-adapters`, or wrap Databricks SQL execution as a plain LangChain `Tool`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "tableau": {"command": "npx", "args": ["-y", "@tableau/mcp-server@latest"],
                "env": {"SERVER": "...", "SITE_NAME": "...", "PAT_NAME": "...", "PAT_VALUE": "..."}}
})
tableau_tools = await mcp_client.get_tools()
```

Then bind whichever tools a given node needs — schema search only in `discover_schema`, SQL execution only in `execute_sql` — rather than exposing the full toolset to the model at every step, which is itself a security/reliability win over a single flat tool list.

## Net comparison for this specific pipeline

| Concern | Agent SDK | LangGraph |
|---|---|---|
| Speed to first working version | Faster — model drives sequencing | More upfront graph/state design |
| Guaranteed "ask before execute" | Relies on prompt discipline | Structural (`interrupt_before`) |
| Retry-with-feedback on bad SQL | You'd hand-roll a loop check | Native conditional edge |
| Multi-model routing (e.g. cheap model for keyword extraction, Claude for SQL) | Not really the model | Native |
| Audit trail of state at each stage | Via hooks | Native (checkpointed state) |

Given this pipeline touches production data and writes to a shared BI tool, the human-in-the-loop gate before `execute_sql` and `publish_dashboard` is worth the extra setup cost — that's the one piece I'd weight most heavily toward LangGraph here, more than the multi-model flexibility, since you're Claude-committed anyway.


Good questions — let's demystify MCP's actual runtime shape, since "server" here is a bit of a misnomer that trips people up.

## What MCP actually is

MCP (Model Context Protocol) is a **client-server protocol over JSON-RPC**, not a specific piece of infrastructure. An "MCP server" is just a process that speaks this protocol and exposes tools/resources; an "MCP client" (your Claude Agent SDK app, Claude Desktop, Claude Code) speaks to it and calls those tools on the model's behalf. Nothing about the protocol dictates where that process runs — that's an implementation choice per server.

## Where does it "live"? Two transport modes

**1. Local/stdio (most common for dev tools and DB access)**

The MCP server is just a subprocess launched by your agent's host process, communicating over stdin/stdout. This is what you saw in the Tableau example:

```json
{
  "mcpServers": {
    "tableau": {
      "command": "npx",
      "args": ["-y", "@tableau/mcp-server@latest"],
      "env": { "SERVER": "...", "PAT_VALUE": "..." }
    }
  }
}
```

When your agent starts, it literally spawns `npx @tableau/mcp-server` as a child process on the **same machine** running your agent code. No network hop, no separate deployment — it lives and dies with your agent process. This is the default for database-connector-style MCP servers (Unity Catalog, Postgres, etc.) because it's simplest to run wherever your app already has network access to the DB.

**2. Remote/HTTP+SSE (for hosted, multi-tenant services)**

The MCP server runs as its own standalone service — a real deployment, with a URL your agent connects to over HTTPS. This is what Looker's managed MCP server and Google's "MCP Toolbox for Databases" are: Google hosts and operates the server, and your agent just points at an endpoint with OAuth. You don't run this yourself; the Looker-managed MCP server is a built-in integration that Google hosts, removing the need for you to deploy and maintain your own middleware infrastructure.

So the answer to "where does it live" is genuinely **it depends on the server**: a DB-connector MCP server you'll almost always self-host (stdio, local process, or a small container in your own VPC next to the warehouse); a vendor's managed BI server (Looker's) lives on their infrastructure.

## What language is it implemented in?

The protocol is language-agnostic — the SDKs exist in Python, TypeScript, and others, and a server can be written in whatever's convenient since it just needs to implement JSON-RPC over the chosen transport. In practice:

- **Tableau's official MCP server** ships as an npm package (`@tableau/mcp-server`) — TypeScript/Node.
- Most community/reference MCP servers (Postgres, filesystem, GitHub) are also TypeScript, since Anthropic's reference SDK and most early tooling shipped Node-first — the Tableau-MCP example server referenced earlier is Python-based instead, built on the Python `mcp` SDK, so both ecosystems are common.
- Anthropic publishes official MCP SDKs for **Python, TypeScript, Java, Kotlin, and C#** — so a server can genuinely be written in any of those with roughly equal support.

For your own DB-connector server, language choice is really just "whatever your team is comfortable maintaining" — Python is the natural pick given your PySpark/Databricks stack, and there's no protocol penalty for that.

## Where do DB credentials and schema info live?

This is the part worth being deliberate about, because it's the actual security boundary of the whole pipeline.

**Credentials**: They live with the **MCP server process**, never with the LLM or the agent's prompt context. Concretely:

- **Local/stdio servers**: credentials are passed as environment variables or config at server-launch time (as in the Tableau JSON above — `PAT_VALUE` in `env`). The server process holds the live DB connection; the LLM only ever sees tool inputs/outputs, never the credential itself.
- **Remote/managed servers**: credentials are configured server-side (e.g., a Looker service account registered with Google's managed server) or negotiated per-user via OAuth at connection time — again, the model never touches them directly.
- **Best practice for your case**: use a **read-only service account/role** scoped narrowly (SELECT only, ideally scoped to the specific catalogs/schemas the agent needs), stored in a secrets manager (Databricks secret scopes, AWS Secrets Manager, Azure Key Vault) and injected into the MCP server's environment at deploy time — not hardcoded, not in the agent's system prompt, not in your repo.

**Schema/metadata for table discovery**: This lives wherever you choose to index it — it's not part of the MCP protocol itself, it's just data your `search_tables` tool queries:

- Simplest: query Unity Catalog's `information_schema` live, on each discovery call.
- Better at scale: pre-build a small vector index (table/column names + descriptions/comments/tags) refreshed periodically, so discovery is a fast embedding search rather than hitting `information_schema` fresh each time. This index can live in whatever you already use for vector search (Databricks Vector Search, pgvector, etc.) — again, entirely separate from where MCP "lives."

## Practical shape for your pipeline

```
Your VPC/network
┌──────────────────────────────────────────────┐
│  Agent host (your app, running Agent SDK)     │
│    │ spawns (stdio) or calls (HTTP)            │
│    ▼                                          │
│  DB MCP server (Python, local process)        │
│    - holds read-only Databricks/UC credential │
│      pulled from secret scope at startup      │
│    - queries information_schema / vector index│
│    - executes SELECT-only SQL                 │
└──────────────────────────────────────────────┘
         │ (separate, outbound HTTPS)
         ▼
Tableau MCP server (Node, local or containerized)
  - holds Tableau PAT from secrets manager
  - calls Tableau REST API
```

The key architectural point: **credentials never pass through the LLM's context window.** The model only ever sees tool *names*, *schemas*, and *results* — the actual secret material stays inside the MCP server process boundary, which you control and can audit independently of what the model says or does.
