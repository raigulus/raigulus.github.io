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
