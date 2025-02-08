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

from anime_rpc.states import State, WatchingState

PORT = 56727


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
                    assert "watching_state" in data
                    data["watching_state"] = WatchingState(data["watching_state"])
                    assert "origin" in data
                    origin = data["origin"]
                    await queue.put(data)
                    continue

                break
        except:
            raise
        finally:
            # clear presence
            await queue.put(State(origin=origin))

        return resp

    return wrapper


async def get_app(queue: asyncio.Queue[State]) -> Application:
    app = Application()
    app.router.add_get("/ws", ws_handler(queue))
    return app


async def start_app(app: Application) -> TCPSite:
    runner = AppRunner(app)
    await runner.setup()
    webserver = TCPSite(runner, "0.0.0.0", PORT)
    await webserver.start()
    print("Serving WS on", PORT)
    return webserver
