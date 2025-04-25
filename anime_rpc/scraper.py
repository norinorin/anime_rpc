from __future__ import annotations

import json
import logging
import pprint
import re
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import platformdirs
from bs4 import BeautifulSoup

import anime_rpc

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.states import State

MAL_PATTERN = re.compile(r"https?://myanimelist\.net/anime/(?P<id>\d+)")
CACHE_DIR = Path(platformdirs.user_cache_dir("anime_rpc", anime_rpc.__author__))
_LOGGER = logging.getLogger("scraper")


class PossibleInvalidURLError(Exception):
    """A signal if the URL is invalid (returns 403 or 404).

    The caller should handle this error by caching an empty dict
    so we don't spam calls to this URL.
    """


async def _get_text(session: aiohttp.ClientSession, url: str) -> str | None:
    async with session.get(url) as response:
        if response.status != HTTPStatus.OK:
            _LOGGER.error("Failed to fetch %s. Code: %d", url, response.status)
            if response.status in (
                HTTPStatus.NOT_FOUND,
                HTTPStatus.FORBIDDEN,
                HTTPStatus.METHOD_NOT_ALLOWED,
            ):
                raise PossibleInvalidURLError
            return None

        return await response.text()


async def _get_episodes_url(session: aiohttp.ClientSession, url: str) -> str | None:
    _LOGGER.info("Getting episodes url from %s", url)

    if (html := await _get_text(session, url)) is None:
        return None

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("#horiznav_nav ul li a"):
        if a.string == "Episodes":
            url = str(a["href"])
            _LOGGER.info("Found episodes url: %s", url)
            return str(a["href"])

    return None


async def _get_episodes(
    session: aiohttp.ClientSession,
    url: str,
    *,
    sort: bool = True,
) -> dict[str, str]:
    _LOGGER.info("Getting episodes from %s", url)

    ret: dict[str, str] = {}
    if (html := await _get_text(session, url)) is None:
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

    episodes: dict[str, str] = {}

    try:
        if not (episodes_url := await _get_episodes_url(session, url)):
            return None

        episodes = await _get_episodes(session, episodes_url)
    except PossibleInvalidURLError:
        _LOGGER.error("Caching %s as an invalid URL", url)  # noqa: TRY400
    else:
        _LOGGER.info("Scraped %d episodes from %s", len(episodes), episodes_url)

    with cached.open("w", encoding="utf-8") as f:
        _LOGGER.info(
            "Dumping episodes:\n%s to %s",
            pprint.pformat(episodes, indent=4, sort_dicts=False),
            cached,
        )
        json.dump(episodes, f)

    return episodes


async def update_episode_title_in(
    state: State,
    session: aiohttp.ClientSession,
) -> State:
    episodes = await scrape_episodes(state, session)
    # scraping fails, no need to mutate
    if not episodes:
        return state

    assert "episode" in state
    if episode_title := episodes.get(str(state["episode"])):
        state["episode_title"] = episode_title

    return state
