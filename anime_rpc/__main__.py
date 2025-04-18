import asyncio
import logging
import signal
import sys
from contextlib import suppress

import aiohttp

from anime_rpc.asyncio_helper import Bail, wait
from anime_rpc.cli import CLI_ARGS, print_cli_args
from anime_rpc.config import Config, read_rpc_config
from anime_rpc.formatting import ms2timestamp
from anime_rpc.monkey_patch import patch_pypresence
from anime_rpc.pollers import BasePoller, Vars
from anime_rpc.presence import Presence
from anime_rpc.scraper import update_episode_title_in
from anime_rpc.states import State, states_logger
from anime_rpc.ux import init_logging
from anime_rpc.webserver import get_app, start_app

TIME_DISCREPANCY_TOLERANCE_MS = 3_000  # 3 seconds
POLLING_INTERVAL = 1.0  # fetch vars every 1 second

_LOGGER = logging.getLogger("main")


async def poll_player(
    poller: type[BasePoller],
    event: asyncio.Event,
    queue: asyncio.Queue[State],
    session: aiohttp.ClientSession,
) -> None:
    config: Config | None = None

    while not event.is_set():
        state: State = poller.get_empty_state()
        vars_: Vars | None
        if (vars_ := await wait(poller.get_vars(session), event)) and (
            config := read_rpc_config(
                vars_["filedir"],
                last_config=config,
            )
        ):
            state = poller.get_state(vars_, config)

        await queue.put(state)

        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=POLLING_INTERVAL)


async def consumer_loop(
    event: asyncio.Event, queue: asyncio.Queue[State], session: aiohttp.ClientSession
) -> None:
    presence = Presence(event)
    last_state: State = {}
    last_pos: int = 0
    last_origin: str = ""
    logger = states_logger()
    next(logger)

    while not event.is_set():
        state = await wait(queue.get(), event)

        # state fed should always contain origin
        if "origin" not in state:
            continue

        origin = state.pop("origin")

        # since multiple pollers can be used, one of them may return empty states,
        # which will interrupt an "active" poller, i.e., clear its presence.
        # ensure that exactly only one origin can occupy the rich presence at a time.
        if state and not last_origin:
            last_origin = origin

        # rich presence is occupied
        # ignore current state
        if last_origin != origin:
            continue

        logger.send(state)

        if CLI_ARGS.fetch_episode_titles:
            state = await wait(update_episode_title_in(state, session), event)

        # only force update if the position seems off (seeking)
        pos: int = state.get("position", 0)
        if seeking := abs(pos - last_pos) > TIME_DISCREPANCY_TOLERANCE_MS:
            _LOGGER.debug(
                "Seeking from %s to %s",
                ms2timestamp(last_pos),
                ms2timestamp(pos),
            )

        last_state = await wait(
            presence.update(
                state,
                last_state,
                origin,
                force=seeking,
            ),
            event,
        )

        # if last_state is empty
        # it's given up control
        if not last_state:
            last_origin = ""
        last_pos = pos


async def main() -> None:
    queue: asyncio.Queue[State] = asyncio.Queue()
    event = asyncio.Event()
    session = aiohttp.ClientSession()
    signal.signal(signal.SIGINT, lambda *_: _sigint_callback(event))  # type: ignore[reportUnknownArgumentType]

    consumer_task = asyncio.create_task(
        consumer_loop(event, queue, session),
        name="consumer",
    )
    poller_tasks = [
        asyncio.create_task(
            poll_player(poller, event, queue, session),
            name=poller.__class__.__name__,
        )
        for poller in CLI_ARGS.pollers
    ]

    _LOGGER.info("Waiting for activity feed updates...")

    webserver = None
    if CLI_ARGS.enable_webserver:
        app = await get_app(queue)
        webserver = await start_app(app)

    with suppress(Bail):
        await asyncio.gather(consumer_task, *poller_tasks)

    if webserver is not None:
        await webserver.stop()

    await session.close()


def _sigint_callback(event: asyncio.Event) -> None:
    _LOGGER.info("Received CTRL+C")
    asyncio.get_running_loop().call_soon_threadsafe(lambda: event.set())


init_logging()
print_cli_args()

if not (CLI_ARGS.pollers or CLI_ARGS.enable_webserver):
    _LOGGER.error("Nothing's running. Exiting...")
    sys.exit(1)

patch_pypresence()

asyncio.run(main())
