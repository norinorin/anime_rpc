from enum import IntEnum
from http.client import CannotSendRequest, HTTPConnection
import re
from typing import TypedDict

P_TAG_PATTERN = re.compile(
    r'<p id="(file|filedir|state|position|duration|positionstring|durationstring)">(.+)<\/p>'
)


class WatchingState(IntEnum):
    NOT_AVAILABLE = -1
    STOPPED = 0
    PAUSED = 1
    PLAYING = 2


class Vars(TypedDict):
    file: str
    filedir: str
    state: WatchingState
    position: int
    duration: int
    positionstring: str
    durationstring: str


def _get_vars_html(html: str) -> Vars:
    ret: Vars = Vars(**{k: v for k, v in P_TAG_PATTERN.findall(html)})
    ret["state"] = WatchingState(int(ret["state"]))
    ret["position"] = int(ret["position"])
    ret["duration"] = int(ret["duration"])
    return ret


def get_vars(port: int = 13579) -> Vars | None:
    try:
        conn = HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/variables.html")
        response = conn.getresponse()
    except (ConnectionRefusedError, CannotSendRequest):
        return None

    if response.status != 200:
        return None

    data = response.read().decode()
    return _get_vars_html(data)
