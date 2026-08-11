#!/usr/bin/env python3
"""Superlearn publisher: push your standalone board HTML to GitHub Pages.

Takes the self-contained files in .superlearn/exports/, generates an index
page, and commits them to a Pages branch of the current repository using a
temporary git worktree — your working tree is never touched.

Usage (from your project root, explicitly invoked — this pushes!):
    python3 publish.py                       # exports → gh-pages → push
    python3 publish.py --no-push             # build the branch locally only
    python3 publish.py --branch docs-boards  # custom branch
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


def board_meta(boards_dir: Path, stem: str) -> dict:
    path = boards_dir / f"{stem}.json"
    try:
        board = json.loads(path.read_text(encoding="utf-8"))
        return {
            "title": board.get("title", stem),
            "emoji": board.get("emoji", "🧠"),
            "topic": board.get("topic", ""),
            "blocks": len(board.get("blocks", [])),
            "mode": board.get("mode", "study"),
        }
    except (OSError, json.JSONDecodeError):
        return {"title": stem, "emoji": "🧠", "topic": "", "blocks": 0, "mode": "study"}


def build_index(entries: list[tuple[str, dict]], site_title: str) -> str:
    cards = "\n".join(
        f'<a class="b" href="{html.escape(fname)}">'
        f'<span class="e">{html.escape(m["emoji"])}</span>'
        f'<span><strong>{html.escape(m["title"])}</strong>'
        f'<small>{html.escape(m["topic"])} · {m["blocks"]} blocks · {html.escape(m["mode"])}</small></span></a>'
        for fname, m in entries
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(site_title)}</title>
<style>
  body{{background:#0b0b10;color:#d4d4e2;font-family:system-ui,sans-serif;margin:0;
       min-height:100vh;display:grid;place-items:center;padding:40px 20px;box-sizing:border-box}}
  main{{max-width:640px;width:100%}}
  h1{{color:#ececf4;font-size:28px;letter-spacing:-.02em}} h1 span{{color:#7c5cff}}
  p{{color:#8a8aa3;margin-bottom:28px}}
  .b{{display:flex;gap:14px;align-items:center;background:#171724;border:1px solid #2a2a3d;
      border-radius:14px;padding:16px 18px;margin-bottom:12px;text-decoration:none;color:#d4d4e2;
      transition:border-color .15s}}
  .b:hover{{border-color:#7c5cff}}
  .e{{font-size:26px}} strong{{display:block;color:#ececf4}} small{{color:#8a8aa3}}
</style></head><body><main>
<h1><span>✦</span> {html.escape(site_title)}</h1>
<p>Learning boards built with Superlearn — fully self-contained pages.</p>
{cards}
</main></body></html>
"""


def pages_url(repo_root: str, remote: str) -> str | None:
    try:
        url = run(["git", "remote", "get-url", remote], cwd=repo_root).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    return f"https://{owner}.github.io/{repo}/"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exports-dir", default=".superlearn/exports")
    ap.add_argument("--boards-dir", default=".superlearn/boards")
    ap.add_argument("--branch", default="gh-pages")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--title", default="Superlearn boards")
    ap.add_argument("--no-push", action="store_true", help="build the branch, don't push")
    args = ap.parse_args()

    try:
        repo_root = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    except subprocess.CalledProcessError:
        print("ERROR: not inside a git repository", file=sys.stderr)
        return 1

    exports = Path(args.exports_dir).resolve()
    boards_dir = Path(args.boards_dir).resolve()
    files = sorted(exports.glob("*.html")) if exports.is_dir() else []
    if not files:
        print(f"ERROR: no exported boards in {exports} — run export_html.py first", file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="superlearn-pages-"))
    worktree_added = False
    try:
        # Attach a worktree on the pages branch (create it orphaned if new).
        branch_exists = (
            run(["git", "rev-parse", "--verify", "--quiet", args.branch],
                cwd=repo_root, check=False).returncode == 0
            or run(["git", "rev-parse", "--verify", "--quiet", f"{args.remote}/{args.branch}"],
                   cwd=repo_root, check=False).returncode == 0
        )
        if branch_exists:
            if run(["git", "rev-parse", "--verify", "--quiet", args.branch],
                   cwd=repo_root, check=False).returncode != 0:
                run(["git", "branch", args.branch, f"{args.remote}/{args.branch}"], cwd=repo_root)
            run(["git", "worktree", "add", str(tmp), args.branch], cwd=repo_root)
        else:
            run(["git", "worktree", "add", "--detach", str(tmp), "HEAD"], cwd=repo_root)
            run(["git", "checkout", "--orphan", args.branch], cwd=str(tmp))
            run(["git", "rm", "-rf", "--quiet", "."], cwd=str(tmp), check=False)
        worktree_added = True

        # Lay down the site: exported boards + generated index. `.nojekyll`
        # stops GitHub Pages from mangling anything.
        for stale in tmp.iterdir():
            if stale.name == ".git":
                continue
            shutil.rmtree(stale) if stale.is_dir() else stale.unlink()
        entries = []
        for f in files:
            shutil.copy2(f, tmp / f.name)
            entries.append((f.name, board_meta(boards_dir, f.stem)))
        (tmp / "index.html").write_text(build_index(entries, args.title), encoding="utf-8")
        (tmp / ".nojekyll").write_text("", encoding="utf-8")

        if not run(["git", "status", "--porcelain"], cwd=str(tmp)).stdout.strip():
            print("[publish] nothing changed — site already up to date")
            return 0

        run(["git", "add", "-A"], cwd=str(tmp))
        run(["git", "-c", "user.email=superlearn@local", "-c", "user.name=Superlearn",
             "commit", "-m", f"Publish {len(files)} Superlearn board(s)"], cwd=str(tmp))

        if args.no_push:
            print(f"[publish] built branch '{args.branch}' locally ({len(files)} boards) — not pushed")
        else:
            run(["git", "push", "-u", args.remote, args.branch], cwd=str(tmp))
            print(f"[publish] pushed {len(files)} board(s) to {args.remote}/{args.branch}")
            url = pages_url(repo_root, args.remote)
            if url:
                print(f"[publish] once Pages is enabled for '{args.branch}': {url}")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: {' '.join(exc.cmd)} failed:\n{exc.stderr}", file=sys.stderr)
        return 1
    finally:
        if worktree_added:
            run(["git", "worktree", "remove", "--force", str(tmp)], cwd=repo_root, check=False)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
