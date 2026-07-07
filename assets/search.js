document.addEventListener("DOMContentLoaded", function () {
  var blocks = document.querySelectorAll("[data-guide-search]");
  if (!blocks.length) return;
  var params = new URLSearchParams(window.location.search);
  var initial = params.get("tag") || params.get("q") || "";
  blocks.forEach(function (block) {
    var input = block.querySelector("[data-guide-search-input]");
    var count = block.querySelector("[data-guide-search-count]");
    var cards = Array.prototype.slice.call(document.querySelectorAll("[data-search-card]"));
    if (!input || !cards.length) return;
    if (initial) input.value = initial;
    function applyFilter() {
      var query = input.value.trim().toLowerCase();
      var visible = 0;
      cards.forEach(function (card) {
        var haystack = (card.getAttribute("data-search") || "").toLowerCase();
        var match = !query || haystack.indexOf(query) !== -1;
        card.hidden = !match;
        if (match) visible += 1;
      });
      if (count) count.textContent = visible + " guide" + (visible === 1 ? "" : "s");
    }
    input.addEventListener("input", applyFilter);
    applyFilter();
  });
});
