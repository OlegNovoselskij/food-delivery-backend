from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import client_ip, limit_by_ip
from app.schemas.user import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageOut,
    RegisterRequest,
    ResendCodeRequest,
    ResetPasswordRequest,
    Token,
    VerifyRegistrationRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("register", limit=10, window_seconds=3600))],
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    auth_service.register_user(db, data)
    return {"message": "A confirmation code was sent to your email"}


@router.post(
    "/resend-code",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("resend-code", limit=10, window_seconds=3600))],
)
def resend_code(data: ResendCodeRequest, db: Session = Depends(get_db)):
    auth_service.resend_code(db, data.email)
    return {"message": "If a registration is waiting for this email, a new code was sent"}  # the same answer always


@router.post(
    "/verify-email",
    response_model=Token,
    dependencies=[Depends(limit_by_ip("verify-email", limit=20, window_seconds=3600))],
)
def verify_email(data: VerifyRegistrationRequest, db: Session = Depends(get_db)):
    return Token(access_token=auth_service.verify_registration(db, data.email, data.code, data.password))


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(limit_by_ip("login", limit=20, window_seconds=60))],
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return Token(access_token=auth_service.login(db, data.email, data.password, client_ip(request)))


@router.post(
    "/forgot-password",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("forgot-password", limit=5, window_seconds=3600))],
)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.forgot_password(db, data.email)
    return {"message": "If an account with this email exists, a reset code was sent"}  # the same answer always


@router.post(
    "/reset-password",
    response_model=MessageOut,
    dependencies=[Depends(limit_by_ip("reset-password", limit=20, window_seconds=3600))],
)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, data.email, data.code, data.new_password)
    return {"message": "Password changed, please log in again"}
