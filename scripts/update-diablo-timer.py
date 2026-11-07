#!/usr/bin/env python3
"""Update the static "Next spawn" line on the Diablo 4 World Boss Timer page.

Calculates the next spawn from the 3.5-hour cycle anchor (30 Oct 2026 00:00 UTC)
and writes it between the DIABLO-TIMER-STATIC markers in the HTML.

Usage:
    python scripts/update-diablo-timer.py            # update in place
    python scripts/update-diablo-timer.py --check    # exit 1 if stale
"""

from __future__ import annotations
import argparse
import datetime
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "diablo-4" / "world-boss-timer" / "index.html"
ANCHOR = datetime.datetime(2026, 10, 30, 0, 0, 0, tzinfo=datetime.timezone.utc)
CYCLE_MINUTES = 210
MARKER_RE = re.compile(
    r"<!-- DIABLO-TIMER-STATIC-START -->.*?<!-- DIABLO-TIMER-STATIC-END -->",
    re.DOTALL,
)


def next_spawn(now=None):
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    delta = (now - ANCHOR).total_seconds()
    cycles = int(delta // (CYCLE_MINUTES * 60)) + 1
    spawn = ANCHOR + datetime.timedelta(minutes=cycles * CYCLE_MINUTES)
    return spawn


def render_line(spawn):
    return (
        '<!-- DIABLO-TIMER-STATIC-START -->\n'
        f'        <p class="meta" id="diablo-static-spawn">Next spawn: {spawn.strftime("%Y-%m-%d %H:%M")} UTC (static, updates every 30 min)</p>\n'
        '        <!-- DIABLO-TIMER-STATIC-END -->'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = PAGE.read_text(encoding="utf-8")
    spawn = next_spawn()
    new_block = render_line(spawn)
    new_content = MARKER_RE.sub(new_block, content, count=1)

    if args.check:
        if new_content == content:
            print("OK: static spawn line is up to date")
            raise SystemExit(0)
        else:
            print("STALE: static spawn line needs update")
            raise SystemExit(1)

    PAGE.write_text(new_content, encoding="utf-8")
    print(f"Updated: Next spawn {spawn.strftime('%Y-%m-%d %H:%M')} UTC")


if __name__ == "__main__":
    main()
