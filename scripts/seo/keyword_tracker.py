#!/usr/bin/env python3
"""
Raigulus SEO Tool - Keyword Tracker
==========================================
Anahtar kelime sıralama takibi:
- GSC'den sıralama verisi çekme
- Sıralama değişimlerini izleme
- Haftalık karşılaştırma raporu
- Kelime grupları oluşturma

Kullanım:
    python keyword_tracker.py add "the division 2 targeted loot"
    python keyword_tracker.py track --days 7
    python keyword_tracker.py report
    python keyword_tracker.py compare --weeks 4
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "assets" / "data"
REPORTS = ROOT / "seo-reports"
KEYWORDS_FILE = DATA / "tracked-keywords.json"
RANKINGS_HISTORY = DATA / "rankings-history.json"

# GSC Configuration
GSC_PROPERTY = "https://raigulus.github.io/"
GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"


def load_tracked_keywords():
    """Load tracked keywords from file."""
    if KEYWORDS_FILE.exists():
        return json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))
    return {
        "keywords": [],
        "groups": {},
        "created": datetime.now().isoformat(),
    }


def save_tracked_keywords(data):
    """Save tracked keywords to file."""
    KEYWORDS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Keywords saved: {KEYWORDS_FILE}")


def load_rankings_history():
    """Load rankings history."""
    if RANKINGS_HISTORY.exists():
        return json.loads(RANKINGS_HISTORY.read_text(encoding="utf-8"))
    return {"snapshots": []}


def save_rankings_history(data):
    """Save rankings history."""
    RANKINGS_HISTORY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ History saved: {RANKINGS_HISTORY}")


def get_gsc_credentials():
    """GSC OAuth2 credentials from environment."""
    client_id = os.environ.get("GSC_CLIENT_ID", "")
    client_secret = os.environ.get("GSC_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GSC_REFRESH_TOKEN", "")
    
    if not all([client_id, client_secret, refresh_token]):
        print("Warning: GSC credentials not set. Using demo mode.")
        return None
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }


def get_access_token(credentials):
    """Get OAuth2 access token from refresh token."""
    if not credentials:
        return None
    
    from urllib.parse import urlencode
    data = urlencode({
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
        "refresh_token": credentials["refresh_token"],
        "grant_type": "refresh_token",
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("access_token")
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None


def fetch_keyword_rankings(keywords, days=7):
    """Fetch rankings for tracked keywords from GSC."""
    credentials = get_gsc_credentials()
    if not credentials:
        print("Demo mode: Using simulated data")
        return generate_demo_data(keywords)
    
    access_token = get_access_token(credentials)
    if not access_token:
        return generate_demo_data(keywords)
    
    end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")
    
    results = []
    
    for keyword in keywords:
        endpoint = f"/sites/{quote(GSC_PROPERTY, safe='')}/searchAnalytics/query"
        data = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "query",
                    "expression": keyword,
                }],
            }],
            "rowLimit": 1,
        }
        
        req_data = json.dumps(data).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"{GSC_API_BASE}{endpoint}"
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                rows = result.get("rows", [])
                
                if rows:
                    row = rows[0]
                    results.append({
                        "keyword": keyword,
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": row.get("ctr", 0),
                        "position": row.get("position", 0),
                    })
                else:
                    results.append({
                        "keyword": keyword,
                        "clicks": 0,
                        "impressions": 0,
                        "ctr": 0,
                        "position": 0,
                    })
        except Exception as e:
            print(f"Error fetching {keyword}: {e}")
            results.append({
                "keyword": keyword,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0,
                "position": 0,
            })
    
    return results


def generate_demo_data(keywords):
    """Generate demo data for testing."""
    import random
    results = []
    
    for keyword in keywords:
        results.append({
            "keyword": keyword,
            "clicks": random.randint(0, 10),
            "impressions": random.randint(10, 200),
            "ctr": random.uniform(0, 0.1),
            "position": random.uniform(1, 50),
        })
    
    return results


def add_keyword(keyword, group=None):
    """Add a keyword to track."""
    data = load_tracked_keywords()
    
    # Check if already exists
    for kw in data["keywords"]:
        if kw["keyword"] == keyword:
            print(f"Keyword already tracked: {keyword}")
            return
    
    # Add keyword
    entry = {
        "keyword": keyword,
        "added": datetime.now().isoformat(),
        "group": group,
        "tags": [],
    }
    
    data["keywords"].append(entry)
    
    # Add to group if specified
    if group:
        if group not in data["groups"]:
            data["groups"][group] = []
        data["groups"][group].append(keyword)
    
    save_tracked_keywords(data)
    print(f"✓ Added: {keyword}")


def remove_keyword(keyword):
    """Remove a keyword from tracking."""
    data = load_tracked_keywords()
    
    data["keywords"] = [kw for kw in data["keywords"] if kw["keyword"] != keyword]
    
    # Remove from groups
    for group in data["groups"]:
        if keyword in data["groups"][group]:
            data["groups"][group].remove(keyword)
    
    save_tracked_keywords(data)
    print(f"✓ Removed: {keyword}")


def list_keywords():
    """List all tracked keywords."""
    data = load_tracked_keywords()
    
    if not data["keywords"]:
        print("No keywords tracked yet.")
        return
    
    print(f"\n📊 Tracked Keywords ({len(data['keywords'])} total)")
    print("-" * 60)
    
    for kw in data["keywords"]:
        group = kw.get("group", "-")
        print(f"  • {kw['keyword'][:50]} [{group}]")
    
    if data["groups"]:
        print(f"\n📁 Groups ({len(data['groups'])})")
        print("-" * 60)
        for group, keywords in data["groups"].items():
            print(f"  • {group}: {len(keywords)} keywords")


def track_rankings(days=7):
    """Track rankings for all keywords."""
    data = load_tracked_keywords()
    keywords = [kw["keyword"] for kw in data["keywords"]]
    
    if not keywords:
        print("No keywords to track. Add some first.")
        return
    
    print(f"Tracking {len(keywords)} keywords...")
    results = fetch_keyword_rankings(keywords, days)
    
    # Save snapshot
    history = load_rankings_history()
    snapshot = {
        "date": datetime.now().isoformat(),
        "results": results,
    }
    history["snapshots"].append(snapshot)
    
    # Keep only last 90 days
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    history["snapshots"] = [s for s in history["snapshots"] if s["date"] > cutoff]
    
    save_rankings_history(history)
    print(f"✓ Snapshot saved ({len(results)} keywords)")
    
    return results


def generate_report():
    """Generate rankings report."""
    history = load_rankings_history()
    
    if not history["snapshots"]:
        print("No data yet. Run 'track' first.")
        return
    
    latest = history["snapshots"][-1]
    previous = history["snapshots"][-2] if len(history["snapshots"]) > 1 else None
    
    report = f"""# Raigulus Keyword Sıralama Raporu

