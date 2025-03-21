import logging
import os
import sys


def init_logging():
    # get rid of discord-rpc default logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.getLogger("Discord RPC").disabled = True

    logging.basicConfig(
        level=os.getenv("ANIME_RPC_LOG_LEVEL", "INFO"),
        format="%(levelname)-1.1s %(asctime)23.23s %(name)s: %(message)s",
        stream=sys.stderr,
    )
