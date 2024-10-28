function getStateFromBilibili() {
  let videoElement = window.document.querySelector(
    ".player-mobile-video-wrap"
  )?.firstChild;

  if (!videoElement) {
    return;
  }

  if (!window.document.querySelector(".bstar-meta-tag--anime")) {
    return;
  }

  let title = window.document.querySelector(".bstar-meta__title")?.textContent;
  let episode = window.document
    .querySelector(".ep-item--active")
    ?.textContent.match(/\d+/)[0];
  return { title, episode, videoElement };
}
