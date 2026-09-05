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
});
