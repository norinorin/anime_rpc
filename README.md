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
# rpc.config
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

| Key             | Default Value                                         | Description                                                                                                                                                                                  |
| --------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| title\*         | Scraped from MAL if `url` is a MAL URL                | Title of the anime, used in the Rich Presence.                                                                                                                                               |
| image_url\*     | Scraped from MAL if `url` is a MAL URL                | Image shown in Rich Presence.                                                                                                                                                                |
| match\*         | Auto-generated if folder has more than one video file | Regex pattern used to extract episode metadata from filenames. Must include a named group `ep` that matches numbers, or use `movie` for movies.                                              |
| url?            | `""`                                                  | URL for the presence button. Set to a MAL URL to enable scraping for metadata and episode titles.                                                                                            |
| url_text?       | `""`                                                  | Button label. If empty, the button will not be shown.                                                                                                                                        |
| rewatching?     | `0`                                                   | Set to `1` if you're rewatching the anime.                                                                                                                                                   |
| application_id? | `1088900742523392133`                                 | Discord application ID. Defaults to the "Anime" app. To display "Watching a stream" instead, use `1337621628179316848`. Otherwise, you can create your own app and use its `application_id`. |

\* If one of these is missing, the folder is ignored.

? Optional.

## 🖥️ Supported Platforms

| Platform    | Type      | Description                                                                                              |
| ----------- | --------- | -------------------------------------------------------------------------------------------------------- |
| mpv         | poller    | Polls mpv via native IPC socket or [simple-mpv-webui](https://github.com/open-dynaMIX/simple-mpv-webui). |
| mpc         | poller    | Polls MPC via its web interface.                                                                         |
| bilibili.tv | websocket | Support for [Bstation](https://www.bilibili.tv/anime).                                                   |

and more coming!

## 📅 Plans

- [x] Automatically generate a regex given filenames in a folder.
- [x] Add formatting templates for `.rpc.match` (`%ep%`, `%title%`).
- [ ] Rework browser extension.
- [ ] Add more support for anime sites and media players.
- [ ] Implement a customisable formatting.
- [ ] Implement automatic MyAnimeList/AniList episode tracking.

## 📝 License

MIT
