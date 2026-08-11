#!/usr/bin/env python3
"""Superlearn board validator.

Checks a board JSON against the block schema before it's served: required
fields, per-type block fields, YouTube ID format, URL validity, quiz answer
indices, and common Mermaid hazards. Errors fail the build (exit 1);
warnings should still be fixed.

Usage:
    python3 validate_board.py .superlearn/boards/my-topic.json
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse

YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
LAYOUTS = {"board", "notes", "grid", "mindmap", "feed", "canvas"}
DEPTHS = {"overview", "standard", "deep"}
THEMES = {"midnight", "blueprint", "terminal", "paper", "sepia", "arctic"}
MODES = {"study", "interview", "research", "documentation"}
CHART_KINDS = {"line", "bar", "scatter"}
# Mirrors RUN_KINDS in app/index.html — the languages with a browser runtime.
RUNNABLE_LANGS = {
    "javascript", "js", "node", "nodejs", "python", "py", "python3", "html",
}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def is_http_url(s) -> bool:
    if not isinstance(s, str):
        return False
    try:
        p = urllib.parse.urlparse(s)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def req_str(obj: dict, field: str, where: str) -> str:
    v = obj.get(field)
    if not isinstance(v, str) or not v.strip():
        err(f"{where}: missing or empty '{field}'")
        return ""
    return v


def check_mermaid(src: str, where: str) -> None:
    first = next((ln.strip() for ln in src.splitlines() if ln.strip()), "")
    known = (
        "flowchart", "graph", "mindmap", "sequenceDiagram", "classDiagram",
        "stateDiagram", "erDiagram", "journey", "gantt", "pie", "timeline",
        "quadrantChart", "gitGraph",
    )
    if not first.startswith(known):
        warn(f"{where}: mermaid does not start with a known diagram type (got '{first[:40]}')")
    if "```" in src:
        err(f"{where}: mermaid contains markdown fences — strip them")
    # Parentheses inside [label] or {label} nodes break flowchart parsing.
    if first.startswith(("flowchart", "graph")):
        for m in re.finditer(r"\[([^\]\"]*)\]", src):
            if "(" in m.group(1) or ")" in m.group(1):
                warn(f"{where}: parentheses inside node label '[{m.group(1)[:30]}]' — quote the label or remove them")


def check_chart(b: dict, where: str) -> None:
    """Charts carry their own data, so the shape has to be right or the SVG
    renders empty. Bars are category-indexed; lines and scatters are (x, y)."""
    kind = b.get("chart")
    if kind not in CHART_KINDS:
        err(f"{where}: chart 'chart' must be one of {sorted(CHART_KINDS)}")
        return

    series = b.get("series")
    if not isinstance(series, list) or not series:
        err(f"{where}: chart needs a non-empty 'series' array")
        return
    # Beyond these counts the palette stops separating reliably under CVD, so
    # the app drops the extras — flag it at authoring time instead.
    cap = 3 if kind == "scatter" else 6
    if len(series) > cap:
        warn(
            f"{where}: {len(series)} series but only the first {cap} render "
            f"({kind} colors stop being distinguishable past that) — split the chart"
        )

    cats = b.get("categories")
    if kind == "bar":
        if not isinstance(cats, list) or not cats:
            err(f"{where}: bar chart needs a non-empty 'categories' array")
            return
        if not all(isinstance(c, (str, int, float)) for c in cats):
            err(f"{where}: chart 'categories' must be strings or numbers")

    for si, s in enumerate(series):
        at = f"{where}.series[{si}]"
        if not isinstance(s, dict):
            err(f"{at}: not an object")
            continue
        if not isinstance(s.get("name"), str) or not s["name"].strip():
            err(f"{at}: needs a 'name'")
        if kind == "bar":
            vals = s.get("values")
            if not isinstance(vals, list):
                err(f"{at}: bar series needs a 'values' array")
            elif isinstance(cats, list) and len(vals) != len(cats):
                err(f"{at}: {len(vals)} values but {len(cats)} categories — they must line up")
            elif not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
                err(f"{at}: 'values' must all be numbers")
        else:
            pts = s.get("points")
            if not isinstance(pts, list) or not pts:
                err(f"{at}: {kind} series needs a non-empty 'points' array")
                continue
            for pi, p in enumerate(pts):
                if (
                    not isinstance(p, dict)
                    or not isinstance(p.get("x"), (int, float))
                    or not isinstance(p.get("y"), (int, float))
                    or isinstance(p.get("x"), bool)
                    or isinstance(p.get("y"), bool)
                ):
                    err(f"{at}.points[{pi}]: needs numeric 'x' and 'y'")
                    break

    if not b.get("yLabel"):
        warn(f"{where}: no 'yLabel' — an unlabeled axis leaves the reader guessing at units")


def check_block(b, i: int) -> None:
    where = f"blocks[{i}]"
    if not isinstance(b, dict):
        err(f"{where}: not an object")
        return

    btype = b.get("type")
    req_str(b, "title", where)

    # Optional section name — groups blocks into frames on the canvas view.
    section = b.get("section")
    if section is not None and (
        not isinstance(section, str) or not section.strip() or len(section) > 40
    ):
        err(f"{where}: 'section' must be a short non-empty string (≤40 chars)")

    # Optional user highlights — text the user marked from the app. Like
    # annotations, these are the user's own and must never be authored,
    # edited, or removed by the model.
    hls = b.get("highlights")
    if hls is not None:
        if not isinstance(hls, list) or not all(
            isinstance(h, str) and h.strip() and len(h) <= 600 for h in hls
        ):
            err(f"{where}: 'highlights' must be an array of non-empty strings (≤600 chars)")

    # Optional cross-board links, valid on any block type.
    related = b.get("related")
    if related is not None:
        if not isinstance(related, list):
            err(f"{where}: 'related' must be an array of links")
        else:
            for ri, r in enumerate(related):
                if not isinstance(r, dict) or not isinstance(r.get("board"), str) or not r["board"]:
                    err(f"{where}.related[{ri}]: needs a string 'board' (target board id)")
                elif not all(
                    isinstance(r.get(f), (str, type(None))) for f in ("block", "label")
                ):
                    err(f"{where}.related[{ri}]: 'block' and 'label' must be strings")

    if btype in ("summary", "concept", "note"):
        req_str(b, "markdown", where)
    elif btype == "video":
        vid = req_str(b, "videoId", where)
        if vid and not YT_ID.match(vid):
            err(f"{where}: '{vid}' is not a valid 11-char YouTube videoId")
    elif btype == "diagram":
        src = req_str(b, "mermaid", where)
        if src:
            check_mermaid(src, where)
    elif btype == "code":
        req_str(b, "code", where)
        lang = req_str(b, "language", where).strip().lower()
        # The language tag drives syntax highlighting and decides whether the
        # block gets a Run button, so a vague tag quietly costs both.
        if lang in ("code", "text", "plain", "output", "shell-session"):
            warn(
                f"{where}: language '{lang}' is not a real language — tag the "
                "actual one (python, rust, bash, …) so it gets highlighted"
            )
        if "runnable" in b and not isinstance(b["runnable"], bool):
            err(f"{where}: 'runnable' must be true or false")
        if b.get("runnable") is True and lang not in RUNNABLE_LANGS:
            warn(
                f"{where}: runnable:true has no effect for '{lang}' — only "
                f"{sorted(RUNNABLE_LANGS)} execute in the browser"
            )
    elif btype == "quiz":
        err(
            f"{where}: quiz blocks are not part of Superlearn — this is a "
            "depth-first learning tool. Fold the key checks into concepts, "
            "notes, or flashcards instead."
        )
    elif btype == "flashcards":
        cards = b.get("cards")
        if not isinstance(cards, list) or not cards:
            err(f"{where}: flashcards needs a non-empty 'cards' array")
            return
        for ci, c in enumerate(cards):
            if not isinstance(c, dict) or not c.get("front") or not c.get("back"):
                err(f"{where}.cards[{ci}]: needs 'front' and 'back'")
    elif btype == "resource":
        if not is_http_url(b.get("url")):
            err(f"{where}: resource 'url' must be a valid http(s) URL")
    elif btype == "roadmap":
        steps = b.get("steps")
        if not isinstance(steps, list) or not steps:
            err(f"{where}: roadmap needs a non-empty 'steps' array")
            return
        for si, s in enumerate(steps):
            if not isinstance(s, dict) or not s.get("label"):
                err(f"{where}.steps[{si}]: needs 'label'")
    elif btype == "image":
        if not is_http_url(b.get("url")):
            err(f"{where}: image 'url' must be a valid http(s) URL")
        if not isinstance(b.get("alt"), str) or not b["alt"].strip():
            err(f"{where}: image needs a non-empty 'alt' description")
    elif btype == "chart":
        check_chart(b, where)
    elif btype == "glossary":
        entries = b.get("entries")
        if not isinstance(entries, list) or not entries:
            err(f"{where}: glossary needs a non-empty 'entries' array")
            return
        for ei, e in enumerate(entries):
            if not isinstance(e, dict) or not e.get("term") or not e.get("definition"):
                err(f"{where}.entries[{ei}]: needs 'term' and 'definition'")
    else:
        err(f"{where}: unknown block type '{btype}'")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            board = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}")
        return 1

    if not isinstance(board, dict):
        print("ERROR: board root must be a JSON object")
        return 1

    for field in ("id", "topic", "title", "emoji"):
        req_str(board, field, "board")

    if board.get("layout") not in LAYOUTS:
        warn(f"board: 'layout' should be one of {sorted(LAYOUTS)}")
    if board.get("depth") not in DEPTHS:
        warn(f"board: 'depth' should be one of {sorted(DEPTHS)}")
    mode = board.get("mode")
    if mode is not None and mode not in MODES:
        err(f"board: 'mode' must be one of {sorted(MODES)} (default: study)")

    theme = board.get("theme")
    if theme is None:
        warn(
            "board: no 'theme' set — choose one deliberately "
            f"({sorted(THEMES)}) instead of defaulting"
        )
    elif not isinstance(theme, dict):
        err("board: 'theme' must be an object like {\"preset\": \"paper\"}")
    else:
        if theme.get("preset") not in THEMES:
            err(f"board: theme.preset must be one of {sorted(THEMES)}")
        accent = theme.get("accent")
        if accent is not None and (
            not isinstance(accent, str) or not HEX_COLOR.match(accent)
        ):
            err("board: theme.accent must be a 6-digit hex color like '#8a2d3b'")

    # Optional canvas arrangement — where the user dragged each section's
    # frame on the whiteboard. User-owned: preserve it, never author it.
    canvas = board.get("canvas")
    if canvas is not None:
        if not isinstance(canvas, dict) or not all(
            isinstance(k, str)
            and isinstance(p, dict)
            and isinstance(p.get("x"), (int, float))
            and isinstance(p.get("y"), (int, float))
            for k, p in canvas.items()
        ):
            err("board: 'canvas' must map section names to {x, y} positions")

    blocks = board.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        err("board: 'blocks' must be a non-empty array")
        blocks = []

    summaries = [b for b in blocks if isinstance(b, dict) and b.get("type") == "summary"]
    if len(summaries) != 1:
        warn(f"board: expected exactly 1 summary block, found {len(summaries)}")
    elif blocks and blocks[0].get("type") != "summary":
        warn("board: the summary block should come first")

    for i, b in enumerate(blocks):
        check_block(b, i)

    # Sections are all-or-nothing: a partially sectioned board dumps the
    # unlabeled blocks into a "More" frame on the canvas.
    sectioned = [b for b in blocks if isinstance(b, dict) and isinstance(b.get("section"), str)]
    if sectioned and len(sectioned) < len(blocks):
        warn(
            f"board: {len(blocks) - len(sectioned)} block(s) have no 'section' "
            "while others do — they will land in a generic 'More' frame on the canvas"
        )

    sources = board.get("sources", [])
    if isinstance(sources, list):
        for si, s in enumerate(sources):
            if not isinstance(s, dict) or not is_http_url(s.get("url")):
                err(f"sources[{si}]: needs a valid http(s) 'url'")
    else:
        err("board: 'sources' must be an array")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    if errors:
        print(f"\n✗ {path}: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"✓ {path}: valid ({len(blocks)} blocks), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
