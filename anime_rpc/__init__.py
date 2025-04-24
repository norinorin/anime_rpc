import contextlib
import shutil
import subprocess

__author__ = "norinorin"
__version__ = "unknown"

with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError, OSError):
    _git_path = shutil.which("git")
    if _git_path:
        commit_hash = (
            subprocess.check_output(  # noqa: S603
                [_git_path, "rev-parse", "--short", "HEAD"],
            )
            .decode("ascii")
            .strip()
        )
        branch_name = (
            subprocess.check_output(  # noqa: S603
                [_git_path, "rev-parse", "--abbrev-ref", "HEAD"],
            )
            .decode("ascii")
            .strip()
        )
        __version__ = f"{branch_name}@{commit_hash}"
