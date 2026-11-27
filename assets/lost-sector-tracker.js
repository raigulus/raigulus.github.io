// Destiny 2 Lost Sector Tracker - Client-side calculation
    (function() {
      // Destiny 2 daily reset: 10:00 AM Pacific local (17:00 UTC in PDT, 18:00 UTC in PST)
      var RESET_MINUTE_UTC = 0;

      // Lost Sector rotations per destination (simplified - in reality Bungie rotates these)
      // These are approximate rotations based on known Lost Sectors
      var lostSectors = {
        edz: [
          "The Empty Tank", "Scavenger's Den", "Skydock IV", "Hallowed Grove", "K1 Revelation",
          "The Drain", "Widow's Walk", "Aphelion's Rest", "Chamber of Starlight", "Bay of Drowned Wishes"
        ],
        cosmodrome: [
          "The Grotto", "K1 Revelation", "Skydock IV", "The Empty Tank", "Scavenger's Den"
        ],
        moon: [
          "K1 Revelation", "K1 Communion", "K1 Crew Quarters", "K1 Logistics", "K1 Ridgeline"
        ],
        europa: [
          "Exodus Garden 2A", "Perdition", "Bunker E15", "Beyond", "The Rift"
        ],
        "throne-world": [
          "The Quietest Void", "Aphelion's Rest", "Chamber of Starlight", "Bay of Drowned Wishes", "The Drain"
        ]
      };

      // Champion and shield info per Lost Sector (simplified)
      var championInfo = {
        "The Empty Tank": "Barrier, Overload / Solar shields",
        "Scavenger's Den": "Barrier, Unstoppable / Arc shields",
        "Skydock IV": "Overload, Unstoppable / Void shields",
        "Hallowed Grove": "Barrier, Overload / Solar shields",
        "K1 Revelation": "Barrier, Unstoppable / Arc shields",
        "The Drain": "Overload, Unstoppable / Void shields",
        "Widow's Walk": "Barrier, Overload / Solar shields",
        "Aphelion's Rest": "Barrier, Unstoppable / Void shields",
        "Chamber of Starlight": "Overload, Unstoppable / Arc shields",
        "Bay of Drowned Wishes": "Barrier, Overload / Solar shields",
        "The Grotto": "Barrier, Unstoppable / Arc shields",
        "K1 Communion": "Overload, Unstoppable / Void shields",
        "K1 Crew Quarters": "Barrier, Overload / Solar shields",
        "K1 Logistics": "Barrier, Unstoppable / Arc shields",
        "K1 Ridgeline": "Overload, Unstoppable / Void shields",
        "Exodus Garden 2A": "Barrier, Overload / Solar shields",
        "Perdition": "Barrier, Unstoppable / Arc shields",
        "Bunker E15": "Overload, Unstoppable / Void shields",
        "Beyond": "Barrier, Overload / Solar shields",
        "The Rift": "Barrier, Unstoppable / Arc shields",
        "The Quietest Void": "Overload, Unstoppable / Void shields"
      };

      function ptClockParts(date) {
  var parts = {};
  new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", hour12: false,
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  }).formatToParts(date).forEach(function (p) { parts[p.type] = p.value; });
  return { h: parseInt(parts.hour, 10) % 24, m: parseInt(parts.minute, 10), s: parseInt(parts.second, 10) };
}

// The reset is 10:00 AM Pacific *local* time. A fixed UTC hour breaks across
// daylight saving: 17:00 UTC is 10:00 PDT but 09:00 PST, so the countdown used
// to fire an hour early for roughly two thirds of the year. Both sides of the
// subtraction are Pacific wall-clock, so this holds on either side of a DST change.
function getNextReset() {
  var now = new Date();
  var t = ptClockParts(now);
  var elapsed = t.h * 3600 + t.m * 60 + t.s;
  var delta = 10 * 3600 - elapsed;
  if (delta <= 0) delta += 24 * 3600;
  var guess = new Date(now.getTime() + delta * 1000);

  // On the two DST changeover days the wall-clock step lands on 09:00 or 11:00
  // because 02:00 either never happens or happens twice. Nudge by the observed
  // hour difference; a couple of passes converge and the result is exact on
  // every day of the year.
  for (var i = 0; i < 3; i++) {
    var diff = 10 - ptClockParts(guess).h;
    if (diff === 0) break;
    guess = new Date(guess.getTime() + diff * 3600 * 1000);
  }
  return guess;
}

      function getDaysSinceEpoch() {
        var epoch = new Date(Date.UTC(2024, 0, 1)); // Reference date
        var now = new Date();
        return Math.floor((now.getTime() - epoch.getTime()) / (24 * 60 * 60 * 1000));
      }

      function getLostSectorForDestination(destination, dayIndex) {
        var sectors = lostSectors[destination];
        if (!sectors || sectors.length === 0) return "Unknown";
        return sectors[dayIndex % sectors.length];
      }

      function updateTracker() {
        var nextReset = getNextReset();
        var now = new Date();
        var diff = nextReset.getTime() - now.getTime();

        var hours = Math.floor(diff / (1000 * 60 * 60));
        var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        var seconds = Math.floor((diff % (1000 * 60)) / 1000);

        document.getElementById("countdown").textContent = hours + "h " + minutes + "m " + seconds + "s";
        document.getElementById("last-reset").textContent = "Last reset: " + now.toISOString().split("T")[0];

        // Get current day index for rotations
        var dayIndex = getDaysSinceEpoch();

        // Update each destination
        var destinations = ["edz", "cosmodrome", "moon", "europa", "throne-world"];
        destinations.forEach(function(dest) {
          var sectorName = getLostSectorForDestination(dest, dayIndex);
          var info = championInfo[sectorName] || "Champions and shields vary";

          document.getElementById(dest + "-name").textContent = sectorName;
          document.getElementById(dest + "-info").textContent = info;
          document.getElementById(dest + "-legend").textContent = "Legend";
          document.getElementById(dest + "-master").textContent = "Master";
        });
      }

      // Update immediately and then every second
      updateTracker();
      setInterval(updateTracker, 1000);
    })();
