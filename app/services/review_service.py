from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.exceptions import CourseNotFound, ReviewAlreadyExists, ReviewNotAllowed, ReviewNotFound
from app.models.catalog import Course, Lesson, Module
from app.models.enrollment import Enrollment, LessonProgress
from app.models.review import Review
from app.models.user import User
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CatalogChanged
from app.repository import course_repository
from app.repository.enrollment_repository import ACCESS_STATUSES
from app.schemas.review import ReviewCreate, ReviewFilters, ReviewUpdate
from app.services.access import can_view_course


def _refresh_rating(db: Session, course_id: int) -> None:
    average, count = (
        db.query(func.avg(Review.rating), func.count(Review.id)).filter(Review.course_id == course_id).one()
    )
    db.query(Course).filter(Course.id == course_id).update(
        {"rating_avg": round(average, 2) if average is not None else None, "reviews_count": count},
        synchronize_session=False,
    )


def _has_started_learning(db: Session, student_id: int, course_id: int) -> bool:
    enrollment = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status.in_(ACCESS_STATUSES),
        )
        .first()
    )
    if enrollment is None:
        return False
    return (
        db.query(LessonProgress.id)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .filter(LessonProgress.enrollment_id == enrollment.id, Module.course_id == course_id)
        .first()
        is not None
    )


def _finish(db: Session, course_id: int) -> None:
    db.flush()
    _refresh_rating(db, course_id)
    event_bus.publish(db, CatalogChanged(reason="rating_changed"))
    db.commit()


def create_review(db: Session, student: User, course_id: int, data: ReviewCreate) -> Review:
    course = course_repository.get_by_id(db, course_id)
    if course is None or course.status == "draft":
        raise CourseNotFound()
    if course.teacher_id == student.id or not _has_started_learning(db, student.id, course_id):
        raise ReviewNotAllowed()
    if db.query(Review.id).filter(Review.course_id == course_id, Review.student_id == student.id).first():
        raise ReviewAlreadyExists()

    review = Review(course_id=course_id, student_id=student.id, rating=data.rating, comment=data.comment or None)
    db.add(review)
    try:
        _finish(db, course_id)
    except IntegrityError:  # two parallel requests: the unique constraint lets only one through
        db.rollback()
        raise ReviewAlreadyExists()
    return _load(db, review.id)


def _load(db: Session, review_id: int) -> Review:
    return db.query(Review).options(joinedload(Review.student)).populate_existing().filter(Review.id == review_id).one()


def update_review(db: Session, review_id: int, user: User, data: ReviewUpdate) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None or review.student_id != user.id:
        raise ReviewNotFound()
    changes = data.model_dump(exclude_unset=True)
    if changes.get("rating") is None:
        changes.pop("rating", None)
    for field, value in changes.items():
        setattr(review, field, value or None if field == "comment" else value)
    _finish(db, review.course_id)
    return _load(db, review_id)


def delete_review(db: Session, review_id: int, user: User) -> None:
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None or not (user.role == "admin" or review.student_id == user.id):
        raise ReviewNotFound()
    course_id = review.course_id
    db.delete(review)
    _finish(db, course_id)


def list_reviews(db: Session, course_id: int, viewer: User | None, filters: ReviewFilters) -> dict:
    course = course_repository.get_by_id(db, course_id)
    if course is None or not can_view_course(db, course, viewer):
        raise CourseNotFound()
    query = db.query(Review).options(joinedload(Review.student)).filter(Review.course_id == course_id)
    items = (
        query.order_by(Review.created_at.desc(), Review.id.desc())
        .offset((filters.page - 1) * filters.size)
        .limit(filters.size)
        .all()
    )
    return {
        "items": items,
        "total": course.reviews_count,
        "page": filters.page,
        "size": filters.size,
        "rating_avg": float(course.rating_avg) if course.rating_avg is not None else None,
        "reviews_count": course.reviews_count,
    }
