from types import SimpleNamespace

from app.patterns.factories.grading_factory import GradingStrategyFactory
from app.patterns.strategies.grading import (
    MultipleChoiceGrading,
    OpenTextGrading,
    SingleChoiceGrading,
    StudentAnswer,
)


def question(kind: str, points: int, correct: tuple[int, ...], wrong: tuple[int, ...] = ()):
    options = [SimpleNamespace(id=i, is_correct=True) for i in correct] + [
        SimpleNamespace(id=i, is_correct=False) for i in wrong
    ]
    return SimpleNamespace(question_type=kind, points=points, options=options)


def answer(*ids: int, text: str | None = None) -> StudentAnswer:
    return StudentAnswer(option_ids=frozenset(ids), text=text)


def test_single_choice_is_all_or_nothing():
    q = question("single_choice", 2, (1,), (2, 3))
    assert SingleChoiceGrading().grade(q, answer(1)).points == 2
    assert SingleChoiceGrading().grade(q, answer(2)).points == 0
    assert SingleChoiceGrading().grade(q, answer()).is_correct is False


def test_multiple_choice_gives_partial_credit_and_punishes_wrong_picks():
    q = question("multiple_choice", 3, (1, 2), (3, 4))
    grade = MultipleChoiceGrading().grade
    assert grade(q, answer(1, 2)).points == 3 and grade(q, answer(1, 2)).is_correct is True
    assert grade(q, answer(1)).points == 1
    assert grade(q, answer(1, 3)).points == 0
    assert grade(q, answer(1, 2, 3)).points == 1
    assert grade(q, answer(3, 4)).points == 0


def test_open_answers_wait_for_the_teacher():
    q = question("open_text", 5, ())
    result = OpenTextGrading().grade(q, answer(text="My explanation"))
    assert result.points is None and result.needs_review is True


def test_an_empty_open_answer_scores_zero_without_review():
    q = question("open_text", 5, ())
    for blank in (None, "", "   "):
        result = OpenTextGrading().grade(q, answer(text=blank))
        assert result.points == 0 and result.needs_review is False


def test_the_factory_picks_the_strategy_by_question_type():
    for kind, expected in (
        ("single_choice", SingleChoiceGrading),
        ("multiple_choice", MultipleChoiceGrading),
        ("open_text", OpenTextGrading),
    ):
        assert isinstance(GradingStrategyFactory.for_question(SimpleNamespace(question_type=kind)), expected)
