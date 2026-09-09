#!/usr/bin/env python3
"""Generate the weekly "This Week in The Division 2" digest page.

Reads ONLY local snapshots (no new external fetches):
  - assets/data/escalation-target-loot.json (loot rotation + vendor caches)
  - assets/data/division-2-status.json (server state)
  - assets/data/division-2-maintenance.json (latest Steam notice, if any)
Manhunt week is date math from the Y8S3 season start (no fetch).

Staleness guards: if the loot snapshot is not from this Tuesday or its
status is not ok, the page says so instead of presenting stale loot.

Usage:
    python3 scripts/generate-weekly-digest.py [YYYY-MM-DD]  (default: today UTC)
"""

import html
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://raigulus.github.io"
SEASON_LABEL = "Y8S3 Red Horizon"
SEASON_START = date(2026, 8, 27)  # Thursday season launch
FIRST_TUESDAY = date(2026, 9, 1)  # weekly scout cadence anchors on Tuesdays


def esc(value):
    return html.escape(str(value), quote=True)


def load_json(name):
    p = ROOT / "assets" / "data" / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def tuesday_of(day):
    return day - timedelta(days=(day.weekday() - 1) % 7)


def fmt_day(d):
    return f"{d.strftime('%b')} {d.day}"


def main():
    today = datetime.now(timezone.utc).date()
    if len(sys.argv) > 1:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    tue = tuesday_of(today)
    mon = tue + timedelta(days=6)
    week_n = max(1, (tue - FIRST_TUESDAY).days // 7 + 2)
    slug = tue.isoformat()
    day_label = f"{fmt_day(tue)} – {mon.strftime('%b %d, %Y')}"
    short_label = f"{fmt_day(tue)}"

    loot = load_json("escalation-target-loot.json")
    status = load_json("division-2-status.json")
    maint = load_json("division-2-maintenance.json")

    try:
        loot_day = datetime.strptime(loot.get("date", ""), "%Y-%m-%d").date()
    except Exception:
        loot_day = None
    fresh = loot.get("status") == "ok" and loot_day is not None and tue <= loot_day <= tue + timedelta(days=6)
    missions = loot.get("missions") or []
    caches = loot.get("vendor_caches") or []

    if fresh:
        loot_rows = "".join(
            "<tr><th>" + esc(m.get("mission", "?")) + "</th><td>" + esc(m.get("loot", "?")) + "</td></tr>\n"
            for m in missions
        )
        loot_block = (
            "<h2>This Week's Targeted Loot</h2>\n"
            "<table class=\"facts\">\n" + loot_rows + "</table>\n"
            "<p>Full daily context: <a href=\"/division-2/loot/\">today's targeted loot hub</a>.</p>"
        )
    else:
        loot_block = (
            "<h2>This Week's Targeted Loot</h2>\n"
            "<p>This week's snapshot is still being verified — check "
            "<a href=\"/division-2/loot/\">today's targeted loot hub</a> for the live data.</p>"
        )
    if caches:
        cache_rows = "".join(
            "<tr><th>" + esc(c.get("type", "?")) + "</th><td>" + esc(c.get("item", "?")) + "</td></tr>\n"
            for c in caches
        )
        cache_block = (
            "<h2>Vendor Caches</h2>\n<table class=\"facts\">\n" + cache_rows + "</table>"
        )
    else:
        cache_block = ""

    st = (status.get("status") or "unknown").lower()
    st_text = "operational" if st == "operational" else esc(status.get("status") or "unknown")
    st_checked = esc(status.get("last_checked") or "recently")
    server_block = (
        "<h2>Servers &amp; Maintenance</h2>\n"
        "<p>Servers last reported <strong>" + st_text + "</strong> (" + st_checked + "). "
        "Live tracker: <a href=\"/division-2/server-status/\">server status</a>.</p>"
    )
    if maint.get("title"):
        server_block += (
            "<p>Latest related official notice: " + esc(maint["title"])
            + " (" + esc(maint.get("date", "")) + ") — "
            "<a href=\"" + esc(maint.get("url", "https://store.steampowered.com/news/app/2221490")) + "\">"
            "read the full post</a>.</p>"
        )

    title = f"This Week in Division 2 ({short_label}): Loot, Vendors & Reset [2026]"
    desc = (
        f"What resets in The Division 2 this week ({day_label}): targeted loot rotation, "
        f"vendor caches, {SEASON_LABEL} manhunt week {week_n}, server status and maintenance notes by Raigulus."
    )
    url = f"{BASE_URL}/division-2/this-week/{slug}/"

    faq = [
        ("What resets on Tuesday in The Division 2?",
         "Vendor stock, weekly projects, invasions and the mission rotation refresh around 08:00 UTC. "
         "Daily targeted loot refreshes every morning at the same hour. Live countdowns are on the reset times page."),
        ("Where is this week's targeted loot?",
         "The table above summarizes the weekly rotation. For the daily snapshot, use the targeted loot hub."),
    ]
    faq_visible = "".join(f"<dt>{esc(q)}</dt><dd>{esc(a)}</dd>\n" for q, a in faq)
    faq_json = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (esc(q), esc(a))
        for q, a in faq
    )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="blogarama-site-verification" content="blogarama-e6104966-f8b0-49ea-803a-101ddc0264b6">
  <link rel="canonical" href="{url}">
  <link rel="alternate" type="application/rss+xml" title="Raigulus Division 2 video feed" href="https://raigulus.github.io/feed.xml">
  <meta property="og:title" content="{esc(title)} | Raigulus">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta property="og:image" content="https://i.ytimg.com/vi/CTbj7jMF1rI/hqdefault.jpg">
  <meta property="twitter:image" content="https://i.ytimg.com/vi/CTbj7jMF1rI/hqdefault.jpg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
  <noscript><link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet"></noscript>
  <link rel="stylesheet" href="/assets/styles.css">
  <script src="/assets/search.js" defer></script>
  <script src="/assets/site.js" defer></script>
  <script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"{esc(title)}","description":"{esc(desc)}","url":"{url}","isPartOf":{{"@type":"WebSite","name":"Raigulus","url":"https://raigulus.github.io"}}}}</script>
  <script type="application/ld+json">{{"@context":"https://schema.org","@type":"FAQPage","url":"{url}","mainEntity":[{faq_json}]}}</script>
  <script type="application/ld+json">{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"https://raigulus.github.io/"}},{{"@type":"ListItem","position":2,"name":"The Division 2","item":"https://raigulus.github.io/division-2/"}},{{"@type":"ListItem","position":3,"name":"This Week","item":"https://raigulus.github.io/division-2/this-week/"}}]}}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">Raigulus</a>
    <nav>
      <a href="/division-2/">Division 2</a>
      <a href="/division-2/builds/">Builds</a>
      <a href="/division-2/build-maker/">Build Maker</a>
      <a href="/division-2/loot/">Loot</a>
      <a href="/division-2/server-status/">Server Status</a>
      <a href="/division-2/missions/">Missions</a>
      <a href="/division-2/escalation/">Escalation</a>
      <a href="/division-2/dark-zone-surge/">Dark Zone</a>
      <a href="/division-2/manhunts/">Manhunts</a>
      <a href="/division-2/bosses/">Bosses</a>
      <a href="/division-2/incursions-raids/">Incursions &amp; Raids</a>
      <a href="/division-2/pvp/">PvP</a>
      <a href="/lore/">Lore</a>
      <a href="/about/">About</a>
      <a href="/discord/">Discord</a>
      <a href="https://www.youtube.com/@raigulus">YouTube</a>
    </nav>
  </header>
  <main>
    <section class="section">
      <div class="content">
        <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/division-2/">The Division 2</a> / <span>This Week</span></nav>
        <p class="eyebrow">The Division 2 / This Week</p>
        <h1>This Week in The Division 2: {esc(day_label)}</h1>
        <p>Loot rotation, vendor caches, {esc(SEASON_LABEL)} manhunt week {week_n}, server state and maintenance notes for the week of {esc(day_label)}. Updated automatically every Tuesday.</p>
        <p class="meta">Week of <time datetime="{slug}">{esc(day_label)}</time> · Manhunt week {week_n}</p>
        {loot_block}
        {cache_block}
        {server_block}
        <h2>Related Guide Hubs</h2>
        <div class="grid">
          <article class="video-card" data-c="special">
  <div class="card-body">
    <p class="eyebrow">Loot Today</p>
    <h2><a href="/division-2/loot/">Division 2 Loot Today and Targeted Loot</a></h2>
    <p>Today's targeted loot snapshot, updated around the daily 08:00 UTC reset.</p>
    <p class="meta"><a href="/division-2/loot/">Open hub</a></p>
  </div>
