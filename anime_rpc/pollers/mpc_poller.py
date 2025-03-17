import re

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState

P_TAG_PATTERN = re.compile(r'<p id="(file|filedir|state|position|duration)">(.+)<\/p>')


class MPCPoller(BasePoller):
    port = 13579  # TODO: allow for custom ports via cli

    @classmethod
    def origin(cls) -> str:
        return "mpc"

    @staticmethod
    def _get_vars_html(html: str) -> Vars:
        ret: Vars = Vars(**{k: v for k, v in P_TAG_PATTERN.findall(html)})
        ret["state"] = WatchingState(int(ret["state"]))
        ret["position"] = int(ret["position"])
        ret["duration"] = int(ret["duration"])
        return ret

    @staticmethod
    async def get_vars(client: aiohttp.ClientSession) -> Vars | None:
        try:
            async with client.get(
                f"http://127.0.0.1:{MPCPoller.port}/variables.html"
            ) as response:
                if response.status != 200:
                    return None

                data = await response.text()
                return MPCPoller._get_vars_html(data)
        except aiohttp.ClientConnectionError:
            return
