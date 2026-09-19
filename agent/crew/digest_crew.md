```python
"""
CrewAI implementation of the arXiv lecture-notes digest agent.

What this is meant to demonstrate about CrewAI specifically:
  - The ROLE-BASED mental model: three named agents (Physics Researcher,
    Math Researcher, Editor) each with a role/goal/backstory, rather
    than a graph of functions.
  - TASKS assigned to agents, with `context=[...]` wiring one task's
    output into another's input -- CrewAI's version of data flow.
  - A `Crew` that orchestrates execution order (here: two research
    tasks run, an editor task consumes both). CrewAI's retry-on-
    condition is expressed as the Editor agent's own tool-calling
    loop (via a `widen_search` tool) rather than a graph edge --
    this is the "delegate a fuzzy sub-goal to an agent" style, in
    contrast to LangGraph's explicit conditional edges.
  - Human-in-the-loop via Task(human_input=True) -- CrewAI pauses for
    literal console input on that task, a simpler mechanism than
    LangGraph's resumable interrupt/Command.

Run:
    pip install crewai
    export OPENAI_API_KEY=...   # or configure another LLM via crewai's llm= param
    python digest_crew.py
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from shared.arxiv_client import (
    search_physics_lecture_notes,
    search_math_lecture_notes,
)
from shared.state_store import load_seen, save_seen, dedupe_against_seen

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

MIN_HITS = 3
MAX_DAYS = 60


# ---- tools each agent can call --------------------------------------------

@tool("search_physics_lecture_notes")
def search_physics_tool(days: int = 14) -> str:
    """Search arXiv physics categories (quant-ph, hep-th, cond-mat) for
    lecture-notes-style papers on quantum mechanics, QFT, or solid state
    physics published in the last `days` days. Returns a JSON list of
    {title, arxiv_id, topic_tags}. If fewer than 3 results come back,
    call this again with a larger `days` value (double it, cap at 60)."""
    import json
    results = search_physics_lecture_notes(days=days)
    return json.dumps([
        {"title": a.title, "arxiv_id": a.arxiv_id, "topic_tags": a.topic_tags}
        for a in results
    ])


@tool("search_math_lecture_notes")
def search_math_tool(days: int = 14) -> str:
    """Search arXiv math.* categories for lecture-notes-style papers
    published in the last `days` days. Returns a JSON list of
    {title, arxiv_id}. If fewer than 3 results come back, call this
    again with a larger `days` value (double it, cap at 60)."""
    import json
    results = search_math_lecture_notes(days=days)
    return json.dumps([
        {"title": a.title, "arxiv_id": a.arxiv_id} for a in results
    ])


@tool("dedupe_against_history")
def dedupe_tool(titles_json: str) -> str:
    """Given a JSON list of article titles, remove any that were
    already reported in a previous run and return the JSON list of
    genuinely new titles. Also records the new titles as seen."""
    import json
    titles = json.loads(titles_json)
    seen = load_seen()
    fresh = [t for t in titles if t not in seen]
    save_seen(seen | set(fresh))
    return json.dumps(fresh)


# ---- agents ----------------------------------------------------------

physics_researcher = Agent(
    role="Physics Lecture Notes Researcher",
    goal=(
        f"Find at least {MIN_HITS} recent arXiv lecture-notes-style papers on "
        "quantum mechanics, QFT, or solid state physics. Start with a 14-day "
        "window; if you get fewer than the minimum, retry with a wider "
        "window (double it, up to 60 days) before giving up."
    ),
    backstory=(
        "A physics postdoc who maintains a reading-group digest of new "
        "pedagogical material and knows exactly which arXiv categories "
        "carry lecture notes."
    ),
    tools=[search_physics_tool],
    verbose=True,
)

math_researcher = Agent(
    role="Math Lecture Notes Researcher",
    goal=(
        f"Find at least {MIN_HITS} recent arXiv lecture-notes-style papers "
        "in any math.* category. Start with a 14-day window; if you get "
        "fewer than the minimum, retry with a wider window (double it, up "
        "to 60 days) before giving up."
    ),
    backstory="A math librarian who tracks new expository/course material on arXiv.",
    tools=[search_math_tool],
    verbose=True,
)

editor = Agent(
    role="Digest Editor",
    goal=(
        "Combine the physics and math findings into one clean Markdown "
        "digest, remove anything already reported in a previous run, and "
        "ask a human to approve it before publishing."
    ),
    backstory="A careful editor who never ships a digest without a human sign-off.",
    tools=[dedupe_tool],
    verbose=True,
)


# ---- tasks -------------------------------------------------------------

physics_task = Task(
    description=(
        "Search for recent physics lecture notes as described in your goal. "
        "Report the final list of titles with their arXiv IDs and topic tags "
        "(quantum mechanics / QFT / solid state physics), and note how many "
        "widen-retries you needed."
    ),
    expected_output="A bulleted list of physics lecture-note titles with IDs and tags.",
    agent=physics_researcher,
)

math_task = Task(
    description=(
        "Search for recent math lecture notes as described in your goal. "
        "Report the final list of titles with their arXiv IDs, and note how "
        "many widen-retries you needed."
    ),
    expected_output="A bulleted list of math lecture-note titles with IDs.",
    agent=math_researcher,
)

editor_task = Task(
    description=(
        "Take the physics and math results from the two researchers, "
        "dedupe titles against history using your tool, and produce one "
        "Markdown digest with '## Physics' and '## Math' sections. "
        "Then present it to the human for approval."
    ),
    expected_output="Final approved (or rejected) Markdown digest.",
    agent=editor,
    context=[physics_task, math_task],  # CrewAI wires prior task outputs in here
    human_input=True,  # CrewAI pauses for literal console approval on this task
)


def build_crew() -> Crew:
    return Crew(
        agents=[physics_researcher, math_researcher, editor],
        tasks=[physics_task, math_task, editor_task],
        process=Process.sequential,  # editor_task naturally waits on both via `context`
        verbose=True,
    )


if __name__ == "__main__":
    crew = build_crew()
    result = crew.kickoff()
    out_path = pathlib.Path(__file__).parent / "digest.md"
    out_path.write_text(str(result))
    print(f"\nDigest written to {out_path}")
```
