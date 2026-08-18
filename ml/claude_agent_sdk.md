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
