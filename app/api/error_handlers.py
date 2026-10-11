from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import exceptions as exc

ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    exc.EmailAlreadyRegistered: (409, "Email already registered"),
    exc.InvalidCredentials: (401, "Incorrect email or password"),
    exc.CategoryNotFound: (404, "Category not found"),
    exc.CategoryAlreadyExists: (409, "Category with this name already exists"),
    exc.CategoryInUse: (409, "Category has courses and cannot be deleted"),
    exc.CourseNotFound: (404, "Course not found"),
    exc.NotCourseOwner: (403, "You can only modify your own courses"),
    exc.InvalidCourseTransition: (409, "This status change is not allowed"),
    exc.CourseNotDeletable: (409, "Only draft courses can be deleted, archive it instead"),
    exc.ModuleNotFound: (404, "Module not found"),
    exc.LessonNotFound: (404, "Lesson not found"),
    exc.LessonLocked: (403, "Enroll in the course to access this lesson"),
    exc.CourseHasEnrollments: (409, "Course already has students, content cannot be deleted"),
    exc.CourseIncomplete: (409, "Add at least one lesson before publishing"),
    exc.InvalidOrdering: (422, "ids must match the current items exactly"),
    exc.StorageUnavailable: (503, "File storage is unavailable, try again later"),
    exc.InvalidUploadTicket: (400, "Upload ticket is invalid or expired"),
    exc.UploadNotFound: (409, "File is not in storage yet, upload it first"),
    exc.InvalidUploadedFile: (422, "Uploaded file has a wrong type or is too large, it was removed"),
    exc.LessonHasNoVideo: (404, "Lesson has no video"),
    exc.MaterialNotFound: (404, "Material not found"),
    exc.EnrollmentNotFound: (404, "Enrollment not found"),
    exc.AlreadyEnrolled: (409, "You are already enrolled in this course"),
    exc.CannotEnrollInOwnCourse: (409, "You cannot enroll in your own course"),
    exc.InvalidEnrollmentTransition: (409, "This action is not allowed for the current enrollment status"),
    exc.PaymentNotRequired: (409, "This enrollment does not need a payment"),
    exc.PaymentDeclined: (402, "Payment was declined"),
    exc.PaymentRefundFailed: (502, "Refund failed, try again later"),
    exc.EnrollmentNotActive: (409, "Progress can only be changed while the enrollment is active"),
    exc.QuizNotFound: (404, "Quiz not found"),
    exc.QuestionNotFound: (404, "Question not found"),
    exc.AttemptNotFound: (404, "Attempt not found"),
    exc.QuizAlreadyExists: (409, "This module already has a quiz"),
    exc.QuizHasAttempts: (409, "Students already took this quiz, this change is not allowed"),
    exc.QuizNotReady: (409, "Quiz has no questions yet"),
    exc.QuizAccessDenied: (403, "Enroll in the course to take this quiz"),
    exc.AttemptLimitReached: (409, "No attempts left for this quiz"),
    exc.QuizAlreadyPassed: (409, "You have already passed this quiz"),
    exc.AttemptAwaitingReview: (409, "Your previous attempt is waiting for the teacher's review"),
    exc.InvalidAttemptState: (409, "This action is not allowed for the current attempt status"),
    exc.InvalidAnswers: (422, "Answers do not match the quiz questions"),
    exc.InvalidQuestion: (422, "Option ids do not belong to this question"),
    exc.InvalidReview: (422, "Grades must cover exactly the answers waiting for review and stay within question points"),
    exc.NotificationNotFound: (404, "Notification not found"),
    exc.CertificateNotFound: (404, "Certificate not found"),
}


def _make_handler(status_code: int, detail: str):
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    async def handler(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)

    return handler


def register_error_handlers(app: FastAPI) -> None:
    for error_class, (status_code, detail) in ERROR_MAP.items():
        app.add_exception_handler(error_class, _make_handler(status_code, detail))