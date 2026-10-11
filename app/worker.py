import logging
import signal
import time
from datetime import datetime, timedelta, timezone

from app import config
from app.database import SessionLocal
from app.emails.message import EmailSendError, OutgoingEmail
from app.emails.senders import EmailSender, get_email_sender
from app.models.user import User
from app.repository import email_outbox_repository

logger = logging.getLogger("worker")

MAX_DELAY_SECONDS = 6 * 3600
ABANDONED_AFTER = timedelta(days=7)
CLEANUP_EVERY_SECONDS = 3600
_stop = False


def _request_stop(signum, frame) -> None:
    global _stop
    _stop = True  # finish the current email, then exit


def _retry_delay(attempts: int) -> int:
    return min(config.EMAIL_RETRY_BASE_SECONDS * 5 ** (attempts - 1), MAX_DELAY_SECONDS)


def process_one(sender: EmailSender) -> bool:
    with SessionLocal() as db:
        item = email_outbox_repository.claim_next(db)  # locked until the commit below: other workers skip it
        if item is None:
            return False

        message = OutgoingEmail(
            to_email=item.to_email,
            subject=item.subject,
            text=item.text_body or "",
            html=item.html_body or "",
            idempotency_key=f"email-{item.id}",  # the same key on every retry: providers drop duplicates
        )
        item.attempts += 1
        try:
            sender.send(message)
        except Exception as error:
            if not isinstance(error, EmailSendError):  # a bug must not block the queue: a temporary failure
                error = EmailSendError(f"unexpected error: {error!r}")
            item.last_error = str(error)[:500]
            if error.permanent or item.attempts >= config.EMAIL_MAX_ATTEMPTS:
                item.status = "failed"
                logger.error("Email %s failed for good after %s attempt(s): %s", item.id, item.attempts, error)
            else:
                delay = _retry_delay(item.attempts)
                item.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                logger.warning("Email %s will be retried in %ss: %s", item.id, delay, error)
        else:
            item.status = "sent"
            item.sent_at = datetime.now(timezone.utc)
            item.last_error = None
            item.text_body = None  # one-time codes must not stay in the database
            item.html_body = None
            logger.info("Email %s sent", item.id)  # ids only: no addresses in logs
        db.commit()
        return True


def cleanup_abandoned_registrations() -> None:
    with SessionLocal() as db:
        deleted = (
            db.query(User)
            .filter(
                User.email_verified.is_(False),
                User.password_hash.is_(None),
                User.created_at < datetime.now(timezone.utc) - ABANDONED_AFTER,
            )
            .delete(synchronize_session=False)  # their codes disappear too (ON DELETE CASCADE)
        )
        db.commit()
        if deleted:
            logger.info("Removed %s abandoned registration(s)", deleted)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    sender = get_email_sender()
    logger.info("Email worker started (provider: %s)", config.EMAIL_PROVIDER)

    last_cleanup = 0.0
    while not _stop:
        try:
            if time.monotonic() - last_cleanup > CLEANUP_EVERY_SECONDS:
                cleanup_abandoned_registrations()
                last_cleanup = time.monotonic()
            worked = process_one(sender)
        except Exception:  # for example, the database is not ready yet
            logger.exception("Worker error, pausing")
            time.sleep(5)
            continue
        if not worked:
            time.sleep(config.EMAIL_POLL_SECONDS)  # queue is empty: wait; otherwise take the next email at once
    logger.info("Email worker stopped")


if __name__ == "__main__":
    main()
