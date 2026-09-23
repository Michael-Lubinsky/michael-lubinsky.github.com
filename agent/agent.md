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
  structured tools (LangGraph, CrewAI) are model-agnostic.

  The two "give the agent a computer" harnesses (Claude Agent SDK, omp.sh) are
  the most capable at _real OS-level work_ (files, shell, a live Python
  kernel) but hand you a single powerful agent plus a way to spawn
  narrow helpers, not a graph or a role hierarchy.


1. **What "real OS-level work" actually means in this repo** — contrasts CrewAI's Editor, which *cannot* call `publish_digest` (the tool object isn't in its `tools=` list, full stop) against Claude Agent SDK/omp.sh agents that hold general-purpose primitives (`read`/`write`/`edit`/`bash`, a persistent Python/Bun kernel) *in addition to* their project-specific tools — e.g. omp.sh's orchestrator runs filter→compose→approve→publish as one script inside a live interpreter, not four separate tool calls.

2. **What's traded away** — no inspectable graph or role hierarchy. LangGraph's and CrewAI's structure is typed Python objects you can enumerate and unit-test without ever invoking the model (which is literally how the v4 fan-in bug got found and fixed). Claude Agent SDK's `ORCHESTRATOR_PROMPT` and omp.sh's `SYSTEM.md` are prose the model interprets at runtime — nothing to point at as "the" delegation edge. I also tied this back to the CrewAI v3 fix: an instruction alone was never a real gate there either, and noted that Claude Agent SDK's `PreToolUse` hook is a genuine exception (enforcement code, not wording) while omp.sh has no equivalent at all.

3. **Where the lock-in specifically bites**   
    LangGraph/CrewAI's portability is a one-line `llm=` swap;  
   Claude Agent SDK's `PreToolUse` hook (this project's strongest approval gate) is that SDK's own runtime construct with no fallback off-Claude,  
   and omp.sh is a distinct product (its own kernel, its own TOML subagent config) you'd rebuild against, independent of which model it's pointed at.

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

### LangGraph Note

 **The graph itself is not the main value of LangGraph.** You can implement nodes, edges, branches, loops, and parallel execution perfectly well with Python `if`, `while`, functions, `asyncio`, etc.

What LangGraph adds is primarily a **runtime for stateful, long-running graphs**, especially around LLM/agent workflows. Its own documentation describes it as a low-level orchestration framework providing durable execution, persistence, streaming, human-in-the-loop, and memory. ([LangChain AI][1])

Consider your arXiv workflow:

```text
Physics ──┐
          ├─> Merge -> Digest -> Human approval -> Publish
Math ─────┘
```

Writing that yourself is easy. Where LangGraph starts earning its keep is when execution becomes operationally complicated.

### The biggest benefit: checkpointed state

Suppose the workflow reaches:

```text
✓ Physics search
✓ Math search
✓ Merge
✓ Generate digest
→ Waiting for human approval
```

and you approve it **three hours later**, possibly after the original process has disappeared.

With ordinary Python, you need to design persistence yourself: what state to serialize, where to store it, how to identify the run, and how to restart from the correct point.

LangGraph has the concept of a **checkpointer**. It stores graph-state snapshots associated with a `thread_id`, specifically supporting resumption, human-in-the-loop, fault tolerance, and state history. ([LangChain AI][2])

So the interesting comparison isn't:

```text
Python                    LangGraph

if result:
    publish()             graph.add_edge(...)
```

It's:

```text
Your implementation       LangGraph
───────────────────       ─────────────────
execution graph           built in
state model               built in
checkpointing             built in
resume execution          built in
human interrupts          built in
state history             built in
streaming events/state    built in
parallel graph nodes      built in
```

### Human-in-the-loop is a good example

Your arXiv project requires approval before publication.

In plain Python you might write:

```python
answer = input("Approve? ")
if answer == "yes":
    publish()
```

That's fine for a command-line demo.

But suppose approval comes tomorrow through a web UI. The application must stop now, preserve the workflow state, and later continue the same execution.

