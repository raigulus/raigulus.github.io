// Site-wide: open outbound links in a new tab so visitors stay on the site.
// Same-origin links are untouched. Existing rel tokens (e.g. nofollow) are kept.
document.addEventListener("DOMContentLoaded", function () {
  var links = document.querySelectorAll('a[href^="http://"], a[href^="https://"]');
  for (var i = 0; i < links.length; i++) {
    var a = links[i];
    try {
      var url = new URL(a.getAttribute("href"), window.location.href);
      if (url.origin === window.location.origin) continue;
      a.setAttribute("target", "_blank");
      var rel = (a.getAttribute("rel") || "").split(/\s+/).filter(function (t) { return t.length > 0; });
      if (rel.indexOf("noopener") === -1) rel.push("noopener");
      a.setAttribute("rel", rel.join(" "));
    } catch (e) {}
  }

  // Discord widget facade: the widget pulls ~190 KiB of unoptimized avatars
  // from Discord's CDN. The iframe carries data-src only (never src), so the
  // browser preload scanner can't fetch it early - nothing downloads until click.
  var widgets = document.querySelectorAll('iframe[data-src*="discord.com/widget"]');
  for (var j = 0; j < widgets.length; j++) {
    (function (frame) {
      var src = frame.getAttribute("data-src");
      if (!src) return;
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "discord-facade-button";
      btn.textContent = "Load Discord widget";
      btn.setAttribute("aria-label", "Load the Raigulus Discord server widget");
      var w = frame.getAttribute("width") || "350";
      var h = frame.getAttribute("height") || "500";
      btn.style.maxWidth = w + "px";
      btn.style.minHeight = Math.min(parseInt(h, 10) || 500, 240) + "px";
      frame.style.display = "none";
      btn.addEventListener("click", function () {
        frame.setAttribute("src", src);
        frame.removeAttribute("data-src");
        frame.style.display = "";
        btn.remove();
      });
      frame.parentNode.insertBefore(btn, frame);
    })(widgets[j]);
  }

  // Giscus comments facade: the embed pulls ~38 KiB of JS from giscus.app plus a
  // loading GIF, none of it needed until a visitor asks for it. The eager script
  // tag also shifted the page after first paint - CLS 0.362 on the build maker,
  // which put that page at 76/100 on Lighthouse mobile. The button ships as
  // static markup so it renders without JS and stays keyboard reachable.
  var giscusCfg = {
    "data-repo": "raigulus/raigulus.github.io",
    "data-repo-id": "R_kgDOS0xxMw",
    "data-category": "General",
    "data-category-id": "DIC_kwDOS0xxM84DGN2n",
    "data-mapping": "pathname",
    "data-strict": "0",
    "data-reactions-enabled": "1",
    "data-emit-metadata": "0",
    "data-input-position": "bottom",
    "data-theme": "dark",
    "data-lang": "en",
    "data-loading": "lazy"
  };
  var giscusBtns = document.querySelectorAll("button[data-giscus-facade]");
  for (var g = 0; g < giscusBtns.length; g++) {
    (function (btn) {
      btn.addEventListener("click", function () {
        var el = document.createElement("script");
        el.src = "https://giscus.app/client.js";
        el.async = true;
        el.crossOrigin = "anonymous";
        for (var key in giscusCfg) {
          if (Object.prototype.hasOwnProperty.call(giscusCfg, key)) {
            el.setAttribute(key, giscusCfg[key]);
          }
        }
        btn.parentNode.replaceChild(el, btn);
      });
    })(giscusBtns[g]);
  }

  // YouTube thumbnail fallback chain: maxres -> hq -> mq -> default.
  // Thumbnails are served from our own origin, so a missing local copy steps down
  // to a smaller size rather than showing broken art. A video added after the last
  // thumbnail sync falls through the whole chain and finally points at the remote
  // copy, so a fresh page is never blank.
  var thumbOrder = ["maxresdefault", "hqdefault", "mqdefault", "default"];
  var thumbRoot = "/assets/img/yt/";
  var thumbRemote = "https://i.ytimg.com/vi/";
  function thumbLocalName(src) {
    if (src.indexOf(thumbRoot) !== 0) return null;
    var rest = src.slice(thumbRoot.length);
    var dash = rest.lastIndexOf("-");
    var dot = rest.lastIndexOf(".");
    if (dash === -1 || dot === -1 || dot < dash) return null;
    return { id: rest.slice(0, dash), size: rest.slice(dash + 1, dot) };
  }
  function thumbFallback(img) {
    if (img.getAttribute("data-thumb-fallback") === "done") return;
    var parsed = thumbLocalName(img.getAttribute("src") || "");
    if (!parsed) return;
    var index = thumbOrder.indexOf(parsed.size);
    if (index !== -1 && index < thumbOrder.length - 1) {
      img.setAttribute("src", thumbRoot + parsed.id + "-" + thumbOrder[index + 1] + ".jpg");
      return;
    }
    img.setAttribute("src", thumbRemote + parsed.id + "/" + parsed.size + ".jpg");
    img.setAttribute("data-thumb-fallback", "done");
  }
  var thumbs = document.querySelectorAll('img[src*="/assets/img/yt/"]');
  for (var k = 0; k < thumbs.length; k++) {
    (function (img) {
      img.addEventListener("error", function () { thumbFallback(img); });
      if (img.complete && img.naturalWidth === 0 && img.getAttribute("src")) thumbFallback(img);
    })(thumbs[k]);
  }

  // The header nav scrolls horizontally but its scrollbar is hidden, so links past
// the viewport edge have no visible affordance. Resting the pointer near either end
// ramps a slow auto-scroll instead. Speed eases in across RAMP px so a passing
// cursor never jerks the nav, and it stops dead once the end is reached.
// MAX is px per SECOND and tick() scales by elapsed time: a px-per-frame step makes
// the motion frame-rate dependent and visibly ticks on fast displays.
  var navs = document.querySelectorAll(".site-header nav");
  for (var n = 0; n < navs.length; n++) {
    (function (nav) {
      if (nav.scrollWidth <= nav.clientWidth + 1) return;
var EDGE = 90;
      // RAMP is the ease-in distance: speed climbs from 0 at EDGE px away to MAX at the
      // edge itself. Setting RAMP = EDGE makes MAX a real, reachable top speed.
      var RAMP = 90;
      var MAX = 210;
      // The slide must survive the pointer leaving the EDGE band and run all the way to
      // the end, otherwise a hand tremor or a nudge toward a link kills it after ~12px.
      // On release the speed decays from hold to hold * FLOOR over GRACE ms, then holds
      // that floor until the end is reached, the pointer re-enters a band, or the
      // pointer leaves the nav. FLOOR is a ratio of the peak, not an absolute px/s, so
      // retuning MAX keeps the shape of the glide.
      var GRACE = 600;
      var FLOOR = 0.45;
      var dir = 0;
      var hold = 0;
      var coast = 0;
      var lastX = 0;
      var lastT = 0;
      var raf = null;

      function stop() { dir = 0; lastT = 0; hold = 0; coast = 0; }

      function tick(now) {
        raf = null;
        if (!dir) { lastT = 0; return; }
        var elapsed = lastT ? now - lastT : 16;
        var dt = Math.min(elapsed / 1000, 0.05);
        lastT = now;
        var r = nav.getBoundingClientRect();
        var span = nav.scrollWidth - nav.clientWidth;
        if ((dir > 0 && nav.scrollLeft >= span - 0.5) || (dir < 0 && nav.scrollLeft <= 0.5)) { stop(); return; }
        var fromEdge = dir > 0 ? r.right - lastX : lastX - r.left;
        var speed = MAX * Math.min(1, Math.max(0, (EDGE - fromEdge) / RAMP));
        // hold must be sampled before the decay branch. Testing it first aborts the very
        // first frame, because hold is still 0 when mousemove starts the slide and hold is
        // only ever raised here - the run dies before it can move a pixel.
        if (speed > hold) hold = speed;
        if (hold <= 1) { stop(); return; }
        if (speed <= 1) {
          // The decay budget has to accumulate across frames. elapsed is a single-frame
          // delta, so comparing GRACE against it directly never expires.
          coast += elapsed;
          speed = coast < GRACE ? hold * (1 - (1 - FLOOR) * coast / GRACE) : hold * FLOOR;
        } else {
          coast = 0;
        }
        nav.scrollLeft += dir * speed * dt;
raf = requestAnimationFrame(tick);
      }

      // next === 0 means the pointer left the EDGE band. Clearing dir there killed the
      // slide on the first pixel of tremor, so an in-progress run is left alive for
      // tick() to coast down; only a real reversal or a fresh engagement resets it.
      nav.addEventListener("mousemove", function (e) {
        lastX = e.clientX;
        var r = nav.getBoundingClientRect();
        var next = r.right - lastX < EDGE ? 1 : (lastX - r.left < EDGE ? -1 : 0);
        if (next) {
          if (next !== dir) {
            dir = next;
            lastT = 0;
            hold = 0;
          }
          if (!raf) raf = requestAnimationFrame(tick);
        } else if (!dir) {
          lastT = 0;
        }
      });

      nav.addEventListener("mouseleave", function () { dir = 0; lastT = 0; hold = 0; });
    })(navs[n]);
  }

  // Scroll hint: when the nav is horizontally scrollable, the edge that still has
  // content fades out. Not a fixed mask - it follows the scroll position
  // (end / start / both) and disappears entirely when there is nothing to scroll.
  // tick() writes scrollLeft programmatically; the `scroll` event fires for that
  // too, so no extra call is needed.
  function navHint(nav) {
    var max = nav.scrollWidth - nav.clientWidth;
    if (max <= 2) { nav.removeAttribute("data-hint"); return; }
    var atStart = nav.scrollLeft <= 2;
    var atEnd = nav.scrollLeft >= max - 2;
    nav.setAttribute("data-hint", atStart ? "end" : (atEnd ? "start" : "both"));
  }
  for (var h = 0; h < navs.length; h++) {
    (function (nav) {
      navHint(nav);
      nav.addEventListener("scroll", function () { navHint(nav); }, { passive: true });
    })(navs[h]);
  }
  window.addEventListener("resize", function () {
    for (var h = 0; h < navs.length; h++) navHint(navs[h]);
  });
});

