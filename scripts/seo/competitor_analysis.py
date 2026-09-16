#!/usr/bin/env python3
"""
Raigulus SEO Tool - Competitor Analysis
==========================================
Rakip sitelerin SEO performansını analiz etme:
- Sıralama karşılaştırması
- İçerik analizi
- Backlink karşılaştırması
- Teknik SEO karşılaştırması

Kullanım:
    python competitor_analysis.py add "division2hub.com"
    python competitor_analysis.py compare
    python competitor_analysis.py report
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
from urllib.parse import urlparse
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "assets" / "data"
REPORTS = ROOT / "seo-reports"
COMPETITORS_FILE = DATA / "competitors.json"
ANALYSIS_HISTORY = DATA / "competitor-history.json"


def load_competitors():
    """Load competitors from file."""
    if COMPETITORS_FILE.exists():
        return json.loads(COMPETITORS_FILE.read_text(encoding="utf-8"))
    return {
        "competitors": [],
        "created": datetime.now().isoformat(),
    }


def save_competitors(data):
    """Save competitors to file."""
    COMPETITORS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Competitors saved: {COMPETITORS_FILE}")


def add_competitor(domain, name=None, category=None):
    """Add a competitor to track."""
    data = load_competitors()
    
    # Check if already exists
    for comp in data["competitors"]:
        if comp["domain"] == domain:
            print(f"Competitor already tracked: {domain}")
            return
    
    entry = {
        "domain": domain,
        "name": name or domain,
        "category": category or "general",
        "added": datetime.now().isoformat(),
        "tags": [],
    }
    
    data["competitors"].append(entry)
    save_competitors(data)
    print(f"✓ Added competitor: {domain}")


def remove_competitor(domain):
    """Remove a competitor."""
    data = load_competitors()
    data["competitors"] = [c for c in data["competitors"] if c["domain"] != domain]
    save_competitors(data)
    print(f"✓ Removed: {domain}")


def list_competitors():
    """List all competitors."""
    data = load_competitors()
    
    if not data["competitors"]:
        print("No competitors tracked yet.")
        return
    
    print(f"\n📊 Tracked Competitors ({len(data['competitors'])} total)")
    print("-" * 60)
    
    for comp in data["competitors"]:
        print(f"  • {comp['name']:<25} {comp['domain']:<30} [{comp.get('category', '-')}]")  


def fetch_competitor_data(domain):
    """Fetch basic SEO data from competitor site."""
    url = f"https://{domain}"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RaigulusCompetitorBot/1.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            
            result = {
                "domain": domain,
                "fetched": datetime.now().isoformat(),
                "status": "success",
                "title": "",
                "description": "",
                "has_schema": False,
                "has_canonical": False,
                "link_count": 0,
                "word_count": 0,
            }
            
            # Extract title
            title_match = re.search(r"<title>([^<]+)</title>", content, re.IGNORECASE)
            if title_match:
                result["title"] = title_match.group(1).strip()[:100]
            
            # Extract meta description
            desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', content, re.IGNORECASE)
            if desc_match:
                result["description"] = desc_match.group(1).strip()[:200]
            
            # Check schema
            if 'application/ld+json' in content.lower():
                result["has_schema"] = True
            
            # Check canonical
            if 'rel="canonical"' in content.lower():
                result["has_canonical"] = True
            
            # Count links
            links = re.findall(r'href=["\']([^"\']+)["\']', content)
            result["link_count"] = len(links)
            
            # Word count (rough)
            text = re.sub(r'<[^>]+>', ' ', content)
            result["word_count"] = len(text.split())
            
            return result
            
    except Exception as e:
        return {
            "domain": domain,
            "fetched": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


def run_analysis():
    """Run analysis on all competitors."""
    data = load_competitors()
    
    if not data["competitors"]:
        print("No competitors to analyze.")
        return
    
    print(f"Analyzing {len(data['competitors'])} competitors...")
    results = []
    
    # Also fetch our own site
    print("Fetching raigulus.github.io...")
    our_data = fetch_competitor_data("raigulus.github.io")
    our_data["is_ours"] = True
    results.append(our_data)
    
    for comp in data["competitors"]:
        print(f"Fetching {comp['domain']}...")
        result = fetch_competitor_data(comp["domain"])
        result["category"] = comp.get("category")
        results.append(result)
    
    # Save history
    history = load_analysis_history()
    snapshot = {
        "date": datetime.now().isoformat(),
        "results": results,
    }
    history["snapshots"].append(snapshot)
    
    # Keep only last 30 snapshots
    if len(history["snapshots"]) > 30:
        history["snapshots"] = history["snapshots"][-30:]
    
    save_analysis_history(history)
    print(f"✓ Analysis saved ({len(results)} sites)")
    
    return results


def load_analysis_history():
    """Load analysis history."""
    if ANALYSIS_HISTORY.exists():
        return json.loads(ANALYSIS_HISTORY.read_text(encoding="utf-8"))
    return {"snapshots": []}


def save_analysis_history(data):
    """Save analysis history."""
    ANALYSIS_HISTORY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_report():
    """Generate competitor comparison report."""
    history = load_analysis_history()
    
    if not history["snapshots"]:
        print("No analysis data. Run 'compare' first.")
        return
    
    latest = history["snapshots"][-1]
    results = latest["results"]
    
    report = f"""# Raigulus Rakip Analiz Raporu

