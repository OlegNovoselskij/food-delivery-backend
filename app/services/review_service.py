from sqlalchemy.orm import Session

from app.exceptions import ReviewNotFound
from app.models.review import Review
from app.models.user import User
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CatalogChanged


def delete_review(db: Session, review_id: int, user: User) -> None:
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None or not (user.role == "admin" or review.student_id == user.id):
        raise ReviewNotFound()
    db.delete(review)
    db.flush()
    event_bus.publish(db, CatalogChanged(reason="rating_changed"))
    db.commit()
