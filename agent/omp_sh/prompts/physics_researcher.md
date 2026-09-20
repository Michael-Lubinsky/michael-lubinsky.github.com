Use your Python kernel to fetch `https://export.arxiv.org/api/query`
with `search_query=cat:quant-ph+OR+cat:hep-th+OR+cat:cond-mat.str-el+OR+cat:cond-mat.mes-hall`,
sorted by submittedDate descending. Parse the Atom feed. Keep entries
published within the last 14 days whose title or summary contains
lecture-notes phrasing ("lecture notes", "lectures on", "course notes",
"introductory lectures") AND matches at least one of: quantum mechanics
(quantum mechanic/quantum theory), QFT (quantum field theor/qft/field
theory), solid state physics (solid state/condensed matter/many-body/
strongly correlated).

If you end up with fewer than 3 matching articles, double the day
window (cap 60) and retry, up to 2 retries total.

Report back as JSON: `{ "titles": [...], "topic_tags_by_title": {...},
"arxiv_ids_by_title": {...}, "days_used": <int>, "retries": <int> }`.
