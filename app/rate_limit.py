import hashlib
import logging

from redis.exceptions import RedisError

from app import config, redis_client
from app.exceptions import RateLimitExceeded

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return config.RATE_LIMITS_ENABLED and not redis_client.is_down()


def _failed() -> None:
    logger.warning("Valkey is unavailable, rate limiting is skipped", exc_info=True)
    redis_client.mark_down()


def _count(key: str, window_seconds: int) -> tuple[int, int] | None:
    try:
        pipe = redis_client.get_redis().pipeline(transaction=True)  # MULTI/EXEC: all commands or none
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)  # the window starts at the first event and is never extended
        pipe.ttl(key)
        count, _, ttl = pipe.execute()
    except RedisError:
        _failed()
        return None
    return int(count), int(ttl) if ttl > 0 else window_seconds


def hit(key: str, limit: int, window_seconds: int) -> None:
    if not _enabled():
        return
    counted = _count(key, window_seconds)
    if counted is None:
        return
    count, seconds_left = counted
    if count > limit:
        raise RateLimitExceeded(seconds_left)


def login_client_key(client_ip: str, email: str) -> str:
    # the email is hashed: no personal data in Valkey keys, and the key length is bounded
    return f"{client_ip}:{hashlib.sha256(email.encode()).hexdigest()[:16]}"


def _login_key(client_key: str) -> str:
    return f"rl:login-fail:{client_key}"


def ensure_login_allowed(client_key: str) -> None:
    if not _enabled():
        return
    key = _login_key(client_key)
    try:
        client = redis_client.get_redis()
        failures, ttl = client.get(key), client.ttl(key)
    except RedisError:
        _failed()
        return
    if failures is not None and int(failures) >= config.LOGIN_MAX_FAILURES:
        raise RateLimitExceeded(ttl if ttl > 0 else config.LOGIN_LOCK_SECONDS)


def register_login_failure(client_key: str) -> None:
    if _enabled():
        _count(_login_key(client_key), config.LOGIN_LOCK_SECONDS)


def clear_login_failures(client_key: str) -> None:
    if not _enabled():
        return
    try:
        redis_client.get_redis().delete(_login_key(client_key))
    except RedisError:
        _failed()
