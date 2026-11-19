#!/usr/bin/env python3
"""Read-only validator for local internal links and asset references.

The site is a static GitHub Pages build: every route is either an ``index.html``
directory page or a static asset under ``assets/``. This script checks that
local references from HTML files resolve to a real file, and that local
fragments resolve to an ``id`` in the target page.

It never accesses the network and never modifies any file.

Exclusions (documented deliberately, not silently):
  * External URLs (http/https, protocol-relative //, mailto:, tel:,
    javascript:, data:, about:) -- no network access by design.
  * Placeholder links ``href="#"`` and empty href/src.
  * Fragment-only "query" anchors (e.g. ``#tag=frost`` or ``#q=term``): the
    site's local search/form UI consumes these as query state, not element IDs.
  * ``seo-reports/`` -- generated, untracked report artifacts (uploaded to a
    workflow artifact, never published).
  * VCS/runtime directories (``.git``, ``.omo``, ``agents``, ``__pycache__``)
    and ``*.pyc`` -- not part of the published site.

Usage:
  python scripts/check_internal_links.py                 # check the repo
  python scripts/check_internal_links.py --json          # machine-readable
  python scripts/check_internal_links.py --root DIR      # custom root (tests)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".omo", "agents", "__pycache__", "seo-reports", "node_modules"}
SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "javascript:", "data:", "about:")

# href on anchors/links, src on images/scripts/iframes, and every srcset URL.
REF_PATTERNS = (
    re.compile(r"""(?:href|src)\s*=\s*["']([^"']*)["']""", re.I),
    re.compile(r"""srcset\s*=\s*["']([^"']*)["']""", re.I),
)
ID_PATTERN = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.I)


def is_external(raw: str) -> bool:
    """True when a reference must not be resolved locally."""
    raw = raw.strip()
    return (
        not raw
        or raw == "#"
        or raw.startswith("//")
        or raw.lower().startswith(SKIP_SCHEMES)
    )


def extract_refs(html: str) -> list[str]:
    """Return all href/src/srcset values from an HTML document."""
    refs: list[str] = []
    for pattern in REF_PATTERNS:
        for match in pattern.findall(html):
            if pattern is REF_PATTERNS[1]:
                # srcset entries: "url 320w, url2 480w" -> take first token.
                for part in match.split(","):
                    refs.append(part.strip().split()[0] if part.strip() else "")
            else:
                refs.append(match)
    return refs


def resolve_local(raw: str, source: Path, root: Path) -> Path | None:
    """Resolve a local reference to a filesystem path, or None if skipped."""
    if is_external(raw):
        return None
    parsed = urlsplit(raw)
    if parsed.scheme:
        return None  # any other scheme is not a local file
    path_part = unquote(parsed.path)
    if not path_part:
        return None  # fragment/query only
    if path_part.startswith("/"):
        candidate = root / path_part.lstrip("/")
    else:
        candidate = (source.parent / path_part).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return None  # reference escapes the repository root
    # Directory-style routes resolve to their index.html.
    if path_part.endswith("/") or not candidate.suffix:
        candidate = candidate / "index.html"
    return candidate


def fragment_is_query(fragment: str) -> bool:
    """Fragments consumed by in-page search/filter UIs, not element IDs."""
    return "=" in fragment


def page_ids(path: Path) -> set[str]:
    if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return set(ID_PATTERN.findall(text))


def iter_html(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def check_repository(root: Path) -> tuple[list[dict], int]:
    """Return (issues, checked_reference_count). Strictly read-only."""
    issues: list[dict] = []
    checked = 0
    for source in iter_html(root):
        html = source.read_text(encoding="utf-8", errors="ignore")
        for raw in extract_refs(html):
            target = resolve_local(raw, source, root)
            if target is None:
                continue
            checked += 1
            rel_source = source.relative_to(root).as_posix()
            if not target.exists():
                issues.append({
                    "file": rel_source,
                    "target": raw,
                    "problem": "missing target",
                    "detail": target.relative_to(root).as_posix(),
                })
                continue
            fragment = urlsplit(raw).fragment
            if fragment and not fragment_is_query(fragment):
                ids = page_ids(target)
                if fragment not in ids:
                    issues.append({
                        "file": rel_source,
                        "target": raw,
                        "problem": "missing fragment id",
                        "detail": "#" + fragment,
                    })
    return issues, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="report problems but exit 0 (used in CI while pre-existing missing "
             "thumbnail variants are tracked for cleanup)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"check_internal_links: root not found: {root}", file=sys.stderr)
        return 2
    issues, checked = check_repository(root)
    if args.json:
        print(json.dumps({"root": str(root), "checked": checked, "issues": issues}, indent=2))
    else:
        for issue in issues:
            print(f"{issue['file']}: {issue['problem']}: {issue['target']} ({issue['detail']})")
        print(f"Checked {checked} local references; {len(issues)} problem(s) found.")
    if issues and args.warn_only:
        print("warn-only mode: reporting without failing (pre-existing debt).")
        return 0
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
