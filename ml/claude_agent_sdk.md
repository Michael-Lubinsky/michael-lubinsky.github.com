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
