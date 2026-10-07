from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import require_role
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return category_service.list_categories(db)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return category_service.create_category(db, data)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return category_service.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    category_service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)