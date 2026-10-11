from types import SimpleNamespace

import pytest

from app.exceptions import InvalidAttemptState, InvalidEnrollmentTransition
from app.patterns.states.attempt_state import AttemptStateMachine
from app.patterns.states.enrollment_state import EnrollmentStateMachine


def enrollment(status: str):
    return SimpleNamespace(status=status, enrolled_at=None, completed_at=None)


def test_enrollment_happy_path():
    item = enrollment("pending_payment")
    machine = EnrollmentStateMachine(item)
    assert machine.accepts_payment()
    machine.activate()
    assert item.status == "active" and not machine.accepts_payment()
    machine.complete()
    assert item.status == "completed" and item.completed_at is not None


@pytest.mark.parametrize(
    ("status", "action"),
    [
        ("pending_payment", "complete"),
        ("active", "activate"),
        ("completed", "cancel"),
        ("completed", "activate"),
        ("cancelled", "complete"),
        ("cancelled", "cancel"),
    ],
)
def test_forbidden_enrollment_transitions(status, action):
    with pytest.raises(InvalidEnrollmentTransition):
        getattr(EnrollmentStateMachine(enrollment(status)), action)()


def test_a_cancelled_enrollment_can_be_reopened_only_as_pending_or_active():
    item = enrollment("cancelled")
    item.completed_at = "old"
    EnrollmentStateMachine(item).reopen("active")
    assert item.status == "active" and item.completed_at is None
    with pytest.raises(InvalidEnrollmentTransition):
        EnrollmentStateMachine(enrollment("cancelled")).reopen("completed")


def test_attempt_lifecycle():
    graded = SimpleNamespace(status="in_progress", submitted_at=None)
    AttemptStateMachine(graded).submit(needs_review=False)
    assert graded.status == "graded" and graded.submitted_at is not None

    waiting = SimpleNamespace(status="in_progress", submitted_at=None)
    machine = AttemptStateMachine(waiting)
    machine.submit(needs_review=True)
    assert waiting.status == "pending_review" and machine.accepts_review()
    machine.grade()
    assert waiting.status == "graded"


def test_forbidden_attempt_transitions():
    with pytest.raises(InvalidAttemptState):
        AttemptStateMachine(SimpleNamespace(status="in_progress")).grade()
    with pytest.raises(InvalidAttemptState):
        AttemptStateMachine(SimpleNamespace(status="graded", submitted_at=None)).submit(needs_review=False)
