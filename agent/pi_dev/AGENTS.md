# arXiv Lecture Notes Digest — Pi agent instructions

You are running inside Pi, a minimal terminal coding-agent harness whose
built-in tools are exactly: read, write, edit, bash. There is no
multi-agent primitive and no graph in Pi's core -- extensibility comes
from TypeScript extensions (see `arxiv_tools.ts` in this directory) and
from you, the model, sequencing the work yourself inside one session.
This is the point of comparison: everywhere another framework in this
project uses a graph node, a crew role, a handoff, or a subagent, Pi
instead gives you a slightly bigger toolbox and trusts the model's own
planning to sequence the steps.

## Task

Produce `digest.md` in this directory: an arXiv lecture-notes digest
with two sections.

1. **Physics.** Call the `arxiv_search` tool with
   `category="physics", days=14`. It returns JSON:
   `{ articles: [{title, arxivId, topicTags}], count }`.
   Only titles whose `topicTags` include at least one of
   `"quantum mechanics"`, `"QFT"`, `"solid state physics"` count.
   If `count < 3`, call it again with `days` doubled (cap at 60),
   up to 2 retries total, before moving on with whatever you have.

2. **Math.** Same tool with `category="math", days=14"`. If
   `count < 3`, retry with doubled `days` (cap 60), up to 2 retries.

3. **Dedupe.** Read `../shared/seen_titles.json` (a JSON array of
   strings) with the `read` tool if it exists; treat a missing file as
   an empty list. Drop any title already in that list from both
   sections. Then `write` the updated union of old + newly reported
   titles back to that file -- this is Pi's version of "persistent
   state": a file, because that's what the harness gives you.

4. **Compose.** `write` `digest.md` with:
   ```
   # arXiv Lecture Notes Digest

   ## Physics (window: <days> days, <retries> retries)
   - **<title>** _(tags: <tags>)_ — <arxivId>
   ...

   ## Math (window: <days> days, <retries> retries)
   - **<title>** — <arxivId>
   ...
   ```

5. **Human approval.** Print the digest to the terminal and ask the
   user to type `y` to approve. Pi has no built-in approval primitive
   (no interrupt(), no human_input=True) -- this is a plain question
   in the conversation, gated only by your own instructions, which is
   the honest tradeoff of a minimal harness: you get simplicity, you
   lose an enforced pause. If approved, leave `digest.md` in place and
   say "APPROVED — written to digest.md". If not approved, delete
   `digest.md` with `bash` (`rm digest.md`) and say "NOT APPROVED —
   digest discarded".

Do not fabricate arXiv results if the tool call fails -- report the
failure and stop.
