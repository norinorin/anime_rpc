import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar, cast

T = TypeVar("T")


class Bail(Exception): ...


async def wait(coro: Coroutine[Any, Any, T], event: asyncio.Event) -> T:
    done, pending = await asyncio.wait(
        [
            asyncio.Task(coro, name="queue"),
            asyncio.Task(event.wait(), name="event"),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )
    task = done.pop()

    try:
        for future in pending:
            future.cancel()
            await future
    except asyncio.CancelledError:
        pass

    if task.get_name() == "event":
        raise Bail()

    return cast(T, task.result())
