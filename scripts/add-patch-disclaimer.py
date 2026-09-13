#!/usr/bin/env python3
"""Add 'Unofficial fan guide' disclaimer to all patch pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES_DIR = ROOT / "division-2" / "patches"
DISCLAIMER = '<div class="patch-disclaimer"><p>This is an unofficial fan-made guide. The Division 2 is developed by Ubisoft Massive. All game assets, names, and trademarks belong to their respective owners.</p></div>'
CSS = ".patch-disclaimer{max-width:800px;margin:32px auto 0;padding:16px 20px;border:1px solid rgba(237,240,244,.08);border-radius:6px;background:rgba(237,240,244,.02)}.patch-disclaimer p{font-size:12px;color:rgba(237,240,244,.35);margin:0;text-align:center;line-height:1.5}"


def add_disclaimer(html: str) -> str:
    if "patch-disclaimer" in html:
        return html

    style_match = re.search(r"</style>", html, re.IGNORECASE)
    if style_match:
        html = html[:style_match.end()] + "\n    " + CSS + "\n  " + html[style_match.end():]

    main_close = re.search(r"</main>", html, re.IGNORECASE)
    if main_close:
        html = html[:main_close.start()] + "\n  " + DISCLAIMER + "\n" + html[main_close.start():]

    return html


def main() -> int:
    count = 0
    for d in sorted(PATCHES_DIR.iterdir()):
        if not d.is_dir():
            continue
        index = d / "index.html"
        if not index.exists():
            continue
        original = index.read_text(encoding="utf-8")
        updated = add_disclaimer(original)
        if updated != original:
            index.write_text(updated, encoding="utf-8")
            count += 1
            print(f"  + {d.name}")

    print(f"Disclaimer added to {count} patch pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
