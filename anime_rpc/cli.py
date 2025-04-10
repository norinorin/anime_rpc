import argparse
import logging

from anime_rpc.pollers import BasePoller

_LOGGER = logging.getLogger("cli")


class CLIArgs(argparse.Namespace):
    clear_on_pause: bool
    no_webserver: bool
    pollers: list[type[BasePoller]]
    fetch_episode_titles: bool


_parser = argparse.ArgumentParser(
    "anime-rpc",
    description="Discord anime integration (rich presence)",
    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=40),
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
_parser.add_argument(
    "--fetch-episode-titles",
    action="store_true",
    help=(
        "automatically fetch episode titles if ep_title "
        "is not present/captured by the match expression"
    ),
    default=False,
)
CLI_ARGS, *_ = _parser.parse_known_args(namespace=CLIArgs)


def print_cli_args() -> None:
    _LOGGER.info("Clear presence on pause: %s", CLI_ARGS.clear_on_pause)
    _LOGGER.info("Pollers used: %s", ", ".join(p.origin() for p in CLI_ARGS.pollers))
    _LOGGER.info("Webserver: %s", CLI_ARGS.no_webserver and "disabled" or "enabled")
    _LOGGER.info("Fetch missing episode titles: %s", CLI_ARGS.fetch_episode_titles)
