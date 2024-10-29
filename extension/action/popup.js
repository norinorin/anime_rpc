(async () => {
  const animeName = document.querySelector("#animeName");
  const imageUrl = document.querySelector("#imageUrl");
  const url = document.querySelector("#url");
  const rewatching = document.querySelector("#rewatching");
  const content = document.querySelector("#content");
  const errorContent = document.querySelector("#error-content");
  let tabId;

  tabs = await browser.tabs.query({ currentWindow: true, active: true });
  if (!tabs) {
    return;
  }
  tabId = tabs[0].id;

  function sendMessage(message, cb, ecb) {
    browser.tabs.sendMessage(tabId, message).then(cb, ecb);
  }

  sendMessage({ cmd: "requestState" }, (response) => {
    animeName.textContent = response.title;
    content.classList.toggle("hidden");
    errorContent.classList.toggle("hidden");

    browser.storage.local.get(response.title).then((cached) => {
      data = cached[response.title];
      if (!data) return;
      console.log("Getting cached", data);
      imageUrl.textContent = data.imageUrl || "";
      url.textContent = data.url || "";
      rewatching.checked = data.rewatching || false;
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
})();
