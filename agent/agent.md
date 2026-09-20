## Agent SDK  architectural differences: LangGraph, CrewAI, OpenAI, Claude, Pi, OMP

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

That is an important advantage visible in project below: you don't need to express ordinary programming constructs as framework concepts.

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

### Which differences project below demonstrates

| If you want to demonstrate...                                  | Framework that illustrates it particularly clearly in your code |
| -------------------------------------------------------------- | --------------------------------------------------------------- |
| Explicit deterministic workflow                                | **LangGraph**                                                   |
| Agents modeled as people/roles with assigned tasks             | **CrewAI**                                                      |
| Agentic behavior while retaining ordinary Python orchestration | **OpenAI Agents SDK**                                           |
| Controlling agent actions through lifecycle/tool hooks         | **Claude Agent SDK**                                            |
| Lightweight TypeScript agent implementation                    | **pi.dev**                                                      |
| Minimal CLI-oriented agent orchestration                       | **omp.sh**                                                      |

One especially useful point attached repository below demonstrates is that **“agentic SDK” does not mean the same programming model**. The business problem is identical—two researchers → dedupe → editor → human approval → publish—but each framework puts the abstraction boundary in a different place:

```text
LangGraph       → workflow is first-class
CrewAI          → team/tasks are first-class
OpenAI Agents   → agents/tools are first-class; Python orchestrates
Claude SDK      → agent/tool loop + hooks are first-class
pi.dev          → lightweight agent/tool runtime
omp.sh          → CLI/prompt/tool orchestration
```


# Project: arXiv Lecture Notes Digest — six framework implementations

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

[Download agents.zip](arxiv_digest_agents_v7.zip)
 
## Status of what's included

