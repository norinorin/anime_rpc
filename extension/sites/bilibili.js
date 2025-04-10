function getStateFromBilibili() {
  let videoElement = window.document.querySelector(
    ".player-mobile-video-wrap"
  )?.firstChild;

  if (!videoElement) return;

  if (!window.document.querySelector(".bstar-meta-tag--anime")) return;

  let title = window.document.querySelector(".bstar-meta__title")?.textContent;
  let epElement = window.document.querySelector(".ep-item--active");
  let episode = epElement?.textContent.match(/\d+/)[0];
  let episode_title = epElement?.title;

  if (!episode) return;

  return { title, episode_title, episode, videoElement };
}
