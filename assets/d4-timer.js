// Diablo 4 event timers - shared by /diablo-4/event-timer/ and /diablo-4/world-boss-timer/
//
// Schedules are deterministic: each event repeats on a fixed cycle counted from a
// shared epoch. All source-of-truth values are UTC; display converts from UTC.
//
// Anchor note: World Boss spawns on a 210-minute (3.5h) cycle. 210 does NOT divide a
// 24h day (24/3.5 = 6.857), so a FIXED epoch makes the cycle drift 3h per day and the
// "next spawn" wall-clock time would be wrong for every day except the epoch's own.
// The anchor is therefore the CURRENT UTC day's 00:00, recomputed on every tick, which
// keeps spawns on the :00/:30 UTC grid and stable across days.
//
// Verified against two independent live trackers (nexttier.pro and
// diablo4worldbosstimer.live), which report the same grid: 07:00, 10:30, 14:00, 17:30.
//
// Per-page configuration is declared on the page, not here:
//   <div class="video-card" data-timer="world-boss"
//        data-cycle="210" data-duration="15" data-active-label="SPAWNED"
//        data-warn-label="Kill within" data-idle-label="Spawns in"
//        data-warn-before="30">
//     <h2 data-timer-field="status">Loading...</h2>
//     <div data-timer-field="countdown">--:--:--</div>
//     <p data-timer-field="info">Loading...</p>
//     <p class="meta"><span data-timer-field="next">Next: Loading...</span></p>
//   </div>
(function () {
  "use strict";

  // Anchor for the current UTC day, recomputed on every tick so the cycle stays on the
  // :00/:30 grid instead of drifting 3h per day (see note above).
  function currentDayEpoch() {
    var now = new Date();
    return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0);
  }

  function formatDuration(ms) {
    if (ms <= 0) return "0:00:00";
    var total = Math.floor(ms / 1000);
    var hours = Math.floor(total / 3600);
    var minutes = Math.floor((total % 3600) / 60);
    var seconds = total % 60;
    return (
      hours +
      ":" +
      (minutes < 10 ? "0" : "") +
      minutes +
      ":" +
      (seconds < 10 ? "0" : "") +
      seconds
    );
  }

  function getEventState(cfg) {
    var cycleMs = cfg.cycle * 60 * 1000;
    var durationMs = cfg.duration * 60 * 1000;
    var now = Date.now();
    var epoch = currentDayEpoch();
    var cyclePosition = ((now - epoch) % cycleMs + cycleMs) % cycleMs;
    var nextStartMs = now + (cycleMs - cyclePosition);
    return {
      isActive: cyclePosition < durationMs,
      timeUntilStart: cycleMs - cyclePosition,
      timeUntilEnd: durationMs - cyclePosition,
      nextStartUtc: new Date(nextStartMs)
    };
  }

  function formatUtcTime(date) {
    return date.toISOString().slice(11, 16);
  }

  function setField(card, field, value) {
    var el = card.querySelector('[data-timer-field="' + field + '"]');
    if (el) el.textContent = value;
  }

  function renderCard(card) {
    var cfg = {
      cycle: parseFloat(card.getAttribute("data-cycle")),
      duration: parseFloat(card.getAttribute("data-duration")),
      activeLabel: card.getAttribute("data-active-label") || "ACTIVE NOW",
      warnLabel: card.getAttribute("data-warn-label") || "",
      idleLabel: card.getAttribute("data-idle-label") || "Starts in",
      infoIdle: card.getAttribute("data-info-idle") || "",
      warnBefore: parseFloat(card.getAttribute("data-warn-before") || "0")
    };
    if (!cfg.cycle || !cfg.duration) return;

    var state = getEventState(cfg);

    if (state.isActive) {
      setField(card, "status", cfg.activeLabel);
      setField(card, "countdown", formatDuration(state.timeUntilEnd));
      setField(card, "info", (cfg.warnLabel || "Ends in") + " " + formatDuration(state.timeUntilEnd));
    } else {
      // Inside the pre-spawn warning window, lead with the warning instead of the
      // raw countdown - that is the moment a player actually needs to act.
      if (cfg.warnBefore > 0 && state.timeUntilStart <= cfg.warnBefore * 60 * 1000) {
        setField(card, "status", "SPAWNING SOON");
        setField(card, "info", "Expected in " + formatDuration(state.timeUntilStart));
      } else {
        setField(card, "status", "Inactive");
        setField(card, "info", cfg.infoIdle);
      }
      setField(card, "countdown", formatDuration(state.timeUntilStart));
    }
    setField(card, "next", "Next: " + formatUtcTime(state.nextStartUtc) + " UTC");
  }

  function update() {
    var cards = document.querySelectorAll("[data-timer]");
    for (var i = 0; i < cards.length; i++) renderCard(cards[i]);
  }

  function start() {
    update();
    setInterval(update, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();