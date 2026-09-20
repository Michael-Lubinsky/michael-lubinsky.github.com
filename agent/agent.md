Agent SDK  architectural differences.

| SDK / Framework       | Main orchestration model                  | How agents cooperate in your code                                                             | Tool calling                               | Parallel agents                                         | Human approval                           | Workflow/state model                                                     | Main distinguishing feature                                                        |
| --------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **LangGraph**         | **Explicit graph / state machine**        | Nodes connected by edges; results accumulated in shared state                                 | Python functions/tools used by graph nodes | **Yes**, graph branches can fan out and join            | Explicit approval node                   | **Strongest explicit state management** via `State` passed through graph | You design the **workflow graph yourself**                                         |
| **CrewAI**            | **Crew + agents + tasks**                 | Researcher agents execute assigned tasks; Editor combines results                             | Tools attached directly to agents          | Supported, but task-oriented rather than graph-oriented | `human_input=True` on task               | Mostly managed by Crew/task execution                                    | Highest-level **role/task abstraction**                                            |
| **OpenAI Agents SDK** | **Agents + Runner + tools**               | Your Python code explicitly runs Physics and Math agents with `asyncio.gather()`, then Editor | Native function tools                      | **Yes**, explicitly through Python async                | Application-level approval/publish logic | Mostly normal Python variables/results                                   | **Minimal agent abstraction integrated with normal Python**                        |
| **Claude Agent SDK**  | **Agentic tool loop + hooks**             | Claude decides when/how to use supplied tools; application provides lifecycle hooks           | MCP-style/custom tools                     | More agent-directed; not expressed as a workflow graph  | **PreToolUse hook** can block publishing | Conversation/tool-loop oriented                                          | **Hooks around agent/tool execution**, especially useful for enforcing permissions |
| **pi.dev**            | **Minimal TypeScript agent/tool runtime** | Agent works through tools and instructions with relatively little framework structure         | TypeScript tools                           | Mostly controlled by your application/agent loop        | Implemented around publishing logic      | Application-managed                                                      | **Lightweight TypeScript-first approach**                                          |
| **omp.sh**            | **CLI / shell-oriented agent execution**  | Workflow largely expressed through prompts, tools and command-line orchestration              | CLI/tool capabilities                      | Depends primarily on external orchestration             | Application/prompt/tool boundary         | Little formal workflow state                                             | **Agentic workflow with minimal application framework/code**                       |

### The biggest conceptual difference

The six approaches can be placed roughly on a spectrum:

```text
Explicit workflow                                      Agent autonomy
      │                                                       │
      ▼                                                       ▼

 LangGraph  ─── CrewAI ─── OpenAI Agents ─── Claude ─── pi.dev / omp.sh

 graph          tasks        Python          tool-loop       lightweight
 controlled     roles        controlled       + hooks         runtime/CLI
```

This is simplified—the SDKs overlap considerably—but it captures what your examples demonstrate particularly well.

**LangGraph asks:** *What is the workflow?*
You explicitly define:

```text
START
  ├── Physics Research
  └── Math Research
          ↓
       Merge
          ↓
       Editor
          ↓
      Approval
          ↓
       Publish
```

The graph itself is the central abstraction.

**CrewAI asks:** *Who performs each job?*
Your main concepts become:

```text
Agents:
    Physics Researcher
    Math Researcher
    Editor

Tasks:
    Research physics
    Research math
    Build digest
```

So it models an organization/team more naturally than a state machine.

**OpenAI Agents SDK asks:** *Which agent should I run, and which tools can it use?*
Your ordinary Python remains responsible for orchestration:

```python
physics_result, math_result = await asyncio.gather(
    Runner.run(physics_agent, ...),
    Runner.run(math_agent, ...),
)

result = await Runner.run(editor_agent, ...)
```

That is an important advantage visible in your project: you don't need to express ordinary programming constructs as framework concepts.

**Claude Agent SDK asks:** *What should the agent do with these tools, and what controls should surround tool execution?*
The particularly interesting part of your implementation is the hook:

```text
Claude
   ↓
wants publish_digest
   ↓
PreToolUse hook
   ↓
Human approval
   ├── No  → DENY
   └── Yes → tool executes
```

That is materially different from simply telling an agent, *"ask the human before publishing."* The application can enforce the boundary.

### Which differences your project demonstrates best

