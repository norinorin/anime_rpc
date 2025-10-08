// ==UserScript==
// @name         Anime RPC - AniWatch Scraper
// @namespace    https://github.com/norinorin/anime_rpc
// @version      1.0.0
// @description  Adds AniWatch support to the Anime RPC Core Engine.
// @author       norinorin
// @downloadURL  https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/aniwatch/aniwatch.user.js
// @updateURL    https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/aniwatch/aniwatch.user.js
// @match        *://*.aniwatchtv.to/*
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  "use strict";

  const HOSTNAME = "aniwatchtv.to";

  let lastVideoState = {
    position: 0,
    duration: 0,
    paused: true,
  };

  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "ANIME_RPC_VIDEO_STATE") {
      const payload = event.data.payload;
      if (payload) {
        lastVideoState = payload;
        console.debug(
          "[AniWatch Scraper] Received video state:",
          lastVideoState
        );
      }
    }
  });

  function getState() {
    const iframe = document.querySelector("#iframe-embed");
    console.debug("[AniWatch Scraper] iframe URL:", iframe?.src);
    if (!iframe) return;

    const currentEpisode = document.querySelector("a.ep-item.active");
    console.debug("[AniWatch Scraper] currentEpisode:", currentEpisode);
    if (!currentEpisode) return;

    const episode = currentEpisode.getAttribute("data-number");
    const episodeTitle = currentEpisode.getAttribute("title");
    const title = document.querySelector("h2.film-name")?.textContent.trim();

    console.debug("[AniWatch Scraper] title:", title);
    console.debug("[AniWatch Scraper] episode:", episode);
    console.debug("[AniWatch Scraper] episodeTitle:", episodeTitle);

    return {
      title,
      episode_title: episodeTitle,
      episode,
      display_name: "AniWatch",
      ...lastVideoState,
    };
  }

  const registryInterval = setInterval(() => {
    if (unsafeWindow.animeRPC_Scrapers) {
      clearInterval(registryInterval);
      console.log("[AniWatch Scraper] Core engine found. Registering scraper.");
      unsafeWindow.animeRPC_Scrapers[HOSTNAME] = getState;
    }
  }, 100);
})();
