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

Plus: click-to-play video lectures, Mermaid diagrams and mindmaps, code blocks with copy buttons, curated papers/articles as the board's spine, optional flashcards for genuinely memorization-heavy domains, full-text block filtering, JSON export, and print/PDF.

**Live iteration**: the app polls the server and hot-reloads the open board the moment Claude edits it — keep asking questions in the running Claude Code session ("go deeper on X", "add the original papers", "make it feel more academic") and watch the page update in place.

Boards are portable JSON files in `.superlearn/boards/` — share them with anyone who has the plugin.

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
scripts/           scrape_web.py · scrape_youtube.py · validate_board.py · serve.py
app/               the Superlearn web app (single file, zero build step)
```

## Board format

Boards are plain JSON — a `title`, `emoji`, `topic`, `theme` (preset + optional accent), `layout`, `sources`, and an array of typed blocks: `summary`, `roadmap`, `concept`, `note`, `diagram` (Mermaid), `code`, `video`, `resource`, `flashcards`, `glossary`. The full schema lives in [skills/superlearn/SKILL.md](skills/superlearn/SKILL.md), and `scripts/validate_board.py` checks any board against it.

## License

MIT
