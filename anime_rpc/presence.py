from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, TypedDict

# TODO: async pipes
from discordrpc import RPC  # type: ignore[reportMissingTypeStubs]
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

rpc_client: RPC | None = None
last_application_id: int | None = None
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
    state: str | None
    details: str | None
    act_type: int | None
    ts_start: int | None
    ts_end: int | None
    large_image: str | None
    large_text: str | None
    party_id: str | None
    buttons: list[dict[str, str]] | None


async def _ensure_application_id(application_id: int) -> None:
    global rpc_client, last_application_id  # noqa: PLW0603

    if rpc_client is None or application_id != last_application_id:
        rpc_client = RPC(application_id)
        last_application_id = application_id

        # stupid untyped library, type ignore it
        _LOGGER.info(
            "Connected to %s (%s)",
            rpc_client.User.get("username", "unknown"),  # type: ignore[reportAttributeAccessIssue]
            rpc_client.User.get("id", "<unknown id>"),  # type: ignore[reportAttributeAccessIssue]
        )


async def _set_activity(
    event: asyncio.Event,
    application_id: int,
    *args: tuple[Any, ...],
    **kwargs: Unpack[ActivityOptions],
) -> None:
    global rpc_client  # noqa: PLW0603

    i = 0
    try:
        while 1:
            await _ensure_application_id(application_id)
            # bad stubs, just type ignore it
            return rpc_client.set_activity(*args, **kwargs)  # type: ignore[reportAttributeAccessIssue]
    except (OSError, ConnectionRefusedError):
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
            await wait(asyncio.sleep(delay), event)
        except Bail:
            return None
        i = min(i + 1, 6)
        rpc_client = None

    return None


def now() -> int:
    return int(time.mktime(time.localtime()))


async def clear(
    event: asyncio.Event,
    application_id: int,
    last_state: State,
) -> State:
    # only clear activity if last state is not empty
    if last_state:
        _LOGGER.info("Clearing presence...")
        await _set_activity(event, application_id, act_type=None)

    return State()


# async interface
# but pipes are still sync
async def update_activity(
    event: asyncio.Event,
    state: State,
    last_state: State,
    origin: str,
    *,
    force: bool = False,
) -> State:
    application_id = int(state.get("application_id", DEFAULT_APPLICATION_ID))

    if not state:
        return await clear(event, application_id, last_state)

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
        "act_type": 3,
        "large_image": state["image_url"],
    }

    if (url := state.get("url")) and (url_text := state.get("url_text")):
        assert "url_text" in state
        kwargs["buttons"] = [{"label": url_text, "url": url}]

    assert "episode" in state
    assert "position" in state
    assert "duration" in state

    _now = now()
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
        kwargs["ts_start"] = _now - pos // 1_000
        kwargs["ts_end"] = _now + (dur - pos) // 1_000
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
        return await clear(event, application_id, last_state)

    # only compare states after validating watching state
    if not force and compare_states(state, last_state):
        return state

    _LOGGER.info(
        "Setting presence to [%s] %s @ %s",
        watching_state.name,
        f"{state['title']}" + f" E{ep}" * (not is_movie),
        ms2timestamp(state["position"]),
    )
    await _set_activity(event, application_id, **kwargs)
    return state
