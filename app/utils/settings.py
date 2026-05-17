import threading
from typing import Any

from app.db import GetDB, crud

_lock = threading.RLock()
_cache: dict[str, Any] = {}
_loaded = False


def _load() -> None:
    global _loaded
    with GetDB() as db:
        rows = crud.get_all_settings(db)
    with _lock:
        _cache.clear()
        for r in rows:
            _cache[r.key] = r.value
        _loaded = True


def invalidate_cache() -> None:
    global _loaded
    with _lock:
        _cache.clear()
        _loaded = False


def get_panel_setting(key: str, default: Any = None) -> Any:
    with _lock:
        loaded = _loaded
    if not loaded:
        _load()
    with _lock:
        return _cache.get(key, default)
