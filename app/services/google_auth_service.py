from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import google_identity, security
from app.exceptions import GoogleAccountConflict, GoogleAccountNotSupported
from app.models.user import User
from app.repository import user_repository


def _names(claims: dict) -> tuple[str, str]:
    name = claims.get("given_name") or claims.get("name") or claims["email"].split("@")[0]
    surname = claims.get("family_name") or "-"  # some Google accounts have no family name
    return name[:50], surname[:50]


def _find_or_create(db: Session, sub: str, email: str, claims: dict, role: str, retry: bool = True) -> User:
    user = user_repository.get_by_google_sub(db, sub)
    if user is not None:
        return user  # a returning Google user: matched by the stable id, never by email

    user = user_repository.get_by_email(db, email)
    try:
        if user is None:
            name, surname = _names(claims)
            user = User(
                name=name, surname=surname, email=email, role=role,
                password_hash=None, email_verified=True, google_sub=sub,
            )
            user_repository.add(db, user)
        elif user.google_sub is not None:
            raise GoogleAccountConflict()  # this email is already linked to a different Google account
        else:
            user.google_sub = sub  # Google vouches for the address: link the account instead of asking for a password
            user.email_verified = True  # also finishes an unfinished registration
        db.commit()
    except IntegrityError:  # two parallel first logins: look again, the other request has finished
        db.rollback()
        if not retry:
            raise
        return _find_or_create(db, sub, email, claims, role, retry=False)
    return user


def login_with_google(db: Session, credential: str, role: str) -> str:
    claims = google_identity.verify_id_token(credential)  # an invalid token costs nothing: the nonce is untouched
    google_identity.consume_nonce(claims.get("nonce"))
    if not google_identity.is_authoritative(claims):
        raise GoogleAccountNotSupported()

    user = _find_or_create(db, claims["sub"], claims["email"].lower(), claims, role)
    return security.create_access_token(user.id, user.role)
