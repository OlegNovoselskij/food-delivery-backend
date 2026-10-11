from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.attempt import QuizAttempt
from app.models.catalog import Module
from app.models.quiz import Question, Quiz


def get_quiz(db: Session, quiz_id: int) -> Quiz | None:
    return (
        db.query(Quiz)
        .options(
            joinedload(Quiz.module).joinedload(Module.course),
            selectinload(Quiz.questions).selectinload(Question.options),
        )
        .populate_existing()
        .filter(Quiz.id == quiz_id)
        .first()
    )


def get_question(db: Session, question_id: int) -> Question | None:
    return (
        db.query(Question)
        .options(
            joinedload(Question.quiz).joinedload(Quiz.module).joinedload(Module.course),
            selectinload(Question.options),
        )
        .populate_existing()
        .filter(Question.id == question_id)
        .first()
    )


def has_attempts(db: Session, quiz_id: int) -> bool:
    return db.query(QuizAttempt.id).filter(QuizAttempt.quiz_id == quiz_id).first() is not None


def next_question_position(db: Session, quiz_id: int) -> int:
    max_pos = db.query(func.max(Question.position)).filter(Question.quiz_id == quiz_id).scalar()
    return 0 if max_pos is None else max_pos + 1


def add(db: Session, obj: Quiz | Question) -> None:
    db.add(obj)
    db.flush()


def delete(db: Session, obj: Quiz | Question) -> None:
    db.delete(obj)
