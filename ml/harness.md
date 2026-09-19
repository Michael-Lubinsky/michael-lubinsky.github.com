

## Vendor-agnostic orchestration frameworks

<https://www.kdnuggets.com/10-agentic-ai-frameworks-you-should-know-in-2026>

**LangGraph** — Models agents as nodes in an explicit state graph with shared state, checkpointing, and human-in-the-loop primitives. It reached 1.0 GA on October 22, 2025, with a no-breaking-changes commitment until 2.0, and documented production users include Klarna, Replit, Uber, LinkedIn, and Elastic. It's model-agnostic via LangChain's integration layer. Steepest learning curve of the group, but it's the strongest production story: durable execution means agents survive server restarts, and LangSmith gives full tracing/observability. Best when you need explicit control over execution paths, retries, and branching logic.

**CrewAI** — Role-based: Agents (with roles), Tasks, and Crews that orchestrate them — the mental model is a team of specialists working together, not a flowchart. It's the fastest path to a working multi-agent prototype — you can have something running before lunch — and by March 2026 it had native MCP and A2A (agent-to-agent) protocol support. Weaker on fine-grained control: if you need to specify exactly which node executes after which condition, CrewAI's higher-level abstractions can feel limiting. Best for role-mapped pipelines (researcher → writer → reviewer, support triage).

## Vendor harness SDKs

**Claude Agent SDK** (what Claude Code itself runs on) — Anthropic extracted the agent harness that powers Claude Code and shipped it as a general-purpose SDK, renamed from the Claude Code SDK along the way. The design philosophy is "give one capable agent a computer" — a single autonomous agent with deep OS/filesystem access, controlled by what it's allowed to do. It treats MCP as native plumbing, unsurprising since Anthropic created the protocol — this is the natural fit if you want your agent reading/writing files, running shell commands, or orchestrating pipelines directly. It centers on hooks and subagents — intercepting and controlling behavior at lifecycle points, with task delegation through child agents — giving precise control over what an agent can and cannot do. Both Python and TypeScript are first-class.

**OpenAI Agents SDK** — Opposite philosophy: many lightweight agents wired together, controlling how work flows between them via explicit typed handoffs, guardrails, and tools. Originally the more minimal/orchestration-only of the two, but it closed the capability gap fast: an April 15, 2026 overhaul added native sandbox execution (Modal, Daytona, Docker, E2B), a model-native harness, durable state via externalized snapshotting/rehydration, and subagents — the features that used to be Claude/LangGraph's exclusive edge. It's genuinely provider-agnostic now, working with 100+ non-OpenAI models, not locked to OpenAI as older comparisons claim. Best if you want lightweight orchestration, voice (still OpenAI's clear strength), or model flexibility.

## The oddball: pi.dev

Different category entirely — a minimal, open-source terminal coding agent harness built around one thesis: an agent needs exactly four tools (read, write, edit, bash) and a system prompt under 1,000 tokens, with everything else opt-in via a typed TypeScript extension system. It's MIT-licensed, from the earendil-works monorepo, created by Mario Zechner (libGDX's author). Not an orchestration framework like LangGraph/CrewAI — closer to a bring-your-own-everything coding-agent shell, positioned against commercial tools like Claude Code by staying deliberately unopinionated and hackable.

## Quick take for your stack

| | Model lock-in | Mental model | Sweet spot |
|---|---|---|---|
| LangGraph | None | State graph | Complex, stateful, production pipelines needing checkpointing/HITL |
| CrewAI | None | Team of roles | Fast prototyping, role-shaped workflows |
| Claude Agent SDK | Anthropic | One agent + a computer | File/code/OS-heavy agents, MCP-first stacks |
| OpenAI Agents SDK | Loosening | Handoffs between agents | Lightweight orchestration, voice, multi-model flexibility |
| pi.dev | None (any model) | Minimal 4-tool loop | Building your own coding-agent harness from scratch |

Worth noting the honest caveat several of these comparisons make: if your agent just calls two or three tools in a linear flow, a framework adds friction rather than value — a plain SDK loop with a max_steps cap does the job. Frameworks earn their keep once human-in-the-loop, multi-agent coordination, or durable execution enter the picture.

## OMP / Oh My Pi (omp.sh)

Built on top of pi.dev but goes considerably further — a Rust-core coding agent harness (~55k lines) rather than pi's minimal 4-tool core. Its architectural bets:

