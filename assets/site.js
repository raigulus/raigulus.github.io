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

  // YouTube thumbnail fallback chain: maxres -> hq -> mq -> default.
  // Headless bots (PageSpeed included) sometimes get 403s from i.ytimg.com,
  // and old videos may lack maxres thumbs. Step down instead of showing broken art.
  var thumbOrder = ["maxresdefault", "hqdefault", "mqdefault", "default"];
  function thumbFallback(img) {
    if (img.getAttribute("data-thumb-fallback") === "done") return;
    var src = img.getAttribute("src") || "";
    for (var i = 0; i < thumbOrder.length - 1; i++) {
      if (src.indexOf("/" + thumbOrder[i] + ".") !== -1) {
        img.setAttribute("src", src.replace("/" + thumbOrder[i] + ".", "/" + thumbOrder[i + 1] + "."));
        if (i + 1 === thumbOrder.length - 1) img.setAttribute("data-thumb-fallback", "done");
        return;
      }
    }
    img.setAttribute("data-thumb-fallback", "done");
  }
  var thumbs = document.querySelectorAll('img[src*="i.ytimg.com/vi/"]');
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
