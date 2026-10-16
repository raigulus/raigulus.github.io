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


def video_page_entries() -> list[str]:
    """One llms.txt line per published video page.

    videos.json is the primary source, but 15 pages are not in it, so any page
    without a record falls back to its own <title> and meta description.
    """
    records = json.loads(
        (ROOT / "assets" / "data" / "videos.json").read_text(encoding="utf-8")
    )
    by_path = {
        record["url"].replace("https://raigulus.github.io", "").strip("/"): record
        for record in records
    }

    lines = []
    videos_dir = ROOT / "division-2" / "videos"
    for page in sorted(videos_dir.glob("*/index.html")):
        content = page.read_text(encoding="utf-8")
        title_match = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
        if not title_match:
            continue
        # Redirect stubs carry noindex/refresh and point elsewhere; listing them
        # would advertise a dead URL to every crawler that reads llms.txt.
        if 'content="noindex"' in content or re.search(
            r'http-equiv=["\']?refresh', content, re.I
        ):
            continue

        path = "/" + page.parent.relative_to(ROOT).as_posix() + "/"
        record = by_path.get(path.strip("/"))
        if record:
            title = record["title"]
            summary = re.sub(r"\s+", " ", record.get("summary") or "").strip()
        else:
            desc_match = re.search(
                r'<meta name="description" content="(.*?)"', content, re.DOTALL
            )
            title = title_match.group(1).strip()
            summary = desc_match.group(1).strip() if desc_match else ""
        title = title.split(" | Raigulus")[0].strip()
        if len(summary) > 200:
            summary = summary[:197].rsplit(" ", 1)[0] + "..."
        entry = f"- [{title}](https://raigulus.github.io{path})"
        lines.append(entry + (f": {summary}" if summary else ""))
    return lines


def sync_video_section(content: str) -> tuple[str, int]:
    """Replace the Video Guides section wholesale so it can never drift again."""
    marker = "## Video Guides"
    wanted = video_page_entries()
    block = marker + "\n\n" + "\n".join(wanted) + "\n"

    if marker not in content:
        anchor = "## SameAs"
        if anchor in content:
            head, _, tail = content.partition(anchor)
            return head + block + "\n" + anchor + tail, len(wanted)

    start = content.index(marker)
    rest = content[start + len(marker) :]
    next_section = re.search(r"^## ", rest, re.MULTILINE)
    end = start + len(marker) + next_section.start() if next_section else len(content)

    current = content[start:end]
    if current.rstrip() == block.rstrip():
        return content, 0
    return content[:start] + block + content[end:].lstrip("\n"), len(wanted)


def pages_missing_icons() -> list[str]:
    """Published pages whose <head> lost the icon links.

    Guards the three page generators: if a template change drops the links,
    this reports every page that regressed instead of letting it ship.
    """
    missing = []
    for page in sorted(ROOT.rglob("*.html")):
        if any(
            part in {"_note_backups", ".git", ".omo", "node_modules"}
            for part in page.relative_to(ROOT).parts
        ):
            continue
        content = page.read_text(encoding="utf-8")
        if '<link rel="stylesheet" href="/assets/styles.css">' not in content:
            continue
        if 'content="noindex"' in content:
            continue
        if 'rel="icon"' not in content or 'rel="apple-touch-icon"' not in content:
            missing.append(page.relative_to(ROOT).as_posix())
    return missing


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

    llms, video_changes = sync_video_section(
        (ROOT / "llms.txt").read_text(encoding="utf-8")
    )
    if video_changes:
        stale_files.append("llms.txt")
        if not args.check:
            llms_path.write_text(llms, encoding="utf-8")

    iconless = pages_missing_icons()

    if args.check and stale_files:
        print("Stale site metadata: " + ", ".join(stale_files))
        print(
            f"Required updates: {item_changes} ItemList name(s), "
            f"{social_changes} SameAs link(s), {video_changes} video guide line(s)"
        )
        return 1

    if iconless:
        print(f"Pages missing icon links: {len(iconless)}")
        for name in iconless[:20]:
            print("  " + name)
        return 1

    action = "Verified" if args.check else "Synchronized"
    print(
        f"{action} site metadata: {item_changes} ItemList name update(s), "
        f"{social_changes} SameAs update(s), {video_changes} video guide line(s), "
        f"icon links present on every page"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
