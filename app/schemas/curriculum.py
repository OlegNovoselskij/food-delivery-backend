from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LessonType = Literal["video", "article"]


class ModuleCreate(BaseModel):
    title: Title


class ModuleUpdate(BaseModel):
    title: Title


class LessonCreate(BaseModel):
    title: Title
    lesson_type: LessonType = "video"
    content: str | None = Field(default=None, max_length=50000)
    duration_minutes: int | None = Field(default=None, ge=0, le=1000)
    is_preview: bool = False


class LessonUpdate(BaseModel):
    title: Title | None = None
    lesson_type: LessonType | None = None
    content: str | None = Field(default=None, max_length=50000)
    duration_minutes: int | None = Field(default=None, ge=0, le=1000)
    is_preview: bool | None = None

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for field in ("title", "lesson_type", "is_preview"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class OrderUpdate(BaseModel):
    ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_are_unique(self):
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("ids must be unique")
        return self


class LessonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    lesson_type: str
    duration_minutes: int | None
    position: int
    is_preview: bool
    has_video: bool


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    content_type: str | None
    size_bytes: int | None


class LessonOut(LessonSummary):
    module_id: int
    content: str | None
    materials: list[MaterialOut]


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    position: int
    has_quiz: bool
    quiz_id: int | None
    quiz_questions_count: int
    lessons: list[LessonSummary]


class ProgramOut(BaseModel):
    course_id: int
    total_lessons: int
    total_duration_minutes: int
    modules: list[ModuleOut]
