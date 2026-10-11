from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models.user import User
from app.repository import user_repository
from app.patterns.adapters.payment_gateway import MockPaymentGateway, PaymentGateway
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
    return user_repository.get_by_id(db, user_id)


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
