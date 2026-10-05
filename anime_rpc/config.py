from __future__ import annotations

import logging
from io import TextIOWrapper
from typing import TypedDict

_LOGGER = logging.getLogger("config")
_MISSING_LOG_MSG = "Missing %s in config file, ignoring..."


class Config(TypedDict):
    # fmt: off
    # REQUIRED SETTINGS unless url is set to MAL
    title: str
    image_url: str

    # OPTIONAL SETTINGS
    url: str             # defaults to ""
    rewatching: bool     # defaults to False
    application_id: int  # defaults to DEFAULT_APPLICATION_ID
    match: str           # will attempt to generate a regex pattern if not set


def _parse_bool(value: str | int | None) -> bool:
    if value is None:
        return False

    if isinstance(value, int):
        return bool(value)

    if value.lower().strip() == "true":
        return True

    if value.isdigit():
        return bool(int(value))

    return False


def parse_rpc_config(handle: TextIOWrapper) -> Config | None:
    config: Config = {}  # type: ignore[reportGeneralTypeIssues]
    valid_keys = {*Config.__annotations__.keys()}

    for line in handle:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.count("=") == 0:
            _LOGGER.warning("Ignoring line with invalid syntax %r in .rpc", stripped)
            continue

        _LOGGER.debug("Parsing line %s", stripped)
        key, value = stripped.split("=", maxsplit=1)

        if key not in valid_keys:
            _LOGGER.warning("Ignoring invalid key %r with value %r in .rpc", key, value)
            continue

        config[key] = value.strip()

    # optional settings
    config.setdefault("url", "")
    config["rewatching"] = bool(_parse_bool(config.get("rewatching")))
    config["application_id"] = config.get("application_id", "default")
    return config


def validate_config(config: Config) -> set[str]:
    ret: set[str] = set()

    if not config.get("match"):
        _LOGGER.debug(_MISSING_LOG_MSG, "match")
        ret.add("match")

    return ret
