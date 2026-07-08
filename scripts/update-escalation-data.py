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
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://raigulus.github.io"
HOST = "raigulus.github.io"
USER_AGENT = "RaigulusGuideDataBot/1.0 (+https://raigulus.github.io/division-2/server-status/)"
PRIMARY_SOURCE_URL = os.environ.get("ESCALATION_PRIMARY_SOURCE_URL", "").strip()
DAILY_SNAPSHOT_RESET_HOUR_UTC = 10
DAILY_SNAPSHOT_GRACE_MINUTES = 20
DIVISION2_STATUS_SOURCE_LABEL = "Official Ubisoft service status"
DIVISION2_STATUS_SOURCE_URL = "https://ubistatic-a.akamaihd.net/0115/tctd2/status.html"
DIVISION2_STATUS_API_URL = (
    "https://public-ubiservices.ubi.com/v1/applications/gameStatuses?"
    "applicationIds=6c6b8cd7-d901-4cd5-8279-07ba92088f06,"
    "6f220906-8a24-4b6a-a356-db5498501572,"
    "7d9bbf16-d76d-43e1-9e82-1e64b4dd5543,"
    "42e81559-1fbc-42cd-bd12-e42460f9aaeb"
)
UBISOFT_PUBLIC_APP_ID = "5c5d3b21-e1fc-4460-9213-87b4cd440d44"


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


