#!/usr/bin/env python3
"""
hub_scraper.py – Scrape Division Fandom Wiki hub/compendium pages
and generate collectible JSON lore-entry files.

Each hub page (e.g. "Comms/Hyenas") contains multiple individual comms.
This script creates ONE entry per hub, with each comm as a section.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIKI_API = "https://thedivision.fandom.com/api.php"
WIKI_BASE = "https://thedivision.fandom.com/wiki/"
ENTRIES_ROOT = Path("/tmp/raigulus-site/content/lore/entries")
TODAY = date.today().isoformat()
MAX_PARA_CHARS = 800

# ---------------------------------------------------------------------------
# Hub registry: (wiki_path, display_name, category)
# ---------------------------------------------------------------------------

HUB_REGISTRY: list[tuple[str, str, str]] = [
    # TD2 Comms (faction/settlement/profile)
    ("Comms/Hyenas", "TD2 Comms: Hyenas", "comms"),
    ("Comms/True Sons", "TD2 Comms: True Sons", "comms"),
    ("Comms/Outcasts", "TD2 Comms: Outcasts", "comms"),
    ("Comms/Black Tusk", "TD2 Comms: Black Tusk", "comms"),
    ("Comms/JTF", "TD2 Comms: JTF", "comms"),
    ("Comms/Division", "TD2 Comms: Division", "comms"),
    ("Comms/Government", "TD2 Comms: Government", "comms"),
    ("Comms/Dark Zone", "TD2 Comms: Dark Zone", "comms"),
    ("Comms/Contaminated Areas", "TD2 Comms: Contaminated Areas", "comms"),
    ("Comms/Dead Drops", "TD2 Comms: Dead Drops", "comms"),
    ("Comms/Campus", "TD2 Comms: Campus", "comms"),
    ("Comms/Castle", "TD2 Comms: Castle", "comms"),
    ("Comms/Theater", "TD2 Comms: Theater", "comms"),
    ("Comms/New York", "TD2 Comms: New York", "comms"),
    ("Comms/Lower Manhattan", "TD2 Comms: Lower Manhattan", "comms"),
    ("Comms/Coney Island", "TD2 Comms: Coney Island", "comms"),
    ("Comms/Langley Reports", "TD2 Comms: Langley Reports", "comms"),
    ("Comms/Pentagon Staff Logs", "TD2 Comms: Pentagon Staff Logs", "comms"),
    ("Comms/BTSU Team 9", "TD2 Comms: BTSU Team 9", "comms"),
    ("Comms/Brenner's Orders", "TD2 Comms: Brenner's Orders", "comms"),
    ("Comms/Shay", "TD2 Comms: Shay", "comms"),
    ("Comms/Roy Benitez", "TD2 Comms: Roy Benitez", "comms"),
    ("Comms/Paul Rhodes", "TD2 Comms: Paul Rhodes", "comms"),
    ("Comms/Aaron Keener", "TD2 Comms: Aaron Keener", "comms"),
    ("Comms/James Dragov", "TD2 Comms: James Dragov", "comms"),
    ("Comms/Javier Kajika", "TD2 Comms: Javier Kajika", "comms"),
    ("Comms/Theo Parnell", "TD2 Comms: Theo Parnell", "comms"),
    ("Comms/Vivian Conley", "TD2 Comms: Vivian Conley", "comms"),
    ("Comms/Faye Lau", "TD2 Comms: Faye Lau", "comms"),
    ("Comms/Profile: Agent Kelso", "TD2 Comms: Profile - Agent Kelso", "comms"),
    ("Comms/Profile: Antwon Ridgeway", "TD2 Comms: Profile - Antwon Ridgeway", "comms"),
    ("Comms/Profile: Emeline Shaw", "TD2 Comms: Profile - Emeline Shaw", "comms"),
    ("Comms/Profile: Henry Hayes", "TD2 Comms: Profile - Henry Hayes", "comms"),
    ("Comms/Profile: Odessa Sawyer", "TD2 Comms: Profile - Odessa Sawyer", "comms"),
    ("Comms/Profile: President Ellis", "TD2 Comms: Profile - President Ellis", "comms"),
    # TD2 Manhunt Comms
    ("Comms/Manhunt: Shadow Tide", "TD2 Comms: Manhunt - Shadow Tide", "comms"),
    ("Comms/Manhunt: Keener's Legacy", "TD2 Comms: Manhunt - Keener's Legacy", "comms"),
    ("Comms/Manhunt: Concealed Agenda", "TD2 Comms: Manhunt - Concealed Agenda", "comms"),
    ("Comms/Manhunt: End of Watch", "TD2 Comms: Manhunt - End of Watch", "comms"),
    ("Comms/Manhunt: Hidden Alliance", "TD2 Comms: Manhunt - Hidden Alliance", "comms"),
    ("Comms/Manhunt: Price of Power", "TD2 Comms: Manhunt - Price of Power", "comms"),
    ("Comms/Manhunt: Reign of Fire", "TD2 Comms: Manhunt - Reign of Fire", "comms"),
    ("Comms/Manhunt: Broken Wings", "TD2 Comms: Manhunt - Broken Wings", "comms"),
    ("Comms/Manhunt: Puppeteers", "TD2 Comms: Manhunt - Puppeteers", "comms"),
    ("Comms/Manhunt: Vanguard", "TD2 Comms: Manhunt - Vanguard", "comms"),
    ("Comms/Manhunt: First Rogue", "TD2 Comms: Manhunt - First Rogue", "comms"),
    ("Comms/Manhunt: Shades of Red", "TD2 Comms: Manhunt - Shades of Red", "comms"),
    ("Comms/Manhunt: Burden of Truth", "TD2 Comms: Manhunt - Burden of Truth", "comms"),
    ("Comms/Manhunt: Crossroads", "TD2 Comms: Manhunt - Crossroads", "comms"),
    ("Comms/Manhunt: The Pact", "TD2 Comms: Manhunt - The Pact", "comms"),
    ("Comms/Manhunt: Mutiny", "TD2 Comms: Manhunt - Mutiny", "comms"),
    ("Comms/Manhunt: Rise Up", "TD2 Comms: Manhunt - Rise Up", "comms"),
    ("Comms/Incursion: Paradise Lost", "TD2 Comms: Incursion - Paradise Lost", "comms"),
    # TD2 Brooklyn Comms
    ("Comms/Brooklyn: Bridge", "TD2 Comms: Brooklyn - Bridge", "comms"),
    ("Comms/Brooklyn: Friendly", "TD2 Comms: Brooklyn - Friendly", "comms"),
    ("Comms/Brooklyn: History", "TD2 Comms: Brooklyn - History", "comms"),
    ("Comms/Brooklyn: Hostiles", "TD2 Comms: Brooklyn - Hostiles", "comms"),
    # TD1 Phone Recordings
    ("Phone Recordings/Before Outbreak", "TD1 Phone Recordings: Before Outbreak", "phone-recordings"),
    ("Phone Recordings/Birds", "TD1 Phone Recordings: Birds", "phone-recordings"),
    ("Phone Recordings/Calling the Other Side", "TD1 Phone Recordings: Calling the Other Side", "phone-recordings"),
    ("Phone Recordings/Come Together", "TD1 Phone Recordings: Come Together", "phone-recordings"),
    ("Phone Recordings/Creep", "TD1 Phone Recordings: Creep", "phone-recordings"),
    ("Phone Recordings/Directive 51", "TD1 Phone Recordings: Directive 51", "phone-recordings"),
    ("Phone Recordings/Growing Wild", "TD1 Phone Recordings: Growing Wild", "phone-recordings"),
    ("Phone Recordings/JTF", "TD1 Phone Recordings: JTF", "phone-recordings"),
    ("Phone Recordings/Keener's Confession", "TD1 Phone Recordings: Keener's Confession", "phone-recordings"),
    ("Phone Recordings/Keener's Reports", "TD1 Phone Recordings: Keener's Reports", "phone-recordings"),
    ("Phone Recordings/LMB Status Report", "TD1 Phone Recordings: LMB Status Report", "phone-recordings"),
    ("Phone Recordings/Lucky Girl", "TD1 Phone Recordings: Lucky Girl", "phone-recordings"),
    ("Phone Recordings/National Guard", "TD1 Phone Recordings: National Guard", "phone-recordings"),
]


# ---------------------------------------------------------------------------
# HTML text extractor
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                    "li", "tr", "td", "th", "dd", "dt"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    ext = _TextExtractor()
    ext.feed(html)
    return ext.get_text()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(params: dict[str, Any]) -> dict[str, Any]:
    """MediaWiki API GET with retries."""
    from urllib.parse import urlencode
    for attempt in range(3):
        try:
            url = WIKI_API + "?" + urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": "RaigulusLoreBot/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    return {}


def fetch_hub_html(wiki_path: str) -> str:
    """Fetch rendered HTML for a hub page via action=parse."""
    params = {
        "action": "parse",
        "page": wiki_path,
        "prop": "text",
        "format": "json",
        "redirects": "1",
    }
    data = api_get(params)
    if "error" in data:
        print(f"  ERROR: {data['error'].get('info', 'unknown')}", file=sys.stderr)
        return ""
    return data.get("parse", {}).get("text", {}).get("*", "")


# ---------------------------------------------------------------------------
# Comm parser
# ---------------------------------------------------------------------------

def _find_content_start(lines: list[str]) -> int:
    """Find first comm title by pattern: title -> description -> audio URL."""
    for i in range(len(lines)):
        line = lines[i].strip()
        if not line or line.startswith('"') or line.startswith("http") or line.startswith("[IMG:"):
            continue
        # Look ahead for description (skip empties)
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines):
            break
        desc = lines[j].strip()
        if desc.startswith('"'):
            # Look ahead for audio URL (skip empties)
            k = j + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and lines[k].strip().startswith("http") and ".ogg" in lines[k]:
                return i
    return 0


def parse_comms_from_text(text: str) -> list[dict[str, str]]:
    """Parse individual comm entries from hub page text."""
    lines = text.split("\n")
    entries: list[dict[str, str]] = []

    content_start = _find_content_start(lines)
    i = content_start

    while i < len(lines):
        line = lines[i].strip()

        if not line or line.startswith("http") or line.startswith("[IMG:"):
            i += 1
            continue

        # Coordinates -> attach to previous entry
        if re.match(r"^[A-Z][a-z]+.*\(\d+,\s*\d+\)$", line):
            if entries:
                entries[-1]["location"] = line
            i += 1
            continue

        # Detect title: next non-empty line starts with "
        is_title = False
        if line and not line.startswith('"') and not line.startswith("(") and not line.startswith("http"):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith('"'):
                is_title = True
            elif (len(line) < 60 and ":" not in line
                  and not any(kw in line.upper() for kw in
                              ["MEMBER", "BOSS", "AGENT", "OFFICER", "SOLDIER",
                               "JTF", "HYENA", "TRUE", "BLACK", "OUTCAST",
                               "CLEANER", "RIKER", "LMB", "PRESIDENT"])):
                is_title = True

        if is_title:
            entry: dict[str, str] = {
                "title": line,
                "description": "",
                "audio_url": "",
                "location": "",
                "transcript": "",
            }
            i += 1

            # Skip empties
            while i < len(lines) and not lines[i].strip():
                i += 1

            # Description
            if i < len(lines) and lines[i].strip().startswith('"'):
                desc_lines = [lines[i].strip().strip('"')]
                i += 1
                while i < len(lines) and lines[i].strip().startswith('"'):
                    desc_lines.append(lines[i].strip().strip('"'))
                    i += 1
                entry["description"] = " ".join(desc_lines)

            # Skip empties
            while i < len(lines) and not lines[i].strip():
                i += 1

            # Audio URL
            if i < len(lines) and lines[i].strip().startswith("http") and ".ogg" in lines[i]:
                entry["audio_url"] = lines[i].strip().split("noicon")[0].strip()
                i += 1

            # Skip empties
            while i < len(lines) and not lines[i].strip():
                i += 1

            # Location
            if i < len(lines):
                loc = lines[i].strip()
                if re.match(r"^(.+?)\s*\((\d+),\s*(\d+)\)$", loc):
                    entry["location"] = loc
                    i += 1

            # Transcript
            tlines: list[str] = []
            while i < len(lines):
                t = lines[i].strip()
                if not t:
                    i += 1
                    continue
                # Next title?
                if (t and not t.startswith('"') and not t.startswith("(") and not t.startswith("http")):
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and lines[j].strip().startswith('"'):
                        break
                tlines.append(t)
                i += 1

            entry["transcript"] = "\n".join(tlines)
            if entry["transcript"] or entry["description"]:
                entries.append(entry)
        else:
            i += 1

    return entries


# ---------------------------------------------------------------------------
# Entry builder
# ---------------------------------------------------------------------------

def slugify(title: str) -> str:
    slug = title.lower()
    slug = unicodedata.normalize("NFKD", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _split_into_chunks(text: str, max_chars: int = MAX_PARA_CHARS) -> list[str]:
    """Split text into chunks at line boundaries, respecting max_chars."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for line in text.split("\n"):
        ll = len(line) + 1
        if cur_len + ll > max_chars and cur:
            chunks.append("\n".join(cur))
            cur = [line]
            cur_len = ll
        else:
            cur.append(line)
            cur_len += ll
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def build_hub_entry(
    wiki_path: str,
    display_name: str,
    category: str,
    comms: list[dict[str, str]],
) -> dict[str, Any]:
    """Build a collectible entry dict from parsed hub comms."""
    slug = slugify(display_name)
    source_id = "wiki-" + wiki_path.lower().replace(" ", "-").replace(":", "").replace("'", "").replace('"', '')

    total = len(comms)
    with_transcript = sum(1 for c in comms if c.get("transcript"))
    with_location = sum(1 for c in comms if c.get("location"))

    cat_label = category.replace("-", " ").title()
    summary = (
        f"A collection of {total} {cat_label.lower()} from The Division universe, "
        f"scraped from the Fandom wiki hub page. "
        f"{with_transcript} entries include full audio transcripts; "
        f"{with_location} have known map locations."
    )

    # Claims
    claims: list[dict[str, Any]] = []
    for ci, comm in enumerate(comms, 1):
        txt = f'Comm "{comm["title"]}"'
        if comm.get("description"):
            txt += f": {comm['description']}"
        if comm.get("location"):
            txt += f" (Location: {comm['location']})"
        claims.append({
            "id": f"{slug}-comm-{ci}",
            "text": txt,
            "assessment": "confirmed",
            "source_ids": [source_id],
        })

    # Sections
    entry_sections: list[dict[str, Any]] = []
    for ci, comm in enumerate(comms):
        paras: list[dict[str, Any]] = []
        if comm.get("transcript"):
            for chunk in _split_into_chunks(comm["transcript"]):
                paras.append({
                    "text": chunk,
                    "claim_ids": [f"{slug}-comm-{ci + 1}"],
                })
        if not paras and comm.get("description"):
            paras.append({
                "text": comm["description"],
                "claim_ids": [f"{slug}-comm-{ci + 1}"],
            })

        sec: dict[str, Any] = {"heading": comm["title"], "paragraphs": paras}
        if comm.get("location"):
            sec["location"] = comm["location"]
        if comm.get("audio_url"):
            sec["audio_url"] = comm["audio_url"]
        entry_sections.append(sec)

    entry: dict[str, Any] = {
        "schema_version": 2,
        "id": f"collectible-{slug}",
        "franchise": "tom-clancys-the-division",
        "continuity": "division-game-universe",
        "type": "collectible",
        "title": display_name,
        "slug": slug,
        "section": "collectibles",
        "summary": summary,
        "canon_status": "game-canon",
        "connection_status": "not-applicable",
        "spoiler_level": "minor",
        "collectible_subtype": category,
        "total_entries": total,
        "claims": claims,
        "sections": entry_sections,
        "relations": [],
        "verification": {
            "status": "draft",
            "last_reviewed": TODAY,
            "human_reviewed": False,
            "notes": (
                f"Auto-generated from Fandom wiki hub \"{wiki_path}\" "
                f"({WIKI_BASE}{quote(wiki_path.replace(' ', '_'))}). "
                f"{total} collectible sub-entries with transcripts. Needs human review."
            ),
        },
    }
    return entry


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def get_output_path(entry: dict[str, Any]) -> Path:
    cat = entry.get("collectible_subtype", "comms")
    return ENTRIES_ROOT / "collectibles" / cat / f"{entry['slug']}.json"


