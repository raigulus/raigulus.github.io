#!/usr/bin/env python3
"""Validate lore records and report site inventory drift."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
ENTRY_DIR = ROOT / "content" / "lore" / "entries"
SOURCES_PATH = ROOT / "content" / "lore" / "sources.json"

CONNECTION_STATUSES = {
    "confirmed-influence",
    "explicit-reference",
    "documented-parallel",
    "thematic-similarity",
    "community-theory",
    "disputed",
}
VERIFICATION_STATUSES = {
    "draft",
    "source-reviewed",
    "human-reviewed",
    "published",
    "superseded",
}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_string(record, field, where, errors):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: {field} must be a non-empty string")
        return ""
    return value.strip()


def load_records():
    sources_payload = load_json(SOURCES_PATH)
    sources = sources_payload.get("sources", [])
    entries = [load_json(path) for path in sorted(ENTRY_DIR.glob("*.json"))]
    return sources, entries


def validate_records(sources, entries):
    errors = []
    warnings = []
    source_map = {}

    if not sources:
        errors.append("sources.json: at least one source is required")
    for index, source in enumerate(sources):
        where = f"sources.json sources[{index}]"
        source_id = require_string(source, "id", where, errors)
        require_string(source, "title", where, errors)
        require_string(source, "publisher", where, errors)
        require_string(source, "source_type", where, errors)
        require_string(source, "scope", where, errors)
        require_string(source, "accessed_date", where, errors)
        url = require_string(source, "url", where, errors)
        if source_id in source_map:
            errors.append(f"{where}: duplicate source id {source_id}")
        source_map[source_id] = source
        if url and urlparse(url).scheme not in {"http", "https"}:
            errors.append(f"{where}: source URL must use http or https")

    entry_map = {}
    paths = set()
    for index, entry in enumerate(entries):
        where = f"entries[{index}]"
        entry_id = require_string(entry, "id", where, errors)
        title = require_string(entry, "title", where, errors)
        require_string(entry, "type", where, errors)
        slug = require_string(entry, "slug", where, errors)
        section = require_string(entry, "section", where, errors)
        require_string(entry, "summary", where, errors)
        require_string(entry, "canon_status", where, errors)
        connection = require_string(entry, "connection_status", where, errors)
        spoiler = require_string(entry, "spoiler_level", where, errors)

        if entry_id in entry_map:
            errors.append(f"{where}: duplicate entry id {entry_id}")
        entry_map[entry_id] = entry
        path_key = (section, slug)
        if path_key in paths:
            errors.append(f"{where}: duplicate output path /lore/{section}/{slug}/")
        paths.add(path_key)
        if slug and not SLUG_PATTERN.fullmatch(slug):
            errors.append(f"{where}: invalid slug {slug}")
        if section and not SLUG_PATTERN.fullmatch(section):
            errors.append(f"{where}: invalid section {section}")
        if connection not in CONNECTION_STATUSES:
            errors.append(f"{where}: unsupported connection_status {connection}")
        if spoiler not in {"none", "minor", "major"}:
            errors.append(f"{where}: unsupported spoiler_level {spoiler}")

        claims = entry.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"{where}: at least one claim is required")
            claims = []
        claim_map = {}
        for claim_index, claim in enumerate(claims):
            claim_where = f"{where} claim[{claim_index}]"
            claim_id = require_string(claim, "id", claim_where, errors)
            require_string(claim, "text", claim_where, errors)
            require_string(claim, "assessment", claim_where, errors)
            source_ids = claim.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                errors.append(f"{claim_where}: source_ids must not be empty")
                source_ids = []
            if claim_id in claim_map:
                errors.append(f"{claim_where}: duplicate claim id {claim_id}")
            claim_map[claim_id] = claim
            for source_id in source_ids:
                if source_id not in source_map:
                    errors.append(f"{claim_where}: unknown source id {source_id}")

        sections = entry.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(f"{where}: at least one content section is required")
            sections = []
        for section_index, content_section in enumerate(sections):
            section_where = f"{where} section[{section_index}]"
            require_string(content_section, "heading", section_where, errors)
            paragraphs = content_section.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                errors.append(f"{section_where}: at least one paragraph is required")
                continue
            for paragraph_index, paragraph in enumerate(paragraphs):
                paragraph_where = f"{section_where} paragraph[{paragraph_index}]"
                require_string(paragraph, "text", paragraph_where, errors)
                claim_ids = paragraph.get("claim_ids")
                if not isinstance(claim_ids, list) or not claim_ids:
                    errors.append(f"{paragraph_where}: every paragraph needs claim_ids")
                    continue
                for claim_id in claim_ids:
                    if claim_id not in claim_map:
                        errors.append(f"{paragraph_where}: unknown claim id {claim_id}")

        for comparison_index, comparison in enumerate(entry.get("comparisons", [])):
            comparison_where = f"{where} comparison[{comparison_index}]"
            for field in ("topic", "real_world", "division", "assessment"):
                require_string(comparison, field, comparison_where, errors)
            source_ids = comparison.get("source_ids", [])
            if not source_ids:
                errors.append(f"{comparison_where}: source_ids must not be empty")
            for source_id in source_ids:
                if source_id not in source_map:
                    errors.append(f"{comparison_where}: unknown source id {source_id}")

        verification = entry.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{where}: verification object is required")
        else:
            status = require_string(verification, "status", f"{where} verification", errors)
            require_string(verification, "last_reviewed", f"{where} verification", errors)
            if status not in VERIFICATION_STATUSES:
                errors.append(f"{where}: unsupported verification status {status}")
            if not isinstance(verification.get("human_reviewed"), bool):
                errors.append(f"{where}: human_reviewed must be boolean")
            if status in {"human-reviewed", "published"} and not verification.get("human_reviewed"):
                errors.append(f"{where}: {status} requires human_reviewed=true")

        if not title:
            warnings.append(f"{where}: missing title")

    for entry_id, entry in entry_map.items():
        for relation in entry.get("relations", []):
            target_id = relation.get("target_id")
            if target_id not in entry_map:
                errors.append(f"{entry_id}: relation points to unknown entry {target_id}")
            require_string(relation, "relationship", f"{entry_id} relation", errors)

    return errors, warnings


def site_inventory_warnings():
    warnings = []
    video_root = ROOT / "division-2" / "videos"
    page_slugs = {path.parent.name for path in video_root.glob("*/index.html")}
    video_records = load_json(ROOT / "assets" / "data" / "videos.json")
    record_slugs = {
        urlparse(record.get("url", "")).path.rstrip("/").split("/")[-1]
        for record in video_records
        if record.get("url")
    }
    missing_records = sorted(page_slugs - record_slugs)
    missing_pages = sorted(record_slugs - page_slugs)
    if missing_records:
        warnings.append(
            f"site inventory: {len(missing_records)} video page(s) are absent from videos.json: "
            + ", ".join(missing_records)
        )
    if missing_pages:
        warnings.append(
            f"site inventory: {len(missing_pages)} videos.json record(s) have no page: "
            + ", ".join(missing_pages)
        )
    return warnings


def run_validation(strict_site_inventory=False):
    sources, entries = load_records()
    errors, warnings = validate_records(sources, entries)
    inventory = site_inventory_warnings()
    warnings.extend(inventory)
    if strict_site_inventory:
        errors.extend(inventory)
    return sources, entries, errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-site-inventory",
        action="store_true",
        help="Treat existing video page/data drift as an error.",
    )
    args = parser.parse_args()
    sources, entries, errors, warnings = run_validation(args.strict_site_inventory)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Lore validation passed: {len(entries)} entries, {len(sources)} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
