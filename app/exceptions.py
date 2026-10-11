# auth
class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


# categories
class CategoryNotFound(Exception):
    pass


class CategoryAlreadyExists(Exception):
    pass


class CategoryInUse(Exception):
    pass


# courses
class CourseNotFound(Exception):
    pass


class NotCourseOwner(Exception):
    pass


class InvalidCourseTransition(Exception):
    pass


class CourseNotDeletable(Exception):
    pass


class ModuleNotFound(Exception):
    pass


class LessonNotFound(Exception):
    pass


class LessonLocked(Exception):
    pass


class CourseHasEnrollments(Exception):
    pass


class CourseIncomplete(Exception):
    pass


class InvalidOrdering(Exception):
    pass


class StorageUnavailable(Exception):
    pass


class InvalidUploadTicket(Exception):
    pass


class UploadNotFound(Exception):
    pass


class InvalidUploadedFile(Exception):
    pass


class LessonHasNoVideo(Exception):
    pass


class MaterialNotFound(Exception):
    pass


class EnrollmentNotFound(Exception):
    pass


class AlreadyEnrolled(Exception):
    pass


class CannotEnrollInOwnCourse(Exception):
    pass


class InvalidEnrollmentTransition(Exception):
    pass


class PaymentNotRequired(Exception):
    pass


class PaymentDeclined(Exception):
    pass


class PaymentRefundFailed(Exception):
    pass


class EnrollmentNotActive(Exception):
    pass


class QuizNotFound(Exception):
    pass


class QuestionNotFound(Exception):
    pass


class AttemptNotFound(Exception):
    pass


class QuizAlreadyExists(Exception):
    pass


class QuizHasAttempts(Exception):
    pass


class QuizNotReady(Exception):
    pass


class QuizAccessDenied(Exception):
    pass


class AttemptLimitReached(Exception):
    pass


class QuizAlreadyPassed(Exception):
    pass


class AttemptAwaitingReview(Exception):
    pass


class InvalidAttemptState(Exception):
    pass


class InvalidAnswers(Exception):
    pass


class InvalidQuestion(Exception):
    pass


class InvalidReview(Exception):
    pass


class NotificationNotFound(Exception):
    pass


class CertificateNotFound(Exception):
    pass


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")
        self.retry_after = retry_after


class ReportAccessDenied(Exception):
    pass


class ReviewNotFound(Exception):
    pass


class InvalidCode(Exception):
    pass