LangGraph lets a node do conceptually:

```python
approved = interrupt({
    "question": "Publish this digest?",
    "digest": state["digest"]
})
```

At the interrupt, the graph state is checkpointed. Later you resume the same thread with a `Command(resume=...)`. ([LangChain AI][3])

That's substantially harder to implement robustly yourself.

### Failure recovery is another important difference

Imagine:

```text
Physics search       ✓   $0.05
Math search          ✓   $0.05
Summarization        ✓   $0.20
Human approval       ✓
Publish to website   ✗   network error
```

You don't necessarily want to run all those LLM calls again.

LangGraph checkpoints at graph/node boundaries. Its checkpoint model also preserves successful pending writes when other nodes fail, allowing completed work to be reused during recovery. ([LangChain AI][4])

Again, you *can* build this yourself—but you're now writing a workflow runtime rather than business logic.

### State inspection and debugging

A normal Python workflow often leaves you asking:

```text
What happened on this run?
What did the state contain before summarization?
Why did the graph take branch B?
Can I restart from an earlier state?
```

LangGraph maintains checkpoint history, making state evolution inspectable. ([LangChain AI][4])

This matters considerably more with agents because control flow is partially nondeterministic.

### But there's an important downside

For something as simple as your current arXiv digest:

```text
search physics
search math
merge
generate
approve
write file
```

**LangGraph may be overkill.**

I could write this quite naturally:

```python
physics, math = await asyncio.gather(
    search_physics(),
    search_math()
)

papers = dedupe(physics + math)
digest = generate_digest(papers)

if await approve(digest):
    publish(digest)
    mark_published(papers)
```

That is easier for almost any Python developer to understand than the equivalent graph definition.

LangGraph becomes compelling when the workflow evolves toward something like:

```text
                 ┌── retry ──────────┐
                 ↓                   │
Physics → Validate ── insufficient ──┘
   │
   ├─────────────┐
                 ↓
Math → Validate → Merge
                   ↓
               Summarize
                   ↓
               Fact check
                ↙      ↘
             retry     good
               ↑        ↓
               └── Digest
                     ↓
                  interrupt
                     ↓
               Human review
                 ↙       ↘
              revise    approve
                ↑          ↓
                └────── Publish
                           ↓
                      persist state
```

Now persistence, retries, branching, cycles, parallelism, interrupts and observability start making a workflow engine attractive.

So I'd characterize LangGraph in your framework comparison as:

> **LangGraph is not valuable because it lets you draw an execution graph. Its value is providing a durable stateful runtime around that graph.**

And that actually gives you an interesting lesson for your repository: **don't judge LangGraph primarily by how elegantly it expresses your arXiv graph.** Your example is simple enough that ordinary Python wins on simplicity. The more meaningful test is whether its **checkpoint/resume, failure recovery and human-approval lifecycle** require less infrastructure than implementing those capabilities yourself.

[1]: https://langchain-ai.github.io/langgraph/reference/?utm_source=chatgpt.com "langgraph | LangChain Reference"
[2]: https://langchain-ai.github.io/langgraphjs/how-tos/cross-thread-persistence-functional/?utm_source=chatgpt.com "Persistence - Docs by LangChain"
[3]: https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/?featured_on=talkpython&utm_source=chatgpt.com "Interrupts - Docs by LangChain"
[4]: https://langchain-ai.github.io/langgraph/reference/checkpoints/?h=langgraph+checkpoint+sqlite+import+saver&utm_source=chatgpt.com "checkpoints | langgraph | LangChain Reference"

##  LangGraph vs Claude Agent SDK

The key distinction is **who should control the workflow**.

**LangGraph is generally a better fit when your application should control the execution. Claude Agent SDK is generally a better fit when you want Claude to control how a task gets accomplished.**

Anthropic's own documentation makes a similar distinction: with ordinary Agent SDK subagents, Claude decides what to delegate turn by turn; with deterministic workflows, code holds the plan. ([Claude Platform][1])

### Example 1: Your arXiv digest

Your requirements are quite deterministic:

