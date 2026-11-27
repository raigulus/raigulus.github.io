(function() {
      function pad(n) { return (n < 10 ? "0" : "") + n; }
      function nextDaily(hourUTC) {
        var now = new Date();
        var t = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hourUTC, 0, 0));
        if (t <= now) t.setUTCDate(t.getUTCDate() + 1);
        return t;
      }
      function nextWeekly(dayUTC, hourUTC) {
        var now = new Date();
        var t = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hourUTC, 0, 0));
        var d = (dayUTC - t.getUTCDay() + 7) % 7;
        if (d === 0 && t <= now) d = 7;
        t.setUTCDate(t.getUTCDate() + d);
        return t;
      }
      var timers = [
        { el: "cd-daily", when: function() { return nextDaily(8); } },
        { el: "cd-chest", when: function() { return nextWeekly(1, 8); } },
        { el: "cd-weekly", when: function() { return nextWeekly(2, 8); } },
        { el: "cd-cassie", when: function() { return nextWeekly(3, 8); } }
      ];
      function fmt(ms) {
        var s = Math.floor(ms / 1000);
        var d = Math.floor(s / 86400); s -= d * 86400;
        var h = Math.floor(s / 3600); s -= h * 3600;
        var m = Math.floor(s / 60); s -= m * 60;
        return d + "d " + pad(h) + ":" + pad(m) + ":" + pad(s);
      }
      function tick() {
        var now = new Date();
        for (var i = 0; i < timers.length; i++) {
          var t = timers[i].when();
          var el = document.getElementById(timers[i].el);
          if (el) el.textContent = fmt(t - now) + " (" + t.toLocaleString() + " your time)";
        }
      }
      tick();
      setInterval(tick, 1000);
    })();
