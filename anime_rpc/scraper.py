from __future__ import annotations

import asyncio
import json
import logging
import pprint
import re
from abc import ABC, abstractmethod
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, TypedDict

from bs4 import BeautifulSoup

from anime_rpc.cache import SCRAPING_CACHE_DIR
from anime_rpc.file_watcher import FileWatcherManager, Subscription

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.config import Config
    from anime_rpc.states import State

_LOGGER = logging.getLogger("scraper")


class Scraped(TypedDict, total=False):
    id: str
    episodes: dict[str, str]
    title: str
    image_url: str
    episodes_url: str
    last_updated: int


class BaseScraper(ABC):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    def get_cache_path(self, id_: str | None = None) -> Path:
        cache_dir = SCRAPING_CACHE_DIR / self.subdir
        if id_ is not None:
            return cache_dir / f"{id_}.json"
        return cache_dir

    @property
    @abstractmethod
    def subdir(self) -> str: ...

    @abstractmethod
    async def get_episodes(self, url: str, episode: str) -> dict[str, str]: ...

    @abstractmethod
    async def get_metadata(self, url: str) -> Scraped: ...

    @classmethod
    @abstractmethod
    def extract_id(cls, url: str) -> str | None: ...

    async def update_episode_title_in(
        self,
        state: State,
    ) -> State:
        if state.get("episode_title") is not None:
            return state

        if not (url := state.get("url")):
            return state

        if not (episode := str(state.get("episode", ""))):
            return state

        if not (episodes := await self.get_episodes(url, episode)):
            return state

        if episode_title := episodes.get(episode):
            state["episode_title"] = episode_title

        return state

    async def update_missing_metadata_in(
        self,
        config: Config,
    ) -> list[str]:
        diff: list[str] = []

        missing_metadata = [m for m in ("title", "image_url") if not config.get(m)]

        if not missing_metadata:
            return diff

        if not (scraped := await self.get_metadata(config["url"])):
            return diff

        for m in missing_metadata:
            if m not in scraped:
                continue
            diff.append(f"{m}={scraped[m]}")
            config[m] = scraped[m]

        return diff

    async def _get_text(self, url: str) -> str | HTTPStatus:
        async with self.session.get(url) as response:
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


class _CachingScraper(BaseScraper):
    def __init__(
        self, session: aiohttp.ClientSession, file_watcher_manager: FileWatcherManager
    ) -> None:
        super().__init__(session)

        self.file_watcher_manager = file_watcher_manager
        self._last_queried: tuple[str, Scraped | None] | None = None
        self._subscription: Subscription[Scraped] | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._event = asyncio.Event()

    @abstractmethod
    async def fetch_episodes(self, url: str, episode: str) -> dict[str, str]: ...

    @abstractmethod
    async def fetch_metadata(self, url: str) -> Scraped: ...

    async def _consume_queue(
        self, id_: str, queue: asyncio.Queue[Scraped | None]
    ) -> None:
        _LOGGER.debug("Starting consumer for %s", id_)
        while 1:
            self._last_queried = (id_, await queue.get())
            self._event.set()

    async def subscribe(self, id_: str, path: Path) -> None:
        if self._last_queried and self._last_queried[0] == id_:
            return None

        if self._subscription:
            self.file_watcher_manager.unsubscribe(self._subscription)

        if self._consumer_task:
            _LOGGER.debug("Cancelling consumer task for %S", id_)
            self._consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._consumer_task

        path.parent.mkdir(parents=True, exist_ok=True)
        self._event.clear()
        self._subscription = self.file_watcher_manager.subscribe(path, json.load)
        self._consumer_task = asyncio.create_task(
            self._consume_queue(id_, self._subscription.queue)
        )
        await self._event.wait()

    @property
    def last_queried(self) -> Scraped | None:
        return self._last_queried[1] if self._last_queried else None

    async def get_metadata(self: "_CachingScraper", url: str) -> Scraped:
        if not (id_ := self.extract_id(url)):
            return Scraped()

        path = self.get_cache_path(id_)
        task = asyncio.create_task(self.subscribe(id_, path))

        # with caching, we make a distinction between None and an empty Scraped()
        # None means the file doesn't exist, and an empty Scraped() means the
        # scraping fails and we've marked the url as invalid
        if path.exists():
            await task  # wait until we get the intial value
            if self.last_queried is not None:
                return self.last_queried

        _LOGGER.info("[API CALL] Fetching metadata from %s", url)
        metadata = await self.fetch_metadata(url)
        metadata["id"] = id_
        with path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f)
        return metadata

    async def get_episodes(
        self: "_CachingScraper", url: str, episode: str
    ) -> dict[str, str]:
        if not (metadata := await self.get_metadata(url)):
            _LOGGER.debug("Failed to get metadata for %s. Is URL valid?", url)
            return {}

        if episode in (episodes := metadata.get("episodes", {})):
            return episodes

        if episodes:
            # not our first time fetching episodes
            _LOGGER.info("Episode %s seems like a new episode, updating cache", episode)

        if not (episodes_url := metadata.get("episodes_url")):
            return {}

        # time to hit the api
        _LOGGER.info("[API CALL] Fetching episodes from %s", episodes_url)
        new_episodes = await self.fetch_episodes(url, episode)
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
        path = self.get_cache_path(metadata["id"])
        with path.open("w", encoding="utf-8") as f:
            _LOGGER.info(
                "Dumping episodes:\n%s to %s",
                pprint.pformat(episodes, indent=4, sort_dicts=False),
                path,
            )
            json.dump(metadata, f)
        return episodes


class MALScraper(_CachingScraper):
    ID_PATTERN = re.compile(r"https?://myanimelist\.net/anime/(?P<id>\d+)")

    @property
    def subdir(self) -> str:
        return "mal/"

    @classmethod
    def extract_id(cls, url: str) -> str | None:
        if not (match := cls.ID_PATTERN.match(url)):
            _LOGGER.debug("URL doesn't match MAL pattern: %s", url)
            return None

        return match.group("id")

    async def fetch_metadata(self, url: str) -> Scraped:
        _LOGGER.info("Fetching metadata from %s", url)

        ret = Scraped()

        if isinstance(html := await self._get_text(url), HTTPStatus):
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

    async def fetch_episodes(self, url: str, episode: str) -> dict[str, str]:
        # _CachingScraper handles the metadata fetching and caching
        # at this point, the cache should have the episodes_url
        assert self.last_queried and "episodes_url" in self.last_queried
        episode_url = self.last_queried["episodes_url"]

        ret: dict[str, str] = {}
        if isinstance(html := await self._get_text(episode_url), HTTPStatus):
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

        ret = dict(
            sorted(ret.items(), key=lambda i: (i[0].isdigit() and int(i[0])) or i[0]),
        )
        return ret
