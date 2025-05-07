<h1 align="center">
  Anime RPC
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a><img alt="latest commit" src="https://img.shields.io/github/last-commit/norinorin/anime_rpc/main"></a>
</h1>

<p align="center">
  A Discord Rich Presence integration that shows what (anime) you are watching.
</p>

<p align="center">
  <img alt="anime rich presence" src="assets/docs/anime.png" />
  <img alt="generic stream rich presence" src="assets/docs/generic.png">
</p>

---

## Installation

1. Clone the repository:

```sh
git clone https://github.com/norinorin/anime_rpc.git
cd anime_rpc
```

2. Install the dependencies:

```sh
pip install -r requirements.txt
```

3. Run the app:

```sh
python -OOm anime_rpc -h
```

## Configuration

anime_rpc looks for a configuration file named `rpc.config` in the anime folder you're watching (when watching locally). If no such file is found, the folder is ignored. Refer to [the example config](example.rpc.config) to get started.

Unfortunately, you'll need to manually create a config file for each anime folder. However, if the anime is on MyAnimeList (which is likely), you only need to set the `url` field to the anime's MAL page. The rest of the required fields will be filled in automatically. See the table below:

| Key             | Default Value                                         | Description                                                                                                                                                                                  |
| --------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| title\*         | scraped from MAL if `url` is a MAL URL                | Title of the anime, used in the Rich Presence.                                                                                                                                               |
| image_url\*     | scraped from MAL if `url` is a MAL URL                | Image shown in Rich Presence.                                                                                                                                                                |
| match\*         | auto-generated if folder has more than one video file | Regex pattern used to extract episode metadata from filenames. Must include a named group `ep` that matches numbers, or use `movie` for movies.                                              |
| url?            | `""`                                                  | URL for the presence button. set to a MAL URL to enable scraping for metadata and episode titles.                                                                                            |
| url_text?       | `""`                                                  | Button label. If empty, the button will not be shown.                                                                                                                                        |
| rewatching?     | `0`                                                   | Set to `1` if you're rewatching the anime.                                                                                                                                                   |
| application_id? | `1088900742523392133`                                 | Discord application ID. Defaults to the "Anime" app. To display "Watching a stream" instead, use `1337621628179316848`. Otherwise, you can create your own app and use its `application_id`. |

\* If one of these is missing, the folder is ignored.

? Optional.

## Supported platforms

| poller name | type      | description                                                                                              |
| ----------- | --------- | -------------------------------------------------------------------------------------------------------- |
| mpv         | poller    | polls mpv via native IPC socket or [simple-mpv-webui](https://github.com/open-dynaMIX/simple-mpv-webui). |
| mpc         | poller    | polls MPC via its web interface.                                                                         |
| bilibili.tv | websocket | support for [Bstation](https://www.bilibili.tv/anime).                                                   |

and more coming!

## Plans

- [x] Automatically generate a regex given filenames in a folder.
- [x] Add formatting templates for `rpc.config.match` (`%ep%`, `%title%`).
- [ ] Rework browser extension.
- [ ] Add more support for anime sites and media players.
- [ ] Implement a customisable formatting.

## License

MIT
