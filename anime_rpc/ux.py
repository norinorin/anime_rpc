import logging
import os

import coloredlogs  # type: ignore[reportMissingTypeStubs]


def init_logging():
    # get rid of discord-rpc default logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.getLogger("Discord RPC").disabled = True
    logging.getLogger("watchdog").setLevel(logging.WARNING)

    level = os.getenv("ANIME_RPC_LOG_LEVEL", "INFO").upper()

    coloredlogs.install(level=level)  # type: ignore[reportUnknownMemberType]
