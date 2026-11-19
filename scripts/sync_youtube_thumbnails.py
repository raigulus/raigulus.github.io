#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download and verify the YouTube thumbnails referenced by local HTML.

Thumbnails never change for a given video id, so a verified download is cached
forever. Serving them from our own origin keeps visitor IPs away from Google.

Discovery
---------
The previous version scanned only *remote* ``i.ytimg.com`` URLs. Those appear
solely in JSON-LD ``thumbnailUrl`` (hq only) on a minority of pages, so
``mqdefault`` (used by every ``srcset``) was never requested and most older
video IDs were never discovered at all. This version scans the *local*
``/assets/img/yt/<id>-<size>default.jpg`` references emitted by add_videos.py
(src, srcset, og:image, twitter:image), and still accepts remote URLs so older
pages remain covered.

Safety
------
* Every response is validated (JPEG magic + minimum size) before being saved.
* Downloads are written to a temporary file and atomically replaced, so a
  failed write can never corrupt an existing valid thumbnail.
* Valid existing files are skipped (idempotent, no needless network requests).
* Transient failures (429, 5xx, timeouts, network errors) get bounded retries;
  permanent failures (400/403/404/410/414) are reported immediately.
* After downloading, all referenced local thumbnails are verified again. Any
  unresolved reference makes the run fail loudly instead of reporting success.

Usage:
  python scripts/sync_youtube_thumbnails.py
  python scripts/sync_youtube_thumbnails.py --verify-only   # read-only gate
  python scripts/sync_youtube_thumbnails.py --root DIR      # isolated tests
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "img" / "yt"
TIMEOUT = 20
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
MIN_BYTES = 513  # original script rejected <= 512 bytes
JPEG_MAGIC = b"\xff\xd8\xff"
PERMANENT_STATUSES = {400, 403, 404, 410, 414}
EXCLUDED_DIRS = {".git", ".omo", "agents", "__pycache__", "seo-reports", "node_modules"}

# Local refs are what the generator emits; remote refs are kept for old pages.
LOCAL_PATTERN = re.compile(r"/assets/img/yt/([A-Za-z0-9_-]{6,})-([a-z]+)default\.jpg")
REMOTE_PATTERN = re.compile(
    r"i\d?\.ytimg\.com/vi/([A-Za-z0-9_-]{6,})/([a-z]+)default\.jpg", re.I
)


def referenced_thumbnails(root=ROOT):
    """Return sorted (video_id, variant) pairs referenced by site HTML."""
    found = set()
    for path in sorted(root.glob("**/*.html")):
        try:
            rel = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in (LOCAL_PATTERN, REMOTE_PATTERN):
            for match in pattern.finditer(text):
                found.add((match.group(1), match.group(2)))
    return sorted(found)


def payload_problem(payload):
    """Return None for a valid JPEG, otherwise a short reason string."""
    if not payload:
        return "empty response"
    if payload[:3] != JPEG_MAGIC:
        return "not-a-jpeg"
    if len(payload) <= MIN_BYTES - 1:
        return f"too-small ({len(payload)} bytes)"
    return None


def file_is_valid(path):
    """True only for a file that passes the same validity rules."""
    try:
        if not path.is_file() or path.stat().st_size < MIN_BYTES:
            return False
        with open(path, "rb") as handle:
            return handle.read(3) == JPEG_MAGIC
    except OSError:
        return False


def fetch_payload(url, opener=None, sleeper=None, attempts=MAX_ATTEMPTS):
    """Fetch bytes with bounded retries on transient failures.

    Returns ``(payload, None)`` on success or ``(None, error_dict)``. Tests
    inject ``opener`` and ``sleeper`` so no real network or delay is used.
    """
    opener = opener or urllib.request.urlopen
    sleeper = sleeper or time.sleep
    error = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener(request, timeout=TIMEOUT) as response:
                payload = response.read()
            return payload, None
        except urllib.error.HTTPError as exc:
            kind = "permanent" if exc.code in PERMANENT_STATUSES else "transient"
            error = {"kind": kind, "detail": f"HTTP {exc.code}", "attempt": attempt}
        except Exception as exc:  # URLError, timeout, socket, etc.
            error = {
                "kind": "transient",
                "detail": f"{type(exc).__name__}: {exc}",
                "attempt": attempt,
            }
        if error["kind"] == "permanent":
            break
        if attempt < attempts:
            sleeper(BACKOFF_SECONDS * attempt)
    return None, error


