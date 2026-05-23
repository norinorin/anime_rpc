from __future__ import annotations

import asyncio
from enum import StrEnum, auto
import json
import logging
import pprint
import re
from abc import ABC, abstractmethod
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from time import time
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Literal,
    TypeVar,
    TypedDict,
    Unpack,
)

from aiohttp import ClientResponse
from bs4 import BeautifulSoup

from anime_rpc.cache import METADATA_CACHE_DIR
from anime_rpc.file_watcher import FileWatcherManager, Subscription

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.states import State

_LOGGER = logging.getLogger("metadata_provider")
T = TypeVar("T")


# TODO: decouple MAL and AL-specific fields
class Metadata(TypedDict, total=False):
    """This class is used internally on Python side."""

    id: str
    mal_id: str
    episodes: dict[str, str]
    title: str
    image_url: str
    episodes_url: str
    last_updated: int


class MediaFormat(StrEnum):
    TV = auto()
    MOVIE = auto()
    OVA = auto()
    ONA = auto()
    SPECIAL = auto()


class AiringStatus(StrEnum):
    FINISHED = auto()
    RELEASING = auto()
    TBA = auto()


class SearchResult(TypedDict):
    """This class is used externally on Rust side."""

    id: str
    title: str
    url: str
    image_url: str
    year: int | None
    media_format: MediaFormat | None
    status: AiringStatus | None
    # on a scale of 1000; we preserve 2 floating points
    score: int | None


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> list[SearchResult] | HTTPStatus: ...


class _RequestOptions(TypedDict, total=False):
    json: dict[str, Any]


class HTTPMixin:
    def __init__(self, session: aiohttp.ClientSession, **kwargs: Any) -> None:
        self.session = session
        super().__init__(**kwargs)

    async def _make_request(
        self,
        method: Literal["GET", "POST"],
        url: str,
        parser: Callable[[ClientResponse], Awaitable[T]],
        **kwargs: Unpack[_RequestOptions],
    ) -> T | HTTPStatus:
        async with self.session.request(method, url, **kwargs) as response:
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

            return await parser(response)

    async def _get_text(self, url: str) -> str | HTTPStatus:
        response_or_status = await self._make_request("GET", url, lambda r: r.text())
        if isinstance(response_or_status, HTTPStatus):
            return response_or_status
        return response_or_status

    async def _get_json(
        self, url: str, json_type: Callable[[Any], T]
    ) -> T | HTTPStatus:
        response_or_status = await self._make_request("GET", url, lambda r: r.json())
        if isinstance(response_or_status, HTTPStatus):
            return response_or_status
        return json_type(response_or_status)

    async def _post_json(
        self, url: str, payload: dict[str, Any], json_type: Callable[[Any], T]
    ) -> T | HTTPStatus:
        response_or_status = await self._make_request(
            "POST", url, lambda r: r.json(), json=payload
        )
        if isinstance(response_or_status, HTTPStatus):
            return response_or_status
        return json_type(response_or_status)


class BaseMetadataProvider(HTTPMixin, ABC):
    def get_cache_path(self, id_: str | None = None) -> Path:
        cache_dir = METADATA_CACHE_DIR / self.name
        if id_ is not None:
            return cache_dir / f"{id_}.json"
        return cache_dir

    @property
    @abstractmethod
    def name(self) -> str: ...

    @classmethod
    @abstractmethod
    def get_id_pattern(cls) -> re.Pattern[str]: ...

    @abstractmethod
    async def get_episodes(self, url: str, episode: str) -> dict[str, str]: ...

    @abstractmethod
    async def get_metadata(self, url: str) -> Metadata: ...

    @classmethod
    def extract_id(cls, url: str) -> str | None:
        if not (match := cls.get_id_pattern().match(url)):
            _LOGGER.debug("URL doesn't match %s pattern: %s", cls.__name__, url)
            return None

        return match.group("id")

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
        state: State,
    ) -> State:
        missing_metadata = [m for m in ("title", "image_url") if not state.get(m)]

        if not missing_metadata:
            return state

        if not (scraped := await self.get_metadata(state.get("url", ""))):
            return state

        for m in missing_metadata:
            if m not in scraped:
                continue
            state[m] = scraped[m]

        return state


