import threading
import time
from typing import Any

import anime_rpc.monkey_patch  # type: ignore
from anime_rpc.config import Config, read_rpc_config
from anime_rpc.mpc import Vars, get_vars
from anime_rpc.presence import update_activity


TIME_DISCREPANCY_TOLERANCE = 3_000  # 3 seconds


def loop(event: threading.Event):
    last_file_dir: str | None = None
    config: Config | None = None
    last_pos: int = 0
    state: dict[str, Any] = {}

    while not event.is_set():
        vars: Vars | None = get_vars()
        if vars and vars["filedir"] != last_file_dir:
            config = read_rpc_config(vars["filedir"])
            last_file_dir = vars["filedir"]

        # only force update if the position seems off (seeking)
        pos: int = vars["position"] if vars else 0
        state = update_activity(
            vars, config, state, abs(pos - last_pos) > TIME_DISCREPANCY_TOLERANCE
        )
        last_pos = pos
        event.wait(1)


def main():
    event = threading.Event()
    loop_thread = threading.Thread(target=loop, args=(event,))
    loop_thread.start()

    try:
        while loop_thread.is_alive():
            time.sleep(10)
    except KeyboardInterrupt:
        event.set()


main()
