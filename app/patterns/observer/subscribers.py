from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import AttemptSubmitted, CourseCompleted, PaymentSucceeded, QuizGraded
from app.patterns.observer.observers import CertificateObserver, NotificationObserver

_registered = False


def register_subscribers() -> None:
    global _registered
    if _registered:
        return
    certificates = CertificateObserver()
    notifications = NotificationObserver()

    # order matters: the certificate exists before the notification that mentions it
    event_bus.subscribe(CourseCompleted, certificates.on_course_completed)
    for event_type in (PaymentSucceeded, AttemptSubmitted, QuizGraded, CourseCompleted):
        event_bus.subscribe(event_type, notifications.on_event)
    _registered = True
