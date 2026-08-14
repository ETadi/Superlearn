# Contributing to Superlearn

Thanks for wanting to make this better. The project is deliberately small and
dependency-free — most contributions are a single-file change.

## The two rules that shape everything

1. **Python is standard library only.** Every script in `scripts/` must run on
   a stock Python 3.9+ with nothing to `pip install`. If a change needs a
   third-party package, it needs a different design.
2. **The app has no build step.** `app/index.html` is one file — HTML, CSS,
   and vanilla JS — served as-is. No bundler, no framework, no npm install.
   External libraries (Mermaid, KaTeX, highlight.js, Pyodide) load lazily from
   a CDN and must degrade gracefully when they can't load.

## Getting started

```bash
git clone https://github.com/raiyanyahya/superlearn
cd superlearn

# See the app with the shipped example boards
python3 scripts/serve.py --boards-dir examples --port 4321
# → http://localhost:4321

# Run it as a plugin against your clone
claude
/plugin marketplace add /path/to/superlearn
/plugin install superlearn@superlearn-marketplace
```

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

The suite is stdlib-only and needs no network and no browser: it validates the
example boards, exercises the validator's failure modes, round-trips the
server API (including the security guards), and checks the exporter's
script-context neutralization. If `node` is on your PATH it also syntax-checks
the app's JavaScript. CI runs exactly this on every push and pull request.

## Making changes

- **Board schema changes** touch four places, always together:
  `scripts/validate_board.py` (enforce it), `skills/superlearn/SKILL.md`
  (teach Claude to author it), `app/index.html` (render it), and the README's
  board-format section. A schema field only in some of those is a bug.
- **User-owned data is sacred.** `annotation`, `highlights`, and the board's
  `canvas` arrangement are written by the reader, never by the model. Any new
  user-owned field must follow the same pattern: merged against the freshest
  board on disk before PUT (`saveBoardPatch`), preserved by the skill's
  iteration rules, and validated permissively.
- **Board content is untrusted.** It is authored from scraped pages. Anything
  that renders it must escape first (`esc`/`md2html`), any URL must pass
  `safeUrl`/`safeImageUrl`, and anything that executes it (the code runner)
  stays inside the sandboxed iframe with `allow-scripts` only.
- **Test in a real browser.** CSS-var theming, the canvas, and the runner have
  behavior that unit tests can't see. If you change the app, open it against
  `examples/` in all six themes and the white/black base modes.

## Pull requests

Keep them focused — one behavior per PR. Include what you verified (validator
output, test run, which themes/views you eyeballed). Screenshots for anything
visual. If the validator or tests fail on your branch, the PR isn't ready.
