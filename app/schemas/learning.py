from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enrollment import EnrollmentOut


class ProgressSummaryOut(BaseModel):
    percent: int
    lessons_total: int
    lessons_completed: int
    quizzes_total: int
    quizzes_passed: int
    minutes_total: int
    minutes_completed: int


class LessonProgressOut(BaseModel):
    id: int
    title: str
    position: int
    duration_minutes: int | None
    completed: bool
    completed_at: datetime | None


class QuizProgressOut(BaseModel):
    id: int
    title: str
    passed: bool


class ModuleProgressOut(BaseModel):
    id: int
    title: str
    position: int
    progress: ProgressSummaryOut
    quiz: QuizProgressOut | None
    lessons: list[LessonProgressOut]


class ProgressOut(BaseModel):
    enrollment_id: int
    course_id: int
    enrollment_status: str
    progress: ProgressSummaryOut
    next_lesson_id: int | None
    modules: list[ModuleProgressOut]


class HistoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment: EnrollmentOut
    progress: ProgressSummaryOut
    last_activity_at: datetime | None
