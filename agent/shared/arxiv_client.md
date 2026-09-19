```python
"""
Shared arXiv client used by every framework implementation in this project.

Keeping this identical across implementations is the point: the interesting
differences between LangGraph / CrewAI / OpenAI Agents SDK / Claude Agent SDK /
pi.dev / omp.sh are in ORCHESTRATION (delegation, branching, state, tool
execution, human approval) -- not in how you happen to call the arXiv API.
Every framework wraps these same two functions as its "tool".

arXiv's public Atom API: https://export.arxiv.org/api/query
No API key required.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Sequence

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "https://export.arxiv.org/api/query"

# arXiv category codes we care about for this task.
CATEGORY_GROUPS = {
    "physics": [
        "quant-ph",   # quantum physics
        "hep-th",     # high energy physics - theory (QFT lives here)
        "cond-mat.str-el",  # strongly correlated electrons (solid state)
        "cond-mat.mes-hall",  # mesoscale / solid state
    ],
    "math": ["math.*"],  # math.* umbrella; arXiv's own "math" listing
}

# Keyword sets per physics sub-topic. A title/abstract must hit "lecture
# notes"-style phrasing AND one of these to count for that sub-topic.
PHYSICS_TOPIC_KEYWORDS = {
    "quantum mechanics": ["quantum mechanic", "quantum theory", "qm "],
    "QFT": ["quantum field theor", "qft", "field theory"],
    "solid state physics": ["solid state", "condensed matter", "many-body", "strongly correlated"],
}
LECTURE_NOTE_KEYWORDS = ["lecture note", "lecture notes", "lectures on", "course note", "introductory lectures"]

MATH_LECTURE_KEYWORDS = LECTURE_NOTE_KEYWORDS  # math side: just "lecture notes", any subject


@dataclass
class Article:
    arxiv_id: str
    title: str
    published: str  # ISO date
    categories: list[str]
    summary: str
    topic_tags: list[str]  # which sub-topics matched (physics only; empty for math)

    def to_dict(self) -> dict:
        return asdict(self)


def _fetch_atom(search_query: str, max_results: int = 100) -> ET.Element:
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = resp.read()
    return ET.fromstring(data)


def _entries_from_feed(feed: ET.Element) -> list[dict]:
    out = []
    for entry in feed.findall(f"{ATOM_NS}entry"):
        arxiv_id = entry.findtext(f"{ATOM_NS}id", default="").rsplit("/", 1)[-1]
        title = " ".join(entry.findtext(f"{ATOM_NS}title", default="").split())
        summary = " ".join(entry.findtext(f"{ATOM_NS}summary", default="").split())
        published = entry.findtext(f"{ATOM_NS}published", default="")
        categories = [
            c.attrib.get("term", "")
            for c in entry.findall(f"{ATOM_NS}category")
        ]
        out.append(
            dict(
                arxiv_id=arxiv_id,
                title=title,
                summary=summary,
                published=published,
                categories=categories,
            )
        )
    return out


def _within_window(published_iso: str, days: int, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        published = dt.datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (now - published) <= dt.timedelta(days=days)


def _matches_any(text: str, keywords: Sequence[str]) -> bool:
    text = text.lower()
    return any(k.lower() in text for k in keywords)


def search_physics_lecture_notes(days: int = 14, max_results: int = 100) -> list[Article]:
    """Search physics categories for lecture-notes-style papers on
    quantum mechanics, QFT, or solid state physics, published in the
    last `days` days."""
    cats = CATEGORY_GROUPS["physics"]
    query = " OR ".join(f"cat:{c}" for c in cats)
    feed = _fetch_atom(query, max_results=max_results)
    entries = _entries_from_feed(feed)

    results: list[Article] = []
    for e in entries:
        if not _within_window(e["published"], days):
            continue
        blob = f"{e['title']} {e['summary']}"
        if not _matches_any(blob, LECTURE_NOTE_KEYWORDS):
            continue
        tags = [
            topic
            for topic, kws in PHYSICS_TOPIC_KEYWORDS.items()
            if _matches_any(blob, kws)
        ]
        if not tags:
            continue
        results.append(
            Article(
                arxiv_id=e["arxiv_id"],
                title=e["title"],
                published=e["published"],
                categories=e["categories"],
                summary=e["summary"][:280],
                topic_tags=tags,
            )
        )
    return results


def search_math_lecture_notes(days: int = 14, max_results: int = 100) -> list[Article]:
    """Search math categories for lecture-notes-style papers published
    in the last `days` days (any math subject)."""
    query = "cat:math.*"
    feed = _fetch_atom(query, max_results=max_results)
    entries = _entries_from_feed(feed)

    results: list[Article] = []
    for e in entries:
        if not _within_window(e["published"], days):
            continue
        blob = f"{e['title']} {e['summary']}"
        if not _matches_any(blob, MATH_LECTURE_KEYWORDS):
            continue
        results.append(
            Article(
                arxiv_id=e["arxiv_id"],
                title=e["title"],
                published=e["published"],
                categories=e["categories"],
                summary=e["summary"][:280],
                topic_tags=[],
            )
        )
    return results


def widen_and_retry(search_fn, days: int, min_hits: int, max_days: int = 60, retries: int = 2):
    """Shared retry/widen helper: several frameworks below re-implement
    this as an explicit graph edge (LangGraph), a crew task-retry
    (CrewAI), or a plain loop (others) -- included here once so the
    logic itself isn't what's being compared."""
    attempt = 0
    current_days = days
    results = search_fn(days=current_days)
    while len(results) < min_hits and attempt < retries and current_days < max_days:
        attempt += 1
        current_days = min(current_days * 2, max_days)
        results = search_fn(days=current_days)
    return results, current_days, attempt


if __name__ == "__main__":
    import json

    phys, days_used, attempts = widen_and_retry(search_physics_lecture_notes, days=14, min_hits=3)
    math, mdays_used, mattempts = widen_and_retry(search_math_lecture_notes, days=14, min_hits=3)
    print(json.dumps({
        "physics": {"days_used": days_used, "retries": attempts, "count": len(phys),
                     "titles": [a.title for a in phys]},
        "math": {"days_used": mdays_used, "retries": mattempts, "count": len(math),
                  "titles": [a.title for a in math]},
    }, indent=2))
```
