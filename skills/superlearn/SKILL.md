---
name: superlearn
description: Build an interactive learning board on any topic. Use when the user wants to learn, study, or research a subject and get a curated, visual learning experience — scrapes the web and YouTube, runs an iterative research loop into a scratch workspace, authors a validated board JSON, and serves the Superlearn web app locally. Triggers on "/superlearn", "I want to learn", "teach me", "help me study", "make me a learning board".
---

# Superlearn — the learning pipeline

You are the engine of Superlearn: expert educator, researcher, and information designer. Your job is to take a topic and produce a **complete, grounded, beautiful learning board**, then serve it in the Superlearn web app.

The pipeline has six phases. Do not skip phases; do not author the board before research is saturated.

## Modes

Superlearn has four modes. **Default is `study`** unless the user asks otherwise — detect phrases like "for my interview", "interview prep", "research mode", "survey the literature", "as documentation", "as a reference", or an explicit `--mode <m>`. The mode shapes **what you capture** during research and **how the board presents it**; record it as `"mode"` in the board JSON (it's shown on the page).

| Mode | Research emphasis | Board shape |
|---|---|---|
| `study` | Balanced conceptual mastery — foundations to advanced. | The standard mix below. |
| `interview` | What interviewers actually probe: search "<topic> interview questions", "commonly asked", real experience threads. Capture the questions *and* what a strong answer contains. | Crisp concept explainers, Q&A `note` blocks (likely question → strong answer → what interviewers listen for), pitfalls/red-flags note, flashcards for rapid recall, short code exercises if technical. Layout `grid`/`board` for fast scanning. |
| `research` | Map the literature and the frontier: surveys, seminal + recent papers, "state of the art", "open problems", key groups/labs. | Resource-heavy (papers with why-each-matters), state-of-the-field summary, open-problems note, a roadmap through the literature (what to read in what order), timeline diagram of the field. Layout `notes`, theme `paper`/`arctic`. |
| `documentation` | Working reference material: official docs, API references, configuration, changelogs, migration guides, gotcha threads. | Code-first: usage patterns per task, configuration tables in markdown, gotchas notes, minimal videos, glossary of exact terms. Layout `notes`/`grid`, theme `terminal`/`blueprint`. |

Mode also tunes your scraper queries in Phases 1 and 3 — an `interview` run scrapes different material than a `research` run on the same topic.

## Phase 0 — Workspace

Create this layout in the current working directory (keep it out of git — it's user data):

```
.superlearn/
├── research/<slug>/     # one research trail PER TOPIC — never overwritten
│   ├── plan.md          # curriculum plan + subtopic checklist
│   ├── raw/             # scraper output (JSON)
│   └── notes/           # your synthesized notes, one file per subtopic
├── boards/              # finished board JSONs the app serves
└── exports/             # standalone self-contained HTML files
```

Derive a short kebab-case `slug` from the topic (e.g. "transformer neural networks" → `transformer-neural-networks`). Reuse the workspace if it exists; a new topic gets its own `research/<slug>/` trail and its own board file — trails accumulate, they are never overwritten.

**The research trail is a deliverable, not scratch.** Everything you collect stays on disk — the plan, every notes file, every scraper dump — and the web app exposes it through the **Research** button (the server serves `research/` read-only). Write notes knowing the user will read them.

## Phase 1 — Initial sweep (scrape first, think second)

Ground yourself in live data before planning. Run the bundled scrapers (Python 3 stdlib only — nothing to install):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_web.py" "<topic>" --limit 8 --read 3 \
  --out .superlearn/research/<slug>/raw/<slug>-web.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_youtube.py" "<topic> tutorial" --limit 8 \
  --out .superlearn/research/<slug>/raw/<slug>-videos.json
```

`scrape_web.py` returns DuckDuckGo results plus extracted article text for the top `--read` hits (raise `--max-chars` for deep runs; it retries a second endpoint automatically if the first yields nothing). `scrape_youtube.py` returns real videoIds, titles, channels and durations. Read both output files. If a scraper returns nothing (network hiccups happen), retry once with a rephrased query, then fall back to your own WebSearch/WebFetch — the pipeline must never stall on a scraper.

**The trail stays complete on the fallback path too.** When research comes through WebSearch/WebFetch instead of a scraper, save what you found — the URLs and the key extracts, not just your conclusions — to `.superlearn/research/<slug>/raw/<slug>-fallback-<n>.md`. The Research panel must show the full evidence regardless of which path produced it.

**For paper-driven topics and `research` mode**, also sweep the literature:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_arxiv.py" "<topic>" --limit 10 \
  --out .superlearn/research/<slug>/raw/<slug>-arxiv.json
```

It returns titles, abstracts, authors, dates, and PDF links from the official arXiv API — the seeds of the board's reading list.

**User-provided sources come first.** If `.superlearn/sources/` contains files (PDFs, docs, text — you can read PDFs natively), read every relevant one *before* planning, and write a digest to `research/<slug>/notes/00-user-sources.md` citing each file by name. The user put them there because they matter — ground the board in *their* material, supplemented by the web, not the other way around.

## Phase 2 — Curriculum plan

Write `.superlearn/research/<slug>/plan.md`:

- A 2–3 sentence framing of the topic and who's learning it (ask the user only if the request is genuinely ambiguous).
- A **subtopic checklist** — `- [ ] subtopic` lines. Size it to the topic: ~4–6 for a narrow topic, 8–12 for a broad one. Order from foundations to advanced.
- A short list of the best sources and videos found in Phase 1.

## Phase 3 — Research loop (iterate until saturated)

This is the heart of Superlearn. For **each unchecked subtopic**:

1. Scrape it: `scrape_web.py "<topic> <subtopic>" --read 2 --out .superlearn/research/<slug>/raw/<slug>-<n>.json`
2. Supplement with your own WebSearch/WebFetch where the scrape is thin, plus your expert knowledge.
3. Write `.superlearn/research/<slug>/notes/<nn>-<subtopic-slug>.md`: the key ideas, concrete examples, pitfalls, one candidate diagram idea, pointers for going deeper (papers, primary sources, advanced material), and the URLs that back it.
4. Tick the checkbox in `plan.md`.

Repeat until **every** box is ticked. When there are 6+ subtopics, fan out with the `superlearn-researcher` agent (several in parallel), each owning one subtopic and writing its own notes file; you review each file when it lands and re-research anything thin.

Saturation check before moving on: every subtopic has a notes file with concrete substance (not generic filler), you have at least a handful of real URLs, and at least a few real videoIds (or you've confirmed video coverage is genuinely poor for this topic).

## Phase 4 — Design and author the board

Write `.superlearn/boards/<slug>.json`. This is a **teaching artifact for serious learners, not a summary dump** — every block should deepen understanding. Ground claims in your notes; use real URLs and videoIds only. No quizzes, ever: Superlearn is depth-first, and the validator rejects quiz blocks.

### Design the experience first

**You decide the page's structure and visual identity — deliberately, per topic.** Never default to the same layout/theme out of habit. Choose:

- `layout` — the default view: `board` (masonry cards), `notes` (single-column document), `grid` (uniform cards), `mindmap` (map-first), `feed` (full-width sequence).
- `theme` — `{"preset": "<name>", "accent": "#rrggbb"?}`. Presets are complete visual identities (background, ink scale, typography):

| Preset | Feel | Suits |
|---|---|---|
| `midnight` | dark violet, modern sans | general, creative, product/design topics |
| `blueprint` | deep navy grid, cyan lines | engineering, systems, architecture, hardware |
| `terminal` | near-black, monospace, green | programming, CLIs, infra, security |
| `paper` | warm white, serif, academic | math, theory, research-paper-heavy topics |
| `sepia` | warm tan, bookish serif | history, philosophy, literature, humanities |
| `arctic` | cool light, clean sans | science, medicine, data, finance |

Match structure to the material: a history topic reads best as `notes`/`feed` in `sepia`; a systems-design topic as `board`/`grid` in `blueprint` with diagrams everywhere; a paper-driven field as `notes` in `paper` with a strong resource spine. The optional `accent` recolors the whole identity — use it when the subject has a natural color. **Record the choice and a one-line justification in `plan.md`.**

### Board schema

```json
{
  "id": "<slug>",
  "topic": "<original topic>",
  "title": "<compelling title, ≤60 chars>",
  "emoji": "<one emoji>",
  "createdAt": "<ISO 8601>",
  "mode": "study | interview | research | documentation",
  "depth": "standard",
  "layout": "<your deliberate choice>",
  "theme": { "preset": "<your deliberate choice>", "accent": "#8a2d3b" },
  "blocks": [ ... ],
  "sources": [{ "title": "...", "url": "...", "snippet": "..." }]
}
```

### Block types

Every block: `"type"`, `"title"`, plus type-specific fields. Markdown fields support `###` headings, bold, lists, inline code, fenced code, links, tables.

| type | fields | notes |
|---|---|---|
| `summary` | `markdown` | The big picture. Exactly one, first block. |
| `roadmap` | `steps: [{label, detail}]` | Ordered path from beginner → mastery. One, early. |
| `concept` | `tagline`, `markdown` | One core idea per block, crisply explained with examples. The backbone — 4–8 of these. |
| `note` | `markdown` | Practical tips, gotchas, mental models. |
| `diagram` | `mermaid`, `caption` | Valid Mermaid. Prefer `flowchart TD` or `mindmap`. Short node labels, quote labels with special chars, **no parentheses inside labels**. Include at least one `mindmap` diagram mapping the whole topic. |
| `code` | `language`, `code`, `explanation` | Runnable, idiomatic examples. Only for technical topics. |
| `video` | `videoId`, `channel`, `reason` | **Only videoIds from the scraper output.** Never invent IDs. `reason` = why this video earns its slot. Prefer lectures and deep talks over pop explainers. |
| `resource` | `url`, `source`, `description` | **Only URLs from your research.** Papers, primary sources, authoritative docs, and the best long-form writing — this is the board's spine for going deeper. |
| `flashcards` | `cards: [{front, back}]` | Optional. Only when the domain is genuinely memorization-heavy (vocabulary, anatomy, notation, dates) — serious recall practice, not gamification. |
| `glossary` | `entries: [{term, definition}]` | The vocabulary of the field. |

A standard board is 12–18 blocks: 1 summary, 1 roadmap, 4–8 concepts, 1–3 diagrams (≥1 mindmap), 1–3 notes, code if technical, 2–4 videos, **4–8 resources** (papers, docs, long-form articles), 1 glossary, flashcards only where recall genuinely matters. For deep-dive requests, add an "advanced / open problems" note and more primary sources. Scale down for "quick overview".

### Cross-board links and user annotations

- Any block may carry `"related": [{"board": "<board-id>", "block": "<block title>", "label": "..."}]` — rendered as navigation chips. **When boards overlap conceptually** (Rust ownership ↔ C++ RAII), add links in both directions so the user's library becomes a connected map.
- Blocks may carry `"annotation"` — **the user's own note, written from the app. Never edit, remove, or overwrite annotations.** Do read them: an annotation like "still don't get this" is a direct request to deepen that block on your next iteration.

### Validate — never serve an unvalidated board

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_board.py" .superlearn/boards/<slug>.json
```

Fix every error and warning it reports (it checks schema, mode/theme values, videoId formats, URL validity, and Mermaid smells). Re-run until clean.

### Export the standalone HTML

After validation passes, bake a self-contained HTML file — the whole app plus the board in one file that opens anywhere with no server:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export_html.py" .superlearn/boards/<slug>.json
# → .superlearn/exports/<slug>.html
```

Re-export after any later board edit so the file stays current.

## Phase 5 — Serve and hand over

Start the local Superlearn server in the background (check it isn't already running first — `curl -s http://localhost:4321/api/health`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --boards-dir .superlearn/boards --port 4321
```

Run it in the background so the session stays free. Confirm it's up (`curl -s http://localhost:4321/api/boards`), then tell the user:

- Open **http://localhost:4321** — their board is live, in the layout and theme you designed for the topic.
- The view switcher (Board / Notes / Grid / Mindmap / Feed) restyles the whole experience.
- Diagrams and mindmaps render inline, videos play in place, flashcards (when present) track what they know.
- The **Research** button opens the full research trail — plan, notes, and raw scraper output — right in the app; the same files live in `.superlearn/research/`.
- **Everything is saved on disk**: board JSON in `.superlearn/boards/`, a standalone single-file HTML in `.superlearn/exports/` (also downloadable via the app's HTML button — it works offline, no server), and the research trail alongside.
- **Their notes live in the board**: the ✎ button on any card saves their own annotation into the board JSON — it survives exports and shares, and you read it on the next iteration.
- **Review** runs spaced repetition across every board's flashcards (SM-2 scheduling, due counts on the button); the **Anki** button exports any deck as TSV for their existing Anki setup.
- **Updated cards are badged** — after you edit the board, changed blocks carry an "updated" chip on their next visit, so nothing new gets missed.
- **The session stays live**: they can keep prompting you — the page updates itself within seconds (see below).
- If they ask to **share boards online**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py"` pushes the standalone exports to a `gh-pages` branch of their repo with a generated index page (only run this when explicitly asked — it pushes to their remote).

## Phase 6 — Iterate with the user (live updates)

Serving the board is not the end — it's the start of a conversation. The app polls the server every few seconds and **hot-reloads the open board the moment its JSON changes on disk**, preserving scroll position and showing an update toast. So when the user says things like:

- *"go deeper on X"* / *"add the original papers"* → research if needed, then **append or expand blocks** in the board JSON.
- *"this section is too shallow"* / *"explain Y properly"* → rewrite that block's markdown with real depth.
- *"add a diagram of Z"* / *"map how these relate"* → add a `diagram` block.
- *"change the look"* / *"make it feel more academic"* → update `theme` and/or `layout`.
- *"new topic: W"* → run the full pipeline again; boards accumulate and the picker updates live.

Rules for iteration: **edit surgically** — never regenerate the whole board for a local change; keep everything grounded (research before adding claims, and save that research to the trail like any other); **preserve every `annotation` field** (they're the user's own notes — and read them: they tell you exactly where to go deeper); add `related` links when a new board connects to an existing one; **re-run the validator after every edit**; **re-export the standalone HTML** so `.superlearn/exports/` stays current; never restart the server (it re-reads boards from disk on every request). The user's browser badges changed blocks and updates itself — tell them nothing more than "done, it's on your board".

## Quality bar

- **Complete, never trimmed**: a block is as long as the teaching requires — markdown fields can be essays with multiple sections, worked examples, and tables. Never compress content below usefulness, never cut material to "keep cards short", never summarize where you could teach. The app is built for long-form: cards grow, nothing is clipped. If a concept needs 600 words, write 600 words; if a topic needs 20 blocks, write 20 blocks.
- **Grounded**: claims trace to research notes; no invented URLs or videoIds — the validator and the app both enforce this, but you enforce it first.
- **Deep, not gamified**: this is a tool for people who want mastery. No quizzes, no filler engagement mechanics. Advanced sections, primary sources, open problems, and honest complexity belong on the board.
- **Taught, not listed**: prefer "here's the idea, here's an example, here's the pitfall" over bullet dumps.
- **Visual**: at least one mindmap of the whole territory; diagrams wherever structure beats prose.
- **Designed**: layout and theme chosen for the subject, with the reasoning noted in plan.md — never the same default twice in a row out of habit.
