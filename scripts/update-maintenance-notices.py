#!/usr/bin/env python3
"""Poll Steam News for Division 2 maintenance notices and refresh the
Official Maintenance Notices block on the server-status page.

Copyright rules enforced here (do not weaken):
- Never copy item body text onto the page. Only facts travel:
  notice title, post date, and the link to the full post.
- The visible summary is always our own sentence about the notice,
  never a quote or close paraphrase of the announcement.
- The block always carries a default state ("no active maintenance
  detected in the latest official notices") so an old notice is never
  presented as current status. Live state comes from the hourly
  Ubisoft status check, not from this feed.
- Files are rewritten only when the latest matching notice changes,
  so the workflow commits only on real change.
"""

import html
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPID = "2221490"
FEED_URL = (
    "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    "?appid=2221490&count=20&maxlength=500&format=json"
)
USER_AGENT = "RaigulusGuideDataBot/1.0 (+https://raigulus.github.io/division-2/server-status/)"
KEYWORDS = (
    "maintenance",
    "downtime",
    "outage",
    "degraded",
    "server issue",
    "servers are back",
    "emergency maintenance",
)
JSON_PATH = ROOT / "assets" / "data" / "division-2-maintenance.json"
PAGE_PATH = ROOT / "division-2" / "server-status" / "index.html"
START = "<!-- division-2-maintenance-start -->"
END = "<!-- division-2-maintenance-end -->"


def esc(value):
    return html.escape(str(value), quote=True)


def fetch_feed():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def latest_notice(items):
    best = None
    for it in items or []:
        text = ((it.get("title") or "") + " " + (it.get("contents") or "")).lower()
        if not any(k in text for k in KEYWORDS):
            continue
        if best is None or it.get("date", 0) > best.get("date", 0):
            best = it
    return best


def fmt_date(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")


def render_block(notice):
    """Our own sentences only: title/date/link facts, default state always present."""
    if not notice:
        return (
            "<h2>Official Maintenance Notices</h2>\n"
            "<p>No maintenance-related official notices found in the recent "
            "Steam News feed, and no active maintenance is currently detected. "
            "Ubisoft's own status source above remains the authority during an outage.</p>"
        )
    title = notice.get("title", "Untitled notice")
    date = fmt_date(notice.get("date", 0))
    url = notice.get("url", "https://store.steampowered.com/news/app/2221490")
    return (
        "<h2>Official Maintenance Notices</h2>\n"
        "<p>No active maintenance is currently detected in the latest official "
        "notices. The most recent related notice is summarized below "
        "in our own words; read the full text at the source link.</p>\n"
        '<table class="facts">\n'
        "<tr><th>Notice</th><td>" + esc(title) + "</td></tr>\n"
        "<tr><th>Posted</th><td>" + esc(date) + " UTC</td></tr>\n"
        '<tr><th>Source</th><td><a href="' + esc(url) + '">Steam News post by Ubisoft</a></td></tr>\n'
        "</table>"
    )


def main():
    try:
        feed = fetch_feed()
    except Exception as exc:  # keep last good state on fetch failure
        print(f"Steam News fetch failed, keeping existing state: {exc}")
        return 0
    notice = latest_notice((feed.get("appnews") or {}).get("newsitems"))
    gid = notice.get("gid") if notice else None

    prev = {}
    if JSON_PATH.exists():
        try:
            prev = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    if prev.get("gid") == gid:
        print("No new maintenance notice.")
        return 0

    record = {
        "appid": APPID,
        "gid": gid,
        "title": notice.get("title") if notice else None,
        "date": fmt_date(notice.get("date", 0)) if notice else None,
        "url": notice.get("url") if notice else None,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    JSON_PATH.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    page = PAGE_PATH.read_text(encoding="utf-8")
    if START not in page or END not in page:
        raise SystemExit("maintenance markers missing from server-status page")
    before, rest = page.split(START, 1)
    _, after = rest.split(END, 1)
    PAGE_PATH.write_text(before + START + "\n" + render_block(notice) + "\n" + END + after, encoding="utf-8")
    print(f"Maintenance block updated (gid={gid}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