// Site-wide search overlay. The index is ~1.6 MB, so it is fetched the first
// time the dialog is opened, never on page load - same approach the /search/
// page uses. "/" and Ctrl/Cmd+K open it, Escape closes and returns focus to
// the trigger so keyboard users keep their place.
(function () {
  var dialog = document.getElementById("site-search-overlay");
  if (!dialog) return;
  var openBtn = document.querySelector("[data-search-open]");
  var input = dialog.querySelector("#site-search-overlay-input");
  var results = dialog.querySelector("#site-search-overlay-results");
  var status = dialog.querySelector("#site-search-overlay-status");
  var closeBtn = dialog.querySelector("[data-search-close]");
  var indexRequest = null;
  var pages = null;
  var lastFocus = null;

  // Order matters in close(): inert must be dropped before focus is restored,
  // because the trigger button lives inside .site-header and cannot be focused
  // while that ancestor is inert.
  var background = Array.prototype.filter.call(
    document.querySelectorAll(".site-header, main, .site-footer"),
    function (el) { return el && !dialog.contains(el); }
  );

  if (status) {
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
  }
  if (openBtn) {
    openBtn.setAttribute("aria-expanded", "false");
    openBtn.setAttribute("aria-controls", dialog.id);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function sectionName(s) {
    var map = {
      "division-2": "Division 2", "destiny-2": "Destiny 2", "diablo-4": "Diablo 4",
      guides: "Guides", lore: "Lore", home: "Raigulus"
    };
    if (map[s]) return map[s];
    return String(s || "").replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }
  function ensureIndex() {
    if (pages) return Promise.resolve(pages);
    if (indexRequest) return indexRequest;
    status.textContent = "Loading the index...";
    indexRequest = fetch("/assets/data/search-index.json", { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("index missing");
        return r.json();
      })
      .then(function (data) {
        pages = data.pages || [];
        indexRequest = null;
        return pages;
      })
      .catch(function () {
        indexRequest = null;
        status.textContent = "Search index failed to load.";
        return [];
      });
    return indexRequest;
  }
  function scorePage(p, terms) {
    var title = (p.t || "").toLowerCase();
    var rest = ((p.d || "") + " " + (p.b || "") + " " + (p.u || "") + " " + (p.s || "")).toLowerCase();
    var sc = 0;
    for (var i = 0; i < terms.length; i++) {
      var inTitle = title.indexOf(terms[i]) !== -1;
      if (!inTitle && rest.indexOf(terms[i]) === -1) return -1;
      sc += inTitle ? 2 : 1;
    }
    return sc;
  }
  function render() {
    var q = input.value.trim();
    if (!pages) { results.innerHTML = ""; return; }
    var terms = q.toLowerCase().split(/\s+/).filter(function (t) { return t.length > 0; });
    if (!terms.length) {
      results.innerHTML = "";
      status.textContent = "Type to search " + pages.length + " pages.";
      return;
    }
    var hits = [];
    for (var i = 0; i < pages.length; i++) {
      var sc = scorePage(pages[i], terms);
      if (sc >= 0) hits.push({ p: pages[i], sc: sc });
    }
    hits.sort(function (a, b) { return b.sc - a.sc; });
    hits = hits.slice(0, 8);
    status.textContent = hits.length + (hits.length === 1 ? " result" : " results") + ' for "' + q + '"';
    results.innerHTML = hits.map(function (h) {
      return '<a class="site-search-hit" href="' + esc(h.p.u) + '">' +
        '<span class="site-search-hit-eyebrow">' + esc(sectionName(h.p.s)) + "</span>" +
        "<strong>" + esc(h.p.t) + "</strong></a>";
    }).join("") || '<p class="site-search-empty">No matches. Try fewer words.</p>';
  }
  function open() {
    lastFocus = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("has-search-open");
    background.forEach(function (el) { el.setAttribute("inert", ""); });
    if (openBtn) openBtn.setAttribute("aria-expanded", "true");
    input.value = "";
    results.innerHTML = "";
    ensureIndex().then(function () { render(); });
    input.focus();
  }
  function close() {
    dialog.hidden = true;
    document.body.classList.remove("has-search-open");
    background.forEach(function (el) { el.removeAttribute("inert"); });
    if (openBtn) openBtn.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  // aria-modal: Tab must stay inside. Hit links render after the index resolves, so never cache this list.
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';
  function focusableItems() {
    return Array.prototype.filter.call(dialog.querySelectorAll(FOCUSABLE), function (el) {
      return el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement;
    });
  }
  function trapTab(e) {
    var items = focusableItems();
    if (items.length === 0) { e.preventDefault(); return; }
    var first = items[0];
    var last = items[items.length - 1];
    var active = document.activeElement;
    if (e.shiftKey) {
      if (active === first || !dialog.contains(active)) {
        e.preventDefault();
        last.focus();
      }
    } else if (active === last || !dialog.contains(active)) {
      e.preventDefault();
      first.focus();
    }
  }
  if (openBtn) openBtn.addEventListener("click", open);
  if (closeBtn) closeBtn.addEventListener("click", close);
  dialog.addEventListener("click", function (e) {
    if (e.target === dialog || e.target.closest("[data-search-close]")) close();
  });
  input.addEventListener("input", function () {
    // ensureIndex() resolves with the page list, so render() always runs after
    // the index is in memory. Chaining off the old return value raced: a second
    // keystroke saw the in-flight request and rendered against null pages.
    ensureIndex().then(function () { render(); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !dialog.hidden) { close(); return; }
    if (!dialog.hidden && e.key === "Tab") { trapTab(e); return; }
    if (dialog.hidden && (e.key === "/" || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k"))) {
      var t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      e.preventDefault();
      open();
    }
  });
})();
