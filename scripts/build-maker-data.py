#!/usr/bin/env python3
"""div2hub/game-data CSV'lerini indirip build-maker.json'a cevirir.

Source: https://github.com/div2hub/game-data (community data hub)
Output: assets/data/build-maker.json (in the site repo)

Re-run after a patch: python3 scripts/build-maker-data.py
"""
import csv
import io
import json
import sys
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

    FAIL-SAFE: a missing file, malformed JSON, or invalid schema raises
    an error. We must never silently continue with zero overrides.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PvP overrides file missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in PvP overrides file {path}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"Invalid schema: top level must be a list (got {type(data).__name__})")
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid schema: entry #{i} is not an object")
        collection = entry.get("collection")
        name = entry.get("name")
        if collection not in ("brands", "gearSets"):
            raise ValueError(f"Invalid schema: entry #{i} has invalid collection {collection!r}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid schema: entry #{i} has invalid name {name!r}")
        pvp_keys = [k for k in entry if k.startswith("pvp_")]
        if not pvp_keys:
            raise ValueError(f"Invalid schema: entry #{i} ({name}) has no pvp_* fields")
        for key in pvp_keys:
            value = entry[key]
            if not isinstance(value, str) or not value.strip() or value == "N/A":
                raise ValueError(f"Invalid schema: entry #{i} ({name}) has invalid {key}={value!r}")
        unknown = {k for k in entry} - {"collection", "name"} - set(pvp_keys)
        if unknown:
            raise ValueError(f"Invalid schema: entry #{i} ({name}) has unexpected keys {sorted(unknown)}")
    return data


def pvp_count(data):
    """Count pvp_*pc_bonus fields in a data dict."""
    return sum(1 for n in data.get("brands", []) + data.get("gearSets", [])
               for pc in ("1", "2", "3") if n.get("pvp_%spc_bonus" % pc))


def apply_pvp_overrides(data, overrides):
    """Merge PvP overrides into freshly fetched data, in place.

    - Matches nodes by (collection, name).
    - Only ``pvp_*`` keys are copied, everything else is untouched.
    - Re-applying the same overrides is idempotent (no duplication).
    - Unknown nodes emit an explicit warning to stderr (never silent).
    - An override for an unknown node still fails validation upstream:
      callers should compare expected vs applied counts; main() does.
    """
    if overrides is None:
        raise ValueError("Invalid schema: overrides must be a list, got None")
    if not isinstance(overrides, list):
        raise ValueError("Invalid schema: overrides must be a list")
    by_name = {}
    for entry in overrides:
        if not isinstance(entry, dict):
            raise ValueError("Invalid schema: override entry is not an object")
        name = entry.get("name")
        collection = entry.get("collection")
        if collection not in ("brands", "gearSets"):
            raise ValueError(f"Invalid schema: invalid collection {collection!r}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid schema: override has invalid name")
        fields = {k: v for k, v in entry.items() if k.startswith("pvp_")}
        if not fields:
            raise ValueError(f"Invalid schema: override ({collection}:{name}) has no pvp_* fields")
        by_name[(collection, name)] = fields
    found = set()
    for collection in ("brands", "gearSets"):
        for node in data.get(collection, []):
            key = (collection, node.get("name"))
            fields = by_name.get(key)
            if fields is not None:
                node.update(fields)
                found.add(key)
    for key in sorted(set(by_name) - found):
        print(f"WARNING: PvP override references unknown node {key[0]}:{key[1]}", file=sys.stderr)
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
    # FAIL-SAFE: malformed/missing overrides or shortfalls abort the build;
    # never write incomplete production data.
    try:
        _overrides = load_pvp_overrides()
    except Exception as exc:
        print(f"FATAL: PvP overrides load failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    _expected = sum(1 for e in _overrides for k in e if k.startswith("pvp_"))
    apply_pvp_overrides(out, _overrides)
    _applied = pvp_count(out)
    if _applied < _expected or _applied < 53:
        print(f"FATAL: PvP override shortfall: expected {_expected} (minimum 53), applied {_applied}. Abort.",
              file=sys.stderr)
        raise SystemExit(1)
    print(f"PvP overrides preserved: {_applied}/{_expected}")
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