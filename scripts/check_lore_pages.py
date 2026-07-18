#!/usr/bin/env python3
"""Check generated lore HTML structure and internal links."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
LORE_ROOT = ROOT / "lore"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.title_count = 0
        self.h1_count = 0
        self.canonical_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag in {"link", "script", "img"}:
            target = attributes.get("href") or attributes.get("src")
            if target:
                self.links.append(target)
        if tag == "title":
            self.title_count += 1
        if tag == "h1":
            self.h1_count += 1
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical_count += 1


def internal_target(url):
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return None
    path = parsed.path
    if path.endswith("/"):
        return ROOT / path.lstrip("/") / "index.html"
    return ROOT / path.lstrip("/")


def main():
    errors = []
    pages = sorted(LORE_ROOT.rglob("*.html"))
    if not pages:
        errors.append("No generated lore pages found")
    for page in pages:
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        relative = page.relative_to(ROOT)
        if parser.title_count != 1:
            errors.append(f"{relative}: expected one title element")
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected one h1 element")
        if parser.canonical_count != 1:
            errors.append(f"{relative}: expected one canonical link")
        for link in parser.links:
            target = internal_target(link)
            if target is not None and not target.exists():
                errors.append(f"{relative}: broken internal link {link}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Static lore page checks passed: {len(pages)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