**Tarih:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Toplam Snapshot:** {len(history["snapshots"])}
**Son Güncelleme:** {latest['date'][:10]}

## Güncel Sıralamalar

| Anahtar Kelime | Pozisyon | Tıklama | Gösterim | CTR% | Değişim |
|----------------|----------|---------|----------|------|---------|
"""
    
    for result in latest["results"]:
        # Calculate change
        change = ""
        if previous:
            for prev in previous["results"]:
                if prev["keyword"] == result["keyword"]:
                    diff = prev["position"] - result["position"]
                    if diff > 0:
                        change = f"↑ {diff:.1f}"
                    elif diff < 0:
                        change = f"↓ {abs(diff):.1f}"
                    else:
                        change = "→ 0"
                    break
        
        ctr = result["ctr"] * 100
        report += f"| {result['keyword'][:40]} | {result['position']:.1f} | {result['clicks']} | {result['impressions']} | {ctr:.1f}% | {change} |\n"
    
    report += """
## Sıralama Dağılımı

"""
    
    # Position distribution
    positions = [r["position"] for r in latest["results"] if r["position"] > 0]
    if positions:
        top_3 = sum(1 for p in positions if p <= 3)
        top_10 = sum(1 for p in positions if p <= 10)
        top_20 = sum(1 for p in positions if p <= 20)
        top_50 = sum(1 for p in positions if p <= 50)
        
        report += f"""| Sıralama | Sayı | Oran |
