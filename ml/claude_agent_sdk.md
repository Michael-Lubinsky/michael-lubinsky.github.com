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

If you tell me what you're actually trying to build (e.g., a RAG pipeline, a multi-step data pipeline, a supervisor/worker setup), I can sketch how you'd structure it in the Agent SDK's idioms instead of LCEL's.
