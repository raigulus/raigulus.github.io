#!/usr/bin/env python3
"""Build the client-side search index for /search/ from page metadata.

Walks every *.html page, extracts <title> + meta description + canonical
URL, skips noindex redirect stubs, and writes assets/data/search-index.json.

Usage:
    python scripts/build_search_index.py            # write index
    python scripts/build_search_index.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "data" / "search-index.json"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
DESC_RE = re.compile(
    r'<meta\s+name="description"\s+content="(.*?)"', re.DOTALL | re.IGNORECASE
)
CANON_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="(.*?)"', re.DOTALL | re.IGNORECASE
)
NOINDEX_RE = re.compile(
    r'<meta\s+name="robots"\s+content="[^"]*noindex', re.IGNORECASE
)
MAIN_RE = re.compile(r"<main>(.*?)</main>", re.DOTALL | re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script.*?</script>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style.*?</style>", re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

SKIP_FILES = {"404.html"}
SKIP_PREFIXES = (".git/", ".github/", ".omo/")


def body_text(content: str) -> str:
    m = MAIN_RE.search(content)
    text = m.group(1) if m else content
    text = SCRIPT_RE.sub(" ", text)
    text = STYLE_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    return WS_RE.sub(" ", html.unescape(text)).strip()


def page_record(path: Path) -> dict | None:
    rel = path.relative_to(ROOT).as_posix()
    if path.name in SKIP_FILES:
        return None
    if rel.startswith(SKIP_PREFIXES):
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if NOINDEX_RE.search(content):
        return None
    title_m = TITLE_RE.search(content)
    if not title_m:
        return None
    title = html.unescape(title_m.group(1).strip())
    title = re.sub(r"\s*\| Raigulus\s*$", "", title)
    desc_m = DESC_RE.search(content)
    desc = html.unescape(desc_m.group(1).strip()) if desc_m else ""
    canon_m = CANON_RE.search(content)
    if canon_m:
        url = canon_m.group(1).replace("https://raigulus.github.io", "") or "/"
    else:
        url = "/" + rel[:-len("index.html")] if rel.endswith("index.html") else "/" + rel
    section = url.strip("/").split("/")[0] if url.strip("/") else "home"
    return {"t": title, "u": url, "d": desc, "s": section, "b": body_text(content)}


def build() -> dict:
    pages = []
    for path in sorted(ROOT.rglob("*.html")):
        rec = page_record(path)
        if rec:
            pages.append(rec)
    today = datetime.date.today().isoformat()
    return {"updated": today, "pages": pages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    index = build()
    if args.check:
        if not OUT.exists():
            print("search-index.json missing")
            return 1
        current = json.loads(OUT.read_text(encoding="utf-8"))
        if len(current.get("pages", [])) != len(index["pages"]):
            print(
                f"stale search index: {len(current.get('pages', []))} indexed, "
                f"{len(index['pages'])} pages on disk"
            )
            return 1
        print(f"search index fresh: {len(index['pages'])} pages")
        return 0

    OUT.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(index['pages'])} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
