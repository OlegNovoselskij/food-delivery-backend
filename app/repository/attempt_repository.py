from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.catalog import Course, Module
from app.models.enrollment import Enrollment
from app.models.quiz import Question, Quiz


def get_for_update(db: Session, attempt_id: int) -> QuizAttempt | None:
    return db.query(QuizAttempt).populate_existing().filter(QuizAttempt.id == attempt_id).with_for_update().first()


def get_full(db: Session, attempt_id: int) -> QuizAttempt | None:
    return (
        db.query(QuizAttempt)
        .options(
            joinedload(QuizAttempt.enrollment),
            joinedload(QuizAttempt.quiz).joinedload(Quiz.module).joinedload(Module.course),
            joinedload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options),
            selectinload(QuizAttempt.answers),
        )
        .populate_existing()
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )


def find_open(db: Session, enrollment_id: int, quiz_id: int) -> QuizAttempt | None:
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.enrollment_id == enrollment_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "in_progress",
        )
        .first()
    )


def count_submitted(db: Session, enrollment_id: int, quiz_id: int) -> int:
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.enrollment_id == enrollment_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status != "in_progress",
        )
        .count()
    )


def has_passed(db: Session, enrollment_id: int, quiz_id: int) -> bool:
    return (
        db.query(QuizAttempt.id)
        .filter(
            QuizAttempt.enrollment_id == enrollment_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.passed.is_(True),
        )
        .first()
        is not None
    )


def has_pending(db: Session, enrollment_id: int, quiz_id: int) -> bool:
    return (
        db.query(QuizAttempt.id)
        .filter(
            QuizAttempt.enrollment_id == enrollment_id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "pending_review",
        )
        .first()
        is not None
    )


def list_for_enrollment(db: Session, enrollment_id: int, quiz_id: int) -> list[QuizAttempt]:
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.enrollment_id == enrollment_id, QuizAttempt.quiz_id == quiz_id)
        .order_by(QuizAttempt.id)
        .all()
    )


def list_pending_review(db: Session, teacher_id: int | None) -> list[QuizAttempt]:
    query = (
        db.query(QuizAttempt)
        .options(
            joinedload(QuizAttempt.enrollment).joinedload(Enrollment.student),
            joinedload(QuizAttempt.quiz).joinedload(Quiz.module).joinedload(Module.course),
        )
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Module, Quiz.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(QuizAttempt.status == "pending_review")
    )
    if teacher_id is not None:
        query = query.filter(Course.teacher_id == teacher_id)
    return query.order_by(QuizAttempt.submitted_at.asc()).all()


def add(db: Session, attempt: QuizAttempt) -> QuizAttempt:
    db.add(attempt)
    db.flush()
    return attempt


def add_answer(db: Session, answer: AttemptAnswer) -> None:
    db.add(answer)
