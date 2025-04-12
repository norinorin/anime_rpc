from __future__ import annotations

import json
import logging
import re
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.states import State

MAL_PATTERN = re.compile(r"https?://myanimelist\.net/anime/(?P<id>\d+)")
CACHE_DIR = Path("~/.cache/anime_rpc").expanduser()

_LOGGER = logging.getLogger("scraper")


async def _get_episodes_url(session: aiohttp.ClientSession, url: str) -> str | None:
    _LOGGER.debug("Getting episodes url from %s", url)
    async with session.get(url) as response:
        if response.status != HTTPStatus.OK:
            _LOGGER.info("Failed to fetch %s. Code: %d", url, response.status)
            return None

        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("#horiznav_nav ul li a"):
            if a.string == "Episodes":
                return str(a["href"])

    return None


async def _get_episodes(session: aiohttp.ClientSession, url: str) -> dict[str, str]:
    _LOGGER.debug("Getting episodes from %s", url)
    ret: dict[str, str] = {}

    async with session.get(url) as response:
        if response.status != HTTPStatus.OK:
            _LOGGER.info("Failed to fetch %s. Code: %d", url, response.status)
            return ret

        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("tr.episode-list-data"):
            number_cell = row.select_one("td.episode-number")
            title_cell = row.select_one("td.episode-title a")

            if not (number_cell and title_cell):
                continue

            episode_number = number_cell.get_text(strip=True)
            episode_title = title_cell.get_text(strip=True)
            ret[episode_number] = episode_title

    return ret


async def scrape_episodes(
    session: aiohttp.ClientSession,
    state: State,
) -> dict[str, str] | None:
    # no url is provided
    if not (url := state.get("url")):
        _LOGGER.debug("No url provided, skipping scraping")
        return None

    if not (match := MAL_PATTERN.match(url)):
        _LOGGER.debug("URL %s does not match MAL pattern", url)
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    id_ = int(match.group("id"))
    if (cached := (CACHE_DIR / f"{id_}.json")).exists():
        # TODO: handle case where the cache is outdated
        # i.e., the user is watching a new episode of an ongoing anime
        _LOGGER.debug("Using cached episodes for %s", url)
        return json.loads(cached.read_text(encoding="utf-8"))

    # episode title is already present
    # bail
    if state.get("episode_title") is not None:
        _LOGGER.debug("Episode title already present, skipping scraping")
        return None

    if not (episodes_url := await _get_episodes_url(session, url)):
        return None

    episodes = await _get_episodes(session, episodes_url)
    _LOGGER.debug("Scraped %d episodes from %s", len(episodes), episodes_url)
    with cached.open("w", encoding="utf-8") as f:
        _LOGGER.debug("Dumping %s to %s", episodes, cached)
        json.dump(episodes, f)

    return episodes


async def update_episode_title_in(
    state: State,
    session: aiohttp.ClientSession,
) -> State:
    episodes = await scrape_episodes(session, state)
    # scraping fails, no need to mutate
    if not episodes:
        return state

    assert "episode" in state
    if episode_title := episodes[str(state["episode"])]:
        state["episode_title"] = episode_title

    return state
