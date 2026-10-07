from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryOut

Level = Literal["beginner", "intermediate", "advanced"]


# ---------- що приймаємо ----------

class CourseCreate(BaseModel):
    category_id: int
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    level: Level = "beginner"
    price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    cover_url: str | None = Field(default=None, max_length=500)


class CourseUpdate(BaseModel):
    category_id: int | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    level: Level | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    cover_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for field in ("category_id", "title", "level", "price"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CourseFilters(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    category_id: int | None = None
    level: Level | None = None
    teacher_id: int | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    sort: Literal["newest", "price_asc", "price_desc"] = "newest"
    page: int = Field(default=1, ge=1)
    size: int = Field(default=12, ge=1, le=50)

    @model_validator(mode="after")
    def check_price_range(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price cannot be greater than max_price")
        return self


# ---------- що віддаємо ----------

class TeacherBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    surname: str


class TeacherPublic(TeacherBrief):
    bio: str | None


class CourseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    level: str
    price: Decimal
    cover_url: str | None
    created_at: datetime
    category: CategoryOut
    teacher: TeacherBrief


class CourseOut(CourseListItem):
    description: str | None
    status: str
    updated_at: datetime | None
    teacher: TeacherPublic


class CoursePage(BaseModel):
    items: list[CourseListItem]
    total: int
    page: int
    size: int