from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import (
    AttemptSubmitted,
    CatalogChanged,
    CourseCompleted,
    PaymentSucceeded,
    QuizGraded,
)
from app.patterns.observer.observers import (
    CacheInvalidationObserver,
    CertificateObserver,
    EmailObserver,
    NotificationObserver,
)

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
    event_bus.subscribe(CatalogChanged, CacheInvalidationObserver().on_catalog_changed)
    emails = EmailObserver()
    for event_type in (PaymentSucceeded, CourseCompleted):
        event_bus.subscribe(event_type, emails.on_event)
    _registered = True
