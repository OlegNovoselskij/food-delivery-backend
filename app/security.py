import hashlib
import hmac
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app import config

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me-in-production-min-32-bytes")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:  # an account without a password (an unfinished registration) can never log in
        return False
    raw = password.encode()
    if len(raw) > 72:  # bcrypt accepts at most 72 bytes; a longer password can never be correct
        return False
    return bcrypt.checkpw(raw, password_hash.encode())


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,  # lets us reject tokens issued before the last password change
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("typ") is not None:  # access tokens have no "typ"; tickets do
        raise jwt.InvalidTokenError("tickets cannot be used as access tokens")
    return payload


def create_upload_ticket(
    *,
    user_id: int,
    kind: str,
    key: str,
    content_type: str,
    filename: str,
    lesson_id: int | None = None,
    course_id: int | None = None,
) -> str:
    expire = datetime.now(UTC) + timedelta(seconds=config.UPLOAD_TICKET_TTL_SECONDS)
    payload = {
        "typ": "upload",
        "uid": user_id,
        "kind": kind,
        "lesson_id": lesson_id,
        "course_id": course_id,
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


def create_ws_ticket(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(seconds=config.WS_TICKET_TTL_SECONDS)
    payload = {"typ": "ws", "uid": user_id, "jti": uuid.uuid4().hex, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_ws_ticket(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("typ") != "ws":
        raise jwt.InvalidTokenError("not a websocket ticket")
    return payload


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(user_id: int, purpose: str, code: str) -> str:
    # bound to the user and the purpose: a code for one account or flow is useless for another
    message = f"{purpose}:{user_id}:{code}".encode()
    return hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def codes_match(stored_hash: str, user_id: int, purpose: str, code: str) -> bool:
    return hmac.compare_digest(stored_hash, hash_code(user_id, purpose, code))
