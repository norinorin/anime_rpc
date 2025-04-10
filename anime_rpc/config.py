from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TypedDict

DEFAULT_APPLICATION_ID = 1088900742523392133
_LOGGER = logging.getLogger("config")
_MISSING_LOG_MSG = "Missing %s in config file, ignoring..."


class Config(TypedDict):
    # fmt: off
    # USER SETTINGS
    title: str
    match: str

    # OPTIONAL SETTINGS
    image_url: str       # defaults to ""
    url: str             # defaults to ""
    url_text: str        # defaults to View Anime
    rewatching: bool     # defaults to 0
    application_id: int  # defaults to DEFAULT_APPLICATION_ID

    # CONTEXT
    path: Path
    read_at: float


def read_rpc_config(
    filedir: str,
    file: str = "rpc.config",
    *,
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

    # required settings
    if "title" not in config:
        _LOGGER.debug(_MISSING_LOG_MSG, "title")
        return None

    if "match" not in config:
        # TODO: automatically generate a regex for the directory
        # based on the file names in it
        _LOGGER.debug(_MISSING_LOG_MSG, "match")
        return None

    if "image_url" not in config:
        _LOGGER.debug(_MISSING_LOG_MSG, "image_url")
        return None

    # optional settings
    config.setdefault("url", "")
    config["url_text"] = config.get("url_text", "View Anime")
    config["rewatching"] = bool(int(config.get("rewatching", 0)))
    config["application_id"] = int(
        config.get("application_id", DEFAULT_APPLICATION_ID),
    )

    # context
    config["path"] = path
    config["read_at"] = time.time()
    return config
