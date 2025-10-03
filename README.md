<h1 align="center">
  Anime RPC
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/License-MIT-yellow.svg" /></a>
  <a><img alt="latest commit" src="https://img.shields.io/github/last-commit/norinorin/anime_rpc/main" /></a>
  <a><img alt="python version" src="https://img.shields.io/badge/python->=3.10-blue.svg" /></a>
</h1>

<p align="center">
  A Discord Rich Presence integration that shows what (anime) you are watching.
</p>

<p align="center">
  <img alt="anime rich presence" src="assets/docs/anime.png" />
  <img alt="generic stream rich presence" src="assets/docs/generic.png">
</p>

---

## 🚀 Features

- 📂 **Per-folder metadata with `.rpc` files**  
  Configure rich presence info for local media players like MPC and MPV by placing `.rpc` files in your anime folders

- 🔄 **Real-time presence updates**  
  Edits to `.rpc` files are picked up instantly, so your Discord status stays in sync without restarting anything.

- 🎉 **Discord Rich Presence without running Discord**  
  Show what you’re watching without needing the Discord client open via OAuth2.

- 📺 **Automatic anime episode tracking & metadata scraping**  
  Scrapes anime details and episode info from MyAnimeList with caching.

- 🎭 **Dynamic activity name**  
  The activity status adapts to what you’re watching, showing the anime title instead of a generic label (see [#14](https://github.com/norinorin/anime_rpc/pull/14)).

## 📦 Installation

1. Clone the repository:

```sh
git clone https://github.com/norinorin/anime_rpc.git
cd anime_rpc
```

2. Install the package:

```sh
pip install -e .
```

3. Run the app:

```sh
anime_rpc -h
```

## ⚙️ Local Playback Configuration

**anime_rpc** looks for a configuration file named `.rpc` (short for Rich Presence Config—not to be confused with Remote Procedure Call, or even Rich Presence Client :p) in the anime folder you're watching. If no such file is found, the folder is ignored.

There are two ways to set the metadata:

<details>

<summary>1. Automatically via MAL scraper (recommended)</summary>

---

To use the scraper, you only need to set the `url` key to the respective MAL page. This will automatically get the title, image URL, and episode titles (if run using `--fetch-episode-titles`) for the presence.

```env
# .rpc
url=MAL_URL_HERE
```

---

</details>

<details>

<summary>2. Manually</summary>

---

Refer to [the example config](example.rpc) to get started.

---

</details>

##### See the table below for more information:

| Key             | Default Value                                           | Description                                                                                                                                                                       |
| --------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| title\*         | Scraped from MAL if `url` is a MAL URL                  | Title of the anime, used in the Rich Presence.                                                                                                                                    |
| match\*         | Auto-generated if folder has more than one video file   | Regex pattern used to extract episode metadata from filenames. Must include a named group `ep` that matches numbers, or use `movie` for movies.                                   |
| image_url       | AniList logo, or scraped from MAL if `url` is a MAL URL | Image shown in Rich Presence.                                                                                                                                                     |
| url?            | `""`                                                    | URL for the presence button. Set to a MAL URL to enable scraping for metadata and episode titles.                                                                                 |
| url_text?       | `""`                                                    | Button label. If empty, the button will not be shown.                                                                                                                             |
| rewatching?     | `0`                                                     | Set to `1` if you're rewatching the anime.                                                                                                                                        |
| application_id? | `1088900742523392133` (anime)                           | Discord application ID. To display "Watching a stream" instead for non-anime use, use `1337621628179316848`. Otherwise, you can create your own app and use its `application_id`. |

\* If one of these is missing, the folder is ignored.

? Optional.

## 🖥️ Supported Platforms

### 1. Pollers

| Platform | CLI Flag                    | Description                                                                                                    |
| -------- | --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| mpv      | `--poller mpv-webui:[port]` | Polls mpv via [simple-mpv-webui](https://github.com/open-dynaMIX/simple-mpv-webui). Port defaults to **8080**. |
| mpc      | `--poller mpc:[port]`       | Polls MPC via its web interface. Port defaults to **13579**.                                                   |

### 2. Userscripts

Userscripts require a two-step installation: (1) the [core engine](https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/userscripts/core.user.js), and then (2) the scraper for each website you want to use:

| Website  | Installation Link                                                                                                      | Description                                                                                                                                                                                                                                                                                                                      |
| -------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| YouTube  | [Install](https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/userscripts/services/youtube.user.js)  | Supported channels: [@MuseAsia](https://www.youtube.com/@MuseAsia) and [@MuseIndonesia](https://www.youtube.com/@MuseIndonesia).<br><br>Caution: It may not work properly due to their inconsistent formatting. We have no reliable way of knowing whether the video is an actual anime or just commentary, PV, highlights, etc. |
| BiliBili | [Install](https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/userscripts/services/bilibili.user.js) | -                                                                                                                                                                                                                                                                                                                                |
| ...      | ...                                                                                                                    | ...                                                                                                                                                                                                                                                                                                                              |

## 📅 Plans

- [x] Automatically generate a regex given filenames in a folder.
- [x] Add formatting templates for `.rpc.match` (`%ep%`, `%title%`).
- [x] ~~Rework browser extension.~~ Migrate to userscripts.
- [ ] Add more support for anime sites and media players.
- [ ] Implement a customisable formatting.
- [ ] Implement automatic MyAnimeList/AniList episode tracking.

## 📝 License

MIT
