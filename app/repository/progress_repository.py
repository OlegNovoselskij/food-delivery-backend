from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attempt import QuizAttempt
from app.models.catalog import Lesson, Module
from app.models.enrollment import LessonProgress
from app.models.quiz import Quiz


def get_progress(db: Session, enrollment_id: int, lesson_id: int) -> LessonProgress | None:
    return (
        db.query(LessonProgress)
        .filter(LessonProgress.enrollment_id == enrollment_id, LessonProgress.lesson_id == lesson_id)
        .first()
    )


def add(db: Session, progress: LessonProgress) -> LessonProgress:
    db.add(progress)
    db.flush()
    return progress


def delete(db: Session, progress: LessonProgress) -> None:
    db.delete(progress)
    db.flush()


def completed_map(db: Session, enrollment_id: int) -> dict[int, datetime]:
    rows = (
        db.query(LessonProgress.lesson_id, LessonProgress.completed_at)
        .filter(LessonProgress.enrollment_id == enrollment_id)
        .all()
    )
    return {lesson_id: completed_at for lesson_id, completed_at in rows}


def passed_quiz_ids(db: Session, enrollment_id: int) -> set[int]:
    rows = (
        db.query(QuizAttempt.quiz_id)
        .filter(QuizAttempt.enrollment_id == enrollment_id, QuizAttempt.passed.is_(True))
        .distinct()
        .all()
    )
    return {quiz_id for (quiz_id,) in rows}


def completed_counts(db: Session, enrollment_ids: list[int]) -> dict[int, tuple[int, int, datetime | None]]:
    rows = (
        db.query(
            LessonProgress.enrollment_id,
            func.count(LessonProgress.id),
            func.coalesce(func.sum(Lesson.duration_minutes), 0),
            func.max(LessonProgress.completed_at),
        )
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .filter(LessonProgress.enrollment_id.in_(enrollment_ids))
        .group_by(LessonProgress.enrollment_id)
        .all()
    )
    return {eid: (int(done), int(minutes), last) for eid, done, minutes, last in rows}


def passed_quiz_counts(db: Session, enrollment_ids: list[int]) -> dict[int, int]:
    rows = (
        db.query(QuizAttempt.enrollment_id, func.count(func.distinct(QuizAttempt.quiz_id)))
        .filter(QuizAttempt.enrollment_id.in_(enrollment_ids), QuizAttempt.passed.is_(True))
        .group_by(QuizAttempt.enrollment_id)
        .all()
    )
    return {eid: int(count) for eid, count in rows}


def course_totals(db: Session, course_ids: list[int]) -> dict[int, tuple[int, int, int]]:
    lesson_rows = (
        db.query(Module.course_id, func.count(Lesson.id), func.coalesce(func.sum(Lesson.duration_minutes), 0))
        .join(Lesson, Lesson.module_id == Module.id)
        .filter(Module.course_id.in_(course_ids))
        .group_by(Module.course_id)
        .all()
    )
    quiz_rows = (
        db.query(Module.course_id, func.count(Quiz.id))
        .join(Quiz, Quiz.module_id == Module.id)
        .filter(Module.course_id.in_(course_ids))
        .group_by(Module.course_id)
        .all()
    )
    totals = {cid: [int(lessons), int(minutes), 0] for cid, lessons, minutes in lesson_rows}
    for cid, quizzes in quiz_rows:
        totals.setdefault(cid, [0, 0, 0])[2] = int(quizzes)
    return {cid: tuple(values) for cid, values in totals.items()}
