from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import client_ip, limit_by_ip
from app.schemas.user import LoginRequest, Token, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_ip("register", limit=10, window_seconds=3600))],
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(limit_by_ip("login", limit=20, window_seconds=60))],
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return Token(access_token=auth_service.login(db, data.email, data.password, client_ip(request)))
