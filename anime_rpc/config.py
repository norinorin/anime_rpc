from __future__ import annotations

import asyncio
import logging
import queue
import threading
from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Literal, SupportsInt, TypedDict

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from anime_rpc.matcher import generate_regex_pattern
from anime_rpc.scraper import update_missing_metadata_in

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from watchdog.events import FileSystemEvent

DEFAULT_APPLICATION_ID = 1088900742523392133
_LOGGER = logging.getLogger("config")
_MISSING_LOG_MSG = "Missing %s in config file, ignoring..."

DEBOUNCE_SECONDS = 1


class Config(TypedDict):
    # fmt: off
    # REQUIRED SETTINGS unless url is set to MAL
    title: str
    image_url: str       # defaults to ""

    # OPTIONAL SETTINGS
    url: str             # defaults to ""
    url_text: str        # defaults to View Anime
    rewatching: bool     # defaults to 0
    application_id: int  # defaults to DEFAULT_APPLICATION_ID
    match: str           # will attempt to generate a regex pattern if not set


def _parse_int(value: SupportsInt, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class EventHandler(FileSystemEventHandler):
    def __init__(self, config_store: ConfigStore) -> None:
        super().__init__()
        self.config_store = config_store
        self.queues: defaultdict[Path, queue.Queue[Path | None]] = defaultdict(
            queue.Queue
        )

        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._event = threading.Event()
        self._running = False

    def _process_queue(self) -> None:
        _LOGGER.debug("Starting config event handler thread")
        while not self._event.wait(DEBOUNCE_SECONDS):
            for file in {*self.queues}:
                _LOGGER.debug("Processing queue for %s", file)
                path: Literal[0] | Path | None = 0
                try:
                    while 1:
                        path = self.queues[file].get_nowait()
                except queue.Empty:
                    pass

                # 0 is the def value, meaning the queue is empty
                if path == 0:
                    _LOGGER.debug("Queue for %s is empty", file)
                    continue

                if not (origins := self.config_store.path_to_origins[file]):
                    _LOGGER.warning(
                        "Received an event not subscribed to any origins: %s",
                        path,
                    )
                    continue

                _LOGGER.debug("Origins subscribed to %s: %s", file, origins)

                config: Config | None = None
                if path:
                    with path.open("r") as f:
                        config = parse_rpc_config(f)

                for origin in origins:
                    if not (config_queue := self.config_store.queues.get(origin)):
                        _LOGGER.warning("Origin %s doesn't have a queue", origin)
                        continue

                    _LOGGER.debug("Queuing %s for %s", config, origin)
                    asyncio.run_coroutine_threadsafe(
                        config_queue.put(config), self.config_store.loop
                    )

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        self._event.set()
        self._thread.join()

    @staticmethod
    def _cast_path(path: str | bytes) -> Path:
        return Path(path.decode() if isinstance(path, bytes) else path)

    def on_any_event(self, event: FileSystemEvent) -> None:
        src_path = self._cast_path(event.src_path)
        dest_path = self._cast_path(event.dest_path)

        if event.is_directory and event.event_type in ("moved", "deleted"):
            _LOGGER.debug(
                "Received an event for dir %s (%s)", src_path, event.event_type
            )
            self.queues[src_path].put(None)
            return

        if (
            not event.is_directory
            and event.event_type
            in (
                "modified",
                "created",
                "moved",
                "deleted",
            )
            and (src_path.name == "rpc.config" or dest_path.name == "rpc.config")
        ):
            _LOGGER.debug(
                "Received an event for file %s (%s)", src_path, event.event_type
            )

            path = dest_path if event.event_type == "moved" else src_path
            if event.event_type in ("modified", "created") or (
                event.event_type == "moved" and path.name == "rpc.config"
            ):
                self.queues[path.parent].put(path)
            else:
                self.queues[src_path.parent].put(None)


class ConfigStore:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.dir_watchers: dict[Path, ObservedWatch] = {}
        self.queues: dict[str, asyncio.Queue[Config | None]] = {}
        self.path_to_origins: defaultdict[Path, set[str]] = defaultdict(set)

        self.event_handler = EventHandler(self)
        self.observer = Observer()
        self.loop = loop

    def start(self) -> None:
        _LOGGER.debug("Starting config store")
        self.observer.start()
        self.event_handler.start()

    def stop(self) -> None:
        _LOGGER.debug("Stopping config store")
        self.observer.stop()
        self.observer.join()
        self.event_handler.stop()

    def subscribe(
        self, filedir: Path, origin: str, queue: asyncio.Queue[Config | None]
    ) -> None:
        if filedir in self.dir_watchers:
            _LOGGER.debug(
                "File %s already being watched, adding %s to an existing watcher",
                filedir,
                origin,
            )
        else:
            self.dir_watchers[filedir] = self.observer.schedule(
                self.event_handler, str(filedir), recursive=False
            )

        self.queues[origin] = queue
        self.path_to_origins[filedir].add(origin)
        _LOGGER.debug("Subscribed %s to %s", origin, filedir)

    def unsubscribe(self, origin: str) -> None:
        self.queues.pop(origin, None)

        for file in {*self.path_to_origins}:
            if origin not in self.path_to_origins[file]:
                continue

            _LOGGER.debug("Unsubscribing %s from %s", origin, file)
            self.path_to_origins[file].remove(origin)

            if not self.path_to_origins[file]:
                _LOGGER.debug(
                    "No more origins for %s, stopping watcher",
                    file,
                )
                self.observer.unschedule(self.dir_watchers[file])
                del self.dir_watchers[file]
                del self.path_to_origins[file]
                del self.event_handler.queues[file]


def parse_rpc_config(handle: TextIOWrapper) -> Config | None:
    config: Config = {}  # type: ignore[reportGeneralTypeIssues]

    for line in handle:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        _LOGGER.debug("Parsing line %s", stripped)
        key, value = stripped.split("=", maxsplit=1)
        config[key] = value.strip()

    # optional settings
    config.setdefault("url", "")
    config["url_text"] = config.get("url_text", "View Anime")
    config["rewatching"] = bool(_parse_int(config.get("rewatching")))
    config["application_id"] = _parse_int(
        config.get("application_id"),
        DEFAULT_APPLICATION_ID,
    )
    return config


async def fill_in_missing_data(
    config: Config | None, session: ClientSession, filedir: Path
) -> Config | None:
    if not config:
        return None

    if session and (diff := await update_missing_metadata_in(config, session)):
        with (Path(filedir) / "rpc.config").open("a") as f:
            f.write("\n# Fetched metadata\n" + "\n".join(diff) + "\n")

    if not config.get("title"):
        _LOGGER.debug(_MISSING_LOG_MSG, "title")
        return None

    if not config.get("image_url"):
        _LOGGER.debug(_MISSING_LOG_MSG, "image_url")
        return None

    if not config.get("match") and (match := generate_regex_pattern(filedir)):
        config["match"] = match

    return config
