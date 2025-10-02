// ==UserScript==
// @name         Anime RPC - BiliBili Scraper
// @namespace    https://github.com/norinorin/anime_rpc
// @version      1.0.0
// @description  Adds BiliBili support to the Anime RPC Core Engine.
// @author       norinorin
// @downloadURL  https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/bilibili.user.js
// @updateURL    https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/bilibili.user.js
// @match        *://*.bilibili.tv/*
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  "use strict";

  const HOSTNAME = "www.bilibili.tv";

  function getState() {
    let videoElement = window.document.querySelector(
      ".player-mobile-video-wrap"
    )?.firstChild;

    if (!videoElement) return;

    if (!window.document.querySelector(".bstar-meta-tag--anime")) return;

    let title =
      window.document.querySelector(".bstar-meta__title")?.textContent;
    let epElement = window.document.querySelector(".ep-item--active");
    let episode = epElement?.textContent.match(/\d+/)[0];
    let episode_title = epElement?.title;

    if (!episode) return;

    return { title, episode_title, episode, videoElement };
  }

  const registryInterval = setInterval(() => {
    if (unsafeWindow.animeRPC_Scrapers) {
      clearInterval(registryInterval);
      console.log("[BiliBili Scraper] Core engine found. Registering scraper.");
      unsafeWindow.animeRPC_Scrapers[HOSTNAME] = getState;
    }
  }, 100);
})();
