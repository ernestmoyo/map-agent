"""On-disk cache for geoserver responses.

Keyed by hash of request parameters. TTLs configured in settings.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from map_agent.core.config import settings


def _cache_dir() -> Path:
    """Return the cache directory, creating it if needed."""
    path = settings.cache_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(namespace: str, **params: Any) -> str:
    """Generate a deterministic cache key from namespace + params."""
    raw = json.dumps({"ns": namespace, **params}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def get_cached_path(namespace: str, suffix: str = ".json", **params: Any) -> Path | None:
    """Return cached file path if it exists and hasn't expired.

    Args:
        namespace: Cache category (e.g., "capabilities", "raster", "boundaries").
        suffix: File extension for the cached file.
        **params: Request parameters to include in the cache key.

    Returns:
        Path to cached file, or None if not cached / expired.
    """
    key = _cache_key(namespace, **params)
    cached = _cache_dir() / f"{namespace}_{key}{suffix}"

    if not cached.exists():
        return None

    ttl = settings.capabilities_ttl if namespace == "capabilities" else settings.data_ttl
    age = time.time() - cached.stat().st_mtime
    if age > ttl:
        cached.unlink(missing_ok=True)
        return None

    return cached


def cache_path_for(namespace: str, suffix: str = ".json", **params: Any) -> Path:
    """Return the path where a cached file should be written.

    Always returns a path — caller decides whether to write to it.
    """
    key = _cache_key(namespace, **params)
    _cache_dir()
    return _cache_dir() / f"{namespace}_{key}{suffix}"


def read_json_cache(namespace: str, **params: Any) -> Any | None:
    """Read a JSON-cached value, or None if missing/expired."""
    path = get_cached_path(namespace, suffix=".json", **params)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_cache(namespace: str, data: Any, **params: Any) -> Path:
    """Write a JSON value to cache and return the file path."""
    path = cache_path_for(namespace, suffix=".json", **params)
    path.write_text(json.dumps(data, default=str), encoding="utf-8")
    return path
