```python
"""
Tiny JSON-backed "seen titles" store, shared by every implementation.

This exists so the dedup/persistence requirement isn't reinvented five
times -- what differs between frameworks is WHO calls this and WHEN
(a LangGraph node with a checkpointer, a CrewAI tool, a Claude Agent SDK
file-backed tool, etc.), not the storage mechanism itself.
"""
from __future__ import annotations

import json
import pathlib
from typing import Iterable

DEFAULT_PATH = pathlib.Path(__file__).parent / "seen_titles.json"


def load_seen(path: pathlib.Path = DEFAULT_PATH) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))


def save_seen(seen: Iterable[str], path: pathlib.Path = DEFAULT_PATH) -> None:
    path.write_text(json.dumps(sorted(set(seen)), indent=2))


def dedupe_against_seen(articles, seen: set[str]):
    """articles: list of objects with a `.title` attribute or dicts with 'title'."""
    fresh = []
    for a in articles:
        title = a.title if hasattr(a, "title") else a["title"]
        if title not in seen:
            fresh.append(a)
    return fresh

```
