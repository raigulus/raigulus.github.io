#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://raigulus.github.io"
HOST = "raigulus.github.io"
USER_AGENT = "RaigulusEscalationBot/1.0 (+https://raigulus.github.io/division-2/escalation/)"
PRIMARY_SOURCE_URL = os.environ.get("ESCALATION_PRIMARY_SOURCE_URL", "").strip()


def utc_now():
    return datetime.now(timezone.utc)


def add_cache_buster(url):
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append(("raigulus_cache_bust", str(int(utc_now().timestamp()))))
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


def fetch_text(url, timeout=15):
    request = urllib.request.Request(
        add_cache_buster(url),
        headers={
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def repo_paths():
    cwd = Path.cwd()
    if (cwd / "work" / "input").exists():
        input_path = cwd / "work" / "input" / "escalation-target-loot.json"
        site_dir = Path(os.environ.get("RAIGULUS_SITE_DIR", cwd / "work" / "deploy" / "raigulus.github.io"))
    else:
        input_path = None
        site_dir = cwd
    return input_path, site_dir


def parse_primary_source_text(text):
    data = {
        "date": "",
        "rotation": "",
        "missions": [],
        "vendor_caches": [],
        "last_updated": "",
        "status": "ok",
    }
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower == "missions:":
            section = "missions"
            continue
        if lower == "vendor caches:":
            section = "vendor_caches"
            continue
        if line.startswith("Date:"):
            data["date"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Rotation:"):
            data["rotation"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Last updated:"):
            data["last_updated"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Source:"):
            continue
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            if section == "missions":
                data["missions"].append({"mission": key.strip(), "loot": value.strip()})
            elif section == "vendor_caches":
                data["vendor_caches"].append({"type": key.strip(), "item": value.strip()})
    return data


def read_existing(input_path, site_dir):
    candidates = []
    if input_path:
        candidates.append(input_path)
    candidates.append(site_dir / "assets" / "data" / "escalation-target-loot.json")
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return {}


def fetch_primary(existing):
    if not PRIMARY_SOURCE_URL:
        data = dict(existing) if existing else {}
        data.setdefault("missions", [])
        data.setdefault("vendor_caches", [])
        sanitize_public_data(data)
        data["status"] = "stale" if data.get("missions") else "pending"
        return data, "Primary source URL is not configured"
    try:
        text = fetch_text(PRIMARY_SOURCE_URL)
        data = parse_primary_source_text(text)
        return data, None
    except Exception as error:
        data = dict(existing) if existing else {}
        data.setdefault("missions", [])
        data.setdefault("vendor_caches", [])
        sanitize_public_data(data)
        data["status"] = "stale" if data.get("missions") else "error"
        return data, f"{type(error).__name__}: {error}"


def sanitize_public_data(data):
    allowed_keys = {
        "date",
        "rotation",
        "missions",
        "vendor_caches",
        "last_updated",
        "status",
        "fetched_at",
        "error",
    }
    sanitized = {key: value for key, value in data.items() if key in allowed_keys}
    data.clear()
    data.update(sanitized)
    return data


def render_live_html(data, marker, heading, intro, mission_heading, cache_heading):
    def esc(value):
        return html.escape(str(value or ""), quote=True)

    missions = data.get("missions") or []
    caches = data.get("vendor_caches") or []
    last_updated = data.get("last_updated") or data.get("fetched_at") or "Waiting for first automated check"
    date_label = data.get("date") or "Current target loot date"
    mission_rows = "\n".join(
        f"<tr><th>{esc(item.get('mission', 'Mission'))}</th><td>{esc(item.get('loot', 'Target loot pending'))}</td></tr>"
        for item in missions
    ) or '<tr><th>Snapshot</th><td>Waiting for the first automated source check.</td></tr>'
    cache_rows = "\n".join(
        f"<tr><th>{esc(item.get('type', 'Cache'))}</th><td>{esc(item.get('item', 'Pending'))}</td></tr>"
        for item in caches
    ) or '<tr><th>Vendor Caches</th><td>Waiting for the first automated source check.</td></tr>'
    return f"""<!-- {marker}-live-start -->
        <h2>{esc(heading)}</h2>
        <p>{esc(intro)}</p>
        <table class="facts">
          <tr><th>Date</th><td>{esc(date_label)}</td></tr>
          <tr><th>Mission rotation</th><td>{esc(data.get('rotation') or 'Weekly mission rotation')}</td></tr>
          <tr><th>Target loot cadence</th><td>Daily</td></tr>
          <tr><th>Status</th><td>{esc(data.get('status') or 'pending')}</td></tr>
          <tr><th>Last checked</th><td>{esc(last_updated)}</td></tr>
          <tr><th>Snapshot</th><td>Automated daily loot check</td></tr>
        </table>
        <h2>{esc(mission_heading)}</h2>
        <table class="facts">{mission_rows}</table>
        <h2>{esc(cache_heading)}</h2>
        <table class="facts">{cache_rows}</table>
<!-- {marker}-live-end -->"""


def update_page_block(site_dir, relative_page, marker, html_block):
    page = site_dir / relative_page
    if not page.exists():
        return False
    content = page.read_text(encoding="utf-8")
    pattern = re.compile(rf"<!-- {re.escape(marker)}-live-start -->.*?<!-- {re.escape(marker)}-live-end -->", re.S)
    if not pattern.search(content):
        return False
    page.write_text(pattern.sub(html_block, content), encoding="utf-8")
    return True


def update_pages(site_dir, data):
    blocks = [
        (
            Path("division-2/escalation/index.html"),
            "escalation",
            render_live_html(
                data,
                "escalation",
                "Escalation Loot Today",
                "Current Escalation loot snapshot. Mission locations can stay weekly, while target loot is checked for daily changes.",
                "Current Escalation Mission Target Loot",
                "Escalation Requisition Vendor Caches",
            ),
        ),
        (
            Path("division-2/loot/index.html"),
            "loot",
            render_live_html(
                data,
                "loot",
                "Targeted Loot Today",
                "Daily loot snapshot for players checking Division 2 loot today, targeted loot, loot map context, and farming routes.",
                "Current Targeted Loot Snapshot",
                "Current Cache Snapshot",
            ),
        ),
        (
            Path("division-2/prototype-gear/index.html"),
            "prototype-gear",
            render_live_html(
                data,
                "prototype-gear",
                "Prototype Gear and Vendor Snapshot",
                "Current cache and loot snapshot for Prototype Gear, Escalation vendor checks, and gear cache planning.",
                "Current Escalation Mission Loot",
                "Prototype Gear and Vendor Caches",
            ),
        ),
    ]
    changed = 0
    for page, marker, html_block in blocks:
        if update_page_block(site_dir, page, marker, html_block):
            changed += 1
    return changed


def update_sitemap(site_dir):
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.exists():
        return False
    today = utc_now().date().isoformat()
    content = sitemap.read_text(encoding="utf-8")
    updated = content
    for url in [
        f"{BASE_URL}/division-2/loot/",
        f"{BASE_URL}/division-2/escalation/",
        f"{BASE_URL}/division-2/prototype-gear/",
    ]:
        target = re.escape(url)
        pattern = re.compile(rf"(<loc>{target}</loc><lastmod>)([^<]+)(</lastmod>)")
        updated = pattern.sub(rf"\g<1>{today}\g<3>", updated)
    if updated != content:
        sitemap.write_text(updated, encoding="utf-8")
        return True
    return False


def find_indexnow_key(site_dir):
    for path in site_dir.glob("*.txt"):
        if re.fullmatch(r"[a-f0-9]{32}\.txt", path.name):
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return ""


def submit_indexnow(site_dir):
    key = find_indexnow_key(site_dir)
    if not key:
        print("IndexNow skipped: key file not found")
        return
    payload = json.dumps(
        {
            "host": HOST,
            "key": key,
            "urlList": [
                f"{BASE_URL}/division-2/loot/",
                f"{BASE_URL}/division-2/escalation/",
                f"{BASE_URL}/division-2/prototype-gear/",
                f"{BASE_URL}/division-2/",
                f"{BASE_URL}/sitemap.xml",
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"IndexNow: {response.status} {response.reason}")
    except urllib.error.HTTPError as error:
        print(f"IndexNow error: {error.code} {error.reason}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Fetch public The Division 2 Escalation source data for Raigulus.")
    parser.add_argument("--submit-indexnow", action="store_true", help="Submit updated Escalation URLs to IndexNow.")
    args = parser.parse_args()

    input_path, site_dir = repo_paths()
    if not PRIMARY_SOURCE_URL:
        print("Primary Escalation source URL is not configured; skipping source fetch.")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            return 2
        return 0
    existing = read_existing(input_path, site_dir)
    data, error = fetch_primary(existing)
    data["fetched_at"] = utc_now().isoformat()
    if error:
        data["error"] = error
    else:
        data.pop("error", None)
    sanitize_public_data(data)

    if input_path:
        write_json(input_path, data)
        print(f"Wrote {input_path}")
    write_json(site_dir / "assets" / "data" / "escalation-target-loot.json", data)
    print(f"Wrote {site_dir / 'assets' / 'data' / 'escalation-target-loot.json'}")
    updated_pages = update_pages(site_dir, data)
    if updated_pages:
        print(f"Updated {updated_pages} guide hub live blocks")
    update_sitemap(site_dir)
    if args.submit_indexnow:
        submit_indexnow(site_dir)
    if data.get("status") == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
