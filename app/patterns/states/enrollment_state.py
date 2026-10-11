from datetime import UTC, datetime

from app.exceptions import InvalidEnrollmentTransition
from app.models.enrollment import Enrollment

PENDING_PAYMENT = "pending_payment"
ACTIVE = "active"
COMPLETED = "completed"
CANCELLED = "cancelled"


class EnrollmentState:
    name: str
    accepts_payment = False

    def activate(self, enrollment: Enrollment) -> None:
        raise InvalidEnrollmentTransition()

    def complete(self, enrollment: Enrollment) -> None:
        raise InvalidEnrollmentTransition()

    def cancel(self, enrollment: Enrollment) -> None:
        raise InvalidEnrollmentTransition()

    def reopen(self, enrollment: Enrollment, target: str) -> None:
        raise InvalidEnrollmentTransition()


class PendingPaymentState(EnrollmentState):
    name = PENDING_PAYMENT
    accepts_payment = True

    def activate(self, enrollment: Enrollment) -> None:
        enrollment.status = ACTIVE

    def cancel(self, enrollment: Enrollment) -> None:
        enrollment.status = CANCELLED


class ActiveState(EnrollmentState):
    name = ACTIVE

    def complete(self, enrollment: Enrollment) -> None:
        enrollment.status = COMPLETED
        enrollment.completed_at = datetime.now(UTC)

    def cancel(self, enrollment: Enrollment) -> None:
        enrollment.status = CANCELLED


class CompletedState(EnrollmentState):
    name = COMPLETED


class CancelledState(EnrollmentState):
    name = CANCELLED

    def reopen(self, enrollment: Enrollment, target: str) -> None:
        if target not in (PENDING_PAYMENT, ACTIVE):
            raise InvalidEnrollmentTransition()
        enrollment.status = target
        enrollment.enrolled_at = datetime.now(UTC)
        enrollment.completed_at = None


_STATES = {state.name: state for state in (PendingPaymentState(), ActiveState(), CompletedState(), CancelledState())}


class EnrollmentStateMachine:
    def __init__(self, enrollment: Enrollment) -> None:
        self._enrollment = enrollment

    @property
    def state(self) -> EnrollmentState:
        return _STATES[self._enrollment.status]

    def accepts_payment(self) -> bool:
        return self.state.accepts_payment

    def activate(self) -> None:
        self.state.activate(self._enrollment)

    def complete(self) -> None:
        self.state.complete(self._enrollment)

    def cancel(self) -> None:
        self.state.cancel(self._enrollment)

    def reopen(self, target: str) -> None:
        self.state.reopen(self._enrollment, target)
