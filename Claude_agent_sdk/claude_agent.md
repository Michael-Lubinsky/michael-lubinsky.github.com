```python
"""
Claude Agent SDK implementation of the arXiv lecture-notes digest agent.

What this is meant to demonstrate about the Claude Agent SDK specifically:
  - "GIVE ONE CAPABLE AGENT A COMPUTER": a single primary agent with real
    filesystem/tool access does the work end-to-end, rather than several
    small agents passing typed messages. It reads its own state file,
    writes the digest as an actual file, and can shell out if needed --
    no other framework in this comparison writes to disk natively.
  - SUBAGENTS for the two research tracks (Physics / Math), each with a
    narrow tool allowlist -- the SDK's delegation primitive, invoked via
    the Task tool rather than a "handoff" (SDK keeps control with the
    orchestrator) or a "crew" (no persistent role-play, just scoped
    sub-tasks).
  - MCP-STYLE CUSTOM TOOLS (create_sdk_mcp_server) exposing the shared
    arxiv_client functions -- because Anthropic created MCP, this is the
    idiomatic way to hand the agent new capabilities.
  - A HOOK (PreToolUse) that intercepts the "publish" tool call and
    requires human approval before it's allowed to run -- hooks are this
    SDK's lifecycle-interception mechanism, distinct from LangGraph's
    graph-level interrupt() or CrewAI's Task(human_input=True).

Run:
    pip install claude-agent-sdk
    export ANTHROPIC_API_KEY=...
    python digest_agent.py
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from shared.arxiv_client import search_physics_lecture_notes, search_math_lecture_notes
from shared.state_store import load_seen, save_seen

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    create_sdk_mcp_server,
    tool,
    HookMatcher,
)

MIN_HITS = 3
MAX_DAYS = 60
DIGEST_PATH = pathlib.Path(__file__).parent / "digest.md"


# ---- custom MCP tools, the idiomatic way to extend this SDK -----------

@tool(
    "search_physics",
    "Search arXiv physics categories for lecture-notes-style papers on "
    "quantum mechanics, QFT, or solid state physics within the last N days.",
    {"days": int},
)
async def search_physics_tool(args):
    results = search_physics_lecture_notes(days=args["days"])
    payload = [
        {"title": a.title, "arxiv_id": a.arxiv_id, "topic_tags": a.topic_tags}
        for a in results
    ]
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool(
    "search_math",
    "Search arXiv math.* categories for lecture-notes-style papers "
    "within the last N days.",
    {"days": int},
)
async def search_math_tool(args):
    results = search_math_lecture_notes(days=args["days"])
    payload = [{"title": a.title, "arxiv_id": a.arxiv_id} for a in results]
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool(
    "dedupe_and_record",
    "Given a JSON list of titles, drop ones already reported previously "
    "and record the rest as seen. Returns the fresh subset as JSON.",
    {"titles_json": str},
)
async def dedupe_tool(args):
    titles = json.loads(args["titles_json"])
    seen = load_seen()
    fresh = [t for t in titles if t not in seen]
    save_seen(seen | set(fresh))
    return {"content": [{"type": "text", "text": json.dumps(fresh)}]}


@tool(
    "publish_digest",
    "Write the final Markdown digest to disk. Gated by a PreToolUse hook "
    "requiring human approval.",
    {"markdown": str},
)
async def publish_tool(args):
    DIGEST_PATH.write_text(args["markdown"])
    return {"content": [{"type": "text", "text": f"written to {DIGEST_PATH}"}]}


arxiv_server = create_sdk_mcp_server(
    name="arxiv-digest-tools",
    version="1.0.0",
    tools=[search_physics_tool, search_math_tool, dedupe_tool, publish_tool],
)


# ---- hook: intercept publish_digest for human approval -------------------

async def require_approval_hook(input_data, tool_use_id, context):
    """PreToolUse hook: fires before ANY tool call; we only act when the
    tool about to run is our gated publish_digest tool. Blocking here
    (permissionDecision='deny') stops the SDK's own tool execution --
    this is enforced by the harness, not by agent good behavior."""
    tool_name = input_data.get("tool_name", "")
    if not tool_name.endswith("publish_digest"):
        return {}

    markdown = input_data.get("tool_input", {}).get("markdown", "")
    print("\n----- DIGEST PREVIEW -----\n")
    print(markdown)
    answer = input("\nApprove for publishing? [y/N] ").strip().lower()
    if answer == "y":
        return {}  # allow the tool call to proceed
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Human rejected the digest.",
        }
    }


# ---- subagent definitions -------------------------------------------------

physics_subagent = AgentDefinition(
    description="Researches recent physics arXiv lecture notes.",
    prompt=(
        f"Use mcp__arxiv-digest-tools__search_physics starting with days=14. "
        f"If you get fewer than {MIN_HITS} hits, call it again doubling "
        f"`days` (cap {MAX_DAYS}), up to 2 retries. Report the final title "
        "list, arxiv IDs, topic tags, days window used, and retry count."
    ),
    tools=["mcp__arxiv-digest-tools__search_physics"],
    model="sonnet",
)

math_subagent = AgentDefinition(
    description="Researches recent math arXiv lecture notes.",
    prompt=(
        f"Use mcp__arxiv-digest-tools__search_math starting with days=14. "
        f"If you get fewer than {MIN_HITS} hits, call it again doubling "
        f"`days` (cap {MAX_DAYS}), up to 2 retries. Report the final title "
        "list, arxiv IDs, days window used, and retry count."
    ),
    tools=["mcp__arxiv-digest-tools__search_math"],
    model="sonnet",
)


ORCHESTRATOR_PROMPT = """\
You are building today's arXiv lecture-notes digest.

1. Delegate to the `physics-researcher` subagent and the `math-researcher`
   subagent (via the Task tool) to gather results. Run both.
2. Combine their reported titles into one JSON list and call
   mcp__arxiv-digest-tools__dedupe_and_record on it to drop anything
   already published in a previous run.
3. Write a Markdown digest with '## Physics' and '## Math' sections,
   listing only the deduped, fresh titles (physics entries should note
   their topic tags).
4. Call mcp__arxiv-digest-tools__publish_digest with that markdown.
   This call is gated by a human-approval hook -- if it is denied,
   tell the user the digest was not published and stop.
"""


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"arxiv-digest-tools": arxiv_server},
        allowed_tools=[
            "Task",
            "mcp__arxiv-digest-tools__search_physics",
            "mcp__arxiv-digest-tools__search_math",
            "mcp__arxiv-digest-tools__dedupe_and_record",
            "mcp__arxiv-digest-tools__publish_digest",
        ],
        agents={
            "physics-researcher": physics_subagent,
            "math-researcher": math_subagent,
        },
        hooks={
            "PreToolUse": [HookMatcher(matcher=None, hooks=[require_approval_hook])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(ORCHESTRATOR_PROMPT)
        async for message in client.receive_response():
            print(message)


if __name__ == "__main__":
    asyncio.run(main())

```
