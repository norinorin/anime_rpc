// ==UserScript==
// @name         Anime RPC - YouTube Scraper
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Adds YouTube support to the Anime RPC Core Engine.
// @author       norinorin
// @downloadURL  https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/youtube.user.js
// @updateURL    https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/youtube.user.js
// @match        *://*.youtube.com/*
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  "use strict";

  const HOSTNAME = "www.youtube.com";

  // all handles must be in lowercase
  // FIXME: test more channels
  const ANIME_CHANNELS = new Set(["@museasia"]);

  function ensureAnimeChannel() {
    const channelNameElement = document.querySelector(
      "ytd-channel-name #text > a"
    );
    const channelHref = channelNameElement?.getAttribute("href");
    const channelHandle = channelHref?.substring(1).toLowerCase();
    return channelHandle && ANIME_CHANNELS.has(channelHandle);
  }

  function parseTimeToSeconds(timeStr) {
    const parts = timeStr.split(":").map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    return 0;
  }

  function handleMarathonVideo(videoElement, rawTitle, chapterList) {
    const chapterData = [];

    chapterList.forEach((chapterEl) => {
      const chapterTitle = chapterEl
        .querySelector("h4.macro-markers")
        ?.textContent.trim();
      const chapterTimeStr = chapterEl
        .querySelector("#time")
        ?.textContent.trim();
      if (chapterTitle && chapterTimeStr !== undefined) {
        chapterData.push({
          title: chapterTitle,
          startTime: parseTimeToSeconds(chapterTimeStr),
        });
      }
    });

    console.debug("Parsed chapter data:", chapterData);

    if (chapterData.length === 0) return null;
    chapterData.sort((a, b) => a.startTime - b.startTime);

    console.debug("Sorted chapter data:", chapterData);

    const currentTime = videoElement.currentTime;
    let currentChapter = null;
    let currentChapterIndex = -1;

    for (let i = 0; i < chapterData.length; i++) {
      if (currentTime >= chapterData[i].startTime) {
        currentChapter = chapterData[i];
        currentChapterIndex = i;
      } else {
        break;
      }
    }

    console.debug("Current time:", currentTime);
    console.debug("Current chapter:", currentChapter);

    if (!currentChapter) return null;

    const nextChapterStartTime =
      chapterData[currentChapterIndex + 1]?.startTime || videoElement.duration;
    const chapterDuration = nextChapterStartTime - currentChapter.startTime;
    const chapterPosition = currentTime - currentChapter.startTime;

    const episodeMatch = currentChapter.title.match(
      /ep(?:isode)?\s*(?<ep>\d+)\s*[:：]\s*(?<title>.+)?/i
    );
    const episodeNumber = episodeMatch?.groups?.ep;
    const episodeTitle = episodeMatch?.groups?.title || "";

    console.debug("Episode match:", episodeMatch);
    console.debug("Episode number:", episodeNumber);
    console.debug("Episode title:", episodeTitle);

    if (!episodeNumber) return null;

    const title = rawTitle.replace(/\[.*?\]|【.*?】|[-|]/g, "").trim();

    console.debug(currentChapter, episodeNumber, episodeTitle);
    return {
      title,
      episode: episodeNumber,
      episode_title: episodeTitle,
      position: Math.round(chapterPosition * 1000),
      duration: Math.round(chapterDuration * 1000),
    };
  }

  function handleSingleVideo(videoElement, rawTitle) {
    const episodeMatch = rawTitle.match(
      /ep(?:isode)?\s*(\d+(?:\s*[～~-]\s*\d+)?)/i
    );
    const episode = episodeMatch?.[1];

    console.debug("Single video episode match:", episodeMatch);
    console.debug("Single video episode:", episode);

    if (!episode) return null;

    const title = rawTitle
      .split(episodeMatch[0])[0]
      .replace(/\[.*?\]|【.*?】|[-|]/g, "")
      .trim();

    return {
      title,
      episode: episode.replace(/\s/g, ""),
      position: Math.round(videoElement.currentTime * 1000),
      duration: Math.round(videoElement.duration * 1000),
    };
  }

  function getStateFromYouTube() {
    if (!window.location.href.match(/\/watch/)) return;

    const videoElement = document.querySelector(
      "#container video.video-stream"
    );
    console.debug("getting video element");
    if (!videoElement) return null;
    console.debug("matching anime channel");
    if (!ensureAnimeChannel()) return null;

    const rawTitle = document.querySelector(
      "#title .ytd-watch-metadata yt-formatted-string"
    ).title;
    console.debug("getting raw title");
    if (!rawTitle) return null;

    // we have to query twice cos if you open the chapters, they'll get duplicated in the DOM
    const chapterList = document
      .querySelector(
        'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-macro-markers-description-chapters"]'
      )
      ?.querySelectorAll(
        "#content ytd-macro-markers-list-renderer:not(.browser-mode) #contents ytd-macro-markers-list-item-renderer #endpoint #details"
      );
    console.debug("detected chapter list", chapterList);

    let state =
      chapterList?.length > 0
        ? handleMarathonVideo(videoElement, rawTitle, chapterList)
        : handleSingleVideo(videoElement, rawTitle);

    if (state) {
      state.videoElement = videoElement;
      state.display_name = "YouTube";
      return state;
    }

    return null;
  }

  const registryInterval = setInterval(() => {
    if (unsafeWindow.animeRPC_Scrapers) {
      clearInterval(registryInterval);
      console.log("[YouTube Scraper] Core engine found. Registering scraper.");
      unsafeWindow.animeRPC_Scrapers[HOSTNAME] = getStateFromYouTube;
    }
  }, 100);
})();