def fetch_json(url, timeout=15):
    request = urllib.request.Request(
        add_cache_buster(url),
        headers={
            "User-Agent": USER_AGENT,
            "Ubi-AppId": UBISOFT_PUBLIC_APP_ID,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


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
        "last_checked": "",
        "parsed_at": "",
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


def parse_snapshot_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except ValueError:
        return None


def expected_snapshot_update_time(checked_at):
    return checked_at.replace(
        hour=DAILY_SNAPSHOT_RESET_HOUR_UTC,
        minute=DAILY_SNAPSHOT_GRACE_MINUTES,
        second=0,
        microsecond=0,
    )


def apply_target_loot_freshness(data, checked_at):
    if data.get("status") == "error":
        data.setdefault("snapshot_note", "Automated source check failed; showing the latest saved snapshot.")
        return data

    reset_time = expected_snapshot_update_time(checked_at)
    data["next_expected_update"] = "Around 10:00 UTC / 13:00 TRT"
    snapshot_date = parse_snapshot_date(data.get("date"))
    today = checked_at.date()

    if not snapshot_date:
        data["status"] = "pending"
        data["snapshot_note"] = "Waiting for the first dated daily loot snapshot."
        return data

    if snapshot_date < today:
        if checked_at < reset_time:
            data["status"] = "pending"
            data["snapshot_note"] = (
                "Daily reset window has not arrived yet; showing the latest available snapshot."
            )
        else:
            data["status"] = "stale"
            data["snapshot_note"] = (
                "Checked after the expected daily reset window, but the source still returned an older snapshot."
            )
        return data

    data["status"] = "ok"
    data["snapshot_note"] = "Current dated loot snapshot is available."
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
        "last_checked",
        "parsed_at",
        "status",
        "fetched_at",
        "error",
        "snapshot_note",
        "next_expected_update",
    }
    sanitized = {key: value for key, value in data.items() if key in allowed_keys}
    data.clear()
    data.update(sanitized)
    return data


def read_existing_status(site_dir):
    path = site_dir / "assets" / "data" / "division-2-status.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def normalize_ubisoft_platform_status(status, is_maintenance):
    if is_maintenance:
        return "maintenance"
    status = (status or "").strip().lower()
    if status == "online":
        return "operational"
    if status == "interrupted":
        return "outage"
    if status == "degraded":
        return "problems"
    if status == "maintenance":
        return "maintenance"
    return "unknown"


def aggregate_platform_status(platforms):
    values = set(platforms.values())
    for status in ("outage", "maintenance", "problems", "unknown", "pending"):
        if status in values:
            return status
    if values and values == {"operational"}:
        return "operational"
    return "unknown"


def status_message(status):
    if status == "operational":
        return "Servers appear operational based on the checked official source."
    if status == "maintenance":
        return "Maintenance is indicated by the checked official source."
    if status == "problems":
        return "Service problems are indicated by the checked official source."
    if status == "outage":
        return "An outage is indicated by the checked official source."
    if status == "stale":
        return "Latest automated status check failed; showing stale data."
    return "Status could not be confirmed from the checked official source."


def sanitize_status_data(data):
    allowed_keys = {"status", "platforms", "message", "last_checked", "fetched_at", "source_label", "source_url", "error"}
    sanitized = {key: value for key, value in data.items() if key in allowed_keys}
    platforms = sanitized.get("platforms") if isinstance(sanitized.get("platforms"), dict) else {}
    status = str(sanitized.get("status") or "unknown").lower()
    sanitized["platforms"] = {
        "pc": str(platforms.get("pc") or status).lower(),
        "playstation": str(platforms.get("playstation") or status).lower(),
        "xbox": str(platforms.get("xbox") or status).lower(),
    }
    sanitized["status"] = status
    sanitized.setdefault("message", status_message(status))
    sanitized.setdefault("last_checked", "Waiting for first automated check")
    sanitized.setdefault("fetched_at", "")
    sanitized["source_label"] = DIVISION2_STATUS_SOURCE_LABEL
    sanitized["source_url"] = DIVISION2_STATUS_SOURCE_URL
    data.clear()
    data.update(sanitized)
    return data


def fetch_division2_status(existing):
    try:
        payload = fetch_json(DIVISION2_STATUS_API_URL, timeout=15)
        game_statuses = payload.get("gameStatuses")
        if not isinstance(game_statuses, list) or not game_statuses:
            raise ValueError("No gameStatuses returned")
        platforms = {}
        platform_names = {"pc": "pc", "orbis": "playstation", "durango": "xbox"}
        for item in game_statuses:
            key = platform_names.get(str(item.get("platformType", "")).lower())
            if not key:
                continue
            platforms[key] = normalize_ubisoft_platform_status(item.get("status"), item.get("isMaintenance"))
        if not platforms:
            raise ValueError("No known platforms returned")
        aggregate = aggregate_platform_status(platforms)
        for key in ("pc", "playstation", "xbox"):
            platforms.setdefault(key, aggregate)
        data = {
            "status": aggregate,
            "platforms": platforms,
            "message": status_message(aggregate),
            "source_label": DIVISION2_STATUS_SOURCE_LABEL,
            "source_url": DIVISION2_STATUS_SOURCE_URL,
        }
        return data, None
    except Exception as error:
        data = dict(existing) if existing else {}
        data.setdefault("platforms", {"pc": "unknown", "playstation": "unknown", "xbox": "unknown"})
        data["status"] = "stale"
        data["message"] = status_message("stale")
        data["source_label"] = DIVISION2_STATUS_SOURCE_LABEL
        data["source_url"] = DIVISION2_STATUS_SOURCE_URL
        return data, f"{type(error).__name__}: {error}"


def render_live_html(data, marker, heading, intro, mission_heading, cache_heading):
    def esc(value):
        return html.escape(str(value or ""), quote=True)

    missions = data.get("missions") or []
    caches = data.get("vendor_caches") or []
    last_updated = data.get("last_checked") or data.get("last_updated") or data.get("fetched_at") or "Waiting for first automated check"
    date_label = data.get("date") or "Current target loot date"
    mission_rows = "\n".join(
        f"<tr><th>{esc(item.get('mission', 'Mission'))}</th><td>{esc(item.get('loot', 'Target loot pending'))}</td></tr>"
        for item in missions
    ) or '<tr><th>Snapshot</th><td>Waiting for the first automated source check.</td></tr>'
    cache_rows = "\n".join(
        f"<tr><th>{esc(item.get('type', 'Cache'))}</th><td>{esc(item.get('item', 'Pending'))}</td></tr>"
        for item in caches
    ) or '<tr><th>Vendor Caches</th><td>Waiting for the first automated source check.</td></tr>'
    source_updated_row = ""
    if data.get("last_updated"):
        source_updated_row = f"<tr><th>Source snapshot updated</th><td>{esc(data.get('last_updated'))}</td></tr>"
    note_row = ""
    if data.get("snapshot_note"):
        note_row = f"<tr><th>Update note</th><td>{esc(data.get('snapshot_note'))}</td></tr>"
    return f"""<!-- {marker}-live-start -->
        <h2>{esc(heading)}</h2>
        <p>{esc(intro)}</p>
        <table class="facts">
          <tr><th>Date</th><td>{esc(date_label)}</td></tr>
          <tr><th>Mission rotation</th><td>{esc(data.get('rotation') or 'Weekly mission rotation')}</td></tr>
          <tr><th>Target loot cadence</th><td>Daily</td></tr>
          <tr><th>Status</th><td>{esc(data.get('status') or 'pending')}</td></tr>
          <tr><th>Last checked</th><td>{esc(last_updated)}</td></tr>
          {source_updated_row}
          <tr><th>Expected update window</th><td>{esc(data.get('next_expected_update') or 'Around 10:00 UTC / 13:00 TRT')}</td></tr>
          {note_row}
          <tr><th>Snapshot</th><td>Automated daily loot check</td></tr>
        </table>
        <h2>{esc(mission_heading)}</h2>
        <table class="facts">{mission_rows}</table>
        <h2>{esc(cache_heading)}</h2>
        <table class="facts">{cache_rows}</table>
<!-- {marker}-live-end -->"""


def render_status_live_html(data):
    def esc(value):
        return html.escape(str(value or ""), quote=True)

    status = str(data.get("status") or "pending").lower()
    platforms = data.get("platforms") if isinstance(data.get("platforms"), dict) else {}
    labels = {
        "operational": "Operational",
        "maintenance": "Maintenance",
        "problems": "Problems",
        "outage": "Outage",
        "stale": "Stale",
        "pending": "Pending",
        "unknown": "Unknown",
    }
    platform_rows = "\n".join(
        f"<tr><th>{esc(label)}</th><td>{esc(labels.get(str(platforms.get(key, status)).lower(), 'Unknown'))}</td></tr>"
        for key, label in [("pc", "PC"), ("playstation", "PlayStation"), ("xbox", "Xbox")]
    )
    error_row = ""
    if data.get("error"):
        error_row = f"<tr><th>Last error</th><td>{esc(data.get('error'))}</td></tr>"
    lead = (
        "Servers appear operational. Check today's loot before you play."
        if status == "operational"
        else "Servers do not look clean right now based on public Ubisoft status pages."
    )
    return f"""<!-- division-2-status-live-start -->
        <h2>Current Server Status</h2>
        <p>{esc(lead)}</p>
        <table class="facts">
          <tr><th>Status</th><td><span class="status-chip status-{esc(status)}">{esc(labels.get(status, 'Unknown'))}</span></td></tr>
          <tr><th>Message</th><td>{esc(data.get('message') or status_message(status))}</td></tr>
          <tr><th>Last checked</th><td>{esc(data.get('last_checked') or 'Waiting for first automated check')}</td></tr>
          <tr><th>Source</th><td><a href="{esc(data.get('source_url') or DIVISION2_STATUS_SOURCE_URL)}">{esc(data.get('source_label') or DIVISION2_STATUS_SOURCE_LABEL)}</a></td></tr>
          <tr><th>ETA</th><td>Official ETA not detected from the checked source.</td></tr>
          {error_row}
        </table>
        <h2>Platform Status</h2>
        <table class="facts">{platform_rows}</table>
<!-- division-2-status-live-end -->"""


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


def update_status_page(site_dir, data):
    return update_page_block(
        site_dir,
        Path("division-2/server-status/index.html"),
        "division-2-status",
        render_status_live_html(data),
    )


def update_sitemap(site_dir):
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.exists():
        return False
    today = utc_now().date().isoformat()
    content = sitemap.read_text(encoding="utf-8")
    updated = content
    for url in [
        f"{BASE_URL}/division-2/loot/",
        f"{BASE_URL}/division-2/server-status/",
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
                f"{BASE_URL}/division-2/server-status/",
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
    checked_at = utc_now()
    exit_code = 0
    data = {}

    if not PRIMARY_SOURCE_URL:
        print("Primary Escalation source URL is not configured; skipping Escalation source fetch.")
    else:
        existing = read_existing(input_path, site_dir)
        data, error = fetch_primary(existing)
        data["fetched_at"] = checked_at.isoformat()
        data["last_checked"] = checked_at.strftime("%Y-%m-%d %H:%M UTC")
        if not data.get("parsed_at"):
            data["parsed_at"] = checked_at.isoformat()
        if error:
            data["error"] = error
        else:
            data.pop("error", None)
        apply_target_loot_freshness(data, checked_at)
        sanitize_public_data(data)

        if input_path:
            write_json(input_path, data)
            print(f"Wrote {input_path}")
        write_json(site_dir / "assets" / "data" / "escalation-target-loot.json", data)
        print(f"Wrote {site_dir / 'assets' / 'data' / 'escalation-target-loot.json'}")
        updated_pages = update_pages(site_dir, data)
        if updated_pages:
            print(f"Updated {updated_pages} guide hub live blocks")
        if data.get("status") == "error":
            exit_code = 1

    status_existing = read_existing_status(site_dir)
    status_data, status_error = fetch_division2_status(status_existing)
    checked_at = utc_now()
    status_data["fetched_at"] = checked_at.isoformat()
    status_data["last_checked"] = checked_at.strftime("%Y-%m-%d %H:%M UTC")
    if status_error:
        status_data["error"] = status_error
    else:
        status_data.pop("error", None)
    sanitize_status_data(status_data)
    write_json(site_dir / "assets" / "data" / "division-2-status.json", status_data)
    print(f"Wrote {site_dir / 'assets' / 'data' / 'division-2-status.json'}")
    if update_status_page(site_dir, status_data):
        print("Updated Division 2 server status live block")

    update_sitemap(site_dir)
    if args.submit_indexnow:
        submit_indexnow(site_dir)
    if status_data.get("status") == "stale" and status_error:
        exit_code = max(exit_code, 1)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