```text
Physics search ──┐
                 ├── Merge → Dedupe → Digest
Math search ─────┘                 ↓
                              Human approval
                               ↙        ↘
                            reject     approve
                                         ↓
                                      publish
                                         ↓
                                  mark_published
```

You probably **don't want an LLM deciding** whether deduplication happens before or after approval, whether to skip a research branch, or whether `mark_published()` should execute.

That's a natural LangGraph-style problem:

```python
graph.add_edge("physics", "merge")
graph.add_edge("math", "merge")
graph.add_edge("merge", "digest")
graph.add_edge("digest", "approval")
...
```

The LLM does the fuzzy work inside selected nodes; application code owns the business process.

For your arXiv application, I'd therefore lean **LangGraph—or even plain Python—over Claude Agent SDK**.

---

### Example 2: Research assistant

Now imagine:

> Investigate whether quantum error correction has had important experimental advances recently. Search papers, inspect promising ones, follow references when useful, compare competing approaches, and write a report.

You don't know beforehand whether the execution should be:

```text
search → read → write
```

or:

```text
search
  ↓
read 10 papers
  ↓
discover interesting reference
  ↓
search again
  ↓
delegate superconducting-qubit research
  ↓
delegate trapped-ion research
  ↓
compare
  ↓
notice contradiction
  ↓
research contradiction
  ↓
write report
```

Trying to encode every possibility into a LangGraph graph can become counterproductive.

This is where Claude Agent SDK becomes attractive. Its agent can decide which tools to call and can delegate to specialized subagents with separate contexts. Anthropic describes subagents as supporting specialization, context separation, and parallelization. ([Claude Platform][2])

---

### The distinction isn't absolute anymore

Claude Agent SDK has become more workflow-capable. Anthropic now supports **dynamic workflows**, where Claude can create an orchestration script and a runtime executes the explicit logic, including parallel/staged subagents. ([Claude Platform][1])

And Anthropic also has Managed Agents with persistent stateful sessions, event history, long-running execution, interruption and steering. ([Claude Platform][3])

So I wouldn't describe this as “LangGraph has persistence and Claude doesn't.” That distinction is increasingly outdated.

Instead, I'd use this decision rule:

| Requirement                                   | More natural fit     |
| --------------------------------------------- | -------------------- |
| Predetermined workflow                        | **LangGraph**        |
| LLM determines workflow dynamically           | **Claude Agent SDK** |
| Strict business process                       | **LangGraph**        |
| Many explicit branches/cycles                 | **LangGraph**        |
| Need checkpoint/resume of your explicit graph | **LangGraph**        |
| Open-ended research                           | **Claude Agent SDK** |
| Coding/filesystem agent                       | **Claude Agent SDK** |
| Agent decides which tools/subagents it needs  | **Claude Agent SDK** |
| Highly autonomous task                        | **Claude Agent SDK** |
| Provider/model flexibility matters            | **LangGraph**        |
| Primarily using Claude anyway                 | **Claude Agent SDK** |

### A useful mental model

Think of LangGraph as:

> **Your program is the boss; LLMs are workers inside the program.**

```text
Application
     │
     ├── Node ── LLM
     │
     ├── Node ── Python
     │
     ├── condition
     │      ├── Node ── LLM
     │      └── Node ── API
     │
     └── approval
```

Think of Claude Agent SDK as:

> **Claude is the worker/manager; your program gives it capabilities and constraints.**

```text
          Claude
             │
       decides next action
       ┌─────┼─────┐
       ↓     ↓     ↓
     Tool  Agent  Tool
             │
             ↓
           Agent
             │
       decides again...
```

That difference is more fundamental than the syntax of either SDK.

And it explains why your framework-comparison project is useful: **LangGraph and Claude Agent SDK aren't simply two competing implementations of the same abstraction.** They represent two different answers to *where orchestration intelligence should live*: primarily in deterministic application code versus primarily in an autonomous model-driven loop.