class _CachingMetadataProvider(BaseMetadataProvider):
    def __init__(
        self, session: aiohttp.ClientSession, file_watcher_manager: FileWatcherManager
    ) -> None:
        super().__init__(session)

        self.file_watcher_manager = file_watcher_manager
        self._last_queried: tuple[str, Metadata | None] | None = None
        self._subscription: Subscription[Metadata] | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._cache_ready_event = asyncio.Event()

    @abstractmethod
    async def _fetch_episodes(
        self, id_: str, url: str, episode: str
    ) -> dict[str, str]: ...

    @abstractmethod
    async def _fetch_metadata(self, id_: str, url: str) -> Metadata: ...

    async def _consume_queue(
        self, id_: str, queue: asyncio.Queue[Metadata | None]
    ) -> None:
        _LOGGER.debug("Starting consumer for %s", id_)
        while 1:
            item = await queue.get()
            self._last_queried = (id_, item)
            (
                self._cache_ready_event.clear()
                if item is None
                else self._cache_ready_event.set()
            )

    async def subscribe(self, id_: str, path: Path) -> None:
        if self._last_queried and self._last_queried[0] == id_:
            return None

        if self._subscription:
            self.file_watcher_manager.unsubscribe(self._subscription)

        if self._consumer_task:
            _LOGGER.debug("Cancelling consumer task %r", self._consumer_task.get_name())
            self._consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._consumer_task

        path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_ready_event.clear()
        self._subscription = self.file_watcher_manager.subscribe(path, json.load)
        self._consumer_task = asyncio.create_task(
            self._consume_queue(id_, self._subscription.queue),
            name=f"consume-{id_}.json",
        )
        _LOGGER.debug("Spawning new consumer task %s", self._consumer_task.get_name())
        await self.wait_for_cache_ready()

    async def wait_for_cache_ready(self) -> None:
        await self._cache_ready_event.wait()

    @property
    def last_queried(self) -> Metadata | None:
        return self._last_queried[1] if self._last_queried else None

    async def get_metadata(self: "_CachingMetadataProvider", url: str) -> Metadata:
        if not (id_ := self.extract_id(url)):
            return Metadata()

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
        metadata = await self._fetch_metadata(id_, url)
        metadata["id"] = id_

        # always clear event before writing so we
        # can wait for the new value to be parsed
        # and passed to the consumer, otherwise
        # we may end up scraping twice
        self._cache_ready_event.clear()
        # FIXME: write in a dedicated thread
        with path.open("w", encoding="utf-8") as f:
            _LOGGER.info(
                "Dumping metadata:\n%s to %s",
                pprint.pformat(metadata, indent=4),
                path,
            )
            json.dump(metadata, f)
        await self.wait_for_cache_ready()
        return metadata

    async def get_episodes(
        self: "_CachingMetadataProvider", url: str, episode: str
    ) -> dict[str, str]:
        if not (metadata := await self.get_metadata(url)):
            _LOGGER.debug("Failed to get metadata for %s. Is URL valid?", url)
            return {}

        if episode in (episodes := metadata.get("episodes", {})):
            return episodes

        if episodes:
            # not our first time fetching episodes
            _LOGGER.info(
                "Episode %s seems to be a new episode, updating cache", episode
            )

        if not (episodes_url := metadata.get("episodes_url")):
            return {}

        # time to hit the api
        _LOGGER.info("[API CALL] Fetching episodes from %s", episodes_url)
        assert "id" in metadata
        new_episodes = await self._fetch_episodes(metadata["id"], url, episode)
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

        metadata["episodes"] = dict(
            sorted(
                episodes.items(),
                key=lambda i: (0, int(i[0])) if i[0].isdigit() else (1, i[0]),
            ),
        )
        assert "id" in metadata
        path = self.get_cache_path(metadata["id"])
        self._cache_ready_event.clear()
        # FIXME: write in a dedicated thread
        with path.open("w", encoding="utf-8") as f:
            _LOGGER.info(
                "Dumping episodes:\n%s to %s",
                pprint.pformat(episodes, indent=4, sort_dicts=False),
                path,
            )
            json.dump(metadata, f)
        await self.wait_for_cache_ready()
        return episodes


