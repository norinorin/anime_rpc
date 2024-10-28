import re
from typing import TypedDict

import aiohttp

from anime_rpc.config import Config
from anime_rpc.states import State, WatchingState

P_TAG_PATTERN = re.compile(r'<p id="(file|filedir|state|position|duration)">(.+)<\/p>')


class Vars(TypedDict):
    file: str
    filedir: str
    state: WatchingState
    position: int
    duration: int


def get_ep_title(pattern: str, file: str) -> tuple[int, str | None] | None:
    if not (match := re.search(pattern, file)):
        return

    groups = match.groupdict()
    ep = groups["ep"]
    title = groups.get("title")
    return int(ep), title.strip() if title else None


def _get_vars_html(html: str) -> Vars:
    ret: Vars = Vars(**{k: v for k, v in P_TAG_PATTERN.findall(html)})
    ret["state"] = WatchingState(int(ret["state"]))
    ret["position"] = int(ret["position"])
    ret["duration"] = int(ret["duration"])
    return ret


async def get_vars(client: aiohttp.ClientSession, port: int = 13579) -> Vars | None:
    try:
        async with client.get(f"http://127.0.0.1:{port}/variables.html") as response:
            if response.status != 200:
                return None

            data = await response.text()
            return _get_vars_html(data)
    except aiohttp.ClientConnectionError:
        return


def get_state(vars: Vars, config: Config) -> State:
    state: State = State()
    state["title"] = config["title"]
    state["rewatching"] = config["rewatching"]
    state["position"] = vars["position"]
    state["duration"] = vars["duration"]
    maybe_ep_title = get_ep_title(config["match"], vars["file"])

    # if nothing matches, return an empty state as to clear the activity
    if not maybe_ep_title:
        return State()

    state["episode"], ep_title = maybe_ep_title

    # the title of the episode is optional
    if ep_title:
        state["episode_title"] = ep_title

    state["image_url"] = config["image_url"]
    state["url"] = config["url"]
    state["watching_state"] = vars["state"]
    return state
