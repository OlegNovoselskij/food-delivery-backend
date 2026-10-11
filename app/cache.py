import logging

from redis.exceptions import RedisError

from app import config, redis_client

logger = logging.getLogger(__name__)

_VERSION_KEY = "catalog:version"


class CatalogCache:
    def lookup(self, suffix: str) -> tuple[str | None, str]:
        # the version is read BEFORE the database is queried: if a writer bumps it in the meantime,
        # our fresh body lands under the old version, which nobody reads anymore
        if redis_client.is_down():
            return None, ""
        try:
            client = redis_client.get_redis()
            key = f"catalog:v{client.get(_VERSION_KEY) or 0}:{suffix}"
            return client.get(key), key
        except RedisError:
            logger.warning("Valkey is unavailable, the catalog is served without cache", exc_info=True)
            redis_client.mark_down()
            return None, ""

    def store(self, key: str, body: str) -> None:
        if not key:
            return
        try:
            redis_client.get_redis().set(key, body, ex=config.CATALOG_CACHE_TTL_SECONDS)
        except RedisError:
            redis_client.mark_down()

    def invalidate(self) -> None:
        try:
            redis_client.get_redis().incr(_VERSION_KEY)
        except RedisError:
            logger.warning("Could not invalidate the catalog cache", exc_info=True)
            redis_client.mark_down()


catalog_cache = CatalogCache()
