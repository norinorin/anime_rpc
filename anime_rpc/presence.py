from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
import time
from typing import Any, TypedDict, cast

from pypresence import (  # type: ignore[reportMissingTypeStubs]
    ActivityType,
    AioPresence,
    PipeClosed,
    ResponseTimeout,
)
from typing_extensions import Unpack

from anime_rpc.asyncio_helper import Bail, wait
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


class Presence:
    def __init__(self, event: asyncio.Event) -> None:
        self._rpc: AioPresence | None = None
        self._last_application_id: int | None = None
        self.event = event

    async def _ensure_application_id(self, application_id: int) -> None:
        if self._rpc is None or application_id != self._last_application_id:
            _ = self._rpc and self._rpc.close()
            self._rpc = AioPresence(application_id)
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
    ) -> None:
        i = 0
        try:
            while not self.event.is_set():
                await self._ensure_application_id(application_id)
                assert self._rpc is not None
                await self._rpc.update(*args, **kwargs)  # type: ignore[reportCallIssue]
                return
        except (
            OSError,
            ConnectionRefusedError,
            PipeClosed,
            ResponseTimeout,
            struct.error,
        ):
            # discord is probably closed/restarted
            # try to reconnect
            delay = 5 * i
            _LOGGER.info(
                (
                    "Disconnected, reconnecting..."
                    if i == 0
                    else f"Failed to reconnect, retrying in {delay} seconds..."
                ),
            )
            try:
                await wait(asyncio.sleep(delay), self.event)
            except Bail:
                return
            i = min(i + 1, 6)
            self._rpc = None

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
            ):
                await self._rpc.clear()

        return State()

    @staticmethod
    def _now() -> int:
        return int(time.mktime(time.localtime()))

    async def update(
        self,
        state: State,
        last_state: State,
        origin: str,
        *,
        force: bool = False,
    ) -> State:
        application_id = int(state.get("application_id", DEFAULT_APPLICATION_ID))

        if not state:
            return await self._clear(last_state)

        assert "title" in state
        assert "rewatching" in state
        assert "image_url" in state
        title = state["title"]
        watching_state = state.get("watching_state", WatchingState.NOT_AVAILABLE)
        ep_title = state.get("episode_title")
        show_title_in_large_text = (
            watching_state == WatchingState.PAUSED and ep_title is not None
        )
        kwargs: dict[str, Any] = {
            "large_text": (
                f"{('re' * state['rewatching'] + 'watching').title()} "
                f"{(quote(title)+' ') * show_title_in_large_text}"
                f"on {ORIGIN2SERVICE.get(origin, origin)}"
            ),
            "activity_type": 3,
            "large_image": state["image_url"],
        }

        if (url := state.get("url")) and (url_text := state.get("url_text")):
            assert "url_text" in state
            kwargs["buttons"] = [{"label": url_text, "url": url}]

        assert "episode" in state
        assert "position" in state
        assert "duration" in state

        _now = self._now()
        ep = state["episode"]
        pos = state["position"]
        dur = state["duration"]
        is_movie = ep == "Movie"

        if watching_state == WatchingState.PLAYING:
            kwargs["details"] = state["title"]
            kwargs["state"] = (
                f"{'Episode ' * (not is_movie)}{ep}"
                f" {quote(ep_title) if ep_title else ''}"
            )
            kwargs["start"] = _now - pos // 1_000
            kwargs["end"] = _now + (dur - pos) // 1_000
            kwargs["small_text"] = "Playing"
            kwargs["small_image"] = ASSETS["PLAYING"]
        elif watching_state == WatchingState.PAUSED and not CLI_ARGS.clear_on_pause:
            kwargs["details"] = (
                title
                if is_movie
                else (
                    f"Episode {ep} {quote(ep_title)}"
                    if ep_title
                    else f"{quote(title)} E{ep}"
                )
            )
            kwargs["state"] = "Paused - " + " / ".join(
                [ms2timestamp(i) for i in (pos, dur)],
            )
            kwargs["small_text"] = "Paused"
            kwargs["small_image"] = ASSETS["PAUSED"]
        else:
            return await self._clear(last_state)

        # only compare states after validating watching state
        if not force and compare_states(state, last_state):
            return state

        _LOGGER.info(
            "Setting presence to [%s] %s @ %s",
            watching_state.name,
            f"{state['title']}" + f" E{ep}" * (not is_movie),
            ms2timestamp(state["position"]),
        )
        await self._update(application_id, **kwargs)
        return state
