import logging
from enum import IntEnum
from typing import Generator, TypedDict

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

    # keep setting 'origin' to the current active source so that no other source can take control (mpc feeds states every 1 second)
    # we don't want our web rpc to be cleared because mpc isn't playing
    origin: str

    # allow str for browser extensions (js)
    application_id: int | str


def compare_states(a: State, b: State) -> bool:
    KEYS_TO_IGNORE: tuple[str, ...] = ("position", "origin")
    a = {**a}
    b = {**b}

    for key in KEYS_TO_IGNORE:
        a.pop(key, None)
        b.pop(key, None)

    return a == b


def states_logger(verbose: bool = False) -> Generator[None, State, None]:
    last_state: State = State()
    KEYS_TO_IGNORE = ("position", "duration")

    while 1:
        state = yield
        state = State(**state)

        if not verbose:
            for key in KEYS_TO_IGNORE:
                state.pop(key, None)

            if not state:
                continue

        if state != last_state or verbose:
            _LOGGER.debug("Received state: %s", state)

        last_state = state
