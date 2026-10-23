#!/usr/bin/env python3
"""Pre-push guard: English-only + no local/region/identity leaks in tracked files.

Run from the repo root:  python scripts/check_lang_privacy.py
Exit code 1 when something is wrong, so it can gate a push or a CI job.

Checks
  1. Turkish text (characters and function words)
  2. Local filesystem paths (Windows / macOS / Linux)
  3. Real email addresses (placeholders like you@example.com are allowed)
  4. Region markers (Turkish cities, locales, currency, phone prefix)
  5. Secret-looking tokens

There is a small allowlist so legitimate content passes - see ALLOW below.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
SUFFIXES = {".html", ".css", ".js", ".json", ".md", ".txt", ".xml", ".py", ".yml", ".yaml", ".svg", ".csv"}

# --- Turkish -----------------------------------------------------------------
# Turkish letters, matched unconditionally.
#
# The previous pattern guarded c-C-c-O-O-u-U with lookarounds so it would only
# fire on a character that does not touch an ASCII letter. That was backwards:
# the letter it skipped is the one that appears in the middle of a Turkish word,
# so "Veri yukleniyor" sailed straight through while "Turkiye'de" got caught by
# its g. Every Turkish letter is now matched wherever it appears. A handful of
# loanwords (cafe, facade, Angstrom) may need an allowlist entry; silently
# missing real Turkish copy is the worse failure.
TR_CHARS = re.compile("[ıİşŞğĞçÇöÖüÜ]")
# Deliberately excludes bare "not" (Turkish for "not") because it collides with
# the English keyword and produces thousands of false positives.
TR_WORDS = re.compile(
    r"(?i)\b(?:için|icin|değil|degil|olarak|ancak|göre|gore|üzere|uzere|çok|cok|"
    r"veri|yükle\w*|yukle\w*|arama|işlem\w*|islem\w*|sonuç\w*|sonuc\w*|göster\w*|"
    r"goster\w*|tıklama\w*|tiklama\w*|güncel\w*|guncel\w*|hata|dosya\w*|klasör\w*|"
    r"klavor\w*|başlangıç\w*|başla\w*|bitince|açıklama\w*|açık\w*|değişiklik\w*|"
    r"düşük\w*|dusuk\w*|güncelle\w*|guncelle\w*|kaldır\w*|kaldir\w*|yedekle\w*|"
    r"çalıştır\w*|calistir\w*|şey|vardır\w*|gibi|kadar|sonra|önce|"
    r"hâlâ|hala|başka|baska|aynı|ayni|nasıl|nasil|çünkü|çıktı|cıkti|adet|rapor\w*|"
    r"sorgu\w*|sayfa\w*|şema\w*|analiz\w*|öneri\w*|oneri\w*|kırık\w*|kirik\w*|"
    r"karşılaştırma\w*|karsilastirma\w*|takip\w*|şey|"
    r"Türkiye|Türkçe|türkçe|düzen\w*|duzen\w*|bulunamadı\w*|hata)\b"
)

# --- leaks -------------------------------------------------------------------
LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/][^\\\"'<>]{1,60}"
                        r"|/(?:Users|home)/[A-Za-z0-9._-]+/[^\"'<>]{1,40}"
                        r"|OneDrive|AppData|%USERPROFILE%|%APPDATA%)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@?(?:example|test|localhost|domain|your|you)\.", re.I)
# The published privacy contact is intentionally public. Every other address
# still fails the guard, including personal and role addresses.
EMAIL_ALLOW = {"raigulus.official@gmail.com"}
REGION = re.compile(r"(?:\btr[-_]TR\b|\btr[-_]EDU\b|Europe/Istanbul|Asia/Istanbul"
                    r"|\bTürkiye\b|\bTurkiye\b|\bTURKIYE\b"
                    r"|\b(?:Istanbul|İstanbul|Ankara|İzmir|Izmir|Antalya|Bursa|Gaziantep|Trabzon)\b"
                    r"|\+90[\s\-(]|\bTL\b|₺|\bTRY\b)")
TOKEN = re.compile(r"(?:ghp_|gho_|github_pat_|xox[baprs]-|AKIA)[A-Za-z0-9_\-]{10,}")

# --- allowlist ---------------------------------------------------------------
# (path glob, reason) - the file is exempt from the Turkish check.
# (path glob, regex, reason) - exempt from one specific pattern.
ALLOW = [
    ("scripts/check_lang_privacy.py", "contains the detection patterns themselves"),
    ("AGENTS.md", "documents the rules and quotes CJK examples on purpose"),
    ("assets/data/build-maker.json", "'Ekim\'s Long Stick' is a real Division 2 named weapon (M700)"),
    ("assets/data/build-maker-prev.json", "same build data, previous snapshot"),
    ("seo-reports/gsc-report-*.md", "captured GSC query strings; 'baska site' is a real query"),
    ("assets/data/gsc-analytics.json", "captured GSC query strings in several languages, e.g. Spanish"),
]


def _matches(path: str, pattern: str) -> bool:
    import fnmatch
    return fnmatch.fnmatch(path, pattern) or path.endswith("/" + pattern)


def is_allowed(path: str) -> bool:
    return any(_matches(path, pat) for pat, _ in ALLOW)


def main() -> int:
    # Only git-tracked files matter: local-only files (GSC-QUEUE.txt) never ship.
    names = []
    try:
        import subprocess
        res = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60)
        names = [n for n in res.stdout.split("\0") if n]
    except Exception:
        names = []
    if names:
        files = [ROOT / n for n in names
                 if (ROOT / n).suffix.lower() in SUFFIXES
                 and not (SKIP_DIRS & set((ROOT / n).parts))]
    else:
        files = [p for p in ROOT.rglob("*")
                 if p.is_file()
                 and not (SKIP_DIRS & set(p.parts))
                 and p.suffix.lower() in SUFFIXES]
    files = [p for p in files if not is_allowed(str(p.relative_to(ROOT)).replace("\\", "/"))]

    problems = []
    for f in files:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.split("\n"), 1):
            if len(line) > 4000:
                line = line[:4000]
            if not is_allowed(rel):
                m = TR_CHARS.search(line) or TR_WORDS.search(line)
                if m:
                    problems.append((rel, i, "turkish", m.group(0), line.strip()[:90]))
            m = LOCAL_PATH.search(line)
            if m:
                problems.append((rel, i, "local-path", m.group(0), line.strip()[:90]))
            m = EMAIL.search(line)
            if m and not EMAIL_OK.search(m.group(0)) and m.group(0).lower() not in EMAIL_ALLOW:
                problems.append((rel, i, "email", m.group(0), line.strip()[:90]))
            m = REGION.search(line)
            if m:
                problems.append((rel, i, "region", m.group(0), line.strip()[:90]))
            m = TOKEN.search(line)
            if m:
                problems.append((rel, i, "token", m.group(0)[:16], line.strip()[:90]))

    scanned = len(files)
    if not problems:
        print(f"OK - {scanned} files scanned. No Turkish text, local paths, "
              f"emails, region markers or tokens.")
        return 0

    by_kind = {}
    for rel, i, kind, frag, line in problems:
        by_kind.setdefault(kind, []).append((rel, i, frag, line))

    print(f"FAIL - {len(problems)} problem(s) in {scanned} files scanned:\n")
    for kind, rows in sorted(by_kind.items()):
        print(f"  [{kind}] {len(rows)}")
        for rel, i, frag, line in rows[:12]:
            print(f"     {rel}:{i}  {frag!r}")
            print(f"        {line}")
        if len(rows) > 12:
            print(f"     ... and {len(rows) - 12} more")
        print()
    return 1


def _self_test() -> int:
    # Guards the Turkish detector itself. The build maker shipped "Veri yukleniyor"
    # for months because the old lookaround only matched c/o/u when they did not
    # touch an ASCII letter, so the one inside the word went unnoticed while every
    # guard run reported OK. These cases are the regression.
    must_catch = [
        "Veri yukleniyor...",
        "Veri yükleniyor...",
        "Sayfa yüklenemedi",
        "Dosya bulunamadı",
        "hata occurred",
        "Türkçe içerik",
        "gösterim",
    ]
    must_pass = [
        "Loading data...",
        "The page loaded without errors.",
        "Once the boss spawns, the window opens.",
        "One half of the Hyenas command pair at Bank Headquarters.",
        "Choose your gear, weapons, and skills.",
        "café facade",
        "Load Data Here",
        "Divide the file into parts.",
    ]
    failed = []
    for s in must_catch:
        if not (TR_CHARS.search(s) or TR_WORDS.search(s)):
            failed.append(f"MISSED Turkish: {s!r}")
    for s in must_pass:
        if TR_CHARS.search(s) or TR_WORDS.search(s):
            failed.append(f"FALSE POSITIVE: {s!r}")
    if failed:
        print("SELF-TEST FAILED:")
        for f in failed:
            print("  " + f)
        return 1
    print(f"Self-test OK: {len(must_catch)} Turkish strings caught, "
          f"{len(must_pass)} English strings passed.")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    sys.exit(main())
