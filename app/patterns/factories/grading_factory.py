from app.models.quiz import Question
from app.patterns.strategies.grading import (
    GradingStrategy,
    MultipleChoiceGrading,
    OpenTextGrading,
    SingleChoiceGrading,
)


class GradingStrategyFactory:
    _strategies: dict[str, GradingStrategy] = {
        "single_choice": SingleChoiceGrading(),
        "multiple_choice": MultipleChoiceGrading(),
        "open_text": OpenTextGrading(),
    }

    @classmethod
    def for_question(cls, question: Question) -> GradingStrategy:
        return cls._strategies[question.question_type]
