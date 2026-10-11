import hashlib
import secrets

from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from redis.exceptions import RedisError

from app import config, redis_client
from app.exceptions import GoogleLoginUnavailable, InvalidGoogleToken

NONCE_TTL_SECONDS = 300
_GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_http = google_requests.Request()


def verify_id_token(credential: str) -> dict:
    if not config.GOOGLE_CLIENT_ID:
        raise GoogleLoginUnavailable()
    try:
        claims = id_token.verify_oauth2_token(credential, _http, config.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10)
    except google_exceptions.TransportError as error:  # could not download Google's public keys
        raise GoogleLoginUnavailable() from error
    except ValueError as error:  # malformed, wrong signature, wrong audience, expired
        raise InvalidGoogleToken() from error
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise InvalidGoogleToken()
    return claims


def is_authoritative(claims: dict) -> bool:
    # Google itself guarantees the mailbox for Gmail and Workspace accounts; a Google account created with a
    # third-party address proves nothing about that mailbox
    email = str(claims.get("email", "")).lower()
    if not email or claims.get("email_verified") is not True:
        return False
    return email.endswith("@gmail.com") or bool(claims.get("hd"))


def _nonce_key(nonce: str) -> str:
    return "google-nonce:" + hashlib.sha256(nonce.encode()).hexdigest()[:32]


def issue_nonce() -> str:
    nonce = secrets.token_urlsafe(24)
    try:
        redis_client.get_redis().set(_nonce_key(nonce), "1", ex=NONCE_TTL_SECONDS)
    except RedisError as error:
        raise GoogleLoginUnavailable() from error
    return nonce


def consume_nonce(nonce: str | None) -> None:
    # a nonce works once: a stolen or replayed Google token cannot be used to log in again
    if not nonce:
        raise InvalidGoogleToken()
    try:
        existed = redis_client.get_redis().getdel(_nonce_key(nonce))
    except RedisError as error:
        raise GoogleLoginUnavailable() from error
    if existed is None:
        raise InvalidGoogleToken()
