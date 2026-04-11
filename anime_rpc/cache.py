from pathlib import Path

from platformdirs import user_cache_dir

from anime_rpc import __author__

__all__: tuple[str, ...] = ("BASE_CACHE_DIR", "METADATA_CACHE_DIR")

BASE_CACHE_DIR = Path(user_cache_dir("anime_rpc", __author__))
METADATA_CACHE_DIR = BASE_CACHE_DIR / "metadata"
METADATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
