from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user
from app.models.user import User
from app.schemas.enrollment import EnrollmentFilters
from app.schemas.learning import HistoryItemOut, ProgressOut
from app.services import progress_service

router = APIRouter(tags=["learning"])


@router.get("/learning/history", response_model=list[HistoryItemOut])
def learning_history(
    filters: Annotated[EnrollmentFilters, Query()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return progress_service.history(db, user, filters)


@router.get("/enrollments/{enrollment_id}/progress", response_model=ProgressOut)
def get_progress(enrollment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return progress_service.get_progress(db, enrollment_id, user)


@router.post("/enrollments/{enrollment_id}/lessons/{lesson_id}/complete", response_model=ProgressOut)
def mark_lesson_completed(
    enrollment_id: int, lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return progress_service.mark_lesson(db, enrollment_id, lesson_id, user)


@router.delete("/enrollments/{enrollment_id}/lessons/{lesson_id}/complete", response_model=ProgressOut)
def unmark_lesson_completed(
    enrollment_id: int, lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return progress_service.unmark_lesson(db, enrollment_id, lesson_id, user)
