# omp.sh (Oh My Pi) implementation

omp is pi.dev's philosophy (minimal core, model does the sequencing)
with a much heavier Rust-core harness bolted on: in-process bash/
ripgrep/glob, a persistent Python + Bun kernel, native LSP/DAP, and a
built-in subagent-spawning tool (single/parallel/chain -- what backs
`/review`). Two of those (LSP, DAP) aren't relevant to a research task
with no code to refactor or debug, so this implementation leans on the
two that are:

- **Native parallel subagent spawn.** `omp.config.toml` declares
  `physics-researcher` and `math-researcher` as first-class subagents;
  `SYSTEM.md` tells the orchestrator to spawn both via the `task` tool
  at once. Unlike pi.dev (no subagent primitive at all, so the same
  work would run sequentially in one session) this is closer to the
  Claude Agent SDK's Task-tool subagents -- except configured via TOML
  instead of Python `AgentDefinition` objects, and without an MCP
  server layer in between.
- **Persistent Python kernel with tool loopback.** Once both subagents
  report back, the orchestrator does the merge/dedupe/compose step
  inside ONE running Python interpreter that can call back into the
  agent's own `read`/`write` tools mid-script. This is the feature
  omp's README highlights (loading a CSV with `tool.read` from inside
  Python, charting it from JS in the same cell) -- here it means the
  dedupe-against-history logic is one coherent script, not a chain of
  separate one-shot tool calls the way it would be in pi.dev's bash-
  only core.
- **No harness-enforced approval gate** -- same honest gap as pi.dev.
  `omp.config.toml` even says so explicitly
  (`approval.enforced_by_harness = false`): the pause-for-approval step
  is an instruction in `SYSTEM.md`, not something the harness itself
  blocks on the way LangGraph's `interrupt()` or the Claude Agent SDK's
  `PreToolUse` hook do.

## Run

```bash
# install per https://omp.sh (Rust binary, single executable)
cd omp_sh
omp   # reads omp.config.toml + SYSTEM.md automatically
```

## What this demonstrates vs. pi.dev

Same "trust the model to sequence the work" philosophy at the top
level, but omp gives that model a genuinely richer execution
environment (parallel subagent spawn as a real primitive, a live
Python process instead of fork-exec bash) -- so the same task needs
noticeably less "please do X then Y then Z" hand-holding in the system
prompt and can express the physics/math split as actual concurrent
subagents instead of two sequential tool calls in one transcript.
