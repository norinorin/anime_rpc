import asyncio
import json
from typing import Any, Callable, Coroutine

from aiohttp import WSMsgType
from aiohttp.web import (
    Application,
    AppRunner,
    Request,
    Response,
    TCPSite,
    WebSocketResponse,
)

from anime_rpc.states import State


def ws_handler(
    queue: asyncio.Queue[State],
) -> Callable[[Request], Coroutine[Any, Any, WebSocketResponse | Response]]:
    async def wrapper(request: Request) -> WebSocketResponse | Response:
        resp = WebSocketResponse()

        await resp.prepare(request)
        await resp.send_str("Hello!")

        async for msg in resp:
            if msg.type is WSMsgType.TEXT:
                # await queue.put(json.loads(msg.data))
                ...
            else:
                return resp

        # on exit dont forget to set state back to {}
        # queue.put(State())
        return resp

    return wrapper


async def get_app(queue: asyncio.Queue[State]) -> Application:
    app = Application()
    app.router.add_get("/ws", ws_handler(queue))
    return app


async def start_app(app: Application) -> TCPSite:
    runner = AppRunner(app)
    await runner.setup()
    webserver = TCPSite(runner, "0.0.0.0", 56727)
    await webserver.start()
    return webserver
