#!/usr/bin/env python3
"""Convert eager YouTube embeds to click-to-play facades and enrich video OG tags."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMBED_RE = re.compile(
    r'(?P<indent>\s*)<iframe class="watch" '
    r'src="https://www\.youtube\.com/embed/(?P<video_id>[A-Za-z0-9_-]{11})" '
    r'title="(?P<title>[^"]+)" allowfullscreen></iframe>'
)
SCRIPT_TAG = '  <script src="/assets/video-player.js" defer></script>\n'


def facade(match: re.Match[str], description: str | None = None) -> str:
    indent = match.group("indent")
    video_id = match.group("video_id")
    title = match.group("title")
    alt = f"Video thumbnail: {title}."
    if description:
        sent = description.strip()
        for sep in (". ", "! ", "? "):
            if sep in sent:
                sent = sent[: sent.index(sep) + 1]
                break
        else:
            sent = sent.rstrip(".") + "."
        alt = f"{alt} {sent}"
        if len(alt) > 200:
            room = 200 - len(f"Video thumbnail: {title}.") - 2
            cut = sent[:room]
            if " " in cut:
                cut = cut.rsplit(" ", 1)[0]
            alt = f"Video thumbnail: {title}. {cut.rstrip('.,;:')}..."
    alt = html.escape(alt, quote=True)
    return f'''{indent}<div class="watch video-facade" data-video-id="{video_id}" data-video-title="{title}">
          <button class="video-facade-button" type="button" aria-label="Play {title}">
            <img src="https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" alt="{alt}" width="480" height="360" decoding="async" fetchpriority="high">
            <span class="video-facade-play" aria-hidden="true"></span>
            <span class="video-facade-label">Play video</span>
          </button>
          <noscript><a class="video-facade-fallback" href="https://www.youtube.com/watch?v={video_id}">Watch {title} on YouTube</a></noscript>
        </div>'''


def video_og_tags(video_id: str) -> str:
    player = f"https://www.youtube.com/embed/{video_id}"
    return (
        f'  <meta property="og:video" content="{player}">\n'
        f'  <meta property="og:video:secure_url" content="{player}">\n'
        '  <meta property="og:video:type" content="text/html">\n'
        '  <meta property="og:video:width" content="1280">\n'
        '  <meta property="og:video:height" content="720">\n'
    )


def optimize(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    match = EMBED_RE.search(content)
    if not match:
        return False

    video_id = match.group("video_id")
    desc_m = re.search(r'<meta name="description" content="([^"]*)"', content)
    description = desc_m.group(1) if desc_m else None
    content = EMBED_RE.sub(lambda m: facade(m, description), content, count=1)
    if "/assets/video-player.js" not in content:
        anchor = '  <script src="/assets/search.js" defer></script>\n'
        if anchor in content:
            content = content.replace(anchor, anchor + SCRIPT_TAG, 1)
        else:
            content = content.replace("</head>", SCRIPT_TAG + "</head>", 1)

    if "/division-2/videos/" in path.as_posix():
        content = content.replace(
            '<meta property="og:type" content="website">',
            '<meta property="og:type" content="video.other">',
            1,
        )
        if 'property="og:video"' not in content:
            image_line = re.search(r'^  <meta property="og:image"[^\n]*>\n', content, re.MULTILINE)
            if not image_line:
                raise ValueError(f"Missing og:image in {path}")
            content = content[:image_line.end()] + video_og_tags(video_id) + content[image_line.end():]

    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        changed += int(optimize(path))
    print(f"Optimized {changed} YouTube embed page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
