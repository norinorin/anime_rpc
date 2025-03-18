import asyncio
import time
from typing import Any

# TODO: async pipes
from discordrpc import RPC  # type: ignore

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import DEFAULT_APPLICATION_ID
from anime_rpc.formatting import ms2timestamp, quote
from anime_rpc.states import WatchingState  # type: ignore
from anime_rpc.states import State, compare_states

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


async def _ensure_application_id(application_id: int):
    global rpc_client, last_application_id

    if rpc_client is None or application_id != last_application_id:
        rpc_client = RPC(application_id)
        last_application_id = application_id


async def _set_activity(application_id: int, *args: Any, **kwargs: Any):
    global rpc_client

    while 1:
        try:
            await _ensure_application_id(application_id)
            # bad stubs, just type ignore it
            return rpc_client.set_activity(*args, **kwargs)  # type: ignore
        except (OSError, ConnectionRefusedError):
            # discord is probably closed/restarted
            # reconnect in 30 seconds
            print("Disconnected, reconnecting in 30 seconds...")
            await asyncio.sleep(30)
            rpc_client = None
            continue


def now() -> int:
    return int(time.mktime(time.localtime()))


async def clear(application_id: int, last_state: State) -> State:
    # only clear activity if last state is not empty
    if last_state:
        await _set_activity(application_id, act_type=None)  # type: ignore

    return State()


# async interface
# but pipes are still sync
async def update_activity(
    state: State,
    last_state: State,
    origin: str,
    force: bool = False,
) -> State:
    application_id = int(state.get("application_id", DEFAULT_APPLICATION_ID))

    if not state:
        return await clear(application_id, last_state)

    assert "title" in state
    title = state["title"]
    kwargs: dict[str, Any] = {
        "large_text": f"{('re' * state.get('rewatching', 0) + 'watching').title()} on {ORIGIN2SERVICE.get(origin, origin)}",
        "act_type": 3,
    }

    if image_url := state.get("image_url"):
        kwargs["large_image"] = image_url

    if url := state.get("url"):
        kwargs["buttons"] = [
            {"label": state.get("url_text") or "View Anime", "url": url}
        ]

    assert "episode" in state
    assert "position" in state
    assert "duration" in state

    _now = now()
    watching_state = state.get("watching_state", WatchingState.NOT_AVAILABLE)
    ep = state["episode"]
    ep_title = state.get("episode_title")
    pos = state["position"]
    dur = state["duration"]
    is_movie = ep == "Movie"

    if watching_state == WatchingState.PLAYING:
        kwargs["details"] = state["title"]
        kwargs["state"] = (
            f"{'Episode ' * (not is_movie)}{ep} {quote(ep_title) if ep_title else ''}"
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
        kwargs["state"] = "/".join([ms2timestamp(i) for i in (pos, dur)])
        kwargs["ts_start"] = _now
        kwargs["small_text"] = "Paused"
        kwargs["small_image"] = ASSETS["PAUSED"]
    else:
        return await clear(application_id, last_state)

    # only compare states after validating watching state
    if not force and compare_states(state, last_state):
        return state

    await _set_activity(application_id, **kwargs)  # type: ignore
    return state
