from __future__ import annotations

import logging
from io import TextIOWrapper
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


def _parse_int(value: SupportsInt, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_rpc_config(handle: TextIOWrapper) -> Config | None:
    config: Config = {}  # type: ignore[reportGeneralTypeIssues]

    for line in handle:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        _LOGGER.debug("Parsing line %s", stripped)
        key, value = stripped.split("=", maxsplit=1)
        config[key] = value.strip()

    # optional settings
    config.setdefault("url", "")
    config["url_text"] = config.get("url_text", "View Anime")
    config["rewatching"] = bool(_parse_int(config.get("rewatching")))
    config["application_id"] = _parse_int(
        config.get("application_id"),
        DEFAULT_APPLICATION_ID,
    )
    return config


async def fill_in_missing_data(
    config: Config | None, session: ClientSession, filedir: Path
) -> Config | None:
    if not config:
        return None

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

    return config
