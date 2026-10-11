from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.exceptions import LessonLocked, LessonNotFound
from app.models.catalog import Lesson
from app.models.user import User
from app.repository import curriculum_repository, enrollment_repository
from app.services.access import can_manage_course


class LessonContent(ABC):
    @abstractmethod
    def load(self) -> Lesson: ...


class DatabaseLessonContent(LessonContent):
    def __init__(self, db: Session, lesson_id: int) -> None:
        self._db = db
        self._lesson_id = lesson_id

    def load(self) -> Lesson:
        lesson = curriculum_repository.get_lesson(self._db, self._lesson_id)
        if lesson is None:
            raise LessonNotFound()
        return lesson


class LessonAccessProxy(LessonContent):
    def __init__(self, real: LessonContent, db: Session, viewer: User | None) -> None:
        self._real = real
        self._db = db
        self._viewer = viewer

    def load(self) -> Lesson:
        lesson = self._real.load()
        course = lesson.module.course
        is_manager = can_manage_course(course, self._viewer)

        if course.status != "published" and not is_manager:
            raise LessonNotFound()
        if is_manager or lesson.is_preview:
            return lesson
        if self._viewer is not None and enrollment_repository.has_access(self._db, self._viewer.id, course.id):
            return lesson
        raise LessonLocked()
