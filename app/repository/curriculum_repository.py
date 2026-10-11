from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.catalog import Course, Lesson, Module
from app.models.quiz import Quiz


def get_program_course(db: Session, course_id: int) -> Course | None:
    return (
        db.query(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons),
            selectinload(Course.modules).selectinload(Module.quiz).selectinload(Quiz.questions),
        )
        .populate_existing()
        .filter(Course.id == course_id)
        .first()
    )


def get_module(db: Session, module_id: int) -> Module | None:
    return (
        db.query(Module)
        .options(joinedload(Module.course), selectinload(Module.lessons), joinedload(Module.quiz))
        .populate_existing()
        .filter(Module.id == module_id)
        .first()
    )


def get_lesson(db: Session, lesson_id: int) -> Lesson | None:
    return (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course), selectinload(Lesson.materials))
        .populate_existing()
        .filter(Lesson.id == lesson_id)
        .first()
    )


def list_modules(db: Session, course_id: int) -> list[Module]:
    return db.query(Module).filter(Module.course_id == course_id).all()


def next_module_position(db: Session, course_id: int) -> int:
    max_pos = db.query(func.max(Module.position)).filter(Module.course_id == course_id).scalar()
    return 0 if max_pos is None else max_pos + 1


def next_lesson_position(db: Session, module_id: int) -> int:
    max_pos = db.query(func.max(Lesson.position)).filter(Lesson.module_id == module_id).scalar()
    return 0 if max_pos is None else max_pos + 1


def count_lessons(db: Session, course_id: int) -> int:
    return (
        db.query(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id)
        .scalar()
    )


def add(db: Session, obj: Module | Lesson) -> None:
    db.add(obj)
    db.flush()


def delete(db: Session, obj: Module | Lesson) -> None:
    db.delete(obj)
