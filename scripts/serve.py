#!/usr/bin/env python3
"""Superlearn local server — hosts the web app and the boards API.

Stdlib only. Serves the static app from the plugin's app/ directory and the
user's boards from --boards-dir. Boards are re-read from disk on every
request, so edits made by Claude Code appear on browser refresh.

Endpoints:
    GET  /                  → app
    GET  /api/health        → {"ok": true}
    GET  /api/boards        → board summaries [{id,title,emoji,topic,...}]
    GET  /api/boards/<id>   → full board JSON
    PUT  /api/boards/<id>   → save board JSON (in-app edits, progress)

Usage:
    python3 serve.py --boards-dir .superlearn/boards --port 4321
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socketserver
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-_]*$")


def load_boards(boards_dir: Path) -> dict[str, dict]:
    boards: dict[str, dict] = {}
    if not boards_dir.is_dir():
        return boards
    for path in sorted(boards_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                board = json.load(f)
            if isinstance(board, dict) and isinstance(board.get("blocks"), list):
                board_id = str(board.get("id") or path.stem)
                boards[board_id] = board
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[serve] skipping {path.name}: {exc}", file=sys.stderr)
    return boards


class Handler(SimpleHTTPRequestHandler):
    boards_dir: Path  # set by make_handler

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    # ── helpers ──────────────────────────────────────────────────────────

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def board_id_from_path(self) -> str | None:
        m = re.match(r"^/api/boards/([A-Za-z0-9-_]+)$", self.path.split("?")[0])
        return m.group(1) if m else None

    # ── routes ───────────────────────────────────────────────────────────

    def do_GET(self):  # noqa: N802 (http.server API)
        path = self.path.split("?")[0]

        if path == "/api/health":
            self.send_json({"ok": True})
            return

        if path == "/api/boards":
            boards = load_boards(self.boards_dir)
            summaries = [
                {
                    "id": bid,
                    "title": b.get("title", bid),
                    "emoji": b.get("emoji", "🧠"),
                    "topic": b.get("topic", ""),
                    "createdAt": b.get("createdAt", ""),
                    "layout": b.get("layout", "board"),
                    "blockCount": len(b.get("blocks", [])),
                }
                for bid, b in boards.items()
            ]
            summaries.sort(key=lambda s: str(s["createdAt"]), reverse=True)
            self.send_json(summaries)
            return

        board_id = self.board_id_from_path()
        if board_id:
            boards = load_boards(self.boards_dir)
            if board_id in boards:
                self.send_json(boards[board_id])
            else:
                self.send_json({"error": "board not found"}, 404)
            return

        super().do_GET()

    def do_PUT(self):  # noqa: N802
        board_id = self.board_id_from_path()
        if not board_id:
            self.send_json({"error": "not found"}, 404)
            return
        if not SLUG.match(board_id):
            self.send_json({"error": "invalid board id"}, 400)
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 8_000_000:
            self.send_json({"error": "invalid body size"}, 400)
            return

        try:
            board = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json({"error": "invalid JSON"}, 400)
            return

        if not isinstance(board, dict) or not isinstance(board.get("blocks"), list):
            self.send_json({"error": "not a board"}, 400)
            return

        board["id"] = board_id
        self.boards_dir.mkdir(parents=True, exist_ok=True)
        target = self.boards_dir / f"{board_id}.json"
        tmp = target.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(board, f, indent=2, ensure_ascii=False)
        os.replace(tmp, target)
        self.send_json({"ok": True})

    def log_message(self, fmt, *args):  # quiet: only log API errors
        if "/api/" in (args[0] if args else "") and args[1:2] and args[1] not in ("200",):
            super().log_message(fmt, *args)


class ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--boards-dir", default=".superlearn/boards", help="directory of board JSONs")
    ap.add_argument("--port", type=int, default=4321)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    boards_dir = Path(args.boards_dir).resolve()
    Handler.boards_dir = boards_dir

    if not APP_DIR.is_dir():
        print(f"[serve] app directory missing: {APP_DIR}", file=sys.stderr)
        return 1

    boards = load_boards(boards_dir)
    print(f"[serve] Superlearn on http://{args.host}:{args.port}")
    print(f"[serve] boards dir: {boards_dir} ({len(boards)} board(s))")

    with ThreadingServer((args.host, args.port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] bye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