| If you want to demonstrate...                                  | Framework that illustrates it particularly clearly in your code |
| -------------------------------------------------------------- | --------------------------------------------------------------- |
| Explicit deterministic workflow                                | **LangGraph**                                                   |
| Agents modeled as people/roles with assigned tasks             | **CrewAI**                                                      |
| Agentic behavior while retaining ordinary Python orchestration | **OpenAI Agents SDK**                                           |
| Controlling agent actions through lifecycle/tool hooks         | **Claude Agent SDK**                                            |
| Lightweight TypeScript agent implementation                    | **pi.dev**                                                      |
| Minimal CLI-oriented agent orchestration                       | **omp.sh**                                                      |

One especially useful point your repository demonstrates is that **“agentic SDK” does not mean the same programming model**. The business problem is identical—two researchers → dedupe → editor → human approval → publish—but each framework puts the abstraction boundary in a different place:

```text
LangGraph       → workflow is first-class
CrewAI          → team/tasks are first-class
OpenAI Agents   → agents/tools are first-class; Python orchestrates
Claude SDK      → agent/tool loop + hooks are first-class
pi.dev          → lightweight agent/tool runtime
omp.sh          → CLI/prompt/tool orchestration
```


# arXiv Lecture Notes Digest — six framework implementations

Same task, six harnesses/frameworks, so the differences show up in
**how work is structured**, not in what the task does.

## The task

1. Search arXiv **physics** categories (quant-ph, hep-th, cond-mat) for
   lecture-notes-style papers from the last 2 weeks on quantum
   mechanics, QFT, or solid state physics.
2. Search arXiv **math** categories for lecture-notes-style papers from
   the last 2 weeks (any subject).
3. If either search returns fewer than 3 hits, widen the window
   (double it, cap 60 days) and retry, up to 2 retries.
4. Merge, dedupe against titles already reported in a previous run
   (persisted state), and produce one Markdown digest.
5. Require a human approval step before "publishing" (writing the
   final `digest.md`).

`shared/arxiv_client.py` and `shared/state_store.py` hold the one piece
that's identical everywhere — the arXiv Atom API call, the keyword
filters, and the JSON-backed seen-titles file — so every implementation
below is orchestration logic only.

[Download agents.zip](arxiv_digest_agents_v3.zip)
 

## Status of what's included

