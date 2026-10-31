"""Build /sitemap/index.xml and small child sitemaps from sitemap.xml.

Google has been unable to fetch the root sitemaps even though they return
200. A sitemap index on a fresh path, with smaller child files, gives the
crawler a second route and keeps each file easy to process.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "sitemap"
BASE = "https://raigulus.github.io"


def urls() -> list[str]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>(.*?)</loc>", text)


def write_urlset(name: str, locs: list[str]) -> None:
    body = "\n".join(f"  <url><loc>{loc}</loc></url>" for loc in locs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
    (OUT / name).write_text(xml, encoding="utf-8")
    print(f"{name}: {len(locs)} URLs")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    all_urls = urls()
    videos = [u for u in all_urls if "/division-2/videos/" in u]
    lore = [u for u in all_urls if "/lore/" in u]
    pages = [u for u in all_urls if u not in set(videos) | set(lore)]

    write_urlset("pages.xml", pages)
    write_urlset("videos.xml", videos)
    write_urlset("lore.xml", lore)

    today = dt.date.today().isoformat()
    children = ["pages.xml", "videos.xml", "lore.xml"]
    body = "\n".join(
        f"  <sitemap><loc>{BASE}/sitemap/{name}</loc><lastmod>{today}</lastmod></sitemap>"
        for name in children
    )
    index = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</sitemapindex>\n"
    )
    (OUT / "index.xml").write_text(index, encoding="utf-8")
    print(f"index.xml: {len(children)} children, total {len(all_urls)} URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
