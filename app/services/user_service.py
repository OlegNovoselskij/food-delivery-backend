from sqlalchemy.orm import Session

from app.models.user import User
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CatalogChanged
from app.schemas.user import UserUpdate


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    if user.role == "teacher":
        event_bus.publish(db, CatalogChanged(reason="teacher_profile_updated"))
    db.commit()
    db.refresh(user)
    return user