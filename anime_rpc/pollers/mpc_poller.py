from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any

import aiohttp

from anime_rpc.pollers.base_poller import BasePoller, Vars
from anime_rpc.states import WatchingState

P_TAG_PATTERN = re.compile(
    r'<p id="(file|filedir|state|position|duration)"'
    r">(.+)<\/p>",
)
EDITION_PATTERN = re.compile(r"<title>(MPC\-.*?) WebServer</title>")


class MPCPoller(BasePoller):
    default_port = 13579

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.edition = None

    @classmethod
    def origin(cls) -> str:
        return "mpc"

    @property
    def display_name(self) -> str:
        return self.edition or "MPC"

    @staticmethod
    def _get_vars_html(html: str) -> Vars:
        ret: Vars = Vars(**dict(P_TAG_PATTERN.findall(html)))
        ret["state"] = WatchingState(int(ret["state"]))
        ret["position"] = int(ret["position"])
        ret["duration"] = int(ret["duration"])
        return ret

    async def _fetch_edition(self, client: aiohttp.ClientSession) -> None:
        if self.edition is not None:
            return

        try:
            async with client.get(
                f"http://127.0.0.1:{self.port}/index.html"
            ) as response:
                if response.status != HTTPStatus.OK:
                    return

                data = await response.text()
                match = EDITION_PATTERN.search(data)
                if match:
                    self.edition = match.group(1)
        except aiohttp.ClientConnectionError:
            return

    def _reset_edition(self) -> None:
        self.edition = None

    async def get_vars(self, client: aiohttp.ClientSession) -> Vars | None:
        try:
            await self._fetch_edition(client)
            async with client.get(
                f"http://127.0.0.1:{self.port}/variables.html",
            ) as response:
                if response.status != HTTPStatus.OK:
                    self._reset_edition()
                    return None

                data = await response.text()
                return MPCPoller._get_vars_html(data)
        except aiohttp.ClientConnectionError:
            self._reset_edition()
            return None
