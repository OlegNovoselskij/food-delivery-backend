from sqlalchemy.orm import Session

from app.emails.render import EmailContent, render
from app.repository import email_outbox_repository


def enqueue(db: Session, to_email: str, content: EmailContent, *, dedupe_key: str | None = None) -> None:
    # the email exists if and only if the caller's transaction is committed; the worker sends it later
    subject, text, html = render(content)
    email_outbox_repository.add(
        db, to_email=to_email, subject=subject, text_body=text, html_body=html, dedupe_key=dedupe_key
    )