Every Python-based implementation was verified in this environment to
**import cleanly and construct its full object graph** (agents, tasks,
tools, handoffs, the compiled LangGraph state graph, the Claude Agent
SDK's MCP server/subagents) without errors. The shared `arxiv_client.py`
parsing/filtering logic was verified against a mocked arXiv feed and
correctly handled the retry-and-widen path. What could **not** be run
end-to-end here: this sandbox's network allowlist blocks
`export.arxiv.org` (only package registries and GitHub are reachable),
and none of the four LLM-backed frameworks had API keys configured. So:
correct wiring is confirmed; a live, LLM-driven run is not. Run any of
these from a normal machine with network access and the relevant API
key to see it go end to end.

The pi.dev and omp.sh "implementations" are config/prompt/extension
files, not Python — both harnesses are driven by a CLI + Markdown
instructions + (for pi) a small TypeScript tool, so there's no Python
object graph to construct. The TypeScript tool's parsing logic was
type-checked and verified against a mocked feed in Node directly.


## Side-by-side

| | Orchestration unit | Parallel fan-out | Retry/widen mechanism | Persistence | Human approval | Distinctive primitive |
|---|---|---|---|---|---|---|
| **LangGraph** | Graph nodes + edges | Native (two branches from `__start__`) | Explicit conditional edge, re-enters search node | `MemorySaver` checkpointer, keyed by `thread_id` | `interrupt()` + `Command(resume=...)` — graph genuinely suspends | Explicit, drawable state graph |
| **CrewAI** | Role-based Agents + Tasks | Sequential by default; editor task's `context=[...]` waits on both research tasks | Agent's own tool-calling loop (instructed to retry, not enforced) | A dedupe **tool** the Editor agent calls | `Task(human_input=True)` — blocks on literal input | Role/goal/backstory mental model |
| **OpenAI Agents SDK** | Small Agents + typed handoffs | Triage agent hands off to both specialists | `output_guardrail` trips when `hit_count < MIN_HITS` | A `function_tool` wrapping the JSON store | A tool call (`request_human_approval`) the orchestrator must invoke | Guardrails as the control primitive |
| **Claude Agent SDK** | One primary agent + Task-tool subagents | Two subagents launched via `Task` | Subagent's own instructed loop (like CrewAI) | MCP tool wrapping the JSON store; agent has real file I/O too | **`PreToolUse` hook** denies the `publish_digest` tool call until approved — enforced by the harness, not the model | "Give one agent a computer"; hooks intercept tool execution |
| **pi.dev** | One session, one model, bigger toolbox | None — sequential, inside one transcript | Written as an instruction in `AGENTS.md`; nothing enforces it | Model reads/writes the JSON file directly with its own `read`/`write` tools | Plain conversational question; nothing blocks the file write | Minimal 4-tool core + a single TS extension |
| **omp.sh** | One orchestrator + native subagent spawn | **Native parallel task spawn** (physics + math subagents at once) | Each subagent's own instructed loop | Persistent Python kernel with tool-loopback does merge/dedupe as one script | Same gap as pi.dev — instruction-only, not harness-enforced | Persistent Python/Bun kernel callable from the agent's own tools |

## What this actually teaches

- **Control enforcement vs. model discretion.** Only LangGraph
  (`interrupt()`) and the Claude Agent SDK (`PreToolUse` hook) make the
  approval step something the *harness* blocks on. CrewAI's
  `human_input=True` is close but simpler (a literal input() pause,
  not a resumable graph state). OpenAI's guardrail model enforces
  *validation* (did the specialist meet the minimum?) more naturally
  than it enforces *human* gates — you'd reach for `needs_approval` on
  a tool in a fuller build. pi.dev and omp.sh enforce nothing — the
  model can skip the approval question if it decides to, which is the
  honest cost of a minimal harness.
- **Where "state" lives.** LangGraph's checkpointer is the only one
  that persists the *entire graph state* (not just the seen-titles
  file) keyed by a thread ID, meaning you could resume a crashed run
  mid-graph. Everyone else treats persistence as "a tool that reads/
  writes one JSON file" — functionally equivalent for this task, but
  LangGraph's version generalizes to much longer-running agents.
- **Parallelism is a spectrum.** LangGraph and omp.sh have real
  native fan-out (two things genuinely happen concurrently, wired at
  the framework level). OpenAI's handoff model is nominally
  sequential (triage hands off once, one at a time in this
  implementation, though the SDK supports parallel handoffs).
  CrewAI's default `Process.sequential` waits on `context=[...]`
  rather than truly forking. pi.dev has no fan-out primitive at all.
- **Vendor lock-in is inversely related to structure.** The two most
  structured tools (LangGraph, CrewAI) are model-agnostic. The two
  "give the agent a computer" harnesses (Claude Agent SDK, omp.sh) are
  the most capable at real OS-level work (files, shell, a live Python
  kernel) but are the least structured about *coordinating multiple
  agents* — they hand you a single powerful agent plus a way to spawn
  narrow helpers, not a graph or a role hierarchy.

## Layout

```
agent/
├── shared/
│   ├── arxiv_client.py       # identical arXiv search/filter logic, used by every Python impl
│   └── state_store.py        # identical JSON seen-titles store
├── langgraph/digest_graph.py
├── crew/digest_crew.py
├── openai_agents_sdk/digest_agents.py
├── claude_agent_sdk/digest_agent.py
├── pi_dev/{AGENTS.md, arxiv_tools.ts, prompts/digest.md, README.md}
├── omp_sh/{omp.config.toml, SYSTEM.md, prompts/*.md, README.md}
└── requirements.txt
```


### What's in here

shared/ — identical arXiv API client + JSON dedup store, used by every Python implementation, so the differences you see are pure orchestration, not incidental code differences.

langgraph/digest_graph.py — explicit StateGraph with real parallel fan-out, a conditional edge for the widen-retry, a MemorySaver checkpointer, and interrupt()/Command(resume=...) for approval. Verified: compiles and I printed its Mermaid graph to confirm the topology is right.

crew/digest_crew.py — role-based Physics/Math/Editor agents, context=[...] task wiring, Task(human_input=True). Verified: constructs cleanly.

openai_agents_sdk/digest_agents.py — Triage agent with typed handoffs to two specialists, an output_guardrail enforcing the min-hits rule. Verified: constructs cleanly.

claude_agent_sdk/digest_agent.py — one orchestrator agent, Task-tool subagents, custom MCP tools, and a PreToolUse hook that actually denies the publish tool call until approved. Verified: constructs cleanly.

pi_dev/ — AGENTS.md (orchestration as plain instructions) + a TypeScript arxiv_search tool. Verified: type-checks and its filtering logic matched Python's output against a mocked feed.

omp_sh/ — TOML config declaring native parallel subagents plus a SYSTEM.md leaning on omp's persistent Python kernel. Verified: TOML is well-formed.
