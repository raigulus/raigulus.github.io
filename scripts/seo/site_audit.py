#!/usr/bin/env python3
"""
Raigulus SEO Tool - Site Audit
==========================================
Site SEO denetimi:
- Kırık linkler
- Meta tag kontrolü
- Schema markup
- Başlık uzunlukları
- Meta description kontrolü

Kullanım:
    python site_audit.py --full
    python site_audit.py --check-links
    python site_audit.py --check-meta
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "seo-reports"

# SEO Rules
MAX_TITLE_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 160
MIN_DESCRIPTION_LENGTH = 70


def check_links(html_files):
    """Check for broken links in HTML files."""
    broken_links = []
    all_links = []
    
    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8", errors="replace")
        
        # Find all links
        link_pattern = r'href=["\']([^"\']+)["\']'
        links = re.findall(link_pattern, content)
        
        for link in links:
            if link.startswith(("#", "mailto:", "javascript:")):
                continue
            
            # Convert relative to absolute
            if link.startswith("/"):
                link = f"https://raigulus.github.io{link}"
            elif not link.startswith("http"):
                link = f"https://raigulus.github.io/{link}"
            
            all_links.append({
                "file": str(html_file.relative_to(ROOT)),
                "link": link,
            })
    
    print(f"Found {len(all_links)} links to check...")
    
    # Check links (sample for speed)
    checked = 0
    for item in all_links[:100]:  # Check first 100 for speed
        link = item["link"]
        try:
            req = urllib.request.Request(link, method="HEAD", headers={"User-Agent": "RaigulusAudit/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except urllib.error.HTTPError as e:
            if e.code == 404:
                broken_links.append(item)
        except Exception:
            pass
        
        checked += 1
        if checked % 20 == 0:
            print(f"  Checked {checked}/{min(len(all_links), 100)}...")
    
    return broken_links


def check_meta_tags(html_files):
    """Check meta tags for SEO issues."""
    issues = []
    
    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8", errors="replace")
        rel_path = str(html_file.relative_to(ROOT))
        
        # Check title
        title_match = re.search(r"<title>([^<]+)</title>", content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if len(title) > MAX_TITLE_LENGTH:
                issues.append({
                    "file": rel_path,
                    "issue": "title_too_long",
                    "detail": f"Title is {len(title)} chars (max {MAX_TITLE_LENGTH})",
                    "value": title,
                })
        else:
            issues.append({
                "file": rel_path,
                "issue": "missing_title",
                "detail": "No <title> tag found",
            })
        
        # Check meta description
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if desc_match:
            desc = desc_match.group(1).strip()
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                issues.append({
                    "file": rel_path,
                    "issue": "description_too_long",
                    "detail": f"Description is {len(desc)} chars (max {MAX_DESCRIPTION_LENGTH})",
                    "value": desc[:100] + "...",
                })
            elif len(desc) < MIN_DESCRIPTION_LENGTH:
                issues.append({
                    "file": rel_path,
                    "issue": "description_too_short",
                    "detail": f"Description is {len(desc)} chars (min {MIN_DESCRIPTION_LENGTH})",
                    "value": desc,
                })
        else:
            issues.append({
                "file": rel_path,
                "issue": "missing_description",
                "detail": "No meta description found",
            })
        
        # Check canonical
        if 'rel="canonical"' not in content.lower():
            issues.append({
                "file": rel_path,
                "issue": "missing_canonical",
                "detail": "No canonical tag found",
            })
        
        # Check Open Graph
        if 'og:title' not in content.lower():
            issues.append({
                "file": rel_path,
                "issue": "missing_og_title",
                "detail": "No og:title tag found",
            })
        
        if 'og:description' not in content.lower():
            issues.append({
                "file": rel_path,
                "issue": "missing_og_description",
                "detail": "No og:description tag found",
            })
    
    return issues


def check_schema(html_files):
    """Check for structured data (JSON-LD)."""
    results = []
    
    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8", errors="replace")
        rel_path = str(html_file.relative_to(ROOT))
        
        # Find JSON-LD
        schema_pattern = r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>'
        schemas = re.findall(schema_pattern, content, re.DOTALL | re.IGNORECASE)
        
        has_schema = len(schemas) > 0
        schema_types = []
        
        for schema in schemas:
            try:
                data = json.loads(schema)
                if "@type" in data:
                    schema_types.append(data["@type"])
            except json.JSONDecodeError:
                pass
        
        results.append({
            "file": rel_path,
            "has_schema": has_schema,
            "schema_types": schema_types,
        })
    
    return results


def generate_audit_report(broken_links, meta_issues, schema_results):
    """Generate audit report."""
    report = f"""# Raigulus SEO Denetim Raporu

