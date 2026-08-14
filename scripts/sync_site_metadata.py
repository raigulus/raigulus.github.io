#!/usr/bin/env python3
"""Synchronize video ItemList names and public SameAs links from site sources."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>',
    re.DOTALL,
)
SOCIAL_URLS = (
    "https://www.youtube.com/@raigulus",
    "https://www.instagram.com/raigulus/",
    "https://www.facebook.com/raigulus/",
)


def video_titles() -> dict[str, str]:
    records = json.loads(
        (ROOT / "assets" / "data" / "videos.json").read_text(encoding="utf-8")
    )
    return {record["url"]: record["title"] for record in records}


def sync_item_lists(value, titles: dict[str, str]) -> int:
    changes = 0
    if isinstance(value, dict):
        if value.get("@type") == "ItemList":
            for item in value.get("itemListElement", []):
                if not isinstance(item, dict) or item.get("@type") != "ListItem":
                    continue
                expected = titles.get(item.get("url", ""))
                if expected and item.get("name") != expected:
                    item["name"] = expected
                    changes += 1
        for nested in value.values():
            changes += sync_item_lists(nested, titles)
    elif isinstance(value, list):
        for nested in value:
            changes += sync_item_lists(nested, titles)
    return changes


def sync_html(path: Path, titles: dict[str, str]) -> tuple[str, int]:
    content = path.read_text(encoding="utf-8")
    changes = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changes
        data = json.loads(match.group(1))
        updated = sync_item_lists(data, titles)
        if not updated:
            return match.group(0)
        changes += updated
        return '<script type="application/ld+json">' + json.dumps(
            data, ensure_ascii=False, separators=(",", ":")
        ) + "</script>"

    return JSON_LD_RE.sub(replace, content), changes


def sync_llms(content: str) -> tuple[str, int]:
    marker = "## SameAs"
    if marker not in content:
        block = marker + "\n\n" + "\n".join(f"- {url}" for url in SOCIAL_URLS)
        return content.rstrip() + "\n\n" + block + "\n", len(SOCIAL_URLS)

    start = content.index(marker)
    next_section = re.search(r"^## ", content[start + len(marker) :], re.MULTILINE)
    end = (
        start + len(marker) + next_section.start()
        if next_section
        else len(content)
    )
    section = content[start:end]
    missing = [url for url in SOCIAL_URLS if f"- {url}" not in section]
    if not missing:
        return content, 0
    addition = "".join(f"- {url}\n" for url in missing)
    updated_section = section.rstrip() + "\n" + addition
    if end < len(content):
        updated_section += "\n"
    return content[:start] + updated_section + content[end:], len(missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="report stale generated metadata without writing files",
    )
    args = parser.parse_args()

    titles = video_titles()
    stale_files = []
    item_changes = 0
    for path in sorted(ROOT.rglob("*.html")):
        content, changes = sync_html(path, titles)
        if not changes:
            continue
        stale_files.append(path.relative_to(ROOT).as_posix())
        item_changes += changes
        if not args.check:
            path.write_text(content, encoding="utf-8")

    llms_path = ROOT / "llms.txt"
    llms, social_changes = sync_llms(llms_path.read_text(encoding="utf-8"))
    if social_changes:
        stale_files.append("llms.txt")
        if not args.check:
            llms_path.write_text(llms, encoding="utf-8")

    if args.check and stale_files:
        print("Stale site metadata: " + ", ".join(stale_files))
        print(f"Required updates: {item_changes} ItemList name(s), {social_changes} SameAs link(s)")
        return 1

    action = "Verified" if args.check else "Synchronized"
    print(
        f"{action} site metadata: {item_changes} ItemList name update(s), "
        f"{social_changes} SameAs update(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
