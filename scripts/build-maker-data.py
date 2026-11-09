#!/usr/bin/env python3
"""div2hub/game-data CSV'lerini indirip build-maker.json'a cevirir.

Source: https://github.com/div2hub/game-data (community data hub)
Output: assets/data/build-maker.json (in the site repo)

Re-run after a patch: python3 scripts/build-maker-data.py
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "data" / "build-maker.json"
PREV = ROOT / "assets" / "data" / "build-maker-prev.json"
OVERRIDES = ROOT / "assets" / "data" / "build-maker-pvp-overrides.json"
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


def load_pvp_overrides(path=OVERRIDES):
    """Raigulus-specific PvP overrides, kept separate from upstream data.

    The upstream div2hub CSVs do not carry ``pvp_*pc_bonus`` fields.
    These verified values were hand-added (Oct 28) and must survive every
    automated refresh. They live in their own file so the merge is
    deterministic and reviewable.
    """
    if not Path(path).exists():
        return []
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def apply_pvp_overrides(data, overrides):
    """Merge PvP overrides into freshly fetched data, in place.

    - Matches nodes by (collection, name); unknown names are skipped.
    - Only ``pvp_*`` keys are copied, everything else is untouched.
    - Re-applying the same overrides is idempotent (no duplication).
    """
    if not overrides:
        return data
    by_name = {}
    for entry in overrides:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        collection = entry.get("collection")
        if not name or collection not in ("brands", "gearSets"):
            continue
        fields = {k: v for k, v in entry.items()
                  if k.startswith("pvp_") and v not in (None, "", "N/A")}
        if fields:
            by_name[(collection, name)] = fields
    for collection in ("brands", "gearSets"):
        for node in data.get(collection, []):
            fields = by_name.get((collection, node.get("name")))
            if fields:
                node.update(fields)
    return data


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
    # Preserve Raigulus-specific PvP overrides across upstream refreshes.
    # The upstream CSVs carry no pvp_* fields, so without this overlay the
    # verified values are silently wiped on every automated refresh.
    apply_pvp_overrides(out, load_pvp_overrides())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Check whether the data changed (excluding meta.generated) -> idempotent
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        old.pop("meta", None)
        new = dict(out)
        new.pop("meta", None)
        if old == new:
            print("Data unchanged - file not updated (idempotent).")
            return
    # Back up the previous version (for the changelog diff)
    if OUT.exists():
        PREV.write_bytes(OUT.read_bytes())
        print(f"Previous version backed up: {PREV.name}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nYazildi: {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()