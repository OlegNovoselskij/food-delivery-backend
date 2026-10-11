from functools import lru_cache

import redis
import redis.asyncio as redis_async

from app import config


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        config.VALKEY_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=2
    )


@lru_cache
def get_async_redis() -> redis_async.Redis:
    return redis_async.Redis.from_url(
        config.VALKEY_URL, decode_responses=True, socket_connect_timeout=2, health_check_interval=30
    )
