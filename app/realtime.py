import json
import logging

from app import redis_client

logger = logging.getLogger(__name__)


def channel_for(user_id: int) -> str:
    return f"notifications:{user_id}"


def publish(user_id: int, message: dict) -> None:
    # best effort: the notification is already saved in Postgres, so a lost push is not a lost notification
    if redis_client.is_down():
        return
    try:
        redis_client.get_redis().publish(channel_for(user_id), json.dumps(message))
    except Exception:
        logger.exception("Could not publish a realtime message for user %s", user_id)
        redis_client.mark_down()
