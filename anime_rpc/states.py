from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from typing import Generator  # noqa: UP035

_LOGGER = logging.getLogger("states")


class WatchingState(IntEnum):
    NOT_AVAILABLE = -1
    STOPPED = 0
    PAUSED = 1
    PLAYING = 2


class State(TypedDict, total=False):
    title: str
    episode: int | str  # str for "Movie"
    episode_title: str
    position: int  # in ms
    duration: int  # in ms
    image_url: str
    url: str
    url_text: str
    rewatching: bool
    watching_state: WatchingState

    # keep setting 'origin' to the current active source
    # so that no other source can take control (mpc feeds states every 1 second)
    # we don't want our web rpc to be cleared because mpc isn't playing
    origin: str

    # allow str for browser extensions (js)
    application_id: int | str


_KEYS_TO_IGNORE_CMP: tuple[str, ...] = ("position", "origin")
_KEYS_TO_IGNORE_LOG: tuple[str, ...] = ("position", "duration")


def compare_states(a: State, b: State) -> bool:
    a = {**a}
    b = {**b}

    for key in _KEYS_TO_IGNORE_CMP:
        a.pop(key, None)
        b.pop(key, None)

    return a == b


def states_logger(*, verbose: bool = False) -> Generator[None, State, None]:
    last_state: State = State()

    while 1:
        state = yield
        state = State(**state)

        if not verbose:
            for key in _KEYS_TO_IGNORE_LOG:
                state.pop(key, None)

            if not state:
                continue

        if state != last_state or verbose:
            _LOGGER.debug("Received state: %s", state)

        last_state = state