[1]: https://platform.claude.com/cookbook/claude-agent-sdk-08-dynamic-workflows?utm_source=chatgpt.com "Orchestrate subagents at scale with dynamic workflows | Claude Cookbook"
[2]: https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent?utm_source=chatgpt.com "The chief of staff agent | Claude Cookbook"
[3]: https://platform.claude.com/docs/en/managed-agents/sessions?utm_source=chatgpt.com "Start a session - Claude Platform Docs"





## Vendor-agnostic orchestration frameworks

<https://www.kdnuggets.com/10-agentic-ai-frameworks-you-should-know-in-2026>

<https://habr.com/ru/articles/1084030/> Jev

**LangGraph** — Models agents as nodes in an explicit state graph with shared state, checkpointing, and human-in-the-loop primitives. It reached 1.0 GA on October 22, 2025, with a no-breaking-changes commitment until 2.0, and documented production users include Klarna, Replit, Uber, LinkedIn, and Elastic. It's model-agnostic via LangChain's integration layer. Steepest learning curve of the group, but it's the strongest production story: durable execution means agents survive server restarts, and LangSmith gives full tracing/observability. Best when you need explicit control over execution paths, retries, and branching logic.

**CrewAI** — Role-based: Agents (with roles), Tasks, and Crews that orchestrate them — the mental model is a team of specialists working together, not a flowchart. It's the fastest path to a working multi-agent prototype — you can have something running before lunch — and by March 2026 it had native MCP and A2A (agent-to-agent) protocol support. Weaker on fine-grained control: if you need to specify exactly which node executes after which condition, CrewAI's higher-level abstractions can feel limiting. Best for role-mapped pipelines (researcher → writer → reviewer, support triage).

## Vendor harness SDKs

**Claude Agent SDK** (what Claude Code itself runs on) — Anthropic extracted the agent harness that powers Claude Code and shipped it as a general-purpose SDK, renamed from the Claude Code SDK along the way. The design philosophy is "give one capable agent a computer" — a single autonomous agent with deep OS/filesystem access, controlled by what it's allowed to do.   
It treats MCP as native plumbing, unsurprising since Anthropic created the protocol — this is the natural fit if you want your agent reading/writing files, running shell commands, or orchestrating pipelines directly. It centers on hooks and subagents — intercepting and controlling behavior at lifecycle points, with task delegation through child agents — giving precise control over what an agent can and cannot do. Both Python and TypeScript are first-class.

**OpenAI Agents SDK** — Opposite philosophy: many lightweight agents wired together, controlling how work flows between them via explicit typed handoffs, guardrails, and tools. Originally the more minimal/orchestration-only of the two, but it closed the capability gap fast:   
an April 15, 2026 overhaul added native sandbox execution (Modal, Daytona, Docker, E2B),  
a model-native harness, durable state via externalized snapshotting/rehydration, and subagents — the features that used to be Claude/LangGraph's exclusive edge.   
It's genuinely provider-agnostic now, working with 100+ non-OpenAI models, not locked to OpenAI as older comparisons claim.   
Best if you want lightweight orchestration, voice (still OpenAI's clear strength), or model flexibility.

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

Positioning-wise: 
### pi.dev's whole pitch is "four tools, get out of the way, extend via TypeScript." 

### OMP takes the opposite bet — "most harnesses give the agent a sandbox and call it done
we wire in everything your IDE knows" — trading pi's minimalism for a much deeper, batteries-included environment while keeping pi's model-agnostic, terminal-first spirit. 
It sits closest to Claude Agent SDK's "give the agent a computer" philosophy, but as an independent, provider-agnostic open-source project rather than a vendor SDK.

### Where it'd fit against the others: 

if you're choosing between LangGraph/CrewAI (orchestration frameworks) vs. Claude Agent SDK/OpenAI Agents SDK (vendor harnesses) vs. pi/OMP (open-source terminal coding-agent harnesses) — pi and OMP are really answering a different question than LangGraph/CrewAI.   
They're not for building multi-agent business workflows; they're alternative engines for a single deeply-capable coding agent, competing more directly with Claude Code itself than with graph orchestrators.

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
