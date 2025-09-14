from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from pymediainfo import MediaInfo

from anime_rpc.config import validate_config
from anime_rpc.states import State, WatchingState

if TYPE_CHECKING:
    import aiohttp

    from anime_rpc.config import Config


EP_TEMPLATE = ("%ep%", r"(?P<ep>\d+(?:\.\d+)?)")
EP_TITLE_TEMPLATE = ("%title%", r"(?P<title>.+)")
EP_NORMALIZER = re.compile(r"^0+(?=\d)")


class Vars(TypedDict):
    file: str
    filedir: str
    state: WatchingState
    position: int
    duration: int


class BasePoller(ABC):
    default_port = None

    def __init__(self, port: int | None = None) -> None:
        self.port = port if port is not None else self.default_port

    @classmethod
    @abstractmethod
    def origin(cls) -> str: ...

    @abstractmethod
    async def get_vars(self, client: aiohttp.ClientSession) -> Vars | None: ...

    @staticmethod
    def get_ep_title(
        pattern: str,
        file: str,
        filedir: str,
    ) -> tuple[str, str | None] | None:
        if pattern.lower() == "movie":
            return "Movie", None

        pattern = pattern.replace(*EP_TEMPLATE, 1).replace(*EP_TITLE_TEMPLATE, 1)

        for f in (MediaInfo.parse(Path(filedir) / file).general_tracks[0].title, file):
            if f is None:
                continue

            if match := re.search(pattern, f):
                break
        else:
            return None

        groups = match.groupdict()
        ep = groups["ep"]
        title = groups.get("title")
        return EP_NORMALIZER.sub("", ep), title.strip() if title else None

    @classmethod
    def get_empty_state(cls) -> State:
        return State(origin=cls.origin())

    @classmethod
    def get_state(cls, vars_: Vars, config: Config) -> State:
        state: State = cls.get_empty_state()

        if validate_config(config):
            return state

        state["rewatching"] = config["rewatching"]
        state["position"] = vars_["position"]
        state["duration"] = vars_["duration"]
        maybe_ep_title = cls.get_ep_title(
            config["match"],
            vars_["file"],
            vars_["filedir"],
        )

        # if nothing matches, return an empty state as to clear the activity
        if not maybe_ep_title:
            return cls.get_empty_state()

        state["episode"], ep_title = maybe_ep_title

        # the title of the episode is optional
        if ep_title:
            state["episode_title"] = ep_title

        # title and image_url may be scraped later
        if title := config.get("title"):
            state["title"] = title

        if image_url := config.get("image_url"):
            state["image_url"] = image_url

        # url, state, application_id, and url_text have default values
        # which are set during config parsing, this won't raise KeyError
        state["url"] = config["url"]
        state["watching_state"] = vars_["state"]
        state["application_id"] = config["application_id"]
        state["url_text"] = config["url_text"]
        return state

    @staticmethod
    def get_pollers() -> dict[str, type[BasePoller]]:
        return {s.origin(): s for s in BasePoller.__subclasses__()}
