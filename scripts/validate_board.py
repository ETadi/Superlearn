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
LAYOUTS = {"board", "notes", "grid", "mindmap", "feed"}
DEPTHS = {"overview", "standard", "deep"}
THEMES = {"midnight", "blueprint", "terminal", "paper", "sepia", "arctic"}

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


def check_block(b, i: int) -> None:
    where = f"blocks[{i}]"
    if not isinstance(b, dict):
        err(f"{where}: not an object")
        return

    btype = b.get("type")
    req_str(b, "title", where)

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
        req_str(b, "language", where)
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
