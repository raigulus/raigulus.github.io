#!/usr/bin/env python3
"""Small, conservative copy pass: replace repeated AI-sounding boilerplate.

Only visible body text is touched. Links, numbers, metadata, JSON-LD and
structured data are left alone so SEO and facts do not move. Variants are
chosen per file so the site does not swap one repeated phrase for another.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VARIANTS = {
    "Unofficial fan summary. Game content belongs to Ubisoft; full texts linked above.": [
        "Fan-written notes, not Ubisoft copy. The game is theirs; the source link is up top.",
        "Written by a player, not Ubisoft. The official wording is linked at the top.",
        "Our own notes, not official documentation. Ubisoft owns the game; source above.",
        "Unofficial notes by Raigulus. Ubisoft's full text is linked up top.",
    ],
    "Our plain-language summary below: full texts live on ": [
        "Here's the short version. Ubisoft's full post is at ",
        "We boiled it down. The original wording is on ",
        "Quick read below; the official text is on ",
    ],
    "This is our plain-language summary; the full text is on ": [
        "Short version below. Original notes: ",
        "Here's our take. Full Ubisoft text: ",
        "The short read is below; Ubisoft has it in full at ",
    ],
    "plain-language overview below: full texts live on ": [
        "quick rundown below; Ubisoft's version is on ",
        "short overview below; the original is on ",
    ],
    "plain-language roundup below: full texts live on ": [
        "short roundup below; original notes on ",
        "quick pass below; Ubisoft's post is on ",
    ],
    "Unofficial fan summary. Game content belongs to Ubisoft; full notes linked above.": [
        "Fan-written notes, not Ubisoft copy. The game is theirs; the source link is up top.",
        "Written by a player, not Ubisoft. The official wording is linked at the top.",
        "Our own notes, not official documentation. Ubisoft owns the game; source above.",
    ],
    "below is our plain-language summary, numbers are facts from the official notes, sentences are ours.": [
        "Below is our short take; numbers are facts from Ubisoft, the wording is ours."
    ],
    "Below is our plain-language summary, numbers are facts from the official notes, sentences are ours.": [
        "Below is our short take; numbers are facts from Ubisoft, the wording is ours."
    ],
    "Full texts: ": ["Official notes: "],
    "each gets its own plain-language page as the archive grows.": [
        "each gets its own short page as the archive grows."
    ],
    "note this page is not a full text replacement for the official patch notes.": [
        "This page doesn't replace the official patch notes."
    ],
    "Our plain-language summary below:": ["Here's the short version:"],
    "full texts linked above.": ["source link above."],
    "full text is on ": ["original is on "],
    "All 163 Division 2 video guides in one place:": [
        "Every Division 2 video guide we've posted, together:"
    ],
    "All Division 2 video guides from Raigulus in one place.": [
        "Division 2 video guides from Raigulus, all together."
    ],
    "Every weekly Division 2 reset digest in one place:": [
        "Weekly Division 2 reset digests, week after week:"
    ],
    "keeps Raigulus Escalation videos grouped in one place.": [
        "keeps the Escalation videos together."
    ],
    "Every season update summarized in our own words, newest first.": [
        "Season updates in our own words, newest at the top."
    ],
    "Unofficial fan archive, numbers come from the official notes, linked on each page.": [
        "Fan archive. Numbers come from the official notes linked on each page."
    ],
    "If you're looking for ": ["If you want "],
    "Looking for ": ["Trying to find "],
    "Additionally,": ["Also,"],
    "Furthermore,": ["On top of that,"],
    "designed to ": ["built to "],
    "aims to ": ["tries to "],
    "allows you to ": ["lets you "],
    "ensures that ": ["makes sure "],
}

TAG = re.compile(r"(<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>)", re.S | re.I)
TEXT = re.compile(r"(>)([^<]+)(<)")


def variant_for(seed: str, key: str) -> str:
    options = VARIANTS[key]
    if len(options) == 1:
        return options[0]
    n = int(hashlib.sha256((seed + "|" + key).encode("utf-8")).hexdigest()[:8], 16)
    return options[n % len(options)]


def humanize(text: str, seed: str) -> tuple[str, int]:
    parts = TAG.split(text)
    changed = 0
    for i, part in enumerate(parts):
        if i % 2 == 1:  # script/style block
            continue
        def repl(m):
            nonlocal changed
            body = m.group(2)
            original = body
            for key in VARIANTS:
                if key in body:
                    body = body.replace(key, variant_for(seed, key))
            if body != original:
                changed += 1
            return m.group(1) + body + m.group(3)
        parts[i] = TEXT.sub(repl, part)
    return "".join(parts), changed


def main() -> int:
    total_files = 0
    total_edits = 0
    files = list(ROOT.rglob("*.html")) + list((ROOT / "scripts").glob("*.py"))
    for path in files:
        if ".git" in path.parts or "seo-reports" in path.parts:
            continue
        with open(path, encoding="utf-8", newline="") as f:
            original = f.read()
        new, edits = humanize(original, path.relative_to(ROOT).as_posix())
        if edits:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            total_files += 1
            total_edits += edits
    print(f"humanized {total_edits} text node(s) in {total_files} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
