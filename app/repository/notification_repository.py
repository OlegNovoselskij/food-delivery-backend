from sqlalchemy.orm import Session

from app.models.notification import Notification


def add(db: Session, notification: Notification) -> Notification:
    db.add(notification)
    db.flush()
    return notification


def list_for_user(
    db: Session, user_id: int, *, unread_only: bool, offset: int, limit: int
) -> tuple[list[Notification], int]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    total = query.count()
    items = query.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit).all()
    return items, total


def unread_count(db: Session, user_id: int) -> int:
    return db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read.is_(False)).count()


def get_for_user(db: Session, notification_id: int, user_id: int) -> Notification | None:
    return db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()


def mark_all_read(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
