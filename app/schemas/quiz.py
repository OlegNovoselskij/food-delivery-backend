from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.course import TeacherBrief

QuestionType = Literal["single_choice", "multiple_choice", "open_text"]

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
OptionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class QuizCreate(BaseModel):
    title: Title
    passing_score: int = Field(default=60, ge=1, le=100)
    max_attempts: int | None = Field(default=None, ge=1, le=20)


class QuizUpdate(BaseModel):
    title: Title | None = None
    passing_score: int | None = Field(default=None, ge=1, le=100)
    max_attempts: int | None = Field(default=None, ge=1, le=20)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for field in ("title", "passing_score"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class OptionIn(BaseModel):
    id: int | None = None
    text: OptionText
    is_correct: bool = False


class QuestionIn(BaseModel):
    text: QuestionText
    question_type: QuestionType
    points: int = Field(default=1, ge=1, le=100)
    explanation: str | None = Field(default=None, max_length=2000)
    options: list[OptionIn] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def check_options(self):
        if self.question_type == "open_text":
            if self.options:
                raise ValueError("Open questions cannot have options")
            return self

        if len(self.options) < 2:
            raise ValueError("At least two options are required")
        correct = sum(option.is_correct for option in self.options)
        if self.question_type == "single_choice" and correct != 1:
            raise ValueError("Exactly one option must be correct")
        if self.question_type == "multiple_choice" and correct < 1:
            raise ValueError("At least one option must be correct")

        texts = [option.text.lower() for option in self.options]
        if len(set(texts)) != len(texts):
            raise ValueError("Option texts must be unique")
        ids = [option.id for option in self.options if option.id is not None]
        if len(set(ids)) != len(ids):
            raise ValueError("Option ids must be unique")
        return self


class AnswerIn(BaseModel):
    question_id: int
    option_ids: list[int] = Field(default_factory=list, max_length=10)
    text: str | None = Field(default=None, max_length=10000)


class SubmitRequest(BaseModel):
    answers: list[AnswerIn] = Field(max_length=200)

    @model_validator(mode="after")
    def questions_are_unique(self):
        ids = [answer.question_id for answer in self.answers]
        if len(set(ids)) != len(ids):
            raise ValueError("Each question can be answered only once")
        return self


class ReviewGrade(BaseModel):
    question_id: int
    points: int = Field(ge=0, le=100)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRequest(BaseModel):
    grades: list[ReviewGrade] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def questions_are_unique(self):
        ids = [grade.question_id for grade in self.grades]
        if len(set(ids)) != len(ids):
            raise ValueError("Each question can be graded only once")
        return self


class OptionManageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    is_correct: bool


class QuestionManageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    question_type: str
    points: int
    position: int
    explanation: str | None
    options: list[OptionManageOut]


class QuizManageOut(BaseModel):
    id: int
    module_id: int
    title: str
    passing_score: int
    max_attempts: int | None
    has_attempts: bool
    total_points: int
    questions: list[QuestionManageOut]


class OptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class QuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    question_type: str
    points: int
    position: int
    options: list[OptionPublic]


class AnswerReviewOut(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    points: int
    options: list[OptionPublic]
    selected_option_ids: list[int]
    text_answer: str | None
    correct_option_ids: list[int]
    is_correct: bool | None
    points_awarded: int | None
    needs_review: bool
    explanation: str | None
    teacher_comment: str | None


class AttemptOut(BaseModel):
    id: int
    quiz_id: int
    quiz_title: str
    status: str
    passing_score: int
    started_at: datetime
    submitted_at: datetime | None
    score: int | None
    passed: bool | None
    points_earned: int | None
    points_total: int | None
    questions: list[QuestionPublic] | None
    review: list[AnswerReviewOut] | None


class AttemptSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    score: int | None
    passed: bool | None
    points_earned: int | None
    points_total: int | None
    started_at: datetime
    submitted_at: datetime | None


class PendingReviewOut(BaseModel):
    attempt_id: int
    quiz_id: int
    quiz_title: str
    course_id: int
    course_title: str
    student: TeacherBrief
    submitted_at: datetime | None
