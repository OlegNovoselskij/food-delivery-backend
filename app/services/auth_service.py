from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.models.user import User
from app.repository import user_repository
from app.schemas.user import UserCreate
from app.security import create_access_token, hash_password, verify_password


def register_user(db: Session, data: UserCreate) -> User:
    email = data.email.lower()
    if user_repository.get_by_email(db, email):
        raise EmailAlreadyRegistered()

    user = User(
        name=data.name,
        surname=data.surname,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        bio=data.bio,
        role=data.role,
    )
    try:
        user_repository.add(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegistered()

    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> str:
    user = user_repository.get_by_email(db, email.lower())
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return create_access_token(user.id, user.role)