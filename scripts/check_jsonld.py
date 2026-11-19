#!/usr/bin/env python3
"""Read-only structural validation of JSON-LD blocks in site HTML.

This checks JSON syntax and a small set of structural properties that the
existing site consistently provides. It does NOT claim full Schema.org or
Google rich-result compliance, and it never accesses the network.

Rules (deliberately conservative, derived from the current site content):
  * Every JSON-LD block must parse as JSON.
  * A block must be a non-empty object, a non-empty list of objects, or an
    object with a non-empty ``@graph`` array of objects.
  * Every object node must carry ``@context`` and ``@type``.
  * For a few well-established types, require the fields the site always
    emits: WebSite/Organization (name, url), ItemList/BreadcrumbList
    (itemListElement), FAQPage (mainEntity), VideoObject (name), Article
    (headline). Unknown types are only checked for @context and @type.

Exclusions: generated/untracked report directories and VCS/runtime folders
are skipped, matching check_internal_links.py.

Usage:
  python scripts/check_jsonld.py                 # check the repo
  python scripts/check_jsonld.py --json          # machine-readable report
  python scripts/check_jsonld.py --root DIR      # custom root (tests)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".omo", "agents", "__pycache__", "seo-reports", "node_modules"}
BLOCK_PATTERN = re.compile(
    r"""<script[^>]*type=["']application/ld\+json["'][^>]*>([\s\S]*?)</script>""", re.I
)

REQUIRED_FIELDS = {
    "WebSite": ("name", "url"),
    "Organization": ("name", "url"),
    "ItemList": ("itemListElement",),
    "BreadcrumbList": ("itemListElement",),
    "FAQPage": ("mainEntity",),
    "VideoObject": ("name",),
    "Article": ("headline",),
}


def jsonld_blocks(path: Path) -> list[str]:
    """Return raw JSON-LD block contents from an HTML file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return BLOCK_PATTERN.findall(text)


def iter_html(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def _node_types(data: object) -> tuple[list[object], str | None]:
    """Return (nodes, inherited_context).

    @graph nodes commonly omit @context because it is declared once at the
    top level; inherit it in that case rather than imposing a false rule.
    """
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict) and isinstance(data.get("@graph"), list):
        return data["@graph"], data.get("@context")
    return [data], None


def validate_block(raw: str, file_label: str, index: int) -> list[dict]:
    """Validate one JSON-LD block; return a list of issue dicts."""
    issues: list[dict] = []
    where = f"{file_label} block {index}"

    def add(problem: str, detail: str) -> None:
        issues.append({"file": file_label, "block": index, "problem": problem, "detail": detail})

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        add("malformed JSON", f"line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return issues

    nodes, inherited_context = _node_types(data)
    if not nodes or all(node in ({}, [], None) for node in nodes):
        add("empty JSON-LD", "block contains no object nodes")
        return issues

    for pos, node in enumerate(nodes):
        if not isinstance(node, dict) or not node:
            add("invalid node", f"node {pos} is not a non-empty object")
            continue
        node_label = f"node {pos} ({node.get('@type', 'missing @type')})"
        if not node.get("@context") and not inherited_context:
            add("missing @context", node_label)
        if not node.get("@type"):
            add("missing @type", node_label)
            continue
        types = node["@type"] if isinstance(node["@type"], list) else [node["@type"]]
        for schema_type in types:
            for field in REQUIRED_FIELDS.get(str(schema_type), ()):
                value = node.get(field)
                if value is None or value == "" or value == []:
                    add("missing expected field", f"{node_label}: {field}")
    return issues


def validate_file(path: Path, root: Path) -> list[dict]:
    label = path.relative_to(root).as_posix()
    issues: list[dict] = []
    for index, raw in enumerate(jsonld_blocks(path), start=1):
        issues.extend(validate_block(raw, label, index))
    return issues


def check_repository(root: Path) -> tuple[list[dict], int]:
    issues: list[dict] = []
    block_count = 0
    for path in iter_html(root):
        blocks = jsonld_blocks(path)
        block_count += len(blocks)
        issues.extend(validate_file(path, root))
    return issues, block_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="report problems but exit 0 (used in CI while pre-existing "
             "structured-data debt is tracked for cleanup)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"check_jsonld: root not found: {root}", file=sys.stderr)
        return 2
    issues, blocks = check_repository(root)
    if args.json:
        print(json.dumps({"root": str(root), "blocks": blocks, "issues": issues}, indent=2))
    else:
        for issue in issues:
            print(
                f"{issue['file']} block {issue['block']}: {issue['problem']}: {issue['detail']}"
            )
        print(f"Checked {blocks} JSON-LD blocks; {len(issues)} problem(s) found.")
    if issues and args.warn_only:
        print("warn-only mode: reporting without failing (pre-existing debt).")
        return 0
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
