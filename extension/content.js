console.log("Loaded");
const ws = new WebSocket("ws://localhost:56727/ws");
ws.onmessage = (e) => console.log(e);
ws.onopen = () => {
  setInterval(ws.send("keepalive"), 30000);
};

const SITES_MAP = { "www.bilibili.tv": getStateFromBilibili };
let lastUrl = window.location.href;
let interval;
let state;

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.cmd === "requestState") {
    sendResponse(state);
  }
});

async function handleVideoStateChanges() {
  const origin = window.location.hostname;
  const func = SITES_MAP[origin];
  state = func();

  if (!state) return;

  // state found
  clearInterval(interval);

  const { videoElement } = state;
  delete state.videoElement;

  videoElement.onseeked = () => handleVideoStateChanges(videoElement);
  videoElement.onplay = () => handleVideoStateChanges(videoElement);
  videoElement.onpause = () => handleVideoStateChanges(videoElement);

  data = (await browser.storage.local.get(state.title))[state.title];
  if (data) {
    console.log("Getting cached", data);
    state.image_url = data.imageUrl || "";
    state.url = data.url || "";
    state.rewatching = data.rewatching || false;
  }

  const { currentTime, duration, paused } = videoElement;
  const payload = {
    ...state,
    position: currentTime * 1000,
    duration: duration * 1000,
    watching_state: 1 + !paused,
    origin,
  };

  // duration can be null
  if (!payload.duration) {
    // 0 equals stopped in mpc-hc
    payload.watching_state = 0;
  }

  console.log(`Sending ${JSON.stringify(payload)}`);

  ws.send(JSON.stringify(payload));
}

const observer = new MutationObserver(() => {
  const currentUrl = window.location.href;
  if (currentUrl !== lastUrl) {
    init();
    lastUrl = currentUrl;
  }
});

function init() {
  // idk why but setting interval fixes everything
  clearInterval(interval);
  interval = setInterval(handleVideoStateChanges, 1000);
}

observer.observe(document.body, { childList: true, subtree: true });
init();
