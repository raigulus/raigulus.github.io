// Feedback form handler for guide pages.
// Extracted from inline script to support strict CSP (no unsafe-inline).
(function () {
  var box = document.querySelector("[data-feedback]");
  if (!box) return;
  function done(msg) {
    box.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
    var p = box.querySelector("p");
    if (p) p.innerHTML = "<strong>" + msg + "</strong>";
  }
  function send(v) {
    try {
      if (typeof gtag === "function") gtag("event", "guide_feedback", { feedback: v, page_path: window.location.pathname });
    } catch (e) {}
    done("Thanks for the feedback!");
  }
  var y = box.querySelector("[data-feedback-yes]");
  var n = box.querySelector("[data-feedback-no]");
  if (y) y.addEventListener("click", function () { send("yes"); });
  if (n) n.addEventListener("click", function () { send("no"); });
})();
