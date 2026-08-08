(function () {
  var refreshMs = 5 * 60 * 1000;

  function refreshOpenLootHubs() {
    var blocks = Array.prototype.slice.call(document.querySelectorAll("[data-live-loot-hub]"));
    if (!blocks.length) return;

    var version = Math.floor(Date.now() / refreshMs);
    fetch("/assets/data/escalation-target-loot.json?v=" + version, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("Loot snapshot request failed");
        return response.json();
      })
      .then(function (data) {
        var checked = String(data.last_checked || data.last_updated || "");
        if (!checked) return;
        var needsRefresh = blocks.some(function (block) {
          return block.getAttribute("data-live-loot-checked") !== checked;
        });
        if (!needsRefresh) return;

        var retryKey = "raigulus-live-loot-reload-" + version;
        if (window.sessionStorage.getItem(retryKey)) return;
        window.sessionStorage.setItem(retryKey, "1");

        var url = new URL(window.location.href);
        url.searchParams.set("live", String(version));
        window.location.replace(url.toString());
      })
      .catch(function () {
        // Keep the server-rendered snapshot visible when the refresh check fails.
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    refreshOpenLootHubs();
    window.setInterval(refreshOpenLootHubs, refreshMs);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) refreshOpenLootHubs();
    });
  });
})();
