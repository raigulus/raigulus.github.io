#!/usr/bin/env python3
"""
Raigulus SEO Tool - Backlink Monitor
==========================================
Backlink takibi ve analizi:
- Backlink kazanma/kayıp takibi
- Anchor text analizi
- Doman otoritesi karşılaştırması
- Backlink raporu oluşturma

Kullanım:
    python backlink_monitor.py add "example.com"
    python backlink_monitor.py scan
    python backlink_monitor.py report
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "assets" / "data"
REPORTS = ROOT / "seo-reports"
BACKLINKS_FILE = DATA / "backlinks.json"
BACKLINK_HISTORY = DATA / "backlink-history.json"

# Known backlink sources for Division 2 community
KNOWN_SOURCES = [
    "reddit.com",
    "twitter.com",
    "youtube.com",
    "discord.com",
    "twitch.tv",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "division.fandom.com",
    "thedivision.fandom.com",
    "ubisoft.com",
    "github.com",
]


def load_backlinks():
    """Load backlinks from file."""
    if BACKLINKS_FILE.exists():
        return json.loads(BACKLINKS_FILE.read_text(encoding="utf-8"))
    return {
        "backlinks": [],
        "created": datetime.now().isoformat(),
    }


def save_backlinks(data):
    """Save backlinks to file."""
    BACKLINKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Backlinks saved: {BACKLINKS_FILE}")


def load_backlink_history():
    """Load backlink history."""
    if BACKLINK_HISTORY.exists():
        return json.loads(BACKLINK_HISTORY.read_text(encoding="utf-8"))
    return {"snapshots": []}


def save_backlink_history(data):
    """Save backlink history."""
    BACKLINK_HISTORY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_backlink(source_url, target_url, anchor_text=None, category=None):
    """Add a backlink to track."""
    data = load_backlinks()
    
    # Check if already exists
    for bl in data["backlinks"]:
        if bl["source"] == source_url and bl["target"] == target_url:
            print(f"Backlink already tracked: {source_url} → {target_url}")
            return
    
    entry = {
        "source": source_url,
        "target": target_url,
        "anchor": anchor_text or "",
        "category": category or "other",
        "added": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "status": "active",
    }
    
    data["backlinks"].append(entry)
    save_backlinks(data)
    print(f"✓ Added backlink: {source_url} → {target_url}")


def remove_backlink(source_url, target_url):
    """Remove a backlink."""
    data = load_backlinks()
    data["backlinks"] = [
        bl for bl in data["backlinks"]
        if not (bl["source"] == source_url and bl["target"] == target_url)
    ]
    save_backlinks(data)
    print(f"✓ Removed backlink: {source_url} → {target_url}")


def list_backlinks():
    """List all tracked backlinks."""
    data = load_backlinks()
    
    if not data["backlinks"]:
        print("No backlinks tracked yet.")
        return
    
    print(f"\n📊 Tracked Backlinks ({len(data['backlinks'])} total)")
    print("-" * 80)
    
    for bl in data["backlinks"]:
        status = "✓" if bl.get("status") == "active" else "✗"
        anchor = bl.get("anchor", "-")[:20]
        print(f"  {status} {bl['source'][:35]:<35} → {bl['target'][:30]:<30} [{anchor}]")
    
    # Category breakdown
    categories = {}
    for bl in data["backlinks"]:
        cat = bl.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n📁 Kategoriler ({len(categories)})")
    print("-" * 40)
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cat}: {count}")


def verify_backlinks():
    """Verify backlinks are still active."""
    data = load_backlinks()
    
    if not data["backlinks"]:
        print("No backlinks to verify.")
        return
    
    print(f"Verifying {len(data['backlinks'])} backlinks...")
    changes = 0
    
    for bl in data["backlinks"]:
        source = bl["source"]
        
        try:
            req = urllib.request.Request(source, method="HEAD", headers={
                "User-Agent": "RaigulusBacklinkBot/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                # Check if our link is still there
                req2 = urllib.request.Request(source, headers={
                    "User-Agent": "RaigulusBacklinkBot/1.0",
                })
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    content = resp2.read().decode("utf-8", errors="replace")
                    
                    # Check for our domain
                    if "raigulus.github.io" in content:
                        bl["status"] = "active"
                        bl["last_seen"] = datetime.now().isoformat()
                        changes += 1
                    else:
                        bl["status"] = "broken"
                        changes += 1
        except Exception as e:
            bl["status"] = "error"
            changes += 1
        
        print(f"  {'✓' if bl['status'] == 'active' else '✗'} {source[:50]}")
    
    if changes > 0:
        save_backlinks(data)
        print(f"\n✓ Verified {changes} backlinks")
    
    return changes


def generate_report():
    """Generate backlink report."""
    data = load_backlinks()
    history = load_backlink_history()
    
    report = f"""# Raigulus Backlink Raporu

