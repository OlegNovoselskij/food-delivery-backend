from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewFilters, ReviewOut, ReviewPage, ReviewUpdate
from app.services import review_service

router = APIRouter(tags=["reviews"])


@router.get("/courses/{course_id}/reviews", response_model=ReviewPage)
def list_reviews(
    course_id: int,
    filters: Annotated[ReviewFilters, Query()],
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return review_service.list_reviews(db, course_id, viewer, filters)


@router.post("/courses/{course_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    course_id: int,
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.create_review(db, user, course_id, data)


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    data: ReviewUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.update_review(db, review_id, user, data)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    review_service.delete_review(db, review_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
