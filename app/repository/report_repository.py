from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, literal_column
from sqlalchemy.orm import Session

from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.catalog import Category, Course, Lesson, Module
from app.models.enrollment import Certificate, Enrollment, LessonProgress, Payment
from app.models.quiz import Question, Quiz
from app.models.review import Review
from app.models.user import User
from app.repository import rating_repository
from app.repository.enrollment_repository import ACCESS_STATUSES

# fixed SQL fragments: the grouping comes from a closed list, never from user input
_TRUNC = {"day": "'day'", "week": "'week'", "month": "'month'"}


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _period(column, date_from: date | None, date_to: date | None) -> list:
    conditions = []
    if date_from is not None:
        conditions.append(column >= _day_start(date_from))
    if date_to is not None:
        conditions.append(column < _day_start(date_to + timedelta(days=1)))
    return conditions


def _bucket(group_by: str, column):
    return func.date_trunc(literal_column(_TRUNC[group_by]), column)


def _full_name():
    return func.concat(User.name, " ", User.surname)


def _money():
    revenue = func.coalesce(func.sum(Payment.amount).filter(Payment.status == "succeeded"), 0)
    refunded = func.coalesce(func.sum(Payment.amount).filter(Payment.status == "refunded"), 0)
    payments = func.count(Payment.id).filter(Payment.status == "succeeded")
    return revenue, refunded, payments


def _counts(db: Session, column, keys: tuple[str, ...]) -> dict[str, int]:
    found = {value: int(count) for value, count in db.query(column, func.count()).group_by(column).all()}
    return {key: found.get(key, 0) for key in keys}


def platform_totals(db: Session) -> dict:
    revenue, refunded, _ = _money()
    money_row = db.query(revenue, refunded).one()
    return {
        "users": _counts(db, User.role, ("student", "teacher", "admin")),
        "courses": _counts(db, Course.status, ("draft", "published", "archived")),
        "enrollments": _counts(db, Enrollment.status, ("pending_payment", "active", "completed", "cancelled")),
        "revenue": money_row[0],
        "refunded": money_row[1],
        "certificates": db.query(func.count(Certificate.id)).scalar(),
        "reviews": db.query(func.count(Review.id)).scalar(),
    }


def course_stats(
    db: Session,
    *,
    teacher_id: int | None,
    include_drafts: bool,
    category_id: int | None,
    date_from: date | None,
    date_to: date | None,
    sort: str,
    limit: int,
) -> list:
    enrollments = (
        db.query(
            Enrollment.course_id.label("course_id"),
            func.count(Enrollment.id).filter(Enrollment.status.in_(ACCESS_STATUSES)).label("students"),
            func.count(Enrollment.id).filter(Enrollment.status == "completed").label("completed"),
        )
        .filter(*_period(Enrollment.enrolled_at, date_from, date_to))
        .group_by(Enrollment.course_id)
        .subquery()
    )
    revenue = (
        db.query(Enrollment.course_id.label("course_id"), func.sum(Payment.amount).label("revenue"))
        .join(Payment, Payment.enrollment_id == Enrollment.id)
        .filter(Payment.status == "succeeded", *_period(Payment.created_at, date_from, date_to))
        .group_by(Enrollment.course_id)
        .subquery()
    )
    ratings = rating_repository.course_ratings(db)
    students = func.coalesce(enrollments.c.students, 0)
    completed = func.coalesce(enrollments.c.completed, 0)
    money = func.coalesce(revenue.c.revenue, 0)
    reviews = func.coalesce(ratings.c.reviews_count, 0)

    query = (
        db.query(
            Course.id.label("course_id"),
            Course.title,
            Course.status,
            Category.name.label("category"),
            _full_name().label("teacher_name"),
            ratings.c.rating_avg.label("rating_avg"),
            reviews.label("reviews_count"),
            students.label("students"),
            completed.label("completed"),
            money.label("revenue"),
        )
        .join(Category, Category.id == Course.category_id)
        .join(User, User.id == Course.teacher_id)
        .outerjoin(enrollments, enrollments.c.course_id == Course.id)
        .outerjoin(revenue, revenue.c.course_id == Course.id)
        .outerjoin(ratings, ratings.c.course_id == Course.id)
    )
    if not include_drafts:
        query = query.filter(Course.status != "draft")
    if teacher_id is not None:
        query = query.filter(Course.teacher_id == teacher_id)
    if category_id is not None:
        query = query.filter(Course.category_id == category_id)

    order = {
        "students": (students.desc(), Course.id.desc()),
        "completed": (completed.desc(), students.desc(), Course.id.desc()),
        "revenue": (money.desc(), Course.id.desc()),
        "rating": (ratings.c.rating_avg.desc().nulls_last(), reviews.desc(), Course.id.desc()),
    }[sort]
    return query.order_by(*order).limit(limit).all()


