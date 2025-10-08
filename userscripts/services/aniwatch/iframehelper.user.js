// ==UserScript==
// @name         Anime RPC - AniWatch Iframe Helper
// @namespace    https://github.com/norinorin/anime_rpc
// @version      1.0.0
// @description  Sends video data from the AniWatch iframe to the main page.
// @author       norinorin
// @downloadURL  https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/aniwatch/iframehelper.user.js
// @updateURL    https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/aniwatch/iframehelper.user.js
// @match        *://megacloud.blog/*
// TODO: add more mirror sites
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  const findVideoInterval = setInterval(() => {
    const video = document.querySelector("video");

    if (video) {
      clearInterval(findVideoInterval);
      console.log("[Iframe Helper] Video element found. Ready to send data.");

      const sendState = () => {
        if (!video.duration || isNaN(video.duration)) return;

        const payload = {
          position: Math.round(video.currentTime * 1000),
          duration: Math.round(video.duration * 1000),
          paused: video.paused,
        };

        window.parent.postMessage(
          { type: "ANIME_RPC_VIDEO_STATE", payload },
          "*"
        );
      };

      setInterval(sendState, 2000);
    }
  }, 500);
})();
