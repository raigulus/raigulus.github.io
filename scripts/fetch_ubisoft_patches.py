#!/usr/bin/env python3
"""Discover new Ubisoft Division 2 patch notes and add fan summary pages.

Runs in GitHub Actions (no local scheduler). Uses only the standard library.
Every generated page links back to the official Ubisoft article; text is a short
unofficial summary built from headings and bullets, never a full repost.
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS_URL = (
    "https://www.ubisoft.com/en-us/game/the-division/the-division-2/news-updates"
)
BASE = "https://raigulus.github.io"
PATCHES = ROOT / "division-2" / "patches"
HUB = PATCHES / "index.html"
STATE = ROOT / "assets" / "data" / "ubisoft-patches-state.json"
TEMPLATE = PATCHES / "y8s4-spearfall-pts" / "index.html"
UA = "Mozilla/5.0 (compatible; RaigulusPatchFetcher/1.0)"
PATCH_WORDS = ("patch-notes", "title-update", "tu8", "tu7", "update-notes")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def discover(source: str) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for m in re.finditer(r"news-updates/([A-Za-z0-9]+)/([a-z0-9-]+)", source):
        article_id, slug = m.group(1), m.group(2)
        if any(word in slug for word in PATCH_WORDS):
            found.setdefault(article_id, slug)
    return list(found.items())


def extract(article_html: str) -> dict:
    title = ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", article_html, re.S | re.I)
    if m:
        title = text(m.group(1))
    desc = ""
    m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', article_html, re.I)
    if m:
        desc = html.unescape(m.group(1)).strip()
    date = ""
    m = re.search(rf"({MONTHS})\s+\d{{1,2}},\s+\d{{4}}", article_html)
    if m:
        date = m.group(0)
    headings = [text(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", article_html, re.S | re.I)]
    bullets = [text(b) for b in re.findall(r"<li[^>]*>(.*?)</li>", article_html, re.S | re.I)]
    headings = [h for h in headings if h and len(h) < 90][:10]
    bullets = [b for b in bullets if b and 25 < len(b) < 320 and "news-updates" not in b][:12]
    return {"title": title, "description": desc, "date": date, "headings": headings, "bullets": bullets}


def slug_for(article_slug: str, title: str) -> str:
    s = article_slug.replace("the-division-2-", "").replace("-patch-notes", "")
    if "spearfall" in article_slug and "y8s" not in s:
        s = "y8s4-" + s
    m = re.search(r"(Y8S\d+(?:\.\d+)?)", title, re.I)
    if m and not re.match(r"y8s", s, re.I):
        s = m.group(1).lower() + "-" + s
    return re.sub(r"[^a-z0-9-]", "", s.lower()).strip("-")


def esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def build_page(info: dict, source_url: str, slug: str, url: str) -> str:
    t = TEMPLATE.read_text(encoding="utf-8")
    head = t[: t.index("<body>")]
    header = t[t.index("<body>") + len("<body>") : t.index("  <main>")]
    footer = t[t.index('  <footer class="site-footer">'):]
    title = info["title"] or "Division 2 Patch Notes"
    title = title if "Division 2" in title else f"Division 2 {title}"
    desc = (info["description"] or f"Unofficial fan summary of {title}.")[:200]
    for old in ("Division 2 Y8S4 Spearfall PTS Patch Notes [2026]", "Spearfall PTS Patch Notes"):
        head = head.replace(old, title)
    head = head.replace("https://raigulus.github.io/division-2/patches/y8s4-spearfall-pts/", url)
    head = head.replace(
        "Unofficial fan summary of the Y8S4 Spearfall Public Test Server notes, sourced from Ubisoft.",
        desc,
    )
    ld = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
    page_ld = {
        "@context": "https://schema.org", "@type": "WebPage", "name": title,
        "description": desc, "url": url,
        "isPartOf": {"@type": "WebSite", "name": "Raigulus", "url": BASE},
    }
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage", "url": url,
        "mainEntity": [
            {"@type": "Question", "name": "Are these the official patch notes?",
             "acceptedAnswer": {"@type": "Answer", "text": "No. This is an unofficial fan summary. Full notes are linked to Ubisoft above."}},
            {"@type": "Question", "name": "Where can I read every detail?",
             "acceptedAnswer": {"@type": "Answer", "text": "Follow the official Ubisoft source link at the top of this page."}},
        ],
    }
    crumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "The Division 2", "item": BASE + "/division-2/"},
            {"@type": "ListItem", "position": 3, "name": "Patches", "item": BASE + "/division-2/patches/"},
            {"@type": "ListItem", "position": 4, "name": title, "item": url},
        ],
    }
    for obj in (page_ld, faq, crumb):
        head = ld.sub(
            lambda m, payload=json.dumps(obj, ensure_ascii=False, separators=(",", ":")): m.group(1) + payload + m.group(3),
            head,
            count=1,
        )
    today = datetime.now(timezone.utc).date().isoformat()
    sections = []
    for h in info["headings"] or ["Official Notes Summary"]:
        sections.append(f"<h2>{esc(h)}</h2>")
        used = 0
        for b in info["bullets"]:
            if used >= 2:
                break
            if b.lower() in h.lower():
                continue
            sections.append(f"<p>{esc(b)}</p>")
            used += 1
        if used == 0:
            sections.append("<p>Ubisoft's source link has the full wording for this bit.</p>")
    body = f'''  <main>
    <section class="section">
      <div class="content">
        <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/division-2/">The Division 2</a> / <a href="/division-2/patches/">Patches</a> / <span>{esc(title)}</span></nav>
        <p class="eyebrow">The Division 2 / Official Patch Notes</p>
        <h1>{esc(title)}</h1>
        <p>Here's our short take on Ubisoft's notes. The <a href="{esc(source_url)}">official article</a> has every number and mechanic; the wording here is ours.</p>
        <p class="meta">Published: {esc(info["date"] or "date not listed")} &middot; Last updated: <time datetime="{today}">{today}</time></p>
        <p class="meta">Fan-written notes, not Ubisoft copy. Source link at the top.</p>
        {''.join(sections)}
      </div>
    </section>
  </main>
'''
    return head + "<body>\n" + header + body + footer


def update_hub(title: str, slug: str, url: str, date: str) -> None:
    s = HUB.read_text(encoding="utf-8")
    if url in s:
        return
    card = f'''          <article class="video-card" data-c="special" data-search-card data-search="{esc(title)} patch notes division 2 ubisoft">
  <div class="card-body">
    <p class="eyebrow">{esc(date or "Official notes")}</p>
    <h3><a href="/division-2/patches/{slug}/">{esc(title)}</a></h3>
    <p>Our short take on Ubisoft's latest patch notes.</p>
    <p class="meta"><a href="/division-2/patches/{slug}/">Open guide</a></p>
  </div>
</article>
'''
    idx = s.index('<div class="grid">', s.index('<h2 id="patches">')) + len('<div class="grid">')
    s = s[:idx] + "\n" + card + s[idx:]
    def repl(m):
        if '"itemListElement"' not in m.group(2):
            return m.group(0)
        d = json.loads(m.group(2))
        els = d.get("itemListElement")
        if isinstance(els, list):
            d["itemListElement"] = [{"@type": "ListItem", "position": 1, "url": url, "name": title}] + [
                {**e, "position": i + 2} for i, e in enumerate(els)
            ]
        return m.group(1) + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + m.group(3)
    s = re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', repl, s, count=1, flags=re.S)
    s = re.sub(r">(\d+) guides<", f">{len(re.findall('data-search-card', s))} guides<", s, count=1)
    HUB.write_text(s, encoding="utf-8")


def update_lists(url: str, date: str) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    for rel, priority in (("sitemap-all.xml", False), ("sitemap.xml", True)):
        p = ROOT / rel
        s = p.read_text(encoding="utf-8")
        if url in s:
            continue
        entry = f"  <url><loc>{url}</loc><lastmod>{today}</lastmod></url>\n"
        if priority:
            entry = entry.replace("</url>", "<changefreq>weekly</changefreq><priority>0.7</priority></url>")
        p.write_text(s.replace("</urlset>", entry + "</urlset>"), encoding="utf-8")
    p = ROOT / "sitemap.txt"
    lines = p.read_text(encoding="utf-8").splitlines()
    if url not in lines:
        lines.insert(1, url)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p = ROOT / "llms.txt"
    s = p.read_text(encoding="utf-8")
    if url not in s:
        line = f"- [Ubisoft Patch Notes]({url}): Short fan summary of Ubisoft's latest update.\n"
        s = s.replace("## YouTube Playlists", line + "\n## YouTube Playlists", 1)
        p.write_text(s, encoding="utf-8")
    p = ROOT / "assets" / "data" / "landing-data.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "patches" in d.get("stats", {}):
        d["stats"]["patches"] = len([x for x in PATCHES.iterdir() if x.is_dir() and (x / "index.html").exists()])
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"processed": []}
    seen = {item["id"] for item in state["processed"]}
    try:
        articles = discover(fetch(NEWS_URL))
    except Exception as exc:
        print(f"Could not read Ubisoft news index: {exc}")
        return 0
    print(f"Discovered {len(articles)} patch-note candidate(s).")
    for article_id, slug in articles[:5]:
        if article_id in seen:
            continue
        source_url = f"{NEWS_URL}/{article_id}/{slug}"
        try:
            info = extract(fetch(source_url))
        except Exception as exc:
            print(f"Could not fetch {source_url}: {exc}")
            continue
        if not info["title"]:
            print(f"No title extracted from {source_url}; skipping.")
            continue
        page_slug = slug_for(slug, info["title"])
        page_dir = PATCHES / page_slug
        if page_dir.exists():
            print(f"Page already exists for {slug}; recording state only.")
        else:
            page_dir.mkdir(parents=True, exist_ok=True)
            url = f"{BASE}/division-2/patches/{page_slug}/"
            (page_dir / "index.html").write_text(build_page(info, source_url, page_slug, url), encoding="utf-8")
            update_hub(info["title"], page_slug, url, info["date"])
            update_lists(url, info["date"])
            print(f"Added patch page: /division-2/patches/{page_slug}/")
        state["processed"].append({
            "id": article_id, "slug": slug, "title": info["title"],
            "url": source_url, "checked_at": datetime.now(timezone.utc).date().isoformat(),
        })
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
