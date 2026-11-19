# -*- coding: utf-8 -*-
"""Guardrails for the landing-page latest-video selection.

``generate-landing-data.py`` sorts videos.json by ``published_date`` and keeps
one record per guide URL so duplicate uploads cannot produce duplicate cards on
the homepage. That deduplication fixed a real production bug, but it had no
test. These tests pin the *existing* behavior using a pure helper, without
reading repository data, writing files, or invoking the generator.

Run: python -m unittest scripts/test_generate_landing_data.py
"""
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR = os.path.join(ROOT, "scripts", "generate-landing-data.py")

# The generator filename contains hyphens, so it cannot be imported by module
# name. Load it by path; its ``if __name__ == "__main__"`` guard keeps import
# side-effect free (no file reads, writes, or network calls at import time).
_spec = importlib.util.spec_from_file_location("generate_landing_data", GENERATOR)
_generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generator)
dedupe_latest_videos = _generator.dedupe_latest_videos

FIELDS = {"title", "url", "youtube_url", "thumbnail", "published_date", "cluster", "summary"}


def record(url, date, title="Title", youtube_id="abc1234567", **extra):
    data = {
        "title": title,
        "url": url,
        "youtube_url": f"https://www.youtube.com/watch?v={youtube_id}",
        "published_date": date,
        "cluster": "escalation run",
        "summary": "Summary",
    }
    data.update(extra)
    return data


class DedupeLatestVideosTests(unittest.TestCase):
    def test_unique_urls_are_preserved(self):
        records = [
            record("https://example.test/a/", "2026-11-13", "A"),
            record("https://example.test/b/", "2026-11-12", "B"),
            record("https://example.test/c/", "2026-11-11", "C"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual([r["url"] for r in out], [r["url"] for r in records])
        self.assertEqual([r["title"] for r in out], ["A", "B", "C"])

    def test_duplicate_urls_are_reduced_to_one_record(self):
        records = [
            record("https://example.test/a/", "2026-11-13", "Newest", "newwwwwwwww"),
            record("https://example.test/a/", "2026-11-11", "Older", "olddddddddd"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Newest")

    def test_newest_record_wins_when_dates_differ(self):
        # Deliberately listed oldest-first: sorting happens before deduping.
        records = [
            record("https://example.test/a/", "2026-11-01", "Oldest"),
            record("https://example.test/a/", "2026-11-15", "Newest"),
            record("https://example.test/a/", "2026-11-10", "Middle"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["published_date"], "2026-11-15")
        self.assertEqual(out[0]["title"], "Newest")

    def test_output_order_follows_published_date_descending(self):
        records = [
            record("https://example.test/old/", "2026-11-01", "Old"),
            record("https://example.test/new/", "2026-11-16", "New"),
            record("https://example.test/mid/", "2026-11-08", "Mid"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual([r["title"] for r in out], ["New", "Mid", "Old"])

    def test_equal_date_duplicates_keep_first_input_record(self):
        # Python's sort is stable; for equal dates the first record in the
        # source list survives. Pin that deterministic behavior.
        records = [
            record("https://example.test/a/", "2026-11-13", "First", "firstid00001"),
            record("https://example.test/a/", "2026-11-13", "Second", "secondid0002"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "First")

    def test_missing_and_empty_urls_collapse_to_one_record(self):
        no_url = record("https://example.test/x/", "2026-11-13", "No URL")
        no_url.pop("url")
        records = [
            no_url,
            record("", "2026-11-12", "Empty URL"),
            record("https://example.test/valid/", "2026-11-11", "Valid"),
        ]
        out = dedupe_latest_videos(records, 3)
        self.assertEqual(len(out), 2)
        self.assertEqual([r["title"] for r in out], ["No URL", "Valid"])
        self.assertEqual(out[0]["url"], "")
        # The missing-URL fixture keeps the youtube_url supplied by record();
        # the empty-URL record is removed by URL dedupe, so this value survives.
        self.assertEqual(out[0]["youtube_url"], "https://www.youtube.com/watch?v=abc1234567")

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(dedupe_latest_videos([], 3), [])

    def test_input_records_are_not_mutated(self):
        records = [
            record("https://example.test/a/", "2026-11-13", "A"),
            record("https://example.test/a/", "2026-11-12", "B"),
        ]
        snapshot = [dict(r) for r in records]
        dedupe_latest_videos(records, 3)
        self.assertEqual(records, snapshot)

    def test_count_limit_is_applied_after_dedupe(self):
        records = [
            record("https://example.test/a/", "2026-11-15", "A"),
            record("https://example.test/a/", "2026-11-14", "A-old"),
            record("https://example.test/b/", "2026-11-13", "B"),
            record("https://example.test/c/", "2026-11-12", "C"),
        ]
        out = dedupe_latest_videos(records, 2)
        self.assertEqual([r["title"] for r in out], ["A", "B"])

    def test_output_schema_is_unchanged(self):
        out = dedupe_latest_videos([record("https://example.test/a/", "2026-11-13")], 3)
        self.assertEqual(set(out[0]), FIELDS)
        self.assertTrue(out[0]["thumbnail"].endswith("-hqdefault.jpg"))

    def test_repeated_calls_are_deterministic(self):
        records = [
            record("https://example.test/a/", "2026-11-13", "A"),
            record("https://example.test/a/", "2026-11-11", "A-old"),
            record("https://example.test/b/", "2026-11-12", "B"),
        ]
        self.assertEqual(dedupe_latest_videos(records, 3), dedupe_latest_videos(records, 3))


if __name__ == "__main__":
    unittest.main()
