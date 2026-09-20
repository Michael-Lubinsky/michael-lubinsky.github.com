# pi.dev implementation

Pi has no graph, no crew, no handoff/subagent primitive in its core --
it is deliberately four tools (read/write/edit/bash) plus a system
prompt, with everything else opt-in via TypeScript extensions. So this
"implementation" is:

- `arxiv_tools.ts` — one extension adding a single `arxiv_search` tool
  (physics or math category, date window in, articles out). This is
  the idiomatic Pi way to add a capability: a typed function, nothing
  more.
- `AGENTS.md` — the orchestration logic that in every other framework
  here lives in code (graph edges, task definitions, handoffs, hooks)
  is instead written as instructions for the model to carry out itself
  inside one session: search physics, retry-and-widen if thin, search
  math, retry-and-widen, dedupe against a JSON file it reads/writes
  directly with its own `read`/`write` tools, compose the digest, and
  ask for approval as a plain conversational question.
- `prompts/digest.md` — a Pi prompt template (`/digest`) that kicks the
  whole thing off.

## Run

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
# Register the extension per Pi's extension-loading convention, e.g.
# copy arxiv_tools.ts into ~/.pi/agent/extensions/ or package it as a
# Pi Package -- see https://pi.dev docs for the current mechanism.
cd pi_dev
pi
# then, inside the Pi session:
/digest
```

## What this demonstrates

Pi trusts one model, in one session, with a slightly bigger toolbox, to
sequence multi-step work itself -- no enforced retry edge, no enforced
approval gate, no separate agent processes. That is Pi's whole thesis:
push complexity out of the harness and into either (a) a small
extension or (b) the model's own judgement. You get simplicity and
full auditability of "what actually ran" (it's just tool calls in one
transcript); you lose the structural guarantees LangGraph's conditional
edges or the Claude Agent SDK's PreToolUse hook give you -- here, "must
retry if <3 hits" and "must pause for approval" are both instructions
the model could, in principle, skip.
