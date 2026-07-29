(function () {
  "use strict";

  const fields = [
    ["alignment", "Alignment"],
    ["faction", "Faction"],
    ["theatre", "Theatre"],
    ["content", "Content"],
    ["role", "Role"]
  ];
  const state = { data: null, target: null, dateKey: null, mode: "daily", guesses: [], solved: false, selected: null };
  const els = {};

  function byId(id) { return document.getElementById(id); }
  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, function (character) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;" })[character];
    });
  }
  function initials(name) {
    return name.split(/\s+/).filter(Boolean).slice(0, 2).map(function (part) { return part[0]; }).join("").toUpperCase();
  }
  function factionClass(target) {
    if (target.factionFamily === "Rogue network") return "faction-rogue";
    if (target.factionFamily === "Black Tusk") return "faction-black";
    return "faction-washington";
  }
  function utcDateKey() { return new Date().toISOString().slice(0, 10); }
  function humanDate(key) {
    const pieces = key.split("-").map(Number);
    return new Intl.DateTimeFormat("en", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(pieces[0], pieces[1] - 1, pieces[2])));
  }
  function stableIndex(key, length) {
    let hash = 2166136261;
    for (let index = 0; index < key.length; index += 1) {
      hash ^= key.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) % length;
  }
  function storageKey() { return "raigulus-agent-briefing-v" + state.data.version + "-" + state.dateKey; }
  function solvedDaysKey() { return "raigulus-agent-briefing-solved-v" + state.data.version; }
  function getTargetById(id) { return state.data.targets.find(function (target) { return target.id === id; }); }
  function readDailyProgress() {
    try {
      const progress = JSON.parse(localStorage.getItem(storageKey()) || "{}");
      state.guesses = Array.isArray(progress.guesses) ? progress.guesses.map(getTargetById).filter(Boolean) : [];
      state.solved = Boolean(progress.solved) || state.guesses.some(function (target) { return target.id === state.target.id; });
    } catch (error) {
      state.guesses = [];
      state.solved = false;
    }
  }
  function saveDailyProgress() {
    if (state.mode !== "daily") return;
    try {
      localStorage.setItem(storageKey(), JSON.stringify({ guesses: state.guesses.map(function (target) { return target.id; }), solved: state.solved }));
    } catch (error) {
      // The game remains usable when storage is unavailable.
    }
  }
  function recordDailySolve() {
    if (state.mode !== "daily") return;
    try {
      const days = new Set(JSON.parse(localStorage.getItem(solvedDaysKey()) || "[]"));
      days.add(state.dateKey);
      localStorage.setItem(solvedDaysKey(), JSON.stringify(Array.from(days).sort().slice(-730)));
    } catch (error) {
      // A streak is an optional local convenience, not a game requirement.
    }
  }
  function currentStreak() {
    if (state.mode !== "daily") return null;
    try {
      const days = new Set(JSON.parse(localStorage.getItem(solvedDaysKey()) || "[]"));
      let cursor = new Date(state.dateKey + "T00:00:00Z");
      let streak = 0;
      while (days.has(cursor.toISOString().slice(0, 10))) {
        streak += 1;
        cursor.setUTCDate(cursor.getUTCDate() - 1);
      }
      return streak;
    } catch (error) {
      return 0;
    }
  }
  function setStatus(message, value) {
    els.status.innerHTML = escapeHtml(message) + "<strong>" + escapeHtml(value) + "</strong>";
  }
  function setFormEnabled() {
    const inactive = state.solved;
    els.input.disabled = inactive;
    els.submit.disabled = inactive || !state.selected;
    if (inactive) {
      els.input.value = "Dossier complete";
      hideSuggestions();
    }
  }
  function compareField(guess, target, field) {
    if (guess[field] === target[field]) return "match";
    const groupKey = field + "Family";
    if (target[groupKey] && guess[groupKey] === target[groupKey]) return "near";
    if (field === "theatre" && guess.theatreRegion === target.theatreRegion) return "near";
    return "miss";
  }
  function yearCell(guess, target) {
    if (guess.firstSeen === target.firstSeen) return '<td class="match year-cell">' + guess.firstSeen + "</td>";
    const arrow = target.firstSeen > guess.firstSeen ? "↑" : "↓";
    const label = target.firstSeen > guess.firstSeen ? "Target first appeared later" : "Target first appeared earlier";
    return '<td class="miss year-cell">' + guess.firstSeen + '<span class="briefing-year-arrow" aria-label="' + label + '">' + arrow + "</span></td>";
  }
  function rowMarkup(guess) {
    const target = state.target;
    const targetState = guess.id === target.id ? "match" : "miss";
    const valueCells = fields.map(function (entry) {
      const field = entry[0];
      return '<td class="' + compareField(guess, target, field) + '">' + escapeHtml(guess[field]) + "</td>";
    }).join("");
    return "<tr>" +
      '<td class="target-cell ' + targetState + '"><div class="briefing-target"><span class="briefing-mini-dossier ' + factionClass(guess) + '">' + initials(guess.name) + '</span><span class="briefing-target-text"><span class="briefing-target-name">' + escapeHtml(guess.name) + '</span><span class="briefing-target-sub">' + escapeHtml(guess.faction) + "</span></span></div></td>" +
      valueCells + yearCell(guess, target) +
      "</tr>";
  }
  function renderRows() {
    els.rows.innerHTML = state.guesses.map(rowMarkup).join("");
    els.empty.classList.toggle("is-hidden", state.guesses.length > 0);
  }
  function renderResult() {
    if (!state.solved) {
      els.result.hidden = true;
      return;
    }
    const attempts = state.guesses.length;
    const streak = currentStreak();
    els.result.hidden = false;
    els.resultAvatar.className = "briefing-avatar " + factionClass(state.target);
    els.resultAvatar.textContent = initials(state.target.name);
    els.resultHeading.textContent = state.mode === "practice" ? "Practice dossier complete" : "Dossier complete: " + state.target.name;
    const streakText = state.mode === "daily" && streak ? " Current streak: " + streak + "." : "";
    els.resultCopy.textContent = state.target.brief + " Solved in " + attempts + " " + (attempts === 1 ? "attempt" : "attempts") + "." + streakText;
    els.watch.href = state.target.watchUrl || "https://www.youtube.com/@raigulus";
  }
  function render() {
    renderRows();
    renderResult();
    setStatus(state.solved ? "Dossier status" : "Attempts", state.solved ? "Complete" : String(state.guesses.length));
    setFormEnabled();
  }
  function suggestionMarkup(target, active) {
    return '<button type="button" class="briefing-suggestion" role="option" aria-selected="' + Boolean(active) + '" data-target-id="' + escapeHtml(target.id) + '"><span class="briefing-mini-dossier ' + factionClass(target) + '">' + initials(target.name) + '</span><span>' + escapeHtml(target.name) + '</span><small>' + escapeHtml(target.faction) + "</small></button>";
  }
  function hideSuggestions() {
    els.suggestions.hidden = true;
    els.suggestions.innerHTML = "";
    els.input.setAttribute("aria-expanded", "false");
  }
  function showSuggestions(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized || state.solved) { hideSuggestions(); return; }
    const available = state.data.targets.filter(function (target) {
      const haystack = [target.name].concat(target.aliases || []).join(" ").toLowerCase();
      return haystack.includes(normalized) && !state.guesses.some(function (guess) { return guess.id === target.id; });
    }).slice(0, 7);
    if (!available.length) { hideSuggestions(); return; }
    if (!state.selected || !available.some(function (target) { return target.id === state.selected.id; })) state.selected = available[0];
    els.suggestions.innerHTML = available.map(function (target) { return suggestionMarkup(target, state.selected && target.id === state.selected.id); }).join("");
    els.suggestions.hidden = false;
    els.input.setAttribute("aria-expanded", "true");
  }
  function selectTarget(target, fillInput) {
    state.selected = target;
    if (fillInput) els.input.value = target.name;
    els.submit.disabled = state.solved;
    hideSuggestions();
  }
  function submitSelection() {
    const guess = state.selected;
    if (!guess || state.solved || state.guesses.some(function (item) { return item.id === guess.id; })) return;
    state.guesses.push(guess);
    state.selected = null;
    els.input.value = "";
    if (guess.id === state.target.id) {
      state.solved = true;
      recordDailySolve();
    }
    saveDailyProgress();
    render();
  }
  function shareResult() {
    const date = state.mode === "daily" ? state.dateKey : "practice";
    const squares = state.guesses.map(function (guess) { return guess.id === state.target.id ? "🟧" : "🟥"; }).join("");
    const text = "Agent Briefing " + date + "\n" + squares + "\n" + state.guesses.length + " attempts · " + (state.solved ? "dossier complete" : "dossier open") + "\nhttps://raigulus.github.io/division-2/agent-briefing/";
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        els.share.textContent = "Copied";
        window.setTimeout(function () { els.share.textContent = "Share result"; }, 1500);
      }).catch(function () { window.prompt("Copy your result", text); });
    } else {
      window.prompt("Copy your result", text);
    }
  }
  function openPractice() {
    const candidates = state.data.targets.filter(function (target) { return target.id !== state.target.id; });
    const random = candidates[Math.floor(Math.random() * candidates.length)];
    state.mode = "practice";
    state.target = random;
    state.guesses = [];
    state.solved = false;
    state.selected = null;
    els.date.textContent = "Practice dossier // no daily streak";
    els.date.removeAttribute("datetime");
    els.practice.textContent = "Return to daily dossier";
    render();
    els.input.focus();
  }
  function returnDaily() {
    state.mode = "daily";
    state.dateKey = utcDateKey();
    state.target = state.data.targets[stableIndex(state.dateKey, state.data.targets.length)];
    state.guesses = [];
    state.solved = false;
    state.selected = null;
    readDailyProgress();
    els.date.textContent = "Dossier " + humanDate(state.dateKey) + " // resets 00:00 UTC";
    els.date.dateTime = state.dateKey;
    els.practice.textContent = "Open practice dossier";
    render();
    els.input.focus();
  }
  function bindEvents() {
    els.form.addEventListener("submit", function (event) { event.preventDefault(); submitSelection(); });
    els.input.addEventListener("input", function () { state.selected = null; els.submit.disabled = true; showSuggestions(els.input.value); });
    els.input.addEventListener("keydown", function (event) {
      const buttons = Array.from(els.suggestions.querySelectorAll("[data-target-id]"));
      if (!buttons.length) return;
      const current = state.selected ? buttons.findIndex(function (button) { return button.dataset.targetId === state.selected.id; }) : 0;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const next = event.key === "ArrowDown" ? (current + 1) % buttons.length : (current - 1 + buttons.length) % buttons.length;
        state.selected = getTargetById(buttons[next].dataset.targetId);
        showSuggestions(els.input.value);
      } else if (event.key === "Enter" && state.selected) {
        event.preventDefault();
        submitSelection();
      } else if (event.key === "Escape") {
        hideSuggestions();
      }
    });
    els.suggestions.addEventListener("click", function (event) {
      const button = event.target.closest("[data-target-id]");
      if (!button) return;
      selectTarget(getTargetById(button.dataset.targetId), true);
      submitSelection();
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".briefing-search-wrap")) hideSuggestions();
    });
    els.share.addEventListener("click", shareResult);
    els.practice.addEventListener("click", function () { state.mode === "daily" ? openPractice() : returnDaily(); });
  }
  function initializeElements() {
    Object.assign(els, {
      date: byId("briefing-date"), status: byId("briefing-status"), form: byId("briefing-form"), input: byId("briefing-input"), submit: byId("briefing-submit"), suggestions: byId("briefing-suggestions"), rows: byId("briefing-rows"), empty: byId("briefing-empty"), result: byId("briefing-result"), resultAvatar: byId("briefing-result-avatar"), resultHeading: byId("briefing-result-heading"), resultCopy: byId("briefing-result-copy"), watch: byId("briefing-watch"), share: byId("briefing-share"), practice: byId("briefing-practice")
    });
  }
  function start(data) {
    state.data = data;
    state.dateKey = utcDateKey();
    state.target = data.targets[stableIndex(state.dateKey, data.targets.length)];
    initializeElements();
    els.date.textContent = "Dossier " + humanDate(state.dateKey) + " // resets 00:00 UTC";
    els.date.dateTime = state.dateKey;
    readDailyProgress();
    bindEvents();
    render();
  }

  fetch("/assets/data/agent-intel.json", { cache: "no-cache" })
    .then(function (response) { if (!response.ok) throw new Error("The dossier index is unavailable."); return response.json(); })
    .then(function (data) { if (!data.targets || !data.targets.length) throw new Error("The dossier index is empty."); start(data); })
    .catch(function () {
      const status = byId("briefing-status");
      if (status) status.innerHTML = "Dossier status<strong>Unavailable</strong>";
      const empty = byId("briefing-empty");
      if (empty) empty.textContent = "The dossier index could not be loaded. Please refresh and try again.";
    });
}());
