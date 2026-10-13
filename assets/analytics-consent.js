(function () {
  "use strict";

  var STORAGE_KEY = "raigulus-analytics-consent";
  var LOG_KEY = "raigulus-consent-log";
  var GA_ID = "G-C8XHNXWMVQ";
  var CLARITY_ID = "x5tl7t5cqi";
  // Session recordings are only collected on the pages that actually contain a
  // custom interface a visitor can struggle with. Guide pages are rendered text,
  // so recording pointer movement there produces data with nothing to act on.
  var CLARITY_PATHS = [
    "/division-2/agent-briefing/",
    "/division-2/build-maker/",
    "/diablo-4/event-timer/",
    "/diablo-4/world-boss-timer/"
  ];
  var POLICY_VERSION = "2026-10-13";
  var loaded = false;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag("js", new Date());
  window.gtag("consent", "default", { analytics_storage: "denied" });

  function readChoice() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  }

  function saveChoice(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (error) {
      // Storage can be unavailable in private modes; the choice still applies to
      // this page view, it just is not remembered.
    }
  }

  function record(choice) {
    // Proof of consent: the choice, when it was made, and which policy version
    // was on screen. Without this record the consent cannot be demonstrated.
    try {
      var log = JSON.parse(window.localStorage.getItem(LOG_KEY) || "[]");
      if (!Array.isArray(log)) log = [];
      log.push({ choice: choice, policy: POLICY_VERSION, at: new Date().toISOString() });
      window.localStorage.setItem(LOG_KEY, JSON.stringify(log.slice(-20)));
    } catch (error) {
      // A full or blocked store must not break the page.
    }
  }

  function globalPrivacyControl() {
    // Browsers with the Global Privacy Control enabled expose this. The signal is
    // a recognised opt-out request, so it is honoured as a refusal without asking.
    return navigator.globalPrivacyControl === true;
  }

  function appendScript(src) {
    var script = document.createElement("script");
    script.src = src;
    script.async = true;
    document.head.appendChild(script);
  }

  function clarityAllowed() {
    var path = window.location.pathname;
    return CLARITY_PATHS.some(function (prefix) { return path.indexOf(prefix) === 0; });
  }

  function applyChoice(choice) {
    if (choice !== "granted") {
      if (loaded) {
        window.gtag("consent", "update", { analytics_storage: "denied" });
        // Clarity keeps writing cookies after its script is appended, so a
        // withdrawal has to be reported to it explicitly rather than only
        // stopping future loads.
        if (typeof window.clarity === "function") window.clarity("consent", false);
        loaded = false;
      }
      document.documentElement.setAttribute("data-analytics", "denied");
      return;
    }
    if (loaded) return;
    loaded = true;
    window.gtag("consent", "update", { analytics_storage: "granted" });
    // No advertising on this site, so Analytics is told not to use the data for
    // ads personalisation or demographics. This also suppresses Google's own
    // signal enrichment, which is collected by default unless opted out.
    window.gtag("config", GA_ID, { allow_google_signals: false });
    appendScript("https://www.googletagmanager.com/gtag/js?id=" + GA_ID);
    if (clarityAllowed()) {
      (function (c, l, a, r, i, t, y) {
        c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
        t = l.createElement(r);
        t.async = 1;
        t.src = "https://www.clarity.ms/tag/" + i;
        y = l.getElementsByTagName(r)[0];
        y.parentNode.insertBefore(t, y);
      })(window, document, "clarity", "script", CLARITY_ID);
      if (typeof window.clarity === "function") window.clarity("consent", true);
    }
    document.documentElement.setAttribute("data-analytics", "granted");
  }

  function button(label, primary) {
    var el = document.createElement("button");
    el.type = "button";
    el.className = primary ? "rg-consent-btn rg-consent-btn-primary" : "rg-consent-btn";
    el.textContent = label;
    return el;
  }

  function openDialog() {
    var previous = document.querySelector(".rg-consent");
    if (previous) previous.remove();

    var bar = document.createElement("div");
    bar.className = "rg-consent";
    bar.setAttribute("role", "dialog");
    bar.setAttribute("aria-label", "Analytics consent");

    var text = document.createElement("p");
    text.className = "rg-consent-text";
    text.textContent = globalPrivacyControl()
      ? "Your browser sent a Global Privacy Control signal. That is treated as a refusal, so " +
        "no analytics are loaded."
      : "Raigulus uses Google Analytics and Microsoft Clarity to count visits and to see " +
        "which pages are read. Nothing reaches either service unless you accept. Video " +
        "thumbnails, comment threads and the feedback form work either way. You can change " +
        "this choice at any time from Cookie settings in the footer.";
    bar.appendChild(text);

    var actions = document.createElement("div");
    actions.className = "rg-consent-actions";

    var decline = button("Decline", false);
    decline.addEventListener("click", function () {
      saveChoice("denied");
      record("denied");
      bar.remove();
      applyChoice("denied");
    });

    var accept = button("Accept", true);
    accept.addEventListener("click", function () {
      saveChoice("granted");
      record("granted");
      bar.remove();
      applyChoice("granted");
    });

    actions.appendChild(decline);
    actions.appendChild(accept);
    bar.appendChild(actions);
    document.body.appendChild(bar);
    document.documentElement.setAttribute("data-consent-dialog", "open");
    accept.focus();
  }

  function init() {
    if (globalPrivacyControl()) {
      record("denied-gpc");
      applyChoice("denied");
      return;
    }
    var choice = readChoice();
    if (choice === "granted" || choice === "denied") {
      applyChoice(choice);
      return;
    }
    openDialog();
  }

  // Reachable from the footer link so withdrawal is as easy as granting.
  window.raigulusConsent = { open: openDialog, version: POLICY_VERSION };

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest ? event.target.closest("[data-consent-open]") : null;
    if (!trigger) return;
    event.preventDefault();
    openDialog();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();