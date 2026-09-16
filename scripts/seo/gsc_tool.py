#!/usr/bin/env python3
"""
Raigulus SEO Tool - GSC Submit + Analytics
==========================================
Google Search Console API entegrasyonu ile:
- URL gönderimi (IndexNow + GSC)
- GSC analitik veri çekme
- Haftalık rapor oluşturma

Kullanım:
    python gsc_tool.py submit --url https://raigulus.github.io/path/
    python gsc_tool.py analytics --days 7
    python gsc_tool.py report --output weekly-report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "assets" / "data"
REPORTS = ROOT / "seo-reports"

# GSC Configuration
GSC_PROPERTY = "https://raigulus.github.io/"
GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"

# IndexNow Configuration
INDEXNOW_KEY_FILE = ROOT / "indexnow-key.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_HOST = "raigulus.github.io"


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


def gsc_request(endpoint, access_token, method="GET", data=None):
    """Make authenticated GSC API request."""
    url = f"{GSC_API_BASE}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"GSC API error {e.code}: {body[:200]}")
        return None


def submit_url(url):
    """Submit URL to GSC via API."""
    credentials = get_gsc_credentials()
    if not credentials:
        print(f"Demo mode: Would submit {url}")
        return True
    
    access_token = get_access_token(credentials)
    if not access_token:
        return False
    
    # GSC URL Inspection API
    endpoint = f"/sites/{urllib.parse.quote(GSC_PROPERTY, safe='')}/urlInspection:inspect"
    data = {
        "inspectionUrl": url,
        "siteUrl": GSC_PROPERTY,
    }
    
    result = gsc_request(endpoint, access_token, method="POST", data=data)
    if result:
        print(f"✓ Submitted to GSC: {url}")
        return True
    return False


def submit_indexnow(urls):
    """Submit URLs to IndexNow."""
    key_file = INDEXNOW_KEY_FILE
    if not key_file.exists():
        print("IndexNow key file not found")
        return False
    
    key = key_file.read_text(encoding="utf-8").strip()
    
    payload = json.dumps({
        "host": INDEXNOW_HOST,
        "key": key,
        "urlList": urls,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"✓ IndexNow: {resp.status} {resp.reason}")
            return True
    except Exception as e:
        print(f"IndexNow error: {e}")
        return False


def fetch_analytics(days=7):
    """Fetch GSC analytics data for the last N days."""
    credentials = get_gsc_credentials()
    if not credentials:
        print("Demo mode: Using cached data")
        return load_cached_analytics()
    
    access_token = get_access_token(credentials)
    if not access_token:
        return load_cached_analytics()
    
    end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")
    
    endpoint = f"/sites/{urllib.parse.quote(GSC_PROPERTY, safe='')}/searchAnalytics/query"
    data = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query", "page"],
        "rowLimit": 1000,
    }
    
    result = gsc_request(endpoint, access_token, method="POST", data=data)
    if result:
        # Cache the data
        cache_file = DATA / "gsc-analytics.json"
        cache_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Fetched analytics: {len(result.get('rows', []))} rows")
        return result
    
    return load_cached_analytics()


def load_cached_analytics():
    """Load cached analytics data."""
    cache_file = DATA / "gsc-analytics.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    return {"rows": []}


def generate_report(analytics_data, output_file=None):
    """Generate markdown report from analytics data."""
    rows = analytics_data.get("rows", [])
    
    # Aggregate by query
    query_stats = {}
    for row in rows:
        query = row.get("keys", [])[0] if row.get("keys") else ""
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        ctr = row.get("ctr", 0)
        position = row.get("position", 0)
        
        if query not in query_stats:
            query_stats[query] = {"clicks": 0, "impressions": 0, "positions": []}
        query_stats[query]["clicks"] += clicks
        query_stats[query]["impressions"] += impressions
        query_stats[query]["positions"].append(position)
    
    # Sort by clicks
    top_queries = sorted(query_stats.items(), key=lambda x: x[1]["clicks"], reverse=True)[:20]
    
    # Aggregate by page
    page_stats = {}
    for row in rows:
        page = row.get("keys", [])[1] if len(row.get("keys", [])) > 1 else ""
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        
        if page not in page_stats:
            page_stats[page] = {"clicks": 0, "impressions": 0}
        page_stats[page]["clicks"] += clicks
        page_stats[page]["impressions"] += impressions
    
    top_pages = sorted(page_stats.items(), key=lambda x: x[1]["clicks"], reverse=True)[:20]
    
    # Calculate totals
    total_clicks = sum(q["clicks"] for q in query_stats.values())
    total_impressions = sum(q["impressions"] for q in query_stats.values())
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    # Generate report
    report = f"""# Raigulus GSC Haftalık Rapor