class MALMetadataProvider(_CachingMetadataProvider, SearchProvider):
    ID_PATTERN = re.compile(r"https?://myanimelist\.net/anime/(?P<id>\d+)")
    MEDIA_TYPE_MAPPING = {
        "TV": MediaFormat.TV,
        "Movie": MediaFormat.MOVIE,
        "OVA": MediaFormat.OVA,
        "ONA": MediaFormat.ONA,
        "Special": MediaFormat.SPECIAL,
    }
    AIRING_STATUS_MAPPING = {
        "Finished Airing": AiringStatus.FINISHED,
        "Currently Airing": AiringStatus.RELEASING,
        "Not yet aired": AiringStatus.TBA,
    }

    @property
    def name(self) -> str:
        return "myanimelist"

    @classmethod
    def get_id_pattern(cls):
        return cls.ID_PATTERN

    async def _fetch_metadata(self, id_: str, url: str) -> Metadata:
        ret = Metadata()

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

    async def _fetch_episodes(self, id_: str, url: str, episode: str) -> dict[str, str]:
        # _CachingScraper handles the metadata fetching and caching
        # at this point, the cache should have the episodes_url
        await self.wait_for_cache_ready()
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

        return ret

    async def search(self, query: str) -> list[SearchResult] | HTTPStatus:
        url = f"https://myanimelist.net/search/prefix.json?type=anime&keyword={query}"

        data = await self._get_json(url, dict[str, Any])
        if isinstance(data, HTTPStatus):
            return data

        items = data.get("categories", [{}])[0].get("items", [])
        return [
            SearchResult(
                id=id,
                title=title,
                url=url,
                image_url=image_url,
                year=int(payload.get("start_year", 0)) or None,
                score=int(float(score) * 100)
                if (score := payload.get("score")) and score != "N/A"
                else None,
                media_format=self.MEDIA_TYPE_MAPPING.get(
                    payload.get("media_type"), None
                ),
                status=self.AIRING_STATUS_MAPPING.get(payload.get("status"), None),
            )
            for item in items
            if (id := str(item.get("id")),)
            and (title := item.get("name"),)
            and (url := item.get("url"),)
            and (image_url := item.get("image_url"),)
            and (payload := item.get("payload", {0: 0}))
        ]


class AniListMetadataProvider(_CachingMetadataProvider, SearchProvider):
    ID_PATTERN = re.compile(r"https?://anilist\.co/anime/(?P<id>\d+)")
    API_URL = "https://graphql.anilist.co"
    MEDIA_TYPE_MAPPING = {
        "TV": MediaFormat.TV,
        # should this be added as a separate field?
        "TV_SHORT": MediaFormat.TV,
        "MOVIE": MediaFormat.MOVIE,
        "SPECIAL": MediaFormat.SPECIAL,
        "OVA": MediaFormat.OVA,
        "ONA": MediaFormat.ONA,
    }
    AIRING_STATUS_MAPPING = {
        "FINISHED": AiringStatus.FINISHED,
        "RELEASING": AiringStatus.RELEASING,
        "NOT_YET_RELEASED": AiringStatus.TBA,
    }

    @property
    def name(self) -> str:
        return "anilist"

    @classmethod
    def get_id_pattern(cls):
        return cls.ID_PATTERN

    async def _fetch_metadata(self, id_: str, url: str) -> Metadata:
        ret = Metadata()

        # TODO: cli option --preferred-lang
        gql_query = """
          query ($id: Int) {
              Media(id: $id, type: ANIME) {
                  idMal
                  title { romaji }
                  coverImage { extraLarge }
              }
          }  
        """
        payload = {"query": gql_query, "variables": {"id": int(id_)}}
        data = await self._post_json(self.API_URL, payload, dict)

        if isinstance(data, HTTPStatus):
            return ret

        media = data.get("data", {}).get("Media")
        if not media:
            return ret

        if title := media.get("title", {}).get("romaji"):
            ret["title"] = title

        if image_url := media.get("coverImage", {}).get("extraLarge"):
            ret["image_url"] = image_url

        if mal_id := media.get("idMal"):
            ret["mal_id"] = mal_id

        ret["last_updated"] = int(time() * 1000)
        return ret

    async def _fetch_episodes(self, id_: str, url: str, episode: str) -> dict[str, str]:
        # TODO: delegate to MALMetadataProvider using malID
        return {}

    async def search(self, query: str) -> list[SearchResult] | HTTPStatus:
        gql_query = """
          query ($search: String) {
              Page(page: 1, perPage: 10) {
                  media(search: $search, type: ANIME) {
                      id
                      title { romaji }
                      coverImage { extraLarge }
                      format
                      seasonYear
                      status
                      averageScore
                  }
              }
          }  
        """
        payload = {"query": gql_query, "variables": {"search": query}}
        data = await self._post_json(self.API_URL, payload, dict)
        if isinstance(data, HTTPStatus):
            return data

        media_list = data.get("data", {}).get("Page", {}).get("media", [])
        return [
            SearchResult(
                id=id,
                title=title,
                url=url,
                image_url=image_url,
                year=item.get("seasonYear"),
                media_format=self.MEDIA_TYPE_MAPPING.get(item.get("format")),
                status=self.AIRING_STATUS_MAPPING.get(item.get("status")),
                score=int(score) * 10
                if (score := item.get("averageScore")) is not None
                else None,
            )
            for item in media_list
            if (id := str(item.get("id")))
            and (title := item.get("title", {}).get("romaji", ""))
            and (url := f"https://anilist.co/anime/{item.get('id')}")
            and (image_url := item.get("coverImage", {}).get("extraLarge", ""))
        ]
