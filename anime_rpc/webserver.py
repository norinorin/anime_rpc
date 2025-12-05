from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Callable

from aiohttp.web_response import json_response

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Coroutine

from aiohttp import WSMsgType
from aiohttp.web import (
    Application,
    AppRunner,
    Request,
    Response,
    TCPSite,
    WebSocketResponse,
)

from anime_rpc.states import State, WatchingState

PORT = 56727
_LOGGER = logging.getLogger("webserver")


def ws_handler(
    queue: asyncio.Queue[State],
) -> Callable[[Request], Coroutine[Any, Any, WebSocketResponse | Response]]:
    async def wrapper(request: Request) -> WebSocketResponse | Response:
        resp = WebSocketResponse()

        await resp.prepare(request)
        await resp.send_str("Hello!")

        origin: str = "web"

        try:
            async for msg in resp:
                if msg.type is WSMsgType.TEXT:
                    if msg.data == "keepalive":
                        continue

                    data: State = json.loads(msg.data)
                    if "watching_state" in data:
                        data["watching_state"] = WatchingState(
                            data["watching_state"],
                        )
                    assert "origin" in data
                    origin = data["origin"]
                    await queue.put(data)
                    continue

                break
        finally:
            # clear presence
            await queue.put(State(origin=origin))

        return resp

    return wrapper


async def status_handler(request: Request) -> Response:
    return json_response(request.app["current_state"])


async def get_app(queue: asyncio.Queue[State]) -> Application:
    app = Application()
    app["current_state"] = {}
    app.router.add_get("/ws", ws_handler(queue))
    app.router.add_get("/status", status_handler)
    return app


async def start_app(app: Application) -> TCPSite:
    runner = AppRunner(app)
    await runner.setup()
    webserver = TCPSite(runner, "127.0.0.1", PORT)
    await webserver.start()
    _LOGGER.info("Serving WS on %d", PORT)
    return webserver
