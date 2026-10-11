from dataclasses import dataclass
from decimal import Decimal


class DomainEvent:
    pass


@dataclass(frozen=True)
class PaymentSucceeded(DomainEvent):
    enrollment_id: int
    student_id: int
    course_id: int
    course_title: str
    amount: Decimal


@dataclass(frozen=True)
class AttemptSubmitted(DomainEvent):
    attempt_id: int
    teacher_id: int
    student_name: str
    quiz_title: str
    course_id: int
    course_title: str


@dataclass(frozen=True)
class QuizGraded(DomainEvent):
    attempt_id: int
    student_id: int
    quiz_id: int
    quiz_title: str
    course_id: int
    score: int
    passed: bool


@dataclass(frozen=True)
class CourseCompleted(DomainEvent):
    enrollment_id: int
    student_id: int
    course_id: int
    course_title: str
