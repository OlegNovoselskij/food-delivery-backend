from sqlalchemy.orm import Session

from app.exceptions import (
    CategoryNotFound,
    CourseNotDeletable,
    CourseNotFound,
    InvalidCourseTransition,
    NotCourseOwner,
)
from app.models.catalog import Course
from app.models.user import User
from app.repository import category_repository, course_repository
from app.schemas.course import CourseCreate, CourseFilters, CourseUpdate

# з якого статусу в які можна перейти
ALLOWED_TRANSITIONS = {
    "draft": {"published"},
    "published": {"archived"},
    "archived": {"published"},
}


def _can_manage(course: Course, user: User) -> bool:
    return user.role == "admin" or course.teacher_id == user.id


def _get_course_for_edit(db: Session, course_id: int, user: User) -> Course:
    course = course_repository.get_by_id(db, course_id)
    if course is None:
        raise CourseNotFound()
    if not _can_manage(course, user):
        raise NotCourseOwner()
    return course


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
    if course.status != "published" and not (viewer and _can_manage(course, viewer)):
        raise CourseNotFound()  # 404, а не 403: чужу чернетку не видно навіть як факт
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
    course = _get_course_for_edit(db, course_id, user)
    changes = data.model_dump(exclude_unset=True)

    if "category_id" in changes and category_repository.get_by_id(db, changes["category_id"]) is None:
        raise CategoryNotFound()

    for field, value in changes.items():
        setattr(course, field, value)
    db.commit()
    return course_repository.get_by_id(db, course_id)


def change_status(db: Session, course_id: int, user: User, target: str) -> Course:
    course = _get_course_for_edit(db, course_id, user)
    if target not in ALLOWED_TRANSITIONS[course.status]:
        raise InvalidCourseTransition()
    course.status = target
    db.commit()
    return course_repository.get_by_id(db, course_id)


def delete_course(db: Session, course_id: int, user: User) -> None:
    course = _get_course_for_edit(db, course_id, user)
    if course.status != "draft":
        raise CourseNotDeletable()
    course_repository.delete(db, course)
    db.commit()