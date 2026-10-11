from sqlalchemy.orm import Session

from app.exceptions import CourseNotFound, LessonNotFound, ModuleNotFound, NotCourseOwner
from app.models.catalog import Course, Lesson, Module
from app.models.user import User
from app.repository import course_repository, curriculum_repository, enrollment_repository


def can_manage_course(course: Course, user: User | None) -> bool:
    return user is not None and (user.role == "admin" or course.teacher_id == user.id)


def can_view_course(db: Session, course: Course, viewer: User | None) -> bool:
    if can_manage_course(course, viewer):
        return True
    if course.status == "published":
        return True
    return (
        course.status == "archived"
        and viewer is not None
        and enrollment_repository.has_access(db, viewer.id, course.id)
    )


def get_course_for_edit(db: Session, course_id: int, user: User) -> Course:
    course = course_repository.get_by_id(db, course_id)
    if course is None:
        raise CourseNotFound()
    if not can_manage_course(course, user):
        raise NotCourseOwner()
    return course


def get_module_for_edit(db: Session, module_id: int, user: User) -> Module:
    module = curriculum_repository.get_module(db, module_id)
    if module is None:
        raise ModuleNotFound()
    if not can_manage_course(module.course, user):
        raise NotCourseOwner()
    return module


def get_lesson_for_edit(db: Session, lesson_id: int, user: User) -> Lesson:
    lesson = curriculum_repository.get_lesson(db, lesson_id)
    if lesson is None:
        raise LessonNotFound()
    if not can_manage_course(lesson.module.course, user):
        raise NotCourseOwner()
    return lesson
