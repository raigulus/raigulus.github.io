#!/usr/bin/env python3
"""div2hub/game-data CSV'lerini indirip build-maker.json'a cevirir.

Kaynak: https://github.com/div2hub/game-data (topluluk veri merkezi)
Cikti: assets/data/build-maker.json (site reposunda)

Patch sonrasi yeniden calistir: python3 scripts/build-maker-data.py
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "data" / "build-maker.json"
BASE = "https://raw.githubusercontent.com/div2hub/game-data/main"

FILES = [
    "attributes.csv", "stats.csv",
    "gear/brand_sets.csv", "gear/gear_sets.csv", "gear/gear_talents.csv",
    "gear/gear_mods.csv", "gear/masks.csv", "gear/chests.csv", "gear/backpacks.csv",
    "gear/gloves.csv", "gear/holsters.csv", "gear/knees.csv",
    "weapons/assault_rifles.csv", "weapons/lmgs.csv", "weapons/mmrs.csv",
    "weapons/pistols.csv", "weapons/rifles.csv", "weapons/shotguns.csv",
    "weapons/smgs.csv", "weapons/weapon_talents.csv", "weapons/weapon_mods.csv",
    "skills/skills.csv", "specializations/specialization_talents.csv",
]


def fetch(name: str) -> list[dict]:
    url = f"{BASE}/{name}"
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main():
    data = {}
    for f in FILES:
        key = f.split("/")[-1].replace(".csv", "")
        data[key] = fetch(f)
        print(f"OK {key}: {len(data[key])} satir")

    out = {
        "meta": {
            "source": "https://github.com/div2hub/game-data",
            "generated": datetime.now(timezone.utc).isoformat(),
            "counts": {k: len(v) for k, v in data.items()},
        },
        "stats": {r["id"]: r["name"] for r in data["stats"]},
        "attributes": data["attributes"],
        "brands": data["brand_sets"],
        "gearSets": data["gear_sets"],
        "gearTalents": data["gear_talents"],
        "weaponTalents": data["weapon_talents"],
        "gearMods": data["gear_mods"],
        "weaponMods": data["weapon_mods"],
        "skills": data["skills"],
        "gear": {
            "mask": data["masks"],
            "chest": data["chests"],
            "backpack": data["backpacks"],
            "gloves": data["gloves"],
            "holster": data["holsters"],
            "knees": data["knees"],
        },
        "weapons": {
            "assault-rifle": data["assault_rifles"],
            "lmg": data["lmgs"],
            "mmr": data["mmrs"],
            "pistol": data["pistols"],
            "rifle": data["rifles"],
            "shotgun": data["shotguns"],
            "smg": data["smgs"],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nYazildi: {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()