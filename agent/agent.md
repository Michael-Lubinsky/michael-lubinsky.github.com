What's in here

shared/ — identical arXiv API client + JSON dedup store, used by every Python implementation, so the differences you see are pure orchestration, not incidental code differences.

langgraph/digest_graph.py — explicit StateGraph with real parallel fan-out, a conditional edge for the widen-retry, a MemorySaver checkpointer, and interrupt()/Command(resume=...) for approval. Verified: compiles and I printed its Mermaid graph to confirm the topology is right.

crewai/digest_crew.py — role-based Physics/Math/Editor agents, context=[...] task wiring, Task(human_input=True). Verified: constructs cleanly.

openai_agents_sdk/digest_agents.py — Triage agent with typed handoffs to two specialists, an output_guardrail enforcing the min-hits rule. Verified: constructs cleanly.

claude_agent_sdk/digest_agent.py — one orchestrator agent, Task-tool subagents, custom MCP tools, and a PreToolUse hook that actually denies the publish tool call until approved. Verified: constructs cleanly.

pi_dev/ — AGENTS.md (orchestration as plain instructions) + a TypeScript arxiv_search tool. Verified: type-checks and its filtering logic matched Python's output against a mocked feed.

omp_sh/ — TOML config declaring native parallel subagents plus a SYSTEM.md leaning on omp's persistent Python kernel. Verified: TOML is well-formed.
