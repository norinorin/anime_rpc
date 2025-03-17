import asyncio
import json
import os
from typing import Callable, Type

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState


def _get_mpv_vars(filename, working_dir, paused, position, duration):
    # depending on how you spawn mpv, the filename may be relative or absolute
    # filename is absolute if you activate a video file in thunar for example.
    full_path = filename

    if not os.path.isabs(full_path):
        full_path = os.path.join(working_dir, full_path)

    return Vars(
        file=os.path.basename(full_path),
        filedir=os.path.dirname(full_path),
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
                f"http://127.0.0.1:{MPVWebUIPoller.port}/api/status"
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if "working-dir" not in data:
                    raise RuntimeError(
                        "Missing working-dir entry in mpv-webui response.\n"
                        "Please add the following line to your simple-mpv-webui/main.lua's `build_status_response()` function:\n\n"
                        "[\"working-dir\"] = mp.get_property('working-directory') or '',\n\n"
                        "Then restart mpv and try again."
                    )

                return _get_mpv_vars(
                    data["filename"],
                    data["working-dir"],
                    data["pause"],
                    data["position"],
                    data["duration"],
                )
        except aiohttp.ClientConnectionError:
            return


class MPVIPCPoller(BasePoller):
    # TODO: allow for custom paths
    ipc_path = "\\\\.\\pipe\\mpv-pipe" if os.name == "nt" else "/tmp/mpvsocket"

    if os.name == "nt":

        @staticmethod
        async def _send_command(command: bytes) -> bytes:
            # The following code is untested
            try:
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
                    MPVIPCPoller.ipc_path
                )
                writer.write(command)
                await writer.drain()

                response = await reader.readline()
                writer.close()
                await writer.wait_closed()
                return response
            except (ConnectionRefusedError, ConnectionResetError):
                return b"{}"

    @classmethod
    def origin(cls) -> str:
        return "mpv-ipc"

    @staticmethod
    async def send_command(command: dict) -> dict:
        cmd_json = json.dumps(command) + "\n"
        response = await MPVIPCPoller._send_command(cmd_json.encode("utf-8"))
        return json.loads(response.decode("utf-8"))

    @staticmethod
    async def get_property(
        property: str, typecast: Type | Callable = str
    ) -> str | None:
        command = {"command": ["get_property_string", property]}
        response = await MPVIPCPoller.send_command(command)
        if not response:
            return

        return typecast(data) if (data := response["data"]) is not None else None

    @staticmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None:
        filename = await MPVIPCPoller.get_property("filename", str)
        working_dir = await MPVIPCPoller.get_property("working-directory", str)
        paused = await MPVIPCPoller.get_property("pause", lambda x: x == "yes")
        position = await MPVIPCPoller.get_property("time-pos", float)
        duration = await MPVIPCPoller.get_property("duration", float)

        if (
            filename is None
            or working_dir is None
            or paused is None
            or position is None
            or duration is None
        ):
            return

        return _get_mpv_vars(filename, working_dir, paused, position, duration)
