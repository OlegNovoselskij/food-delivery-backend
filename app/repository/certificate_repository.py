from sqlalchemy.orm import Session, joinedload

from app.models.catalog import Course
from app.models.enrollment import Certificate, Enrollment


def _with_relations(query):
    return query.options(
        joinedload(Certificate.enrollment).joinedload(Enrollment.student),
        joinedload(Certificate.enrollment).joinedload(Enrollment.course).joinedload(Course.teacher),
    )


def get_by_enrollment(db: Session, enrollment_id: int) -> Certificate | None:
    return db.query(Certificate).filter(Certificate.enrollment_id == enrollment_id).first()


def get_by_id(db: Session, certificate_id: int) -> Certificate | None:
    return _with_relations(db.query(Certificate)).filter(Certificate.id == certificate_id).first()


def get_by_number(db: Session, number: str) -> Certificate | None:
    return _with_relations(db.query(Certificate)).filter(Certificate.certificate_number == number).first()


def list_by_student(db: Session, student_id: int) -> list[Certificate]:
    return (
        _with_relations(db.query(Certificate))
        .join(Enrollment, Certificate.enrollment_id == Enrollment.id)
        .filter(Enrollment.student_id == student_id)
        .order_by(Certificate.issued_at.desc())
        .all()
    )


def add(db: Session, certificate: Certificate) -> Certificate:
    db.add(certificate)
    db.flush()
    return certificate
