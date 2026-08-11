# ✦ Superlearn

**Learn anything, beautifully — from inside Claude Code.**

Superlearn is a Claude Code plugin that turns any topic into a deep, visual learning experience. Type what you want to learn; Superlearn scrapes the live web and YouTube, runs an iterative research loop until the topic is fully covered, synthesizes everything into a curated learning board, and serves it in a local web app **designed for that topic** — research notes, concept deep-dives, diagrams and mindmaps, curated papers and long-form articles, learning roadmaps, and embedded lectures. Depth-first, for people who actually want to master things. No quizzes, no gamification.

Because it runs inside Claude Code, **it uses your existing Claude subscription** — no API keys to manage, nothing to configure.

```
/superlearn transformer neural networks
```

…and a few minutes later:

```
✦ Superlearn is live → http://localhost:4321
```

## How it works

```
 /superlearn <topic>
        │
        ▼
 ┌─────────────────┐   Python scrapers (stdlib-only):
 │ 1. SCRAPE       │   DuckDuckGo search · article extraction · YouTube
 └─────────────────┘
        ▼
 ┌─────────────────┐   Claude plans a curriculum: subtopic checklist
 │ 2. PLAN         │   written to .superlearn/research/plan.md
 └─────────────────┘
        ▼
 ┌─────────────────┐   The loop: scrape each subtopic → supplement with
 │ 3. RESEARCH ⟳   │   Claude's own web research → write dense notes →
 └─────────────────┘   tick the checklist → repeat until saturated.
        ▼               (parallel researcher agents for big topics)
 ┌─────────────────┐   Claude DESIGNS the page for the topic (layout +
 │ 4. DESIGN &     │   theme), then authors boards/<topic>.json — summary,
 │    AUTHOR       │   roadmap, concepts, Mermaid diagrams, code, notes,
 └─────────────────┘   glossary, real videos & primary sources — and
        ▼               validates it with the bundled validator.
 ┌─────────────────┐   A local server hosts the Superlearn web app.
 │ 5. SERVE        │   You learn — and keep prompting Claude. The page
 │    & ITERATE ⟳  │   hot-reloads with new material within seconds.
 └─────────────────┘
```

## The app

**Claude designs each board's identity.** Six themes — `midnight`, `blueprint` (engineering), `terminal` (programming/infra), `paper` (academic serif), `sepia` (humanities), `arctic` (science/data) — plus an optional custom accent, chosen per topic. Engineering topics arrive on a blueprint grid; philosophy arrives as a sepia document; systems programming arrives in a terminal. Never the same default twice out of habit.

Five layout modes, switchable live:

| View | What you get |
|---|---|
| **Board** | Masonry of learning cards |
| **Notes** | A single-column document, ordered for reading |
| **Grid** | Uniform card grid |
| **Mindmap** | An auto-generated map of the whole territory + every diagram |
| **Feed** | Everything, full-width, in sequence |

Plus: click-to-play video lectures, Mermaid diagrams and mindmaps, code blocks with copy buttons, curated papers/articles as the board's spine, full-text block filtering, JSON export, and print/PDF.

**Made for serious study:**

- **Your notes live in the board** — annotate any card with your own words; notes save into the board JSON, survive exports and shares, and Claude reads them on the next iteration ("you wrote *'still don't get lifetimes'* — I rewrote that card").
- **Real spaced repetition** — flashcards are scheduled with SM-2 (Again/Hard/Good/Easy, growing intervals), and the **Review** button runs everything due *across all your boards*. One click exports any deck as TSV for Anki.
- **"Updated" badges** — when Claude extends a board, the changed cards are marked on your next visit. Nothing new slips past you.
- **Cross-board links** — related concepts link between boards (Rust ownership ↔ C++ RAII); your library becomes a connected map, not a pile of pages.
- **Bring your own sources** — drop PDFs, papers, or internal docs into `.superlearn/sources/` and boards are grounded in *your* material first, the web second. Research mode also sweeps **arXiv** directly (official API) for abstracts, authors, and reading order.
- **Publish** — `python3 scripts/publish.py` pushes your standalone board HTML to a `gh-pages` branch with a generated index, turning your boards into shareable URLs.

**Live iteration**: the app polls the server and hot-reloads the open board the moment Claude edits it — keep asking questions in the running Claude Code session ("go deeper on X", "add the original papers", "make it feel more academic") and watch the page update in place.

**Nothing is thrown away.** Every run leaves a complete paper trail on disk:

```
.superlearn/
├── research/    the full research trail — plan, synthesized notes, raw scraper
│                output. Browsable in the app via the Research button.
├── boards/      portable board JSON — share with anyone who has the plugin
└── exports/     standalone single-file HTML — the whole app + board baked into
                 one file that opens anywhere, offline, no server needed
```

## Modes

`study` is the default; pass another mode in plain words ("for my interview", "survey the literature", "as a reference") or with `--mode`:

| Mode | What changes |
|---|---|
| `study` | Balanced conceptual mastery — the default experience |
| `interview` | Likely questions with strong answers, pitfalls interviewers probe, rapid-recall material, fast-scan layout |
| `research` | Literature map: seminal + recent papers with why-each-matters, state of the field, open problems, reading order |
| `documentation` | A working reference: code-first usage patterns, configuration tables, gotchas, exact terminology |

## Install

From a marketplace-enabled Claude Code:

```
/plugin marketplace add raiyanyahya/superlearn
/plugin install superlearn@superlearn-marketplace
```

Or clone and load locally:

```bash
git clone https://github.com/raiyanyahya/superlearn
claude --plugin-dir ./superlearn
```

Requirements: Claude Code and Python 3.10+ (stdlib only — the scrapers, validator, and server need nothing installed).

## Usage

```
/superlearn quantum computing
/superlearn the french revolution — deep dive
/superlearn rust lifetimes, I already know C++
```

While the server is running you can keep talking to Claude Code — the page updates itself:

- *"Add a section on error correction to my quantum computing board"*
- *"Go deeper on decoherence — include the original papers"*
- *"Make it feel more academic"* (theme/layout change, live)
- *"Build me a second board on quantum hardware"* — boards accumulate; switch between them in the app.

Serve existing boards any time without re-researching:

```bash
python3 scripts/serve.py --boards-dir .superlearn/boards --port 4321
```

## Repository layout

```
.claude-plugin/    plugin + marketplace manifests
commands/          /superlearn slash command
skills/superlearn/ the research→author→serve playbook Claude follows
agents/            parallel subtopic researcher
scripts/           scrape_web.py · scrape_youtube.py · scrape_arxiv.py · validate_board.py
                   export_html.py · serve.py · publish.py
app/               the Superlearn web app (single file, zero build step)
```

## Board format

Boards are plain JSON — a `title`, `emoji`, `topic`, `mode`, `theme` (preset + optional accent), `layout`, `sources`, and an array of typed blocks: `summary`, `roadmap`, `concept`, `note`, `diagram` (Mermaid), `code`, `video`, `resource`, `flashcards`, `glossary`. The full schema lives in [skills/superlearn/SKILL.md](skills/superlearn/SKILL.md), `scripts/validate_board.py` checks any board against it, and `scripts/export_html.py` bakes any board into a standalone HTML file.

## License

MIT
