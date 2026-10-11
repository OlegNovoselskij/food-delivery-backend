from sqlalchemy.orm import Session

from app.exceptions import CourseHasEnrollments, CourseNotFound
from app.models.catalog import Course, Lesson, Module
from app.models.user import User
from app.patterns.proxy.lesson_access import DatabaseLessonContent, LessonAccessProxy
from app.repository import curriculum_repository, enrollment_repository, media_repository
from app.schemas.curriculum import LessonCreate, LessonUpdate, ModuleCreate, ModuleUpdate
from app.services.access import can_view_course, get_course_for_edit, get_lesson_for_edit, get_module_for_edit
from app.services.ordering import apply_order
from app.storage import S3Storage


def _ensure_no_enrollments(db: Session, course_id: int) -> None:
    # deleting content would cascade-delete students' progress
    if enrollment_repository.course_has_enrollments(db, course_id):
        raise CourseHasEnrollments()


def get_program(db: Session, course_id: int, viewer: User | None) -> Course:
    course = curriculum_repository.get_program_course(db, course_id)
    if course is None or not can_view_course(db, course, viewer):
        raise CourseNotFound()
    return course


def build_program(course: Course) -> dict:
    lessons = [lesson for module in course.modules for lesson in module.lessons]
    return {
        "course_id": course.id,
        "total_lessons": len(lessons),
        "total_duration_minutes": sum(lesson.duration_minutes or 0 for lesson in lessons),
        "modules": course.modules,
    }


def get_lesson_for_viewer(db: Session, lesson_id: int, viewer: User | None) -> Lesson:
    return LessonAccessProxy(DatabaseLessonContent(db, lesson_id), db, viewer).load()


def create_module(db: Session, course_id: int, user: User, data: ModuleCreate) -> Module:
    course = get_course_for_edit(db, course_id, user)
    module = Module(
        course_id=course.id,
        title=data.title,
        position=curriculum_repository.next_module_position(db, course.id),
    )
    curriculum_repository.add(db, module)
    db.commit()
    return curriculum_repository.get_module(db, module.id)


def update_module(db: Session, module_id: int, user: User, data: ModuleUpdate) -> Module:
    module = get_module_for_edit(db, module_id, user)
    module.title = data.title
    db.commit()
    return curriculum_repository.get_module(db, module_id)


def delete_module(db: Session, module_id: int, user: User, storage: S3Storage) -> None:
    module = get_module_for_edit(db, module_id, user)
    _ensure_no_enrollments(db, module.course_id)
    keys = media_repository.storage_keys(db, module_id=module.id)  # collect BEFORE the cascade delete
    curriculum_repository.delete(db, module)
    db.commit()
    storage.delete_many(keys)


def reorder_modules(db: Session, course_id: int, user: User, ids: list[int]) -> Course:
    course = get_course_for_edit(db, course_id, user)
    apply_order(curriculum_repository.list_modules(db, course.id), ids)
    db.commit()
    return curriculum_repository.get_program_course(db, course.id)


def create_lesson(db: Session, module_id: int, user: User, data: LessonCreate) -> Lesson:
    module = get_module_for_edit(db, module_id, user)
    lesson = Lesson(
        module_id=module.id,
        position=curriculum_repository.next_lesson_position(db, module.id),
        **data.model_dump(),
    )
    curriculum_repository.add(db, lesson)
    db.commit()
    return curriculum_repository.get_lesson(db, lesson.id)


def update_lesson(db: Session, lesson_id: int, user: User, data: LessonUpdate) -> Lesson:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    db.commit()
    return curriculum_repository.get_lesson(db, lesson_id)


def delete_lesson(db: Session, lesson_id: int, user: User, storage: S3Storage) -> None:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    _ensure_no_enrollments(db, lesson.module.course_id)
    keys = media_repository.storage_keys(db, lesson_id=lesson.id)
    curriculum_repository.delete(db, lesson)
    db.commit()
    storage.delete_many(keys)


def reorder_lessons(db: Session, module_id: int, user: User, ids: list[int]) -> Module:
    module = get_module_for_edit(db, module_id, user)
    apply_order(list(module.lessons), ids)
    db.commit()
    return curriculum_repository.get_module(db, module_id)
