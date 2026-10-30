// Diablo 4 World Boss schedule table + spawn alerts for /diablo-4/world-boss-timer/
//
// Times only. The spawn interval is the documented 210-minute cycle; the boss rotation is
// not published by Blizzard and changes between seasons (seasonal bosses join it), so this
// file deliberately makes no claim about which boss appears next.
//
// The anchor is a community-synced spawn (2026-10-30 00:00 UTC), not the current
// UTC day. A 210-minute cycle does not divide into 24 hours, so the times shift
// 30 minutes later each day; resetting at midnight would skip that shift.
(function () {
  "use strict";

  var CYCLE_MIN = 210;
  var ROWS = 12;
  var ANCHOR = Date.UTC(2026, 9, 30, 0, 0, 0);
  var STORAGE_KEY = "raigulus-d4-wb-alert";

  function upcomingSpawns(count) {
    var cycleMs = CYCLE_MIN * 60 * 1000;
    var now = Date.now();
    var index = Math.floor((now - ANCHOR) / cycleMs);
    var first = ANCHOR + index * cycleMs;
    // Keep the active spawn as the first row during its 15-minute kill window.
    if (now - first >= 15 * 60 * 1000) first += cycleMs;
    var out = [];
    for (var i = 0; i < count; i++) out.push(new Date(first + i * cycleMs));
    return out;
  }

  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }

  function utcTime(date) {
    return pad(date.getUTCHours()) + ":" + pad(date.getUTCMinutes());
  }

  function localTime(date) {
    return pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function dayLabel(date) {
    var today = new Date();
    var startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
    var dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    var days = Math.round((dayStart - startOfToday) / 86400000);
    if (days === 0) return "Today";
    if (days === 1) return "Tomorrow";
    return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  }

  function relative(ms) {
    if (ms <= 0) return "now";
    var minutes = Math.round(ms / 60000);
    var h = Math.floor(minutes / 60);
    var m = minutes % 60;
    if (h === 0) return "in " + m + " min";
    if (m === 0) return "in " + h + " h";
    return "in " + h + " h " + m + " min";
  }

  // --- schedule table -------------------------------------------------------
  function buildTable() {
    var body = document.querySelector("[data-wb-spawns]");
    if (!body) return [];

    var spawns = upcomingSpawns(ROWS);
    body.textContent = "";
    var cells = [];

    for (var i = 0; i < spawns.length; i++) {
      var date = spawns[i];
      var tr = document.createElement("tr");
      if (i === 0) tr.className = "is-next";

      var day = document.createElement("th");
      day.setAttribute("scope", "row");
      day.textContent = dayLabel(date);

      var utc = document.createElement("td");
      utc.textContent = utcTime(date) + " UTC";

      var local = document.createElement("td");
      local.textContent = localTime(date);

      var rel = document.createElement("td");
      rel.className = "meta";

      tr.appendChild(day);
      tr.appendChild(utc);
      tr.appendChild(local);
      tr.appendChild(rel);
      body.appendChild(tr);

      cells.push({ el: rel, at: date.getTime() });
    }
    return cells;
  }

  var countdownCells = [];

  function refreshCountdowns() {
    var now = Date.now();
    for (var i = 0; i < countdownCells.length; i++) {
      countdownCells[i].el.textContent = relative(countdownCells[i].at - now);
    }
  }

  // --- spawn alerts ---------------------------------------------------------
  var audio = null;

  function beep() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      audio = audio || new Ctx();
      if (audio.state === "suspended") audio.resume();
      for (var i = 0; i < 2; i++) {
        var osc = audio.createOscillator();
        var gain = audio.createGain();
        var start = audio.currentTime + i * 0.35;
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, start);
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.2, start + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.3);
        osc.connect(gain);
        gain.connect(audio.destination);
        osc.start(start);
        osc.stop(start + 0.32);
      }
    } catch (e) {
      // audio is a nicety; a blocked AudioContext must not break the page
    }
  }

  function readSetting() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return { minutes: 0, sound: true };
      var parsed = JSON.parse(raw);
      return { minutes: parseInt(parsed.minutes, 10) || 0, sound: parsed.sound !== false };
    } catch (e) {
      return { minutes: 0, sound: true };
    }
  }

  function writeSetting(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch (e) {
      // private mode: the alert still works for this page view
    }
  }

  var firedFor = {};

  function checkAlerts() {
    var setting = readSetting();
    if (!setting.minutes) return;
    var now = Date.now();
    var spawns = upcomingSpawns(2);
    for (var i = 0; i < spawns.length; i++) {
      var at = spawns[i].getTime();
      var delta = at - now;
      var key = String(at);
      if (delta <= 0 || delta > setting.minutes * 60000) continue;
      if (firedFor[key]) continue;
      firedFor[key] = true;

      var when = new Date(at).toLocaleString();
      if (setting.sound) beep();
      try {
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          new Notification("Diablo 4 World Boss in " + relative(delta), { body: "Spawns at " + when + ". Bosses appear on the map shortly before." });
        }
      } catch (e) {
        // some browsers throw on the constructor; the beep already fired
      }
    }
  }

  function setupAlerts() {
    var toggle = document.querySelector("[data-wb-alert-toggle]");
    var select = document.querySelector("[data-wb-alert-minutes]");
    var sound = document.querySelector("[data-wb-alert-sound]");
    if (!toggle || !select) return;

    var setting = readSetting();
    select.value = String(setting.minutes);
    if (sound) sound.checked = setting.sound;

    function syncButton() {
      var minutes = parseInt(select.value, 10) || 0;
      if (!minutes) {
        toggle.textContent = "Alerts off";
        toggle.setAttribute("aria-pressed", "false");
        return;
      }
      toggle.textContent = "Alerts on - " + minutes + " min before";
      toggle.setAttribute("aria-pressed", "true");
    }

    toggle.addEventListener("click", function () {
      var minutes = parseInt(select.value, 10) || 0;
      if (!minutes) {
        writeSetting({ minutes: 0, sound: sound ? sound.checked : true });
        syncButton();
        return;
      }
      var proceed = function () {
        writeSetting({ minutes: minutes, sound: sound ? sound.checked : true });
        beep();
        syncButton();
      };
      try {
        if (typeof Notification !== "undefined" && Notification.permission === "default") {
          Notification.requestPermission().then(proceed);
        } else {
          proceed();
        }
      } catch (e) {
        proceed();
      }
    });

    select.addEventListener("change", function () {
      var minutes = parseInt(select.value, 10) || 0;
      var wanted = sound ? sound.checked : true;
      writeSetting({ minutes: minutes, sound: wanted });
      if (minutes) beep();
      syncButton();
    });

    if (sound) {
      sound.addEventListener("change", function () {
        var minutes = parseInt(select.value, 10) || 0;
        writeSetting({ minutes: minutes, sound: sound.checked });
        if (sound.checked) beep();
      });
    }

    syncButton();
  }

  function start() {
    countdownCells = buildTable();
    refreshCountdowns();
    setupAlerts();
    checkAlerts();
    setInterval(function () {
      refreshCountdowns();
      checkAlerts();
    }, 30000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();