from enum import IntEnum
from typing import TypedDict


class WatchingState(IntEnum):
    NOT_AVAILABLE = -1
    STOPPED = 0
    PAUSED = 1
    PLAYING = 2


class State(TypedDict, total=False):
    title: str
    episode: int
    episode_title: str
    position: int  # in ms
    duration: int  # in ms
    image_url: str
    url: str
    rewatching: bool
    watching_state: WatchingState


def compare_states(a: State, b: State) -> bool:
    KEYS_TO_IGNORE: tuple[str, ...] = ("position",)
    a = {**a}
    b = {**b}

    for key in KEYS_TO_IGNORE:
        a.pop(key, None)
        b.pop(key, None)

    return a == b
