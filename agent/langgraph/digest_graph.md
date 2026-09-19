```python
"""
LangGraph implementation of the arXiv lecture-notes digest agent.

What this is meant to demonstrate about LangGraph specifically:
  - An explicit STATE GRAPH: nodes and conditional edges you can draw.
  - Parallel fan-out (physics + math search nodes run off the same
    entry point) then fan-in at a merge node.
  - A CONDITIONAL EDGE that decides "retry with a wider window" vs.
    "move on" based on the shared state -- not a bare while-loop
    buried in a function.
  - A CHECKPOINTER (MemorySaver here; swap for SqliteSaver/Postgres in
    prod) so "seen titles" persists across runs of the same thread,
    and an `interrupt()` for the human-approval step, which LangGraph
    treats as a first-class graph pause/resume, not an ad hoc `input()`.

Run:
    pip install langgraph
    python digest_graph.py
"""
from __future__ import annotations

import sys
import pathlib
from typing import TypedDict, Annotated
import operator

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from shared.arxiv_client import (
    search_physics_lecture_notes,
    search_math_lecture_notes,
    Article,
)
from shared.state_store import load_seen, save_seen, dedupe_against_seen

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

MIN_HITS = 3
MAX_DAYS = 60
MAX_RETRIES = 2


class DigestState(TypedDict):
    days: int
    physics_days: int
    math_days: int
    physics_attempts: int
    math_attempts: int
    physics_results: list[dict]
    math_results: list[dict]
    digest_markdown: str
    approved: bool


# ---- nodes -----------------------------------------------------------

def search_physics(state: DigestState) -> dict:
    days = state.get("physics_days", state["days"])
    results = search_physics_lecture_notes(days=days)
    return {"physics_results": [a.to_dict() for a in results], "physics_days": days}


def search_math(state: DigestState) -> dict:
    days = state.get("math_days", state["days"])
    results = search_math_lecture_notes(days=days)
    return {"math_results": [a.to_dict() for a in results], "math_days": days}


def widen_physics(state: DigestState) -> dict:
    new_days = min(state["physics_days"] * 2, MAX_DAYS)
    return {
        "physics_days": new_days,
        "physics_attempts": state.get("physics_attempts", 0) + 1,
    }


def widen_math(state: DigestState) -> dict:
    new_days = min(state["math_days"] * 2, MAX_DAYS)
    return {
        "math_days": new_days,
        "math_attempts": state.get("math_attempts", 0) + 1,
    }


def merge_and_dedupe(state: DigestState) -> dict:
    seen = load_seen()
    physics_fresh = dedupe_against_seen(
        [Article(**a) for a in state["physics_results"]], seen
    )
    math_fresh = dedupe_against_seen(
        [Article(**a) for a in state["math_results"]], seen
    )

    lines = ["# arXiv Lecture Notes Digest\n"]
    lines.append(f"## Physics (window: {state['physics_days']} days, "
                 f"{state.get('physics_attempts', 0)} widen-retries)\n")
    if physics_fresh:
        for a in physics_fresh:
            lines.append(f"- **{a.title}** _(tags: {', '.join(a.topic_tags)})_ — {a.arxiv_id}")
    else:
        lines.append("- (no new qualifying articles)")

    lines.append(f"\n## Math (window: {state['math_days']} days, "
                 f"{state.get('math_attempts', 0)} widen-retries)\n")
    if math_fresh:
        for a in math_fresh:
            lines.append(f"- **{a.title}** — {a.arxiv_id}")
    else:
        lines.append("- (no new qualifying articles)")

    new_seen = seen | {a.title for a in physics_fresh} | {a.title for a in math_fresh}
    save_seen(new_seen)

    return {"digest_markdown": "\n".join(lines)}


def human_approval(state: DigestState) -> dict:
    """LangGraph's `interrupt()` pauses the graph and surfaces a value
    to whatever is driving it (CLI, web app, etc.); resuming requires
    a Command(resume=...). This is the graph-native human-in-the-loop
    primitive -- the graph run genuinely suspends, not just "prompt in
    a function"."""
    decision = interrupt(
        {
            "question": "Approve this digest for publishing?",
            "digest_preview": state["digest_markdown"],
        }
    )
    return {"approved": bool(decision)}


def publish(state: DigestState) -> dict:
    out_path = pathlib.Path(__file__).parent / "digest.md"
    if state["approved"]:
        out_path.write_text(state["digest_markdown"])
        print(f"APPROVED -- digest written to {out_path}")
    else:
        print("NOT APPROVED -- digest discarded")
    return {}


# ---- conditional edges -------------------------------------------------

def physics_needs_retry(state: DigestState) -> str:
    attempts = state.get("physics_attempts", 0)
    if len(state["physics_results"]) < MIN_HITS and attempts < MAX_RETRIES \
            and state["physics_days"] < MAX_DAYS:
        return "widen_physics"
    return "join"


def math_needs_retry(state: DigestState) -> str:
    attempts = state.get("math_attempts", 0)
    if len(state["math_results"]) < MIN_HITS and attempts < MAX_RETRIES \
            and state["math_days"] < MAX_DAYS:
        return "widen_math"
    return "join"


# ---- graph assembly ------------------------------------------------------

def build_graph():
    g = StateGraph(DigestState)

    g.add_node("search_physics", search_physics)
    g.add_node("search_math", search_math)
    g.add_node("widen_physics", widen_physics)
    g.add_node("widen_math", widen_math)
    g.add_node("merge_and_dedupe", merge_and_dedupe)
    g.add_node("human_approval", human_approval)
    g.add_node("publish", publish)

    # Fan-out: both searches start from the graph entry point.
    g.set_entry_point("search_physics")
    g.add_edge("__start__", "search_math")  # parallel branch

    # Each branch conditionally loops back to widen its own window.
    g.add_conditional_edges(
        "search_physics", physics_needs_retry,
        {"widen_physics": "widen_physics", "join": "merge_and_dedupe"},
    )
    g.add_edge("widen_physics", "search_physics")

    g.add_conditional_edges(
        "search_math", math_needs_retry,
        {"widen_math": "widen_math", "join": "merge_and_dedupe"},
    )
    g.add_edge("widen_math", "search_math")

    # merge_and_dedupe is a fan-in point LangGraph waits on until both
    # branches have reached it (superstep semantics).
    g.add_edge("merge_and_dedupe", "human_approval")
    g.add_edge("human_approval", "publish")
    g.add_edge("publish", END)

    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    graph = build_graph()
    config = {"configurable": {"thread_id": "arxiv-digest-daily"}}

    initial_state: DigestState = {
        "days": 14,
        "physics_days": 14,
        "math_days": 14,
        "physics_attempts": 0,
        "math_attempts": 0,
        "physics_results": [],
        "math_results": [],
        "digest_markdown": "",
        "approved": False,
    }

    result = graph.invoke(initial_state, config=config)

    # graph paused at interrupt(); result contains the interrupt payload
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(payload["digest_preview"])
        answer = input("\nApprove? [y/N] ").strip().lower() == "y"
        final = graph.invoke(Command(resume=answer), config=config)
        print(final)
```
