# -*- coding: utf-8 -*-
"""Contrast ratios for every theme the stylesheet defines.

A theme swap is a colour change on every page in the repo, and eyeballing 751
pages is not possible. This computes the WCAG ratio for each text/surface pair
per theme so a palette that quietly fails is caught in CI instead of by a
visitor.

Run: python -m scripts.test_contrast
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "assets", "styles.css")

# Foreground -> backgrounds it has to stay legible on.
PAIRS = [
    ("--text", "--bg", 4.5),
    ("--text", "--surface", 4.5),
    ("--text", "--surface2", 4.5),
    ("--text-sub", "--bg", 4.5),
    ("--text-sub", "--surface", 4.5),
    ("--text-dim", "--bg", 4.5),
    ("--accent", "--bg", 3.0),
    ("--accent", "--surface", 3.0),
    ("--mission", "--surface", 3.0),
]


def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def parse_hex(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) == 6:
        value += "ff"
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def parse_any(value):
    value = value.strip()
    if value.startswith("#"):
        return parse_hex(value)
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", value)
    if m:
        return tuple(int(float(m.group(i))) for i in (1, 2, 3))
    return None


def channel(value):
    value = value / 255.0
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (channel(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def tokens_of(block):
    found = {}
    for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", block):
        parsed = parse_any(value)
        if parsed:
            found[name] = parsed
    return found


class TestContrast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = read(CSS_PATH)
        base = {}
        overrides = {}
        for m in re.finditer(r":root(\[[^\]]+\])?\s*\{([^}]*)\}", cls.css, re.S):
            selector = m.group(1)
            found = tokens_of(m.group(2))
            if selector is None:
                # A second bare :root is the archive dossier palette, which keeps
                # its own names. Labeling both "default" made the later block
                # overwrite the base and every pair came back undefined.
                if "--bg" in found:
                    base = found
                continue
            overrides[selector] = found
        cls.base = base
        cls.overrides = overrides

    def test_the_base_theme_defines_every_checked_token(self):
        missing = sorted({n for pair in PAIRS for n in pair[:2]} - set(self.base))
        self.assertEqual(missing, [], "base :root is missing %s" % missing)

    def test_no_theme_fails_its_contrast_pairs(self):
        problems = []
        themes = [("default", {})] + sorted(self.overrides.items())
        for label, extra in themes:
            toks = dict(self.base)
            toks.update(extra)
            for fg_name, bg_name, floor in PAIRS:
                if fg_name not in toks or bg_name not in toks:
                    problems.append("%s: %s / %s not both defined"
                                    % (label, fg_name, bg_name))
                    continue
                got = ratio(toks[fg_name], toks[bg_name])
                if got < floor:
                    problems.append("%s: %s on %s = %.2f, needs %.1f"
                                    % (label, fg_name, bg_name, got, floor))
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)