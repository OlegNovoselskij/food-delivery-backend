from datetime import datetime

from pydantic import BaseModel


class CertificateOut(BaseModel):
    id: int
    certificate_number: str
    issued_at: datetime
    enrollment_id: int
    course_id: int
    course_title: str
    student_name: str
    teacher_name: str


class CertificateVerifyOut(BaseModel):
    valid: bool = True
    certificate_number: str
    student_name: str
    course_title: str
    teacher_name: str
    issued_at: datetime
