from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationOut, RecommendationParams
from app.services import recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=list[RecommendationOut])
def recommendations(
    params: Annotated[RecommendationParams, Query()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommendation_service.recommend(db, user, params)
