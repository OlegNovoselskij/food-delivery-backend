from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.quiz import Question


@dataclass(frozen=True)
class StudentAnswer:
    option_ids: frozenset[int] = frozenset()
    text: str | None = None


@dataclass(frozen=True)
class GradeResult:
    points: int | None
    is_correct: bool | None
    needs_review: bool = False


class GradingStrategy(ABC):
    @abstractmethod
    def grade(self, question: Question, answer: StudentAnswer) -> GradeResult: ...


def _correct_ids(question: Question) -> frozenset[int]:
    return frozenset(option.id for option in question.options if option.is_correct)


class SingleChoiceGrading(GradingStrategy):
    def grade(self, question: Question, answer: StudentAnswer) -> GradeResult:
        correct = answer.option_ids == _correct_ids(question)
        return GradeResult(points=question.points if correct else 0, is_correct=correct)


class MultipleChoiceGrading(GradingStrategy):
    # partial credit: every right pick adds, every wrong pick subtracts, the result is rounded down
    def grade(self, question: Question, answer: StudentAnswer) -> GradeResult:
        correct_ids = _correct_ids(question)
        if not correct_ids:
            return GradeResult(points=0, is_correct=False)
        right = len(answer.option_ids & correct_ids)
        wrong = len(answer.option_ids - correct_ids)
        points = question.points * max(0, right - wrong) // len(correct_ids)
        return GradeResult(points=points, is_correct=answer.option_ids == correct_ids)


class OpenTextGrading(GradingStrategy):
    def grade(self, question: Question, answer: StudentAnswer) -> GradeResult:
        if not (answer.text and answer.text.strip()):
            return GradeResult(points=0, is_correct=False)
        return GradeResult(points=None, is_correct=None, needs_review=True)
