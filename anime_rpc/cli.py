import argparse

from anime_rpc.pollers import BasePoller


class CLIArgs(argparse.Namespace):
    clear_on_pause: bool
    no_webserver: bool
    pollers: list[type[BasePoller]]


_parser = argparse.ArgumentParser(
    "anime-rpc",
    description="Discord anime integration (rich presence)",
)
_parser.add_argument(
    "--clear-on-pause",
    action="store_true",
    help="clear rich presence on media pause",
)
_parser.add_argument(
    "--no-webserver",
    action="store_true",
    help="disable webserver (extension integration)",
    default=False,
)
POLLERS = BasePoller.get_pollers()
_parser.add_argument(
    "--poller",
    help=(
        "list of pollers to use"
        f" (comma-separated) Options: {', '.join(POLLERS.keys())}"
    ),
    default=[],
    type=lambda a: [POLLERS[p] for p in a.split(",")],
    dest="pollers",
)
CLI_ARGS, *_ = _parser.parse_known_args(namespace=CLIArgs)
