Use your Python kernel to fetch `https://export.arxiv.org/api/query`
with `search_query=cat:math.*`, sorted by submittedDate descending.
Parse the Atom feed. Keep entries published within the last 14 days
whose title or summary contains lecture-notes phrasing ("lecture
notes", "lectures on", "course notes", "introductory lectures"), any
math subject.

If you end up with fewer than 3 matching articles, double the day
window (cap 60) and retry, up to 2 retries total.

Report back as JSON: `{ "titles": [...], "arxiv_ids_by_title": {...},
"days_used": <int>, "retries": <int> }`.
