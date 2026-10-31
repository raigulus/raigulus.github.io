"""Build one root-level sitemap-all.xml from sitemap.xml.

The site previously exposed a sitemap index plus child sitemaps. GSC kept
showing the submissions as unfetched, so this keeps the public surface to one
plain <urlset> file at the site root, matching the format that works for
root-level GitHub Pages sites.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    source = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    entries = re.findall(r"<url>\s*<loc>(.*?)</loc>(.*?)</url>", source, re.S)
    lines = []
    for loc, extra in entries:
        lastmod = re.search(r"<lastmod>(.*?)</lastmod>", extra, re.S)
        if lastmod:
            lines.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod.group(1)}</lastmod></url>")
        else:
            lines.append(f"  <url><loc>{loc}</loc></url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(lines)
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap-all.xml").write_text(xml, encoding="utf-8")
    print(f"sitemap-all.xml: {len(lines)} URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
