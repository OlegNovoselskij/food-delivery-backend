import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config, rate_limit, security
from app.emails import messages
from app.exceptions import EmailAlreadyRegistered, InvalidCode, InvalidCredentials
from app.models.user import User
from app.repository import email_code_repository, user_repository
from app.schemas.user import RegisterRequest
from app.services import email_service

VERIFY_EMAIL = "verify_email"
PASSWORD_RESET = "password_reset"
CODE_REQUESTS_PER_HOUR = 5


def _limit_code_requests(email: str, purpose: str) -> None:
    # per address, whatever the number of client IPs: a mailbox cannot be flooded
    digest = hashlib.sha256(email.encode()).hexdigest()[:16]
    rate_limit.hit(f"rl:code:{purpose}:{digest}", CODE_REQUESTS_PER_HOUR, 3600)


def _cooldown_active(db: Session, user_id: int, purpose: str) -> bool:
    age = email_code_repository.age_seconds(db, user_id, purpose)
    return age is not None and age < config.EMAIL_CODE_RESEND_SECONDS


def _send_code(db: Session, user: User, purpose: str) -> None:
    code = security.generate_code()
    email_code_repository.issue(
        db,
        user.id,
        purpose,
        security.hash_code(user.id, purpose, code),
        timedelta(minutes=config.EMAIL_CODE_TTL_MINUTES),
    )
    build = messages.verification_email if purpose == VERIFY_EMAIL else messages.password_reset_email
    email_service.enqueue(db, user.email, build(user.name, code))


def _consume_code(db: Session, user: User, purpose: str, code: str) -> bool:
    # a wrong guess is counted and COMMITTED right here, so a failing request cannot undo the counter
    stored = email_code_repository.get_for_update(db, user.id, purpose)  # row lock: guesses are sequential
    if stored is None:
        return False
    if not security.codes_match(stored.code_hash, user.id, purpose, code):
        stored.attempts += 1
        if stored.attempts >= config.EMAIL_CODE_MAX_ATTEMPTS:
            email_code_repository.delete(db, stored)
        db.commit()
        return False
    email_code_repository.delete(db, stored)
    return True


def register_user(db: Session, data: RegisterRequest) -> None:
    # The password is chosen in step 2, together with the code. If it were chosen here, anybody could register
    # somebody else's address with their own password, and the owner, confirming the code later, would hand the
    # account over to them ("pre-hijacking").
    email = data.email.lower()
    _limit_code_requests(email, VERIFY_EMAIL)

    user = user_repository.get_by_email(db, email)
    if user is not None and user.email_verified:
        raise EmailAlreadyRegistered()

    try:
        if user is None:
            user = User(
                name=data.name,
                surname=data.surname,
                email=email,
                phone=data.phone,
                bio=data.bio,
                role=data.role,
                password_hash=None,
                email_verified=False,
            )
            user_repository.add(db, user)
        else:  # an unfinished registration: the latest data wins (there is no password that could be taken over)
            user.name, user.surname, user.phone, user.bio, user.role = (
                data.name, data.surname, data.phone, data.bio, data.role,
            )
        if not _cooldown_active(db, user.id, VERIFY_EMAIL):
            _send_code(db, user, VERIFY_EMAIL)
        db.commit()
    except IntegrityError:  # two parallel registrations of one new address: the other request sends the code
        db.rollback()


def resend_code(db: Session, email: str) -> None:
    email = email.lower()
    _limit_code_requests(email, VERIFY_EMAIL)
    user = user_repository.get_by_email(db, email)
    if user is None or user.email_verified or _cooldown_active(db, user.id, VERIFY_EMAIL):
        return  # the same answer for any address: accounts cannot be discovered through this endpoint
    _send_code(db, user, VERIFY_EMAIL)
    db.commit()


def verify_registration(db: Session, email: str, code: str, password: str) -> str:
    user = user_repository.get_by_email(db, email.lower())
    if user is None or user.email_verified:
        raise InvalidCode()
    if not _consume_code(db, user, VERIFY_EMAIL, code):
        raise InvalidCode()

    user.password_hash = security.hash_password(password)
    user.email_verified = True
    db.commit()
    return security.create_access_token(user.id, user.role)


def login(db: Session, email: str, password: str, client_ip: str) -> str:
    email = email.lower()
    guard_key = rate_limit.login_client_key(client_ip, email)
    rate_limit.ensure_login_allowed(guard_key)

    user = user_repository.get_by_email(db, email)
    if not user or not security.verify_password(password, user.password_hash):
        rate_limit.register_login_failure(guard_key)
        raise InvalidCredentials()  # the same error for "no such user", "no password yet" and "wrong password"

    rate_limit.clear_login_failures(guard_key)
    return security.create_access_token(user.id, user.role)


def forgot_password(db: Session, email: str) -> None:
    email = email.lower()
    _limit_code_requests(email, PASSWORD_RESET)
    user = user_repository.get_by_email(db, email)
    if user is None or not user.email_verified or _cooldown_active(db, user.id, PASSWORD_RESET):
        return  # the answer never depends on whether the account exists
    _send_code(db, user, PASSWORD_RESET)
    db.commit()


def reset_password(db: Session, email: str, code: str, new_password: str) -> None:
    user = user_repository.get_by_email(db, email.lower())
    if user is None or not user.email_verified:
        raise InvalidCode()
    if not _consume_code(db, user, PASSWORD_RESET, code):
        raise InvalidCode()

    user.password_hash = security.hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)  # tokens issued before this moment stop working
    db.commit()
