from dataclasses import dataclass, field

from jinja2 import Environment

_env = Environment(autoescape=True)  # names and course titles are user input: everything is escaped

_LAYOUT = _env.from_string(
    """<!doctype html>
<html><body style="margin:0;padding:24px;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
<div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:8px;padding:32px;">
<h1 style="font-size:20px;margin:0 0 16px;">{{ heading }}</h1>
{% for paragraph in paragraphs %}<p style="font-size:15px;line-height:1.6;margin:0 0 12px;">{{ paragraph }}</p>
{% endfor %}{% if code %}<p style="font-size:32px;font-weight:bold;letter-spacing:8px;text-align:center;background:#f3f4f6;padding:16px;border-radius:6px;font-family:Consolas,Menlo,monospace;margin:20px 0;">{{ code }}</p>
{% endif %}{% if button_url %}<p style="margin:24px 0;"><a href="{{ button_url }}" style="background:#1d4ed8;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:6px;display:inline-block;">{{ button_label }}</a></p>
<p style="font-size:12px;color:#6b7280;margin:0 0 12px;">If the button does not work, copy this link into your browser:<br>{{ button_url }}</p>
{% endif %}<p style="font-size:12px;color:#6b7280;margin:24px 0 0;">{{ footer }}</p>
</div></body></html>"""
)


@dataclass(frozen=True)
class EmailContent:
    subject: str
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    code: str | None = None
    button_label: str | None = None
    button_url: str | None = None
    footer: str = "You received this email because of your activity on Online Courses."


def render(content: EmailContent) -> tuple[str, str, str]:
    subject = " ".join(content.subject.split())  # a line break inside a subject would break the email headers
    html = _LAYOUT.render(
        heading=content.heading,
        paragraphs=content.paragraphs,
        code=content.code,
        button_label=content.button_label,
        button_url=content.button_url,
        footer=content.footer,
    )
    lines = [content.heading, "", *content.paragraphs]
    if content.code:
        lines += ["", content.code]
    if content.button_url:
        lines += ["", f"{content.button_label}: {content.button_url}"]
    lines += ["", "--", content.footer]
    return subject, "\n".join(lines), html
