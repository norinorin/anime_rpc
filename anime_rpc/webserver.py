from __future__ import annotations

import asyncio
import importlib.resources
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp_cors
from aiohttp.web_response import json_response

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import Config
from anime_rpc.pollers import PollerStatus

if TYPE_CHECKING:
    from collections.abc import Coroutine

from aiohttp import WSMsgType
from aiohttp.web import (
    Application,
    AppRunner,
    FileResponse,
    Request,
    Response,
    StreamResponse,
    TCPSite,
    WebSocketResponse,
)

from anime_rpc.metadata_providers import BaseMetadataProvider
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

    await response.write(f"data: {json.dumps(request.app['pollers'])}\n\n".encode())

    try:
        while data := await queue.get():
            await response.write(f"data: {json.dumps(data)}\n\n".encode())
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        sse_clients.remove(queue)

    return response


def get_static_path() -> Path:
    try:
        return Path(str(importlib.resources.files("anime_rpc"))) / "web" / "static"
    except Exception:  # noqa: BLE001
        return Path(__file__).parent / "web" / "static"


async def index_handler(_request: Request) -> StreamResponse:
    return FileResponse(get_static_path() / "index.html")


async def handle_get_rpc(request: Request) -> Response:
    filedir = request.query.get("dir")
    if not filedir:
        return Response(status=400, text="Missing dir parameter")

    rpc_path = Path(filedir) / ".rpc"
    if not rpc_path.exists():
        return Response(status=404, text="Not found")

    try:
        content = rpc_path.read_text(encoding="utf-8")
        return Response(text=content)
    except Exception:
        _LOGGER.exception("Failed to read RPC config.")
        return Response(status=500, text="Internal server error")


async def handle_post_rpc(request: Request) -> Response:
    try:
        data = await request.json()
        filedir = data.get("dir")
        if not filedir:
            return Response(status=400, text="Missing dir field")

        rpc_path = Path(filedir) / ".rpc"
        raw_lines = (
            rpc_path.read_text(encoding="utf-8").splitlines()
            if rpc_path.exists()
            else []
        )
        updates: dict[str, str | bool | int] = {
            key: data[key] for key in Config.__annotations__ if key in data
        }
        present_keys: set[str] = set()
        new_lines: list[str] = []

        for line in raw_lines:
            if "=" not in line:
                new_lines.append(line)
                continue

            key, _ = line.split("=", 1)

            if key not in updates:
                new_lines.append(line)
                continue

            present_keys.add(key)
            val = updates[key]

            if val:
                new_lines.append(f"{key}={val}")

        for key, val in updates.items():
            if key not in present_keys and val:
                new_lines.append(f"{key}={val}")

        rpc_path.write_text("\n".join(new_lines), encoding="utf-8")
        return Response(status=200, text="OK")
    except Exception:
        _LOGGER.exception("Failed to update RPC keys")
        return Response(status=500, text="Internal server error")


async def _on_shutdown(app: Application) -> None:
    for queue in app.get("sse_clients", []):
        await queue.put(None)


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

    app.on_shutdown.append(_on_shutdown)

    static_dir = get_static_path()
    app.router.add_get("/", index_handler)
    app.router.add_static("/", path=str(static_dir))

    app.router.add_get("/ws", ws_handler(queue))
    app.router.add_get("/search", search_handler)
    app.router.add_get("/pollers", pollers_handler)
    app.router.add_get("/pollers/events", pollers_sse_handler)
    app.router.add_get("/rpc", handle_get_rpc)
    app.router.add_post("/rpc", handle_post_rpc)
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


async def start_app(app: Application) -> tuple[AppRunner, TCPSite]:
    runner = AppRunner(app, handler_cancellation=True)
    await runner.setup()
    webserver = TCPSite(runner, "127.0.0.1", PORT)
    await webserver.start()
    _LOGGER.info("Serving WS on %d", PORT)
    return runner, webserver
