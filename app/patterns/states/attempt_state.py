from datetime import datetime, timezone

from app.exceptions import InvalidAttemptState
from app.models.attempt import QuizAttempt

IN_PROGRESS = "in_progress"
PENDING_REVIEW = "pending_review"
GRADED = "graded"


class AttemptState:
    name: str
    accepts_answers = False
    accepts_review = False

    def submit(self, attempt: QuizAttempt, needs_review: bool) -> None:
        raise InvalidAttemptState()

    def grade(self, attempt: QuizAttempt) -> None:
        raise InvalidAttemptState()


class InProgressState(AttemptState):
    name = IN_PROGRESS
    accepts_answers = True

    def submit(self, attempt: QuizAttempt, needs_review: bool) -> None:
        attempt.status = PENDING_REVIEW if needs_review else GRADED
        attempt.submitted_at = datetime.now(timezone.utc)


class PendingReviewState(AttemptState):
    name = PENDING_REVIEW
    accepts_review = True

    def grade(self, attempt: QuizAttempt) -> None:
        attempt.status = GRADED


class GradedState(AttemptState):
    name = GRADED


_STATES = {state.name: state for state in (InProgressState(), PendingReviewState(), GradedState())}


class AttemptStateMachine:
    def __init__(self, attempt: QuizAttempt) -> None:
        self._attempt = attempt

    @property
    def state(self) -> AttemptState:
        return _STATES[self._attempt.status]

    def accepts_answers(self) -> bool:
        return self.state.accepts_answers

    def accepts_review(self) -> bool:
        return self.state.accepts_review

    def submit(self, needs_review: bool) -> None:
        self.state.submit(self._attempt, needs_review)

    def grade(self) -> None:
        self.state.grade(self._attempt)
