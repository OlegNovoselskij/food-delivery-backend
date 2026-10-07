from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.catalog import Course

SORT_ORDER = {
    "newest": (Course.created_at.desc(), Course.id.desc()),
    "price_asc": (Course.price.asc(), Course.id.asc()),
    "price_desc": (Course.price.desc(), Course.id.desc()),
}


def _with_relations(query):
    return query.options(joinedload(Course.teacher), joinedload(Course.category))


def _escape_like(value: str) -> str:
    # щоб користувач не міг шукати "%" чи "_" як шаблонні символи
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_by_id(db: Session, course_id: int) -> Course | None:
    return _with_relations(db.query(Course)).filter(Course.id == course_id).first()


def list_by_teacher(db: Session, teacher_id: int) -> list[Course]:
    return (
        _with_relations(db.query(Course))
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.created_at.desc())
        .all()
    )


def search(
    db: Session,
    *,
    q: str | None,
    category_id: int | None,
    level: str | None,
    teacher_id: int | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    sort: str,
    offset: int,
    limit: int,
) -> tuple[list[Course], int]:
    query = _with_relations(db.query(Course)).filter(Course.status == "published")

    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        query = query.filter(
            or_(Course.title.ilike(pattern, escape="\\"), Course.description.ilike(pattern, escape="\\"))
        )
    if category_id is not None:
        query = query.filter(Course.category_id == category_id)
    if level is not None:
        query = query.filter(Course.level == level)
    if teacher_id is not None:
        query = query.filter(Course.teacher_id == teacher_id)
    if min_price is not None:
        query = query.filter(Course.price >= min_price)
    if max_price is not None:
        query = query.filter(Course.price <= max_price)

    total = query.count()
    items = query.order_by(*SORT_ORDER[sort]).offset(offset).limit(limit).all()
    return items, total


def add(db: Session, course: Course) -> Course:
    db.add(course)
    db.flush()
    return course


def delete(db: Session, course: Course) -> None:
    db.delete(course)