</article>
          <article class="video-card" data-c="special">
  <div class="card-body">
    <p class="eyebrow">Reset Times</p>
    <h2><a href="/division-2/reset/">Division 2 Reset Times &amp; Countdowns</a></h2>
    <p>Daily 08:00 UTC reset, weekly Tuesday vendors and live countdowns.</p>
    <p class="meta"><a href="/division-2/reset/">Open hub</a></p>
  </div>
</article>
          <article class="video-card" data-c="special">
  <div class="card-body">
    <p class="eyebrow">Manhunts</p>
    <h2><a href="/division-2/manhunts/">Manhunt Walkthroughs &amp; Target Routes</a></h2>
    <p>Weekly scout objectives and HVT walkthroughs for the current season.</p>
    <p class="meta"><a href="/division-2/manhunts/">Open hub</a></p>
  </div>
</article>
        </div>
        <h2>FAQ</h2>
        <dl class="faq-list">{faq_visible}</dl>
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <p>Raigulus archives The Division 2 no commentary walkthroughs, mission and build guides, plus Conflict PvP, Dark Zone, Regulus, and gameplay clips.</p>
    <p><a href="https://www.youtube.com/@raigulus">YouTube @raigulus</a> <span>/</span> <a href="https://www.instagram.com/raigulus/">Instagram @raigulus</a> <span>/</span> <a href="https://www.facebook.com/raigulus/">Facebook</a> <span>/</span> <a href="/discord/">Discord</a></p>
  </footer>
</body>
</html>
"""

    out_dir = ROOT / "division-2" / "this-week" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    page_path = out_dir / "index.html"
    if page_path.exists() and page_path.read_text(encoding="utf-8") == html_doc:
        print(f"No changes for week {slug}.")
        return 0
    page_path.write_text(html_doc, encoding="utf-8")

    loc = f"{BASE_URL}/division-2/this-week/{slug}/"
    txt_path = ROOT / "sitemap.txt"
    txt = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
    if loc not in txt:
        txt_path.write_text(txt.rstrip("\n") + "\n" + loc + "\n", encoding="utf-8")
    xml_path = ROOT / "sitemap.xml"
    xml = xml_path.read_text(encoding="utf-8") if xml_path.exists() else ""
    if loc not in xml:
        entry = f"  <url><loc>{loc}</loc><lastmod>{slug}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>\n"
        xml = xml.replace("</urlset>", entry + "</urlset>", 1) if "</urlset>" in xml else xml + entry
        xml_path.write_text(xml, encoding="utf-8")
    print(f"DONE week {slug} (manhunt week {week_n}, loot fresh: {fresh})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
