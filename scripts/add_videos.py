#!/usr/bin/env python3
"""Add new YouTube videos to the Raigulus site end-to-end.

Reads a spec file (JSON list) with editorial fields per video plus optional
yt-dlp metadata files, then updates:
  - assets/data/videos.json
  - division-2/videos/<slug>/index.html (new page per video)
  - division-2/index.html (card grid + both JSON-LD ItemLists + guide count)
  - index.html (ItemList JSON-LD + Latest Optimized Guides grid)
  - sitemap.txt, sitemap.xml, feed.xml

Usage:
    python3 scripts/add_videos.py new_videos.json
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://raigulus.github.io"
TODAY = datetime.now(timezone.utc).date().isoformat()

PLAYLISTS = {
    "escalation": (
        "PLG6L-oRdfdL-FWVfW-U3H6yARkbvk31B2",
        "The Division 2 Speedruns, Builds &amp; Experiments",
    ),
    "manhunt": (
        "PLG6L-oRdfdL9h6GIqo_I2F91J-gDIVujy",
        "The Division 2 Manhunts &amp; Boss Guides",
    ),
    "pvp": (
        "PLG6L-oRdfdL-qrkEEdqj8MeEtXSTgpdK2",
        "The Division 2 PvP &amp; Conflict Archive",
    ),
    "side": (
        "PLeivDSwrtKVI",
        "The Division 2 Side Activities &amp; Open World Runs",
    ),
}

HUB_LINKS = {
    "escalation run": [
        ("/division-2/escalation/", "Escalation loot and Tier 10 hub"),
        ("/division-2/loot/", "Loot today and farming hub"),
        ("/division-2/prototype-gear/", "Prototype gear and vendor hub"),
    ],
    "manhunt": [
        ("/division-2/manhunts/", "Manhunt weekly hub"),
        ("/division-2/bosses/", "Boss guides hub"),
    ],
    "pvp/archive clip": [
        ("/division-2/pvp/", "Conflict PvP hub"),
    ],
    "side activity": [
        ("/division-2/loot/", "Loot today and farming hub"),
    ],
}

SECTION_TITLES = {
    "escalation run": "Escalation Run Walkthrough",
    "manhunt": "Manhunt Walkthrough",
    "pvp/archive clip": "Match Breakdown",
    "side activity": "Activity Walkthrough",
}


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


MAX_TITLE_CHARS = 60  # Google truncates SERP titles around ~60 chars
LEGACY_SUMMARY_MARKERS = ("nostalgia reference",)


def check_title(title: str, slug: str) -> None:
    if len(title) > MAX_TITLE_CHARS:
        raise SystemExit(
            f"Title too long ({len(title)} chars, max {MAX_TITLE_CHARS}) for '{slug}':\n"
            f"  {title}\n"
            f"Shorten the title in the spec before adding this video."
        )


def default_summary(spec: dict) -> str:
    """Editorial fallback when a spec has no usable summary."""
    core = spec["mission"]
    cluster = spec["cluster"]
    if cluster == "pvp/archive clip":
        return f"{core} - archived The Division 2 Conflict PvP clip from Raigulus."
    if cluster == "escalation run":
        return f"{core} - Division 2 Escalation run with route notes and loot checks from Raigulus."
    if cluster == "manhunt":
        return f"{core} - Division 2 manhunt walkthrough covering objectives and route flow from Raigulus."
    if cluster == "raid/incursion":
        return f"{core} - Division 2 raid and incursion clear archive from Raigulus."
    if cluster == "side activity":
        return f"{core} - Division 2 open world activity run from Raigulus."
    return f"{core} - The Division 2 gameplay archive from Raigulus."[:160]


def resolve_summary(spec: dict) -> str:
    summary = (spec.get("summary") or "").strip()
    if not summary or any(m in summary for m in LEGACY_SUMMARY_MARKERS):
        return default_summary(spec)
    return summary[:160]


def fmt_duration(seconds) -> str:
    if not seconds:
        return "Not listed"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

def related_cards(record: dict, records: list[dict], exclude_self=True) -> str:
    cluster = record["cluster"]
    pool = [
        r for r in records
        if r["cluster"] == cluster and (not exclude_self or r["url"] != record["url"])
    ]
    if len(pool) < 3:
        extra = [r for r in records if r["url"] not in {p["url"] for p in pool}]
        pool += extra[: 3 - len(pool)]
    pool = sorted(pool, key=lambda r: r["published_date"], reverse=True)[:3]
    cards = []
    for rel in pool:
        vid = rel["youtube_url"].split("v=")[-1]
        short = rel["mission"].split(" Y8S")[0].split(" Week")[0][:28]
        search_blob = " ".join([
            rel["title"], rel.get("summary", ""), rel["mission"], rel["cluster"],
            rel.get("difficulty", ""), rel.get("target", ""), *rel.get("tags", []),
        ])
        search_blob = esc(search_blob.replace("'", "&#x27;"))
        cards.append(f'''<article class="video-card" data-c="special" data-search-card data-search="{search_blob}">
  <a class="thumb" href="{rel['url']}">
    <span class="thumb-ph">{esc(short)}</span>
    <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{esc(rel['title'])} thumbnail" loading="lazy">
  </a>
  <div class="card-body">
    <p class="eyebrow">{esc(rel['cluster'])}</p>
    <h2><a href="{rel['url']}">{esc(rel['title'])}</a></h2>
    <p>{esc(rel.get('summary', ''))}</p>
    <p class="meta"><time datetime="{rel['published_date']}">{rel['published_date']}</time> <span>/</span> {esc(rel['mission'])}</p>
  </div>
</article>''')
    return "<div class=\"grid\">" + "\n".join(cards) + "</div>"


def other_versions(record: dict, records: list[dict]) -> str:
    same = [
        r for r in records
        if r["mission"] == record["mission"] and r["url"] != record["url"]
    ]
    if not same:
        return ""
    items = "\n".join(
        f'<li><a href="{r["url"]}">{esc(r["title"])}</a></li>' for r in same
    )
    return f'        <h2>Other Versions of This Mission</h2>\n        <ul class="link-list">{items}</ul>\n'


def faq_items(record: dict) -> list[tuple[str, str]]:
    diff = record.get("difficulty") or "the labeled difficulty"
    return [
        (
            f"What does this {record['mission']} video cover?",
            f"It covers the embedded Raigulus run for {record['mission']}, including route flow, objectives, combat pacing, and visible loot checks where possible.",
        ),
        (
            "What difficulty or variant is shown?",
            f"The page labels the run as {diff}. Check the embedded video for the exact pacing and encounter flow.",
        ),
        (
            "Is this a no commentary guide?",
            "The upload is labeled as gameplay. If commentary or archive context is present, the page describes it instead of forcing it into a no-commentary format.",
        ),
        (
            "Does this video guarantee loot drops or collectibles?",
            "No. The page only mentions loot checks or drops when they are visible in the video, and it does not claim all caches, all collectibles, or guaranteed rewards.",
        ),
        (
            "Can I use this route solo?",
            "Yes, it can be used as a solo route reference, but your build and difficulty setting still matter.",
        ),
    ]


def render_page(record: dict, records: list[dict]) -> str:
    vid = record["youtube_url"].split("v=")[-1]
    slug_url = record["url"]
    canonical = slug_url
    keywords = record["tags"]
    pl_id, pl_name = PLAYLISTS[record["_playlist"]]
    hub_links = HUB_LINKS[record["cluster"]]
    section_title = SECTION_TITLES[record["cluster"]]
    faq = faq_items(record)

    faq_json = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}'
        % (esc(q).replace("'", "\\u0027"), esc(a).replace("'", "\\u0027"))
        for q, a in faq
    )
    video_ld = (
        '{"@context":"https://schema.org","@type":"VideoObject","name":"%s","description":"%s",'
        '"thumbnailUrl":["https://i.ytimg.com/vi/%s/hqdefault.jpg"],"uploadDate":"%s",'
        '"embedUrl":"https://www.youtube.com/embed/%s","contentUrl":"https://www.youtube.com/watch?v=%s",'
        '"keywords":[%s],"author":{"@type":"Person","name":"Raigulus","url":"https://raigulus.github.io",'
        '"sameAs":["https://www.youtube.com/@raigulus","https://www.instagram.com/raigulus/","https://www.facebook.com/raigulus/"]},'
        '"publisher":{"@type":"Organization","name":"Raigulus","url":"https://raigulus.github.io",'
        '"sameAs":["https://www.youtube.com/@raigulus","https://www.instagram.com/raigulus/","https://www.facebook.com/raigulus/"]}}'
    ) % (
        esc(record["title"]).replace("'", "\\u0027"), esc(record["_summary"]).replace("'", "\\u0027"),
        vid, record["published_date"], vid, vid,
        ",".join('"%s"' % esc(k).replace("'", "\\u0027") for k in keywords),
    )
    breadcrumb_ld = (
        '{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":'
        '[{"@type":"ListItem","position":1,"name":"Home","item":"https://raigulus.github.io/"},'
        '{"@type":"ListItem","position":2,"name":"The Division 2","item":"https://raigulus.github.io/division-2/"},'
        '{"@type":"ListItem","position":3,"name":"%s","item":"%s"}]}'
    ) % (esc(record["title"]).replace("'", "\\u0027"), canonical)

    alt_text = esc(f"Video thumbnail: {record['title']}. {record['_summary']}"[:200])
    hub_html = " ".join(f'<a href="{h}>{label}</a>' for h, label in hub_links)
    pills = "\n".join(
        '<li><a class="tag-chip" href="/division-2/?tag=%s">%s</a></li>'
        % (esc(t).replace(" ", "%20"), esc(t))
        for t in keywords
    )
    faq_dl = "\n".join(f"<dt>{esc(q)}</dt><dd>{esc(a)}</dd>" for q, a in faq)
    faq_ld = (
        '{"@context":"https://schema.org","@type":"FAQPage","url":"%s","mainEntity":[%s]}'
        % (canonical, faq_json)
    )

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(record['title'])}</title>
  <meta name="description" content="{esc(record['_summary'])}">
  <meta name="blogarama-site-verification" content="blogarama-e6104966-f8b0-49ea-803a-101ddc0264b6">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" type="application/rss+xml" title="Raigulus Division 2 video feed" href="https://raigulus.github.io/feed.xml">
  <meta property="og:title" content="{esc(record['title'])}">
  <meta property="og:description" content="{esc(record['_summary'])}">
  <meta property="og:type" content="video.other">
  <meta property="og:url" content="{slug_url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta property="og:image" content="https://i.ytimg.com/vi/{vid}/hqdefault.jpg">
  <meta property="og:video" content="https://www.youtube.com/embed/{vid}">
  <meta property="og:video:secure_url" content="https://www.youtube.com/embed/{vid}">
  <meta property="og:video:type" content="text/html">
  <meta property="og:video:width" content="1280">
  <meta property="og:video:height" content="720">
  <meta name="twitter:image" content="https://i.ytimg.com/vi/{vid}/hqdefault.jpg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/styles.css">
  <script src="/assets/search.js" defer></script>
  <script src="/assets/video-player.js" defer></script>
  <script src="/assets/live-loot.js" defer></script>
  <script type="text/javascript">
    (function(c,l,a,r,i,t,y){{
        c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    }})(window, document, "clarity", "script", "x5tl7t5cqi");
  </script>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-C8XHNXWMVQ"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag("js", new Date());
    gtag("config", "G-C8XHNXWMVQ");
  </script>
  <script>
    document.addEventListener("click", function(event) {{
      var link = event.target.closest("a[href]");
      if (!link || typeof gtag !== "function") return;
      var url;
      try {{
        url = new URL(link.href, window.location.href);
      }} catch (error) {{
        return;
      }}
      if (url.origin === window.location.origin) return;
      var host = url.hostname.replace(/^www\\./, "");
      var label = (link.getAttribute("aria-label") || link.textContent || "").trim().slice(0, 120);
      var eventName = "outbound_click";
      if (host === "youtube.com" || host === "youtu.be") eventName = "youtube_click";
      if (host === "instagram.com") eventName = "instagram_click";
      if (host === "discord.com" || host === "discord.gg") eventName = "discord_click";
      gtag("event", eventName, {{
        link_url: url.href,
        link_domain: host,
        link_text: label,
        page_path: window.location.pathname,
        event_category: "engagement"
      }});
    }}, true);
  </script>
  <script type="application/ld+json">{video_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<script type="application/ld+json">{faq_ld}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">Raigulus</a>
    <nav>
      <a href="/division-2/">Division 2</a>
      <a href="/division-2/builds/">Builds</a>
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
        <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/division-2/">The Division 2</a> / <a href="/division-2/?q={esc(record['mission']).replace(' ', '%20')}">{esc(record['mission'])}</a> / <span>{esc(record['title'])}</span></nav>
        <p class="eyebrow">{esc(record['cluster'])}</p>
        <h1>{esc(record['title'])}</h1>
        <p>{esc(record['_summary'])}</p>
        <div class="watch video-facade" data-video-id="{vid}" data-video-title="{esc(record['title'])}">
          <button class="video-facade-button" type="button" aria-label="Play {esc(record['title'])}">
            <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{alt_text}" width="480" height="360" decoding="async" fetchpriority="high">
            <span class="video-facade-play" aria-hidden="true"></span>
            <span class="video-facade-label">Play video</span>
          </button>
          <noscript><a class="video-facade-fallback" href="https://www.youtube.com/watch?v={vid}">Watch {esc(record['title'])} on YouTube</a></noscript>
        </div>
        <h2>Guide Summary</h2>
        <p>{esc(record['_guide_summary'])}</p>
        <p>{hub_html}</p>
        <h2>Guide Facts</h2>
        <table class="facts">
          <tr><th>Mission</th><td>{esc(record['mission'])}</td></tr>
          <tr><th>Content type</th><td>{esc(record['cluster'])}</td></tr>
          <tr><th>Difficulty/variant</th><td>{esc(record.get('difficulty') or 'Gameplay')}</td></tr>
          <tr><th>Duration</th><td>{fmt_duration(record.get('_duration_seconds'))}</td></tr>
          <tr><th>Published</th><td>{record['published_date']}</td></tr>
          <tr><th>Page last checked</th><td>{TODAY}</td></tr>
          <tr><th>Playlist</th><td><a href="https://www.youtube.com/playlist?list={pl_id}">{pl_name}</a></td></tr>
          <tr><th>YouTube</th><td><a href="https://www.youtube.com/watch?v={vid}">Watch on YouTube</a></td></tr>
        </table>

{other_versions(record, records)}
        <h2>{esc(record['mission'])} - {section_title}</h2>
        <h2>Overview</h2>
        <p>This Raigulus gameplay recording follows {esc(record['mission'])} through the opening route, objective order, encounter context, and loot checks visible in the run.</p>
        <p>The embedded Raigulus video is the primary reference for the route, timing, build context, and results shown on this page.</p>
        <h2>Walkthrough Notes</h2>
        <ol>
          <li>Use the embedded run for the opening route and first objective timing.</li>
          <li>Follow the encounter sequence shown before committing to exposed objectives or interaction prompts.</li>
          <li>Use the visible cover positions and line-of-sight breaks as reference when enemy waves stack around doors, balconies, or objective props.</li>
          <li>Use the YouTube timeline to jump between the main objective, boss section, or final encounter.</li>
        </ol>
        <h2>Boss and Objective Notes</h2>
        <p>Use the boss section of the embedded video for exact positioning and timing. The written page avoids naming boss mechanics that are not verified from the current run.</p>
        <h2>Collectibles &amp; Secrets</h2>
        <p>Loot checks are included where possible in the run. This page does not claim all SHD caches, collectibles, hidden rooms, or named drops unless the video title or description explicitly says so.</p>

        <h2>FAQ</h2>
        <dl class="faq-list">{faq_dl}</dl>

        <h2>Search Tags</h2>
        <ul class="pill-list">{pills}</ul>
        <h2>Related Guides</h2>
        {related_cards(record, records)}
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <p>Raigulus archives The Division 2 no commentary walkthroughs, mission and build guides, plus Conflict PvP, Dark Zone, Regulus, and gameplay clips.</p>
    <p><a href="https://www.youtube.com/@raigulus">YouTube @raigulus</a> <span>/</span> <a href="https://www.instagram.com/raigulus/">Instagram @raigulus</a> <span>/</span> <a href="https://www.facebook.com/raigulus/">Facebook</a> <span>/</span> <a href="/discord/">Discord</a></p>
  </footer>
</body>
</html>
'''


# ---------------------------------------------------------------------------
# Site updates
# ---------------------------------------------------------------------------

LD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.DOTALL)


def update_itemlists(content: str, new_records: list[dict]) -> tuple[str, int]:
    """Insert new records at position 1 of every ItemList JSON-LD block."""
    inserted = 0

    def repl(match):
        nonlocal inserted
        body = match.group(2)
        if '"itemListElement"' not in body:
            return match.group(0)
        data = json.loads(body)
        elements = data.get("itemListElement")
        if not elements or not isinstance(elements, list):
            return match.group(0)
        if elements and elements[0].get("url") == new_records[0]["url"]:
            return match.group(0)  # already applied
        new_items = [
            {"@type": "ListItem", "position": i + 1, "url": r["url"], "name": r["title"]}
            for i, r in enumerate(new_records)
        ]
        offset = len(new_items)
        for item in elements:
            item["position"] = item.get("position", 0) + offset
        data["itemListElement"] = new_items + elements
        inserted += 1
        return match.group(1) + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + match.group(3)

    return LD_RE.sub(repl, content), inserted


def update_hub_page(records_new: list[dict], all_records: list[dict]) -> None:
    path = ROOT / "division-2" / "index.html"
    content = path.read_text(encoding="utf-8")

    # 1. Cards: insert before the first search card in the main grid.
    anchor = '<div class="grid"><article class="video-card" data-c="special" data-search-card'
    idx = content.find(anchor)
    if idx == -1:
        raise SystemExit("hub card anchor not found")
    cards = []
    for rec in records_new:
        vid = rec["youtube_url"].split("v=")[-1]
        short = rec["mission"].split(" Y8S")[0].split(" Week")[0][:28]
        search_blob = esc(" ".join([
            rec["title"], rec["_summary"], rec["mission"], rec["cluster"],
            rec.get("difficulty", ""), rec.get("target", ""), *rec["tags"],
        ])).replace("'", "&#x27;")
        cards.append(f'''<article class="video-card" data-c="special" data-search-card data-search="{search_blob}">
  <a class="thumb" href="{rec['url']}">
    <span class="thumb-ph">{esc(short)}</span>
    <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{esc(rec['title'])} thumbnail" loading="lazy">
  </a>
  <div class="card-body">
    <p class="eyebrow">{esc(rec['cluster'])}</p>
    <h2><a href="{rec['url']}">{esc(rec['title'])}</a></h2>
    <p>{esc(rec['_summary'])}</p>
    <p class="meta"><time datetime="{rec['published_date']}">{rec['published_date']}</time> <span>/</span> {esc(rec['mission'])}</p>
  </div>
</article>
''')
    content = content[:idx] + "<div class=\"grid\">" + "".join(cards) + content[idx + len("<div class=\"grid\">"):]

    # 2. JSON-LD ItemLists.
    content, _ = update_itemlists(content, records_new)

    # 3. Guide count.
    total = sum(1 for r in all_records if r["game"] == "division-2")
    content = re.sub(r">\d+ guides<", f">{total} guides<", content)

    path.write_text(content, encoding="utf-8")


def update_root_page(records_new: list[dict]) -> None:
    path = ROOT / "index.html"
    content = path.read_text(encoding="utf-8")
    content, _ = update_itemlists(content, records_new)

    # Latest Optimized Guides grid: insert before first existing card there.
    marker = '<h2>Latest Optimized Guides</h2>'
    m_idx = content.find(marker)
    if m_idx != -1:
        grid_idx = content.find('<div class="grid">', m_idx)
        if grid_idx != -1:
            rec = records_new[0]
            vid = rec["youtube_url"].split("v=")[-1]
            card = f'''<div class="grid"><article class="video-card" data-c="special">
  <a class="thumb" href="{rec['url']}">
    <span class="thumb-ph">{esc(rec['mission'][:28])}</span>
    <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{esc(rec['title'])} thumbnail" loading="lazy">
  </a>
  <div class="card-body">
    <p class="eyebrow">{esc(rec['cluster'])}</p>
    <h2><a href="{rec['url']}">{esc(rec['title'])}</a></h2>
    <p>{esc(rec['_summary'])}</p>
    <p class="meta"><time datetime="{rec['published_date']}">{rec['published_date']}</time> <span>/</span> {esc(rec['mission'])}</p>
  </div>
</article>
'''
            content = content[:grid_idx] + card + content[grid_idx + len('<div class="grid">'):]
    path.write_text(content, encoding="utf-8")


def update_sitemaps(records_new: list[dict]) -> None:
    txt_path = ROOT / "sitemap.txt"
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    urls = [r["url"] for r in records_new]
    last_video = max(i for i, l in enumerate(lines) if "/division-2/videos/" in l)
    lines[last_video + 1:last_video + 1] = urls
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    xml_path = ROOT / "sitemap.xml"
    content = xml_path.read_text(encoding="utf-8")
    entries = "".join(
        f'  <url><loc>{r["url"]}</loc><lastmod>{r["published_date"]}</lastmod></url>\n'
        for r in records_new
    )
    m = re.search(r'  <url><loc>[^<]*/division-2/videos/[^<]*</loc>', content)
    if m:
        content = content[:m.start()] + entries + content[m.start():]
    xml_path.write_text(content, encoding="utf-8")


def update_feed(records_new: list[dict]) -> None:
    path = ROOT / "feed.xml"
    content = path.read_text(encoding="utf-8")
    items = []
    for r in records_new:
        dt = datetime.strptime(r["published_date"], "%Y-%m-%d")
        pub = dt.strftime("%a, %d %b %Y 00:00:00 GMT")
        items.append(f'''    <item>
      <title>{esc(r['title'])}</title>
      <link>{r['url']}</link>
      <guid isPermaLink="true">{r['url']}</guid>
      <pubDate>{pub}</pubDate>
      <description>{esc(r['_summary'])}</description>
      <category>{esc(r['cluster'])}</category>
    </item>
''')
    anchor = content.find("    <item>")
    content = content[:anchor] + "".join(items) + content[anchor:]
    build_date = f"<lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y')} 00:00:00 GMT</lastBuildDate>"
    content = re.sub(r"<lastBuildDate>[^<]+</lastBuildDate>", build_date, content, count=1)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    spec_path = Path(sys.argv[1])
    specs = load_json(spec_path)

    # Merge yt-dlp metadata where provided.
    for spec in specs:
        meta_file = spec.get("metadata_file")
        if meta_file:
            meta = load_json(Path(meta_file))
            spec.setdefault("title", meta.get("title"))
            spec.setdefault("duration_seconds", int(meta.get("duration") or 0))
            spec.setdefault("chapters", meta.get("chapters") or [])
            spec.setdefault("yt_tags", meta.get("tags") or [])
            upload = meta.get("upload_date")
            if upload:
                spec.setdefault("published_date", f"{upload[:4]}-{upload[4:6]}-{upload[6:]}")

    json_path = ROOT / "assets" / "data" / "videos.json"
    records = load_json(json_path)
    existing_urls = {r["url"] for r in records}

    new_records = []
    for spec in specs:
        slug = spec["slug"].strip("/")
        url = f"{BASE_URL}/division-2/videos/{slug}/"
        if url in existing_urls:
            print(f"SKIP (already present): {slug}")
            continue
        tags = list(dict.fromkeys([t.strip().lower() for t in spec["tags"]] + ["raigulus"]))
        check_title(spec["title"], slug)
        record = {
            "title": spec["title"],
            "url": url,
            "youtube_url": spec["youtube_url"],
            "mission": spec["mission"],
            "cluster": spec["cluster"],
            "difficulty": spec.get("difficulty", ""),
            "target": spec.get("target", ""),
            "published_date": spec["published_date"],
            "duration": str(spec.get("duration_seconds") or ""),
            "has_exact_chapters": bool(spec.get("chapters")),
            "page_last_checked": TODAY,
            "game": "division-2",
            "tags": tags,
            # internal-only helpers (stripped before writing videos.json)
            "_slug": slug,
            "_summary": resolve_summary(spec),
            "_guide_summary": spec["guide_summary"],
            "_playlist": spec["playlist"],
            "_duration_seconds": spec.get("duration_seconds") or 0,
        }
        new_records.append(record)

    if not new_records:
        print("Nothing to add.")
        return 0

    new_records.sort(key=lambda r: r["published_date"])  # oldest first for prepends

    # 1. Pages.
    for rec in new_records:
        page_dir = ROOT / "division-2" / "videos" / rec["_slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        page = render_page(rec, records + [r for r in new_records if r is not rec])
        (page_dir / "index.html").write_text(page, encoding="utf-8")
        print(f"PAGE  {rec['_slug']}")

    # 2. videos.json (public schema only).
    public_new = []
    for rec in reversed(new_records):  # newest first at top
        public = {k: v for k, v in rec.items() if not k.startswith("_")}
        public["summary"] = rec["_summary"]
        public_new.append(public)
    records[:0] = public_new
    dump_json(json_path, records)

    # 3. Hub, root, sitemaps, feed.
    update_hub_page(list(reversed(new_records)), records)
    update_root_page(list(reversed(new_records)))
    update_sitemaps(list(reversed(new_records)))
    update_feed(list(reversed(new_records)))
    print(f"DONE  {len(new_records)} video(s) added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
