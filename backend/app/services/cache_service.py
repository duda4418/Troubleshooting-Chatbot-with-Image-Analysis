from __future__ import annotations

import json
from typing import Any, Optional

from app.core.caching import redis_client


class CacheService:
    """Lightweight JSON cache helper backed by Redis."""

    def __init__(self) -> None:
        self._redis = redis_client()

    async def get_json(self, key: str) -> Optional[Any]:
        try:
            payload = self._redis.get(key)
        except Exception as exc:  # noqa: BLE001
            print(f"CACHE DEBUG: Error reading {key}: {exc}")
            return None
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        try:
            data = json.dumps(value, default=str)
            self._redis.set(key, data, ex=ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            print(f"CACHE DEBUG: Error writing {key}: {exc}")

    async def invalidate(self, key: str) -> None:
        try:
            self._redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            print(f"CACHE DEBUG: Error deleting {key}: {exc}")
