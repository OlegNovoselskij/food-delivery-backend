from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.course import CourseListItem

PaymentMethod = Literal["card", "paypal"]
EnrollmentStatus = Literal["pending_payment", "active", "completed", "cancelled"]


class PayRequest(BaseModel):
    method: PaymentMethod
    payment_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class EnrollmentFilters(BaseModel):
    status: EnrollmentStatus | None = None
    course_id: int | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    method: str
    status: str
    transaction_id: str | None
    created_at: datetime


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    enrolled_at: datetime
    completed_at: datetime | None
    course: CourseListItem
    payment: PaymentOut | None
