import time
from functools import lru_cache

import redis
import redis.asyncio as redis_async

from app import config

_BACKOFF_SECONDS = 10
_down_until = 0.0


def is_down() -> bool:
    return time.monotonic() < _down_until


def mark_down() -> None:
    global _down_until
    _down_until = time.monotonic() + _BACKOFF_SECONDS


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(config.VALKEY_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=2)


@lru_cache
def get_async_redis() -> redis_async.Redis:
    return redis_async.Redis.from_url(
        config.VALKEY_URL, decode_responses=True, socket_connect_timeout=2, health_check_interval=30
    )
