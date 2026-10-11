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
