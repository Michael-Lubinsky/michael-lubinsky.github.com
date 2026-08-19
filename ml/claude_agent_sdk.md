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
