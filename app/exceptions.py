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