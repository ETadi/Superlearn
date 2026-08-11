#!/usr/bin/env python3
"""Superlearn web scraper: DuckDuckGo search + readable article extraction.

Stdlib only — no installs. Defensive by design: network failures degrade to
empty results (exit 0) so the learning pipeline never hard-fails on a flaky
source.

Usage:
    python3 scrape_web.py "transformer neural networks" --limit 8 --read 3 \
        --out research/raw/web.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = 15


def fetch(url: str, extra_headers: dict[str, str] | None = None) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
            **(extra_headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset, errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]*>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_ddg_url(href: str) -> str | None:
    """DDG wraps results in /l/?uddg=<encoded>. Unwrap to the real target."""
    try:
        if href.startswith("//"):
            href = "https:" + href
        parsed = urllib.parse.urlparse(urllib.parse.urljoin("https://duckduckgo.com", href))
        qs = urllib.parse.parse_qs(parsed.query)
        target = urllib.parse.unquote(qs["uddg"][0]) if "uddg" in qs else href
        t = urllib.parse.urlparse(target)
        if t.scheme not in ("http", "https"):
            return None
        if "duckduckgo.com" in t.netloc:
            return None
        return target
    except Exception:
        return None


def _assemble(links: list[tuple[str, str]], snippets: list[str], limit: int) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    for i, (url, title) in enumerate(links):
        if url in seen:
            continue
        seen.add(url)
        results.append(
            {"title": title, "url": url, "snippet": snippets[i] if i < len(snippets) else ""}
        )
        if len(results) >= limit:
            break
    return results


def parse_html_results(page: str, limit: int) -> list[dict]:
    """Parses the html.duckduckgo.com endpoint (class-based markup)."""
    links: list[tuple[str, str]] = []
    for m in re.finditer(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        page,
        re.S,
    ):
        url = resolve_ddg_url(html.unescape(m.group(1)))
        title = strip_tags(m.group(2))
        if url and title:
            links.append((url, title))

    snippets = [
        strip_tags(m.group(1))
        for m in re.finditer(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', page, re.S
        )
    ]
    return _assemble(links, snippets, limit)


def parse_lite_results(page: str, limit: int) -> list[dict]:
    """Parses the lite.duckduckgo.com endpoint (plain-table markup) — a
    different, simpler page that tends to survive redesigns of the main one."""
    links: list[tuple[str, str]] = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        url = resolve_ddg_url(html.unescape(m.group(1)))
        title = strip_tags(m.group(2))
        if url and title:
            links.append((url, title))

    snippets = [
        strip_tags(m.group(1))
        for m in re.finditer(
            r'<td[^>]+class="[^"]*result-snippet[^"]*"[^>]*>(.*?)</td>', page, re.S
        )
    ]
    return _assemble(links, snippets, limit)


ENDPOINTS = (
    ("https://html.duckduckgo.com/html/?q=", parse_html_results),
    ("https://lite.duckduckgo.com/lite/?q=", parse_lite_results),
)


def search_duckduckgo(query: str, limit: int) -> list[dict]:
    """Tries the main endpoint, then falls back to the lite one — two
    independent markups, so one redesign can't zero out search."""
    for base, parser in ENDPOINTS:
        try:
            page = fetch(base + urllib.parse.quote(query))
        except Exception as exc:
            print(f"[scrape_web] {base.split('/')[2]} failed: {exc}", file=sys.stderr)
            continue
        results = parser(page, limit)
        if results:
            return results
        print(f"[scrape_web] {base.split('/')[2]} returned no results", file=sys.stderr)
    return []


BLOCK_STRIP = re.compile(
    r"<(script|style|nav|header|footer|aside|noscript|svg|form)[^>]*>.*?</\1>",
    re.S | re.I,
)


def extract_article(url: str, max_chars: int = 6000) -> dict:
    """Rough readability: prefer <article>/<main>, pull paragraph-level text."""
    try:
        page = fetch(url)
    except Exception as exc:
        print(f"[scrape_web] read failed for {url}: {exc}", file=sys.stderr)
        return {"url": url, "title": url, "text": ""}

    title_m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = strip_tags(title_m.group(1)) if title_m else url

    body = BLOCK_STRIP.sub(" ", page)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)

    scoped_m = re.search(r"<article[^>]*>.*?</article>", body, re.S | re.I) or re.search(
        r"<main[^>]*>.*?</main>", body, re.S | re.I
    )
    scoped = scoped_m.group(0) if scoped_m else body

    paragraphs: list[str] = []
    total = 0
    for m in re.finditer(r"<(p|h1|h2|h3|li)[^>]*>(.*?)</\1>", scoped, re.S | re.I):
        text = strip_tags(m.group(2))
        if len(text) > 40:
            paragraphs.append(text)
            total += len(text)
        if total > max_chars * 1.5:
            break

    text = "\n".join(paragraphs)
    if len(text) < 200:
        text = strip_tags(scoped)[:max_chars]
    return {"url": url, "title": title, "text": text[:max_chars]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", help="search query")
    ap.add_argument("--limit", type=int, default=8, help="max search results")
    ap.add_argument("--read", type=int, default=0, help="extract article text for top N results")
    ap.add_argument(
        "--max-chars", type=int, default=6000,
        help="max characters captured per article (raise for deep runs)",
    )
    ap.add_argument("--out", help="write JSON here (default: stdout)")
    args = ap.parse_args()

    results = search_duckduckgo(args.query, args.limit)
    articles = [
        extract_article(r["url"], max_chars=max(args.max_chars, 500))
        for r in results[: max(args.read, 0)]
    ]
    articles = [a for a in articles if a["text"]]

    payload = {"query": args.query, "results": results, "articles": articles}
    output = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(
            f"[scrape_web] {len(results)} results, {len(articles)} articles → {args.out}"
        )
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
