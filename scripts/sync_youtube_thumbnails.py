# -*- coding: utf-8 -*-
"""Download the YouTube thumbnails the site references into assets/img/yt/.

Thumbnails never change for a given video id, so this runs once and the result is
committed. Serving them from the site's own origin means a visitor's IP address is
no longer handed to Google simply by opening a page.

Filenames are keyed by video id and size. Anything that is already present is
skipped, so re-running is cheap and safe.
"""
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "img" / "yt"
PATTERN = re.compile(r"i\d?\.ytimg\.com/vi/([A-Za-z0-9_-]{6,})/([a-z]+)default\.jpg")
TIMEOUT = 25


def referenced_thumbnails():
    found = set()
    for path in ROOT.glob("**/*.html"):
        if ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in PATTERN.finditer(text):
            found.add((match.group(1), match.group(2)))
    return sorted(found)


def download(video_id, size):
    target = OUT_DIR / f"{video_id}-{size}default.jpg"
    if target.exists() and target.stat().st_size > 512:
        return "cached", target.stat().st_size
    url = f"https://i.ytimg.com/vi/{video_id}/{size}default.jpg"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read()
    if payload[:3] != b"\xff\xd8\xff":
        return "not-a-jpeg", len(payload)
    if len(payload) <= 512:
        return "too-small", len(payload)
    target.write_bytes(payload)
    return "downloaded", len(payload)


def main():
    wanted = referenced_thumbnails()
    if not wanted:
        print("No thumbnail references found; nothing to do.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"downloaded": 0, "cached": 0}
    failures = []
    total_bytes = 0

    for video_id, size in wanted:
        try:
            status, size_bytes = download(video_id, size)
        except Exception as error:
            failures.append((f"{video_id}-{size}default", f"{type(error).__name__}: {error}"))
            continue
        if status in stats:
            stats[status] += 1
            total_bytes += size_bytes
        else:
            failures.append((f"{video_id}-{size}default", status))

        if stats["downloaded"] and stats["downloaded"] % 25 == 0 and status == "downloaded":
            print(f"  {stats['downloaded']}/{len(wanted)} saved")

    print(f"downloaded : {stats['downloaded']}")
    print(f"cached     : {stats['cached']}")
    print(f"total size : {total_bytes / 1024 / 1024:.2f} MB")
    print(f"failures   : {len(failures)}")
    for name, reason in failures[:20]:
        print(f"   {name}: {reason}")

    manifest = sorted(p.name for p in OUT_DIR.glob("*.jpg"))
    (OUT_DIR / "manifest.json").write_text(
        json.dumps({"count": len(manifest), "files": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())