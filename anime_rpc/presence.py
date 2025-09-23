from __future__ import annotations

import logging
import struct
import time
from enum import Flag, IntEnum, auto
from typing import Any, TypedDict, cast

from typing_extensions import Unpack

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import DEFAULT_APPLICATION_ID
from anime_rpc.formatting import ms2timestamp, quote
from anime_rpc.services import ORIGIN2SERVICE
from anime_rpc.social_sdk import Discord
from anime_rpc.states import State, WatchingState, compare_states

ASSETS = {
    "PLAYING": "https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/assets/play.png?raw=true",
    "PAUSED": "https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/assets/pause.png?raw=true",
}
CHAR_LIMITS = {
    "details": 128,
    "state": 128,
    "large_text": 128,
    "small_text": 128,
    "button_label": 32,
    "button_url": 512,
}
_LOGGER = logging.getLogger("presence")


class ActivityType(IntEnum):
    PLAYING = 0
    STREAMING = 1
    LISTENING = 2
    WATCHING = 3
    CUSTOMSTATUS = 4
    COMPETING = 5
    HANGSTATUS = 6


class StatusDisplayType(IntEnum):
    NAME = 0
    STATE = 1
    DETAILS = 2


class ActivityOptions(TypedDict, total=False):
    activity_type: ActivityType | None
    state: str | None
    details: str | None
    start: int | None
    end: int | None
    large_image: str | None
    large_text: str | None
    buttons: list[dict[str, str]] | None


class StateOptions(TypedDict):
    """Basically validated State."""

    title: str
    episode: int | str
    ep_title: str | None
    position: int
    duration: int
    now: int
    is_movie: bool
    watching_state: WatchingState
    rewatching: bool
    origin: str
    display_name: str


class UpdateFlags(Flag):
    SEEKING = auto()
    PERIODIC_UPDATE = auto()


