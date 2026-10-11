from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.email_code import EmailCode


def issue(db: Session, user_id: int, purpose: str, code_hash: str, ttl: timedelta) -> None:
    expires_at = datetime.now(UTC) + ttl
    statement = insert(EmailCode).values(
        user_id=user_id, purpose=purpose, code_hash=code_hash, attempts=0, expires_at=expires_at
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["user_id", "purpose"],
            set_={"code_hash": code_hash, "attempts": 0, "expires_at": expires_at, "created_at": func.now()},
        )
    )


def get_for_update(db: Session, user_id: int, purpose: str) -> EmailCode | None:
    return (
        db.query(EmailCode)
        .populate_existing()
        .filter(EmailCode.user_id == user_id, EmailCode.purpose == purpose, EmailCode.expires_at > func.now())
        .with_for_update()
        .first()
    )


def age_seconds(db: Session, user_id: int, purpose: str) -> float | None:
    return (
        db.query(func.extract("epoch", func.now() - EmailCode.created_at))
        .filter(EmailCode.user_id == user_id, EmailCode.purpose == purpose)
        .scalar()
    )


def delete(db: Session, code: EmailCode) -> None:
    db.delete(code)
