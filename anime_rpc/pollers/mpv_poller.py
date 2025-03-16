import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState


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
                return Vars(
                    file=data["filename"],
                    filedir=data["working-dir"],
                    state=WatchingState.PLAYING
                    if not data["pause"]
                    else WatchingState.PAUSED,
                    position=int(data["position"] * 1000),
                    duration=int(data["duration"] * 1000),
                )
        except aiohttp.ClientConnectionError:
            return
