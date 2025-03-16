import asyncio
import signal
from contextlib import suppress

import aiohttp

import anime_rpc.monkey_patch  # type: ignore
from anime_rpc.asyncio_helper import Bail, wait
from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import Config, read_rpc_config
from anime_rpc.formatting import ms2timestamp
from anime_rpc.pollers import BasePoller, Vars
from anime_rpc.presence import update_activity
from anime_rpc.states import State, states_logger
from anime_rpc.webserver import get_app, start_app

TIME_DISCREPANCY_TOLERANCE_MS = 3_000  # 3 seconds
MPC_POLLING_INTERVAL = 1.0  # fetch vars every 1 second


async def poll_player(
    poller: BasePoller, event: asyncio.Event, queue: asyncio.Queue[State]
):
    async with aiohttp.ClientSession() as session:
        config: Config | None = None

        while not event.is_set():
            state: State = poller.get_empty_state()
            vars: Vars | None
            try:
                if (vars := await wait(poller.get_vars(session), event)) and (
                    config := read_rpc_config(vars["filedir"], last_config=config)
                ):
                    state = poller.get_state(vars, config)
            except Bail:
                return

            await queue.put(state)

            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(event.wait(), timeout=MPC_POLLING_INTERVAL)


async def consumer_loop(event: asyncio.Event, queue: asyncio.Queue[State]):
    last_state: State = {}
    last_pos: int = 0
    last_origin: str = ""
    logger = states_logger()
    next(logger)

    while not event.is_set():
        try:
            state = await wait(queue.get(), event)
        except Bail:
            return

        # state fed should always contain origin
        if "origin" not in state:
            continue

        origin = state.pop("origin")

        # since mpc polls every second and may return empty states
        # make it so that an origin can only occupy the rich presence if state is not empty
        # this will allow other origins to be active while mpc is returning empty states
        if state and not last_origin:
            last_origin = origin

        # rich presence is occupied
        # ignore current state
        if last_origin != origin:
            continue

        logger.send(state)

        # only force update if the position seems off (seeking)
        pos: int = state.get("position", 0)

        if seeking := abs(pos - last_pos) > TIME_DISCREPANCY_TOLERANCE_MS:
            print("Seeked from", ms2timestamp(last_pos), "to", ms2timestamp(pos))

        last_state = await update_activity(
            state,
            last_state,
            origin,
            seeking,
        )

        # if last_state is empty
        # it's given up control
        if not last_state:
            last_origin = ""
        last_pos = pos


async def main():
    queue: asyncio.Queue[State] = asyncio.Queue()
    event = asyncio.Event()
    signal.signal(signal.SIGINT, lambda *_: _sigint_callback(event))  # type: ignore

    consumer_task = asyncio.create_task(consumer_loop(event, queue), name="consumer")

    print("Pollers used:", [i.origin for i in CLI_ARGS.pollers])
    poller_tasks = [
        asyncio.create_task(
            poll_player(poller, event, queue), name=poller.__class__.__name__
        )
        for poller in CLI_ARGS.pollers
    ]

    print("Waiting for activity feed updates...")

    webserver = None
    if not CLI_ARGS.no_webserver:
        app = await get_app(queue)
        webserver = await start_app(app)

    await asyncio.gather(consumer_task, *poller_tasks)

    if webserver is not None:
        await webserver.stop()


def _sigint_callback(event: asyncio.Event):
    print("Received CTRL+C")
    asyncio.get_running_loop().call_soon_threadsafe(lambda: event.set())


asyncio.run(main())
