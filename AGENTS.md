# Agent Communication Protocol

## Structural Changes — Always Coordinate First

Before making any structural changes to the site (closing pages, merging hubs, redirecting sections, adding/removing major nav links), **communicate with the other agent first**.

Examples of structural changes:
- Merging or closing section hubs (e.g. missions/ + bosses/ → patches/)
- Adding or removing nav links across 100+ files
- Creating bulk redirects
- Changing sitemap structure

**Why:** On September 11, 2026, both agents worked on overlapping structural changes simultaneously — one was creating 75+ exotic pages while the other was restoring missions/ from redirect. We got lucky it didn't break anything, but next time it could.

## Workflow

1. Before starting a structural change, check if another agent is working on related files
2. If uncertain, ask in the shared context
3. After completing structural changes, note what changed so the other agent knows

## File Encoding Rule

PowerShell `Get-Content` / `Set-Content` corrupts Turkish and special characters. Always use:
```powershell
[System.IO.File]::ReadAllText($path, (New-Object System.Text.UTF8Encoding $false))
[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding $false))
```

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
