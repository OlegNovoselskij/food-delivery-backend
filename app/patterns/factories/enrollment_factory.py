from abc import ABC

from app.models.catalog import Course
from app.models.enrollment import Enrollment


class EnrollmentCreator(ABC):
    initial_status: str

    def create(self, student_id: int, course_id: int) -> Enrollment:
        return Enrollment(student_id=student_id, course_id=course_id, status=self.initial_status)


class FreeEnrollmentCreator(EnrollmentCreator):
    initial_status = "active"


class PaidEnrollmentCreator(EnrollmentCreator):
    initial_status = "pending_payment"


class EnrollmentFactory:
    @staticmethod
    def for_course(course: Course) -> EnrollmentCreator:
        return FreeEnrollmentCreator() if course.price <= 0 else PaidEnrollmentCreator()
