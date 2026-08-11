---
description: Learn anything — research the web, build a learning board, and launch the Superlearn app
argument-hint: <what you want to learn, e.g. "transformer neural networks">
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Task
---

The user wants to learn about: **$ARGUMENTS**

Follow the Superlearn pipeline defined in the `superlearn` skill (skills/superlearn/SKILL.md in this plugin). In short:

0. **Detect the mode**: default `study`; switch to `interview`, `research`, or `documentation` when the arguments say so ("for my interview", "survey the literature", "as a reference", `--mode docs`, …). The mode shapes what you research and how the page presents it — see the Modes table in the skill.
1. **Set up the workspace** at `.superlearn/` in the current directory (create `research/<slug>/raw/`, `research/<slug>/notes/`, `boards/`, and `exports/` — each topic gets its own research trail). The research trail is a deliverable the user can browse — in the app (Research button) and on disk.
2. **Scrape first, think second.** If `.superlearn/sources/` contains user files (PDFs, docs), read those FIRST — they're first-class research input. Then run the plugin's Python scrapers into `research/<slug>/raw/`:
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_web.py" "<query>" --read 3 --out <file>`
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_youtube.py" "<query>" --out <file>`
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_arxiv.py" "<query>" --out <file>` (paper-driven topics / research mode)
3. **Plan the curriculum**: write `research/<slug>/plan.md` with a subtopic checklist sized to the topic.
4. **Iterate until saturated**: for every unchecked subtopic, scrape + use your own WebSearch/WebFetch research, write synthesized notes to `research/<slug>/notes/`, tick the checklist. Repeat until every subtopic has notes. Parallelize with the `superlearn-researcher` agent when there are many subtopics.
5. **Design, then author the board**: deliberately choose the `layout` and `theme` that fit this topic (see the design table in the skill — never default out of habit), then write `boards/<slug>.json` following the exact block schema — summary, roadmap, concepts, diagrams (Mermaid), charts (real numbers only), figures, code, notes, glossary, videos (only scraped videoIds), resources (papers/docs/long-form — only real URLs). Write real TeX (`$$…$$`, `\(…\)`) wherever the field uses it. No quizzes: this is a depth-first tool.
6. **Validate & export**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_board.py" boards/<slug>.json`, fix every reported issue, then bake the standalone file: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export_html.py" .superlearn/boards/<slug>.json` → `.superlearn/exports/<slug>.html`.
7. **Launch**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --boards-dir .superlearn/boards --port 4321` in the background, then tell the user to open http://localhost:4321 and give them a one-paragraph tour — including where everything is saved (board JSON, standalone HTML, research trail) and the in-app Research button.
8. **Stay in the loop**: the page hot-reloads whenever you edit the board JSON. When the user asks follow-ups ("go deeper on X", "add the papers", "change the look"), research if needed, edit the board surgically, re-validate, re-export the HTML — their page updates itself within seconds.

If `$ARGUMENTS` is empty, ask the user what they'd like to learn. If a server is already running on the port, reuse it — new boards appear automatically.
