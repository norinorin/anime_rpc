from os.path import join
from typing import TypedDict


class Config(TypedDict):
    title: str
    match: str
    url: str
    image_url: str
    rewatching: bool
    path: str


def read_rpc_config(
    filedir: str, file: str = "rpc.config", *, last_config: Config | None
) -> Config | None:
    config: Config = {}  # type: ignore
    path = join(filedir, file)

    # config is cached
    # don't reread
    if last_config and path == last_config["path"]:
        return last_config

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                key, value = line.split("=", maxsplit=1)
                config[key] = value.strip()
    except FileNotFoundError:
        return None

    config["path"] = path
    config["rewatching"] = bool(int(config["rewatching"]))
    return config


APPLICATION_ID = 1088900742523392133
