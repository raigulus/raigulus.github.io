#!/usr/bin/env python3
"""Generate landing-data.json for the Raigulus landing page.

Scans the repo to produce a single JSON blob the front-end fetches:
  - Total guide count (from sitemap.xml)
  - Exotics count (from division-2/exotics/)
  - Patches count (from division-2/patches/)
  - Latest patch version + title
  - Today's loot summary (from escalation-target-loot.json)
  - Server operational status (from division-2-status.json)
  - Last updated timestamp
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
OUT = DATA / "landing-data.json"
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
DISCORD_LOOT_CHANNEL_ID = "1528506012900917268"


def count_sitemap_urls() -> int:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return 0
    text = sitemap.read_text(encoding="utf-8")
    return len(re.findall(r"<loc>", text))


def count_exotics() -> int:
    exotics_dir = ROOT / "division-2" / "exotics"
    if not exotics_dir.is_dir():
        return 0
    return sum(1 for d in exotics_dir.iterdir() if d.is_dir() and (d / "index.html").exists())


def count_patches() -> int:
    patches_dir = ROOT / "division-2" / "patches"
    if not patches_dir.is_dir():
        return 0
    return sum(1 for d in patches_dir.iterdir() if d.is_dir() and (d / "index.html").exists())


def latest_patch() -> dict:
    patches_dir = ROOT / "division-2" / "patches"
    if not patches_dir.is_dir():
        return {"slug": "", "title": "", "version": ""}

    candidates = []
    for d in patches_dir.iterdir():
        if not d.is_dir() or not (d / "index.html").exists():
            continue
        html = (d / "index.html").read_text(encoding="utf-8")
        title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else d.name.replace("-", " ").title()

        # Extract version like Y8S3, Y7S1, TU4
        ver_match = re.search(r"(Y\d+S\d+|TU\d+(?:\.\d+)?)", title, re.IGNORECASE)
        version = ver_match.group(0).upper() if ver_match else ""

        year_match = re.search(r"\[(\d{4})\]", title)
        year = int(year_match.group(1)) if year_match else 0

        ver_priority = 0
        if version.startswith("Y"):
            ym = re.match(r"Y(\d+)S(\d+)", version)
            if ym:
                ver_priority = int(ym.group(1)) * 100 + int(ym.group(2))
        elif version.startswith("TU"):
            tm = re.match(r"TU(\d+)", version)
            if tm:
                ver_priority = int(tm.group(1))

        candidates.append({
            "slug": d.name,
            "title": title,
            "version": version,
            "sort_key": (year, ver_priority),
        })

    if not candidates:
        return {"slug": "", "title": "", "version": ""}

    best = max(candidates, key=lambda c: c["sort_key"])
    return {"slug": best["slug"], "title": best["title"], "version": best["version"]}


def loot_summary() -> dict:
    loot_file = DATA / "escalation-target-loot.json"
    if not loot_file.exists():
        return {"active": False}
    data = json.loads(loot_file.read_text(encoding="utf-8"))
    if data.get("status") != "ok":
        return {"active": False}
    missions = data.get("missions", [])
    vendor = data.get("vendor_caches", [])
    return {
        "active": True,
        "date": data.get("date", ""),
        "rotation": data.get("rotation", ""),
        "mission_count": len(missions),
        "vendor_count": len(vendor),
        "next_update": data.get("next_expected_update", ""),
    }


def server_status() -> dict:
    status_file = DATA / "division-2-status.json"
    if not status_file.exists():
        return {"operational": True}
    data = json.loads(status_file.read_text(encoding="utf-8"))
    return {
        "operational": data.get("status") == "operational",
        "last_checked": data.get("last_checked", ""),
    }


def discord_member_count() -> int:
    if not DISCORD_BOT_TOKEN or not DISCORD_LOOT_CHANNEL_ID:
        return 0
    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{DISCORD_LOOT_CHANNEL_ID}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "User-Agent": "RaigulusBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ch = json.loads(resp.read().decode("utf-8"))
            guild_id = ch.get("guild_id")
        if not guild_id:
            return 0
        req2 = urllib.request.Request(
            f"https://discord.com/api/v10/guilds/{guild_id}?with_counts=true",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "User-Agent": "RaigulusBot/1.0"},
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            data = json.loads(resp2.read().decode("utf-8"))
            return data.get("approximate_member_count", 0)
    except Exception:
        return 0


def next_reset_utc() -> str:
    now = datetime.now(timezone.utc)
    reset_hour = 7
    if now.hour >= reset_hour:
        from datetime import timedelta
        next_day = now + timedelta(days=1)
        return next_day.strftime("%Y-%m-%dT07:00:00Z")
    return now.strftime(f"%Y-%m-%dT{reset_hour:02d}:00:00Z")


def main() -> None:
    now = datetime.now(timezone.utc)

    landing = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "total_guides": count_sitemap_urls(),
            "exotics": count_exotics(),
            "patches": count_patches(),
        },
        "latest_patch": latest_patch(),
        "loot": loot_summary(),
        "server": server_status(),
        "discord_members": discord_member_count(),
        "next_reset_utc": next_reset_utc(),
    }

    OUT.write_text(
        json.dumps(landing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"landing-data.json generated: {landing['stats']['total_guides']} guides, "
          f"{landing['stats']['exotics']} exotics, {landing['stats']['patches']} patches")


if __name__ == "__main__":
    main()
