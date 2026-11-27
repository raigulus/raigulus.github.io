(function() {
            function nextWednesday() {
              var now = new Date();
              var t = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 8, 0, 0));
              var d = (3 - t.getUTCDay() + 7) % 7;
              if (d === 0 && t <= now) d = 7;
              t.setUTCDate(t.getUTCDate() + d);
              return t;
            }
            function pad(n) { return (n < 10 ? "0" : "") + n; }
            function tick() {
              var el = document.getElementById("cassie-countdown");
              if (!el) return;
              var ms = nextWednesday().getTime() - Date.now();
              if (ms <= 0) { el.textContent = "OPEN NOW"; return; }
              var s = Math.floor(ms / 1000);
              el.textContent = Math.floor(s / 86400) + "d " + pad(Math.floor(s % 86400 / 3600)) + ":" + pad(Math.floor(s % 3600 / 60)) + ":" + pad(s % 60);
            }
            tick();
            setInterval(tick, 1000);
          })();
