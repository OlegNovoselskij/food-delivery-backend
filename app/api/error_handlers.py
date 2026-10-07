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
}


def _make_handler(status_code: int, detail: str):
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None

    async def handler(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)

    return handler


def register_error_handlers(app: FastAPI) -> None:
    for error_class, (status_code, detail) in ERROR_MAP.items():
        app.add_exception_handler(error_class, _make_handler(status_code, detail))