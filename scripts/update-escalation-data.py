#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://raigulus.github.io"
HOST = "raigulus.github.io"
USER_AGENT = "RaigulusEscalationBot/1.0 (+https://raigulus.github.io/division-2/escalation/)"
PROTOTRACK_STATIC_TEXT_URL = os.environ.get(
    "PROTOTRACK_STATIC_URL",
    "https://prototrack.gg/target-loot/target-loot-current.txt",
)
PROTOTRACK_PAGE_URL = "https://prototrack.gg/target-loot/target-loot.php"
HIDEP_URL = os.environ.get("HIDEP_TARGET_LOOT_URL", "https://hi-dep.github.io/division2/")
REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/Division2/search.rss?"
    + urllib.parse.urlencode({"q": '"Daily Escalation Missions" "Targeted Loot"', "restrict_sr": "1", "sort": "new"}),
    "https://www.reddit.com/r/thedivision/search.rss?"
    + urllib.parse.urlencode({"q": '"Daily Escalation Missions" "Targeted Loot"', "restrict_sr": "1", "sort": "new"}),
]


def utc_now():
    return datetime.now(timezone.utc)


def fetch_text(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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


def parse_prototrack_static(text):
    data = {
        "date": "",
        "rotation": "",
        "missions": [],
        "vendor_caches": [],
        "last_updated": "",
        "source": "ProtoTrack.gg",
        "source_url": PROTOTRACK_STATIC_TEXT_URL,
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
            data["source"] = line.split(":", 1)[1].strip() or "ProtoTrack.gg"
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
    try:
        text = fetch_text(PROTOTRACK_STATIC_TEXT_URL)
        data = parse_prototrack_static(text)
        data["raw_text"] = text
        return data, None
    except Exception as error:
        data = dict(existing) if existing else {}
        data.setdefault("missions", [])
        data.setdefault("vendor_caches", [])
        data.setdefault("source", "ProtoTrack.gg")
        data.setdefault("source_url", PROTOTRACK_STATIC_TEXT_URL)
        data["status"] = "stale" if data.get("missions") else "error"
        return data, f"{type(error).__name__}: {error}"


def fetch_reddit_sources():
    sources = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for url in REDDIT_RSS_URLS:
        try:
            xml_text = fetch_text(url, timeout=10)
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns)[:3]:
                title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link[@rel='alternate']", ns)
                link = link_el.attrib.get("href", "") if link_el is not None else url
                updated = entry.findtext("atom:updated", default="", namespaces=ns) or ""
                if "escalation" in title.lower() or "targeted loot" in title.lower():
                    sources.append({"name": title, "url": link, "updated": updated, "source": "Reddit RSS"})
        except Exception:
            continue
    return sources[:5]


def fetch_cross_checks():
    checks = []
    for name, url in [
        ("ProtoTrack page", PROTOTRACK_PAGE_URL),
        ("hi-dep Division 2 page", HIDEP_URL),
    ]:
        try:
            fetch_text(url, timeout=10)
            checks.append({"name": name, "url": url, "status": "reachable"})
        except Exception as error:
            checks.append({"name": name, "url": url, "status": f"unreachable: {type(error).__name__}"})
    return checks


def render_live_html(data):
    def esc(value):
        return html.escape(str(value or ""), quote=True)

    missions = data.get("missions") or []
    caches = data.get("vendor_caches") or []
    last_updated = data.get("last_updated") or data.get("fetched_at") or "Waiting for first automated check"
    date_label = data.get("date") or "Current rotation"
    mission_rows = "\n".join(
        f"<tr><th>{esc(item.get('mission', 'Mission'))}</th><td>{esc(item.get('loot', 'Target loot pending'))}</td></tr>"
        for item in missions
    ) or '<tr><th>Snapshot</th><td>Waiting for the first automated ProtoTrack check.</td></tr>'
    cache_rows = "\n".join(
        f"<tr><th>{esc(item.get('type', 'Cache'))}</th><td>{esc(item.get('item', 'Pending'))}</td></tr>"
        for item in caches
    ) or '<tr><th>Vendor Caches</th><td>Waiting for the first automated ProtoTrack check.</td></tr>'
    checks = data.get("cross_checks") or []
    check_items = "\n".join(
        f'<li><a href="{esc(item.get("url", "#"))}">{esc(item.get("name", "External source"))}</a>: {esc(item.get("status", "available"))}</li>'
        for item in checks
    ) or "<li>Cross-check sources are monitored by the automation when reachable.</li>"
    return f"""<!-- escalation-live-start -->
        <h2>Escalation Target Loot Today</h2>
        <p>This live snapshot is generated from public source checks. ProtoTrack is used as the primary source and is linked clearly instead of copied without attribution.</p>
        <table class="facts">
          <tr><th>Date</th><td>{esc(date_label)}</td></tr>
          <tr><th>Rotation</th><td>{esc(data.get('rotation') or 'Daily Escalation rotation')}</td></tr>
          <tr><th>Status</th><td>{esc(data.get('status') or 'pending')}</td></tr>
          <tr><th>Last checked</th><td>{esc(last_updated)}</td></tr>
          <tr><th>Primary source</th><td><a href="{esc(data.get('source_url') or PROTOTRACK_STATIC_TEXT_URL)}">ProtoTrack static text</a></td></tr>
        </table>
        <h2>Current Mission Target Loot</h2>
        <table class="facts">{mission_rows}</table>
        <h2>Escalation Requisition Vendor Caches</h2>
        <table class="facts">{cache_rows}</table>
        <h2>Cross-check Sources</h2>
        <ul class="pill-list">{check_items}</ul>
<!-- escalation-live-end -->"""


def update_page(site_dir, data):
    page = site_dir / "division-2" / "escalation" / "index.html"
    if not page.exists():
        return False
    content = page.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- escalation-live-start -->.*?<!-- escalation-live-end -->", re.S)
    if not pattern.search(content):
        return False
    page.write_text(pattern.sub(render_live_html(data), content), encoding="utf-8")
    return True


def update_sitemap(site_dir):
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.exists():
        return False
    today = utc_now().date().isoformat()
    content = sitemap.read_text(encoding="utf-8")
    target = re.escape(f"{BASE_URL}/division-2/escalation/")
    pattern = re.compile(rf"(<loc>{target}</loc><lastmod>)([^<]+)(</lastmod>)")
    updated = pattern.sub(rf"\g<1>{today}\g<3>", content)
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
                f"{BASE_URL}/division-2/escalation/",
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
    existing = read_existing(input_path, site_dir)
    data, error = fetch_primary(existing)
    data["fetched_at"] = utc_now().isoformat()
    if error:
        data["error"] = error
    else:
        data.pop("error", None)
    data["community_sources"] = fetch_reddit_sources()
    data["cross_checks"] = fetch_cross_checks()

    if input_path:
        write_json(input_path, data)
        print(f"Wrote {input_path}")
    write_json(site_dir / "assets" / "data" / "escalation-target-loot.json", data)
    print(f"Wrote {site_dir / 'assets' / 'data' / 'escalation-target-loot.json'}")
    if update_page(site_dir, data):
        print("Updated Escalation page live block")
    update_sitemap(site_dir)
    if args.submit_indexnow:
        submit_indexnow(site_dir)
    if data.get("status") == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
