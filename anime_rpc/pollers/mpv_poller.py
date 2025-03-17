import os

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState


# maybe consider using native socket instead of simple-mpv-webui?
class MPVPoller(BasePoller):
    port = 14567  # TODO: allow for custom ports via cli

    @property
    def origin(self) -> str:
        return "mpv"

    @staticmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None:
        try:
            async with client.get(
                f"http://127.0.0.1:{MPVPoller.port}/api/status"
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                # depending on how you spawn mpv, the filename may be relative or absolute
                # filename is absolute if you activate a video file in thunar for example.
                full_path = data["filename"]

                if not os.path.isabs(full_path):
                    full_path = os.path.join(data["working-dir"], full_path)

                return Vars(
                    file=os.path.basename(full_path),
                    filedir=os.path.dirname(full_path),
                    state=WatchingState.PLAYING
                    if not data["pause"]
                    else WatchingState.PAUSED,
                    position=int(data["position"] * 1000),
                    duration=int(data["duration"] * 1000),
                )
        except aiohttp.ClientConnectionError:
            return
