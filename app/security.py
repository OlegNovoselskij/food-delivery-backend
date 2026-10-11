import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app import config

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me-in-production-min-32-bytes")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode()
    if len(raw) > 72:  # bcrypt accepts at most 72 bytes; a longer password can never be correct
        return False
    return bcrypt.checkpw(raw, password_hash.encode())


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("typ") == "upload":
        raise jwt.InvalidTokenError("upload tickets cannot be used as access tokens")
    return payload


def create_upload_ticket(
    *, user_id: int, kind: str, lesson_id: int, key: str, content_type: str, filename: str
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=config.UPLOAD_TICKET_TTL_SECONDS)
    payload = {
        "typ": "upload",
        "uid": user_id,
        "kind": kind,
        "lesson_id": lesson_id,
        "key": key,
        "ct": content_type,
        "fn": filename,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_upload_ticket(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("typ") != "upload":
        raise jwt.InvalidTokenError("not an upload ticket")
    return payload
