/* Division 2 Build Maker — Raigulus
 * Veri: /assets/data/build-maker.json (div2hub/game-data)
 * Paylasim: URL hash (base64url JSON) + Discord metni
 *
 * v2: Core / nitelik / mod / talent secimi, tahmini stat toplamlari,
 *     silah SVG siluetleri ve taban istatistikleri.
 */
(function () {
  "use strict";

  var DATA = null;
  var state = {
    mask: null, chest: null, backpack: null, gloves: null, holster: null, knees: null,
    primary: null, secondary: null, skills: [null, null],
    cfg: {}   /* "chest:core_1" -> attrId | "backpack:talent_slot" -> talentName | "primary:muzzle" -> modName */
  };
  var picker = { mode: "slot", slot: null, kind: null, filter: "all", search: "" };

  var GEAR_SLOTS = [
    { key: "mask", label: "Mask" },
    { key: "chest", label: "Chest" },
    { key: "backpack", label: "Backpack" },
    { key: "gloves", label: "Gloves" },
    { key: "holster", label: "Holster" },
    { key: "knees", label: "Kneepads" }
  ];
  var WEAPON_SLOTS = [
    { key: "primary", label: "Primary Weapon" },
    { key: "secondary", label: "Secondary Weapon" }
  ];
  var ATTACH_FIELDS = ["optics", "magazine", "muzzle", "underbarrel"];
  var CORE_KIND = { "armor-gear-core": "Armor", "weapon-damage-gear-core": "Weapon Damage", "skill-tier-gear-core": "Skill Tier" };

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  /* ---------- lookups ---------- */

  function statName(statOrAttrId) {
    if (!DATA || !statOrAttrId) return statOrAttrId || "";
    /* once dogrudan stat_id sozlugu */
    if (DATA.stats[statOrAttrId]) return DATA.stats[statOrAttrId];
    /* degilse attribute id -> stat_id */
    var a = DATA.attributes.find(function (x) { return x.id === statOrAttrId; });
    if (!a) return statOrAttrId;
    return DATA.stats[a.stat_id] || a.stat_id;
  }
  function findAttr(id) { return DATA ? DATA.attributes.find(function (x) { return x.id === id; }) || null : null; }
  function findGearMod(id) { return DATA ? DATA.gearMods.find(function (x) { return x.id === id; }) || null : null; }
  function findWMod(name) { return DATA ? DATA.weaponMods.find(function (x) { return x.name === name; }) || null : null; }
  function findGTalent(name) { return DATA ? DATA.gearTalents.find(function (x) { return x.name === name; }) || null : null; }
  function findWTalent(name) { return DATA ? DATA.weaponTalents.find(function (x) { return x.name === name; }) || null : null; }

  function prettyId(id) {
    var s = id.replace(/-(gear|weapon)-(core|minor|mod)$/, "");
    return s.split("-").map(function (w) {
      if (/^[0-9]/.test(w)) return w.toUpperCase();
      if (w === "dtoc") return "DtTOC";
      if (w === "hsd") return "HSD";
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(" ");
  }

  /* ---------- value formatting ---------- */

  function parseVal(v) {
    if (v == null) return null;
    var s = String(v).trim();
    if (!s || s === "N/A") return null;
    if (s.charAt(s.length - 1) === "%") return { v: parseFloat(s) || 0, u: "%" };
    var n = parseFloat(s);
    if (isNaN(n)) return null;
    return { v: n, u: "" };
  }
  function fmtVal(p) {
    if (!p) return "";
    if (p.u === "%") return "+" + (Math.round(p.v * 10) / 10) + "%";
    if (p.u === "tier") return "+" + p.v + " Tier" + (p.v === 1 ? "" : "s");
    return "+" + Math.round(p.v).toLocaleString("en-US");
  }
  function fmtRange(a) {
    if (!a) return "";
    return a.range_min + " \u2013 " + a.range_max;
  }

  /* ---------- item helpers ---------- */

  function itemLabel(item) {
    if (!item) return "";
    var badges = [];
    if (item.is_exotic === "TRUE") badges.push("Exotic");
    else if (item.is_named === "TRUE") badges.push("Named");
    return item.name + (badges.length ? " [" + badges.join(", ") + "]" : "");
  }
  function gearBrand(item) {
    if (!item) return null;
    if (item.brand_set && item.brand_set !== "N/A") return item.brand_set;
    if (item.gear_set && item.gear_set !== "N/A") return item.gear_set;
    return null;
  }
  function isGearSet(item) { return item && item.gear_set && item.gear_set !== "N/A"; }

  /* Effective value of an item field: user pick wins, otherwise fixed:X content. */
  function effValue(slotKey, item, field) {
    if (!item) return null;
    var raw = item[field];
    if (!raw || raw === "N/A") return null;
    var key = slotKey + ":" + field;
    if (state.cfg[key]) return state.cfg[key];
    if (raw.indexOf("fixed:") === 0) return raw.slice(6);
    return null; /* selectable but not chosen */
  }
  function isSelectable(item, field) {
    var raw = item && item[field];
    return !!raw && raw.indexOf("type:") === 0;
  }
  function typeSuffix(item, field) {
    var raw = item && item[field];
    return raw && raw.indexOf("type:") === 0 ? raw.slice(5) : null;
  }

  /* ---------- display resolution ---------- */

  function displayFor(kind, id) {
    if (!id) return { text: "", tip: "" };
    if (kind === "core" || kind === "minor" || kind === "wminor") {
      var a = findAttr(id);
      if (a) {
        var p = parseVal(a.range_max);
        return { text: statName(a.stat_id) + " " + fmtVal(p), tip: "Roll range: " + fmtRange(a) };
      }
      return { text: prettyId(id), tip: "" };
    }
    if (kind === "gmod") {
      var m = findGearMod(id);
      if (m) return { text: statName(m.stat_id) + " +" + m.range_max, tip: "Mod roll max" };
      return { text: prettyId(id), tip: "" };
    }
    if (kind === "wmod") {
      var w = findWMod(id);
      if (w && w.stats) {
        var parts = w.stats.split(/[|,]/).map(function (s) {
          var kv = s.split(":");
          return statName(kv[0]) + " +" + kv.slice(1).join(":");
        });
        return { text: parts.join(", "), tip: w.name + " (" + w.category + ")" };
      }
      return { text: id, tip: "" };
    }
    if (kind === "gtalent") {
      var t = findGTalent(id);
      return { text: id, tip: t ? t.description : "", desc: t ? t.description : "" };
    }
    if (kind === "wtalent") {
      var wt = findWTalent(id);
      return { text: id, tip: wt ? wt.description : "", desc: wt ? wt.description : "" };
    }
    return { text: id, tip: "" };
  }

  var KIND_SOURCE = {
    core: function () {
      return DATA.attributes.filter(function (a) { return a.compatibility.indexOf("gear-core") !== -1; })
        .map(function (a) { return { id: a.id, name: statName(a.stat_id) + " " + fmtVal(parseVal(a.range_max)), sub: cap(a.category), description: "Roll range: " + fmtRange(a) }; });
    },
    minor: function () {
      return DATA.attributes.filter(function (a) { return a.compatibility.indexOf("gear-minor") !== -1; })
        .map(function (a) { return { id: a.id, name: statName(a.stat_id) + " " + fmtVal(parseVal(a.range_max)), sub: cap(a.category), description: "Roll range: " + fmtRange(a) }; });
    },
    wminor: function () {
      return DATA.attributes.filter(function (a) { return a.compatibility.indexOf("weapon-minor") !== -1; })
        .map(function (a) { return { id: a.id, name: statName(a.stat_id) + " " + fmtVal(parseVal(a.range_max)), sub: cap(a.category), description: "Roll range: " + fmtRange(a) }; });
    },
    gmod: function () { return DATA.gearMods.map(function (m) { return { id: m.id, name: statName(m.stat_id) + " +" + m.range_max, sub: cap(m.category) }; }); },
    gtalent: function (suffix) { return DATA.gearTalents.filter(function (t) { return t.compatibility === suffix; }); },
    wtalent: function (suffix) { return DATA.weaponTalents.filter(function (t) { return t.compatibility.split("|").indexOf(suffix) !== -1; }); },
    wmod: function (suffix) {
      return DATA.weaponMods.filter(function (m) { return (m.compatibility || "").split("|").indexOf(suffix) !== -1; })
        .map(function (m) { return { id: m.name, name: m.name, sub: m.stats ? m.stats.replace(/[:]/, " +").replace(/[|,]/g, ", ") : "", category: m.category }; });
    }
  };
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

  /* ---------- weapon svg ---------- */

  var GUN_ART = {
    "assault-rifle": '<rect x="0" y="7" width="7" height="3"/><rect x="7" y="5" width="20" height="6"/><rect x="10" y="3" width="5" height="2" class="acc"/><rect x="12" y="11" width="4" height="4" class="acc"/><rect x="27" y="6" width="14" height="2.5"/><rect x="41" y="5.5" width="3" height="3.5"/>',
    smg: '<rect x="0" y="7" width="4" height="3"/><rect x="4" y="5" width="16" height="6"/><rect x="9" y="11" width="4" height="5" class="acc"/><rect x="20" y="6" width="9" height="2.5"/><rect x="6" y="3" width="4" height="2" class="acc"/>',
    lmg: '<rect x="0" y="7" width="6" height="3"/><rect x="6" y="5" width="24" height="6"/><rect x="14" y="11" width="7" height="4" class="acc"/><rect x="30" y="6" width="15" height="2.5"/><rect x="39" y="8.5" width="1" height="6"/><rect x="42" y="8.5" width="1" height="6"/>',
    shotgun: '<rect x="0" y="7" width="7" height="3"/><rect x="7" y="5" width="18" height="5"/><rect x="14" y="10" width="8" height="2.5" class="acc"/><rect x="25" y="6" width="17" height="2.5"/>',
    rifle: '<rect x="0" y="6" width="8" height="4"/><rect x="8" y="5" width="22" height="5"/><rect x="16" y="10" width="4" height="4" class="acc"/><rect x="30" y="6" width="14" height="2"/>',
    mmr: '<rect x="0" y="7" width="7" height="3"/><rect x="7" y="6" width="22" height="4"/><rect x="12" y="2" width="10" height="2.5" class="acc"/><rect x="14" y="4.5" width="1.5" height="1.5"/><rect x="19" y="4.5" width="1.5" height="1.5"/><rect x="18" y="10" width="4" height="3"/><rect x="29" y="6.5" width="16" height="2"/>',
    pistol: '<rect x="6" y="5" width="16" height="4"/><rect x="8" y="9" width="5" height="6" class="acc"/><rect x="13" y="9" width="4" height="1.5"/><rect x="22" y="5.5" width="2" height="3"/>'
  };
  function gunSvg(cat) {
    var art = GUN_ART[cat] || GUN_ART["assault-rifle"];
    return '<svg class="bm-wsvg" viewBox="0 0 46 16" aria-hidden="true" focusable="false">' +
      '<g fill="#cfd6df">' + art.replace(/class="acc"/g, "") + "</g>" +
      '<g fill="#f55a00">' + art.replace(/<rect(?![^>]*class="acc")[^>]*\/>/g, "").replace(/class="acc"/g, "") + "</g></svg>";
  }

  /* ---------- render: slots ---------- */

  function renderSlots() {
    var gearHtml = "";
    GEAR_SLOTS.forEach(function (s) {
      gearHtml += gearCard(s.key, s.label, state[s.key]);
    });
    $("bm-gear-slots").innerHTML = gearHtml;

    var wpnHtml = "";
    WEAPON_SLOTS.forEach(function (s) {
      wpnHtml += weaponCard(s.key, s.label, state[s.key]);
    });
    $("bm-weapon-slots").innerHTML = wpnHtml;

    var skHtml = "";
    for (var i = 0; i < 2; i++) {
      var sk = state.skills[i];
      skHtml += slotCard("skill" + i, "Skill " + (i + 1), sk ? sk.name : "Empty", sk ? sk.skill : "");
    }
    $("bm-skill-slots").innerHTML = skHtml;
  }

  function slotCard(key, label, name, sub) {
    return '<div class="bm-slot" data-slot="' + key + '">' +
      '<div class="bm-slot-info"><span class="bm-slot-label">' + label + '</span>' +
      '<span class="bm-slot-name">' + esc(name) + "</span>" +
      (sub ? '<span class="bm-slot-sub">' + esc(sub) + "</span>" : "") + "</div>" +
      '<button type="button" class="bm-slot-change" data-slot="' + key + '">Change</button></div>';
  }

  var CFG_PLACEHOLDER = {
    core: "Select core\u2026", minor: "Select attribute\u2026", wminor: "Select attribute\u2026",
    gmod: "Select mod\u2026", gtalent: "Select talent\u2026", wtalent: "Select talent\u2026",
    wmod: "Select attachment\u2026"
  };

  function cfgRow(slotKey, item, field, label, kind) {
    if (!item) return "";
    var raw = item[field];
    if (!raw || raw === "N/A") return "";
    if (raw.indexOf("type:") === 0) {
      var sel = state.cfg[slotKey + ":" + field];
      var d = sel ? displayFor(kind, sel) : null;
      return '<button type="button" class="bm-cfg" data-cfg="' + slotKey + ":" + field + '" ' +
        (d && d.tip ? 'title="' + esc(d.tip) + '"' : "") + ">" +
        '<span class="bm-cfg-k">' + label + "</span>" +
        '<span class="bm-cfg-v' + (d ? "" : " empty") + '">' + (d ? esc(d.text) : CFG_PLACEHOLDER[kind] || "Select\u2026") + "</span></button>";
    }
    if (raw.indexOf("fixed:") === 0) {
      var fd = displayFor(kind, raw.slice(6));
      return '<div class="bm-fixed"' + (fd.tip ? ' title="' + esc(fd.tip) + '"' : "") + ">" +
        '<span class="bm-cfg-k">' + label + '</span><span class="bm-cfg-v">' + esc(fd.text) + "</span></div>";
    }
    return "";
  }

  function gearCard(slotKey, label, item) {
    var html = '<div class="bm-slot" data-slot="' + slotKey + '"><div class="bm-slot-info">' +
      '<span class="bm-slot-label">' + label + "</span>" +
      '<span class="bm-slot-name">' + (item ? esc(itemLabel(item)) : "Empty") + "</span>" +
      (item && gearBrand(item) ? '<span class="bm-slot-sub">' + esc(gearBrand(item)) + "</span>" : "") +
      "</div>" +
      '<button type="button" class="bm-slot-change" data-slot="' + slotKey + '">Change</button>';
    if (item) {
      for (var c = 1; c <= 3; c++) html += cfgRow(slotKey, item, "core_" + c, c === 1 ? "Core" : "Core " + c, "core");
      if (item.talent_slot && item.talent_slot !== "N/A") {
        var tk = isSelectable(item, "talent_slot") ? "gtalent" : "gtalent";
        html += cfgRow(slotKey, item, "talent_slot", "Talent", tk);
      }
      for (var m = 1; m <= 3; m++) html += cfgRow(slotKey, item, "minor_" + m, "Attribute " + m, "minor");
      for (var d = 1; d <= 3; d++) html += cfgRow(slotKey, item, "mod_" + d, "Mod " + d, "gmod");
    }
    return html + "</div>";
  }

  function weaponCard(slotKey, label, w) {
    var cat = w ? w._cat : null;
    var html = '<div class="bm-slot" data-slot="' + slotKey + '">' +
      (w ? gunSvg(cat) : "") +
      '<div class="bm-slot-info"><span class="bm-slot-label">' + label + "</span>" +
      '<span class="bm-slot-name">' + (w ? esc(itemLabel(w)) : "Empty") + "</span>" +
      (w ? '<span class="bm-slot-sub">' + esc(w.family) + "</span>" : "") + "</div>" +
      '<button type="button" class="bm-slot-change" data-slot="' + slotKey + '">Change</button>';
    if (w) {
      var stats = [];
      if (w.base_damage) stats.push("<b>DMG</b> " + Math.round(parseFloat(w.base_damage)).toLocaleString("en-US"));
      if (w.base_rpm) stats.push("<b>RPM</b> " + w.base_rpm);
      if (w.base_mag_size) stats.push("<b>MAG</b> " + w.base_mag_size);
      if (w.base_reload_time) stats.push("<b>RELOAD</b> " + w.base_reload_time + "s");
      if (w.optimal_range) stats.push("<b>RANGE</b> " + w.optimal_range + "m");
      if (w.hsd) stats.push("<b>HSD</b> " + w.hsd + "%");
      if (stats.length) html += '<div class="bm-wstats">' + stats.join(" ") + "</div>";
      for (var c = 1; c <= 3; c++) html += cfgRow(slotKey, w, "core_" + c, c === 1 ? "Core" : "Core " + c, "core");
      html += cfgRow(slotKey, w, "talent_slot", "Talent", "wtalent");
      for (var m = 1; m <= 3; m++) html += cfgRow(slotKey, w, "minor_" + m, "Attribute " + m, "wminor");
      ATTACH_FIELDS.forEach(function (f) {
        html += cfgRow(slotKey, w, f, f.charAt(0).toUpperCase() + f.slice(1), "wmod");
      });
    }
    return html + "</div>";
  }

  /* ---------- render: summary ---------- */

  function activeSetBonuses() {
    var out = [];
    var gearItems = GEAR_SLOTS.map(function (s) { return state[s.key]; }).filter(Boolean);
    var brandCounts = {}, gearSetCounts = {};
    gearItems.forEach(function (item) {
      if (isGearSet(item)) gearSetCounts[item.gear_set] = (gearSetCounts[item.gear_set] || 0) + 1;
      else if (item.brand_set && item.brand_set !== "N/A") brandCounts[item.brand_set] = (brandCounts[item.brand_set] || 0) + 1;
    });
    Object.keys(brandCounts).forEach(function (brand) {
      var n = brandCounts[brand];
      var b = DATA.brands.find(function (x) { return x.name === brand; });
      if (!b) return;
      [1, 2, 3].forEach(function (pc) {
        if (n >= pc && b[pc + "pc_bonus"] && b[pc + "pc_bonus"] !== "N/A") out.push({ name: brand + " " + pc + "pc", bonus: b[pc + "pc_bonus"] });
      });
    });
    Object.keys(gearSetCounts).forEach(function (gs) {
      var n = gearSetCounts[gs];
      var b = DATA.gearSets.find(function (x) { return x.name === gs; });
      if (!b) return;
      [2, 3, 4].forEach(function (pc) {
        if (n >= pc && b[pc + "pc_bonus"] && b[pc + "pc_bonus"] !== "N/A") out.push({ name: gs + " " + pc + "pc", bonus: b[pc + "pc_bonus"] });
      });
    });
    return out;
  }

  function bonusText(bonus) {
    var parsed = parseBonus(bonus);
    if (!parsed) return "";
    return parsed.map(function (p) {
      if (p.type === "stat") return statName(p.stat) + " " + p.value;
      if (p.type === "talent") return "Talent: " + p.name;
      return p.text;
    }).join(", ");
  }
  function parseBonus(bonus) {
    if (!bonus || bonus === "N/A") return null;
    return bonus.split("|").map(function (b) {
      b = b.trim();
      if (b.startsWith("stat:")) {
        var parts = b.split(":");
        return { type: "stat", stat: parts[1], value: parts.slice(2).join(":") };
      }
      if (b.startsWith("talent:")) return { type: "talent", name: b.slice(7) };
      return { type: "raw", text: b };
    });
  }

  /* Collect every stat contribution at max roll. */
  function collectStats() {
    var acc = {};
    function add(statId, valStr) {
      if (!statId || !valStr) return;
      var p = parseVal(valStr);
      if (!p) return;
      var u = p.u === "%" ? "%" : (statId === "skill-tier" ? "tier" : "");
      if (!acc[statId]) acc[statId] = { u: u, v: 0 };
      acc[statId].v += p.v;
    }
    function addAttr(id) {
      var a = findAttr(id);
      if (a) add(a.stat_id, a.range_max);
    }
    GEAR_SLOTS.forEach(function (s) {
      var it = state[s.key];
      if (!it) return;
      ["core_1", "core_2", "core_3", "minor_1", "minor_2", "minor_3"].forEach(function (f) { addAttr(effValue(s.key, it, f)); });
      ["mod_1", "mod_2", "mod_3"].forEach(function (f) {
        var mid = effValue(s.key, it, f);
        var gm = mid && findGearMod(mid);
        if (gm) add(gm.stat_id, gm.range_max);
      });
    });
    WEAPON_SLOTS.forEach(function (s) {
      var w = state[s.key];
      if (!w) return;
      ["core_1", "core_2", "core_3", "minor_1", "minor_2", "minor_3"].forEach(function (f) { addAttr(effValue(s.key, w, f)); });
      ATTACH_FIELDS.forEach(function (f) {
        var mid = effValue(s.key, w, f);
        var wm = mid && findWMod(mid);
        if (wm && wm.stats) wm.stats.split(/[|,]/).forEach(function (kv) {
          var parts = kv.split(":");
          add(parts[0], parts.slice(1).join(":"));
        });
      });
    });
    activeSetBonuses().forEach(function (sb) {
      parseBonus(sb.bonus).forEach(function (p) { if (p.type === "stat") add(p.stat, p.value); });
    });
    return Object.keys(acc).map(function (sid) {
      return { stat: sid, label: DATA.stats[sid] || sid, u: acc[sid].u, v: acc[sid].v };
    }).sort(function (a, b) { return b.v - a.v; });
  }

  function renderSummary() {
    var html = "";

    /* set bonuses */
    var sets = activeSetBonuses();
    html += "<h3>Set Bonuses</h3>" + (sets.length
      ? sets.map(function (sb) {
          return '<div class="bm-bonus"><span class="bm-bonus-name">' + esc(sb.name) + "</span>" +
            '<span class="bm-bonus-part">' + esc(bonusText(sb.bonus)) + "</span></div>";
        }).join("")
      : '<p class="bm-empty">No set bonuses yet \u2014 add gear pieces.</p>');

    /* cores */
    var cores = { Armor: 0, "Weapon Damage": 0, "Skill Tier": 0 };
    var unassigned = 0;
    GEAR_SLOTS.forEach(function (s) {
      var it = state[s.key];
      if (!it) return;
      for (var c = 1; c <= 3; c++) {
        var f = "core_" + c;
        if (!it[f] || it[f] === "N/A") continue;
        var v = effValue(s.key, it, f);
        if (!v) { unassigned++; continue; }
        var a = findAttr(v);
        var lbl = a ? (CORE_KIND[a.id] || DATA.stats[a.stat_id] || a.stat_id) : prettyId(v);
        if (cores[lbl] != null) cores[lbl]++;
        else cores[lbl] = (cores[lbl] || 0) + 1;
      }
    });
    var coreSpans = Object.keys(cores).map(function (k) { return "<span>" + esc(k) + ": " + cores[k] + "</span>"; }).join(" ");
    if (unassigned) coreSpans += ' <span class="bm-unassigned">Unassigned cores: ' + unassigned + "</span>";
    html += "<h3>Cores</h3><p class='bm-cores'>" + coreSpans + "</p>";

    /* estimated totals */
    var totals = collectStats();
    html += "<h3>Estimated Totals <span class='bm-note'>max rolls incl. set bonuses</span></h3>" +
      (totals.length
        ? "<div class='bm-totals'>" + totals.map(function (t) {
            return "<div class='bm-stat-row'><span>" + esc(t.label) + "</span><b>" + fmtVal(t) + "</b></div>";
          }).join("") + "</div>"
        : '<p class="bm-empty">Pick cores, attributes and mods to see totals.</p>');

    /* talents */
    var talents = [];
    GEAR_SLOTS.forEach(function (s) {
      var it = state[s.key];
      var t = it && effValue(s.key, it, "talent_slot");
      if (t) { var d = displayFor("gtalent", t); talents.push({ name: t, desc: d.desc || "" }); }
    });
    WEAPON_SLOTS.forEach(function (s) {
      var w = state[s.key];
      var t = w && effValue(s.key, w, "talent_slot");
      if (t) { var d = displayFor("wtalent", t); talents.push({ name: t, desc: d.desc || "" }); }
    });
    html += "<h3>Talents</h3>" + (talents.length
      ? '<ul class="bm-talents">' + talents.map(function (t) {
          return "<li><strong>" + esc(t.name) + "</strong>" +
            (t.desc ? '<span class="bm-talent-desc">' + esc(t.desc) + "</span>" : "") + "</li>";
        }).join("") + "</ul>"
      : '<p class="bm-empty">No talents selected.</p>');

    /* exotic check */
    var gearItems = GEAR_SLOTS.map(function (s) { return state[s.key]; }).filter(Boolean);
    var exoGear = gearItems.filter(function (i) { return i.is_exotic === "TRUE"; }).length;
    var exoWpn = WEAPON_SLOTS.filter(function (s) { return state[s.key] && state[s.key].is_exotic === "TRUE"; }).length;
    var warns = [];
    if (exoGear > 1) warns.push("More than 1 exotic gear piece \u2014 only one can be equipped.");
    if (exoWpn > 1) warns.push("More than 1 exotic weapon \u2014 only one can be equipped.");
    if (warns.length) html += '<div class="bm-warn">' + warns.map(function (w) { return "<p>" + w + "</p>"; }).join("") + "</div>";

    $("bm-summary").innerHTML = html;
  }

  /* ---------- picker ---------- */

  function openPicker(slotKey) {
    var kind, title;
    if (slotKey.indexOf("skill") === 0) { kind = "skill"; title = "Pick Skill"; }
    else if (slotKey === "primary" || slotKey === "secondary") { kind = "weapon"; title = "Pick Weapon"; }
    else { kind = "gear"; title = "Pick " + GEAR_SLOTS.find(function (s) { return s.key === slotKey; }).label; }
    picker.mode = "slot";
    picker.slot = slotKey;
    picker.kind = kind;
    picker.filter = "all";
    picker.search = "";
    $("bm-modal-title").textContent = title;
    $("bm-modal-search").value = "";
    renderPickerFilters();
    renderPickerList();
    $("bm-modal").hidden = false;
  }

  function openCfgPicker(cfgKey) {
    var parts = cfgKey.split(":");
    var slotKey = parts[0], field = parts[1];
    var item = state[slotKey];
    if (!item) return;
    var suffix = typeSuffix(item, field);
    var kind;
    if (field.indexOf("core_") === 0) kind = "core";
    else if (field === "talent_slot") kind = item._cat ? "wtalent" : "gtalent";
    else if (field.indexOf("minor_") === 0) kind = item._cat ? "wminor" : "minor";
    else if (field.indexOf("mod_") === 0) kind = "gmod";
    else kind = "wmod"; /* optics/magazine/muzzle/underbarrel */
    var titles = {
      core: "Pick Core (Armor / Weapon Damage / Skill Tier)",
      minor: "Pick Attribute", wminor: "Pick Weapon Attribute",
      gmod: "Pick Gear Mod", gtalent: "Pick Talent", wtalent: "Pick Weapon Talent",
      wmod: "Pick Attachment"
    };
    picker.mode = "cfg";
    picker.slot = cfgKey;
    picker.kind = kind;
    picker.suffix = suffix;
    picker.filter = "all";
    picker.search = "";
    $("bm-modal-title").textContent = titles[kind] || "Pick";
    $("bm-modal-search").value = "";
    renderPickerFilters();
    renderPickerList();
    $("bm-modal").hidden = false;
  }

  function renderPickerFilters() {
    var chips = [{ id: "all", label: "All" }];
    if (picker.mode === "slot") {
      chips.push({ id: "exotic", label: "Exotic" }, { id: "named", label: "Named" });
      if (picker.kind === "gear") {
        var brands = {};
        DATA.brands.forEach(function (b) { brands[b.name] = true; });
        DATA.gearSets.forEach(function (g) { brands[g.name] = true; });
        Object.keys(brands).sort().forEach(function (b) { chips.push({ id: "brand:" + b, label: b }); });
      }
      if (picker.kind === "weapon") {
        Object.keys(DATA.weapons).sort().forEach(function (f) { chips.push({ id: "family:" + f, label: f }); });
      }
    } else if (picker.kind === "minor" || picker.kind === "wminor" || picker.kind === "gmod") {
      chips.push({ id: "cat:offensive", label: "Offensive" }, { id: "cat:defensive", label: "Defensive" }, { id: "cat:skill", label: "Skill" });
    }
    var html = chips.map(function (c) {
      return '<button type="button" class="bm-chip' + (picker.filter === c.id ? " active" : "") + '" data-filter="' + esc(c.id) + '">' + esc(c.label) + "</button>";
    }).join("");
    $("bm-modal-filters").innerHTML = html;
  }

  function pickerItems() {
    var items = [];
    if (picker.mode === "slot") {
      if (picker.kind === "gear") items = DATA.gear[picker.slot];
      else if (picker.kind === "weapon") {
        Object.keys(DATA.weapons).forEach(function (f) {
          DATA.weapons[f].forEach(function (w) { items.push(Object.assign({ _cat: f }, w)); });
        });
      } else items = DATA.skills;
    } else {
      var src = KIND_SOURCE[picker.kind];
      items = src ? src(picker.suffix) : [];
    }
    var q = picker.search.toLowerCase();
    if (q) items = items.filter(function (i) {
      return (i.name || "").toLowerCase().indexOf(q) !== -1 ||
        (i.sub || "").toLowerCase().indexOf(q) !== -1 ||
        (i.description || "").toLowerCase().indexOf(q) !== -1;
    });
    if (picker.mode === "slot") {
      if (picker.filter === "exotic") items = items.filter(function (i) { return i.is_exotic === "TRUE"; });
      else if (picker.filter === "named") items = items.filter(function (i) { return i.is_named === "TRUE"; });
      else if (picker.filter.indexOf("brand:") === 0) {
        var b = picker.filter.slice(6);
        items = items.filter(function (i) { return i.brand_set === b || i.gear_set === b; });
      } else if (picker.filter.indexOf("family:") === 0) {
        var f = picker.filter.slice(7);
        items = items.filter(function (i) { return i.family === f; });
      }
    } else if (picker.filter.indexOf("cat:") === 0) {
      var c = picker.filter.slice(4);
      items = items.filter(function (i) { return i.category === c; });
    }
    return items;
  }

  function renderPickerList() {
    var items = pickerItems();
    var html = items.map(function (i) {
      var sub = i.sub;
      if (sub == null) {
        sub = (i.brand_set && i.brand_set !== "N/A" ? i.brand_set : "") ||
              (i.gear_set && i.gear_set !== "N/A" ? i.gear_set : "") ||
              (i.family || i.skill || "") ||
              (i.stat_id ? DATA.stats[i.stat_id] + " (max " + i.range_max + ")" : "") || "";
      }
      var desc = i.description ? '<span class="bm-item-desc">' + esc(i.description) + "</span>" : "";
      var label = picker.mode === "slot" ? itemLabel(i) : (i.name || prettyId(i.id));
      return '<li><button type="button" class="bm-item" data-name="' + esc(i.name || i.id) + '">' +
        '<span class="bm-item-wrap"><span class="bm-item-name">' + esc(label) + "</span>" +
        (sub ? '<span class="bm-item-sub">' + esc(sub) + "</span>" : "") + desc + "</span></button></li>";
    }).join("");
    $("bm-modal-list").innerHTML = html || '<li class="bm-empty">No items match.</li>';
  }

  function setSlot(slotKey, item) {
    if (slotKey.indexOf("skill") === 0) {
      state.skills[parseInt(slotKey.slice(5), 10)] = item;
    } else {
      state[slotKey] = item;
      /* drop stale picks for this slot */
      Object.keys(state.cfg).forEach(function (k) { if (k.indexOf(slotKey + ":") === 0) delete state.cfg[k]; });
    }
    renderSlots(); renderSummary(); updateHash();
  }

  function setCfg(cfgKey, value) {
    state.cfg[cfgKey] = value;
    renderSlots(); renderSummary(); updateHash();
  }

  /* ---------- share ---------- */

  function encodeState() {
    var s = {
      m: state.mask && state.mask.name, c: state.chest && state.chest.name,
      b: state.backpack && state.backpack.name, g: state.gloves && state.gloves.name,
      h: state.holster && state.holster.name, k: state.knees && state.knees.name,
      w1: state.primary && state.primary.name, w2: state.secondary && state.secondary.name,
      s1: state.skills[0] && state.skills[0].name, s2: state.skills[1] && state.skills[1].name
    };
    var keys = Object.keys(state.cfg);
    if (keys.length) { s.cf = {}; keys.sort().forEach(function (k) { s.cf[k] = state.cfg[k]; }); }
    return btoa(JSON.stringify(s)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function decodeState(hash) {
    try {
      var json = atob(hash.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(json);
    } catch (e) { return null; }
  }
  function findByName(list, name) {
    if (!name) return null;
    return list.find(function (i) { return i.name === name; }) || null;
  }
  function applyState(s) {
    if (!s) return;
    state.mask = findByName(DATA.gear.mask, s.m);
    state.chest = findByName(DATA.gear.chest, s.c);
    state.backpack = findByName(DATA.gear.backpack, s.b);
    state.gloves = findByName(DATA.gear.gloves, s.g);
    state.holster = findByName(DATA.gear.holster, s.h);
    state.knees = findByName(DATA.gear.knees, s.k);
    var allWeapons = [];
    Object.keys(DATA.weapons).forEach(function (f) {
      DATA.weapons[f].forEach(function (w) { allWeapons.push(Object.assign({ _cat: f }, w)); });
    });
    state.primary = findByName(allWeapons, s.w1);
    state.secondary = findByName(allWeapons, s.w2);
    state.skills = [findByName(DATA.skills, s.s1), findByName(DATA.skills, s.s2)];
    state.cfg = {};
    if (s.cf && typeof s.cf === "object") {
      var slots = { mask: state.mask, chest: state.chest, backpack: state.backpack, gloves: state.gloves, holster: state.holster, knees: state.knees, primary: state.primary, secondary: state.secondary };
      Object.keys(s.cf).forEach(function (k) {
        var slot = k.split(":")[0];
        if (slots[slot]) state.cfg[k] = s.cf[k];
      });
    }
  }
  function updateHash() {
    var h = encodeState();
    try { history.replaceState(null, "", "#" + h); } catch (e) { /* noop */ }
  }

  function copyText() {
    var lines = ["**Division 2 Build**"];
    var rows = [
      ["Mask", state.mask], ["Chest", state.chest], ["Backpack", state.backpack],
      ["Gloves", state.gloves], ["Holster", state.holster], ["Kneepads", state.knees],
      ["Primary", state.primary], ["Secondary", state.secondary],
      ["Skill 1", state.skills[0]], ["Skill 2", state.skills[1]]
    ];
    rows.forEach(function (r) { lines.push("**" + r[0] + ":** " + (r[1] ? itemLabel(r[1]) : "-")); });
    var gearItems = GEAR_SLOTS.map(function (s) { return state[s.key]; }).filter(Boolean);
    var brands = {};
    gearItems.forEach(function (i) { var b = gearBrand(i); if (b) brands[b] = (brands[b] || 0) + 1; });
    var bonusLine = Object.keys(brands).map(function (b) { return b + " x" + brands[b]; }).join(", ");
    if (bonusLine) lines.push("**Sets:** " + bonusLine);
    var totals = collectStats().slice(0, 8);
    if (totals.length) lines.push("**Totals (max rolls):** " + totals.map(function (t) { return t.label + " " + fmtVal(t); }).join(", "));
    var tal = [];
    GEAR_SLOTS.concat(WEAPON_SLOTS).forEach(function (s) {
      var it = state[s.key];
      var t = it && effValue(s.key, it, "talent_slot");
      if (t) tal.push(t);
    });
    if (tal.length) lines.push("**Talents:** " + tal.join(", "));
    lines.push("Build: " + location.href.split("#")[0] + "#" + encodeState());
    return lines.join("\n");
  }

  function trackShare(kind) {
    try {
      if (typeof gtag === "function") gtag("event", "build_share", { share_type: kind });
    } catch (e) {}
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash("Copied!"); });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); flash("Copied!"); } catch (e) { /* noop */ }
      document.body.removeChild(ta);
    }
  }
  function flash(msg) {
    var el = $("bm-copy-link");
    var old = el.textContent;
    el.textContent = msg;
    setTimeout(function () { el.textContent = old; }, 1500);
  }

  /* ---------- events ---------- */

  document.addEventListener("click", function (e) {
    var change = e.target.closest(".bm-slot-change");
    if (change) { openPicker(change.getAttribute("data-slot")); return; }
    var cfgBtn = e.target.closest(".bm-cfg");
    if (cfgBtn) { openCfgPicker(cfgBtn.getAttribute("data-cfg")); return; }
    var chip = e.target.closest(".bm-chip");
    if (chip) { picker.filter = chip.getAttribute("data-filter"); renderPickerFilters(); renderPickerList(); return; }
    var itemBtn = e.target.closest(".bm-item");
    if (itemBtn) {
      var name = itemBtn.getAttribute("data-name");
      var items = pickerItems();
      var item = items.find(function (i) { return (i.name || i.id) === name; });
      if (item) {
        if (picker.mode === "slot") setSlot(picker.slot, item);
        else setCfg(picker.slot, item.id || item.name);
      }
      $("bm-modal").hidden = true;
      return;
    }
    if (e.target.closest("#bm-modal-close")) { $("bm-modal").hidden = true; return; }
    if (e.target.id === "bm-copy-link") { copyToClipboard(location.href.split("#")[0] + "#" + encodeState()); trackShare("copy_link"); return; }
    if (e.target.id === "bm-copy-text") { copyToClipboard(copyText()); trackShare("copy_text"); return; }
    if (e.target.id === "bm-reset") {
      state = { mask: null, chest: null, backpack: null, gloves: null, holster: null, knees: null,
                primary: null, secondary: null, skills: [null, null], cfg: {} };
      renderSlots(); renderSummary();
      try { history.replaceState(null, "", location.pathname); } catch (err) { /* noop */ }
      return;
    }
  });

  $("bm-modal-search").addEventListener("input", function (e) {
    picker.search = e.target.value;
    renderPickerList();
  });

  $("bm-modal").addEventListener("click", function (e) {
    if (e.target === $("bm-modal")) $("bm-modal").hidden = true;
  });

  /* ---------- init ---------- */

  fetch("/assets/data/build-maker.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      DATA = data;
      var gen = (data.meta.generated || "").slice(0, 10);
      var c = data.meta.counts || {};
      var total = (c.masks || 0) + (c.chests || 0) + (c.backpacks || 0) + (c.gloves || 0) + (c.holsters || 0) + (c.knees || 0);
      $("bm-data-meta").textContent = "Data: " + total + " gear pieces, " +
        ((c.assault_rifles || 0) + (c.lmgs || 0) + (c.mmrs || 0) + (c.pistols || 0) + (c.rifles || 0) + (c.shotguns || 0) + (c.smgs || 0)) +
        " weapons, " + (c.brand_sets || 0) + " brand sets, " + (c.gear_sets || 0) + " gear sets \u2014 updated " + gen +
        " (source: div2hub/game-data)";
      var s = decodeState(location.hash.slice(1));
      applyState(s);
      renderSlots();
      renderSummary();
      loadChangelog();
    })
    .catch(function (err) {
      $("bm-data-meta").textContent = "Data could not be loaded: " + err.message;
    });

  function loadChangelog() {
    var meta = $("bm-changelog-meta"), box = $("bm-changelog");
    fetch("/assets/data/build-maker-changelog.json")
      .then(function (r) { return r.json(); })
      .then(function (c) {
        var t = c.meta.totals;
        if (!c.sections.length) {
          meta.textContent = "No changes since the last data update. The changelog appears automatically after each patch refresh.";
          box.innerHTML = "";
          return;
        }
        meta.textContent = "Changes between " + (c.meta.prev_data || "previous data").slice(0, 10) +
          " and " + (c.meta.cur_data || "current data").slice(0, 10) + " \u2014 " +
          t.added + " added, " + t.removed + " removed, " + t.changed + " modified.";
        var html = c.sections.map(function (s) {
          var h = '<div class="bm-changelog-group"><h3>' + s.group + "</h3>";
          if (s.added.length) h += '<p class="bm-chg bm-chg-added"><strong>Added:</strong> ' + esc(s.added.join(", ")) + "</p>";
          if (s.removed.length) h += '<p class="bm-chg bm-chg-removed"><strong>Removed:</strong> ' + esc(s.removed.join(", ")) + "</p>";
          if (s.changed.length) h += '<p class="bm-chg bm-chg-changed"><strong>Modified:</strong> ' +
            esc(s.changed.map(function (x) { return x.name + " (" + x.fields.join(", ") + ")"; }).join(", ")) + "</p>";
          return h + "</div>";
        }).join("");
        box.innerHTML = html;
      })
      .catch(function () {
        meta.textContent = "Changelog unavailable.";
      });
  }
})();
