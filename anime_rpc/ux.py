import logging
import os
import re
import shutil
import sys
from typing import TextIO, TypeAlias

import coloredlogs  # type: ignore[reportMissingTypeStubs]

from anime_rpc.cli import CLI_ARGS

RawFormattedRecord: TypeAlias = tuple[int, str]
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class GroupedStreamHandler(logging.StreamHandler[TextIO]):
    def __init__(self, stream: TextIO | None = None) -> None:
        super().__init__(stream or sys.stderr)
        self.last_record: RawFormattedRecord | None = None
        self.count: int = 1
        self.last_visual_lines: int = 0
        self.terminator: str = ""
        self.is_tty: bool = hasattr(self.stream, "isatty") and self.stream.isatty()

    def _get_visual_lines(self, msg: str) -> int:
        columns = shutil.get_terminal_size().columns or 80
        clean_msg = ANSI_ESCAPE.sub("", msg)
        return sum(
            max(1, (len(line) + columns - 1) // columns)
            for line in clean_msg.split("\n")
        )

    def _maybe_write_non_tty_summary(self) -> None:
        if self.is_tty or self.count <= 1 or self.last_record is None:
            return

        self.stream.write(f"--- Last message repeated {self.count - 1} times ---\n")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            current_record: RawFormattedRecord = (record.levelno, record.getMessage())

            if current_record == self.last_record:
                self.count += 1

                if not self.is_tty:
                    return

                # \033[{N}A : move up N terminal rows
                # \033[J    : clear from the cursor to the end of the screen
                # \033[90m  : gray colour
                formatted_msg = f"{msg} \033[90m[{self.count}x]\033[0m"
                self.stream.write(
                    f"\033[{self.last_visual_lines}A\033[J{formatted_msg}\n"
                )
                self.stream.flush()
                self.last_visual_lines = self._get_visual_lines(formatted_msg)
                return

            self._maybe_write_non_tty_summary()
            self.stream.write(f"{msg}\n")
            self.stream.flush()
            self.last_record = current_record
            self.count = 1
            self.last_visual_lines = self._get_visual_lines(msg)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        try:
            self._maybe_write_non_tty_summary()
        finally:
            super().close()


def init_logging():
    logging.getLogger("watchdog").setLevel(logging.WARNING)

    level = (
        "DEBUG"
        if CLI_ARGS.verbose
        else os.getenv("ANIME_RPC_LOG_LEVEL", "INFO").upper()
    )

    coloredlogs.install(level=level)  # type: ignore[reportUnknownMemberType]

    root_logger = logging.getLogger()
    if root_logger.handlers:
        original_handler = root_logger.handlers[0]

        grouped_handler = GroupedStreamHandler(original_handler.stream)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
        grouped_handler.setFormatter(original_handler.formatter)

        for filter_ in original_handler.filters:
            grouped_handler.addFilter(filter_)

        root_logger.handlers[0] = grouped_handler
