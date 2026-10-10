# Agent Communication Protocol

## Session Start — Mandatory First Step
Every agent opened here must, before starting work:
1. Read ALL `.md` files in the `agents/` folder (README → SITE-NOTES → the relevant area docs)
2. Take over any work another agent left unfinished
3. Append a dated entry to `agents/SITE-NOTES.md` after finishing every task (append only, never overwrite)

An agent that starts without reading flies blind. An agent that does not write notes does not exist.

## Structural Changes — Always Coordinate First

Before making any structural changes to the site (closing pages, merging hubs, redirecting sections, adding/removing major nav links), **communicate with the other agent first**.

Examples of structural changes:
- Merging or closing section hubs (e.g. missions/ + bosses/ → patches/)
- Adding or removing nav links across 100+ files
- Creating bulk redirects
- Changing sitemap structure

**Why:** On September 11, 2026, both agents worked on overlapping structural changes simultaneously — one was creating 75+ exotic pages while the other was restoring missions/ from redirect. We got lucky it didn't break anything, but next time it could.

## Language And Privacy Rules (MANDATORY)

The site is an international English-language archive. **Never write Turkish into any tracked file.**

1. All code, comments, docs, reports and page content are English.
2. Never write local filesystem paths (`C:\Users\...`, `/Users/<name>/`, `/home/<name>/`).
3. Never write personal names, email addresses, phone numbers, IP addresses, or tokens.
4. Never write country/region identifiers (Turkish cities, `tr-TR`, `Europe/Istanbul`, `₺`, `+90`).
5. `GSC-QUEUE.txt` is local-only and must stay out of git (`git rm --cached` if it ever gets tracked).

Run `python scripts/check_lang_privacy.py` before pushing. It fails on Turkish text, local paths, emails and region markers, and it has a small allowlist so legitimate game data passes.

**Known legitimate exceptions:** `assets/data/build-maker.json` contains "Ekim's Long Stick", a real named weapon in The Division 2 (M700 variant). Do not "fix" it.

## Workflow

1. Before starting a structural change, check if another agent is working on related files
2. If uncertain, ask in the shared context
3. After completing structural changes, note what changed so the other agent knows

## File Encoding Rule

Always write UTF-8 without BOM, and verify after writing. PowerShell `Out-File -Encoding ascii` silently replaces non-ASCII characters with `?` — use Python (`pathlib.Path.write_text(..., encoding="utf-8")`) or `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding $false))`.

## Content Quality — CJK Character Check (MANDATORY)

**Before pushing ANY HTML or Markdown content**, run this check:

```powershell
Select-String -Path "*.html","*.md" -Pattern "[\u4e00-\u9fff]"
```

AI models sometimes generate Chinese/Japanese/Korean (CJK) characters unintentionally when writing English content. These characters slip through because they look plausible in context.

**Common CJK characters found in AI output:**
| Character | Meaning | Replace with |
|---|---|---|
| 密集 | dense/concentrated | dense, heavy |
| 消化 | digest/process | digest, handle |
| 套路 | formula/routine | formula, pattern |

**If CJK characters are found:** Replace with English equivalents before committing.

See `agents/content-checklist.md` for the full pre-push checklist.

## STRUCTURE (repo root)
- `division-2/` (349 files), `lore/` (183), `content/` (169), `assets/` (100) — content body
- `scripts/` (17 py) — pipeline; `.github/workflows/` (7) — automation
- `sitemap.xml` + `sitemap.txt` + `llms.txt` + `feed.xml` — ALL updated on every new page
- `GSC-QUEUE.txt` — indexing queue, never committed

## PIPELINE (scripts/, run from the repo root)
- `build_lore.py` (34KB) — lore regen; `add_videos.py` (31KB) — video pages
- `discover_youtube.py` — RSS retry+backoff, silent exit 0 if all fail (datacenter 404s are normal)
- `update-escalation-data.py` (43KB, the largest) — escalation data
- `validate_lore.py` + `test_validate_lore.py` — the ONLY test infrastructure in the repo
- When a template changes, update `build_lore.py` + `add_videos.py` TOGETHER (done during the nav merge)

## WORKFLOWS
update-videos, refresh-build-maker-data, update-escalation-data, update-maintenance-notices, validate-lore, seo-audit, weekly-digest.
GitHub Actions schedule can lag → fallback: manual `gh workflow run` (SITE-NOTES, 12 Sep).

## GSC
- Submission is the user's job: URL Inspection → Request Indexing (~10 per day quota). Agent: monitoring + queue upkeep.
- After deploy, Pages can lag ~15+ min — verify content on `origin/main` first.
