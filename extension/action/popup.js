const animeName = document.querySelector("#animeName");
const imageUrl = document.querySelector("#imageUrl");
const url = document.querySelector("#url");
const rewatching = document.querySelector("#rewatching");
let tabId;

function sendMessage(message, cb, ecb) {
  if (!tabId) return;
  browser.tabs.sendMessage(tabId, message).then(cb, ecb);
}

browser.tabs.query({ currentWindow: true, active: true }).then((tabs) => {
  if (!tabs[0]) return;

  tabId = tabs[0].id;
  sendMessage({ cmd: "requestState" }, (response) => {
    animeName.textContent = response.title;
    browser.storage.local.get(response.title).then((cached) => {
      data = cached[response.title];
      if (!data) return;
      console.log("Getting cached", data);
      imageUrl.textContent = data.imageUrl || "";
      url.textContent = data.url || "";
      rewatching.checked = data.rewatching || false;
    });
  });
});

window.addEventListener("mouseout", () => {
  if (animeName.textContent) {
    let toStore = {};
    toStore[animeName.textContent] = {
      url: url.textContent,
      imageUrl: imageUrl.textContent,
      rewatching: rewatching.checked,
    };
    console.log(
      "Caching",
      url.textContent,
      imageUrl.textContent,
      rewatching.checked
    );
    browser.storage.local.set(toStore);
  }
});

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log(message, sender, sendResponse);
});
