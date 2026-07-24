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

// Raigulus global archive shell. Appended to assets/search.js so every existing
// page receives the same navigation without changing its content or URLs.
document.addEventListener("DOMContentLoaded", function () {
  var header = document.querySelector(".site-header");
  if (!header || header.getAttribute("data-shell-ready") === "true") return;

  var menus = {
    games: {
      eyebrow: "Active archive",
      title: "The Division 2",
      description: "One connected field archive for routes, builds, loot, PvP, and story records.",
      links: [
        ["Division 2 hub", "Start here", "/division-2/"],
        ["Missions", "Walkthrough index", "/division-2/missions/"],
        ["Dark Zone", "PvP field notes", "/division-2/dark-zone-surge/"],
        ["Assassin's Creed", "Archive foundation / later", "", "future"]
      ]
    },
    guides: {
      eyebrow: "Browse by objective",
      title: "Field guides",
      description: "Move directly to the type of answer you need without breaking the archive structure.",
      links: [
        ["Legendary", "Clean mission runs", "/division-2/legendary/"],
        ["Builds", "Tested loadouts", "/division-2/builds/"],
        ["Loot", "Farming intel", "/division-2/loot/"],
        ["Bosses", "Encounters & secrets", "/division-2/bosses/"]
      ]
    },
    archive: {
      eyebrow: "Complete records",
      title: "Archive index",
      description: "The longer routes: manhunts, escalation runs, PvP records, and story material.",
      links: [
        ["Manhunts", "Season records", "/division-2/manhunts/"],
        ["Escalation", "Tier runs", "/division-2/escalation/"],
        ["PvP", "Conflict archive", "/division-2/pvp/"],
        ["Lore", "Story records", "/lore/"]
      ]
    }
  };

  var brand = header.querySelector(".brand");
  var navigation = header.querySelector("nav");
  if (!brand || !navigation) return;

  header.setAttribute("data-shell-ready", "true");
  header.classList.add("shell-header");
  brand.setAttribute("aria-label", "Raigulus home");
  brand.innerHTML = '<span class="shell-brand-mark" aria-hidden="true">雷</span><span>RAIGULUS</span>';

  navigation.className = "shell-desktop-nav";
  navigation.setAttribute("aria-label", "Primary navigation");
  navigation.innerHTML = ["games", "guides", "archive"].map(function (name) {
    return '<button type="button" class="shell-nav-trigger" data-shell-menu="' + name + '" aria-expanded="false" aria-controls="shell-mega-menu">' + name + '<span aria-hidden="true">⌄</span></button>';
  }).join("") + '<a href="/about/">About</a>';

  var youtube = document.createElement("a");
  youtube.className = "shell-youtube";
  youtube.href = "https://www.youtube.com/@raigulus";
  youtube.innerHTML = 'YouTube <span aria-hidden="true">↗</span>';
  header.appendChild(youtube);

  var mobileToggle = document.createElement("button");
  mobileToggle.type = "button";
  mobileToggle.className = "shell-mobile-toggle";
  mobileToggle.setAttribute("aria-expanded", "false");
  mobileToggle.setAttribute("aria-controls", "shell-mobile-drawer");
  mobileToggle.setAttribute("aria-label", "Open navigation");
  mobileToggle.innerHTML = "<span></span><span></span>";
  header.appendChild(mobileToggle);

  var mega = document.createElement("div");
  mega.id = "shell-mega-menu";
  mega.className = "shell-mega";
  header.appendChild(mega);

  var drawer = document.createElement("div");
  drawer.id = "shell-mobile-drawer";
  drawer.className = "shell-mobile-drawer";
  drawer.innerHTML = '<p>Archive navigation</p>' + ["games", "guides", "archive"].map(function (name) {
    var group = menus[name];
    var links = group.links.map(function (link) {
      if (link[3] === "future") return '<span class="shell-mobile-future">' + link[0] + '<small>' + link[1] + '</small></span>';
      return '<a href="' + link[2] + '">' + link[0] + '<small>' + link[1] + '</small></a>';
    }).join("");
    return '<details><summary>' + name + '<span>+</span></summary>' + links + '</details>';
  }).join("") + '<a class="shell-mobile-youtube" href="https://www.youtube.com/@raigulus">YouTube @raigulus ↗</a>';
  header.appendChild(drawer);

  var activeMenu = null;
  var activeTrigger = null;

  function closeMega(restoreFocus) {
    mega.classList.remove("is-open");
    mega.innerHTML = "";
    if (activeTrigger) activeTrigger.setAttribute("aria-expanded", "false");
    if (restoreFocus && activeTrigger) activeTrigger.focus();
    activeMenu = null;
    activeTrigger = null;
  }

  function openMega(name, trigger) {
    var group = menus[name];
    if (!group) return;
    if (activeMenu === name) {
      closeMega(false);
      return;
    }
    if (activeTrigger) activeTrigger.setAttribute("aria-expanded", "false");
    activeMenu = name;
    activeTrigger = trigger;
    trigger.setAttribute("aria-expanded", "true");
    mega.innerHTML = '<div class="shell-mega-inner"><div class="shell-mega-intro"><span>' + group.eyebrow + '</span><h2>' + group.title + '</h2><p>' + group.description + '</p></div><div class="shell-mega-links">' + group.links.map(function (link, index) {
      var number = String(index + 1).padStart(2, "0");
      var body = '<b>' + number + '</b><span><strong>' + link[0] + '</strong><small>' + link[1] + '</small></span><i aria-hidden="true">' + (link[3] === "future" ? "—" : "↗") + '</i>';
      if (link[3] === "future") return '<div class="shell-mega-link is-future">' + body + '</div>';
      return '<a class="shell-mega-link" href="' + link[2] + '">' + body + '</a>';
    }).join("") + '</div></div>';
    requestAnimationFrame(function () { mega.classList.add("is-open"); });
  }

  navigation.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-shell-menu]");
    if (!trigger) return;
    openMega(trigger.getAttribute("data-shell-menu"), trigger);
  });

  mobileToggle.addEventListener("click", function () {
    var opening = !drawer.classList.contains("is-open");
    drawer.classList.toggle("is-open", opening);
    mobileToggle.classList.toggle("is-open", opening);
    mobileToggle.setAttribute("aria-expanded", String(opening));
    if (opening) closeMega(false);
  });

  document.addEventListener("click", function (event) {
    if (activeMenu && !header.contains(event.target)) closeMega(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    if (drawer.classList.contains("is-open")) {
      drawer.classList.remove("is-open");
      mobileToggle.classList.remove("is-open");
      mobileToggle.setAttribute("aria-expanded", "false");
      mobileToggle.focus();
    } else if (activeMenu) {
      closeMega(true);
    }
  });

  var homeTitle = document.querySelector(".archive-copy h1");
  if (homeTitle && homeTitle.textContent.trim().toLowerCase() === "run it clean.") {
    homeTitle.innerHTML = "<span>Raigulus</span> Game Archives";
  }

  Array.prototype.forEach.call(document.querySelectorAll(".section > h2"), function (heading) {
    var headingText = heading.textContent.trim();
    if (headingText !== "Latest Optimized Guides" && headingText !== "Latest from the Archive") return;
    heading.textContent = "Latest from the Archive";
    heading.parentElement.classList.add("shell-latest-section");
    var kicker = document.createElement("p");
    kicker.className = "shell-section-kicker";
    kicker.textContent = "Recent dispatches";
    heading.parentElement.insertBefore(kicker, heading);
  });

  document.body.classList.add("shell-ready");
});

window.addEventListener("pageshow", function () {
  document.body.classList.remove("shell-page-leaving");
});

document.addEventListener("click", function (event) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  var link = event.target.closest("a[href]");
  if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
  var target = new URL(link.href, window.location.href);
  if (target.origin !== window.location.origin || target.pathname === window.location.pathname || target.hash) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  event.preventDefault();
  document.body.classList.add("shell-page-leaving");
  window.setTimeout(function () { window.location.href = target.href; }, 140);
});