def teacher_ranking(db: Session, *, date_from: date | None, date_to: date | None, sort: str, limit: int) -> list:
    courses = (
        db.query(Course.teacher_id.label("teacher_id"), func.count(Course.id).label("courses"))
        .filter(Course.status != "draft")
        .group_by(Course.teacher_id)
        .subquery()
    )
    learners = (
        db.query(
            Course.teacher_id.label("teacher_id"),
            func.count(Enrollment.student_id.distinct())
            .filter(Enrollment.status.in_(ACCESS_STATUSES))
            .label("students"),
            func.count(Enrollment.id).filter(Enrollment.status == "completed").label("completed"),
        )
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(*_period(Enrollment.enrolled_at, date_from, date_to))
        .group_by(Course.teacher_id)
        .subquery()
    )
    ratings = (
        db.query(
            Course.teacher_id.label("teacher_id"),
            func.avg(Review.rating).label("rating_avg"),
            func.count(Review.id).label("reviews_count"),
        )
        .join(Review, Review.course_id == Course.id)
        .group_by(Course.teacher_id)
        .subquery()
    )
    revenue = (
        db.query(Course.teacher_id.label("teacher_id"), func.sum(Payment.amount).label("revenue"))
        .join(Enrollment, Enrollment.course_id == Course.id)
        .join(Payment, Payment.enrollment_id == Enrollment.id)
        .filter(Payment.status == "succeeded", *_period(Payment.created_at, date_from, date_to))
        .group_by(Course.teacher_id)
        .subquery()
    )
    students = func.coalesce(learners.c.students, 0)
    completed = func.coalesce(learners.c.completed, 0)
    reviews = func.coalesce(ratings.c.reviews_count, 0)
    money = func.coalesce(revenue.c.revenue, 0)

    order = {
        "rating": (ratings.c.rating_avg.desc().nulls_last(), reviews.desc(), User.id),
        "students": (students.desc(), User.id),
        "revenue": (money.desc(), User.id),
        "courses": (courses.c.courses.desc(), User.id),
    }[sort]
    return (
        db.query(
            User.id.label("teacher_id"),
            _full_name().label("name"),
            courses.c.courses.label("courses"),
            students.label("students"),
            completed.label("completed"),
            ratings.c.rating_avg.label("rating_avg"),
            reviews.label("reviews_count"),
            money.label("revenue"),
        )
        .select_from(User)
        .join(courses, courses.c.teacher_id == User.id)
        .outerjoin(learners, learners.c.teacher_id == User.id)
        .outerjoin(ratings, ratings.c.teacher_id == User.id)
        .outerjoin(revenue, revenue.c.teacher_id == User.id)
        .order_by(*order)
        .limit(limit)
        .all()
    )


def revenue_series(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    group_by: str,
    course_id: int | None,
    teacher_id: int | None,
    category_id: int | None,
) -> list[dict]:
    revenue, refunded, payments = _money()
    bucket = _bucket(group_by, Payment.created_at)
    query = (
        db.query(
            bucket.label("period"), revenue.label("revenue"), refunded.label("refunded"), payments.label("payments")
        )
        .select_from(Payment)
        .join(Enrollment, Payment.enrollment_id == Enrollment.id)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(*_period(Payment.created_at, date_from, date_to))
    )
    if course_id is not None:
        query = query.filter(Course.id == course_id)
    if teacher_id is not None:
        query = query.filter(Course.teacher_id == teacher_id)
    if category_id is not None:
        query = query.filter(Course.category_id == category_id)

    rows = query.group_by(bucket).order_by(bucket).all()
    return [
        {"period": row.period.date(), "revenue": row.revenue, "refunded": row.refunded, "payments": row.payments}
        for row in rows
    ]


def revenue_breakdown(db: Session, *, by: str, date_from: date | None, date_to: date | None, limit: int) -> list:
    if by == "course":
        key, label = Course.id, Course.title
    elif by == "teacher":
        key, label = User.id, _full_name()
    else:
        key, label = Category.id, Category.name

    revenue, refunded, payments = _money()
    query = (
        db.query(
            key.label("id"),
            label.label("name"),
            revenue.label("revenue"),
            refunded.label("refunded"),
            payments.label("payments"),
        )
        .select_from(Payment)
        .join(Enrollment, Payment.enrollment_id == Enrollment.id)
        .join(Course, Enrollment.course_id == Course.id)
    )
    if by == "teacher":
        query = query.join(User, User.id == Course.teacher_id)
    elif by == "category":
        query = query.join(Category, Category.id == Course.category_id)

    return (
        query.filter(Payment.status.in_(("succeeded", "refunded")), *_period(Payment.created_at, date_from, date_to))
        .group_by(key, label)
        .order_by(revenue.desc(), key)
        .limit(limit)
        .all()
    )


