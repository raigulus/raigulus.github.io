#!/usr/bin/env python3
"""Regression tests for lore validation guardrails."""

from __future__ import annotations

import copy
import unittest

from scripts.validate_lore import ROOT, load_json, validate_inventories, validate_records


VOCABULARIES = load_json(ROOT / "content" / "lore" / "vocabularies.json")


def source():
    return {
        "id": "official-test-source",
        "title": "Official test source",
        "publisher": "Test Publisher",
        "source_type": "official-publisher",
        "scope": "franchise-lore",
        "accessed_date": "2026-07-18",
        "url": "https://example.com/source",
    }


def entry(entry_id="test-entry", slug="test-entry"):
    return {
        "schema_version": 2,
        "id": entry_id,
        "franchise": "tom-clancys-the-division",
        "continuity": "division-game-universe",
        "type": "person",
        "title": "Test Entry",
        "slug": slug,
        "section": "people",
        "summary": "A fixture used to test validation.",
        "canon_status": "game-canon",
        "connection_status": "not-applicable",
        "spoiler_level": "none",
        "claims": [
            {
                "id": "test-claim",
                "text": "A directly supported fixture claim.",
                "assessment": "confirmed",
                "source_ids": ["official-test-source"],
            }
        ],
        "sections": [
            {
                "heading": "Test section",
                "paragraphs": [
                    {"text": "Fixture prose.", "claim_ids": ["test-claim"]}
                ],
            }
        ],
        "relations": [],
        "verification": {
            "status": "source-reviewed",
            "last_reviewed": "2026-07-18",
            "human_reviewed": False,
            "notes": "Fixture only.",
        },
    }


class LoreRecordValidationTests(unittest.TestCase):
    def validate(self, entries):
        return validate_records([source()], entries, VOCABULARIES)[0]

    def test_valid_entry(self):
        self.assertEqual(self.validate([entry()]), [])

    def test_missing_source(self):
        record = entry()
        record["claims"][0]["source_ids"] = ["missing-source"]
        self.assertTrue(any("unknown source id" in item for item in self.validate([record])))

    def test_missing_claim_mapping(self):
        record = entry()
        record["sections"][0]["paragraphs"][0]["claim_ids"] = ["missing-claim"]
        self.assertTrue(any("unknown claim id" in item for item in self.validate([record])))

    def test_dangling_relation(self):
        record = entry()
        record["relations"] = [
            {"target_id": "missing-entry", "relationship": "appears-in"}
        ]
        self.assertTrue(any("unknown entry" in item for item in self.validate([record])))

    def test_duplicate_output_path(self):
        first = entry("first-entry", "same-slug")
        second = entry("second-entry", "same-slug")
        self.assertTrue(any("duplicate output path" in item for item in self.validate([first, second])))

    def test_invalid_publication_state(self):
        record = entry()
        record["verification"]["status"] = "published"
        self.assertTrue(any("requires human_reviewed=true" in item for item in self.validate([record])))

    def test_disputed_claim_is_explicitly_supported(self):
        record = entry()
        record["claims"][0]["assessment"] = "disputed"
        self.assertEqual(self.validate([record]), [])

    def test_forbidden_public_transcript_field(self):
        record = entry()
        record["full_transcript"] = "This must never enter the public record."
        self.assertTrue(any("forbidden public field" in item for item in self.validate([record])))


class LoreInventoryValidationTests(unittest.TestCase):
    def test_reconciled_inventory_requires_known_matching_total(self):
        inventory = {
            "schema_version": 1,
            "id": "test-inventory",
            "title": "Test Inventory",
            "game": "the-division-2",
            "inventory_status": "in-progress",
            "last_audited": "2026-07-18",
            "categories": [
                {
                    "id": "test-category",
                    "label": "Test category",
                    "expected_count": None,
                    "captured_count": 0,
                    "source_reviewed_count": 0,
                    "human_reviewed_count": 0,
                    "published_count": 0,
                    "status": "reconciled",
                    "notes": "Fixture only.",
                }
            ],
        }
        errors, _ = validate_inventories([inventory], VOCABULARIES)
        self.assertTrue(any("reconciled requires" in item for item in errors))

    def test_review_counts_cannot_exceed_capture_counts(self):
        inventory = {
            "schema_version": 1,
            "id": "test-inventory",
            "title": "Test Inventory",
            "game": "the-division-2",
            "inventory_status": "in-progress",
            "last_audited": "2026-07-18",
            "categories": [
                {
                    "id": "test-category",
                    "label": "Test category",
                    "expected_count": 1,
                    "captured_count": 0,
                    "source_reviewed_count": 1,
                    "human_reviewed_count": 0,
                    "published_count": 0,
                    "status": "in-progress",
                    "notes": "Fixture only.",
                }
            ],
        }
        errors, _ = validate_inventories([inventory], VOCABULARIES)
        self.assertTrue(any("counts must satisfy" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
