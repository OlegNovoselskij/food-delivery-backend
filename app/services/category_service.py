from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import CategoryAlreadyExists, CategoryInUse, CategoryNotFound
from app.models.catalog import Category
from app.repository import category_repository
from app.schemas.category import CategoryCreate, CategoryUpdate


def list_categories(db: Session) -> list[Category]:
    return category_repository.list_all(db)


def create_category(db: Session, data: CategoryCreate) -> Category:
    if category_repository.get_by_name(db, data.name):
        raise CategoryAlreadyExists()
    category = Category(name=data.name)
    try:
        category_repository.add(db, category)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategoryAlreadyExists()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = category_repository.get_by_id(db, category_id)
    if category is None:
        raise CategoryNotFound()

    existing = category_repository.get_by_name(db, data.name)
    if existing and existing.id != category.id:
        raise CategoryAlreadyExists()

    category.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategoryAlreadyExists()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = category_repository.get_by_id(db, category_id)
    if category is None:
        raise CategoryNotFound()
    if category_repository.has_courses(db, category_id):
        raise CategoryInUse()
    category_repository.delete(db, category)
    db.commit()