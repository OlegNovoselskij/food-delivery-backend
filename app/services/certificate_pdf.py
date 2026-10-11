import io
import logging
from datetime import datetime

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app import config

logger = logging.getLogger(__name__)

_FONT, _FONT_BOLD = "CertificateFont", "CertificateFont-Bold"
_fonts_ready = False
_unicode_fonts = False


def _register_fonts() -> tuple[str, str]:
    global _fonts_ready, _unicode_fonts
    if not _fonts_ready:
        try:
            pdfmetrics.registerFont(TTFont(_FONT, config.CERTIFICATE_FONT_PATH))
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, config.CERTIFICATE_FONT_BOLD_PATH))
            _unicode_fonts = True
        except Exception:
            logger.warning("Unicode font not found, non-Latin names will not render", exc_info=True)
        _fonts_ready = True
    return (_FONT, _FONT_BOLD) if _unicode_fonts else ("Helvetica", "Helvetica-Bold")


def _draw_qr(pdf: canvas.Canvas, value: str, x: float, y: float, size: float) -> None:
    widget = QrCodeWidget(value)
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    drawing.add(widget)
    renderPDF.draw(drawing, pdf, x, y)


def render_certificate_pdf(
    *,
    student_name: str,
    course_title: str,
    teacher_name: str,
    issued_at: datetime,
    number: str,
    verify_url: str,
) -> bytes:
    font, bold = _register_fonts()
    width, height = landscape(A4)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.setTitle(f"Certificate {number}")

    accent, text, dark = HexColor("#1D4ED8"), HexColor("#374151"), HexColor("#111827")
    center = width / 2

    pdf.setStrokeColor(accent)
    pdf.setLineWidth(4)
    pdf.rect(28, 28, width - 56, height - 56)
    pdf.setLineWidth(1)
    pdf.rect(40, 40, width - 80, height - 80)

    pdf.setFillColor(accent)
    pdf.setFont(bold, 36)
    pdf.drawCentredString(center, height - 120, "Certificate of Completion")

    pdf.setFillColor(text)
    pdf.setFont(font, 16)
    pdf.drawCentredString(center, height - 170, "This certifies that")

    name_size = 34
    while pdf.stringWidth(student_name, bold, name_size) > width - 160 and name_size > 18:
        name_size -= 2
    pdf.setFillColor(dark)
    pdf.setFont(bold, name_size)
    pdf.drawCentredString(center, height - 225, student_name)

    pdf.setFillColor(text)
    pdf.setFont(font, 16)
    pdf.drawCentredString(center, height - 270, "has successfully completed the course")

    pdf.setFillColor(accent)
    pdf.setFont(bold, 24)
    y = height - 315
    for line in simpleSplit(course_title, bold, 24, width - 160)[:3]:
        pdf.drawCentredString(center, y, line)
        y -= 32

    pdf.setFillColor(text)
    pdf.setFont(font, 13)
    pdf.drawString(80, 110, f"Instructor: {teacher_name}")
    pdf.drawString(80, 90, f"Issued: {issued_at:%Y-%m-%d}")
    pdf.drawString(80, 70, f"Certificate No: {number}")

    _draw_qr(pdf, verify_url, width - 160, 60, 80)
    pdf.setFont(font, 9)
    pdf.drawCentredString(width - 120, 48, "Scan to verify")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
