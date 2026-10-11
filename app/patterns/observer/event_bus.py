from collections import defaultdict
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.patterns.observer.events import DomainEvent

Observer = Callable[[Session, DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._observers: dict[type[DomainEvent], list[Observer]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], observer: Observer) -> None:
        self._observers[event_type].append(observer)

    def publish(self, db: Session, event: DomainEvent) -> None:
        # observers run inside the caller's transaction, in subscription order:
        # if one fails the whole operation is rolled back, so a course is never completed without its certificate
        for observer in self._observers[type(event)]:
            observer(db, event)


event_bus = EventBus()
