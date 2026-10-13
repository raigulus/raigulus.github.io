(function () {
  "use strict";

  var STORAGE_KEY = "raigulus-analytics-consent";
  var GA_ID = "G-C8XHNXWMVQ";
  var CLARITY_ID = "x5tl7t5cqi";
  var loaded = false;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag("js", new Date());

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

  function appendScript(src, attrs) {
    var script = document.createElement("script");
    script.src = src;
    script.async = true;
    if (attrs) {
      Object.keys(attrs).forEach(function (name) { script.setAttribute(name, attrs[name]); });
    }
    document.head.appendChild(script);
  }

  function loadAnalytics() {
    if (loaded) return;
    loaded = true;
    window.gtag("config", GA_ID);
    appendScript("https://www.googletagmanager.com/gtag/js?id=" + GA_ID);
    appendScript("https://www.clarity.ms/tag/" + CLARITY_ID);
    document.documentElement.setAttribute("data-analytics", "loaded");
  }

  function button(label, primary) {
    var el = document.createElement("button");
    el.type = "button";
    el.className = primary ? "rg-consent-btn rg-consent-btn-primary" : "rg-consent-btn";
    el.textContent = label;
    return el;
  }

  function showBanner() {
    var bar = document.createElement("div");
    bar.className = "rg-consent";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "Analytics consent");

    var text = document.createElement("p");
    text.className = "rg-consent-text";
    text.textContent =
      "Raigulus uses Google Analytics and Microsoft Clarity to count visits and see how " +
      "pages are used. Nothing is loaded from either service unless you accept. " +
      "Declining keeps every feature of the site working.";
    bar.appendChild(text);

    var actions = document.createElement("div");
    actions.className = "rg-consent-actions";

    var decline = button("Decline", false);
    decline.addEventListener("click", function () {
      saveChoice("denied");
      bar.remove();
      document.documentElement.setAttribute("data-analytics", "denied");
    });

    var accept = button("Accept", true);
    accept.addEventListener("click", function () {
      saveChoice("granted");
      bar.remove();
      loadAnalytics();
    });

    actions.appendChild(decline);
    actions.appendChild(accept);
    bar.appendChild(actions);
    document.body.appendChild(bar);
    document.documentElement.setAttribute("data-analytics", "pending");
  }

  function init() {
    var choice = readChoice();
    if (choice === "granted") {
      loadAnalytics();
      return;
    }
    if (choice === "denied") {
      document.documentElement.setAttribute("data-analytics", "denied");
      return;
    }
    showBanner();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();