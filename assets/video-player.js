(function () {
  "use strict";

  function activate(facade) {
    var videoId = facade.dataset.videoId || "";
    if (!/^[A-Za-z0-9_-]{11}$/.test(videoId)) return;

    var iframe = document.createElement("iframe");
    iframe.className = "video-facade-player";
    iframe.src = "https://www.youtube-nocookie.com/embed/" + videoId + "?autoplay=1&rel=0";
    iframe.title = facade.dataset.videoTitle || "YouTube video player";
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.allowFullscreen = true;
    facade.replaceChildren(iframe);
    iframe.focus();
  }

  document.querySelectorAll(".video-facade[data-video-id]").forEach(function (facade) {
    var button = facade.querySelector(".video-facade-button");
    if (!button) return;
    button.addEventListener("click", function () {
      activate(facade);
    }, { once: true });
  });
})();
