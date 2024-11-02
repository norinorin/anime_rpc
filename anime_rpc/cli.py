import argparse


class CLIArgs(argparse.Namespace):
    clear_on_pause: bool


_parser = argparse.ArgumentParser(
    "anime-rpc", description="Discord anime integration (rich presence)"
)
_parser.add_argument(
    "--clear-on-pause",
    action="store_true",
    help="clear rich presence on media pause",
)
CLI_ARGS, *_ = _parser.parse_known_args(namespace=CLIArgs)