|----------|------|------|
| Top 3 | {top_3} | %{top_3/len(positions)*100:.1f} |
| Top 10 | {top_10} | %{top_10/len(positions)*100:.1f} |
| Top 20 | {top_20} | %{top_20/len(positions)*100:.1f} |
| Top 50 | {top_50} | %{top_50/len(positions)*100:.1f} |
"""
    
    report += """
## Öneriler

"""
    
    # Find keywords needing improvement
    low_position = [r for r in latest["results"] if r["position"] > 10 and r["impressions"] > 10]
    if low_position:
        report += "### İyileştirme Gereken Kelimeler (Pozisyon > 10, Gösterim > 10)\n\n"
        for r in sorted(low_position, key=lambda x: x["impressions"], reverse=True)[:5]:
            report += f"- **{r['keyword']}**: Pozisyon {r['position']:.1f}, {r['impressions']} gösterim\n"
        report += "\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    # Save report
    REPORTS.mkdir(exist_ok=True)
    filename = f"keyword-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path = REPORTS / filename
    report_path.write_text(report, encoding="utf-8")
    print(f"✓ Report saved: {report_path}")
    
    return report


def compare_weeks(weeks=4):
    """Compare rankings over multiple weeks."""
    history = load_rankings_history()
    
    if len(history["snapshots"]) < 2:
        print("Need at least 2 snapshots for comparison.")
        return
    
    report = f"""# Raigulus Keyword Karşılaştırma Raporu

**Tarih:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Karşılaştırma:** Son {weeks} hafta

## Haftalık Değişim Tablosu

"""
    
    # Get latest N snapshots
    snapshots = history["snapshots"][-weeks:]
    
    # Build comparison table
    keywords = set()
    for snap in snapshots:
        for r in snap["results"]:
            keywords.add(r["keyword"])
    
    report += "| Anahtar Kelime |"
    for i, snap in enumerate(snapshots):
        date = snap["date"][:10]
        report += f" {date} |"
    report += " Değişim |\\n"
    
    report += "|----------------|"
    for _ in snapshots:
        report += "--------|"
    report += "---------|\\n"
    
    for keyword in sorted(keywords):
        report += f"| {keyword[:30]} |"
        positions = []
        for snap in snapshots:
            found = False
            for r in snap["results"]:
                if r["keyword"] == keyword:
                    report += f" {r['position']:.1f} |"
                    positions.append(r["position"])
                    found = True
                    break
            if not found:
                report += " - |"
        
        # Calculate change
        if len(positions) >= 2:
            change = positions[0] - positions[-1]
            if change > 0:
                report += f" ↑{change:.1f} |"
            elif change < 0:
                report += f" ↓{abs(change):.1f} |"
            else:
                report += " →0 |"
        else:
            report += " - |"
        report += "\\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    # Save report
    REPORTS.mkdir(exist_ok=True)
    filename = f"keyword-compare-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path = REPORTS / filename
    report_path.write_text(report, encoding="utf-8")
    print(f"✓ Report saved: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Raigulus SEO Tool - Keyword Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add keyword to track")
    add_parser.add_argument("keyword", help="Keyword to track")
    add_parser.add_argument("--group", help="Group name")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove keyword")
    remove_parser.add_argument("keyword", help="Keyword to remove")
    
    # List command
    subparsers.add_parser("list", help="List tracked keywords")
    
    # Track command
    track_parser = subparsers.add_parser("track", help="Track rankings")
    track_parser.add_argument("--days", type=int, default=7, help="Days to fetch")
    
    # Report command
    subparsers.add_parser("report", help="Generate report")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare weeks")
    compare_parser.add_argument("--weeks", type=int, default=4, help="Weeks to compare")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_keyword(args.keyword, args.group)
    elif args.command == "remove":
        remove_keyword(args.keyword)
    elif args.command == "list":
        list_keywords()
    elif args.command == "track":
        track_rankings(args.days)
    elif args.command == "report":
        generate_report()
    elif args.command == "compare":
        compare_weeks(args.weeks)
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