**Tarih:** {datetime.now().strftime("%Y-%m-%d")}
**Property:** {GSC_PROPERTY}
**Dönem:** Son 7 gün

## Genel Durum

| Metrik | Değer |
|--------|-------|
| Toplam Tıklama | {total_clicks} |
| Toplam Gösterim | {total_impressions} |
| Ortalama CTR | %{avg_ctr:.2f} |
| Benzersiz Sorgu | {len(query_stats)} |

## En Çok Tıklanan Sorgular

| Sorgu | Tıklama | Gösterim | CTR% | Ort. Pozisyon |
|-------|---------|----------|------|---------------|
"""
    
    for query, stats in top_queries:
        avg_pos = sum(stats["positions"]) / len(stats["positions"]) if stats["positions"] else 0
        ctr = (stats["clicks"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
        report += f"| {query[:50]} | {stats['clicks']} | {stats['impressions']} | {ctr:.1f} | {avg_pos:.1f} |\n"
    
    report += """
## En Çok Tıklanan Sayfalar

| Sayfa | Tıklama | Gösterim |
|-------|---------|----------|
"""
    
    for page, stats in top_pages:
        page_display = page.replace("https://raigulus.github.io", "") if page else "/"
        report += f"| {page_display[:50]} | {stats['clicks']} | {stats['impressions']} |\n"
    
    report += """
## Öneriler

"""
    
    # Generate recommendations
    low_ctr_queries = [(q, s) for q, s in top_queries if s["impressions"] > 10 and (s["clicks"] / s["impressions"] * 100) < 2]
    if low_ctr_queries:
        report += "### Düşük CTR'li Sorgular (İyileştirme Gereken)\n\n"
        for query, stats in low_ctr_queries[:5]:
            ctr = (stats["clicks"] / stats["impressions"] * 100)
            report += f"- **{query}**: %{ctr:.1f} CTR ({stats['impressions']} gösterim)\n"
        report += "\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    # Save report
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
        print(f"✓ Report saved: {output_file}")
    else:
        REPORTS.mkdir(exist_ok=True)
        filename = f"gsc-report-{datetime.now().strftime('%Y-%m-%d')}.md"
        report_path = REPORTS / filename
        report_path.write_text(report, encoding="utf-8")
        print(f"✓ Report saved: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Raigulus SEO Tool - GSC Submit + Analytics")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit URL to GSC")
    submit_parser.add_argument("--url", help="URL to submit")
    submit_parser.add_argument("--urls-file", help="File with URLs to submit")
    submit_parser.add_argument("--indexnow", action="store_true", help="Also submit to IndexNow")
    
    # Analytics command
    analytics_parser = subparsers.add_parser("analytics", help="Fetch GSC analytics")
    analytics_parser.add_argument("--days", type=int, default=7, help="Number of days to fetch")
    analytics_parser.add_argument("--cache", action="store_true", help="Use cached data only")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("--output", help="Output file path")
    report_parser.add_argument("--input", help="Input analytics JSON file")
    
    args = parser.parse_args()
    
    if args.command == "submit":
        urls = []
        if args.url:
            urls.append(args.url)
        elif args.urls_file:
            urls = Path(args.urls_file).read_text(encoding="utf-8").strip().split("\n")
            urls = [u.strip() for u in urls if u.strip()]
        
        if not urls:
            print("No URLs to submit")
            return 1
        
        print(f"Submitting {len(urls)} URL(s)...")
        for url in urls:
            submit_url(url)
        
        if args.indexnow:
            print("\nSubmitting to IndexNow...")
            submit_indexnow(urls)
    
    elif args.command == "analytics":
        print(f"Fetching analytics for last {args.days} days...")
        data = fetch_analytics(args.days)
        if data:
            print(f"✓ Got {len(data.get('rows', []))} rows")
    
    elif args.command == "report":
        if args.input:
            data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        else:
            data = load_cached_analytics()
        
        generate_report(data, args.output)
    
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
