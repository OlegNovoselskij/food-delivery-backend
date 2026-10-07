from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_optional_user, require_role
from app.models.user import User
from app.schemas.course import CourseCreate, CourseFilters, CourseOut, CoursePage, CourseUpdate
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=CoursePage)
def list_courses(filters: Annotated[CourseFilters, Query()], db: Session = Depends(get_db)):
    items, total = course_service.search_courses(db, filters)
    return {"items": items, "total": total, "page": filters.page, "size": filters.size}


# УВАГА: "/mine" має бути ДО "/{course_id}", інакше слово "mine" спробують розібрати як число
@router.get("/mine", response_model=list[CourseOut])
def my_courses(teacher: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    return course_service.list_my_courses(db, teacher)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return course_service.get_course_for_viewer(db, course_id, viewer)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    data: CourseCreate,
    teacher: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    return course_service.create_course(db, teacher, data)


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    data: CourseUpdate,
    user: User = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    return course_service.update_course(db, course_id, user, data)


@router.post("/{course_id}/publish", response_model=CourseOut)
def publish_course(
    course_id: int,
    user: User = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    return course_service.change_status(db, course_id, user, "published")


@router.post("/{course_id}/archive", response_model=CourseOut)
def archive_course(
    course_id: int,
    user: User = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    return course_service.change_status(db, course_id, user, "archived")


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    user: User = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    course_service.delete_course(db, course_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)