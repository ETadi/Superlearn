#!/usr/bin/env python3
"""Superlearn YouTube scraper: finds real videos (IDs, titles, channels).

Parses ytInitialData from the public results page. Stdlib only. Degrades to
empty results on failure so the pipeline never stalls.

Usage:
    python3 scrape_youtube.py "transformers tutorial" --limit 8 --out videos.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = 15


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def extract_balanced_json(s: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(s)):
        ch = s[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def deep_text(node) -> str:
    """Extracts text from YouTube's {runs:[{text}]} / {simpleText} shapes."""
    if not isinstance(node, dict):
        return ""
    if isinstance(node.get("simpleText"), str):
        return node["simpleText"]
    runs = node.get("runs")
    if isinstance(runs, list):
        return "".join(str(r.get("text", "")) for r in runs if isinstance(r, dict))
    return ""


def collect_videos(node, out: list[dict], seen: set[str], limit: int) -> None:
    if len(out) >= limit:
        return
    if isinstance(node, list):
        for item in node:
            collect_videos(item, out, seen, limit)
        return
    if not isinstance(node, dict):
        return

    vr = node.get("videoRenderer")
    if isinstance(vr, dict):
        video_id = vr.get("videoId")
        if isinstance(video_id, str) and video_id not in seen:
            title = deep_text(vr.get("title"))
            channel = deep_text(vr.get("ownerText") or vr.get("longBylineText"))
            duration = deep_text(vr.get("lengthText"))
            if title:
                seen.add(video_id)
                out.append(
                    {
                        "videoId": video_id,
                        "title": title,
                        "channel": channel or "YouTube",
                        "duration": duration or None,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    }
                )

    for value in node.values():
        if len(out) >= limit:
            return
        collect_videos(value, out, seen, limit)


def search_youtube(query: str, limit: int) -> list[dict]:
    try:
        page = fetch(
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote(query)
            + "&hl=en"
        )
    except Exception as exc:
        print(f"[scrape_youtube] search failed: {exc}", file=sys.stderr)
        return []

    marker = page.find("ytInitialData")
    if marker < 0:
        return []
    brace = page.find("{", marker)
    if brace < 0:
        return []
    blob = extract_balanced_json(page, brace)
    if not blob:
        return []

    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return []

    videos: list[dict] = []
    collect_videos(data, videos, set(), limit)
    return videos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", help="search query")
    ap.add_argument("--limit", type=int, default=8, help="max videos")
    ap.add_argument("--out", help="write JSON here (default: stdout)")
    args = ap.parse_args()

    videos = search_youtube(args.query, args.limit)
    payload = {"query": args.query, "videos": videos}
    output = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[scrape_youtube] {len(videos)} videos → {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
