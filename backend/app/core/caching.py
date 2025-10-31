import os
from typing import Optional

import redis


def get_redis_client() -> redis.Redis:
    """Create a redis.Redis client using REDIS_URL or default localhost."""
    url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_HOST", "redis")
    # If REDIS_URL like redis://host:6379/0, redis.from_url handles it
    if url.startswith("redis://"):
        return redis.from_url(url, decode_responses=True)
    # otherwise construct
    port = os.environ.get("REDIS_PORT", "6379")
    return redis.Redis(host=url, port=int(port), decode_responses=True)


_client: Optional[redis.Redis] = None


def redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = get_redis_client()
    return _client
