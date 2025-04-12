import argparse
import logging
import shlex

from anime_rpc import __version__
from anime_rpc.pollers import BasePoller

_LOGGER = logging.getLogger("cli")


class CLIArgs(argparse.Namespace):
    clear_on_pause: bool
    enable_webserver: bool
    pollers: list[type[BasePoller]]
    fetch_episode_titles: bool


_parser = argparse.ArgumentParser(
    "anime_rpc",
    description="Discord anime integration (rich presence)",
    formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=40),
)
_parser.add_argument(
    "--clear-on-pause",
    action="store_true",
    help="clear rich presence on media pause",
)
_parser.add_argument(
    "--enable-webserver",
    action="store_true",
    help="enable webserver (extension integration)",
    default=False,
)
POLLERS = BasePoller.get_pollers()
_parser.add_argument(
    "--pollers",
    help=(
        "list of pollers to use"
        f" (comma-separated) Options: {', '.join(POLLERS.keys())}"
    ),
    default=[],
    type=lambda a: [POLLERS[p] for p in a.split(",")],
)
_parser.add_argument(
    "--fetch-episode-titles",
    action="store_true",
    help=(
        "automatically fetch episode titles from MyAnimeList "
        "if ep_title is not present/captured by the match expression. "
        "Requires `url` to be set to the corresponding MyAnimeList URL"
    ),
    default=False,
)
_parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=f"%(prog)s {__version__}",
    help="show program's version number and exit",
)
CLI_ARGS, _unknown_args = _parser.parse_known_args(namespace=CLIArgs)


def print_cli_args() -> None:
    _LOGGER.info("Clear presence on pause: %s", CLI_ARGS.clear_on_pause)
    _LOGGER.info(
        "Pollers used: %s",
        ", ".join(p.origin() for p in CLI_ARGS.pollers) or "none",
    )
    _LOGGER.info(
        "Webserver: %s",
        (CLI_ARGS.enable_webserver and "enabled") or "disabled",
    )
    _LOGGER.info("Fetch missing episode titles: %s", CLI_ARGS.fetch_episode_titles)

    if _unknown_args:
        _LOGGER.warning("Unknown arguments: %s", shlex.join(_unknown_args))