def user_growth(db: Session, *, date_from: date, date_to: date, group_by: str) -> list[dict]:
    bucket = _bucket(group_by, User.created_at)
    rows = (
        db.query(
            bucket.label("period"),
            func.count(User.id).filter(User.role == "student").label("students"),
            func.count(User.id).filter(User.role == "teacher").label("teachers"),
            func.count(User.id).label("total"),
        )
        .filter(*_period(User.created_at, date_from, date_to))
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )
    return [
        {"period": row.period.date(), "students": row.students, "teachers": row.teachers, "total": row.total}
        for row in rows
    ]


def funnel_students(db: Session, course_id: int) -> int:
    return (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.course_id == course_id, Enrollment.status.in_(ACCESS_STATUSES))
        .scalar()
    )


def funnel_rows(db: Session, course_id: int) -> list:
    done = (
        db.query(LessonProgress.lesson_id.label("lesson_id"), func.count(LessonProgress.id).label("completed"))
        .join(Enrollment, LessonProgress.enrollment_id == Enrollment.id)
        .filter(Enrollment.course_id == course_id, Enrollment.status.in_(ACCESS_STATUSES))
        .group_by(LessonProgress.lesson_id)
        .subquery()
    )
    return (
        db.query(
            Lesson.id.label("lesson_id"),
            Lesson.title,
            Lesson.position,
            Module.title.label("module_title"),
            Module.position.label("module_position"),
            func.coalesce(done.c.completed, 0).label("completed"),
        )
        .join(Module, Lesson.module_id == Module.id)
        .outerjoin(done, done.c.lesson_id == Lesson.id)
        .filter(Module.course_id == course_id)
        .order_by(Module.position, Lesson.position, Lesson.id)
        .all()
    )


def quiz_stats(db: Session, course_id: int) -> list:
    submitted = QuizAttempt.status != "in_progress"
    return (
        db.query(
            Quiz.id.label("quiz_id"),
            Quiz.title,
            Module.title.label("module_title"),
            Quiz.passing_score,
            func.count(QuizAttempt.id).filter(submitted).label("attempts"),
            func.count(QuizAttempt.enrollment_id.distinct()).filter(submitted).label("students"),
            func.count(QuizAttempt.enrollment_id.distinct())
            .filter(QuizAttempt.passed.is_(True))
            .label("passed_students"),
            func.avg(QuizAttempt.score).filter(QuizAttempt.status == "graded").label("avg_score"),
            func.count(QuizAttempt.id).filter(QuizAttempt.status == "pending_review").label("pending_review"),
        )
        .join(Module, Quiz.module_id == Module.id)
        .outerjoin(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .filter(Module.course_id == course_id)
        .group_by(Quiz.id, Module.id)
        .order_by(Module.position)
        .all()
    )


def question_stats(db: Session, course_id: int, min_answers: int) -> list:
    return (
        db.query(
            Question.id.label("question_id"),
            Question.text,
            Question.question_type,
            Quiz.title.label("quiz_title"),
            func.count(AttemptAnswer.id).label("answered"),
            func.count(AttemptAnswer.id).filter(AttemptAnswer.is_correct.is_(True)).label("correct"),
        )
        .join(Quiz, Question.quiz_id == Quiz.id)
        .join(Module, Quiz.module_id == Module.id)
        .join(AttemptAnswer, AttemptAnswer.question_id == Question.id)
        .join(QuizAttempt, AttemptAnswer.attempt_id == QuizAttempt.id)
        .filter(
            Module.course_id == course_id,
            QuizAttempt.status != "in_progress",
            AttemptAnswer.is_correct.is_not(None),
        )
        .group_by(Question.id, Quiz.id)
        .having(func.count(AttemptAnswer.id) >= min_answers)
        .all()
    )


def course_students(
    db: Session,
    course_id: int,
    *,
    status: str | None,
    inactive_before: datetime | None,
    offset: int,
    limit: int,
) -> tuple[list, int]:
    last_progress = (
        db.query(
            LessonProgress.enrollment_id.label("enrollment_id"), func.max(LessonProgress.completed_at).label("last_at")
        )
        .group_by(LessonProgress.enrollment_id)
        .subquery()
    )
    activity = func.coalesce(last_progress.c.last_at, Enrollment.enrolled_at)

    query = (
        db.query(
            Enrollment.id.label("enrollment_id"),
            User.id.label("student_id"),
            _full_name().label("name"),
            Enrollment.status,
            Enrollment.enrolled_at,
            activity.label("last_activity_at"),
        )
        .select_from(Enrollment)
        .join(User, User.id == Enrollment.student_id)
        .outerjoin(last_progress, last_progress.c.enrollment_id == Enrollment.id)
        .filter(Enrollment.course_id == course_id)
    )
    query = (
        query.filter(Enrollment.status == status) if status else query.filter(Enrollment.status.in_(ACCESS_STATUSES))
    )
    if inactive_before is not None:
        query = query.filter(Enrollment.status == "active", activity < inactive_before)

    total = query.count()
    order = activity.asc() if inactive_before is not None else activity.desc()
    return query.order_by(order, Enrollment.id).offset(offset).limit(limit).all(), total