- **In-process tooling, not fork-exec.** ripgrep, glob, find, and a `brush` bash implementation with 58 ported CLI utilities (ls, sed, sort, jq, etc.) run inside the same process instead of shelling out — meant to cut latency and avoid missing binaries.
- **Hash-anchored edits ("Hashline Edits").** The model points at stable anchors instead of retyping lines, which avoids the classic whitespace/string-not-found failure mode of diff-based edits — reported to cut output tokens meaningfully (one claim: 61% fewer output tokens on Grok 4 Fast for the same work) and reject patches cleanly when a file has drifted.
- **Real IDE integration.** Native LSP (14 ops) for workspace-aware refactors (renames update barrel files and aliased imports correctly) and DAP (28 ops) for actually attaching a debugger — lldb for a segfaulting C binary, dlv for a hung Go service — rather than just reading logs.
- **Persistent runtime kernels.** Runs persistent Python and a Bun/JS worker that can call back into the agent's own tools over a loopback bridge, so a Python cell can load a CSV via the agent's read tool and hand off to JS to chart it without leaving the session.
- **Subagent review flow.** A `/review` command spawns dedicated reviewer subagents that sweep branches or uncommitted work in parallel and rank issues P0–P3 with confidence scores.
- Cross-platform single binary (macOS/Linux/Windows, no WSL), 40+ model providers, 32 built-in tools.

Positioning-wise: pi.dev's whole pitch is "four tools, get out of the way, extend via TypeScript." OMP takes the opposite bet — "most harnesses give the agent a sandbox and call it done; we wire in everything your IDE knows" — trading pi's minimalism for a much deeper, batteries-included environment while keeping pi's model-agnostic, terminal-first spirit. It sits closest to Claude Agent SDK's "give the agent a computer" philosophy, but as an independent, provider-agnostic open-source project rather than a vendor SDK.

Where it'd fit against the others: if you're choosing between LangGraph/CrewAI (orchestration frameworks) vs. Claude Agent SDK/OpenAI Agents SDK (vendor harnesses) vs. pi/OMP (open-source terminal coding-agent harnesses) — pi and OMP are really answering a different question than LangGraph/CrewAI. They're not for building multi-agent business workflows; they're alternative engines for a single deeply-capable coding agent, competing more directly with Claude Code itself than with graph orchestrators.

Sources:
- [GitHub - can1357/oh-my-pi](https://github.com/can1357/oh-my-pi)
- [GitHub - Raudbjorn/omp](https://github.com/Raudbjorn/omp)
- [OMP (Oh My Pi): AI Coding Agent with LSP, DAP Debugger, and Hashline Edits](https://betterstack.com/community/guides/ai/oh-my-pi-ai-coding-agent/)



Sources:
- [Pi (pi.dev) - Agentic AI Knowledge Base](https://agentic-ai.readthedocs.io/en/latest/AgentHarness/pi-dev/)
- [Pi Coding Agent](https://pi.dev/)
- [ohm.sh](https://ohm.sh)
- [AI Agent Frameworks 2026: LangGraph vs CrewAI & More](https://letsdatascience.com/blog/ai-agent-frameworks-compared)
- [LangGraph vs CrewAI vs OpenAI Agents SDK: Picking Your Agent Framework in 2026](https://dev.to/jamilxt/langgraph-vs-crewai-vs-openai-agents-sdk-picking-your-agent-framework-in-2026-2heo)
- [CrewAI vs LangChain 2026 - NxCode](https://www.nxcode.io/resources/news/crewai-vs-langchain-ai-agent-framework-comparison-2026)
- [LangGraph vs CrewAI vs AutoGen vs Swarms Comparison 2026](https://www.buildmvpfast.com/blog/langgraph-vs-crewai-vs-autogen-vs-swarms-agent-framework-2026)
- [Claude Agent SDK vs OpenAI Agents SDK vs Google ADK - Composio](https://composio.dev/content/claude-agents-sdk-vs-openai-agents-sdk-vs-google-adk)
- [Claude Agent SDK vs OpenAI Agents SDK: Which to Build On in 2026 - NomadX](https://nomadx.ae/blog/claude-agent-sdk-vs-openai-agents-sdk-2026/)
- [Claude Agent SDK vs OpenAI Agents SDK - Agentlas](https://agentlas.pro/compare/claude-agent-sdk-vs-openai-agents-sdk/)
- [LangGraph vs OpenAI Agents SDK vs Claude Agent SDK: The Decision After OpenAI Closed the Gap](https://dreaming.press/posts/agent-sdk-decision-2026-loop-graph-or-handoffs.html)
