// ==UserScript==
// @name         Anime RPC Core Engine
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Handles WebSocket connection and state management for site-specific scrapers.
// @author       norinorin
// @match        *://*/*
// @connect      localhost
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addStyle
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  "use strict";

  const WS_URL = "ws://localhost:56727/ws";

  const SCRIPT_INSTANCE_ID = crypto.randomUUID();
  console.log(`[RPC Core] Instance ID: ${SCRIPT_INSTANCE_ID}`);

  if (!unsafeWindow.animeRPC_Scrapers) {
    unsafeWindow.animeRPC_Scrapers = {};
  }

  let scraperFunc = null;
  let ws = null;
  let mainInterval;
  let lastUrl = window.location.href;
  let currentTitle = "";
  let lastIsEmpty = true;

  let reconnectAttempts = 0;
  const BASE_RECONNECT_DELAY = 1000;
  const MAX_RECONNECT_DELAY = 60000;
  let reconnectTimeout = null;
  let intentionalClose = false;

  function formatOrigin(origin) {
    if (!origin) origin = window.location.hostname;

    return `${origin}-${SCRIPT_INSTANCE_ID}`;
  }

  function createUi() {
    if (document.getElementById("rpc-ui-container")) return;

    console.log("[RPC Core] Creating UI...");

    GM_addStyle(`
            #rpc-ui-container {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                z-index: 99999;
                font-family: sans-serif;
                font-size: 14px;
            }
            #rpc-hover-bar {
                width: 100%;
                height: 5px;
                background-color: #03a9f4;
                transition: height 0.2s ease-in-out;
            }
            #rpc-content-panel {
                padding: 15px;
                background-color: #212121;
                color: #eee;
                display: none;
                flex-direction: column;
                gap: 10px;
            }
            #rpc-ui-container:hover #rpc-hover-bar {
                height: 10px;
            }
            #rpc-ui-container:hover #rpc-content-panel {
                display: flex;
            }
            .rpc-form-row {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .rpc-form-row label {
                width: 120px;
                flex-shrink: 0;
            }
            .rpc-form-row input[type="text"] {
                width: 100%;
                background-color: #424242;
                color: #eee;
                border: 1px solid #616161;
                border-radius: 4px;
                padding: 5px;
            }
            #rpc-title {
                font-weight: bold;
            }
            #rpc-save-status {
                color: #4caf50;
                font-size: 12px;
                opacity: 0;
                transition: opacity 0.5s;
            }
        `);

    const container = document.createElement("div");
    container.id = "rpc-ui-container";

    const hoverBar = document.createElement("div");
    hoverBar.id = "rpc-hover-bar";

    const panel = document.createElement("div");
    panel.id = "rpc-content-panel";

    const createRow = (labelText, childElement) => {
      const row = document.createElement("div");
      row.className = "rpc-form-row";
      const label = document.createElement("label");
      label.textContent = labelText;
      row.appendChild(label);
      row.appendChild(childElement);
      return row;
    };

    const titleSpan = document.createElement("span");
    titleSpan.id = "rpc-title";
    titleSpan.textContent = "None";
    panel.appendChild(createRow("Detected Title:", titleSpan));

    const imageUrlInput = document.createElement("input");
    imageUrlInput.type = "text";
    imageUrlInput.id = "rpc-image-url";
    imageUrlInput.placeholder =
      "Cover image URL; no need to set if Info URL is set to MyAnimeList";
    panel.appendChild(createRow("Image URL:", imageUrlInput));

    const infoUrlInput = document.createElement("input");
    infoUrlInput.type = "text";
    infoUrlInput.id = "rpc-mal-url";
    infoUrlInput.placeholder =
      "URL to fetch metadata from (currently only MyAnimeList is supported)";
    panel.appendChild(createRow("Info URL:", infoUrlInput));

    const rewatchingInput = document.createElement("input");
    rewatchingInput.type = "checkbox";
    rewatchingInput.id = "rpc-rewatching";

    const saveStatusSpan = document.createElement("span");
    saveStatusSpan.id = "rpc-save-status";
    saveStatusSpan.textContent = "Saved!";
    const rewatchingContainer = document.createElement("div");

    rewatchingContainer.appendChild(rewatchingInput);
    rewatchingContainer.appendChild(saveStatusSpan);
    panel.appendChild(createRow("Rewatching:", rewatchingContainer));

    container.appendChild(hoverBar);
    container.appendChild(panel);
    document.body.appendChild(container);

    const saveOnChange = () => {
      const title = document.getElementById("rpc-title").textContent;
      if (!title || title === "None") return;

      const dataToSave = {
        imageUrl: document.getElementById("rpc-image-url").value,
        url: document.getElementById("rpc-mal-url").value,
        rewatching: document.getElementById("rpc-rewatching").checked,
      };

      GM_setValue(title, dataToSave).then(() => {
        const status = document.getElementById("rpc-save-status");
        status.style.opacity = "1";
        setTimeout(() => {
          status.style.opacity = "0";
        }, 1500);
      });
    };

    imageUrlInput.addEventListener("input", saveOnChange);
    infoUrlInput.addEventListener("input", saveOnChange);
    rewatchingInput.addEventListener("change", saveOnChange);
  }

  async function updateUi(state) {
    if (state?.title === currentTitle) return;

    currentTitle = state?.title || "None";

    const uiTitle = document.getElementById("rpc-title");
    const uiImageUrl = document.getElementById("rpc-image-url");
    const uiUrl = document.getElementById("rpc-mal-url");
    const uiRewatching = document.getElementById("rpc-rewatching");

    uiTitle.textContent = currentTitle;

    const cachedData = await GM_getValue(currentTitle, {});
    uiImageUrl.value = cachedData.imageUrl || "";
    uiUrl.value = cachedData.url || "";
    uiRewatching.checked = cachedData.rewatching || false;

    const container = document.getElementById("rpc-ui-container");
    container.style.display = currentTitle === "None" ? "none" : "block";
  }

  function connectWebSocket() {
    clearTimeout(reconnectTimeout);

    if (ws && ws.readyState < 2) {
      console.log(
        "[RPC Core] WebSocket connection is already open or connecting. Reusing it."
      );
      reconnectAttempts = 0;
      if (!mainInterval) {
        mainInterval = setInterval(handleVideoStateChanges, 1500);
      }
      return;
    }

    console.log(
      `[RPC Core] Attempting to establish WebSocket connection... (Attempt #${
        reconnectAttempts + 1
      })`
    );
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log(
        `[RPC Core] WebSocket connected for ${window.location.hostname}`
      );
      reconnectAttempts = 0;
      createUi();
      clearInterval(mainInterval);
      mainInterval = setInterval(handleVideoStateChanges, 1500);
    };

    ws.onclose = (event) => {
      console.log("[RPC Core] WebSocket disconnected.", event.reason);
      clearInterval(mainInterval);
      mainInterval = null;
      ws = null;

      if (intentionalClose) {
        console.log(
          "[RPC Core] WebSocket was closed intentionally. Not reconnecting."
        );
        intentionalClose = false;
        return;
      }

      reconnectAttempts++;
      const delay = Math.min(
        MAX_RECONNECT_DELAY,
        BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1)
      );

      const jitter = Math.random() * 1000;
      const totalDelay = delay + jitter;

      console.log(
        `[RPC Core] Will attempt to reconnect in ${Math.round(
          totalDelay / 1000
        )}s.`
      );
      reconnectTimeout = setTimeout(connectWebSocket, totalDelay);
    };

    ws.onerror = (error) => {
      console.error("[RPC Core] WebSocket error:", error);
    };
  }

  function wsSend(data) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.debug("WebSocket is not open. Cannot send data.");
      return;
    }

    console.debug("Sending data via WebSocket:", data);
    ws.send(JSON.stringify(data));
  }

  function activate() {
    createUi();

    scraperFunc = unsafeWindow.animeRPC_Scrapers[window.location.hostname];
    if (!scraperFunc) {
      console.debug("No scraper for hostname:", window.location.hostname);
      console.debug("Current scrapers:", unsafeWindow.animeRPC_Scrapers);
      updateUi(null);
      if (ws && ws.readyState < 2) {
        console.log(
          "[RPC Core] No scraper found for new URL. Closing existing WebSocket."
        );
        ws.close();
        intentionalClose = true;
        ws = null;
      }
      return false;
    }

    connectWebSocket();
    return true;
  }

  async function handleVideoStateChanges() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const state = scraperFunc();

    updateUi(state);

    if (!state || !state.videoElement) {
      console.debug("No valid video element found.");

      // clear presence on current origin
      !lastIsEmpty && wsSend({ origin: formatOrigin() });
      lastIsEmpty = true;
      return;
    }

    const { videoElement } = state;
    delete state.videoElement;

    const { paused } = videoElement;
    const cachedData = await GM_getValue(state.title, {});

    const payload = {
      ...state,
      image_url: cachedData.imageUrl,
      url: cachedData.url,
      rewatching: cachedData.rewatching,
      watching_state: paused ? 1 : 2,
      origin: formatOrigin(),
    };
    lastIsEmpty = false;

    if (isNaN(payload.duration) || payload.duration === 0) {
      payload.watching_state = 0;
    }

    wsSend(payload);
  }

  const observer = new MutationObserver(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      console.log(
        `[RPC Core] URL changed to: ${lastUrl}. Re-validating connection.`
      );
      const lastHostname = new URL(lastUrl).hostname;
      // clear presence on last origin
      wsSend({ origin: formatOrigin(lastHostname) });
      setTimeout(activate, 500);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  setTimeout(activate, 500);
})();
