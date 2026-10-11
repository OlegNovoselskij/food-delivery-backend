from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_optional_user, get_storage, require_role
from app.models.user import User
from app.schemas.curriculum import (
    LessonCreate,
    LessonOut,
    LessonUpdate,
    ModuleCreate,
    ModuleOut,
    ModuleUpdate,
    OrderUpdate,
    ProgramOut,
)
from app.services import curriculum_service
from app.storage import S3Storage

router = APIRouter(tags=["curriculum"])

staff_only = require_role("teacher", "admin")


@router.get("/courses/{course_id}/program", response_model=ProgramOut)
def get_program(
    course_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    course = curriculum_service.get_program(db, course_id, viewer)
    return curriculum_service.build_program(course)


@router.post("/courses/{course_id}/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(
    course_id: int,
    data: ModuleCreate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    return curriculum_service.create_module(db, course_id, user, data)


@router.put("/courses/{course_id}/modules/order", response_model=ProgramOut)
def reorder_modules(
    course_id: int,
    data: OrderUpdate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    course = curriculum_service.reorder_modules(db, course_id, user, data.ids)
    return curriculum_service.build_program(course)


@router.patch("/modules/{module_id}", response_model=ModuleOut)
def update_module(
    module_id: int,
    data: ModuleUpdate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    return curriculum_service.update_module(db, module_id, user, data)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    curriculum_service.delete_module(db, module_id, user, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/modules/{module_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(
    module_id: int,
    data: LessonCreate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    return curriculum_service.create_lesson(db, module_id, user, data)


@router.put("/modules/{module_id}/lessons/order", response_model=ModuleOut)
def reorder_lessons(
    module_id: int,
    data: OrderUpdate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    return curriculum_service.reorder_lessons(db, module_id, user, data.ids)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return curriculum_service.get_lesson_for_viewer(db, lesson_id, viewer)


@router.patch("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: int,
    data: LessonUpdate,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    return curriculum_service.update_lesson(db, lesson_id, user, data)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    curriculum_service.delete_lesson(db, lesson_id, user, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
