from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.catalog import Course
from app.models.enrollment import Enrollment, Payment

ACCESS_STATUSES = ("active", "completed")


def _with_relations(query):
    return query.options(
        joinedload(Enrollment.course).joinedload(Course.teacher),
        joinedload(Enrollment.course).joinedload(Course.category),
        selectinload(Enrollment.payments),
    )


def get_by_id(db: Session, enrollment_id: int) -> Enrollment | None:
    return (
        _with_relations(db.query(Enrollment))
        .populate_existing()
        .filter(Enrollment.id == enrollment_id)
        .first()
    )


def get_by_id_for_update(db: Session, enrollment_id: int) -> Enrollment | None:
    return db.query(Enrollment).filter(Enrollment.id == enrollment_id).with_for_update().first()


def get_by_student_and_course(db: Session, student_id: int, course_id: int) -> Enrollment | None:
    return (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
        .first()
    )


def list_by_student(
    db: Session, student_id: int, *, status: str | None = None, course_id: int | None = None
) -> list[Enrollment]:
    query = _with_relations(db.query(Enrollment)).filter(Enrollment.student_id == student_id)
    if status is not None:
        query = query.filter(Enrollment.status == status)
    if course_id is not None:
        query = query.filter(Enrollment.course_id == course_id)
    return query.order_by(Enrollment.enrolled_at.desc(), Enrollment.id.desc()).all()


def add(db: Session, enrollment: Enrollment) -> Enrollment:
    db.add(enrollment)
    db.flush()
    return enrollment


def add_payment(db: Session, payment: Payment) -> Payment:
    db.add(payment)
    db.flush()
    return payment


def has_access(db: Session, student_id: int, course_id: int) -> bool:
    return (
        db.query(Enrollment.id)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status.in_(ACCESS_STATUSES),
        )
        .first()
        is not None
    )


def course_has_enrollments(db: Session, course_id: int) -> bool:
    return db.query(Enrollment.id).filter(Enrollment.course_id == course_id).first() is not None
