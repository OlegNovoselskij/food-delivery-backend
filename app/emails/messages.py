from decimal import Decimal

from app import config
from app.emails.render import EmailContent

_CODE_FOOTER = (
    f"The code works for {config.EMAIL_CODE_TTL_MINUTES} minutes. Never share it with anyone, "
    "we will never ask for it. If you did not request it, ignore this email."
)


def verification_email(name: str, code: str) -> EmailContent:
    return EmailContent(
        subject="Your confirmation code",
        heading="Confirm your email address",
        paragraphs=[f"Hi {name},", "Use this code to finish creating your account:"],
        code=code,
        footer=_CODE_FOOTER,
    )


def password_reset_email(name: str, code: str) -> EmailContent:
    return EmailContent(
        subject="Your password reset code",
        heading="Reset your password",
        paragraphs=[f"Hi {name},", "Use this code to choose a new password:"],
        code=code,
        footer=_CODE_FOOTER + " Your password stays the same until you use it.",
    )


def payment_receipt_email(name: str, course_title: str, amount: Decimal, course_id: int) -> EmailContent:
    return EmailContent(
        subject=f"Payment received: {course_title}",
        heading="Payment received",
        paragraphs=[
            f"Hi {name},",
            f'We received your payment of {amount} for "{course_title}".',
            "You can start learning right away.",
        ],
        button_label="Open the course",
        button_url=f"{config.FRONTEND_URL}/courses/{course_id}",
    )


def certificate_email(name: str, course_title: str, number: str) -> EmailContent:
    return EmailContent(
        subject="Your certificate is ready",
        heading="Congratulations!",
        paragraphs=[
            f"Hi {name},",
            f'You completed "{course_title}". Your certificate number is {number}.',
        ],
        button_label="View your certificate",
        button_url=f"{config.FRONTEND_URL}/certificates/{number}",
    )
