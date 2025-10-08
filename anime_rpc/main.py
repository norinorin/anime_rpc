import asyncio
import logging
import signal
import sys
from collections.abc import Coroutine
from contextlib import suppress
from pathlib import Path
from queue import Empty as QueueEmptyError
from typing import Any

import aiohttp

from anime_rpc.asyncio_helper import Bail, wait
from anime_rpc.cli import CLI_ARGS, print_cli_args
from anime_rpc.config import Config, parse_rpc_config
from anime_rpc.file_watcher import FileWatcherManager, Subscription
from anime_rpc.formatting import ms2timestamp
from anime_rpc.matcher import generate_regex_pattern
from anime_rpc.pollers import BasePoller
from anime_rpc.presence import Presence, UpdateFlag
from anime_rpc.scraper import MALScraper
from anime_rpc.social_sdk import Discord
from anime_rpc.states import State, get_states_logger, validate_state
from anime_rpc.timer import Timer
from anime_rpc.ux import init_logging
from anime_rpc.webserver import get_app, start_app

TIME_DISCREPANCY_TOLERANCE_MS = 3_000
# fetch vars every 1 second
POLLING_INTERVAL = 1.0

_LOGGER = logging.getLogger("main")


async def poll_player(
    poller: BasePoller,
    event: asyncio.Event,
    queue: asyncio.Queue[State],
    session: aiohttp.ClientSession,
    file_watcher_manager: FileWatcherManager,
) -> None:
    config: Config | None = None
    filedir: Path | None = None
    subscription: Subscription[Config] | None = None

    while not event.is_set():
        state: State = poller.get_empty_state()
        try:
            vars_ = await wait(poller.get_vars(session), event)
        except Bail:
            break
        except Exception as e:
            # sometimes aiohttp throws a timeout error
            # not sure what's the cause, but we're catching
            # everything here to prevent the poller from crashing.

            # probable cause: mpc zombie process preventing active mpc
            # windows from binding to the port.
            _LOGGER.exception("Error while polling %s: %s", poller.display_name, e)
            continue

        new_filedir = vars_ and (fd := vars_.get("filedir")) and Path(fd) or None

        # user switches folder
        if filedir != new_filedir:
            _ = subscription and file_watcher_manager.unsubscribe(subscription)
            filedir = new_filedir
            subscription = (
                file_watcher_manager.subscribe(
                    filedir / ".rpc", parser=parse_rpc_config
                )
                if filedir
                else None
            )

        # drain the queue and get the latest change
        with suppress(QueueEmptyError):
            config = subscription and subscription.consume()

        if (
            config
            and filedir
            and not config.get("match")
            and (match := generate_regex_pattern(filedir))
        ):
            config["match"] = match

        if vars_ and config:
            state = poller.get_state(vars_, config)

        await queue.put(state)

        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=POLLING_INTERVAL)


async def consumer_loop(
    event: asyncio.Event,
    queue: asyncio.Queue[State],
    scraper: MALScraper,
    discord: Discord,
) -> None:
    presence = Presence(discord)
    timer = Timer()

    # internal states
    last_state: State = {}
    last_pos: int = -1
    last_origin: str = ""
    flags = UpdateFlag(0)

    def _queue_get_with_timeout() -> Coroutine[Any, Any, State]:
        return asyncio.wait_for(queue.get(), timeout=1)

    states_logger = get_states_logger(verbose=CLI_ARGS.verbose)
    queue_get = (
        _queue_get_with_timeout if CLI_ARGS.periodic_forced_updates else queue.get
    )

    while not event.is_set():
        try:
            state = await wait(queue_get(), event)
        except asyncio.TimeoutError:
            state = last_state

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

        states_logger.send(state)

        if CLI_ARGS.fetch_episode_titles:
            state = await wait(scraper.update_episode_title_in(state), event)

        state = await wait(scraper.update_missing_metadata_in(state), event)

        if state and not validate_state(state):
            _LOGGER.debug("Invalid state received: %s", state)
            _LOGGER.debug("Overriding invalid state with an empty one...")
            state = State()

        timer.tick()

        # store this in a variable outside of the while loop
        # so it's only consumed when the origin check passes
        # otherwise inactive pollers could consume this prematurely.
        if timer.should_force_update():
            flags |= UpdateFlag.PERIODIC_UPDATE

        # force update if the position seems off (seeking)
        pos: int | None = state.get("position")
        if (
            pos is not None
            and last_pos >= 0
            and abs(pos - last_pos) > TIME_DISCREPANCY_TOLERANCE_MS
        ):
            _LOGGER.info(
                "Seeking from %s to %s",
                ms2timestamp(last_pos),
                ms2timestamp(pos),
            )
            flags |= UpdateFlag.SEEKING

        try:
            last_state = await presence.update(state, last_state, origin, flags=flags)
        except Exception as e:
            _LOGGER.exception("Failed to update presence: %s", e)
            event.set()
            break

        flags = UpdateFlag(0)
        last_pos = pos or 0

        # if last_state is empty
        # it's given up control
        if not last_state:
            last_origin = ""
            last_pos = -1


async def async_main() -> None:
    discord = Discord()
    queue: asyncio.Queue[State] = asyncio.Queue()
    event = asyncio.Event()
    session = aiohttp.ClientSession()
    file_watcher_manager = FileWatcherManager(loop=asyncio.get_running_loop())
    scraper = MALScraper(session, file_watcher_manager)
    webserver = None
    signal.signal(signal.SIGINT, lambda *_: _sigint_callback(event))  # type: ignore[reportUnknownArgumentType]
    tasks: list[asyncio.Task[Any]] = []

    try:
        if CLI_ARGS.enable_webserver:
            app = await get_app(queue)
            webserver = await start_app(app)

        discord.start()
        file_watcher_manager.start()

        tasks.append(
            asyncio.create_task(
                consumer_loop(event, queue, scraper, discord),
                name="consumer",
            )
        )
        tasks.extend(
            [
                asyncio.create_task(
                    poll_player(poller, event, queue, session, file_watcher_manager),
                    name=poller.__class__.__name__,
                )
                for poller in CLI_ARGS.pollers
            ]
        )

        _LOGGER.info("Waiting for activity feed updates...")
        _LOGGER.info("Press CTRL+C to exit")

        with suppress(Bail):
            await asyncio.gather(*tasks)
    finally:
        _LOGGER.info("Shutting down...")
        event.set()

        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        if webserver is not None:
            await webserver.stop()

        await session.close()
        file_watcher_manager.stop()
        discord.stop()


def _sigint_callback(event: asyncio.Event) -> None:
    _LOGGER.info("Received CTRL+C")
    asyncio.get_running_loop().call_soon_threadsafe(lambda: event.set())


def main() -> None:
    init_logging()
    print_cli_args()

    if not (CLI_ARGS.pollers or CLI_ARGS.enable_webserver):
        _LOGGER.error("Nothing's running. Exiting...")
        sys.exit(1)

    asyncio.run(async_main())
