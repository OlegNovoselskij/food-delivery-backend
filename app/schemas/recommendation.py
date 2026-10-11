from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.course import CourseListItem


class RecommendationParams(BaseModel):
    strategy: Literal["auto", "collaborative", "category", "popular"] = "auto"
    limit: int = Field(default=6, ge=1, le=20)


class RecommendationOut(BaseModel):
    course: CourseListItem
    reason: str
