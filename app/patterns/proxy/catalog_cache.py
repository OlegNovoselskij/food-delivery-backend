import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from app.cache import CatalogCache
from app.models.user import User
from app.schemas.course import CourseFilters, CourseListItem, CourseOut, CoursePage
from app.services import course_service


@dataclass(frozen=True)
class CatalogResult:
    body: str
    public: bool
    cache: str = "BYPASS"


class CatalogReader(ABC):
    @abstractmethod
    def list_courses(self, db: Session, filters: CourseFilters) -> CatalogResult: ...

    @abstractmethod
    def get_course(self, db: Session, course_id: int, viewer: User | None) -> CatalogResult: ...


class DatabaseCatalogReader(CatalogReader):
    def list_courses(self, db: Session, filters: CourseFilters) -> CatalogResult:
        courses, total = course_service.search_courses(db, filters)
        page = CoursePage(
            items=[CourseListItem.model_validate(course) for course in courses],
            total=total,
            page=filters.page,
            size=filters.size,
        )
        return CatalogResult(body=page.model_dump_json(), public=True)

    def get_course(self, db: Session, course_id: int, viewer: User | None) -> CatalogResult:
        course = course_service.get_course_for_viewer(db, course_id, viewer)
        return CatalogResult(
            body=CourseOut.model_validate(course).model_dump_json(),
            public=course.status == "published",
        )


class CachingCatalogProxy(CatalogReader):
    def __init__(self, real: CatalogReader, cache: CatalogCache) -> None:
        self._real = real
        self._cache = cache

    def list_courses(self, db: Session, filters: CourseFilters) -> CatalogResult:
        digest = hashlib.sha1(json.dumps(filters.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
        cached, key = self._cache.lookup(f"list:{digest[:16]}")
        if cached is not None:
            return CatalogResult(body=cached, public=True, cache="HIT")

        result = self._real.list_courses(db, filters)
        self._cache.store(key, result.body)
        return replace(result, cache="MISS" if key else "BYPASS")

    def get_course(self, db: Session, course_id: int, viewer: User | None) -> CatalogResult:
        cached, key = self._cache.lookup(f"course:{course_id}")
        if cached is not None:
            return CatalogResult(body=cached, public=True, cache="HIT")  # only published courses are ever stored

        result = self._real.get_course(db, course_id, viewer)
        if result.public:
            self._cache.store(key, result.body)
        return replace(result, cache="MISS" if (result.public and key) else "BYPASS")
