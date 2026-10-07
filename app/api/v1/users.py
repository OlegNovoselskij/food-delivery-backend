from fastapi import APIRouter, Depends

from app.dependency import get_current_user
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.update_profile(db, current_user, data)