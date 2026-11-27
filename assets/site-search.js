(function() {
            var input = document.getElementById("site-search-input");
            var box = document.getElementById("site-search-results");
            var count = document.getElementById("site-search-count");
            if (!input || !box) return;
            var SECTIONS = {"division-2": "Division 2", "destiny-2": "Destiny 2", "diablo-4": "Diablo 4", "guides": "Guides", "lore": "Lore", "home": "Raigulus"};
            function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
            function sectionName(s) {
              if (SECTIONS[s]) return SECTIONS[s];
              return String(s).replace(/-/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase(); });
            }
            function termsOf(q) { return q.toLowerCase().split(/\s+/).filter(function(t) { return t.length > 0; }); }
            function scorePage(p, terms) {
              var title = p.t.toLowerCase(), rest = (p.d + " " + (p.b || "") + " " + p.u + " " + p.s).toLowerCase(), sc = 0;
              for (var i = 0; i < terms.length; i++) {
                var inTitle = title.indexOf(terms[i]) !== -1;
                if (!inTitle && rest.indexOf(terms[i]) === -1) return -1;
                sc += inTitle ? 2 : 1;
              }
              return sc;
            }
            var pages = null, loading = false;
            function render() {
              var q = input.value.trim();
              if (!pages) {
                box.innerHTML = "";
                count.textContent = loading ? "Loading the index..." : "Start typing to search the archive.";
                return;
              }
              var terms = termsOf(q);
              if (!terms.length) { box.innerHTML = ""; count.textContent = "Type above to search " + pages.length + " pages."; return; }
              var hits = [];
              for (var i = 0; i < pages.length; i++) {
                var sc = scorePage(pages[i], terms);
                if (sc >= 0) hits.push({ p: pages[i], sc: sc });
              }
              hits.sort(function(a, b) { return b.sc - a.sc; });
              hits = hits.slice(0, 50);
              count.textContent = hits.length + (hits.length === 1 ? " result" : " results") + ' for "' + q + '"';
              box.innerHTML = hits.map(function(h) {
                return '<article class="video-card"><div class="card-body">' +
                  '<p class="eyebrow">' + esc(sectionName(h.p.s)) + "</p>" +
                  '<h2><a href="' + esc(h.p.u) + '">' + esc(h.p.t) + "</a></h2>" +
                  (h.p.d ? "<p>" + esc(h.p.d) + "</p>" : "") +
                  "</div></article>";
              }).join("") || "<p>No matches. Try fewer words.</p>";
              if (typeof gtag === "function" && q.length >= 3) {
                try { gtag("event", "site_search", { search_term: q.toLowerCase() }); } catch (e) {}
              }
            }
            // The index is ~1.6 MB. Fetching it on page load charged every visit,
            // including the ones that never typed a query. Pull it on the first
            // interaction instead; a ?q= deep link still counts as intent to search.
            var loadIndex = null;
            function ensureIndex() {
              if (pages || loadIndex) return;
              loadIndex = fetch("/assets/data/search-index.json", { cache: "no-cache" })
                .then(function(r) { if (!r.ok) throw new Error("index missing"); return r.json(); })
                .then(function(data) { pages = data.pages || []; return pages; })
                .catch(function() { count.textContent = "Search index failed to load."; loadIndex = null; });
            }
            var params = new URLSearchParams(window.location.search);
            input.value = params.get("q") || "";
            if (input.value) ensureIndex();
            input.addEventListener("focus", ensureIndex, { once: true });
            input.addEventListener("input", function() { ensureIndex(); render(); });
          })();
