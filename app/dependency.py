from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config, rate_limit
from app.cache import catalog_cache
from app.database import get_db
from app.models.user import User
from app.repository import user_repository
from app.patterns.adapters.payment_gateway import MockPaymentGateway, PaymentGateway
from app.patterns.proxy.catalog_cache import CachingCatalogProxy, CatalogReader, DatabaseCatalogReader
from app.security import decode_access_token
from app.storage import S3Storage

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user(credentials: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    user = user_repository.get_by_id(db, user_id)
    if user is None or not user.email_verified:  # an unfinished registration never authenticates
        return None
    changed = user.password_changed_at
    if changed is not None and int(payload.get("iat", 0)) < int(changed.timestamp()):
        return None  # issued before the last password change
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user = _resolve_user(credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    return _resolve_user(credentials, db)


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user

    return checker


@lru_cache
def get_storage() -> S3Storage:
    return S3Storage(
        endpoint_url=config.S3_ENDPOINT_URL,
        public_endpoint_url=config.S3_PUBLIC_ENDPOINT_URL,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
        bucket=config.S3_BUCKET,
        region=config.S3_REGION,
    )


@lru_cache
def get_payment_gateway() -> PaymentGateway:
    return MockPaymentGateway()


@lru_cache
def get_catalog_reader() -> CatalogReader:
    return CachingCatalogProxy(DatabaseCatalogReader(), catalog_cache)


def client_ip(request: Request) -> str:
    # request.client already honours the proxy headers uvicorn is configured to trust
    return request.client.host if request.client else "unknown"


def limit_by_ip(name: str, *, limit: int, window_seconds: int):
    def dependency(request: Request) -> None:
        rate_limit.hit(f"rl:{name}:ip:{client_ip(request)}", limit, window_seconds)

    return dependency


def limit_by_user(name: str, *, limit: int, window_seconds: int):
    def dependency(user: User = Depends(get_current_user)) -> None:
        rate_limit.hit(f"rl:{name}:user:{user.id}", limit, window_seconds)

    return dependency
