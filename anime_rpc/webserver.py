from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Callable

import aiohttp_cors
from aiohttp.web_response import json_response

from anime_rpc.cli import CLI_ARGS
from anime_rpc.pollers import PollerStatus

if TYPE_CHECKING:
    from collections.abc import Coroutine

from aiohttp import WSMsgType
from aiohttp.web import (
    Application,
    AppRunner,
    Request,
    Response,
    StreamResponse,
    TCPSite,
    WebSocketResponse,
)

from anime_rpc.metadata_provider import BaseMetadataProvider
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


async def search_handler(request: Request) -> Response:
    query = request.query.get("q")
    if not query:
        return json_response({"error": "Missing query parameter 'q'"}, status=400)

    provider_name = request.query.get("provider", "myanimelist").lower()
    providers = request.app["metadata_providers"]
    provider = providers.get(provider_name)
    if not provider:
        return json_response(
            {
                "error": f"Unkown provider '{provider_name}'.",
                "provider_names": list(providers.keys()),
            }
        )

    results = await provider.search(query)
    return json_response(results)


async def pollers_handler(request: Request) -> Response:
    return json_response(request.app["pollers"])


async def pollers_sse_handler(request: Request) -> StreamResponse:
    response = StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await response.prepare(request)

    sse_clients = request.app["sse_clients"]
    queue: asyncio.Queue[dict[str, PollerStatus]] = asyncio.Queue()
    sse_clients.append(queue)

    await response.write(
        f"data: {json.dumps(request.app['pollers'])}\n\n".encode("utf-8")
    )

    try:
        while True:
            data = await queue.get()
            await response.write(f"data: {json.dumps(data)}\n\n".encode("utf-8"))

    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        sse_clients.remove(queue)

    return response


async def get_app(
    queue: asyncio.Queue[State], metadata_providers: dict[str, BaseMetadataProvider]
) -> Application:
    app = Application()
    app["metadata_providers"] = metadata_providers
    app["sse_clients"] = []
    app["pollers"] = {
        p.origin(): PollerStatus(
            {"active": False, "filedir": None, "display_name": p.display_name}
        )
        for p in CLI_ARGS.pollers
    }

    app.router.add_get("/ws", ws_handler(queue))
    app.router.add_get("/search", search_handler)
    app.router.add_get("/pollers", pollers_handler)
    app.router.add_get("/pollers/events", pollers_sse_handler)
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True, expose_headers="*", allow_headers="*"
            )
        },
    )
    for route in list(app.router.routes()):
        cors.add(route)  # type: ignore
    return app


async def start_app(app: Application) -> TCPSite:
    runner = AppRunner(app)
    await runner.setup()
    webserver = TCPSite(runner, "127.0.0.1", PORT)
    await webserver.start()
    _LOGGER.info("Serving WS on %d", PORT)
    return webserver
