from __future__ import annotations

import re
from http import HTTPStatus

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState

P_TAG_PATTERN = re.compile(
    r'<p id="(file|filedir|state|position|duration)"'
    r">(.+)<\/p>",
)


class MPCPoller(BasePoller):
    default_port = 13579

    @classmethod
    def origin(cls) -> str:
        return "mpc"

    @staticmethod
    def _get_vars_html(html: str) -> Vars:
        ret: Vars = Vars(**dict(P_TAG_PATTERN.findall(html)))
        ret["state"] = WatchingState(int(ret["state"]))
        ret["position"] = int(ret["position"])
        ret["duration"] = int(ret["duration"])
        return ret

    async def get_vars(self, client: aiohttp.ClientSession) -> Vars | None:
        try:
            async with client.get(
                f"http://127.0.0.1:{self.port}/variables.html",
            ) as response:
                if response.status != HTTPStatus.OK:
                    return None

                data = await response.text()
                return MPCPoller._get_vars_html(data)
        except aiohttp.ClientConnectionError:
            return None
