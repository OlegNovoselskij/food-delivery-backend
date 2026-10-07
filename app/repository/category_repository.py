from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.catalog import Category, Course


def list_all(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.name).all()


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_name(db: Session, name: str) -> Category | None:
    return db.query(Category).filter(func.lower(Category.name) == name.lower()).first()


def has_courses(db: Session, category_id: int) -> bool:
    return db.query(Course.id).filter(Course.category_id == category_id).first() is not None


def add(db: Session, category: Category) -> Category:
    db.add(category)
    db.flush()
    return category


def delete(db: Session, category: Category) -> None:
    db.delete(category)