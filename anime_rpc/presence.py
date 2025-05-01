from __future__ import annotations

import contextlib
import logging
import struct
import time
from enum import Flag, auto
from typing import Any, TypedDict, cast

from pypresence import (  # type: ignore[reportMissingTypeStubs]
    ActivityType,
    AioPresence,
    DiscordError,
    DiscordNotFound,
    PipeClosed,
    ResponseTimeout,
)
from typing_extensions import Unpack

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import DEFAULT_APPLICATION_ID
from anime_rpc.formatting import ms2timestamp, quote
from anime_rpc.states import (
    State,
    WatchingState,
    compare_states,
)

ORIGIN2SERVICE = {
    "mpc": "MPC-HC",
    "www.bilibili.tv": "BiliBili (Bstation)",
    "mpv-ipc": "mpv",
    "mpv-webui": "mpv",
}
ASSETS = {
    "PLAYING": "https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/assets/play.png?raw=true",
    "PAUSED": "https://raw.githubusercontent.com/norinorin/anime_rpc/refs/heads/main/assets/pause.png?raw=true",
}
_LOGGER = logging.getLogger("presence")


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


class UpdateFlags(Flag):
    SEEKING = auto()
    PERIODIC_UPDATE = auto()


class Presence:
    def __init__(self) -> None:
        self._rpc: AioPresence | None = None
        self._last_application_id: int | None = None
        self._reconnecting = False
        self._last_kwargs: dict[str, Any] = {}

    async def _ensure_application_id(self, application_id: int) -> None:
        if self._rpc is None or application_id != self._last_application_id:
            _ = self._rpc and self._rpc.close()
            self._rpc = AioPresence(
                application_id,
                connection_timeout=5,
                response_timeout=5,
            )
            self._last_application_id = application_id
            data = cast("dict[str, Any]", await self._rpc.handshake())
            user = data["data"]["user"]
            _LOGGER.info(
                "Connected to %s (%s)",
                user.get("username", "unknown"),
                user.get("id", "<unknown id>"),
            )

    async def _update(
        self,
        application_id: int,
        *args: tuple[Any, ...],
        **kwargs: Unpack[ActivityOptions],
    ) -> bool:
        try:
            await self._ensure_application_id(application_id)
            assert self._rpc is not None
            await self._rpc.update(*args, **kwargs)  # type: ignore[reportCallIssue]
        except (
            OSError,
            ConnectionRefusedError,
            PipeClosed,
            ResponseTimeout,
            struct.error,
            DiscordError,
            DiscordNotFound,
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
            self._rpc = None
            self._reconnecting = True
            return False

        self._reconnecting = False
        return True

    async def _clear(self, last_state: State) -> State:
        # only clear activity if last state is not empty
        if last_state and self._rpc:
            _LOGGER.info("Clearing presence...")
            # we don't care if clearing fails
            with contextlib.suppress(
                OSError,
                ConnectionRefusedError,
                PipeClosed,
                ResponseTimeout,
                struct.error,
                DiscordError,
            ):
                await self._rpc.clear()

        return State()

    @staticmethod
    def _now() -> int:
        return int(time.mktime(time.localtime()))

    def _get_large_text(self, **kwargs: Unpack[StateOptions]) -> str:
        watching_state = kwargs["watching_state"]
        ep_title = kwargs["ep_title"]
        rewatching = kwargs["rewatching"]
        title = kwargs["title"]
        origin = kwargs["origin"]
        show_title_in_large_text = (
            watching_state == WatchingState.PAUSED and ep_title is not None
        )
        return (
            f"{('re' * rewatching + 'watching').title()} "
            f"{(quote(title)+' ') * show_title_in_large_text}"
            f"on {ORIGIN2SERVICE.get(origin, origin)}"
        )

    def _get_playing_state_kwargs(
        self,
        **kwargs: Unpack[StateOptions],
    ) -> ActivityOptions:
        title = kwargs["title"]
        now = kwargs["now"]
        pos = kwargs["position"]
        dur = kwargs["duration"]
        ep = kwargs["episode"]
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
                "details": title,
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
        ep_title = kwargs["ep_title"]
        details = (
            title
            if is_movie
            else (f"E{ep} {quote(ep_title)}" if ep_title else f"{quote(title)} E{ep}")
        )
        return cast(
            "ActivityOptions",
            {
                "details": details,
                "state": "Paused - "
                + " / ".join([ms2timestamp(i) for i in (pos, dur)]),
                "small_text": "Paused",
                "small_image": ASSETS["PAUSED"],
            },
        )

    async def update(
        self,
        state: State,
        last_state: State,
        origin: str,
        *,
        flags: UpdateFlags | None = None,
    ) -> State:
        if not state:
            return await self._clear(last_state)

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
        }

        kwargs: dict[str, Any] = {
            "large_text": self._get_large_text(**state_opts),
            "activity_type": 3,
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
            return await self._clear(last_state)

        # only compare states after validating watching state
        if compare_states(state, last_state):
            # if the two are the same
            # ignore update request unless flags are set
            if flags is None:
                return state

            if UpdateFlags.PERIODIC_UPDATE in flags:
                # if it's a periodic update just use the previous kwargs
                # as to prevent the rich presence time to get bugged
                # for a split second
                _LOGGER.debug(
                    "Periodic update triggered, reusing the previous kwargs...",
                )
                kwargs = self._last_kwargs

        _LOGGER.debug(
            "Setting presence to [%s] %s @ %s",
            watching_state.name,
            f"{state['title']}"
            + f" E{state['episode']}" * (not state_opts["is_movie"]),
            ms2timestamp(state["position"]),
        )

        self._last_kwargs = kwargs

        # only log on state changes or seeking
        if await self._update(application_id, **kwargs) and not (
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
