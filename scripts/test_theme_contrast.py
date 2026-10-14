# -*- coding: utf-8 -*-
"""Text tokens must clear AA on the surfaces of the theme that defines them.

test_contrast.py pairs a token with a surface, which catches a value that is too
weak for its own palette. It cannot catch a value that is correct for one theme
and carried unchanged into another, because the pair still resolves inside the
first theme. That failure is real: a light palette that left the text tokens
alone put #edf0f4 on #f7f6f3, a ratio of 1.06, while every pair in the other
test passed.

So this resolves each theme on its own terms -- base tokens plus that theme's
overrides -- and checks the text tokens against the surfaces the same theme
defines.

Run: python -m scripts.test_theme_contrast
"""
import io
import os
import re
import unittest

from scripts.test_contrast import parse_hex, ratio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "assets", "styles.css")

# Tokens that carry body copy or metadata. A theme that redefines the surfaces
# has to redefine these too.
TEXT_TOKENS = [
    "--text", "--text-sub", "--text-dim", "--text-dim-card", "--page-ink",
    "--muted", "--muted-2", "--muted-3", "--eyebrow-ink",
    "--status-ok-ink", "--status-bad-ink", "--status-warn-ink",
]

# The page surfaces a theme paints text onto, and what actually carries each
# one. body paints on --page-bg, so a page-ink check against --bg would pass by
# coincidence until the two were pulled apart.
SURFACES = ["--bg", "--surface", "--surface2", "--page-bg"]
CARRIED_ON = {
    "--page-ink": ["--page-bg", "--bg", "--surface"],
    "--text": ["--bg", "--surface", "--surface2"],
    "--text-sub": ["--bg", "--surface", "--surface2"],
    "--text-dim": ["--bg", "--surface", "--surface2"],
    "--text-dim-card": ["--bg", "--surface", "--surface2"],
    "--muted": ["--bg", "--surface", "--surface2"],
    "--muted-2": ["--bg", "--surface", "--surface2"],
    "--muted-3": ["--bg", "--surface", "--surface2"],
    "--eyebrow-ink": ["--bg", "--surface", "--surface2"],
    "--status-ok-ink": ["--surface"],
    "--status-bad-ink": ["--surface"],
    "--status-warn-ink": ["--surface"],
}


def _tokens(block):
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", block))


class TestThemeContrast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        css = io.open(CSS_PATH, encoding="utf-8").read()
        # Every bare :root applies, and a later one wins, which is how the page
        # tokens reach the palette that also owns the dossier tokens.
        base, themes = {}, {}
        for m in re.finditer(r":root(\[[^\]]+\])?\s*\{([^}]*)\}", css, re.S):
            found = _tokens(m.group(2))
            if m.group(1) is None:
                base.update(found)
                continue
            themes[m.group(1)] = found
        cls.base = base
        cls.themes = themes

    def test_every_theme_defines_the_surfaces_it_is_measured_against(self):
        for label, extra in sorted(self.themes.items()):
            resolved = dict(self.base, **extra)
            missing = sorted(set(SURFACES) - set(resolved))
            self.assertEqual(missing, [], "%s is missing %s" % (label, missing))

    def test_no_theme_leaves_a_text_token_unreadable_on_its_own_surfaces(self):
        problems = []
        for label, extra in [("default", {})] + sorted(self.themes.items()):
            toks = dict(self.base, **extra)
            for fg in TEXT_TOKENS:
                if fg not in toks:
                    problems.append("%s: %s is not defined" % (label, fg))
                    continue
                for bg in CARRIED_ON.get(fg, SURFACES):
                    if bg not in toks:
                        continue
                    got = ratio(parse_hex(toks[fg]), parse_hex(toks[bg]))
                    if got < 4.5:
                        problems.append("%s: %s (%s) on %s (%s) = %.2f, needs 4.5"
                                        % (label, fg, toks[fg], bg, toks[bg], got))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_light_palette_actually_redefines_the_text_tokens(self):
        """A surface flip with no text flip is the exact failure this guards."""
        if "[data-theme=light]" not in self.themes:
            self.skipTest("no light theme")
        light = self.themes["[data-theme=light]"]
        unchanged = sorted(
            name for name in TEXT_TOKENS
            if name in light and light[name].lower() == self.base.get(name, "").lower())
        self.assertEqual(unchanged, [],
                         "light redefines the surfaces but keeps these text tokens: %s"
                         % unchanged)


if __name__ == "__main__":
    unittest.main(verbosity=2)