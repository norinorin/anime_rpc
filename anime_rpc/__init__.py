__version__: str

try:
    # _version.py is dynamically generated during build time
    from anime_rpc._version import (  # type: ignore[reportMissingImports]
        __version__ as __version__,  # type: ignore[reportUnknownVariableType]
    )
except ImportError:
    __version__ = "0.0.0+unknown"

__author__ = "norinorin"
