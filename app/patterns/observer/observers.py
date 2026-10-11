import uuid
from datetime import UTC, datetime
from functools import partial

from sqlalchemy.orm import Session

from app import realtime
from app.cache import catalog_cache
from app.emails import messages
from app.models.enrollment import Certificate
from app.models.notification import Notification
from app.patterns.observer.after_commit import run_after_commit
from app.patterns.observer.events import (
    AttemptSubmitted,
    CatalogChanged,
    CourseCompleted,
    DomainEvent,
    PaymentSucceeded,
    QuizGraded,
)
from app.repository import certificate_repository, notification_repository, user_repository
from app.schemas.notification import NotificationOut
from app.services import email_service


class CertificateObserver:
    def on_course_completed(self, db: Session, event: CourseCompleted) -> None:
        if certificate_repository.get_by_enrollment(db, event.enrollment_id) is not None:
            return
        number = f"CERT-{datetime.now(UTC).year}-{uuid.uuid4().hex[:8].upper()}"
        certificate_repository.add(db, Certificate(enrollment_id=event.enrollment_id, certificate_number=number))


class NotificationObserver:
    def on_event(self, db: Session, event: DomainEvent) -> None:
        for draft in self._drafts(db, event):
            notification = notification_repository.add(db, Notification(**draft))
            db.refresh(notification)
            message = {
                "type": "notification",
                "notification": NotificationOut.model_validate(notification).model_dump(mode="json"),
            }
            run_after_commit(db, partial(realtime.publish, notification.user_id, message))

    @staticmethod
    def _drafts(db: Session, event: DomainEvent) -> list[dict]:
        match event:
            case PaymentSucceeded():
                return [
                    {
                        "user_id": event.student_id,
                        "type": "payment_succeeded",
                        "title": "Payment received",
                        "body": f'Payment of {event.amount} received. You are enrolled in "{event.course_title}".',
                        "payload": {"enrollment_id": event.enrollment_id, "course_id": event.course_id},
                    }
                ]
            case AttemptSubmitted():
                return [
                    {
                        "user_id": event.teacher_id,
                        "type": "attempt_pending_review",
                        "title": "New answers to review",
                        "body": f'{event.student_name} submitted "{event.quiz_title}" in "{event.course_title}".',
                        "payload": {"attempt_id": event.attempt_id, "course_id": event.course_id},
                    }
                ]
            case QuizGraded():
                verdict = "passed" if event.passed else "not passed"
                return [
                    {
                        "user_id": event.student_id,
                        "type": "quiz_graded",
                        "title": "Your quiz was graded",
                        "body": f'"{event.quiz_title}": {event.score}% ({verdict}).',
                        "payload": {
                            "attempt_id": event.attempt_id,
                            "quiz_id": event.quiz_id,
                            "course_id": event.course_id,
                            "score": event.score,
                            "passed": event.passed,
                        },
                    }
                ]
            case CourseCompleted():
                certificate = certificate_repository.get_by_enrollment(db, event.enrollment_id)
                return [
                    {
                        "user_id": event.student_id,
                        "type": "course_completed",
                        "title": "Course completed",
                        "body": f'Congratulations! Your certificate for "{event.course_title}" is ready.',
                        "payload": {
                            "enrollment_id": event.enrollment_id,
                            "course_id": event.course_id,
                            "certificate_id": certificate.id if certificate else None,
                            "certificate_number": certificate.certificate_number if certificate else None,
                        },
                    }
                ]
        return []


class CacheInvalidationObserver:
    def on_catalog_changed(self, db: Session, event: CatalogChanged) -> None:
        run_after_commit(db, catalog_cache.invalidate)


class EmailObserver:
    def on_event(self, db: Session, event: DomainEvent) -> None:
        match event:
            case PaymentSucceeded():
                user = user_repository.get_by_id(db, event.student_id)
                email_service.enqueue(
                    db,
                    user.email,
                    messages.payment_receipt_email(user.name, event.course_title, event.amount, event.course_id),
                )
            case CourseCompleted():
                user = user_repository.get_by_id(db, event.student_id)
                certificate = certificate_repository.get_by_enrollment(db, event.enrollment_id)
                if certificate is not None:
                    email_service.enqueue(
                        db,
                        user.email,
                        messages.certificate_email(user.name, event.course_title, certificate.certificate_number),
                        dedupe_key=f"certificate:{event.enrollment_id}",
                    )
