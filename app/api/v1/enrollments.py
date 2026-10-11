from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user, get_payment_gateway, limit_by_user
from app.models.user import User
from app.patterns.adapters.payment_gateway import PaymentGateway
from app.schemas.enrollment import EnrollmentFilters, EnrollmentOut, PayRequest
from app.services import enrollment_service

router = APIRouter(tags=["enrollments"])


@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return enrollment_service.enroll(db, user, course_id)


# NOTE: "/enrollments/mine" must be declared BEFORE "/enrollments/{enrollment_id}"
@router.get("/enrollments/mine", response_model=list[EnrollmentOut])
def my_enrollments(
    filters: Annotated[EnrollmentFilters, Query()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return enrollment_service.list_my(db, user, filters)


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentOut)
def get_enrollment(enrollment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return enrollment_service.get_one(db, enrollment_id, user)


@router.post(
    "/enrollments/{enrollment_id}/pay",
    response_model=EnrollmentOut,
    dependencies=[Depends(limit_by_user("pay", limit=5, window_seconds=60))],
)
def pay(
    enrollment_id: int,
    data: PayRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway: PaymentGateway = Depends(get_payment_gateway),
):
    return enrollment_service.pay(db, enrollment_id, user, data, gateway)


@router.post("/enrollments/{enrollment_id}/cancel", response_model=EnrollmentOut)
def cancel(
    enrollment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gateway: PaymentGateway = Depends(get_payment_gateway),
):
    return enrollment_service.cancel(db, enrollment_id, user, gateway)
