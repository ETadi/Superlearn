#!/usr/bin/env python3
"""Superlearn standalone HTML exporter.

Bakes a board into a single self-contained HTML file: the full Superlearn
app with the board data embedded, so it opens from disk (file://) with no
server — shareable, archivable, emailable.

Usage:
    python3 export_html.py .superlearn/boards/<slug>.json
    # → .superlearn/exports/<slug>.html   (or use --out)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_HTML = Path(__file__).resolve().parent.parent / "app" / "index.html"


def build_standalone_html(app_html: str, board: dict) -> str:
    """Injects the board as window.SUPERLEARN_EMBEDDED_BOARD before the app
    script; the app detects it and renders without a server."""
    payload = json.dumps(board, ensure_ascii=False).replace("</", "<\\/")
    inject = f"<script>window.SUPERLEARN_EMBEDDED_BOARD = {payload};</script>"
    idx = app_html.index("<script>")
    return app_html[:idx] + inject + "\n" + app_html[idx:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("board", help="path to the board JSON")
    ap.add_argument("--out", help="output HTML path (default: <workspace>/exports/<id>.html)")
    args = ap.parse_args()

    board_path = Path(args.board)
    try:
        board = json.loads(board_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read board: {exc}", file=sys.stderr)
        return 1
    if not isinstance(board, dict) or not isinstance(board.get("blocks"), list):
        print("ERROR: not a Superlearn board", file=sys.stderr)
        return 1

    board_id = str(board.get("id") or board_path.stem)
    out = (
        Path(args.out)
        if args.out
        else board_path.resolve().parent.parent / "exports" / f"{board_id}.html"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    html = build_standalone_html(APP_HTML.read_text(encoding="utf-8"), board)
    out.write_text(html, encoding="utf-8")
    print(f"[export_html] {board_id} → {out} ({len(html) // 1024} KB, self-contained)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
