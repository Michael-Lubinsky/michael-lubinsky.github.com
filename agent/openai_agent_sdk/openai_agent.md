```python
"""
OpenAI Agents SDK implementation of the arXiv lecture-notes digest agent.

What this is meant to demonstrate about the OpenAI Agents SDK specifically:
  - Small, focused Agents wired together with explicit, TYPED HANDOFFS
    (a Triage agent hands off to Physics/Math specialist agents) rather
    than a graph or a role-playing crew.
  - A GUARDRAIL (`output_guardrail`) that validates a specialist's
    output against a Pydantic schema and can trip a "too few results,
    widen the window" retry -- guardrails are this SDK's built-in
    validation/control primitive.
  - `function_tool`-wrapped Python functions as tools (thin wrappers
    around the same shared arxiv_client used everywhere else).
  - A human-approval step modeled as a tool call the Digest agent must
    make and that raises for input() in this demo -- in production
    you'd swap this for the SDK's `needs_approval` flow on a sensitive
    tool call.

Run:
    pip install openai-agents
    export OPENAI_API_KEY=...
    python digest_agents.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from shared.arxiv_client import search_physics_lecture_notes, search_math_lecture_notes
from shared.state_store import load_seen, save_seen, dedupe_against_seen

from pydantic import BaseModel
from agents import (
    Agent,
    Runner,
    function_tool,
    output_guardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
)

MIN_HITS = 3
MAX_DAYS = 60


# ---- tools -------------------------------------------------------------

@function_tool
def search_physics(days: int) -> str:
    """Search arXiv physics categories for lecture-notes-style papers on
    quantum mechanics, QFT, or solid state physics published in the last
    `days` days. Returns a JSON list of {title, arxiv_id, topic_tags}."""
    results = search_physics_lecture_notes(days=days)
    return json.dumps([
        {"title": a.title, "arxiv_id": a.arxiv_id, "topic_tags": a.topic_tags}
        for a in results
    ])


@function_tool
def search_math(days: int) -> str:
    """Search arXiv math.* categories for lecture-notes-style papers
    published in the last `days` days. Returns a JSON list of
    {title, arxiv_id}."""
    results = search_math_lecture_notes(days=days)
    return json.dumps([{"title": a.title, "arxiv_id": a.arxiv_id} for a in results])


@function_tool
def dedupe_and_record(titles: list[str]) -> list[str]:
    """Remove titles already reported in a previous run; record the
    rest as seen. Returns the list of genuinely new titles."""
    seen = load_seen()
    fresh = [t for t in titles if t not in seen]
    save_seen(seen | set(fresh))
    return fresh


@function_tool
def request_human_approval(digest_markdown: str) -> str:
    """Show the human the digest and block for a yes/no approval.
    Returns 'approved' or 'rejected'."""
    print("\n----- DIGEST PREVIEW -----\n")
    print(digest_markdown)
    answer = input("\nApprove for publishing? [y/N] ").strip().lower()
    return "approved" if answer == "y" else "rejected"


@function_tool
def publish_digest(digest_markdown: str) -> str:
    """Write the approved digest to disk."""
    out_path = pathlib.Path(__file__).parent / "digest.md"
    out_path.write_text(digest_markdown)
    return f"written to {out_path}"


# ---- guardrail: enforce the "min 3 hits, else caller must widen" rule ----

class SearchResultCheck(BaseModel):
    reasoning: str
    hit_count: int
    days_used: int
    needs_wider_window: bool


@output_guardrail
async def min_hits_guardrail(
    ctx: RunContextWrapper, agent: Agent, output
) -> GuardrailFunctionOutput:
    """Runs against a specialist agent's final output. If the agent
    reports fewer than MIN_HITS and hasn't already maxed out the
    window, this trips -- in the SDK's model, a tripped output
    guardrail halts the run so the orchestrator (or a retry wrapper)
    can react, which is a very different control style from
    LangGraph's conditional edge or CrewAI's tool-driven self-retry."""
    check = SearchResultCheck(
        reasoning=f"Specialist reported: {output}",
        hit_count=getattr(output, "hit_count", 0),
        days_used=getattr(output, "days_used", 14),
        needs_wider_window=(
            getattr(output, "hit_count", 0) < MIN_HITS
            and getattr(output, "days_used", 14) < MAX_DAYS
        ),
    )
    return GuardrailFunctionOutput(
        output_info=check,
        tripwire_triggered=check.needs_wider_window,
    )


class SpecialistReport(BaseModel):
    titles: list[str]
    days_used: int
    hit_count: int


# ---- agents --------------------------------------------------------------

physics_agent = Agent(
    name="Physics Researcher",
    instructions=(
        f"Use the search_physics tool starting with days=14. If hit_count "
        f"is below {MIN_HITS}, call it again doubling `days` (cap {MAX_DAYS}), "
        "up to 2 retries. Return a SpecialistReport with the final titles, "
        "the days window you ended on, and the hit count."
    ),
    tools=[search_physics],
    output_type=SpecialistReport,
    output_guardrails=[min_hits_guardrail],
)

math_agent = Agent(
    name="Math Researcher",
    instructions=(
        f"Use the search_math tool starting with days=14. If hit_count is "
        f"below {MIN_HITS}, call it again doubling `days` (cap {MAX_DAYS}), "
        "up to 2 retries. Return a SpecialistReport with the final titles, "
        "the days window you ended on, and the hit count."
    ),
    tools=[search_math],
    output_type=SpecialistReport,
    output_guardrails=[min_hits_guardrail],
)

# The Triage agent is the SDK's characteristic piece: it doesn't do the
# research itself, it *hands off* to whichever specialist(s) apply, and
# also owns the final assembly + approval + publish steps.
triage_agent = Agent(
    name="Digest Orchestrator",
    instructions=(
        "You produce a two-section arXiv lecture-notes digest. "
        "1) Hand off to the Physics Researcher and Math Researcher "
        "(both -- this task always needs both sections). "
        "2) Once you have both SpecialistReports, call dedupe_and_record "
        "on the combined title list. "
        "3) Compose Markdown with '## Physics' and '## Math' sections "
        "listing only the deduped, fresh titles. "
        "4) Call request_human_approval with that markdown. "
        "5) If approved, call publish_digest; otherwise say so and stop."
    ),
    handoffs=[physics_agent, math_agent],
    tools=[dedupe_and_record, request_human_approval, publish_digest],
)


async def main():
    result = await Runner.run(
        triage_agent,
        "Build today's arXiv lecture-notes digest for physics and math.",
    )
    print("\nFINAL OUTPUT:\n", result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
```
