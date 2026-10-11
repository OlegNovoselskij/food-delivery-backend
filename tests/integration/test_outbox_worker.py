from datetime import UTC, datetime

from app import config, worker
from app.emails.message import EmailSendError
from app.emails.render import EmailContent
from app.models.email_outbox import EmailOutbox
from app.services import email_service


class RecordingSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent = []

    def send(self, message) -> None:
        if self.error:
            raise self.error
        self.sent.append(message)


def queue(db, **kwargs) -> None:
    email_service.enqueue(
        db, "to@example.com", EmailContent(subject="Hello", heading="Hi", paragraphs=["Body"]), **kwargs
    )
    db.commit()


def only_row(db) -> EmailOutbox:
    db.expire_all()
    return db.query(EmailOutbox).one()


def test_a_sent_email_is_marked_and_its_body_is_removed(db):
    queue(db)
    sender = RecordingSender()
    assert worker.process_one(sender) is True
    row = only_row(db)
    assert row.status == "sent" and row.attempts == 1 and row.text_body is None and row.html_body is None
    assert sender.sent[0].to_email == "to@example.com" and sender.sent[0].idempotency_key == f"email-{row.id}"
    assert worker.process_one(sender) is False


def test_a_temporary_failure_is_retried_later(db):
    queue(db)
    assert worker.process_one(RecordingSender(EmailSendError("timeout"))) is True
    row = only_row(db)
    assert row.status == "pending" and row.attempts == 1 and "timeout" in row.last_error
    assert row.next_attempt_at > datetime.now(UTC)
    assert worker.process_one(RecordingSender()) is False


def test_a_permanent_failure_is_final(db):
    queue(db)
    worker.process_one(RecordingSender(EmailSendError("no such mailbox", permanent=True)))
    assert only_row(db).status == "failed"


def test_the_attempt_limit_ends_the_retries(db, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_MAX_ATTEMPTS", 1)
    queue(db)
    worker.process_one(RecordingSender(EmailSendError("timeout")))
    assert only_row(db).status == "failed"


def test_an_unexpected_error_does_not_block_the_queue(db):
    queue(db)
    worker.process_one(RecordingSender(RuntimeError("boom")))
    row = only_row(db)
    assert row.status == "pending" and "unexpected error" in row.last_error


def test_the_same_logical_email_is_queued_once(db):
    queue(db, dedupe_key="certificate:1")
    queue(db, dedupe_key="certificate:1")
    assert db.query(EmailOutbox).count() == 1
