import asyncio
import time
from typing import Any

# TODO: async pipes
from discordrpc import RPC  # type: ignore

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import APPLICATION_ID
from anime_rpc.formatting import ms2timestamp, quote
from anime_rpc.mpc import WatchingState
from anime_rpc.states import State, compare_states  # type: ignore

RPC_CLIENT = RPC(APPLICATION_ID)
ORIGIN2SERVICE = {"mpc": "MPC-HC", "www.bilibili.tv": "BiliBili (Bstation)"}


async def _set_activity(*args, **kwargs):
    global RPC_CLIENT

    while 1:
        try:
            return RPC_CLIENT.set_activity(*args, **kwargs)
        except OSError:
            # discord is probably closed/restarted
            # reconnect in 30 seconds
            print("Disconnected, reconnecting in 30 seconds...")
            await asyncio.sleep(30)
            RPC_CLIENT = RPC(APPLICATION_ID)
            continue


def now() -> int:
    return int(time.mktime(time.localtime()))


async def clear(last_state: State) -> State:
    # only clear activity if last state is not empty
    if last_state:
        await _set_activity(act_type=None)  # type: ignore

    return State()


# async interface
# but pipes are still sync
async def update_activity(
    state: State,
    last_state: State,
    origin: str,
    force: bool = False,
) -> State:
    if not state:
        return await clear(last_state)

    assert "title" in state
    title = state["title"]
    kwargs: dict[str, Any] = {
        "large_text": f"{('re'*state.get('rewatching', 0) + 'watching').title()} on {ORIGIN2SERVICE.get(origin, origin)}",
        "act_type": 3,
    }

    if image_url := state.get("image_url"):
        kwargs["large_image"] = image_url

    if url := state.get("url"):
        kwargs["buttons"] = [{"label": "View Anime", "url": url}]

    assert "episode" in state
    assert "position" in state
    assert "duration" in state

    _now = now()
    watching_state = state.get("watching_state", WatchingState.NOT_AVAILABLE)
    ep = state["episode"]
    ep_title = state.get("episode_title")
    pos = state["position"]
    dur = state["duration"]

    if watching_state == WatchingState.PLAYING:
        kwargs["details"] = state["title"]
        kwargs["state"] = f"Episode {ep} {quote(ep_title) if ep_title else ''}"
        kwargs["ts_start"] = _now - pos // 1_000
        kwargs["ts_end"] = _now + (dur - pos) // 1_000
        kwargs["small_text"] = "Playing"
        kwargs["small_image"] = "new-playing"
    elif watching_state == WatchingState.PAUSED and not CLI_ARGS.clear_on_pause:
        kwargs["details"] = (
            f"Episode {ep} {quote(ep_title)}" if ep_title else f"{quote(title)} E{ep}"
        )
        kwargs["state"] = "/".join([ms2timestamp(i) for i in (pos, dur)])
        kwargs["ts_start"] = _now
        kwargs["small_text"] = "Paused"
        kwargs["small_image"] = "new-paused"
    else:
        return await clear(last_state)

    # only compare states after validating watching state
    if not force and compare_states(state, last_state):
        return state

    await _set_activity(**kwargs)  # type: ignore
    return state
