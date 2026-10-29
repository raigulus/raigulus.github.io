# Agent Communication Protocol

## Session Start - Mandatory First Step
Every agent opened here must, before starting work:
1. Read ALL `.md` files in the `agents/` folder (README, then SITE-NOTES, then the relevant area docs)
2. Take over any work another agent left unfinished
3. Append a dated entry to `agents/SITE-NOTES.md` after finishing every task (append only, never overwrite)

An agent that starts without reading flies blind. An agent that does not write notes does not exist.

## This File Is Public

Jekyll is disabled for this repository (`.nojekyll`), so GitHub Pages serves every tracked file as-is, this one included. Keep incident logs, local tooling details, credentials and internal schedules in `agents/` (excluded from git). Anything committed here is downloadable by anyone.

## Structural Changes - Always Coordinate First

Before making any structural change to the site (closing pages, merging hubs, redirecting sections, adding or removing major nav links), communicate with the other agent first.

Examples of structural changes:
- Merging or closing section hubs (for example missions/ and bosses/ into patches/)
- Adding or removing nav links across 100+ files
- Creating bulk redirects
- Changing sitemap structure

Two agents once ran overlapping structural work in the same week, one creating dozens of new pages while the other restored a section from a redirect. Nothing broke, but only by luck.

## Language And Privacy Rules (MANDATORY)

The site is an international English-language archive. Never write Turkish into any tracked file.

1. All code, comments, docs, reports and page content are English.
2. Never write absolute filesystem paths (Windows drive paths, macOS or Linux home directories).
3. Never write personal names, email addresses, phone numbers, IP addresses, or tokens. Exception: the published privacy contact address in `privacy/` and `terms/` is intentional and allowlisted in `scripts/check_lang_privacy.py`; never add any other email.
4. Never write country or region identifiers: city names, locale codes, currency symbols, phone country prefixes.
5. `GSC-QUEUE.txt` is local-only and must stay out of git (`git rm --cached` if it ever gets tracked).
6. `seo-reports/` is local-only too: the weekly workflow uploads it as a build artifact and never commits it.

Run `python scripts/check_lang_privacy.py` before pushing. It fails on Turkish text, local paths, emails, region markers and secret-looking tokens. Only the Turkish check has an allowlist, for game data and the checker itself; every published file is still scanned for leaks.

**Known legitimate exception:** `assets/data/build-maker.json` contains a weapon name that collides with a personal name and with the Turkish word list. It is real game data (an M700 variant); do not "fix" it.

## Workflow

1. Before starting a structural change, check if another agent is working on related files
2. If uncertain, ask in the shared context
3. After completing structural changes, note what changed so the other agent knows

## File Encoding Rule

Always write UTF-8 without BOM, and verify after writing. PowerShell `Out-File -Encoding ascii` silently replaces non-ASCII characters with `?`, so use Python (`pathlib.Path.write_text(..., encoding="utf-8")`) or `[System.IO.File]::WriteAllText` with a BOM-less UTF-8 encoder instead.

## Content Quality - CJK Character Check (MANDATORY)

Before pushing ANY HTML or Markdown content, run this check:

```powershell
Select-String -Path "*.html","*.md" -Pattern "[\u4e00-\u9fff]"
```

AI models sometimes generate Chinese, Japanese or Korean (CJK) characters unintentionally when writing English content. These characters slip through because they look plausible in context.

**Common CJK characters found in AI output:**
| Character | Meaning | Replace with |
|---|---|---|
| U+5BC6 U+96C6 | dense/concentrated | dense, heavy |
| U+6D88 U+5316 | digest/process | digest, handle |
| U+5957 U+8DEF | formula/routine | formula, pattern |

**If CJK characters are found:** replace them with English equivalents before committing.

See `agents/content-checklist.md` for the full pre-push checklist.

## STRUCTURE (repo root)
- `division-2/` (349 files), `lore/` (183), `content/` (169), `assets/` (100) - content body
- `scripts/` (17 py) - pipeline; `.github/workflows/` (7) - automation
- `sitemap.xml` + `sitemap.txt` + `llms.txt` + `feed.xml` - ALL updated on every new page
- `GSC-QUEUE.txt` - indexing queue, never committed

## PIPELINE (scripts/, run from the repo root)
- `build_lore.py` (34KB) - lore regen; `add_videos.py` (31KB) - video pages
- `discover_youtube.py` - RSS retry and backoff, silent exit 0 if all fail (datacenter 404s are normal)
- `update-escalation-data.py` (43KB, the largest) - escalation data
- `validate_lore.py` + `test_validate_lore.py` - the ONLY test infrastructure in the repo
- When a template changes, update `build_lore.py` + `add_videos.py` TOGETHER (done during the nav merge)

## WORKFLOWS
update-videos, refresh-build-maker-data, update-escalation-data, update-maintenance-notices, validate-lore, seo-audit, weekly-digest.
The SEO workflow keeps its markdown reports in the run artifact (30 days) and only commits `assets/data/*.json`.
GitHub Actions schedule can lag, so the fallback is a manual `gh workflow run`.

## GSC
- Submission is the user's job: URL Inspection, then Request Indexing (about 10 per day).
- Agent handles monitoring and queue upkeep.
- After deploy, Pages can lag more than 15 minutes. Verify content on `origin/main` first.
