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
# ı/İ are the strongest signal; the rest are function words that do not exist
# in English. Deliberately excludes bare "not" (Turkish for "not") because it
# collides with the English keyword and produces thousands of false positives.
TR_CHARS = re.compile("[ıİşŞğĞ]|(?<![A-Za-z])[çÇöÖüÜ](?![A-Za-z])")
TR_WORDS = re.compile(
    r"(?i)\b(?:için|icin|değil|degil|olarak|ancak|göre|gore|üzere|uzere|çok|cok|"
    r"şey|vardır|vardir|gibi|kadar|sonra|önce|hâlâ|hala|başka|baska|"
    r"aynı|ayni|nasıl|nasil|çünkü|çıktı|cıkti|sonuç|sonuc|adet|rapor|"
    r"sorgu|sayfa|tıklama|tiklama|gösterim|kırık|öneri|oneri|şema|analiz|"
    r"karşılaştırma|karsilastirma|takip|güncelle|guncelle|kaldır|kaldir|"
    r"yedekle|çalıştır|calistir|hata|dosya|klasör|klavor|kontrol|"
    r"Türkiye|Türkçe|türkçe|başlangıç|bitince|açıklama|değişim|düşük)\b"
)

# --- leaks -------------------------------------------------------------------
LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/][^\\\"'<>]{1,60}"
                        r"|/(?:Users|home)/[A-Za-z0-9._-]+/[^\"'<>]{1,40}"
                        r"|OneDrive|AppData|%USERPROFILE%|%APPDATA%)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@?(?:example|test|localhost|domain|your|you)\.", re.I)
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
            if m and not EMAIL_OK.search(m.group(0)):
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


if __name__ == "__main__":
    sys.exit(main())
