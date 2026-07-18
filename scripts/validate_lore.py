#!/usr/bin/env python3
"""Validate lore records, editorial controls and coverage inventories."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
LORE_CONTENT = ROOT / "content" / "lore"
ENTRY_DIR = LORE_CONTENT / "entries"
INVENTORY_DIR = LORE_CONTENT / "inventories"
SOURCES_PATH = LORE_CONTENT / "sources.json"
VOCABULARIES_PATH = LORE_CONTENT / "vocabularies.json"
EDITORIAL_PATH = LORE_CONTENT / "editorial.json"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
META_REFRESH_PATTERN = re.compile(
    r"<meta\s+[^>]*http-equiv=[\"']refresh[\"'][^>]*>", re.IGNORECASE
)
FORBIDDEN_PUBLIC_KEYS = {
    "full_transcript",
    "raw_transcript",
    "subtitle_dump",
    "media_blob",
    "audio_file",
    "video_file",
}
FORBIDDEN_PUBLIC_EXTENSIONS = {
    ".srt",
    ".vtt",
    ".ass",
    ".ssa",
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".flac",
    ".mp4",
    ".mkv",
    ".webm",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_string(record, field, where, errors):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: {field} must be a non-empty string")
        return ""
    return value.strip()


def require_slug(record, field, where, errors):
    value = require_string(record, field, where, errors)
    if value and not SLUG_PATTERN.fullmatch(value):
        errors.append(f"{where}: invalid {field} {value}")
    return value


def validate_date(value, where, errors):
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: must be an ISO date")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"{where}: invalid ISO date {value}")


def vocabulary_set(vocabularies, key, errors):
    values = vocabularies.get(key)
    if not isinstance(values, list) or not values:
        errors.append(f"vocabularies.json: {key} must be a non-empty array")
        return set()
    if len(values) != len(set(values)):
        errors.append(f"vocabularies.json: {key} contains duplicate values")
    return set(values)


def load_records():
    sources_payload = load_json(SOURCES_PATH)
    sources = sources_payload.get("sources", [])
    entries = [load_json(path) for path in sorted(ENTRY_DIR.rglob("*.json"))]
    return sources, entries


def load_inventories():
    if not INVENTORY_DIR.exists():
        return []
    return [load_json(path) for path in sorted(INVENTORY_DIR.rglob("*.json"))]


def load_editorial():
    return load_json(EDITORIAL_PATH)


def find_forbidden_keys(value, where, errors):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PUBLIC_KEYS:
                errors.append(f"{where}: forbidden public field {key}")
            find_forbidden_keys(child, f"{where}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            find_forbidden_keys(child, f"{where}[{index}]", errors)


def validate_records(sources, entries, vocabularies):
    errors = []
    warnings = []
    source_map = {}

    entry_types = vocabulary_set(vocabularies, "entry_types", errors)
    continuities = vocabulary_set(vocabularies, "continuities", errors)
    canon_statuses = vocabulary_set(vocabularies, "canon_statuses", errors)
    connection_statuses = vocabulary_set(vocabularies, "connection_statuses", errors)
    claim_assessments = vocabulary_set(vocabularies, "claim_assessments", errors)
    relationship_types = vocabulary_set(vocabularies, "relationship_types", errors)
    source_types = vocabulary_set(vocabularies, "source_types", errors)
    source_scopes = vocabulary_set(vocabularies, "source_scopes", errors)
    spoiler_levels = vocabulary_set(vocabularies, "spoiler_levels", errors)
    verification_statuses = vocabulary_set(vocabularies, "verification_statuses", errors)
    timeline_precisions = vocabulary_set(vocabularies, "timeline_precisions", errors)

    if not sources:
        errors.append("sources.json: at least one source is required")
    for index, source in enumerate(sources):
        where = f"sources.json sources[{index}]"
        source_id = require_slug(source, "id", where, errors)
        require_string(source, "title", where, errors)
        require_string(source, "publisher", where, errors)
        source_type = require_string(source, "source_type", where, errors)
        scope = require_string(source, "scope", where, errors)
        accessed_date = require_string(source, "accessed_date", where, errors)
        url = require_string(source, "url", where, errors)
        if source_id in source_map:
            errors.append(f"{where}: duplicate source id {source_id}")
        source_map[source_id] = source
        if source_type not in source_types:
            errors.append(f"{where}: unsupported source_type {source_type}")
        if scope not in source_scopes:
            errors.append(f"{where}: unsupported scope {scope}")
        validate_date(accessed_date, f"{where} accessed_date", errors)
        if source.get("published_date"):
            validate_date(source["published_date"], f"{where} published_date", errors)
        if url and urlparse(url).scheme not in {"http", "https"}:
            errors.append(f"{where}: source URL must use http or https")

    entry_map = {}
    paths = set()
    for index, entry in enumerate(entries):
        where = f"entries[{index}]"
        if entry.get("schema_version") != 2:
            errors.append(f"{where}: schema_version must be 2")
        entry_id = require_slug(entry, "id", where, errors)
        require_slug(entry, "franchise", where, errors)
        title = require_string(entry, "title", where, errors)
        entry_type = require_string(entry, "type", where, errors)
        continuity = require_string(entry, "continuity", where, errors)
        slug = require_slug(entry, "slug", where, errors)
        section = require_slug(entry, "section", where, errors)
        require_string(entry, "summary", where, errors)
        canon_status = require_string(entry, "canon_status", where, errors)
        connection = require_string(entry, "connection_status", where, errors)
        spoiler = require_string(entry, "spoiler_level", where, errors)
        find_forbidden_keys(entry, where, errors)

        if entry_id in entry_map:
            errors.append(f"{where}: duplicate entry id {entry_id}")
        entry_map[entry_id] = entry
        path_key = (section, slug)
        if path_key in paths:
            errors.append(f"{where}: duplicate output path /lore/{section}/{slug}/")
        paths.add(path_key)
        if entry_type not in entry_types:
            errors.append(f"{where}: unsupported type {entry_type}")
        if continuity not in continuities:
            errors.append(f"{where}: unsupported continuity {continuity}")
        if canon_status not in canon_statuses:
            errors.append(f"{where}: unsupported canon_status {canon_status}")
        if connection not in connection_statuses:
            errors.append(f"{where}: unsupported connection_status {connection}")
        if spoiler not in spoiler_levels:
            errors.append(f"{where}: unsupported spoiler_level {spoiler}")

        claims = entry.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"{where}: at least one claim is required")
            claims = []
        claim_map = {}
        for claim_index, claim in enumerate(claims):
            claim_where = f"{where} claim[{claim_index}]"
            claim_id = require_slug(claim, "id", claim_where, errors)
            require_string(claim, "text", claim_where, errors)
            assessment = require_string(claim, "assessment", claim_where, errors)
            source_ids = claim.get("source_ids")
            if not isinstance(source_ids, list) or not source_ids:
                errors.append(f"{claim_where}: source_ids must not be empty")
                source_ids = []
            elif len(source_ids) != len(set(source_ids)):
                errors.append(f"{claim_where}: source_ids must be unique")
            if assessment not in claim_assessments:
                errors.append(f"{claim_where}: unsupported assessment {assessment}")
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
                if len(claim_ids) != len(set(claim_ids)):
                    errors.append(f"{paragraph_where}: claim_ids must be unique")
                for claim_id in claim_ids:
                    if claim_id not in claim_map:
                        errors.append(f"{paragraph_where}: unknown claim id {claim_id}")

        for comparison_index, comparison in enumerate(entry.get("comparisons", [])):
            comparison_where = f"{where} comparison[{comparison_index}]"
            for field in ("topic", "real_world", "division", "assessment"):
                require_string(comparison, field, comparison_where, errors)
            source_ids = comparison.get("source_ids", [])
            if not isinstance(source_ids, list) or not source_ids:
                errors.append(f"{comparison_where}: source_ids must not be empty")
                source_ids = []
            for source_id in source_ids:
                if source_id not in source_map:
                    errors.append(f"{comparison_where}: unknown source id {source_id}")

        timeline = entry.get("timeline")
        if timeline is not None:
            timeline_where = f"{where} timeline"
            if not isinstance(timeline, dict):
                errors.append(f"{timeline_where}: must be an object")
            else:
                sequence = timeline.get("sequence")
                if not isinstance(sequence, int) or sequence < 0:
                    errors.append(f"{timeline_where}: sequence must be a non-negative integer")
                require_string(timeline, "label", timeline_where, errors)
                precision = require_string(timeline, "precision", timeline_where, errors)
                if precision not in timeline_precisions:
                    errors.append(f"{timeline_where}: unsupported precision {precision}")
                source_ids = timeline.get("source_ids")
                if not isinstance(source_ids, list) or not source_ids:
                    errors.append(f"{timeline_where}: source_ids must not be empty")
                    source_ids = []
                for source_id in source_ids:
                    if source_id not in source_map:
                        errors.append(f"{timeline_where}: unknown source id {source_id}")

        verification = entry.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{where}: verification object is required")
            verification = {}
        status = require_string(verification, "status", f"{where} verification", errors)
        last_reviewed = require_string(
            verification, "last_reviewed", f"{where} verification", errors
        )
        validate_date(last_reviewed, f"{where} verification last_reviewed", errors)
        if status not in verification_statuses:
            errors.append(f"{where}: unsupported verification status {status}")
        human_reviewed = verification.get("human_reviewed")
        if not isinstance(human_reviewed, bool):
            errors.append(f"{where}: human_reviewed must be boolean")
        if status in {"human-reviewed", "published"} and not human_reviewed:
            errors.append(f"{where}: {status} requires human_reviewed=true")
        if human_reviewed and not str(verification.get("reviewed_by", "")).strip():
            errors.append(f"{where}: human_reviewed=true requires reviewed_by")
        if status == "published":
            for claim in claims:
                known_sources = [source_map.get(item) for item in claim.get("source_ids", [])]
                if known_sources and all(
                    source and source.get("source_type") == "community-lead"
                    for source in known_sources
                ):
                    errors.append(
                        f"{where}: published claim {claim.get('id')} cannot rely only on community leads"
                    )

        if not title:
            warnings.append(f"{where}: missing title")

    for entry_id, entry in entry_map.items():
        relations = entry.get("relations", [])
        if not isinstance(relations, list):
            errors.append(f"{entry_id}: relations must be an array")
            continue
        for index, relation in enumerate(relations):
            where = f"{entry_id} relation[{index}]"
            if not isinstance(relation, dict):
                errors.append(f"{where}: relation must be an object")
                continue
            target_id = require_string(relation, "target_id", where, errors)
            relationship = require_string(relation, "relationship", where, errors)
            if target_id not in entry_map:
                errors.append(f"{where}: relation points to unknown entry {target_id}")
            if relationship not in relationship_types:
                errors.append(f"{where}: unsupported relationship {relationship}")

    return errors, warnings


def validate_inventories(inventories, vocabularies):
    errors = []
    warnings = []
    statuses = vocabulary_set(vocabularies, "inventory_statuses", errors)
    inventory_ids = set()
    category_ids = set()
    for index, inventory in enumerate(inventories):
        where = f"inventories[{index}]"
        if inventory.get("schema_version") != 1:
            errors.append(f"{where}: schema_version must be 1")
        inventory_id = require_slug(inventory, "id", where, errors)
        require_string(inventory, "title", where, errors)
        require_slug(inventory, "game", where, errors)
        status = require_string(inventory, "inventory_status", where, errors)
        last_audited = require_string(inventory, "last_audited", where, errors)
        validate_date(last_audited, f"{where} last_audited", errors)
        if status not in statuses:
            errors.append(f"{where}: unsupported inventory_status {status}")
        if inventory_id in inventory_ids:
            errors.append(f"{where}: duplicate inventory id {inventory_id}")
        inventory_ids.add(inventory_id)
        categories = inventory.get("categories")
        if not isinstance(categories, list) or not categories:
            errors.append(f"{where}: categories must be a non-empty array")
            continue
        for category_index, category in enumerate(categories):
            category_where = f"{where} category[{category_index}]"
            category_id = require_slug(category, "id", category_where, errors)
            require_string(category, "label", category_where, errors)
            require_string(category, "notes", category_where, errors)
            category_status = require_string(category, "status", category_where, errors)
            if category_status not in statuses:
                errors.append(f"{category_where}: unsupported status {category_status}")
            if category_id in category_ids:
                errors.append(f"{category_where}: duplicate category id {category_id}")
            category_ids.add(category_id)
            expected = category.get("expected_count")
            if expected is not None and (not isinstance(expected, int) or expected < 0):
                errors.append(f"{category_where}: expected_count must be null or a non-negative integer")
            counts = []
            for field in (
                "captured_count",
                "source_reviewed_count",
                "human_reviewed_count",
                "published_count",
            ):
                value = category.get(field)
                if not isinstance(value, int) or value < 0:
                    errors.append(f"{category_where}: {field} must be a non-negative integer")
                    value = 0
                counts.append(value)
            captured, source_reviewed, human_reviewed, published = counts
            if not published <= human_reviewed <= source_reviewed <= captured:
                errors.append(
                    f"{category_where}: counts must satisfy published <= human-reviewed <= source-reviewed <= captured"
                )
            if expected is not None and captured > expected:
                errors.append(f"{category_where}: captured_count cannot exceed expected_count")
            if category_status == "reconciled" and (expected is None or captured != expected):
                errors.append(
                    f"{category_where}: reconciled requires a known expected_count equal to captured_count"
                )
            if expected is None:
                warnings.append(f"{category_where}: expected_count is unknown; no completeness claim is allowed")
    return errors, warnings


def validate_editorial(editorial):
    errors = []
    if editorial.get("schema_version") != 1:
        errors.append("editorial.json: schema_version must be 1")
    pages = editorial.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append("editorial.json: pages must be a non-empty array")
        return errors
    slugs = set()
    for index, page in enumerate(pages):
        where = f"editorial.json pages[{index}]"
        slug = require_slug(page, "slug", where, errors)
        require_string(page, "title", where, errors)
        require_string(page, "description", where, errors)
        require_string(page, "eyebrow", where, errors)
        if slug in slugs:
            errors.append(f"{where}: duplicate page slug {slug}")
        slugs.add(slug)
        sections = page.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(f"{where}: sections must be a non-empty array")
            continue
        for section_index, section in enumerate(sections):
            section_where = f"{where} section[{section_index}]"
            require_string(section, "heading", section_where, errors)
            paragraphs = section.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                errors.append(f"{section_where}: paragraphs must be a non-empty array")
                continue
            for paragraph_index, paragraph in enumerate(paragraphs):
                if not isinstance(paragraph, str) or not paragraph.strip():
                    errors.append(f"{section_where} paragraph[{paragraph_index}]: must be non-empty text")
        action_url = page.get("action_url")
        if action_url and urlparse(action_url).scheme not in {"http", "https"}:
            errors.append(f"{where}: action_url must use http or https")
    return errors


def public_asset_errors():
    errors = []
    roots = [LORE_CONTENT, ROOT / "assets" / "lore-media"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in FORBIDDEN_PUBLIC_EXTENSIONS:
                errors.append(
                    f"public asset guard: forbidden raw transcript/media file {path.relative_to(ROOT)}"
                )
    return errors


def is_redirect_page(html_text):
    """Return true for legacy HTML aliases that redirect to a canonical page."""
    return bool(META_REFRESH_PATTERN.search(html_text))


def site_inventory_warnings():
    warnings = []
    video_root = ROOT / "division-2" / "videos"
    page_slugs = {
        path.parent.name
        for path in video_root.glob("*/index.html")
        if not is_redirect_page(path.read_text(encoding="utf-8"))
    }
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
    inventories = load_inventories()
    vocabularies = load_json(VOCABULARIES_PATH)
    editorial = load_editorial()
    errors, warnings = validate_records(sources, entries, vocabularies)
    inventory_errors, inventory_warnings = validate_inventories(inventories, vocabularies)
    errors.extend(inventory_errors)
    warnings.extend(inventory_warnings)
    errors.extend(validate_editorial(editorial))
    errors.extend(public_asset_errors())
    inventory_drift = site_inventory_warnings()
    warnings.extend(inventory_drift)
    if strict_site_inventory:
        errors.extend(inventory_drift)
    return sources, entries, errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-site-inventory",
        action="store_true",
        help="Treat video page/data drift as an error.",
    )
    args = parser.parse_args()
    sources, entries, errors, warnings = run_validation(args.strict_site_inventory)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    inventory_count = len(load_inventories())
    print(
        f"Lore validation passed: {len(entries)} entries, {len(sources)} sources, "
        f"{inventory_count} coverage inventory"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
