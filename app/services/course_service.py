from sqlalchemy.orm import Session

from app.exceptions import (
    CategoryNotFound,
    CourseIncomplete,
    CourseNotDeletable,
    CourseNotFound,
    InvalidCourseTransition,
)
from app.models.catalog import Course
from app.models.user import User
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CatalogChanged
from app.repository import category_repository, course_repository, curriculum_repository, media_repository
from app.schemas.course import CourseCreate, CourseFilters, CourseUpdate
from app.services.access import can_view_course, get_course_for_edit
from app.storage import S3Storage

# allowed status transitions: current status -> possible next statuses
ALLOWED_TRANSITIONS = {
    "draft": {"published"},
    "published": {"archived"},
    "archived": {"published"},
}


def search_courses(db: Session, filters: CourseFilters) -> tuple[list[Course], int]:
    return course_repository.search(
        db,
        **filters.model_dump(exclude={"page", "size"}),
        offset=(filters.page - 1) * filters.size,
        limit=filters.size,
    )


def get_course_for_viewer(db: Session, course_id: int, viewer: User | None) -> Course:
    course = course_repository.get_by_id(db, course_id)
    if course is None:
        raise CourseNotFound()
    if not can_view_course(db, course, viewer):
        raise CourseNotFound()  # 404 instead of 403: do not reveal that someone else's draft exists
    return course


def list_my_courses(db: Session, teacher: User) -> list[Course]:
    return course_repository.list_by_teacher(db, teacher.id)


def create_course(db: Session, teacher: User, data: CourseCreate) -> Course:
    if category_repository.get_by_id(db, data.category_id) is None:
        raise CategoryNotFound()
    course = Course(teacher_id=teacher.id, status="draft", **data.model_dump())
    course_repository.add(db, course)
    db.commit()
    return course_repository.get_by_id(db, course.id)


def update_course(db: Session, course_id: int, user: User, data: CourseUpdate) -> Course:
    course = get_course_for_edit(db, course_id, user)
    changes = data.model_dump(exclude_unset=True)

    if "category_id" in changes and category_repository.get_by_id(db, changes["category_id"]) is None:
        raise CategoryNotFound()

    for field, value in changes.items():
        setattr(course, field, value)
    event_bus.publish(db, CatalogChanged(reason="course_updated"))
    db.commit()
    return course_repository.get_by_id(db, course_id)


def change_status(db: Session, course_id: int, user: User, target: str) -> Course:
    course = get_course_for_edit(db, course_id, user)
    if target not in ALLOWED_TRANSITIONS[course.status]:
        raise InvalidCourseTransition()
    if target == "published" and curriculum_repository.count_lessons(db, course_id) == 0:
        raise CourseIncomplete()
    course.status = target
    event_bus.publish(db, CatalogChanged(reason="course_updated"))
    db.commit()
    return course_repository.get_by_id(db, course_id)


def delete_course(db: Session, course_id: int, user: User, storage: S3Storage) -> None:
    course = get_course_for_edit(db, course_id, user)
    if course.status != "draft":
        raise CourseNotDeletable()
    keys = [*media_repository.storage_keys(db, course_id=course.id), course.cover_key]
    course_repository.delete(db, course)
    db.commit()
    storage.delete_many(keys)
