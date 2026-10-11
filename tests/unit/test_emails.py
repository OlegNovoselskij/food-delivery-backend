import httpx
import pytest

from app import config
from app.emails import senders
from app.emails.message import EmailSendError, OutgoingEmail
from app.emails.render import EmailContent, render


def test_user_input_is_escaped_and_the_subject_stays_on_one_line():
    subject, text, html = render(
        EmailContent(
            subject="Hi\r\nBcc: evil@example.com",
            heading="<b>Heading</b>",
            paragraphs=["<script>alert(1)</script>"],
            code="123456",
        )
    )
    assert subject == "Hi Bcc: evil@example.com"
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "123456" in text and "123456" in html


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status_code = status
        self.text = "body"

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


@pytest.mark.parametrize(
    ("status", "permanent"),
    [(400, True), (404, True), (422, True), (401, False), (403, False), (429, False), (500, False), (503, False)],
)
def test_http_errors_are_classified(monkeypatch, status, permanent):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse(status))
    with pytest.raises(EmailSendError) as error:
        senders._post_json("http://provider.test", {}, {})
    assert error.value.permanent is permanent


def test_a_successful_response_raises_nothing(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse(202))
    senders._post_json("http://provider.test", {}, {})


def test_network_problems_are_temporary(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    with pytest.raises(EmailSendError) as error:
        senders._post_json("http://provider.test", {}, {})
    assert error.value.permanent is False


def test_resend_receives_the_idempotency_key(monkeypatch):
    captured = {}

    def post(url, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers)
        return FakeResponse(200)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test")
    senders.ResendEmailSender().send(OutgoingEmail("to@example.com", "Subject", "text", "<p>html</p>", "email-7"))
    assert captured["headers"]["Idempotency-Key"] == "email-7"
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["json"]["to"] == ["to@example.com"]


def test_the_factory_validates_provider_settings(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    with pytest.raises(RuntimeError):
        senders.get_email_sender()
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test")
    assert isinstance(senders.get_email_sender(), senders.ResendEmailSender)
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "unknown")
    with pytest.raises(RuntimeError):
        senders.get_email_sender()
