import logging
from time import perf_counter

from anime_rpc.cli import CLI_ARGS

_LOGGER = logging.getLogger("timer")


class Timer:
    def __init__(self) -> None:
        self._last_forced_update = perf_counter()
        self._last_log_time = 0.0
        self._periodic_update_in = 0.0

    if CLI_ARGS.periodic_forced_updates:

        def tick(self) -> None:
            now = perf_counter()
            delta = now - self._last_forced_update
            self._periodic_update_in = max(CLI_ARGS.interval - delta, 0)
            if self._periodic_update_in > 0 and self._last_log_time + 1 < now:
                _LOGGER.debug(
                    "%ds onto the next periodic forced update", self._periodic_update_in
                )
                self._last_log_time = now
            elif self.should_force_update():
                _LOGGER.debug("Interval reached, resetting the timer...")
                self._last_forced_update = perf_counter()

        def should_force_update(self) -> bool:
            return self._periodic_update_in == 0

    else:

        def tick(self) -> None: ...

        def should_force_update(self) -> bool:
            return False
