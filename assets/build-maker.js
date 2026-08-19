/* Division 2 Build Maker — Raigulus
 * Veri: /assets/data/build-maker.json (div2hub/game-data)
 * Paylasim: URL hash (base64url JSON) + Discord metni
 */
(function () {
  "use strict";

  var DATA = null;
  var state = { mask: null, chest: null, backpack: null, gloves: null, holster: null, knees: null,
                primary: null, secondary: null, skills: [null, null] };
  var picker = { slot: null, kind: null, filter: "all", search: "" };

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

  function $(id) { return document.getElementById(id); }

  function statName(attrId) {
    if (!DATA || !attrId) return attrId || "";
    var a = DATA.attributes.find(function (x) { return x.id === attrId; });
    if (!a) return attrId;
    return DATA.stats[a.stat_id] || a.stat_id;
  }

  function parseBonus(bonus) {
    if (!bonus || bonus === "N/A") return null;
    return bonus.split("|").map(function (b) {
      b = b.trim();
      if (b.startsWith("stat:")) {
        var parts = b.split(":");
        return { type: "stat", stat: parts[1], value: parts.slice(2).join(":") };
      }
      if (b.startsWith("talent:")) {
        return { type: "talent", name: b.slice(7) };
      }
      return { type: "raw", text: b };
    });
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

  function isGearSet(item) {
    return item && item.gear_set && item.gear_set !== "N/A";
  }

  /* ---------- render ---------- */

  function renderSlots() {
    var gearHtml = "";
    GEAR_SLOTS.forEach(function (s) {
      var item = state[s.key];
      gearHtml += slotCard(s.key, s.label, item ? itemLabel(item) : "Empty", item ? gearBrand(item) : "");
    });
    $("bm-gear-slots").innerHTML = gearHtml;

    var wpnHtml = "";
    WEAPON_SLOTS.forEach(function (s) {
      var item = state[s.key];
      wpnHtml += slotCard(s.key, s.label, item ? itemLabel(item) : "Empty", item ? item.family : "");
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
      '<span class="bm-slot-name">' + name + '</span>' +
      (sub ? '<span class="bm-slot-sub">' + sub + '</span>' : "") + "</div>" +
      '<button type="button" class="bm-slot-change" data-slot="' + key + '">Change</button></div>';
  }

  function renderSummary() {
    var html = "";
    var gearItems = GEAR_SLOTS.map(function (s) { return state[s.key]; }).filter(Boolean);

    /* brand / gear set bonuses */
    var brandCounts = {};
    var gearSetCounts = {};
    gearItems.forEach(function (item) {
      if (isGearSet(item)) {
        gearSetCounts[item.gear_set] = (gearSetCounts[item.gear_set] || 0) + 1;
      } else if (item.brand_set && item.brand_set !== "N/A") {
        brandCounts[item.brand_set] = (brandCounts[item.brand_set] || 0) + 1;
      }
    });

    var bonusRows = "";
    Object.keys(brandCounts).forEach(function (brand) {
      var n = brandCounts[brand];
      var b = DATA.brands.find(function (x) { return x.name === brand; });
      if (!b) return;
      var parts = [];
      if (n >= 1 && b["1pc_bonus"] && b["1pc_bonus"] !== "N/A") parts.push("1pc: " + bonusText(b["1pc_bonus"]));
      if (n >= 2 && b["2pc_bonus"] && b["2pc_bonus"] !== "N/A") parts.push("2pc: " + bonusText(b["2pc_bonus"]));
      if (n >= 3 && b["3pc_bonus"] && b["3pc_bonus"] !== "N/A") parts.push("3pc: " + bonusText(b["3pc_bonus"]));
      bonusRows += '<div class="bm-bonus"><span class="bm-bonus-name">' + brand + " (" + n + "pc)</span>" +
        parts.map(function (p) { return '<span class="bm-bonus-part">' + p + "</span>"; }).join("") + "</div>";
    });
    Object.keys(gearSetCounts).forEach(function (gs) {
      var n = gearSetCounts[gs];
      var b = DATA.gearSets.find(function (x) { return x.name === gs; });
      if (!b) return;
      var parts = [];
      if (n >= 2 && b["2pc_bonus"] && b["2pc_bonus"] !== "N/A") parts.push("2pc: " + bonusText(b["2pc_bonus"]));
      if (n >= 3 && b["3pc_bonus"] && b["3pc_bonus"] !== "N/A") parts.push("3pc: " + bonusText(b["3pc_bonus"]));
      if (n >= 4 && b["4pc_bonus"] && b["4pc_bonus"] !== "N/A") parts.push("4pc: " + bonusText(b["4pc_bonus"]));
      bonusRows += '<div class="bm-bonus"><span class="bm-bonus-name">' + gs + " (" + n + "pc)</span>" +
        parts.map(function (p) { return '<span class="bm-bonus-part">' + p + "</span>"; }).join("") + "</div>";
    });
    html += "<h3>Set Bonuses</h3>" + (bonusRows || '<p class="bm-empty">No set bonuses yet — add gear pieces.</p>');

    /* cores */
    var cores = { armor: 0, weapon: 0, skill: 0, other: 0 };
    gearItems.forEach(function (item) {
      var c = item.core_1 || "";
      if (c.indexOf("armor-gear-core") !== -1) cores.armor++;
      else if (c.indexOf("weapon-damage-gear-core") !== -1) cores.weapon++;
      else if (c.indexOf("skill-tier-gear-core") !== -1) cores.skill++;
      else cores.other++;
    });
    html += "<h3>Cores</h3><p class='bm-cores'>" +
      "<span>Armor: " + cores.armor + "</span> " +
      "<span>Weapon Damage: " + cores.weapon + "</span> " +
      "<span>Skill Tier: " + cores.skill + "</span>" +
      (cores.other ? " <span>Selectable: " + cores.other + "</span>" : "") + "</p>";

    /* talents */
    var talents = [];
    gearItems.forEach(function (item) {
      if (item.talent_slot && item.talent_slot !== "N/A") talents.push(item.talent_slot.replace(/^fixed:/, ""));
    });
    [state.primary, state.secondary].forEach(function (w) {
      if (w && w.talent_slot && w.talent_slot !== "N/A") talents.push(w.talent_slot.replace(/^fixed:/, ""));
    });
    html += "<h3>Talents</h3>" + (talents.length
      ? '<ul class="bm-talents">' + talents.map(function (t) { return "<li>" + t + "</li>"; }).join("") + "</ul>"
      : '<p class="bm-empty">No talents selected.</p>');

    /* exotic check */
    var exoGear = gearItems.filter(function (i) { return i.is_exotic === "TRUE"; }).length;
    var exoWpn = [state.primary, state.secondary].filter(function (w) { return w && w.is_exotic === "TRUE"; }).length;
    var warns = [];
    if (exoGear > 1) warns.push("More than 1 exotic gear piece — only one can be equipped.");
    if (exoWpn > 1) warns.push("More than 1 exotic weapon — only one can be equipped.");
    if (warns.length) html += '<div class="bm-warn">' + warns.map(function (w) { return "<p>" + w + "</p>"; }).join("") + "</div>";

    $("bm-summary").innerHTML = html;
  }

  /* ---------- picker ---------- */

  function openPicker(slotKey) {
    var kind, title;
    if (slotKey.indexOf("skill") === 0) {
      kind = "skill"; title = "Pick Skill";
    } else if (slotKey === "primary" || slotKey === "secondary") {
      kind = "weapon"; title = "Pick Weapon";
    } else {
      kind = "gear"; title = "Pick " + GEAR_SLOTS.find(function (s) { return s.key === slotKey; }).label;
    }
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

  function renderPickerFilters() {
    var chips = [{ id: "all", label: "All" }, { id: "exotic", label: "Exotic" }, { id: "named", label: "Named" }];
    if (picker.kind === "gear") {
      var brands = {};
      DATA.brands.forEach(function (b) { brands[b.name] = true; });
      DATA.gearSets.forEach(function (g) { brands[g.name] = true; });
      Object.keys(brands).forEach(function (b) { chips.push({ id: "brand:" + b, label: b }); });
    }
    if (picker.kind === "weapon") {
      Object.keys(DATA.weapons).forEach(function (f) { chips.push({ id: "family:" + f, label: f }); });
    }
    var html = chips.map(function (c) {
      return '<button type="button" class="bm-chip' + (picker.filter === c.id ? " active" : "") + '" data-filter="' + c.id + '">' + c.label + "</button>";
    }).join("");
    $("bm-modal-filters").innerHTML = html;
  }

  function pickerItems() {
    var items = [];
    if (picker.kind === "gear") {
      items = DATA.gear[picker.slot];
    } else if (picker.kind === "weapon") {
      Object.keys(DATA.weapons).forEach(function (f) {
        DATA.weapons[f].forEach(function (w) { items.push(w); });
      });
    } else {
      items = DATA.skills;
    }
    var q = picker.search.toLowerCase();
    if (q) items = items.filter(function (i) { return i.name.toLowerCase().indexOf(q) !== -1; });
    if (picker.filter === "exotic") items = items.filter(function (i) { return i.is_exotic === "TRUE"; });
    else if (picker.filter === "named") items = items.filter(function (i) { return i.is_named === "TRUE"; });
    else if (picker.filter.indexOf("brand:") === 0) {
      var b = picker.filter.slice(6);
      items = items.filter(function (i) { return i.brand_set === b || i.gear_set === b; });
    } else if (picker.filter.indexOf("family:") === 0) {
      var f = picker.filter.slice(7);
      items = items.filter(function (i) { return i.family === f; });
    }
    return items;
  }

  function renderPickerList() {
    var items = pickerItems();
    var html = items.map(function (i) {
      var sub = i.brand_set && i.brand_set !== "N/A" ? i.brand_set : (i.gear_set && i.gear_set !== "N/A" ? i.gear_set : (i.family || i.skill || ""));
      return '<li><button type="button" class="bm-item" data-name="' + i.name.replace(/"/g, "&quot;") + '">' +
        '<span class="bm-item-name">' + itemLabel(i) + "</span>" +
        (sub ? '<span class="bm-item-sub">' + sub + "</span>" : "") + "</button></li>";
    }).join("");
    $("bm-modal-list").innerHTML = html || '<li class="bm-empty">No items match.</li>';
  }

  function setSlot(slotKey, item) {
    if (slotKey.indexOf("skill") === 0) {
      state.skills[parseInt(slotKey.slice(5), 10)] = item;
    } else {
      state[slotKey] = item;
    }
    renderSlots();
    renderSummary();
    updateHash();
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
    Object.keys(DATA.weapons).forEach(function (f) { allWeapons = allWeapons.concat(DATA.weapons[f]); });
    state.primary = findByName(allWeapons, s.w1);
    state.secondary = findByName(allWeapons, s.w2);
    state.skills = [findByName(DATA.skills, s.s1), findByName(DATA.skills, s.s2)];
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
    rows.forEach(function (r) {
      lines.push("**" + r[0] + ":** " + (r[1] ? itemLabel(r[1]) : "-"));
    });
    var gearItems = GEAR_SLOTS.map(function (s) { return state[s.key]; }).filter(Boolean);
    var brands = {};
    gearItems.forEach(function (i) {
      var b = gearBrand(i);
      if (b) brands[b] = (brands[b] || 0) + 1;
    });
    var bonusLine = Object.keys(brands).map(function (b) { return b + " x" + brands[b]; }).join(", ");
    if (bonusLine) lines.push("**Sets:** " + bonusLine);
    lines.push("Build: " + location.href.split("#")[0] + "#" + encodeState());
    return lines.join("\n");
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
    var chip = e.target.closest(".bm-chip");
    if (chip) { picker.filter = chip.getAttribute("data-filter"); renderPickerFilters(); renderPickerList(); return; }
    var itemBtn = e.target.closest(".bm-item");
    if (itemBtn) {
      var name = itemBtn.getAttribute("data-name");
      var items = pickerItems();
      var item = items.find(function (i) { return i.name === name; });
      if (item) setSlot(picker.slot, item);
      $("bm-modal").hidden = true;
      return;
    }
    if (e.target.closest("#bm-modal-close")) { $("bm-modal").hidden = true; return; }
    if (e.target.id === "bm-copy-link") { copyToClipboard(location.href.split("#")[0] + "#" + encodeState()); return; }
    if (e.target.id === "bm-copy-text") { copyToClipboard(copyText()); return; }
    if (e.target.id === "bm-reset") {
      state = { mask: null, chest: null, backpack: null, gloves: null, holster: null, knees: null,
                primary: null, secondary: null, skills: [null, null] };
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
        " weapons, " + (c.brand_sets || 0) + " brand sets, " + (c.gear_sets || 0) + " gear sets — updated " + gen +
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
          " and " + (c.meta.cur_data || "current data").slice(0, 10) + " — " +
          t.added + " added, " + t.removed + " removed, " + t.changed + " modified.";
        var html = c.sections.map(function (s) {
          var h = '<div class="bm-changelog-group"><h3>' + s.group + '</h3>';
          if (s.added.length) h += '<p class="bm-chg bm-chg-added"><strong>Added:</strong> ' + esc(s.added.join(", ")) + '</p>';
          if (s.removed.length) h += '<p class="bm-chg bm-chg-removed"><strong>Removed:</strong> ' + esc(s.removed.join(", ")) + '</p>';
          if (s.changed.length) h += '<p class="bm-chg bm-chg-changed"><strong>Modified:</strong> ' +
            esc(s.changed.map(function (x) { return x.name + " (" + x.fields.join(", ") + ")"; }).join(", ")) + '</p>';
          return h + "</div>";
        }).join("");
        box.innerHTML = html;
      })
      .catch(function () {
        meta.textContent = "Changelog unavailable.";
      });
  }

  function esc(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();