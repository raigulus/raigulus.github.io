#!/usr/bin/env python3
"""Discover new Raigulus YouTube uploads and add them to the site.

Pipeline: channel RSS -> diff vs videos.json -> yt-dlp metadata ->
new_videos.json spec -> scripts/add_videos.py -> site pages + sitemaps.

No secrets needed (public RSS + public video metadata).
"""

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_ID = "UCaerb1JjASS-QwHO9E48fCA"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
MAX_AGE_DAYS = 45

STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "of", "to", "for", "with",
    "vs", "is", "are", "it", "this", "that", "my", "you", "your", "how",
    "all", "no", "me", "we", "at", "by", "from", "up", "so",
}


def classify(title):
    t = title.lower()
    if "scout" in t or "manhunt" in t:
        return ("manhunt", "manhunt")
    if any(k in t for k in ("conflict", "pvp", "skirmish", "dark zone", "rogue", "clan war", "1v1")):
        return ("pvp/archive clip", "pvp")
    if any(k in t for k in ("escalation", "tier 10", "summit", "countdown", "legendary", "walkthrough", "solo cleared", "speedrun")):
        return ("escalation run", "escalation")
    return ("side activity", "side")


def clean_mission(title):
    m = re.sub(r"(?i)^the division 2\s*", "", title).strip()
    m = m.split("|")[0].strip()
    return m[:60] or "Division 2 Gameplay"


def site_title(title):
    t = re.sub(r"\s+", " ", title).strip()
    if len(t) <= 60:
        return t
    cut = t[:57].rsplit(" ", 1)[0]
    return cut[:57]


def tags_for(title, cluster):
    words = re.findall(r"[a-z0-9]+", title.lower())
    tags = [w for w in words if w not in STOPWORDS and len(w) > 2]
    seen, out = set(), []
    for w in tags:
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= 8:
            break
    return out


def slugify(title, video_id):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50].strip("-")
    return s or video_id


def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "RaigulusDiscover/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml_text = r.read().decode("utf-8")
    # Strip namespaces (YouTube varies prefixes) for robust parsing.
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", xml_text)
    xml_text = re.sub(r"<(/?)(\w+):", r"<\1", xml_text)
    root = ET.fromstring(xml_text)
    ns = {"m": "http://search.yahoo.com/mrss/"}
    items = []
    for e in root.findall("entry"):
        vid = (e.findtext("id") or "").split(":")[-1]
        pub = e.findtext("published") or ""
        desc_el = e.find("group/description")
        items.append({
            "video_id": vid,
            "title": e.findtext("title") or "",
            "published": pub[:10],
            "description": (desc_el.text or "") if desc_el is not None else "",
        })
    return [i for i in items if i["video_id"]]


def fetch_meta(video_id):
    out = subprocess.run(
        ["yt-dlp", "--no-warnings", "--skip-download", "--dump-json",
         f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        print(f"yt-dlp failed for {video_id}: {out.stderr[:200]}")
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    videos = json.loads((ROOT / "assets" / "data" / "videos.json").read_text(encoding="utf-8"))
    known = set()
    for v in videos:
        url = v.get("youtube_url", "")
        m = re.search(r"v=([A-Za-z0-9_-]{6,})", url) or re.search(r"/shorts/([A-Za-z0-9_-]{6,})", url)
        if m:
            known.add(m.group(1))
    fresh = [i for i in fetch_rss() if i["video_id"] not in known]
    print(f"RSS videos checked, {len(fresh)} new")
    if not fresh:
        return 0
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=MAX_AGE_DAYS)).isoformat()
    fresh = [i for i in fresh if (i.get("published") or "") >= cutoff]
    print(f"{len(fresh)} within {MAX_AGE_DAYS}d window")
    if not fresh:
        return 0
    specs = []
    for item in fresh:
        meta = fetch_meta(item["video_id"])
        if not meta:
            continue
        title = meta.get("title") or item["title"]
        cluster, playlist = classify(title)
        upload = str(meta.get("upload_date") or "")
        published = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if len(upload) == 8 else item["published"]
        desc = (meta.get("description") or item["description"] or "").strip().replace("\n", " ")[:160]
        specs.append({
            "slug": slugify(title, item["video_id"]),
            "title": site_title(title),
            "youtube_url": f"https://www.youtube.com/watch?v={item['video_id']}",
            "mission": clean_mission(title),
            "cluster": cluster,
            "difficulty": "PvP" if cluster == "pvp/archive clip" else "",
            "target": "",
            "published_date": published,
            "duration_seconds": int(meta.get("duration") or 0),
            "tags": tags_for(title, cluster),
            "summary": desc or f"{title} - The Division 2 gameplay archive from Raigulus.",
            "guide_summary": (desc or f"{title} - auto-added from YouTube.")[:200],
            "playlist": playlist,
            "chapters": meta.get("chapters") or [],
        })
    if not specs:
        print("No addable videos.")
        return 0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(specs, f, ensure_ascii=False)
        spec_path = f.name
    for s in specs:
        print(f"NEW: {s['title']} [{s['cluster']}]")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "add_videos.py"), spec_path])
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
