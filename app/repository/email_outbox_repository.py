from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.email_outbox import EmailOutbox


def add(db: Session, *, to_email: str, subject: str, text_body: str, html_body: str, dedupe_key: str | None) -> None:
    statement = (
        insert(EmailOutbox)
        .values(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body, dedupe_key=dedupe_key)
        .on_conflict_do_nothing(index_elements=["dedupe_key"])  # NULL keys never conflict
    )
    db.execute(statement)


def claim_next(db: Session) -> EmailOutbox | None:
    return (
        db.query(EmailOutbox)
        .filter(EmailOutbox.status == "pending", EmailOutbox.next_attempt_at <= func.now())
        .order_by(EmailOutbox.id)
        .with_for_update(skip_locked=True)
        .first()
    )
