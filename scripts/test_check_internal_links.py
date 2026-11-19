# -*- coding: utf-8 -*-
"""Isolated tests for check_internal_links.py using temporary fixtures."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_internal_links", SCRIPTS / "check_internal_links.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class InternalLinkTests(unittest.TestCase):
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

    def test_valid_root_relative_directory_link(self):
        self.write("index.html", '<a href="/guides/">Guides</a>')
        self.write("guides/index.html", "<h1>Guides</h1>")
        issues, checked = _mod.check_repository(self.root)
        self.assertEqual(issues, [])
        self.assertEqual(checked, 1)

    def test_missing_root_relative_target_is_reported(self):
        self.write("index.html", '<a href="/missing/">Missing</a>')
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["problem"], "missing target")
        self.assertIn("/missing/", issues[0]["target"])

    def test_relative_link_and_image_src(self):
        self.write("a/index.html", '<img src="../assets/x.png"><a href="b/">B</a>')
        self.write("assets/x.png", "binary")
        self.write("a/b/index.html", "<h1>B</h1>")
        issues, checked = _mod.check_repository(self.root)
        self.assertEqual(issues, [])
        self.assertEqual(checked, 2)

    def test_missing_image_src_is_reported_with_source_file(self):
        self.write("a/index.html", '<img src="/assets/no.png">')
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["file"], "a/index.html")
        self.assertEqual(issues[0]["problem"], "missing target")

    def test_srcset_variants_checked(self):
        self.write("p/index.html", '<img src="/a.jpg" srcset="/a.jpg 1x, /b.jpg 2x">')
        self.write("a.jpg", "binary")
        self.write("b.jpg", "binary")
        issues, checked = _mod.check_repository(self.root)
        self.assertEqual(issues, [])
        self.assertEqual(checked, 3)

    def test_external_and_placeholder_links_ignored(self):
        self.write(
            "index.html",
            '<a href="https://example.com/">ext</a><a href="mailto:a@b.c">mail</a>'
            '<a href="#">top</a><a href="//cdn.example.com/x">cdn</a>',
        )
        issues, checked = _mod.check_repository(self.root)
        self.assertEqual(issues, [])
        self.assertEqual(checked, 0)

    def test_query_and_url_encoded_paths(self):
        self.write("index.html", '<a href="/guides%20list/?q=test">Guides</a>')
        self.write("guides list/index.html", "<h1>Guides</h1>")
        issues, checked = _mod.check_repository(self.root)
        self.assertEqual(issues, [])
        self.assertEqual(checked, 1)

    def test_valid_fragment_id(self):
        self.write("index.html", '<a href="/page/#section">S</a>')
        self.write("page/index.html", '<div id="section">S</div>')
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues, [])

    def test_missing_fragment_id_is_reported(self):
        self.write("index.html", '<a href="/page/#nope">S</a>')
        self.write("page/index.html", "<div>no ids</div>")
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["problem"], "missing fragment id")

    def test_query_style_fragment_is_ignored(self):
        self.write("index.html", '<a href="/page/#tag=frost">T</a>')
        self.write("page/index.html", "<div>search page</div>")
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues, [])

    def test_excluded_dirs_are_not_scanned(self):
        self.write("seo-reports/index.html", '<a href="/missing/">x</a>')
        self.write(".git/index.html", '<a href="/missing/">x</a>')
        self.write("index.html", "<h1>ok</h1>")
        issues, _ = _mod.check_repository(self.root)
        self.assertEqual(issues, [])

    def test_cli_exit_codes_strict_and_warn_only(self):
        import subprocess
        import sys

        self.write("index.html", '<a href="/missing/">x</a>')
        strict = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_internal_links.py"), "--root", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(strict.returncode, 1)
        warn = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_internal_links.py"), "--root", str(self.root), "--warn-only"],
            capture_output=True, text=True,
        )
        self.assertEqual(warn.returncode, 0)
        self.assertIn("warn-only", warn.stdout)


if __name__ == "__main__":
    unittest.main()
