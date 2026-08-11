#!/usr/bin/env python3
"""Superlearn standalone HTML exporter.

Bakes a board into a single self-contained HTML file: the full Superlearn
app with the board data embedded, so it opens from disk (file://) with no
server — shareable, archivable, emailable.

By default diagrams and math still fetch Mermaid/KaTeX from a CDN on first
open. Pass --offline to vendor those libraries — plus the board's figures —
into the file itself, so the export renders with no network at all.

Usage:
    python3 export_html.py .superlearn/boards/<slug>.json
    python3 export_html.py .superlearn/boards/<slug>.json --offline
    # → .superlearn/exports/<slug>.html   (or use --out)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

APP_HTML = Path(__file__).resolve().parent.parent / "app" / "index.html"

MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
KATEX_JS_URL = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"
KATEX_CSS_URL = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css"
KATEX_FONT_BASE = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/fonts/"
HLJS_URL = "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/highlight.min.js"

# Both libraries publish a UMD build that defines a global, and the app's
# loadLib() resolves immediately when the global is already there — so
# inlining these before the app script is all it takes to go offline.
FONT_SRC_RE = re.compile(r"src:[^;}]*?url\(fonts/([A-Za-z0-9_.\-]+\.woff2)\)[^;}]*")


def build_standalone_html(app_html: str, board: dict, vendor: str = "") -> str:
    """Injects the board as window.SUPERLEARN_EMBEDDED_BOARD before the app
    script; the app detects it and renders without a server.

    Board text can contain anything the web gave the model, so the payload is
    neutralized for HTML script context: every `<` becomes the JSON escape
    `\\u003c`. That kills `</script>` breakout *and* the subtler
    `<!--<script` sequence, which flips the HTML parser into the script-data
    double-escaped state where our own closing tag would stop terminating the
    script. U+2028/U+2029 are escaped too — legal in JSON strings, historically
    illegal in JS string literals. All of these round-trip back to the original
    characters via JSON.parse.

    `vendor` is optional pre-built markup (inlined Mermaid/KaTeX) placed ahead
    of the board so the app's lazy loaders find the globals already present.
    """
    payload = (
        json.dumps(board, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    inject = f"<script>window.SUPERLEARN_EMBEDDED_BOARD = {payload};</script>"
    idx = app_html.index("<script>")
    return app_html[:idx] + vendor + inject + "\n" + app_html[idx:]


def fetch(url: str, cache_dir: Path, name: str) -> bytes:
    """Downloads once, then reads from .superlearn/vendor/ forever after."""
    cached = cache_dir / name
    if cached.is_file() and cached.stat().st_size > 0:
        return cached.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "superlearn/2"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return data


def inline_katex_css(css: str, cache_dir: Path) -> str:
    """Rewrites KaTeX's @font-face rules to embedded woff2 data URIs.

    The stock CSS points at sibling `fonts/*.woff2` files, which don't exist
    next to a single-file export. Only the woff2 is embedded — the woff/ttf
    fallbacks in the same rule would roughly triple the size for browsers that
    have supported woff2 for a decade.
    """
    missing: list[str] = []

    def swap(m: re.Match) -> str:
        name = m.group(1)
        try:
            blob = fetch(KATEX_FONT_BASE + name, cache_dir, name)
        except (urllib.error.URLError, OSError, TimeoutError):
            missing.append(name)
            return m.group(0)
        b64 = base64.b64encode(blob).decode("ascii")
        return f'src:url(data:font/woff2;base64,{b64}) format("woff2")'

    out = FONT_SRC_RE.sub(swap, css)
    if missing:
        print(
            f"[export_html] warning: {len(missing)} KaTeX font(s) unavailable "
            "— math will render with fallback glyphs",
            file=sys.stderr,
        )
    return out


# Deliberately no SVG: an inline SVG document can carry script, and the app
# refuses `data:image/svg+xml` for exactly that reason.
IMAGE_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
}
MAX_INLINE_IMAGE = 4_000_000


def inline_board_images(board: dict, cache_dir: Path) -> dict:
    """Embeds `image` block URLs as data URIs so an offline export shows its
    figures. Anything that can't be fetched keeps its URL — the app already
    degrades a failed image to a labelled placeholder."""
    blocks = board.get("blocks")
    if not isinstance(blocks, list):
        return board
    out = dict(board)
    new_blocks = []
    skipped = 0
    for b in blocks:
        url = b.get("url") if isinstance(b, dict) else None
        if not (isinstance(b, dict) and b.get("type") == "image" and isinstance(url, str)):
            new_blocks.append(b)
            continue
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
        mime = IMAGE_TYPES.get(ext)
        try:
            if not mime:
                raise ValueError("unsupported image type " + (ext or "(none)"))
            blob = fetch(url, cache_dir / "images", f"{hashlib.sha256(url.encode()).hexdigest()[:16]}{ext}")
            if len(blob) > MAX_INLINE_IMAGE:
                raise ValueError(f"{len(blob) // 1024} KB exceeds the inline cap")
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            print(f"[export_html] image not inlined ({exc}): {url}", file=sys.stderr)
            skipped += 1
            new_blocks.append(b)
            continue
        nb = dict(b)
        nb["url"] = f"data:{mime};base64,{base64.b64encode(blob).decode('ascii')}"
        new_blocks.append(nb)
    if skipped:
        print(f"[export_html] {skipped} image(s) still point at the network", file=sys.stderr)
    out["blocks"] = new_blocks
    return out


def build_vendor_bundle(cache_dir: Path) -> str:
    """Fetches (or reuses) Mermaid, KaTeX and highlight.js; returns markup to
    inline.

    Pyodide is deliberately not vendored: it is ~15 MB spread over separate
    wasm and stdlib files that it fetches relative to its own base URL, so it
    cannot be folded into a single document. JavaScript and HTML code blocks
    still run in an offline export; Python says so and asks for a connection.
    """
    mermaid = fetch(MERMAID_URL, cache_dir, "mermaid.min.js").decode("utf-8")
    katex_js = fetch(KATEX_JS_URL, cache_dir, "katex.min.js").decode("utf-8")
    hljs = fetch(HLJS_URL, cache_dir, "highlight.min.js").decode("utf-8")
    katex_css = fetch(KATEX_CSS_URL, cache_dir, "katex.min.css").decode("utf-8")
    katex_css = inline_katex_css(katex_css, cache_dir)

    # A bundle could contain the literal `</script>`; splitting it keeps the
    # HTML parser from ending our tag early.
    def script(src: str) -> str:
        return "<script>" + src.replace("</script", "<\\/script") + "</script>"

    return (
        "<style data-katex>" + katex_css + "</style>\n"
        + script(mermaid) + "\n"
        + script(katex_js) + "\n"
        + script(hljs) + "\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("board", help="path to the board JSON")
    ap.add_argument("--out", help="output HTML path (default: <workspace>/exports/<id>.html)")
    ap.add_argument(
        "--offline",
        action="store_true",
        help="inline Mermaid + KaTeX so diagrams and math render with no network",
    )
    ap.add_argument(
        "--vendor-dir",
        help="where downloaded libraries are cached (default: <workspace>/vendor)",
    )
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
    workspace = board_path.resolve().parent.parent
    out = Path(args.out) if args.out else workspace / "exports" / f"{board_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    vendor = ""
    if args.offline:
        cache_dir = Path(args.vendor_dir) if args.vendor_dir else workspace / "vendor"
        try:
            vendor = build_vendor_bundle(cache_dir)
            board = inline_board_images(board, cache_dir)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            # Better to fail loudly than to hand back a file labelled "offline"
            # that silently needs the network the first time it's opened.
            print(
                f"ERROR: could not vendor the diagram/math libraries: {exc}\n"
                f"       Download them into {cache_dir} manually "
                "(mermaid.min.js, katex.min.js, katex.min.css, "
                "highlight.min.js) and re-run, or drop --offline for a "
                "CDN-backed export.",
                file=sys.stderr,
            )
            return 1

    html = build_standalone_html(APP_HTML.read_text(encoding="utf-8"), board, vendor)
    out.write_text(html, encoding="utf-8")
    kind = "self-contained, offline" if args.offline else "self-contained"
    print(f"[export_html] {board_id} → {out} ({len(html) // 1024} KB, {kind})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
