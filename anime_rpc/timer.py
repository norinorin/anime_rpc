import logging
from math import ceil
from time import perf_counter

from anime_rpc.cli import CLI_ARGS
from anime_rpc.formatting import ms2timestamp
from anime_rpc.presence import UpdateFlag
from anime_rpc.states import State, WatchingState

_LOGGER = logging.getLogger("timer")

TIME_DISCREPANCY_TOLERANCE_MS = 3_000


class Timer:
    def __init__(self) -> None:
        self._last_forced_update = perf_counter()
        self._last_log_time = 0.0
        self._periodic_update_in = 0.0

        # drift tracking internals
        self._last_sys_time = perf_counter()
        self._last_pos: int = -1
        self._drift_accumulator: float = 0.0

    def tick(self, state: State, flags: UpdateFlag) -> UpdateFlag:
        now = perf_counter()
        flags = self._check_forced_update(now, flags)
        flags = self._check_time_discrepancy(now, flags, state)
        return flags

    def _check_forced_update(self, now: float, flags: UpdateFlag) -> UpdateFlag:
        if not CLI_ARGS.periodic_forced_updates:
            return flags

        delta = now - self._last_forced_update
        self._periodic_update_in = max(CLI_ARGS.interval - delta, 0)

        if self._periodic_update_in > 0 and self._last_log_time + 1 < now:
            _LOGGER.debug(
                "%ds onto the next periodic forced update",
                ceil(self._periodic_update_in),
            )
            self._last_log_time = now
        elif self._periodic_update_in == 0:
            _LOGGER.debug("Interval reached, resetting the timer...")
            self._last_forced_update = now
            flags |= UpdateFlag.PERIODIC_UPDATE

        return flags

    def _check_time_discrepancy(
        self, now: float, flags: UpdateFlag, state: State
    ) -> UpdateFlag:
        elapsed_sys_ms = (now - self._last_sys_time) * 1_000
        self._last_sys_time = now

        if (pos := state.get("position")) is None:
            self._last_pos = -1
            return flags

        if self._last_pos < 0:
            self._last_pos = pos
            return flags

        elapsed_video_ms = pos - self._last_pos
        time_discrepancy = elapsed_video_ms - elapsed_sys_ms

        if (
            abs(time_discrepancy) > TIME_DISCREPANCY_TOLERANCE_MS
            or elapsed_video_ms < 0
        ):
            _LOGGER.info(
                "Seeking from %s to %s", ms2timestamp(self._last_pos), ms2timestamp(pos)
            )
            flags |= UpdateFlag.SEEKING
            self._drift_accumulator = 0.0
        elif (
            state.get("watching_state", WatchingState.NOT_AVAILABLE)
            == WatchingState.PLAYING
        ):
            self._drift_accumulator += time_discrepancy
            observed_speed = elapsed_video_ms / max(elapsed_sys_ms, 1.0)
            # scale time discrepancy tolerance with playback speed rate
            dynamic_tolerance = TIME_DISCREPANCY_TOLERANCE_MS * max(1.0, observed_speed)

            if abs(self._drift_accumulator) > dynamic_tolerance:
                _LOGGER.info(
                    "Speed drift detected (~%.2fx). Resyncing...", observed_speed
                )
                flags |= UpdateFlag.SPED_UP
                self._drift_accumulator = 0.0

        self._last_pos = pos
        return flags
