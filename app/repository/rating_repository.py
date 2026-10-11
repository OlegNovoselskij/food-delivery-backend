from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.review import Review


def course_ratings(db: Session):
    return (
        db.query(
            Review.course_id.label("course_id"),
            func.avg(Review.rating).label("rating_avg"),
            func.count(Review.id).label("reviews_count"),
        )
        .group_by(Review.course_id)
        .subquery()
    )
