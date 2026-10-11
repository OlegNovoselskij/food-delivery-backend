from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.reports.periods import MAX_BUCKETS, STEP_DAYS

ReportFormat = Literal["json", "csv"]
GroupBy = Literal["day", "week", "month"]


class ReportParams(BaseModel):
    format: ReportFormat = "json"


class PeriodParams(ReportParams):
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def check_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        return self


class SeriesParams(PeriodParams):
    group_by: GroupBy = "month"

    @model_validator(mode="after")
    def apply_defaults_and_limits(self):
        if self.date_to is None:
            self.date_to = date.today()
        if self.date_from is None:
            self.date_from = self.date_to - timedelta(days=364)
        if self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        days = (self.date_to - self.date_from).days + 1
        if days / STEP_DAYS[self.group_by] > MAX_BUCKETS:
            raise ValueError("The period is too long for this grouping, use a coarser group_by")
        return self


class CourseStatsParams(PeriodParams):
    category_id: int | None = None
    sort: Literal["students", "completed", "revenue", "rating"] = "students"
    limit: int = Field(default=50, ge=1, le=200)


class TeacherRankingParams(PeriodParams):
    sort: Literal["rating", "students", "revenue", "courses"] = "rating"
    limit: int = Field(default=20, ge=1, le=100)


class RevenueSeriesParams(SeriesParams):
    course_id: int | None = None
    teacher_id: int | None = None
    category_id: int | None = None


class RevenueBreakdownParams(PeriodParams):
    by: Literal["course", "teacher", "category"] = "course"
    limit: int = Field(default=20, ge=1, le=100)


class GrowthParams(SeriesParams):
    pass


class TeacherDashboardParams(PeriodParams):
    teacher_id: int | None = None


class CourseReportParams(ReportParams):
    course_id: int


class QuestionsQuery(ReportParams):
    limit: int = Field(default=10, ge=1, le=50)
    min_answers: int = Field(default=3, ge=1, le=1000)


class QuestionsParams(QuestionsQuery):
    course_id: int


class StudentsQuery(ReportParams):
    status: Literal["active", "completed"] | None = None
    inactive_days: int | None = Field(default=None, ge=1, le=365)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class StudentsParams(StudentsQuery):
    course_id: int


class CourseStatRow(BaseModel):
    course_id: int
    title: str
    status: str
    category: str
    teacher_name: str
    students: int
    completed: int
    completion_rate: float | None
    rating_avg: float | None
    reviews_count: int
    revenue: Decimal


class CourseStatsTotals(BaseModel):
    students: int
    completed: int
    revenue: Decimal


class CourseStatsOut(BaseModel):
    items: list[CourseStatRow]
    totals: CourseStatsTotals


class TeacherRow(BaseModel):
    teacher_id: int
    name: str
    courses: int
    students: int
    completed: int
    rating_avg: float | None
    reviews_count: int
    revenue: Decimal


class TeacherRankingOut(BaseModel):
    items: list[TeacherRow]


class RevenuePoint(BaseModel):
    period: date
    revenue: Decimal
    refunded: Decimal
    payments: int


class RevenueTotals(BaseModel):
    revenue: Decimal
    refunded: Decimal
    payments: int


class RevenueSeriesOut(BaseModel):
    group_by: str
    date_from: date
    date_to: date
    items: list[RevenuePoint]
    totals: RevenueTotals


class BreakdownRow(BaseModel):
    id: int
    name: str
    revenue: Decimal
    refunded: Decimal
    payments: int


class BreakdownOut(BaseModel):
    by: str
    items: list[BreakdownRow]
    total_revenue: Decimal


class GrowthPoint(BaseModel):
    period: date
    students: int
    teachers: int
    total: int


class GrowthTotals(BaseModel):
    students: int
    teachers: int
    total: int


class GrowthOut(BaseModel):
    group_by: str
    date_from: date
    date_to: date
    items: list[GrowthPoint]
    totals: GrowthTotals


class OverviewOut(BaseModel):
    users: dict[str, int]
    courses: dict[str, int]
    enrollments: dict[str, int]
    revenue: Decimal
    refunded: Decimal
    certificates: int
    reviews: int


class FunnelRow(BaseModel):
    lesson_id: int
    title: str
    module_title: str
    module_position: int
    position: int
    completed: int
    completed_percent: float
    drop_off_percent: float
    biggest_drop: bool


class FunnelOut(BaseModel):
    course_id: int
    students: int
    items: list[FunnelRow]


class QuizStatRow(BaseModel):
    quiz_id: int
    title: str
    module_title: str
    passing_score: int
    attempts: int
    students: int
    passed_students: int
    pass_rate: float | None
    avg_score: float | None
    pending_review: int


class QuizStatsOut(BaseModel):
    course_id: int
    items: list[QuizStatRow]


class QuestionStatRow(BaseModel):
    question_id: int
    text: str
    question_type: str
    quiz_title: str
    answered: int
    correct: int
    correct_percent: float


class QuestionStatsOut(BaseModel):
    course_id: int
    items: list[QuestionStatRow]


class StudentRow(BaseModel):
    enrollment_id: int
    student_id: int
    name: str
    status: str
    enrolled_at: datetime
    progress_percent: int
    lessons_completed: int
    lessons_total: int
    quizzes_passed: int
    quizzes_total: int
    last_activity_at: datetime
    days_inactive: int


class StudentsOut(BaseModel):
    course_id: int
    total: int
    page: int
    size: int
    items: list[StudentRow]
