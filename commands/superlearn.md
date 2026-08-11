---
description: Learn anything — research the web, build a learning board, and launch the Superlearn app
argument-hint: <what you want to learn, e.g. "transformer neural networks">
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Task
---

The user wants to learn about: **$ARGUMENTS**

Follow the Superlearn pipeline defined in the `superlearn` skill (skills/superlearn/SKILL.md in this plugin). In short:

1. **Set up the workspace** at `.superlearn/` in the current directory (create `research/raw/`, `research/notes/`, and `boards/`).
2. **Scrape first, think second.** Run the plugin's Python scrapers to pull live web results, article text, and YouTube videos into `research/raw/`:
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_web.py" "<query>" --read 3 --out <file>`
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_youtube.py" "<query>" --out <file>`
3. **Plan the curriculum**: write `research/plan.md` with a subtopic checklist sized to the topic.
4. **Iterate until saturated**: for every unchecked subtopic, scrape + use your own WebSearch/WebFetch research, write synthesized notes to `research/notes/`, tick the checklist. Repeat until every subtopic has notes. Parallelize with the `superlearn-researcher` agent when there are many subtopics.
5. **Design, then author the board**: deliberately choose the `layout` and `theme` that fit this topic (see the design table in the skill — never default out of habit), then write `boards/<slug>.json` following the exact block schema — summary, roadmap, concepts, diagrams (Mermaid), code, notes, glossary, videos (only scraped videoIds), resources (papers/docs/long-form — only real URLs). No quizzes: this is a depth-first tool.
6. **Validate**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_board.py" boards/<slug>.json` and fix every reported issue.
7. **Launch**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --boards-dir .superlearn/boards --port 4321` in the background, then tell the user to open http://localhost:4321 and give them a one-paragraph tour of their board.
8. **Stay in the loop**: the page hot-reloads whenever you edit the board JSON. When the user asks follow-ups ("go deeper on X", "add the papers", "change the look"), research if needed, edit the board surgically, re-validate — their page updates itself within seconds.

If `$ARGUMENTS` is empty, ask the user what they'd like to learn. If a server is already running on the port, reuse it — new boards appear automatically.
