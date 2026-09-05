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
});
