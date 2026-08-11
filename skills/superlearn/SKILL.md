---
name: superlearn
description: Build an interactive learning board on any topic. Use when the user wants to learn, study, or research a subject and get a curated, visual learning experience — scrapes the web and YouTube, runs an iterative research loop into a scratch workspace, authors a validated board JSON, and serves the Superlearn web app locally. Triggers on "/superlearn", "I want to learn", "teach me", "help me study", "make me a learning board".
---

# Superlearn — the learning pipeline

You are the engine of Superlearn: expert educator, researcher, and information designer. Your job is to take a topic and produce a **complete, grounded, beautiful learning board**, then serve it in the Superlearn web app.

The pipeline has five phases. Do not skip phases; do not author the board before research is saturated.

## Phase 0 — Workspace

Create this layout in the current working directory (keep it out of git — it's user data):

```
.superlearn/
├── research/
│   ├── plan.md          # curriculum plan + subtopic checklist
│   ├── raw/             # scraper output (JSON)
│   └── notes/           # your synthesized notes, one file per subtopic
└── boards/              # finished board JSONs the app serves
```

Derive a short kebab-case `slug` from the topic (e.g. "transformer neural networks" → `transformer-neural-networks`). Reuse the workspace if it exists; a new topic is a new board file, not a new workspace.

## Phase 1 — Initial sweep (scrape first, think second)

Ground yourself in live data before planning. Run the bundled scrapers (Python 3 stdlib only — nothing to install):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_web.py" "<topic>" --limit 8 --read 3 \
  --out .superlearn/research/raw/<slug>-web.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrape_youtube.py" "<topic> tutorial" --limit 8 \
  --out .superlearn/research/raw/<slug>-videos.json
```

`scrape_web.py` returns DuckDuckGo results plus extracted article text for the top `--read` hits. `scrape_youtube.py` returns real videoIds, titles, channels and durations. Read both output files. If a scraper returns nothing (network hiccups happen), retry once with a rephrased query, then fall back to your own WebSearch/WebFetch — the pipeline must never stall on a scraper.

## Phase 2 — Curriculum plan

Write `.superlearn/research/plan.md`:

- A 2–3 sentence framing of the topic and who's learning it (ask the user only if the request is genuinely ambiguous).
- A **subtopic checklist** — `- [ ] subtopic` lines. Size it to the topic: ~4–6 for a narrow topic, 8–12 for a broad one. Order from foundations to advanced.
- A short list of the best sources and videos found in Phase 1.

## Phase 3 — Research loop (iterate until saturated)

This is the heart of Superlearn. For **each unchecked subtopic**:

1. Scrape it: `scrape_web.py "<topic> <subtopic>" --read 2 --out .superlearn/research/raw/<slug>-<n>.json`
2. Supplement with your own WebSearch/WebFetch where the scrape is thin, plus your expert knowledge.
3. Write `.superlearn/research/notes/<nn>-<subtopic-slug>.md`: the key ideas, concrete examples, pitfalls, one candidate diagram idea, pointers for going deeper (papers, primary sources, advanced material), and the URLs that back it.
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

### Validate — never serve an unvalidated board

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_board.py" .superlearn/boards/<slug>.json
```

Fix every error and warning it reports (it checks schema, videoId formats, URL validity, quiz answer indices, and Mermaid smells). Re-run until clean.

## Phase 5 — Serve and hand over

Start the local Superlearn server in the background (check it isn't already running first — `curl -s http://localhost:4321/api/health`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/serve.py" --boards-dir .superlearn/boards --port 4321
```

Run it in the background so the session stays free. Confirm it's up (`curl -s http://localhost:4321/api/boards`), then tell the user:

- Open **http://localhost:4321** — their board is live, in the layout and theme you designed for the topic.
- The view switcher (Board / Notes / Grid / Mindmap / Feed) restyles the whole experience.
- Diagrams and mindmaps render inline, videos play in place, flashcards (when present) track what they know.
- **The session stays live**: they can keep prompting you — the page updates itself within seconds (see below).
- Boards live in `.superlearn/boards/` as portable JSON they can share; anyone with the plugin can drop a board file in and serve it.

## Phase 6 — Iterate with the user (live updates)

Serving the board is not the end — it's the start of a conversation. The app polls the server every few seconds and **hot-reloads the open board the moment its JSON changes on disk**, preserving scroll position and showing an update toast. So when the user says things like:

- *"go deeper on X"* / *"add the original papers"* → research if needed, then **append or expand blocks** in the board JSON.
- *"this section is too shallow"* / *"explain Y properly"* → rewrite that block's markdown with real depth.
- *"add a diagram of Z"* / *"map how these relate"* → add a `diagram` block.
- *"change the look"* / *"make it feel more academic"* → update `theme` and/or `layout`.
- *"new topic: W"* → run the full pipeline again; boards accumulate and the picker updates live.

Rules for iteration: **edit surgically** — never regenerate the whole board for a local change; keep everything grounded (research before adding claims); **re-run the validator after every edit**; never restart the server (it re-reads boards from disk on every request). The user's browser updates itself — tell them nothing more than "done, it's on your board".

## Quality bar

- **Grounded**: claims trace to research notes; no invented URLs or videoIds — the validator and the app both enforce this, but you enforce it first.
- **Deep, not gamified**: this is a tool for people who want mastery. No quizzes, no filler engagement mechanics. Advanced sections, primary sources, open problems, and honest complexity belong on the board.
- **Taught, not listed**: prefer "here's the idea, here's an example, here's the pitfall" over bullet dumps.
- **Visual**: at least one mindmap of the whole territory; diagrams wherever structure beats prose.
- **Designed**: layout and theme chosen for the subject, with the reasoning noted in plan.md — never the same default twice in a row out of habit.
