import re
from typing import Any
import time

from anime_rpc.config import Config, APPLICATION_ID
from anime_rpc.mpc import Vars, WatchingState

from discordrpc import RPC  # type: ignore


RPC_CLIENT = RPC(APPLICATION_ID)


def now() -> int:
    return int(time.mktime(time.localtime()))


def get_ep_title(
    pattern: str, file: str, title_fallback: str
) -> tuple[int, str] | None:
    if not (match := re.search(pattern, file)):
        return

    groups = match.groupdict()
    ep = groups["ep"]
    title = groups.get("title", title_fallback)
    return int(ep), title.strip()


def quote(text: str) -> str:
    if text.startswith('"') or text.endswith('"'):
        return text
    return f'"{text}"'


def _maybe_strip_leading_zeros(timestamp: str) -> str:
    parts = timestamp.split(":")
    if not int(parts[0]):
        return ":".join(parts[1:])

    return timestamp


def _compare_states(a: dict[str, Any], b: dict[str, Any]) -> bool:
    KEYS_TO_IGNORE: tuple[str, ...] = ("ts_end", "ts_start")
    a = {**a}
    b = {**b}

    for key in KEYS_TO_IGNORE:
        a.pop(key, None)
        b.pop(key, None)

    return a == b


def clear(state: dict[str, Any]) -> dict[str, Any]:
    if not _compare_states(state, {}):
        RPC_CLIENT.set_activity(act_type=None)  # type: ignore

    return {}


def update_activity(
    vars: Vars | None,
    config: Config | None,
    state: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    if not vars or not config:
        return clear(state)

    kwargs: dict[str, Any] = {
        "large_image": config["image_url"],
        "large_text": f"{'Rewatching '*config['rewatching']}{config['title']}",
        "buttons": [
            {"label": "View Anime", "url": config["url"]},
        ],
        "act_type": 3,
    }

    ep_title = get_ep_title(config["match"], vars["file"], config["title"])
    if not ep_title:
        return clear(state)

    ep: int
    title: str
    ep, title = ep_title
    _now = now()

    if vars["state"] == WatchingState.PLAYING:
        kwargs["details"] = config["title"]
        kwargs["state"] = f"Episode {ep} {quote(title)*(config['title'] != title)}"
        kwargs["ts_start"] = _now - vars["position"] // 1_000
        kwargs["ts_end"] = _now + (vars["duration"] - vars["position"]) // 1_000
        kwargs["small_text"] = "Playing"
        kwargs["small_image"] = "new-playing"
    elif vars["state"] == WatchingState.PAUSED:
        kwargs["details"] = f"Episode {ep} {quote(title)}"
        kwargs["state"] = (
            f"{_maybe_strip_leading_zeros(vars['positionstring'])}/{_maybe_strip_leading_zeros(vars['durationstring'])}"
        )
        kwargs["ts_start"] = _now
        kwargs["small_text"] = "Paused"
        kwargs["small_image"] = "new-paused"
    else:
        return clear(state)

    if not force and _compare_states(kwargs, state):
        return state

    RPC_CLIENT.set_activity(**kwargs)  # type: ignore
    return kwargs
