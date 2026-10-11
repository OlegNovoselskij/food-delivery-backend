import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from app import redis_client
from app.database import SessionLocal
from app.dependency import get_storage
from app.storage import S3Storage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


def _database_ok() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Readiness: the database check failed")
        return False


def _valkey_ok() -> bool:
    try:
        return bool(redis_client.get_redis().ping())
    except Exception:
        logger.warning("Readiness: the Valkey check failed", exc_info=True)
        return False


def _storage_ok(storage: S3Storage) -> bool:
    try:
        return storage.is_reachable()
    except Exception:
        logger.warning("Readiness: the storage check failed", exc_info=True)
        return False


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response, storage: S3Storage = Depends(get_storage)):
    checks = {"database": _database_ok(), "valkey": _valkey_ok(), "storage": _storage_ok(storage)}
    healthy = all(checks.values())
    if not healthy:
        response.status_code = 503
    return {
        "status": "ok" if healthy else "unavailable",
        "checks": {name: "ok" if passed else "error" for name, passed in checks.items()},
    }