class Presence:
    def __init__(self, client: Discord) -> None:
        self._client = client
        self._last_kwargs: dict[str, Any] = {}

    def _ensure_application_id(self, application_id: int) -> None:
        self._client.set_application_id(application_id)

    def _update(
        self,
        application_id: int,
        *args: tuple[Any, ...],
        **kwargs: Unpack[ActivityOptions],
    ) -> bool:
        try:
            self._ensure_application_id(application_id)
            self._client.set_activity(*args, **kwargs)  # type: ignore[reportCallIssue]
        except (
            OSError,
            ConnectionRefusedError,
            struct.error,
        ):
            if not self._reconnecting:
                _LOGGER.error(  # noqa: TRY400
                    "Failed to connect to Discord. Is Discord running?",
                )
                if CLI_ARGS.interval < 1:
                    _LOGGER.warning(
                        "--interval is not set or is less than 1 second, "
                        "will only try to reconnect on state changes, "
                        "meaning you have to trigger the state changes "
                        "by play/pausing the media",
                    )
                else:
                    _LOGGER.info(
                        "--interval is set, will retry to reconnect every %.2fs",
                        CLI_ARGS.interval,
                    )
            self._reconnecting = True
            return False

        self._reconnecting = False
        return True

    def _clear(self, last_state: State) -> State:
        # only clear activity if last state is not empty
        if last_state:
            _LOGGER.info("Clearing presence...")
            self._client.clear_activity()
            self._last_kwargs = {}

        return State()

    @staticmethod
    def _now() -> int:
        return int(time.mktime(time.localtime()))

    def _get_large_text(self, **kwargs: Unpack[StateOptions]) -> str:
        rewatching = kwargs["rewatching"]
        display_name = kwargs["display_name"]
        return f"{('re' * rewatching + 'watching').title()} on {display_name}"

    def _get_playing_state_kwargs(
        self,
        **kwargs: Unpack[StateOptions],
    ) -> ActivityOptions:
        title = kwargs["title"]
        now = kwargs["now"]
        pos = kwargs["position"]
        dur = kwargs["duration"]
        ep = kwargs["episode"]
        rewatching = kwargs["rewatching"]
        is_movie = kwargs["is_movie"]
        ep_title = kwargs["ep_title"]
        if is_movie:
            state = "Movie"
        else:
            prefix = "E" if ep_title else "Episode "
            state = f"{prefix}{ep} {quote(ep_title) if ep_title else ''}"
        return cast(
            "ActivityOptions",
            {
                "details": ("Rewatching " * bool(rewatching)) + title,
                "state": state,
                "start": now - pos // 1_000,
                "end": now + (dur - pos) // 1_000,
                "small_text": "Playing",
                "small_image": ASSETS["PLAYING"],
            },
        )

    def _get_paused_state_kwargs(
        self,
        **kwargs: Unpack[StateOptions],
    ) -> ActivityOptions:
        title = kwargs["title"]
        pos = kwargs["position"]
        dur = kwargs["duration"]
        ep = kwargs["episode"]
        is_movie = kwargs["is_movie"]
        state = (
            "Paused"
            + (f" on E{ep}" * (not is_movie))
            + " - "
            + " / ".join(
                [ms2timestamp(i) for i in (pos, dur)],
            )
        )
        return cast(
            "ActivityOptions",
            {
                "details": title,
                "state": state,
                "small_text": "Paused",
                "small_image": ASSETS["PAUSED"],
            },
        )

    def _maybe_trim(self, text: str, max_length: int) -> str:
        if not text:
            return ""

        return len(text) <= max_length and text or text[: max_length - 1] + "…"

    def _trim_kwargs(self, kwargs: dict[str, Any]) -> None:
        _maybe_trim = self._maybe_trim

        for key, limit in CHAR_LIMITS.items():
            if key == "button_label" or key == "button_url":
                continue
            if key in kwargs and isinstance(kwargs[key], str):
                kwargs[key] = _maybe_trim(kwargs[key], limit)

        button_url_limit = CHAR_LIMITS["button_url"]
        button_label_limit = CHAR_LIMITS["button_label"]
        for button in kwargs.get("buttons", []):
            if "label" in button and isinstance(button["label"], str):
                button["label"] = _maybe_trim(button["label"], button_label_limit)
            if "url" in button and isinstance(button["url"], str):
                button["url"] = _maybe_trim(button["url"], button_url_limit)

    def update(
        self,
        state: State,
        last_state: State,
        origin: str,
        *,
        flags: UpdateFlags | None = None,
    ) -> State:
        if not state:
            return self._clear(last_state)

        assert "title" in state
        assert "episode" in state
        assert "position" in state
        assert "duration" in state
        assert "image_url" in state
        assert "rewatching" in state

        application_id = int(state.get("application_id", DEFAULT_APPLICATION_ID))
        watching_state = state.get("watching_state", WatchingState.NOT_AVAILABLE)

        state_opts: StateOptions = {
            "now": self._now(),
            "title": state["title"],
            "episode": state["episode"],
            "ep_title": state.get("episode_title"),
            "position": state["position"],
            "duration": state["duration"],
            "is_movie": state["episode"] == "Movie",
            "rewatching": state["rewatching"],
            "watching_state": state.get("watching_state", WatchingState.NOT_AVAILABLE),
            "origin": origin,
            "display_name": state.get(
                "display_name", ORIGIN2SERVICE.get(origin, origin)
            ),
        }

        kwargs: dict[str, Any] = {
            "large_text": self._get_large_text(**state_opts),
            "type_": 3,
            "status_display_type": StatusDisplayType.DETAILS,
            "large_image": state["image_url"],
        }

        if (url := state.get("url")) and (url_text := state.get("url_text")):
            assert "url_text" in state
            kwargs["buttons"] = [{"label": url_text, "url": url}]

        if watching_state == WatchingState.PLAYING:
            kwargs.update(self._get_playing_state_kwargs(**state_opts))
        elif watching_state == WatchingState.PAUSED and not CLI_ARGS.clear_on_pause:
            kwargs.update(self._get_paused_state_kwargs(**state_opts))
        else:
            return self._clear(last_state)

        self._trim_kwargs(kwargs)

        # only compare states after validating watching state
        if compare_states(state, last_state):
            # if the two are the same
            # ignore update request unless flags are set
            if flags is None:
                return state

            if UpdateFlags.PERIODIC_UPDATE in flags:
                # if it's a periodic update just use the previous kwargs
                # as to prevent the rich presence time from bugging
                # for a split second
                _LOGGER.debug(
                    "Periodic update triggered, reusing the previous kwargs...",
                )
                kwargs = self._last_kwargs

                # discord seems to optimise identical updates away,
                # so we add a trailing space to the `small_text` (it can be any field, though)
                # to trick it into thinking it's not an identical payload
                assert "small_text" in kwargs and isinstance(kwargs["small_text"], str)
                kwargs["small_text"] += " "

        _LOGGER.debug(
            "Setting presence to [%s] %s @ %s",
            watching_state.name,
            f"{state['title']}"
            + f" E{state['episode']}" * (not state_opts["is_movie"]),
            ms2timestamp(state["position"]),
        )

        self._last_kwargs = kwargs

        # only log on state changes or seeking
        if self._update(application_id, **kwargs) and not (
            flags and UpdateFlags.PERIODIC_UPDATE in flags
        ):
            _LOGGER.info(
                "Presence set to [%s] %s @ %s",
                watching_state.name,
                f"{state['title']}"
                + f" E{state['episode']}" * (not state_opts["is_movie"]),
                ms2timestamp(state["position"]),
            )

        return state
