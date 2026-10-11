from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    AlreadyEnrolled,
    CannotEnrollInOwnCourse,
    CourseNotFound,
    EnrollmentNotFound,
    PaymentDeclined,
    PaymentNotRequired,
    PaymentRefundFailed,
)
from app.models.enrollment import Enrollment, Payment
from app.models.user import User
from app.patterns.adapters.payment_gateway import PaymentGateway
from app.patterns.factories.enrollment_factory import EnrollmentFactory
from app.patterns.states.enrollment_state import EnrollmentStateMachine
from app.repository import course_repository, enrollment_repository
from app.schemas.enrollment import EnrollmentFilters, PayRequest


def _is_visible_to(enrollment: Enrollment, user: User, *, allow_admin: bool) -> bool:
    return enrollment.student_id == user.id or (allow_admin and user.role == "admin")


def _get_locked(db: Session, enrollment_id: int, user: User, *, allow_admin: bool) -> Enrollment:
    enrollment = enrollment_repository.get_by_id_for_update(db, enrollment_id)
    # 404 instead of 403: do not reveal that someone else's enrollment exists
    if enrollment is None or not _is_visible_to(enrollment, user, allow_admin=allow_admin):
        raise EnrollmentNotFound()
    return enrollment


def enroll(db: Session, student: User, course_id: int) -> Enrollment:
    course = course_repository.get_by_id(db, course_id)
    if course is None or course.status != "published":
        raise CourseNotFound()
    if course.teacher_id == student.id:
        raise CannotEnrollInOwnCourse()

    creator = EnrollmentFactory.for_course(course)
    existing = enrollment_repository.get_by_student_and_course(db, student.id, course.id)

    if existing is None:
        enrollment = creator.create(student.id, course.id)
        try:
            enrollment_repository.add(db, enrollment)
            db.commit()
        except IntegrityError:  # parallel requests: the unique constraint lets only one through
            db.rollback()
            raise AlreadyEnrolled()
        return enrollment_repository.get_by_id(db, enrollment.id)

    machine = EnrollmentStateMachine(existing)
    if existing.status == "cancelled":
        machine.reopen(creator.initial_status)
        db.commit()
    elif not machine.accepts_payment():
        raise AlreadyEnrolled()
    return enrollment_repository.get_by_id(db, existing.id)


def pay(
    db: Session, enrollment_id: int, user: User, data: PayRequest, gateway: PaymentGateway
) -> Enrollment:
    enrollment = _get_locked(db, enrollment_id, user, allow_admin=False)
    machine = EnrollmentStateMachine(enrollment)
    if not machine.accepts_payment():
        raise PaymentNotRequired()

    course = enrollment.course
    if course.status != "published":
        raise CourseNotFound()

    result = gateway.charge(amount=course.price, method=data.method, token=data.payment_token)
    payment = Payment(
        enrollment_id=enrollment.id,
        amount=course.price,
        method=data.method,
        status="succeeded" if result.success else "failed",
        transaction_id=result.transaction_id,
    )
    enrollment_repository.add_payment(db, payment)

    if not result.success:
        db.commit()
        raise PaymentDeclined()

    machine.activate()
    db.commit()
    return enrollment_repository.get_by_id(db, enrollment.id)


def cancel(db: Session, enrollment_id: int, user: User, gateway: PaymentGateway) -> Enrollment:
    enrollment = _get_locked(db, enrollment_id, user, allow_admin=True)
    EnrollmentStateMachine(enrollment).cancel()

    for payment in enrollment.payments:
        if payment.status == "succeeded":
            if not gateway.refund(payment.transaction_id):
                db.rollback()
                raise PaymentRefundFailed()
            payment.status = "refunded"
    db.commit()
    return enrollment_repository.get_by_id(db, enrollment.id)


def list_my(db: Session, student: User, filters: EnrollmentFilters) -> list[Enrollment]:
    return enrollment_repository.list_by_student(
        db, student.id, status=filters.status, course_id=filters.course_id
    )


def get_one(db: Session, enrollment_id: int, user: User) -> Enrollment:
    enrollment = enrollment_repository.get_by_id(db, enrollment_id)
    if enrollment is None or not _is_visible_to(enrollment, user, allow_admin=True):
        raise EnrollmentNotFound()
    return enrollment
