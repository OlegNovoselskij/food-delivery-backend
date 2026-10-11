from sqlalchemy.orm import Session

from app import config
from app.exceptions import CertificateNotFound
from app.models.enrollment import Certificate
from app.models.user import User
from app.repository import certificate_repository
from app.services.certificate_pdf import render_certificate_pdf


def _view(certificate: Certificate) -> dict:
    enrollment = certificate.enrollment
    course = enrollment.course
    return {
        "id": certificate.id,
        "certificate_number": certificate.certificate_number,
        "issued_at": certificate.issued_at,
        "enrollment_id": enrollment.id,
        "course_id": course.id,
        "course_title": course.title,
        "student_name": f"{enrollment.student.name} {enrollment.student.surname}",
        "teacher_name": f"{course.teacher.name} {course.teacher.surname}",
    }


def list_mine(db: Session, student: User) -> list[dict]:
    return [_view(certificate) for certificate in certificate_repository.list_by_student(db, student.id)]


def verify(db: Session, number: str) -> dict:
    certificate = certificate_repository.get_by_number(db, number.strip().upper())
    if certificate is None:
        raise CertificateNotFound()
    return _view(certificate)


def render_pdf(db: Session, certificate_id: int, user: User) -> tuple[bytes, str]:
    certificate = certificate_repository.get_by_id(db, certificate_id)
    is_owner = certificate is not None and certificate.enrollment.student_id == user.id
    if certificate is None or not (is_owner or user.role == "admin"):
        raise CertificateNotFound()  # 404 instead of 403: do not reveal that someone else's certificate exists

    view = _view(certificate)
    pdf = render_certificate_pdf(
        student_name=view["student_name"],
        course_title=view["course_title"],
        teacher_name=view["teacher_name"],
        issued_at=view["issued_at"],
        number=view["certificate_number"],
        verify_url=f"{config.PUBLIC_API_URL}/api/v1/certificates/verify/{view['certificate_number']}",
    )
    return pdf, f"certificate-{view['certificate_number']}.pdf"
