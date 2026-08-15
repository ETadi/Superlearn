---
description: Learn anything — research the web, build a learning board, and launch the Superlearn app
---

The user wants to learn about: **$ARGUMENTS**

Load the `superlearn` skill and follow its pipeline end to end. In the
Superlearn repo it lives at `.agents/skills/superlearn/SKILL.md`; installed
globally it is in your skills directory (`~/.kilo/skills/superlearn/`). If you
cannot find it, ask the user to run `python3 scripts/install.py --kilocode`
from their Superlearn clone.

In short: detect the mode (`study` is the default; switch to `interview`,
`research`, or `documentation` when the arguments say so), set up
`.superlearn/` in the current directory, then research first and think second
— files the user dropped in `.superlearn/sources/` are read before anything
else, then `websearch`/`webfetch` from several angles plus the bundled
YouTube/arXiv scrapers (the only legitimate source of videoIds). Write the
curriculum plan, research every subtopic until saturated — fan out with the
`superlearn-researcher` subagent via the `task` tool when there are many —
then deliberately design and author the board JSON, validate it with
`scripts/validate_board.py` until clean, export the standalone HTML with
`scripts/export_html.py`, and serve with `scripts/serve.py --boards-dir
.superlearn/boards --port 4321` in the background. Tell the user to open
http://localhost:4321, then stay in the loop: the page hot-reloads whenever
the board JSON changes on disk, so follow-ups ("go deeper on X", "add the
papers", "change the look") are surgical edits + re-validate + re-export.

If **$ARGUMENTS** is empty, ask the user what they'd like to learn. If a
server is already running on the port, reuse it — new boards appear
automatically.
