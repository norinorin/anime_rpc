"""Monkey patch module for pypresence.

Provides an API to patch pypresence such that it returns
data received during handshake and not close the loop
on close().
"""

import ast
import inspect
import logging

import pypresence  # type: ignore[reportMissingTypeStubs]

_LOGGER = logging.getLogger("monkey_patch")


# s: https://medium.com/@chipiga86/python-monkey-patching-like-a-boss-87d7ddb8098e
def _get_source(o: object) -> str:
    """Get source of an object and corrects its indentation."""
    s = inspect.getsource(o).split("\n")  # type: ignore[reportUnknownArgumentType]
    indent = len(s[0]) - len(s[0].lstrip())
    return "\n".join(i[indent:] for i in s)


def _patch(source: str, module: object) -> dict[str, object]:
    loc: dict[str, object] = {}
    exec(  # noqa: S102
        compile(ast.parse(source), module.__name__, "exec"),  # type: ignore[reportUnknownMemberType]
        module.__dict__,
        loc,  # type: ignore[reportUnknownArgumentType]
    )
    return loc


def patch_pypresence() -> None:
    """Patch pypresence to return user data and skip loop close."""
    _LOGGER.info("Patching pypresence.BaseClient.handshake...")
    source = _get_source(pypresence.BaseClient.handshake)  # type: ignore[reportUnknownVariableType]
    patched = source + "\n    return data"
    pypresence.BaseClient.handshake = _patch(  # type: ignore[reportAttributeAccessIssue]
        patched,
        pypresence.baseclient,
    )[
        "handshake"
    ]
    _LOGGER.info("Patching pypresence.AioPresence.close...")
    source = _get_source(pypresence.AioPresence.close)  # type: ignore[reportUnknownVariableType]
    patched = source.replace("    self.loop.close()", "")
    pypresence.AioPresence.close = _patch(  # type: ignore[reportAttributeAccessIssue]
        patched,
        pypresence.presence,
    )["close"]
