from __future__ import annotations

import json
import logging
import pprint
import re
from http import HTTPStatus
from time import time
from typing import TYPE_CHECKING, TypedDict

from bs4 import BeautifulSoup

from anime_rpc.cache import SCRAPING_CACHE_DIR

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.config import Config
    from anime_rpc.states import State

MAL_PATTERN = re.compile(r"https?://myanimelist\.net/anime/(?P<id>\d+)")
_LOGGER = logging.getLogger("scraper")


SCRAPING_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class Scraped(TypedDict, total=False):
    id: str
    episodes: dict[str, str]
    title: str
    image_url: str
    episodes_url: str
    last_updated: int


async def _get_text(session: aiohttp.ClientSession, url: str) -> str | HTTPStatus:
    async with session.get(url) as response:
        if response.status != HTTPStatus.OK:
            status = HTTPStatus(response.status)
            _LOGGER.error(
                "Failed to fetch %s. Reason: %s. Code: %d (%s)",
                url,
                status.description,
                status.value,
                status.phrase,
            )
            return status

        return await response.text()


async def _fetch_metadata(session: aiohttp.ClientSession, url: str) -> Scraped:
    _LOGGER.info("Fetching metadata from %s", url)

    ret = Scraped()

    if isinstance(html := await _get_text(session, url), HTTPStatus):
        return ret

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("#horiznav_nav ul li a"):
        if a.string == "Episodes":
            url = str(a["href"])
            _LOGGER.info("Found episodes url: %s", url)
            ret["episodes_url"] = url
            break

    if title := soup.select_one("h1.title-name"):
        ret["title"] = title.get_text(strip=True)

    if img := soup.select_one("div.leftside a img"):
        ret["image_url"] = str(img.attrs["data-src"])

    ret["last_updated"] = int(time() * 1000)
    return ret


async def get_metadata(session: aiohttp.ClientSession, url: str) -> Scraped | None:
    if not (match := MAL_PATTERN.match(url)):
        _LOGGER.debug("URL %s does not match MAL pattern", url)
        return None

    id_ = match.group("id")
    if (cached := SCRAPING_CACHE_DIR / f"{id_}.json").exists():
        _LOGGER.debug("Using cached metadata for %s", url)
        metadata = json.loads(cached.read_text(encoding="utf-8"))
    else:
        metadata = await _fetch_metadata(session, url)
        metadata["id"] = id_
        with cached.open("w", encoding="utf-8") as f:
            json.dump(metadata, f)

    return metadata


async def _get_episodes(
    session: aiohttp.ClientSession,
    url: str,
    *,
    sort: bool = True,
) -> dict[str, str]:
    _LOGGER.info("Getting episodes from %s", url)

    ret: dict[str, str] = {}
    if isinstance(html := await _get_text(session, url), HTTPStatus):
        return ret

    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("tr.episode-list-data"):
        number_cell = row.select_one("td.episode-number")
        title_cell = row.select_one("td.episode-title a")

        if not (number_cell and title_cell):
            continue

        episode_number = number_cell.get_text(strip=True)
        episode_title = title_cell.get_text(strip=True)
        ret[episode_number] = episode_title

    if sort:
        ret = dict(
            sorted(ret.items(), key=lambda i: (i[0].isdigit() and int(i[0])) or i[0]),
        )

    return ret


async def scrape_episodes(
    state: State,
    session: aiohttp.ClientSession,
) -> Scraped | None:
    # episode title is already present
    # bail
    if state.get("episode_title") is not None:
        _LOGGER.debug("Episode title already present, skipping scraping")
        return None

    # no url is provided
    if not (url := state.get("url")):
        _LOGGER.debug("No url provided, skipping scraping")
        return None

    if not (episode := str(state.get("episode", ""))):
        _LOGGER.warning("`episode` is missing in state")
        return None

    if not (metadata := await get_metadata(session, url)):
        _LOGGER.debug("Failed to get metadata for %s. Is URL valid?", url)
        return None

    if episode in (episodes := metadata.get("episodes", {})):
        _LOGGER.debug("Using cached episodes for %s", url)
        return metadata

    if episodes:
        # not our first time fetching episodes
        _LOGGER.info("Episode %s seems like a new episode, updating cache", episode)

    if not (episodes_url := metadata.get("episodes_url")):
        return None

    new_episodes = await _get_episodes(session, episodes_url)

    if not new_episodes:
        _LOGGER.error("Caching %s as an invalid URL", url)
    else:
        _LOGGER.info("Scraped %d episodes from %s", len(episodes), episodes_url)

    # this marks the episode as invalid if it
    # doesn't exist after re-hitting the API
    new_episodes.setdefault(episode, "")
    episodes.update(new_episodes)
    if not episodes[episode]:
        _LOGGER.warning(
            "Episode %s isn't found in the most recent scrape, "
            "is the episode valid?",
            episode,
        )

    metadata["episodes"] = episodes
    assert "id" in metadata
    cached = SCRAPING_CACHE_DIR / f"{metadata['id']}.json"
    with cached.open("w", encoding="utf-8") as f:
        _LOGGER.info(
            "Dumping episodes:\n%s to %s",
            pprint.pformat(episodes, indent=4, sort_dicts=False),
            cached,
        )
        json.dump(metadata, f)

    return metadata


async def update_episode_title_in(
    state: State,
    session: aiohttp.ClientSession,
) -> State:
    scraped = await scrape_episodes(state, session)
    # scraping fails, no need to mutate
    if not (scraped and (episodes := scraped.get("episodes"))):
        return state

    if "episode" not in state:
        return state

    if episode_title := episodes.get(str(state["episode"])):
        state["episode_title"] = episode_title

    return state


async def update_missing_metadata_in(
    config: Config,
    session: aiohttp.ClientSession,
) -> list[str]:
    diff: list[str] = []

    missing_metadata = [m for m in ("title", "image_url") if not config.get(m)]

    if not missing_metadata:
        return diff

    if not (scraped := await get_metadata(session, config["url"])):
        return diff

    for m in missing_metadata:
        diff.append(f"{m}={scraped[m]}")
        config[m] = scraped[m]

    return diff
