import re
from abc import ABC, abstractmethod
from typing import TypedDict

import aiohttp

from anime_rpc.config import Config
from anime_rpc.states import State, WatchingState


class Vars(TypedDict):
    file: str
    filedir: str
    state: WatchingState
    position: int
    duration: int


class BasePoller(ABC):
    @property
    @abstractmethod
    def origin(self) -> str: ...

    @staticmethod
    @abstractmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None: ...

    @staticmethod
    def get_ep_title(pattern: str, file: str) -> tuple[int, str | None] | None:
        if pattern.lower() == "movie":
            return "Movie", None

        if not (match := re.search(pattern, file)):
            return

        groups = match.groupdict()
        ep = groups["ep"]
        title = groups.get("title")
        return int(ep), title.strip() if title else None

    def get_empty_state(self):
        return State(origin=self.origin)

    def get_state(self, vars: Vars, config: Config) -> State:
        state: State = self.get_empty_state()
        state["title"] = config["title"]
        state["rewatching"] = config["rewatching"]
        state["position"] = vars["position"]
        state["duration"] = vars["duration"]
        maybe_ep_title = self.get_ep_title(config["match"], vars["file"])

        # if nothing matches, return an empty state as to clear the activity
        if not maybe_ep_title:
            return self.get_empty_state()

        state["episode"], ep_title = maybe_ep_title

        # the title of the episode is optional
        if ep_title:
            state["episode_title"] = ep_title

        state["image_url"] = config["image_url"]
        state["url"] = config["url"]
        state["watching_state"] = vars["state"]
        state["application_id"] = config["application_id"]
        state["url_text"] = config["url_text"]
        return state

    @staticmethod
    def get_pollers():
        return {s().origin: s for s in BasePoller.__subclasses__()}
