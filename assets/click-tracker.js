// Outbound link click tracking for Google Analytics.
// Extracted from inline script to support strict CSP (no unsafe-inline).
document.addEventListener("click", function (event) {
  var link = event.target.closest("a[href]");
  if (!link || typeof gtag !== "function") return;
  var url;
  try {
    url = new URL(link.href, window.location.href);
  } catch (error) {
    return;
  }
  if (url.origin === window.location.origin) return;
  var host = url.hostname.replace(/^www\./, "");
  var label = (link.getAttribute("aria-label") || link.textContent || "").trim().slice(0, 120);
  var eventName = "outbound_click";
  if (host === "youtube.com" || host === "youtu.be") eventName = "youtube_click";
  if (host === "instagram.com") eventName = "instagram_click";
  if (host === "discord.com" || host === "discord.gg") eventName = "discord_click";
  gtag("event", eventName, {
    link_url: url.href,
    link_domain: host,
    link_text: label,
    page_path: window.location.pathname,
    event_category: "engagement",
  });
}, true);