**Tarih:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Analyze Edilen Site:** {len(results)}

## Genel Karşılaştırma

| Site | Başlık | Schema | Canonical | Link | Kelime |
|------|--------|--------|-----------|------|--------|
"""
    
    our_site = None
    competitors = []
    
    for r in results:
        if r.get("is_ours"):
            our_site = r
        else:
            competitors.append(r)
        
        status = "✓" if r.get("status") == "success" else "✗"
        title = r.get("title", "-")[:30]
        schema = "✓" if r.get("has_schema") else "✗"
        canonical = "✓" if r.get("has_canonical") else "✗"
        links = r.get("link_count", 0)
        words = r.get("word_count", 0)
        
        prefix = "**" if r.get("is_ours") else ""
        suffix = "**" if r.get("is_ours") else ""
        report += f"| {prefix}{r['domain']}{suffix} | {title} | {schema} | {canonical} | {links} | {words} |\n"
    
    report += """
## Detaylı Analiz

"""
    
    if our_site and our_site.get("status") == "success":
        report += "### Bizim Sitemiz (raigulus.github.io)\n\n"
        report += f"- **Başlık:** {our_site.get('title', '-')}\n"
        report += f"- **Açıklama:** {our_site.get('description', '-')[:150]}\n"
        report += f"- **Schema:** {'✓ Var' if our_site.get('has_schema') else '✗ Yok'}\n"
        report += f"- **Canonical:** {'✓ Var' if our_site.get('has_canonical') else '✗ Yok'}\n"
        report += f"- **Link Sayısı:** {our_site.get('link_count', 0)}\n"
        report += f"- **Kelime Sayısı:** {our_site.get('word_count', 0)}\n\n"
    
    report += "### Rakip Siteler\n\n"
    
    for comp in sorted(competitors, key=lambda x: x.get("word_count", 0), reverse=True):
        if comp.get("status") != "success":
            report += f"#### {comp['domain']}\n\n"
            report += f"- **Durum:** Hata — {comp.get('error', 'Bilinmiyor')}\n\n"
            continue
        
        report += f"#### {comp['domain']}\n\n"
        report += f"- **Başlık:** {comp.get('title', '-')}\n"
        report += f"- **Schema:** {'✓ Var' if comp.get('has_schema') else '✗ Yok'}\n"
        report += f"- **Canonical:** {'✓ Var' if comp.get('has_canonical') else '✗ Yok'}\n"
        report += f"- **Link Sayısı:** {comp.get('link_count', 0)}\n"
        report += f"- **Kelime Sayısı:** {comp.get('word_count', 0)}\n\n"
    
    report += """
## Öneriler

"""
    
    # Generate recommendations
    if our_site:
        our_words = our_site.get("word_count", 0)
        avg_comp_words = sum(c.get("word_count", 0) for c in competitors) / len(competitors) if competitors else 0
        
        if our_words < avg_comp_words * 0.5:
            report += "- **İçerik Miktarı:** Rakiplerinizden önemli ölçüde az içeriğiniz var. Daha kapsamlı rehberler yazmayı düşünün.\n"
        
        if not our_site.get("has_schema"):
            report += "- **Schema Markup:** Structured data ekleyerek zengin sonuçlar kazanabilirsiniz.\n"
        
        if not our_site.get("has_canonical"):
            report += "- **Canonical Tag:** Duplicate content sorunlarını önlemek için canonical tag ekleyin.\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    # Save report
    REPORTS.mkdir(exist_ok=True)
    filename = f"competitor-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path = REPORTS / filename
    report_path.write_text(report, encoding="utf-8")
    print(f"✓ Report saved: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Raigulus SEO Tool - Competitor Analysis")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add competitor")
    add_parser.add_argument("domain", help="Competitor domain")
    add_parser.add_argument("--name", help="Competitor name")
    add_parser.add_argument("--category", help="Category")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove competitor")
    remove_parser.add_argument("domain", help="Domain to remove")
    
    # List command
    subparsers.add_parser("list", help="List competitors")
    
    # Compare command
    subparsers.add_parser("compare", help="Run analysis on all competitors")
    
    # Report command
    subparsers.add_parser("report", help="Generate comparison report")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_competitor(args.domain, args.name, args.category)
    elif args.command == "remove":
        remove_competitor(args.domain)
    elif args.command == "list":
        list_competitors()
    elif args.command == "compare":
        run_analysis()
    elif args.command == "report":
        generate_report()
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
