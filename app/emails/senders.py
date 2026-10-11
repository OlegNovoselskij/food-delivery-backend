import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from app import config
from app.emails.message import EmailSendError, OutgoingEmail

logger = logging.getLogger(__name__)


def _from_header() -> str:
    return formataddr((config.EMAIL_FROM_NAME, config.EMAIL_FROM_ADDRESS))


class EmailSender(ABC):
    @abstractmethod
    def send(self, message: OutgoingEmail) -> None: ...


class ConsoleEmailSender(EmailSender):
    def send(self, message: OutgoingEmail) -> None:
        logger.info("EMAIL to=%s subject=%s\n%s", message.to_email, message.subject, message.text)


class SmtpEmailSender(EmailSender):
    def send(self, message: OutgoingEmail) -> None:
        mime = EmailMessage()
        mime["From"] = _from_header()
        mime["To"] = message.to_email
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
                if config.SMTP_STARTTLS:
                    server.starttls()
                if config.SMTP_USERNAME:
                    server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.send_message(mime)
        except smtplib.SMTPRecipientsRefused as error:
            raise EmailSendError(f"recipient refused: {error}", permanent=True) from error
        except smtplib.SMTPAuthenticationError as error:
            raise EmailSendError(f"SMTP authentication failed: {error}") from error
        except smtplib.SMTPResponseException as error:
            raise EmailSendError(
                f"SMTP error {error.smtp_code}", permanent=500 <= error.smtp_code < 600
            ) from error
        except (smtplib.SMTPException, OSError) as error:
            raise EmailSendError(f"SMTP connection problem: {error}") from error
        except ValueError as error:
            raise EmailSendError(f"invalid message: {error}", permanent=True) from error


def _post_json(url: str, headers: dict, payload: dict) -> None:
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
    except httpx.HTTPError as error:
        raise EmailSendError(f"network problem: {error}") from error
    if response.is_success:
        return
    status = response.status_code
    # 429 and 5xx are temporary; 401/403 mean a wrong API key (fixable); any other 4xx is about this very email
    permanent = 400 <= status < 500 and status not in (401, 403, 429)
    raise EmailSendError(f"HTTP {status}: {response.text[:300]}", permanent=permanent)


class ResendEmailSender(EmailSender):
    URL = "https://api.resend.com/emails"

    def send(self, message: OutgoingEmail) -> None:
        headers = {"Authorization": f"Bearer {config.RESEND_API_KEY}"}
        if message.idempotency_key:
            headers["Idempotency-Key"] = message.idempotency_key
        _post_json(
            self.URL,
            headers,
            {
                "from": _from_header(),
                "to": [message.to_email],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            },
        )


class BrevoEmailSender(EmailSender):
    URL = "https://api.brevo.com/v3/smtp/email"

    def send(self, message: OutgoingEmail) -> None:
        payload = {
            "sender": {"name": config.EMAIL_FROM_NAME, "email": config.EMAIL_FROM_ADDRESS},
            "to": [{"email": message.to_email}],
            "subject": message.subject,
            "htmlContent": message.html,
            "textContent": message.text,
        }
        if message.idempotency_key:
            payload["headers"] = {"Idempotency-Key": message.idempotency_key}
        _post_json(self.URL, {"api-key": config.BREVO_API_KEY, "accept": "application/json"}, payload)


def get_email_sender() -> EmailSender:
    provider = config.EMAIL_PROVIDER.lower()
    if provider == "smtp":
        return SmtpEmailSender()
    if provider == "console":
        return ConsoleEmailSender()
    if provider == "resend":
        if not config.RESEND_API_KEY:
            raise RuntimeError("EMAIL_PROVIDER=resend needs RESEND_API_KEY")
        return ResendEmailSender()
    if provider == "brevo":
        if not config.BREVO_API_KEY:
            raise RuntimeError("EMAIL_PROVIDER=brevo needs BREVO_API_KEY")
        return BrevoEmailSender()
    raise RuntimeError(f"Unknown EMAIL_PROVIDER: {config.EMAIL_PROVIDER}")
