from typing import TypedDict
from os.path import join


class Config(TypedDict):
    title: str
    match: str
    url: str
    image_url: str
    rewatching: bool


def read_rpc_config(filedir: str, file: str = "rpc.config") -> Config | None:
    config: Config = {}  # type: ignore
    try:
        with open(join(filedir, file), "r", encoding="utf-8") as f:
            for line in f:
                key, value = line.split("=", maxsplit=1)
                config[key] = value.strip()
    except FileNotFoundError:
        return None

    config["rewatching"] = bool(int(config["rewatching"]))
    return config


APPLICATION_ID = 1088900742523392133
