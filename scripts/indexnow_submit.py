"""Submit changed sitemap URLs to IndexNow (Bing, Yandex, Seznam, Naver).

The key file lives at the site root as <key>.txt and must stay publicly
readable; IndexNow fetches it to verify ownership. Run after a deploy:

    python scripts/indexnow_submit.py --days 3
    python scripts/indexnow_submit.py --all
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "raigulus.github.io"
KEY = "23e05d208776485a64e24554b18cae2d"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10_000


def sitemap_urls(days: int | None) -> list[str]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    entries = re.findall(r"<url>\s*<loc>(.*?)</loc>(.*?)</url>", text, re.S)
    cutoff = None if days is None else dt.date.today() - dt.timedelta(days=days)
    urls: list[str] = []
    for loc, extra in entries:
        loc = loc.strip()
        if not loc.startswith("https://"):
            continue
        if cutoff is not None:
            lastmod = re.search(r"<lastmod>(.*?)</lastmod>", extra, re.S)
            try:
                changed = dt.date.fromisoformat(lastmod.group(1).strip()[:10])
            except (AttributeError, ValueError):
                continue
            if changed < cutoff:
                continue
        urls.append(loc)
    return urls


def submit(urls: list[str]) -> int:
    if not urls:
        print("No URLs to submit.")
        return 0
    failures = 0
    for start in range(0, len(urls), MAX_URLS):
        chunk = urls[start : start + MAX_URLS]
        payload = json.dumps(
            {
                "host": HOST,
                "key": KEY,
                "keyLocation": KEY_LOCATION,
                "urlList": chunk,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "RaigulusIndexNow/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                print(f"IndexNow: HTTP {response.status} for {len(chunk)} URLs")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:500]
            print(f"IndexNow: HTTP {error.code} for {len(chunk)} URLs - {body}")
            failures += 1
        except urllib.error.URLError as error:
            print(f"IndexNow: request failed - {error.reason}")
            failures += 1
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Submit URLs whose sitemap lastmod is within this many days (default 3).",
    )
    parser.add_argument("--all", action="store_true", help="Submit every sitemap URL.")
    parser.add_argument("--dry-run", action="store_true", help="Print the selection without posting.")
    args = parser.parse_args()
    urls = sitemap_urls(None if args.all else args.days)
    print(f"IndexNow: {len(urls)} URL(s) selected.")
    if args.dry_run:
        for url in urls[:10]:
            print(" -", url)
        return 0
    return 1 if submit(urls) else 0


if __name__ == "__main__":
    raise SystemExit(main())
