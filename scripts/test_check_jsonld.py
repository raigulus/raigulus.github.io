# -*- coding: utf-8 -*-
"""Isolated tests for check_jsonld.py using temporary fixtures."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_jsonld", SCRIPTS / "check_jsonld.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def page(block):
    return '<html><head><script type="application/ld+json">%s</script></head></html>' % block


class JsonLdTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative, content):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_valid_website_block(self):
        data = {"@context": "https://schema.org", "@type": "WebSite", "name": "Site", "url": "https://example.test/"}
        self.write("index.html", page(json.dumps(data)))
        self.assertEqual(_mod.check_repository(self.root)[0], [])

    def test_malformed_json_is_reported(self):
        self.write("index.html", page("{not json"))
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["problem"], "malformed JSON")

    def test_empty_object_is_reported(self):
        self.write("index.html", page("{}"))
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["problem"], "empty JSON-LD")

    def test_array_of_objects_supported(self):
        nodes = [
            {"@context": "https://schema.org", "@type": "WebSite", "name": "S", "url": "u"},
            {"@context": "https://schema.org", "@type": "Organization", "name": "O", "url": "u"},
        ]
        self.write("index.html", page(json.dumps(nodes)))
        self.assertEqual(_mod.check_repository(self.root)[0], [])

    def test_graph_container_supported(self):
        data = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebPage", "name": "P", "url": "u"},
                {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.test/"}]},
            ],
        }
        self.write("index.html", page(json.dumps(data)))
        self.assertEqual(_mod.check_repository(self.root)[0], [])

    def test_missing_context_and_type_reported(self):
        self.write("index.html", page(json.dumps({"name": "X"})))
        issues, _ = _mod.check_repository(self.root)
        problems = [i["problem"] for i in issues]
        self.assertIn("missing @context", problems)
        self.assertIn("missing @type", problems)

    def test_missing_expected_field_reported(self):
        data = {"@context": "https://schema.org", "@type": "ItemList", "name": "List"}
        self.write("index.html", page(json.dumps(data)))
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues[0]["problem"], "missing expected field")
        self.assertIn("itemListElement", issues[0]["detail"])

    def test_unknown_type_only_needs_context_and_type(self):
        data = {"@context": "https://schema.org", "@type": "CustomThing", "anything": 1}
        self.write("index.html", page(json.dumps(data)))
        self.assertEqual(_mod.check_repository(self.root)[0], [])

    def test_error_message_includes_source_file(self):
        self.write("deep/page/index.html", page("{broken"))
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues[0]["file"], "deep/page/index.html")

    def test_excluded_dirs_not_scanned(self):
        self.write("seo-reports/index.html", page("{broken"))
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues, [])

    def test_cli_exit_codes_strict_and_warn_only(self):
        self.write("index.html", page("{broken"))
        strict = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_jsonld.py"), "--root", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(strict.returncode, 1)
        warn = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_jsonld.py"), "--root", str(self.root), "--warn-only"],
            capture_output=True, text=True,
        )
        self.assertEqual(warn.returncode, 0)
        self.assertIn("warn-only", warn.stdout)


if __name__ == "__main__":
    unittest.main()