def save_atomic(target, payload):
    """Write payload via a temp file and atomically replace the target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    try:
        with open(temp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if not file_is_valid(temp):
            raise OSError("written thumbnail failed validation")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()


def verify_references(root=ROOT, out_dir=None):
    """Return locally referenced thumbnails that are missing or corrupt."""
    out_dir = out_dir or (root / "assets" / "img" / "yt")
    bad = []
    for video_id, variant in referenced_thumbnails(root):
        target = out_dir / f"{video_id}-{variant}default.jpg"
        if not file_is_valid(target):
            bad.append(target.relative_to(root).as_posix())
    return sorted(bad)


def sync(root=ROOT, out_dir=None, opener=None, sleeper=None):
    """Run discovery, download/verify missing files, then verify all refs."""
    root = Path(root).resolve()
    out_dir = out_dir or (root / "assets" / "img" / "yt")
    wanted = referenced_thumbnails(root)
    report = {
        "wanted": len(wanted),
        "downloaded": [],
        "cached": [],
        "failed": [],
        "unresolved": [],
    }
    if not wanted:
        return report

    for video_id, variant in wanted:
        name = f"{video_id}-{variant}default"
        target = out_dir / f"{name}.jpg"
        if file_is_valid(target):
            report["cached"].append(name)
            continue
        url = f"https://i.ytimg.com/vi/{video_id}/{variant}default.jpg"
        payload, error = fetch_payload(url, opener=opener, sleeper=sleeper)
        if error:
            report["failed"].append(f"{name}: {error['kind']} {error['detail']} "
                                    f"(attempt {error['attempt']}/{MAX_ATTEMPTS})")
            continue
        problem = payload_problem(payload)
        if problem:
            report["failed"].append(f"{name}: invalid image ({problem})")
            continue
        try:
            save_atomic(target, payload)
        except OSError as exc:
            report["failed"].append(f"{name}: save error ({exc})")
            continue
        report["downloaded"].append(name)

    report["unresolved"] = verify_references(root, out_dir)

    manifest = sorted(p.name for p in out_dir.glob("*.jpg"))
    (out_dir / "manifest.json").write_text(
        json.dumps({"count": len(manifest), "files": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def print_report(report):
    print(f"referenced  : {report['wanted']}")
    print(f"downloaded  : {len(report['downloaded'])}")
    print(f"cached      : {len(report['cached'])}")
    print(f"failures    : {len(report['failed'])}")
    for line in report["failed"][:30]:
        print(f"   FAIL {line}")
    print(f"unresolved  : {len(report['unresolved'])}")
    for line in report["unresolved"][:30]:
        print(f"   MISSING {line}")
    emit = os.environ.get("GITHUB_ACTIONS") == "true"
    for line in report["failed"] + report["unresolved"]:
        if emit:
            print(f"::error::thumbnail: {line}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--verify-only", action="store_true",
                        help="only verify locally referenced thumbnails (read-only)")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"sync_youtube_thumbnails: root not found: {root}", file=sys.stderr)
        return 2
    out_dir = root / "assets" / "img" / "yt"

    if args.verify_only:
        bad = verify_references(root, out_dir)
        print(f"Verified local thumbnails; {len(bad)} missing or invalid reference(s).")
        for line in bad:
            print(f"   MISSING {line}")
        return 1 if bad else 0

    report = sync(root, out_dir)
    print_report(report)
    return 1 if (report["failed"] or report["unresolved"]) else 0


if __name__ == "__main__":
    sys.exit(main())