**Tarih:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Toplam Backlink:** {len(data['backlinks'])}

## Genel Durum

"""
    
    # Status breakdown
    status_count = {}
    for bl in data["backlinks"]:
        status = bl.get("status", "unknown")
        status_count[status] = status_count.get(status, 0) + 1
    
    report += "| Durum | Sayı |\n|-------|------|\n"
    for status, count in status_count.items():
        report += f"| {status} | {count} |\n"
    
    report += "\n## Backlink Listesi\n\n"
    report += "| Kaynak | Hedef | Anchor | Durum |\n|--------|-------|--------|------|\n"
    
    for bl in data["backlinks"]:
        status = "✓" if bl.get("status") == "active" else "✗"
        source = bl["source"].replace("https://", "").replace("http://", "")[:35]
        target = bl["target"].replace("https://raigulus.github.io", "")[:30]
        anchor = bl.get("anchor", "-")[:25]
        report += f"| {source} | {target} | {anchor} | {status} |\n"
    
    report += "\n## Anchor Text Analizi\n\n"
    
    # Anchor text analysis
    anchors = {}
    for bl in data["backlinks"]:
        anchor = bl.get("anchor", "")
        if anchor:
            anchors[anchor] = anchors.get(anchor, 0) + 1
    
    if anchors:
        report += "| Anchor | Sayı |\n|--------|------|\n"
        for anchor, count in sorted(anchors.items(), key=lambda x: x[1], reverse=True)[:10]:
            report += f"| {anchor[:40]} | {count} |\n"
    else:
        report += "Anchor text bilgisi yok.\n"
    
    report += "\n## Öneriler\n\n"
    
    # Generate recommendations
    active_count = status_count.get("active", 0)
    broken_count = status_count.get("broken", 0) + status_count.get("error", 0)
    
    if broken_count > 0:
        report += f"- **{broken_count} kırık backlink** bulundu. Bu linkleri düzeltmeyi veya kaldırmayı düşünün.\n"
    
    if active_count < 5:
        report += "- **Backlink sayınız az.** Daha fazla backlink kazanmak için içerik pazarlama stratejileri uygulayın.\n"
    
    report += """
---
*Rapor otomatik oluşturuldu.*
"""
    
    # Save report
    REPORTS.mkdir(exist_ok=True)
    filename = f"backlink-report-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path = REPORTS / filename
    report_path.write_text(report, encoding="utf-8")
    print(f"✓ Report saved: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Raigulus SEO Tool - Backlink Monitor")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add backlink")
    add_parser.add_argument("source", help="Source URL")
    add_parser.add_argument("target", help="Target URL")
    add_parser.add_argument("--anchor", help="Anchor text")
    add_parser.add_argument("--category", help="Category")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove backlink")
    remove_parser.add_argument("source", help="Source URL")
    remove_parser.add_argument("target", help="Target URL")
    
    # List command
    subparsers.add_parser("list", help="List backlinks")
    
    # Verify command
    subparsers.add_parser("verify", help="Verify backlinks are active")
    
    # Report command
    subparsers.add_parser("report", help="Generate report")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_backlink(args.source, args.target, args.anchor, args.category)
    elif args.command == "remove":
        remove_backlink(args.source, args.target)
    elif args.command == "list":
        list_backlinks()
    elif args.command == "verify":
        verify_backlinks()
    elif args.command == "report":
        generate_report()
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