**Tarih:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Özet

| Kategori | Sayı |
|----------|------|
| Kırık Link | {len(broken_links)} |
| Meta Tag Sorunu | {len(meta_issues)} |
| Schema Olan Sayfa | {sum(1 for s in schema_results if s['has_schema'])} |
| Schema Olmayan Sayfa | {sum(1 for s in schema_results if not s['has_schema'])} |

## Kırık Linkler

"""
    
    if broken_links:
        for item in broken_links[:20]:
            report += f"- `{item['file']}` → {item['link']}\n"
    else:
        report += "✓ Kırık link bulunamadı\n"
    
    report += """
## Meta Tag Sorunları

"""
    
    if meta_issues:
        # Group by issue type
        issue_groups = {}
        for issue in meta_issues:
            issue_type = issue["issue"]
            if issue_type not in issue_groups:
                issue_groups[issue_type] = []
            issue_groups[issue_type].append(issue)
        
        for issue_type, issues in issue_groups.items():
            report += f"### {issue_type.replace('_', ' ').title()} ({len(issues)} adet)\n\n"
            for issue in issues[:10]:
                report += f"- `{issue['file']}`: {issue['detail']}\n"
            report += "\n"
    else:
        report += "✓ Meta tag sorunu bulunamadı\n"
    
    report += """
## Schema Markup

| Sayfa | Schema | Türler |
|-------|--------|--------|
"""
    
    for result in schema_results[:20]:
        status = "✓" if result["has_schema"] else "✗"
        types = ", ".join(result["schema_types"]) if result["schema_types"] else "-"
        report += f"| `{result['file']}` | {status} | {types} |\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Raigulus SEO Tool - Site Audit")
    parser.add_argument("--full", action="store_true", help="Run full audit")
    parser.add_argument("--check-links", action="store_true", help="Check for broken links")
    parser.add_argument("--check-meta", action="store_true", help="Check meta tags")
    parser.add_argument("--check-schema", action="store_true", help="Check schema markup")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    # Find all HTML files
    html_files = list(ROOT.rglob("*.html"))
    html_files = [f for f in html_files if "node_modules" not in str(f)]
    print(f"Found {len(html_files)} HTML files")
    
    broken_links = []
    meta_issues = []
    schema_results = []
    
    if args.full or args.check_links:
        print("\nChecking links...")
        broken_links = check_links(html_files)
        print(f"Found {len(broken_links)} broken links")
    
    if args.full or args.check_meta:
        print("\nChecking meta tags...")
        meta_issues = check_meta_tags(html_files)
        print(f"Found {len(meta_issues)} meta issues")
    
    if args.full or args.check_schema:
        print("\nChecking schema...")
        schema_results = check_schema(html_files)
        print(f"Checked {len(schema_results)} files")
    
    # Generate report
    if args.full or broken_links or meta_issues or schema_results:
        report = generate_audit_report(broken_links, meta_issues, schema_results)
        
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
            print(f"\n✓ Report saved: {args.output}")
        else:
            REPORTS.mkdir(exist_ok=True)
            filename = f"audit-report-{datetime.now().strftime('%Y-%m-%d')}.md"
            report_path = REPORTS / filename
            report_path.write_text(report, encoding="utf-8")
            print(f"\n✓ Report saved: {report_path}")
    
    return 0


if __name__ == "__main__":
    from datetime import datetime
    raise SystemExit(main())
