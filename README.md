# ✦ Superlearn

**Learn anything, beautifully — from inside Claude Code.**

Superlearn is a Claude Code plugin that turns any topic into an interactive, visual learning experience. Type what you want to learn; Superlearn scrapes the live web and YouTube, runs an iterative research loop until the topic is fully covered, synthesizes everything into a curated learning board, and serves it in a gorgeous local web app — Pinterest-style boards, document notes, diagrams and mindmaps, interactive quizzes, flip-card flashcards, and embedded videos.

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
 ┌─────────────────┐   Claude authors boards/<topic>.json — summary,
 │ 4. AUTHOR       │   roadmap, concepts, Mermaid diagrams, code, quiz,
 └─────────────────┘   flashcards, glossary, real videos & sources —
        ▼               then validates it with the bundled validator.
 ┌─────────────────┐   A local server hosts the Superlearn web app.
 │ 5. SERVE        │   You learn. Ask Claude to extend the board any
 └─────────────────┘   time — refresh and it's there.
```

## The app

Five layout modes, switchable live:

| View | What you get |
|---|---|
| **Board** | Pinterest-style masonry of learning cards |
| **Notes** | A single-column document, ordered for reading |
| **Grid** | Uniform card grid |
| **Mindmap** | An auto-generated map of the whole territory + every diagram |
| **Feed** | Everything, full-width, in sequence |

Plus: interactive quizzes with scoring, flashcards with flip animation and "known" tracking, click-to-play YouTube embeds, Mermaid diagrams, code blocks with copy buttons, full-text block filtering, JSON export, and print/PDF.

Progress (quiz scores, known flashcards) is saved in your browser. Boards are portable JSON files in `.superlearn/boards/` — share them with anyone who has the plugin.

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

While the server is running you can keep talking to Claude Code:

- *"Add a section on error correction to my quantum computing board"*
- *"Make the quiz harder"*
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

Boards are plain JSON — a `title`, `emoji`, `topic`, `sources`, and an array of typed blocks: `summary`, `roadmap`, `concept`, `note`, `diagram` (Mermaid), `code`, `video`, `resource`, `quiz`, `flashcards`, `glossary`. The full schema lives in [skills/superlearn/SKILL.md](skills/superlearn/SKILL.md), and `scripts/validate_board.py` checks any board against it.

## License

MIT
