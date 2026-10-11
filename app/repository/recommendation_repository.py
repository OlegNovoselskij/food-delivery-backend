from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.catalog import Course
from app.models.enrollment import Enrollment
from app.repository import rating_repository
from app.repository.enrollment_repository import ACCESS_STATUSES


def _published(db: Session):
    return (
        db.query(Course)
        .options(joinedload(Course.teacher), joinedload(Course.category))
        .filter(Course.status == "published")
    )


def excluded_course_ids(db: Session, user_id: int) -> set[int]:
    enrolled = db.query(Enrollment.course_id).filter(Enrollment.student_id == user_id, Enrollment.status != "cancelled")
    taught = db.query(Course.id).filter(Course.teacher_id == user_id)
    return {course_id for (course_id,) in enrolled.all()} | {course_id for (course_id,) in taught.all()}


def category_weights(db: Session, student_id: int) -> dict[int, int]:
    rows = (
        db.query(Course.category_id, func.count(Enrollment.id))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.student_id == student_id, Enrollment.status.in_(ACCESS_STATUSES))
        .group_by(Course.category_id)
        .all()
    )
    return {category_id: int(count) for category_id, count in rows}


def courses_in_categories(db: Session, weights: dict[int, int], exclude: set[int], limit: int) -> list[Course]:
    if not weights:
        return []
    ratings = rating_repository.course_ratings(db)
    weight = case(weights, value=Course.category_id, else_=0)
    query = _published(db).outerjoin(ratings, ratings.c.course_id == Course.id).filter(Course.category_id.in_(list(weights)))
    if exclude:
        query = query.filter(Course.id.not_in(exclude))
    return (
        query.order_by(
            weight.desc(),
            ratings.c.rating_avg.desc().nulls_last(),
            func.coalesce(ratings.c.reviews_count, 0).desc(),
            Course.id.desc(),
        )
        .limit(limit)
        .all()
    )


def co_enrolled_ids(db: Session, student_id: int, exclude: set[int], limit: int) -> list[int]:
    mine = aliased(Enrollment)
    peer = aliased(Enrollment)
    theirs = aliased(Enrollment)

    score = func.count(theirs.student_id.distinct())
    query = (
        db.query(Course.id)
        .join(theirs, theirs.course_id == Course.id)
        .join(peer, peer.student_id == theirs.student_id)
        .join(mine, mine.course_id == peer.course_id)
        .filter(
            Course.status == "published",
            mine.student_id == student_id,
            mine.status.in_(ACCESS_STATUSES),
            peer.student_id != student_id,
            peer.status.in_(ACCESS_STATUSES),
            theirs.status.in_(ACCESS_STATUSES),
            theirs.course_id != mine.course_id,
        )
    )
    if exclude:
        query = query.filter(Course.id.not_in(exclude))
    rows = query.group_by(Course.id).order_by(score.desc(), Course.id).limit(limit).all()
    return [course_id for (course_id,) in rows]


def load_published(db: Session, course_ids: list[int]) -> dict[int, Course]:
    if not course_ids:
        return {}
    return {course.id: course for course in _published(db).filter(Course.id.in_(course_ids)).all()}


def popular_courses(db: Session, exclude: set[int], limit: int, days: int = 90) -> list[Course]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    recent = (
        db.query(Enrollment.course_id.label("course_id"), func.count(Enrollment.id).label("recent"))
        .filter(Enrollment.status.in_(ACCESS_STATUSES), Enrollment.enrolled_at >= since)
        .group_by(Enrollment.course_id)
        .subquery()
    )
    ratings = rating_repository.course_ratings(db)
    query = (
        _published(db)
        .outerjoin(recent, recent.c.course_id == Course.id)
        .outerjoin(ratings, ratings.c.course_id == Course.id)
    )
    if exclude:
        query = query.filter(Course.id.not_in(exclude))
    return (
        query.order_by(
            func.coalesce(recent.c.recent, 0).desc(),
            ratings.c.rating_avg.desc().nulls_last(),
            func.coalesce(ratings.c.reviews_count, 0).desc(),
            Course.id.desc(),
        )
        .limit(limit)
        .all()
    )
