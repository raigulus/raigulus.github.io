# -*- coding: utf-8 -*-
"""Tests for the thumbnail sync pipeline using mocked HTTP responses.

No test uses live YouTube access. ``opener`` and ``sleeper`` are injected so
network and delays are fully controlled.
"""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("sync_thumbs", SCRIPTS / "sync_youtube_thumbnails.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

JPEG = b"\xff\xd8\xff" + b"X" * 2000


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def http_error(code):
    return urllib.error.HTTPError("https://i.ytimg.com/x", code, "err", {}, io.BytesIO())


def opener_from(responses):
    """responses: {(video_id, variant): [result, ...]} where result is bytes or Exception."""
    calls = []

    def opener(request, timeout=None):
        url = request.full_url
        import re
        m = re.search(r"/vi/([A-Za-z0-9_-]{6,})/([a-z]+)default\.jpg", url)
        key = (m.group(1), m.group(2))
        calls.append(key)
        queue = responses.get(key, [JPEG])
        result = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)

    return opener, calls


class ThumbnailSyncTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.out = self.root / "assets" / "img" / "yt"
        self.out.mkdir(parents=True)
        self.sleeps = []

    def tearDown(self):
        self._tmp.cleanup()

    def html(self, *refs):
        body = "".join(
            f'<img src="/assets/img/yt/{v}-{s}default.jpg" '
            f'srcset="/assets/img/yt/{v}-{s}default.jpg 1x">' for v, s in refs
        )
        (self.root / "index.html").write_text(body, encoding="utf-8")

    def run_sync(self, responses=None):
        opener, calls = opener_from(responses or {})
        report = _mod.sync(self.root, self.out, opener=opener, sleeper=self.sleeps.append)
        return report, calls

    # 1. successful download
    def test_successful_download(self):
        self.html(("ABCDEFGH1234", "hq"))
        report, calls = self.run_sync()
        self.assertEqual(report["downloaded"], ["ABCDEFGH1234-hqdefault"])
        self.assertTrue(_mod.file_is_valid(self.out / "ABCDEFGH1234-hqdefault.jpg"))
        self.assertEqual(len(calls), 1)

    # 2. HTTP 404 - permanent, no retry
    def test_http_404_is_permanent_no_retry(self):
        self.html(("ABCDEFGH1234", "hq"))
        report, calls = self.run_sync({("ABCDEFGH1234", "hq"): [http_error(404)]})
        self.assertEqual(len(calls), 1)
        self.assertIn("permanent HTTP 404", report["failed"][0])
        self.assertFalse((self.out / "ABCDEFGH1234-hqdefault.jpg").exists())
        self.assertEqual(self.sleeps, [])

    # 3. HTTP 429 - retried then success
    def test_http_429_retried_then_success(self):
        self.html(("ABCDEFGH1234", "hq"))
        responses = {("ABCDEFGH1234", "hq"): [http_error(429), JPEG]}
        report, calls = self.run_sync(responses)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(report["downloaded"]), 1)
        self.assertEqual(self.sleeps, [1.0])

    # 4. HTTP 5xx - transient
    def test_http_5xx_is_transient(self):
        self.html(("ABCDEFGH1234", "hq"))
        responses = {("ABCDEFGH1234", "hq"): [http_error(503), JPEG]}
        report, calls = self.run_sync(responses)
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["downloaded"], ["ABCDEFGH1234-hqdefault"])

    # 5. timeout / network error
    def test_network_timeout_retried(self):
        self.html(("ABCDEFGH1234", "hq"))
        responses = {("ABCDEFGH1234", "hq"): [TimeoutError("timed out"), JPEG]}
        report, calls = self.run_sync(responses)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(report["downloaded"]), 1)

    # 6. invalid image response
    def test_invalid_image_response_rejected(self):
        self.html(("ABCDEFGH1234", "hq"))
        responses = {("ABCDEFGH1234", "hq"): [b"not a jpeg at all" * 200]}
        report, _ = self.run_sync(responses)
        self.assertIn("invalid image (not-a-jpeg)", report["failed"][0])
        self.assertFalse((self.out / "ABCDEFGH1234-hqdefault.jpg").exists())

    # 7. empty response
    def test_empty_response_rejected(self):
        self.html(("ABCDEFGH1234", "hq"))
        report, _ = self.run_sync({("ABCDEFGH1234", "hq"): [b""]})
        self.assertIn("invalid image (empty response)", report["failed"][0])

    # 8. partial download (valid magic, too small)
    def test_partial_download_rejected(self):
        self.html(("ABCDEFGH1234", "hq"))
        report, _ = self.run_sync({("ABCDEFGH1234", "hq"): [b"\xff\xd8\xff" + b"X" * 10]})
        self.assertIn("too-small", report["failed"][0])

    # 9. existing valid thumbnail cached, no network
    def test_existing_valid_thumbnail_is_cached(self):
        self.html(("ABCDEFGH1234", "hq"))
        (self.out / "ABCDEFGH1234-hqdefault.jpg").write_bytes(JPEG)
        report, calls = self.run_sync()
        self.assertEqual(report["cached"], ["ABCDEFGH1234-hqdefault"])
        self.assertEqual(len(calls), 0)

    # 10. existing corrupt thumbnail is replaced
    def test_existing_corrupt_thumbnail_replaced(self):
        self.html(("ABCDEFGH1234", "hq"))
        (self.out / "ABCDEFGH1234-hqdefault.jpg").write_bytes(b"corrupt")
        report, calls = self.run_sync()
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["downloaded"], ["ABCDEFGH1234-hqdefault"])
        self.assertTrue(_mod.file_is_valid(self.out / "ABCDEFGH1234-hqdefault.jpg"))

    # 11. missing one variant
    def test_missing_one_variant(self):
        self.html(("ABCDEFGH1234", "hq"), ("ABCDEFGH1234", "mq"))
        responses = {("ABCDEFGH1234", "hq"): [JPEG], ("ABCDEFGH1234", "mq"): [http_error(404)]}
        report, _ = self.run_sync(responses)
        self.assertEqual(len(report["downloaded"]), 1)
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(report["unresolved"], ["assets/img/yt/ABCDEFGH1234-mqdefault.jpg"])

    # 12. missing both variants
    def test_missing_both_variants(self):
        self.html(("ABCDEFGH1234", "hq"), ("ABCDEFGH1234", "mq"))
        responses = {
            ("ABCDEFGH1234", "hq"): [http_error(404)],
            ("ABCDEFGH1234", "mq"): [http_error(404)],
        }
        report, _ = self.run_sync(responses)
        self.assertEqual(len(report["unresolved"]), 2)

    # 13. duplicate video IDs deduped
    def test_duplicate_references_are_deduped(self):
        self.html(("ABCDEFGH1234", "hq"), ("ABCDEFGH1234", "hq"))
        (self.root / "other.html").write_text(
            '<img src="/assets/img/yt/ABCDEFGH1234-hqdefault.jpg">', encoding="utf-8"
        )
        report, calls = self.run_sync()
        self.assertEqual(report["wanted"], 1)
        self.assertEqual(len(calls), 1)

    # 14. retry exhaustion
    def test_retry_exhaustion(self):
        self.html(("ABCDEFGH1234", "hq"))
        responses = {("ABCDEFGH1234", "hq"): [http_error(500), http_error(500), http_error(500)]}
        report, calls = self.run_sync(responses)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.sleeps, [1.0, 2.0])
        self.assertIn("attempt 3/3", report["failed"][0])

    # 15. atomic replacement leaves no temp file
    def test_atomic_replacement_no_temp_left(self):
        self.html(("ABCDEFGH1234", "hq"))
        self.run_sync()
        self.assertEqual(list(self.out.glob("*.tmp")), [])
        self.assertTrue(_mod.file_is_valid(self.out / "ABCDEFGH1234-hqdefault.jpg"))

    # 16. repeated execution is idempotent
    def test_idempotent_second_run(self):
        self.html(("ABCDEFGH1234", "hq"))
        report1, calls1 = self.run_sync()
        report2, calls2 = self.run_sync()
        self.assertEqual(len(calls1), 1)
        self.assertEqual(len(calls2), 0)
        self.assertEqual(report2["cached"], ["ABCDEFGH1234-hqdefault"])

    # 17. verify-only is read-only and gates correctly
    def test_verify_only_mode(self):
        self.html(("ABCDEFGH1234", "hq"))
        with patch.object(sys, "argv", ["sync", "--root", str(self.root), "--verify-only"]):
            self.assertEqual(_mod.main(), 1)
        self.assertFalse((self.out / "manifest.json").exists())
        (self.out / "ABCDEFGH1234-hqdefault.jpg").write_bytes(JPEG)
        with patch.object(sys, "argv", ["sync", "--root", str(self.root), "--verify-only"]):
            self.assertEqual(_mod.main(), 0)

    # Extra: remote JSON-LD URL is still discovered (backward compatibility)
    def test_remote_url_discovery(self):
        (self.root / "index.html").write_text(
            '<script type="application/ld+json">{"thumbnailUrl":'
            '["https://i.ytimg.com/vi/ABCDEFGH1234/hqdefault.jpg"]}</script>',
            encoding="utf-8",
        )
        report, calls = self.run_sync()
        self.assertEqual(report["wanted"], 1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
