from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, SupportsInt, TypedDict

from anime_rpc.matcher import generate_regex_pattern
from anime_rpc.scraper import update_missing_metadata_in

if TYPE_CHECKING:
    from aiohttp import ClientSession

DEFAULT_APPLICATION_ID = 1088900742523392133
_LOGGER = logging.getLogger("config")
_MISSING_LOG_MSG = "Missing %s in config file, ignoring..."


class Config(TypedDict):
    # fmt: off
    # REQUIRED SETTINGS unless url is set to MAL
    title: str
    image_url: str       # defaults to ""

    # OPTIONAL SETTINGS
    url: str             # defaults to ""
    url_text: str        # defaults to View Anime
    rewatching: bool     # defaults to 0
    application_id: int  # defaults to DEFAULT_APPLICATION_ID
    match: str           # will attempt to generate a regex pattern if not set

    # CONTEXT
    path: Path
    read_at: float


def _parse_int(value: SupportsInt, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


async def get_rpc_config(
    filedir: str,
    file: str = "rpc.config",
    *,
    session: ClientSession | None = None,
    last_config: Config | None,
) -> Config | None:
    config: Config = {}  # type: ignore[reportGeneralTypeIssues]
    path = Path(filedir) / file

    try:
        modified_at = path.stat().st_mtime
    except FileNotFoundError:
        return None

    # config is cached
    # don't reread unless modified time is greater than read time
    if (
        last_config
        and path == last_config.get("path")
        and (read_at := last_config.get("read_at"))
        and read_at > modified_at
    ):
        return last_config

    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                _LOGGER.debug("Parsing line %s", stripped)
                key, value = stripped.split("=", maxsplit=1)
                config[key] = value.strip()
    except FileNotFoundError:
        return None

    # optional settings
    config.setdefault("url", "")
    config["url_text"] = config.get("url_text", "View Anime")
    config["rewatching"] = bool(_parse_int(config.get("rewatching")))
    config["application_id"] = _parse_int(
        config.get("application_id"),
        DEFAULT_APPLICATION_ID,
    )

    if session and (diff := await update_missing_metadata_in(config, session)):
        with (Path(filedir) / "rpc.config").open("a") as f:
            f.write("\n# Fetched metadata\n" + "\n".join(diff) + "\n")

    if not config.get("title"):
        _LOGGER.debug(_MISSING_LOG_MSG, "title")
        return None

    if not config.get("image_url"):
        _LOGGER.debug(_MISSING_LOG_MSG, "image_url")
        return None

    if not config.get("match") and (match := generate_regex_pattern(filedir)):
        config["match"] = match

    # context
    config["path"] = path
    config["read_at"] = time.time()
    return config
