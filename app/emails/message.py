from dataclasses import dataclass


class EmailSendError(Exception):
    def __init__(self, message: str, *, permanent: bool = False) -> None:
        super().__init__(message)
        self.permanent = permanent


@dataclass(frozen=True)
class OutgoingEmail:
    to_email: str
    subject: str
    text: str
    html: str
    idempotency_key: str | None = None
