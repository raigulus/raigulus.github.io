#!/usr/bin/env python3
"""build-maker.json eski/yeni karsilastirmasi -> patch changelog.

Cikti: assets/data/build-maker-changelog.json
Kullanim: python3 scripts/build-maker-changelog.py
(genelde build-maker-data.py'den sonra calistirilir)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUR = ROOT / "assets" / "data" / "build-maker.json"
PREV = ROOT / "assets" / "data" / "build-maker-prev.json"
OUT = ROOT / "assets" / "data" / "build-maker-changelog.json"

# Karsilastirilacak item gruplari: (json anahtari, gorunen ad)
GEAR_GROUPS = [("mask", "Mask"), ("chest", "Chest"), ("backpack", "Backpack"),
               ("gloves", "Gloves"), ("holster", "Holster"), ("knees", "Kneepads")]
WEAPON_GROUPS = [("assault-rifle", "Assault Rifle"), ("lmg", "LMG"), ("mmr", "MMR"),
                 ("pistol", "Pistol"), ("rifle", "Rifle"), ("shotgun", "Shotgun"), ("smg", "SMG")]
LIST_GROUPS = [("brands", "Brand Set"), ("gearSets", "Gear Set"),
               ("gearTalents", "Gear Talent"), ("weaponTalents", "Weapon Talent"),
               ("skills", "Skill")]

# Degisim kontrol edilecek alanlar (weapon: istatistikler, gear: core/talent)
WEAPON_FIELDS = ["base_damage", "base_rpm", "base_mag_size", "base_reload_time",
                 "optimal_range", "hsd", "talent_slot"]
GEAR_FIELDS = ["core_1", "core_2", "core_3", "minor_1", "minor_2", "minor_3", "talent_slot"]


def diff_items(old: dict, new: dict, fields: list) -> dict:
    added, removed, changed = [], [], []
    old_by_name = {i["name"]: i for i in old}
    new_by_name = {i["name"]: i for i in new}
    for name in sorted(set(new_by_name) - set(old_by_name)):
        added.append(name)
    for name in sorted(set(old_by_name) - set(new_by_name)):
        removed.append(name)
    for name in sorted(set(new_by_name) & set(old_by_name)):
        diffs = [f for f in fields if old_by_name[name].get(f) != new_by_name[name].get(f)]
        if diffs:
            changed.append({"name": name, "fields": diffs})
    return {"added": added, "removed": removed, "changed": changed}


def main():
    if not CUR.exists() or not PREV.exists():
        print("HATA: build-maker.json veya build-maker-prev.json yok.")
        return
    cur = json.loads(CUR.read_text(encoding="utf-8"))
    prev = json.loads(PREV.read_text(encoding="utf-8"))

    sections = []
    total_added = total_removed = total_changed = 0

    for key, label in GEAR_GROUPS:
        d = diff_items(prev["gear"][key], cur["gear"][key], GEAR_FIELDS)
        if d["added"] or d["removed"] or d["changed"]:
            sections.append({"group": label, **d})
            total_added += len(d["added"]); total_removed += len(d["removed"]); total_changed += len(d["changed"])

    for key, label in WEAPON_GROUPS:
        d = diff_items(prev["weapons"][key], cur["weapons"][key], WEAPON_FIELDS)
        if d["added"] or d["removed"] or d["changed"]:
            sections.append({"group": label, **d})
            total_added += len(d["added"]); total_removed += len(d["removed"]); total_changed += len(d["changed"])

    for key, label in LIST_GROUPS:
        old_names = {i["name"] for i in prev[key]}
        new_names = {i["name"] for i in cur[key]}
        added = sorted(new_names - old_names)
        removed = sorted(old_names - new_names)
        if added or removed:
            sections.append({"group": label, "added": added, "removed": removed, "changed": []})
            total_added += len(added); total_removed += len(removed)

    out = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "prev_data": prev["meta"]["generated"],
            "cur_data": cur["meta"]["generated"],
            "totals": {"added": total_added, "removed": total_removed, "changed": total_changed},
        },
        "sections": sections,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Changelog yazildi: {OUT}")
    print(f"Eklendi: {total_added} | Kaldirildi: {total_removed} | Degisti: {total_changed}")


if __name__ == "__main__":
    main()