def write_entry(entry: dict[str, Any], *, dry_run: bool = False) -> Path:
    out = get_output_path(entry)
    if dry_run:
        print(f"  [DRY] {out}  ({entry['total_entries']} comms)")
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    print(f"  -> {out.name}  ({entry['total_entries']} comms)")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scrape_hub(wiki_path: str, display_name: str, category: str,
               *, dry_run: bool = False) -> dict[str, Any] | None:
    print(f"\n  {display_name}")
    html = fetch_hub_html(wiki_path)
    if not html:
        print(f"  SKIP: no HTML")
        return None
    print(f"  HTML: {len(html)} chars")
    comms = parse_comms_from_text(html_to_text(html))
    print(f"  Parsed: {len(comms)} comms")
    if comms:
        print(f"    First: {comms[0]['title']}")
        if len(comms) > 1:
            print(f"    Last:  {comms[-1]['title']}")
    entry = build_hub_entry(wiki_path, display_name, category, comms)
    write_entry(entry, dry_run=dry_run)
    return entry


def main() -> None:
    p = argparse.ArgumentParser(description="Scrape Division wiki hub pages")
    p.add_argument("--hub", help="Scrape one hub (wiki_path)")
    p.add_argument("--all-comms", action="store_true", help="Scrape all registered hubs")
    p.add_argument("--list-hubs", action="store_true", help="List registered hubs")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.list_hubs:
        for wp, dn, cat in HUB_REGISTRY:
            print(f"  {cat:20s} {dn}")
        print(f"\n  Total: {len(HUB_REGISTRY)} hubs")
        return

    if args.hub:
        matches = [(wp, dn, cat) for wp, dn, cat in HUB_REGISTRY if wp == args.hub]
        if not matches:
            print(f"Hub '{args.hub}' not in registry"); sys.exit(1)
        wp, dn, cat = matches[0]
        scrape_hub(wp, dn, cat, dry_run=args.dry_run)
        return

    if args.all_comms:
        total_entries = 0
        ok = 0
        for idx, (wp, dn, cat) in enumerate(HUB_REGISTRY, 1):
            print(f"\n[{idx}/{len(HUB_REGISTRY)}]")
            entry = scrape_hub(wp, dn, cat, dry_run=args.dry_run)
            if entry:
                ok += 1
                total_entries += entry["total_entries"]
            time.sleep(0.5)
        print(f"\n{'='*50}")
        print(f"DONE: {ok}/{len(HUB_REGISTRY)} hubs scraped")
        print(f"Total comm sub-entries: {total_entries}")
        return

    p.print_help()


if __name__ == "__main__":
    main()
