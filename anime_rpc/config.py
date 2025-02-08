import time
from os.path import getmtime, join
from typing import TypedDict

DEFAULT_APPLICATION_ID = 1088900742523392133


class Config(TypedDict):
    # USER SETTINGS
    title: str
    match: str
    url: str
    url_text: str
    image_url: str
    rewatching: bool
    application_id: int

    # CONTEXT
    path: str
    read_at: float


def read_rpc_config(
    filedir: str, file: str = "rpc.config", *, last_config: Config | None
) -> Config | None:
    config: Config = {}  # type: ignore
    path = join(filedir, file)

    try:
        modified_at = getmtime(path)
    except FileNotFoundError:
        return None

    # config is cached
    # don't reread unless modified time is greater than read time
    if (
        last_config
        and path == last_config["path"]
        and last_config["read_at"] > modified_at
    ):
        return last_config

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line or line.startswith("#"):
                    continue

                key, value = line.split("=", maxsplit=1)
                config[key] = value.strip()
    except FileNotFoundError:
        return None

    config["path"] = path
    config["rewatching"] = bool(int(config["rewatching"]))
    config["read_at"] = time.time()
    config["application_id"] = int(config.get("application_id", DEFAULT_APPLICATION_ID))
    config["url_text"] = config.get("url_text", "View Anime")
    return config
