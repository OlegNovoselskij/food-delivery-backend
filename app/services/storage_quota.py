import logging
import time

from redis.exceptions import RedisError, WatchError
from sqlalchemy.orm import Session

from app import config, redis_client
from app.exceptions import StorageQuotaExceeded, StorageUnavailable
from app.repository import media_repository

logger = logging.getLogger(__name__)

RESERVATIONS_KEY = "storage:reservations"
_MAX_ATTEMPTS = 5


def _member(key: str, size: int) -> str:
    return f"{size}|{key}"


def _size_of(member: str) -> int:
    return int(member.split("|", 1)[0])


def _failed() -> None:
    logger.warning("Valkey is unavailable, upload reservations are skipped", exc_info=True)
    redis_client.mark_down()


def reserve(db: Session, key: str, size: int, *, replacing: int = 0) -> None:
    """Hold `size` bytes for an upload until its ticket expires or the upload is confirmed.

    Uploads go straight to the storage, so the database does not know about files that are in flight. They live in a
    sorted set (member = "size|key", score = expiry time). The check and the insert use WATCH/MULTI/EXEC: a concurrent
    reservation changes the set, EXEC fails and the check is repeated, so two requests cannot both take the last free
    bytes. Valkey being down is not a reason to stop all uploads: the database check on confirm still holds the limit.
    """
    available = config.STORAGE_QUOTA_BYTES - (media_repository.used_storage_bytes(db) - replacing)
    if size > available:
        raise StorageQuotaExceeded()
    if redis_client.is_down():
        return

    now = time.time()
    try:
        client = redis_client.get_redis()
        client.zremrangebyscore(RESERVATIONS_KEY, "-inf", now)  # outside WATCH: our own write would abort EXEC
        with client.pipeline() as pipe:
            for _ in range(_MAX_ATTEMPTS):
                try:
                    pipe.watch(RESERVATIONS_KEY)
                    reserved = sum(_size_of(member) for member in pipe.zrange(RESERVATIONS_KEY, 0, -1))
                    if reserved + size > available:
                        raise StorageQuotaExceeded()
                    pipe.multi()
                    pipe.zadd(RESERVATIONS_KEY, {_member(key, size): now + config.UPLOAD_TICKET_TTL_SECONDS})
                    pipe.execute()
                    return
                except WatchError:
                    continue
    except RedisError:
        _failed()
        return
    raise StorageUnavailable()


def release(key: str) -> None:
    if redis_client.is_down():
        return
    try:
        client = redis_client.get_redis()
        suffix = f"|{key}"
        stale = [member for member in client.zrange(RESERVATIONS_KEY, 0, -1) if member.endswith(suffix)]
        if stale:
            client.zrem(RESERVATIONS_KEY, *stale)
    except RedisError:
        _failed()


def ensure_room(db: Session, size: int, *, replacing: int = 0) -> None:
    if media_repository.used_storage_bytes(db) - replacing + size > config.STORAGE_QUOTA_BYTES:
        raise StorageQuotaExceeded()