Every Python-based implementation was verified in this environment to
**import cleanly and construct its full object graph** (agents, tasks,
tools, handoffs/gather, the compiled LangGraph state graph, the Claude
Agent SDK's MCP server/subagents) without errors. Beyond that, this
revision adds **behavioral, offline tests** for the specific bugs the
review found — with real network and LLM calls mocked out, since this
sandbox's network allowlist blocks `export.arxiv.org` and no API keys
are configured here:

- `shared/arxiv_client.py`: pagination genuinely fetches more pages
  when the window widens (verified: `days=14` fetches 1 page,
  `days=150` fetches 2, against a mocked multi-page feed), and the
  returned `truncated` flag correctly distinguishes a scan that
  exhausted the feed or reached the window boundary naturally
  (`False`) from one that hit the page cap first (`True`); a
  future-dated entry is rejected; `canonicalize_id` strips version
  suffixes correctly.
- `shared/state_store.py`: `filter_unpublished` never writes (checked
  by asserting the file doesn't exist after calling it); a rejected
  digest's articles reappear identically on the next call; approving
  via `mark_published` persists them; a subsequent run correctly
  excludes them; a version-bumped resubmission (`v1` → `v2`) still
  dedupes via canonical ID; a 50-process concurrent
  `multiprocessing` stress test against `mark_published` lost zero
  updates with the `fcntl.flock` lock in place, and an equivalent
  control test reproducing the old unlocked read-modify-write under
  identical load lost 9 of 10 updates, confirming the race was real
  and the lock fixes it.
- **LangGraph**: a full simulated run through the compiled graph —
  reject leaves state empty and the same articles reappear next run;
  approve persists them; a third run correctly excludes them; a
  `physics_truncated` flag correctly produces a caveat line in the
  digest markdown when the mocked search reports it; the
  `merge_and_dedupe` fan-in barrier tested directly against an uneven
  branch scenario (physics needs a widen-retry, math doesn't) —
  confirmed `merge_and_dedupe` runs exactly once, only after both
  branches finish, and that the digest shown at the human-approval
  interrupt matches what `merge_and_dedupe` actually produced (this
  was not true before `defer=True` was added: the same scenario
  triggered two merge calls and an approval on incomplete data).
- **CrewAI**: `editor.tools` confirmed to contain only
  `filter_unpublished_titles` (no publish-capable tool present at
  all); `editor_task.output_pydantic is DigestDraft` and
  `editor_task.human_input is False` confirmed directly; the
  host-side `publish()` function tested directly for both a normal
  success (file written, state marked) and a simulated
  `mark_published` failure (confirmed rollback deletes `digest.md`
  and re-raises); `search_physics_tool` confirmed to surface
  `truncated: True` correctly in its JSON payload.
- **OpenAI Agents SDK**: the retry wrapper tested by mocking
  `Runner.run` to simulate three tripwire-then-success calls,
  confirming the actual widen sequence `14 → 28 → 56`; the
  `asyncio.gather` fan-out timed to confirm it runs concurrently
  (~0.2s wall time for two 0.2s calls, not ~0.4s); the tool functions'
  real call path (via `search_physics.__wrapped__`) tested for the
  same reject/approve sequence and confirmed to return a
  `SearchToolResult(truncated=...)` correctly for both a capped and a
  non-capped mocked scan; `publish_digest` tested directly for both a
  normal success and a simulated `mark_published` failure (confirmed
  rollback deletes `digest.md` before the error string is returned).
- **Claude Agent SDK**: the MCP tool handlers (via their `.handler`
  attribute) tested directly for the same reject/approve sequence and
  confirmed to return `{articles, truncated}` correctly for both a
  capped and a non-capped mocked scan; the `PreToolUse` hook function
  tested in isolation to confirm it returns a `deny` decision on
  rejection, `{}` (allow) on approval, and passes through untouched
  for any non-`publish_digest` tool call; `publish_tool` tested
  directly for both a normal success and a simulated `mark_published`
  failure (confirmed rollback deletes `digest.md` and returns an
  `is_error` result rather than silently succeeding).
- **pi.dev's TypeScript client**: type-checked with `tsc --noEmit`
  (zero errors); the `fast-xml-parser`-based parsing tested against
  entity-encoded and version-suffixed mock XML; HTTP-status-check,
  NaN-date-guard, and pagination logic each tested directly in Node;
  a mocked-`fetch` runtime test confirms `arxivSearch` reports
  `truncated: true` when a feed always returns full pages up to
  `MAX_PAGES`, and `truncated: false` when a feed runs out naturally
  within one page.

What still could not be verified here: an actual end-to-end run
against the live arXiv API, and an actual LLM-driven run of any of the
four Python frameworks (no API keys in this sandbox). Run these from a
normal machine with network access and the relevant API key to see a
full run.

## Side-by-side

| | Orchestration unit | Parallel fan-out | Retry/widen mechanism | Persistence | Human approval | Distinctive primitive |
|---|---|---|---|---|---|---|
| **LangGraph** | Graph nodes + edges | Native (two branches from `__start__`), joined at `merge_and_dedupe` via `defer=True` — a plain multi-edge convergence does **not** wait for both branches on its own when they can loop a different number of times | Explicit conditional edge, re-enters search node | `MemorySaver` checkpointer; state written **only** in the `publish` node, post-approval | `interrupt()` + `Command(resume=...)` — graph genuinely suspends | Explicit, drawable state graph |
| **CrewAI** | Role-based Agents + Tasks | Sequential by default; editor task's `context=[...]` waits on both research tasks | Agent's own tool-calling loop (instructed to retry, not enforced) | The Editor agent has **no publish-capable tool at all** — it returns a structured `DigestDraft` (`output_pydantic`); the actual file write + `mark_published()` happen in plain host-side Python, outside any agent's control | A plain `input()` call in host code the agent has no path to bypass, since it never held a tool that could publish | Role/goal/backstory mental model |
| **OpenAI Agents SDK** | Small Agents + explicit `asyncio.gather(Runner.run(...))` | Genuine (`asyncio.gather`, timed and confirmed concurrent) | `output_guardrail` tripwire **caught** by `run_specialist_with_retry`, which reruns with a doubled window | A `publish_digest` tool; state written only there, on approval | A tool call (`request_human_approval`) the orchestrator must invoke | Guardrail exception as a real retry trigger |
| **Claude Agent SDK** | One primary agent + Task-tool subagents | Two subagents launched via `Task` | Subagent's own instructed loop (like CrewAI) | MCP `publish_digest` tool; state written only if the hook allows the call | **`PreToolUse` hook** denies the `publish_digest` call until approved — enforced by the harness, not the model | "Give one agent a computer"; hooks intercept tool execution |
| **pi.dev** | One session, one model, bigger toolbox | None — sequential, inside one transcript | Written as an instruction in `AGENTS.md`; nothing enforces it | Model reads `published.json` read-only at draft time; writes it only in the final, explicitly-approved step | Plain conversational question; nothing blocks an early write except the instructions | Minimal 4-tool core + a single TS extension |
| **omp.sh** | One orchestrator + native subagent spawn | **Native parallel task spawn** (physics + math subagents at once) | Each subagent's own instructed loop | Same read-then-write-only-on-approval split, enforced by instruction only (`omp.config.toml` says so explicitly) | Same gap as pi.dev — instruction-only, not harness-enforced | Persistent Python/Bun kernel callable from the agent's own tools |

## What this actually teaches

- **Control enforcement vs. model discretion — and instructing a model
  better is not the same as removing its discretion.** LangGraph
  (`interrupt()`), the Claude Agent SDK (`PreToolUse` hook), and CrewAI
  (after the v3 fix) all now make the *state write itself* something
  the model has no path to trigger without going through a real gate;

  OpenAI's SDK still relies on the orchestrator agent choosing to call
  an approval tool before a publish tool, same as pi.dev and omp.sh
  rely on the model following an instruction.

  The CrewAI revision is
  the clearest illustration of the difference between the two
  strategies: the v2 fix tried to gate `publish_digest` by *instructing*
  the Editor agent to call it only after approval, and a second review
  round correctly pointed out that's not a permission gate, just a
  hope. The v3 fix doesn't gate the tool better — it removes the tool
  from the agent's reach entirely and does the actual write in host
  code the model never touches. That's the general pattern worth
  taking away: a safety property that depends on an LLM correctly
  interpreting an instruction is strictly weaker than one where the
  capability simply isn't reachable from inside the model's control
  flow, no matter how carefully the instruction is worded.
- **A guardrail is a validator, not a controller, until something
  catches it.** The OpenAI Agents SDK fix is the clearest illustration:
  `output_guardrail` on its own only produces a pass/fail signal
  (a raised exception). Turning "fail" into "retry with different
  parameters" required an explicit `try`/`except` wrapper in
  orchestrator code — the guardrail is necessary but not sufficient.
- **Where "state" lives.** LangGraph's checkpointer persists the
  *entire graph state* (not just the published-articles file) keyed by
  a thread ID, so a crashed run could resume mid-graph. Everyone else
  treats persistence as "a function that reads/writes one JSON file" —
  functionally equivalent for this task, but LangGraph's version
  generalizes further.
- **Parallelism is a spectrum, and "looks parallel" isn't the same as
  "is parallel."** LangGraph and omp.sh have real native fan-out.
  OpenAI's SDK needed an explicit `asyncio.gather` — its `handoffs`
  primitive, despite superficially looking like delegation, is actually
  sequential control transfer and does not fan out on its own. CrewAI's
  default `Process.sequential` waits on `context=[...]` rather than
  truly forking. pi.dev has no fan-out primitive at all.
- **Fanning out is easy; fanning back in correctly is the hard part,
  especially across branches of uneven length.** LangGraph's own fix
  in v4 is the clearest example in this project: two parallel branches
  converging on the same node via ordinary edges looks like a natural
  join, and reads like one in a quick skim — but it's only a real
  barrier if both branches finish in the same superstep. A retry loop
  on just one branch breaks that assumption silently: nothing raises
  an error, the graph just runs the "joined" node once per branch
  instead of once total, on whatever partial state exists each time.
  The fix (`defer=True`) is a one-line, well-documented feature made
  for exactly this — but only if you know a plain multi-edge
  convergence isn't already sufficient, which is exactly the kind of
  assumption that's easy to state confidently in a comment and never
  actually exercise with branches of different lengths.
- **Vendor lock-in is inversely related to structure.** The two most
  structured tools (LangGraph, CrewAI) are model-agnostic. The two
  "give the agent a computer" harnesses (Claude Agent SDK, omp.sh) are
  the most capable at real OS-level work (files, shell, a live Python
  kernel) but hand you a single powerful agent plus a way to spawn
  narrow helpers, not a graph or a role hierarchy.

## Layout

```
arxiv_digest_agents/
├── CHANGELOG.md              # v1→v2 (12 findings), v2→v3 (4 findings), v3→v4 (1 finding), v5/v6 (usability) reviews + fixes
├── shared/
│   ├── arxiv_client.py       # arXiv search/filter/pagination, used by every Python impl
│   └── state_store.py        # published-state store: filter_unpublished / mark_published split
├── langgraph/digest_graph.py
│   └── output/digest.md      # generated at run time, not checked in
├── crewai/digest_crew.py
│   └── output/digest.md      # generated at run time, not checked in
├── openai_agents_sdk/digest_agents.py
│   └── output/digest.md      # generated at run time, not checked in
├── claude_agent_sdk/digest_agent.py
│   └── output/digest.md      # generated at run time, not checked in
├── pi_dev/{AGENTS.md, arxiv_tools.ts, package.json, prompts/arxiv_digest_prompt.md, README.md}
│   └── output/digest.md      # generated at run time, not checked in
├── omp_sh/{omp.config.toml, SYSTEM.md, prompts/*.md, README.md}
│   └── output/digest.md      # generated at run time, not checked in
└── requirements.txt
```

Every implementation writes its generated digest to its own
`output/digest.md`


