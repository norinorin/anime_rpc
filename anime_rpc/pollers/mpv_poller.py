from __future__ import annotations

import asyncio
import json
import os
from http import HTTPStatus
from pathlib import Path
from typing import Callable, TypedDict, TypeVar

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState

T = TypeVar("T")
MISSING_WORKING_DIR_MSG = (
    "Missing working-dir entry in mpv-webui response.\n"
    "Please add the following line to your simple-mpv-webui/main.lua's"
    " `build_status_response()` function:\n\n"
    "[\"working-dir\"] = mp.get_property('working-directory') or '',\n\n"
    "Then restart mpv and try again.",
)


class MPVCommand(TypedDict):
    command: list[str]


class MPVResponse(TypedDict):
    error: str
    data: str | None
    request_id: int


class MPVPlaylistEntry(TypedDict):
    current: bool
    filename: str
    playing: bool
    id: int


def _get_mpv_vars(
    *,
    playlist: list[MPVPlaylistEntry],
    working_dir: str,
    paused: bool,
    position: float,
    duration: float,
) -> Vars | None:
    # depending on how you spawn mpv, the filename may be relative or absolute
    # it's absolute if you activate a video file in thunar for example
    # tho it's only absolute in the playlist field
    current = ([i for i in playlist if i.get("current", False)] + [None])[0]
    if not current:
        return None

    full_path = Path(current["filename"])

    if not full_path.is_absolute():
        full_path = Path(working_dir) / full_path

    return Vars(
        file=full_path.name,
        filedir=str(full_path.parent),
        state=WatchingState.PLAYING if not paused else WatchingState.PAUSED,
        position=int(position * 1000),
        duration=int(duration * 1000),
    )


class MPVWebUIPoller(BasePoller):
    port = 14567  # TODO: allow for custom ports via cli

    @classmethod
    def origin(cls) -> str:
        return "mpv-webui"

    @staticmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None:
        try:
            async with client.get(
                f"http://127.0.0.1:{MPVWebUIPoller.port}/api/status",
            ) as response:
                if response.status != HTTPStatus.OK:
                    return None

                data = await response.json()

                if "working-dir" not in data:
                    raise RuntimeError(MISSING_WORKING_DIR_MSG)

                return _get_mpv_vars(
                    playlist=data["playlist"],
                    working_dir=data["working-dir"],
                    paused=data["pause"],
                    position=data["position"],
                    duration=data["duration"],
                )
        except aiohttp.ClientConnectionError:
            return None


# TODO: maybe consider switching to a hook-based approach
class MPVIPCPoller(BasePoller):
    # TODO: allow for custom paths
    ipc_path = (
        "\\\\.\\pipe\\mpv-pipe" if os.name == "nt" else "/tmp/mpvsocket"
    )  # noqa: S108

    if os.name == "nt":

        @staticmethod
        async def _send_command(command: bytes) -> bytes:
            # The following code is untested
            try:
                # FIXME: write in a another thread
                with open(MPVIPCPoller.ipc_path, "w+b", buffering=0) as pipe:
                    pipe.write(command)
                    return pipe.readline()
            except FileNotFoundError:
                return b"{}"

    else:

        @staticmethod
        async def _send_command(command: bytes) -> bytes:
            try:
                reader, writer = await asyncio.open_unix_connection(
                    MPVIPCPoller.ipc_path,
                )
                writer.write(command)
                await writer.drain()

                while not (
                    b"error" in (response := await reader.readline())
                    and b'"request_id":0' in response
                    and b'"data"' in response
                ):
                    continue

                writer.close()
                await writer.wait_closed()
            except (
                ConnectionRefusedError,
                ConnectionResetError,
                FileNotFoundError,
            ):
                return b"{}"
            else:
                return response

    @classmethod
    def origin(cls) -> str:
        return "mpv-ipc"

    @staticmethod
    async def send_command(command: MPVCommand) -> MPVResponse:
        cmd_json = json.dumps(command) + "\n"
        response = await MPVIPCPoller._send_command(cmd_json.encode("utf-8"))
        return json.loads(response.decode("utf-8"))

    @staticmethod
    async def get_property(
        property_: str,
        /,
        typecast: Callable[[str], T] = str,
    ) -> T | None:
        command: MPVCommand = {"command": ["get_property_string", property_]}
        response = await MPVIPCPoller.send_command(command)
        if not response:
            return None

        return typecast(data) if (data := response["data"]) is not None else None

    @staticmethod
    def _typecast_playlist(data: str) -> list[MPVPlaylistEntry]:
        return json.loads(data)

    @staticmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None:
        # FIXME: is there a way to do this in batch?
        playlist = await MPVIPCPoller.get_property(
            "playlist",
            MPVIPCPoller._typecast_playlist,
        )
        working_dir = await MPVIPCPoller.get_property("working-directory", str)
        paused = await MPVIPCPoller.get_property("pause", lambda x: x == "yes")
        position = await MPVIPCPoller.get_property("time-pos", float)
        duration = await MPVIPCPoller.get_property("duration", float)

        if (
            playlist is None
            or working_dir is None
            or paused is None
            or position is None
            or duration is None
        ):
            return None

        return _get_mpv_vars(
            playlist=playlist,
            working_dir=working_dir,
            paused=paused,
            position=position,
            duration=duration,
        )
