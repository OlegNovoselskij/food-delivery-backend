from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Comment | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: Comment | None = None


class ReviewAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    surname: str


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    rating: int
    comment: str | None
    created_at: datetime
    student: ReviewAuthor


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    size: int
    rating_avg: float | None
    reviews_count: int


class ReviewFilters(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
