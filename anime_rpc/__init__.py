import contextlib
import shutil
import subprocess

__author__ = "norinorin"
__version__ = "unknown"

with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError, OSError):
    _git_path = shutil.which("git")
    if _git_path:
        __version__ = (
            subprocess.check_output(  # noqa: S603
                [_git_path, "rev-parse", "--short", "HEAD"],
            )
            .decode("ascii")
            .strip()
        )
