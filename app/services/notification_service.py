from sqlalchemy.orm import Session

from app import config
from app.exceptions import NotificationNotFound
from app.models.notification import Notification
from app.models.user import User
from app.repository import notification_repository
from app.schemas.notification import NotificationFilters
from app.security import create_ws_ticket


def list_notifications(db: Session, user: User, filters: NotificationFilters) -> dict:
    items, total = notification_repository.list_for_user(
        db, user.id, unread_only=filters.unread, offset=(filters.page - 1) * filters.size, limit=filters.size
    )
    return {
        "items": items,
        "total": total,
        "unread_count": notification_repository.unread_count(db, user.id),
        "page": filters.page,
        "size": filters.size,
    }


def unread_count(db: Session, user: User) -> dict:
    return {"count": notification_repository.unread_count(db, user.id)}


def mark_read(db: Session, notification_id: int, user: User) -> Notification:
    notification = notification_repository.get_for_user(db, notification_id, user.id)
    if notification is None:
        raise NotificationNotFound()
    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> dict:
    updated = notification_repository.mark_all_read(db, user.id)
    db.commit()
    return {"updated": updated}


def issue_ws_ticket(user: User) -> dict:
    return {"ticket": create_ws_ticket(user.id), "expires_in": config.WS_TICKET_TTL_SECONDS}
