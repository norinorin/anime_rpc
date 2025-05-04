from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import threading
from asyncio import Queue as AsyncQueue
from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path
from queue import Empty as QueueEmptyError
from queue import Queue as ThreadSafeQueue
from typing import Any, Callable, Generic, Literal, TypeAlias, TypeVar, cast

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

_LOGGER = logging.getLogger("file_watcher")
DEBOUNCE_SECONDS = 1

T = TypeVar("T")
ParserFunction: TypeAlias = Callable[[TextIOWrapper], T | None]

MODIFIED = cast('Literal["modified"]', sys.intern("modified"))
DELETED = cast('Literal["deleted"]', sys.intern("deleted"))
CREATED = cast('Literal["created"]', sys.intern("created"))
MOVED = cast('Literal["moved"]', sys.intern("moved"))


class Empty:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> Literal[False]:
        return False


class EventHandler(FileSystemEventHandler):
    def __init__(self, file_watcher_manager: FileWatcherManager) -> None:
        super().__init__()
        self.file_watcher_manager = file_watcher_manager
        self.parser_queues: defaultdict[
            Path, ThreadSafeQueue[Literal["modified", "deleted"] | Empty]
        ] = defaultdict(ThreadSafeQueue)

        self._thread = threading.Thread(target=self._consume_parser_queue, daemon=True)
        self._event = threading.Event()
        self._running = False

    @staticmethod
    def dispatch_removed(subscriptions: set[Subscription[Any]]) -> None:
        for s in subscriptions:
            s.put(None)

    @staticmethod
    def dispatch_modified(subscriptions: set[Subscription[Any]]) -> None:
        file_path = next(iter(subscriptions)).file_path
        if not file_path.exists():
            return
        with file_path.open("r") as f:
            for s in subscriptions:
                f.seek(0)
                try:
                    parsed = s.parser(f)
                except Exception:
                    _LOGGER.exception("Failed to parse %s, ignoring...", file_path)
                    continue
                s.put(parsed)

    def _consume_parser_queue(self) -> None:
        _LOGGER.debug("Starting config event handler thread")
        while not self._event.wait(DEBOUNCE_SECONDS):
            for file_path in {*self.parser_queues}:
                event = Empty()
                with contextlib.suppress(QueueEmptyError):
                    while True:
                        event = self.parser_queues[file_path].get_nowait()

                if event is Empty():
                    continue

                if not (
                    subscriptions := self.file_watcher_manager.subscriptions[file_path]
                ):
                    _LOGGER.warning(
                        "Received an event with no subscriptions: %s",
                        file_path,
                    )
                    continue

                if event is DELETED:
                    self.dispatch_removed(subscriptions)
                    continue

                self.dispatch_modified(subscriptions)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        self._event.set()
        self._thread.join()

    @staticmethod
    def _cast_path(path: str | bytes) -> Path:
        return Path(path.decode() if isinstance(path, bytes) else path).resolve()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        if event.event_type not in (MODIFIED, CREATED, MOVED, DELETED):
            return

        src_path = self._cast_path(event.src_path)
        dest_path = self._cast_path(event.dest_path)

        if not (
            src_path in self.file_watcher_manager.subscriptions
            or dest_path in self.file_watcher_manager.subscriptions
        ):
            _LOGGER.debug(
                "Received an event for file %s (%s) but no subscriptions found",
                src_path,
                event.event_type,
            )
            _LOGGER.debug(
                "Current subscriptions: %s", self.file_watcher_manager.subscriptions
            )
            return

        _LOGGER.debug("Received an event for file %s (%s)", src_path, event.event_type)

        path = dest_path if event.event_type is MOVED else src_path
        if event.event_type in (MODIFIED, CREATED) or (
            event.event_type is MOVED and path.name == "rpc.config"
        ):
            self.parser_queues[path].put(MODIFIED)
            return

        self.parser_queues[src_path].put(DELETED)


# this class needs to be instantiated in an async context
class Subscription(Generic[T]):
    def __init__(
        self,
        file_path: Path,
        parser: ParserFunction[T],
        observed: ObservedWatch,
    ) -> None:
        self.parser = parser
        self.file_path = file_path
        self.observed = observed

        # assume loop has been running at this point
        self.queue: AsyncQueue[T | None] = AsyncQueue()

    def consume(self) -> T | None:
        ret = Empty()

        while self.queue.qsize():
            ret = self.queue.get_nowait()

        if ret is Empty():
            raise QueueEmptyError

        assert not isinstance(ret, Empty)
        return ret

    def put(self, item: T | None) -> None:
        self.queue.put_nowait(item)


class FileWatcherManager:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.subscriptions: defaultdict[Path, set[Subscription[Any]]] = defaultdict(set)
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

    # needs to be called in an async context
    def subscribe(self, file_path: Path, parser: ParserFunction[T]) -> Subscription[T]:
        file_path = file_path.resolve()
        subscriptions = self.subscriptions[file_path]
        subscriptions.add(
            subscription := Subscription(
                file_path,
                parser,
                self.observer.schedule(
                    self.event_handler, str(file_path.parent), recursive=False
                ),
            )
        )
        # dispatch false event to trigger the intial parse
        self.event_handler.dispatch_modified({subscription})
        _LOGGER.debug("New subscription for %s", file_path)
        return subscription

    def unsubscribe(self, subscription: Subscription[Any]) -> None:
        file_path = subscription.file_path
        _LOGGER.debug("Unsubscribing %s", file_path)
        self.subscriptions[file_path].discard(subscription)
        if not self.subscriptions[file_path]:
            _LOGGER.debug(
                "No watchers left for %s, removing set...", subscription.observed.path
            )
            self.subscriptions.pop(file_path, None)
            self.event_handler.parser_queues.pop(file_path, None)
