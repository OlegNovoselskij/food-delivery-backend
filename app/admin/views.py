from pydantic import ValidationError
from sqladmin import ModelView, action
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import RedirectResponse
from wtforms import SelectField

from app.admin.db import invalidate_catalog, run_in_db
from app.api.error_handlers import ERROR_MAP
from app.models.catalog import Category, Course
from app.models.email_outbox import EmailOutbox
from app.models.enrollment import Certificate, Enrollment, Payment
from app.models.review import Review
from app.models.user import User
from app.repository import category_repository, user_repository
from app.schemas.category import CategoryCreate
from app.schemas.course import CourseUpdate
from app.schemas.user import UserUpdate
from app.services import course_service, review_service

ROLES = ("student", "teacher", "admin")
LEVELS = ("beginner", "intermediate", "advanced")


def _validation_message(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}" if location else first["msg"]


def _error_message(error: Exception) -> str:
    return ERROR_MAP.get(type(error), (0, "Unexpected error"))[1]


def _category_id_by_name(db, name: str) -> int | None:
    category = category_repository.get_by_name(db, name)
    return category.id if category else None


def _has_courses(db, category_id: int) -> bool:
    return category_repository.has_courses(db, category_id)


def _owns_courses(db, user_id: int) -> bool:
    return db.query(Course.id).filter(Course.teacher_id == user_id).first() is not None


def _change_course_status(db, course_id: int, admin_id: int, target: str) -> None:
    course_service.change_status(db, course_id, user_repository.get_by_id(db, admin_id), target)


def _delete_review(db, review_id: int, admin_id: int) -> None:
    review_service.delete_review(db, review_id, user_repository.get_by_id(db, admin_id))


class SecureView(ModelView):
    page_size = 25
    page_size_options = [25, 50, 100]
    can_export = False  # SQLAdmin exports are not escaped against CSV injection: use /reports?format=csv

    def is_accessible(self, request: Request) -> bool:
        return request.session.get("admin_id") is not None


class ReadOnlyView(SecureView):
    can_create = False
    can_edit = False
    can_delete = False


class UserAdmin(SecureView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    category = "People"

    can_create = False
    can_delete = False

    column_list = [User.id, User.name, User.surname, User.email, User.role, User.email_verified, User.created_at]
    column_searchable_list = [User.email, User.name, User.surname]
    column_sortable_list = [User.id, User.email, User.role, User.created_at]
    column_default_sort = ("created_at", True)
    column_details_exclude_list = [User.password_hash]

    form_columns = [User.name, User.surname, User.phone, User.bio, User.role]
    form_overrides = {"role": SelectField}
    form_args = {"role": {"choices": [(role, role) for role in ROLES]}}

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        if data.get("role") not in ROLES:
            raise ValueError("Unknown role")
        try:
            cleaned = UserUpdate(
                name=data.get("name"),
                surname=data.get("surname"),
                phone=data.get("phone") or None,
                bio=data.get("bio") or None,
            )
        except ValidationError as error:
            raise ValueError(_validation_message(error)) from error
        data.update(cleaned.model_dump())

        if data["role"] != model.role:
            if model.id == request.session.get("admin_id"):
                raise ValueError("You cannot change your own role")
            if data["role"] == "student" and await run_in_db(_owns_courses, model.id):
                raise ValueError("This user owns courses: archive or reassign them before making the user a student")

    async def after_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        await invalidate_catalog()


class CategoryAdmin(SecureView, model=Category):
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-tags"
    category = "Catalog"

    column_list = [Category.id, Category.name]
    column_searchable_list = [Category.name]
    column_sortable_list = [Category.id, Category.name]
    column_default_sort = "name"
    form_columns = [Category.name]

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        try:
            name = CategoryCreate(name=data.get("name") or "").name
        except ValidationError as error:
            raise ValueError(_validation_message(error)) from error
        existing_id = await run_in_db(_category_id_by_name, name)
        if existing_id is not None and existing_id != getattr(model, "id", None):
            raise ValueError("A category with this name already exists")
        data["name"] = name

    async def on_model_delete(self, model, request: Request) -> None:
        if await run_in_db(_has_courses, model.id):
            raise ValueError("This category has courses and cannot be deleted")

    async def after_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        await invalidate_catalog()

    async def after_model_delete(self, model, request: Request) -> None:
        await invalidate_catalog()


class CourseAdmin(SecureView, model=Course):
    name = "Course"
    name_plural = "Courses"
    icon = "fa-solid fa-book"
    category = "Catalog"

    can_create = False
    can_delete = False

    column_list = [
        Course.id,
        Course.title,
        Course.teacher,
        Course.category,
        Course.status,
        Course.price,
        Course.created_at,
    ]
    column_searchable_list = [Course.title]
    column_sortable_list = [Course.id, Course.title, Course.status, Course.price, Course.created_at]
    column_default_sort = ("created_at", True)
    column_details_list = [
        Course.id,
        Course.title,
        Course.description,
        Course.teacher,
        Course.category,
        Course.level,
        Course.price,
        Course.status,
        Course.cover_url,
        Course.created_at,
        Course.updated_at,
    ]

    form_columns = [Course.title, Course.description, Course.level, Course.category]
    form_overrides = {"level": SelectField}
    form_args = {"level": {"choices": [(level, level) for level in LEVELS]}}

    async def on_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        try:
            cleaned = CourseUpdate(
                title=data.get("title"),
                description=data.get("description") or None,
                level=data.get("level"),
            )
        except ValidationError as error:
            raise ValueError(_validation_message(error)) from error
        data.update(title=cleaned.title, description=cleaned.description, level=cleaned.level)

    async def after_model_change(self, data: dict, model, is_created: bool, request: Request) -> None:
        await invalidate_catalog()

    @action(
        name="archive",
        label="Archive",
        confirmation_message="Archive the selected courses? Students who already joined keep their access.",
    )
    async def archive(self, request: Request):
        return await self._change_status(request, "archived")

    @action(name="publish", label="Publish", confirmation_message="Publish the selected courses?")
    async def publish(self, request: Request):
        return await self._change_status(request, "published")

    async def _change_status(self, request: Request, target: str):
        admin_id = request.session["admin_id"]
        errors = []
        for pk in (pk for pk in request.query_params.get("pks", "").split(",") if pk):
            try:
                await run_in_db(_change_course_status, int(pk), admin_id, target)
            except Exception as error:
                errors.append(f"#{pk}: {_error_message(error)}")

        url = URL(str(request.url_for("admin:list", identity=self.identity)))
        if errors:
            url = url.include_query_params(error="; ".join(errors))
        return RedirectResponse(url, status_code=302)


class ReviewAdmin(SecureView, model=Review):
    name = "Review"
    name_plural = "Reviews"
    icon = "fa-solid fa-star"
    category = "Catalog"

    can_create = False
    can_edit = False

    column_list = [Review.id, Review.course, Review.student, Review.rating, Review.comment, Review.created_at]
    column_searchable_list = [Review.comment]
    column_sortable_list = [Review.id, Review.rating, Review.created_at]
    column_default_sort = ("created_at", True)
    column_formatters = {Review.comment: lambda model, attribute: (model.comment or "")[:80]}

    async def delete_model(self, request: Request, pk) -> None:
        await run_in_db(_delete_review, int(pk), request.session["admin_id"])


class EnrollmentAdmin(ReadOnlyView, model=Enrollment):
    name = "Enrollment"
    name_plural = "Enrollments"
    icon = "fa-solid fa-graduation-cap"
    category = "Sales"

    column_list = [
        Enrollment.id,
        Enrollment.student,
        Enrollment.course,
        Enrollment.status,
        Enrollment.enrolled_at,
        Enrollment.completed_at,
    ]
    column_searchable_list = ["student.email", "course.title"]
    column_sortable_list = [Enrollment.id, Enrollment.status, Enrollment.enrolled_at, Enrollment.completed_at]
    column_default_sort = ("enrolled_at", True)
    column_details_list = [
        Enrollment.id,
        Enrollment.student,
        Enrollment.course,
        Enrollment.status,
        Enrollment.enrolled_at,
        Enrollment.completed_at,
        Enrollment.payments,
    ]


class PaymentAdmin(ReadOnlyView, model=Payment):
    name = "Payment"
    name_plural = "Payments"
    icon = "fa-solid fa-credit-card"
    category = "Sales"

    column_list = [
        Payment.id,
        Payment.enrollment,
        Payment.amount,
        Payment.method,
        Payment.status,
        Payment.transaction_id,
        Payment.created_at,
    ]
    column_searchable_list = [Payment.transaction_id]
    column_sortable_list = [Payment.id, Payment.amount, Payment.status, Payment.created_at]
    column_default_sort = ("created_at", True)


class CertificateAdmin(ReadOnlyView, model=Certificate):
    name = "Certificate"
    name_plural = "Certificates"
    icon = "fa-solid fa-certificate"
    category = "Sales"

    column_list = [Certificate.id, Certificate.certificate_number, Certificate.enrollment, Certificate.issued_at]
    column_searchable_list = [Certificate.certificate_number]
    column_sortable_list = [Certificate.id, Certificate.issued_at]
    column_default_sort = ("issued_at", True)


class EmailOutboxAdmin(ReadOnlyView, model=EmailOutbox):
    name = "Email"
    name_plural = "Emails"
    icon = "fa-solid fa-envelope"
    category = "Sales"

    column_list = [
        EmailOutbox.id,
        EmailOutbox.to_email,
        EmailOutbox.subject,
        EmailOutbox.status,
        EmailOutbox.attempts,
        EmailOutbox.next_attempt_at,
        EmailOutbox.last_error,
        EmailOutbox.sent_at,
    ]
    column_searchable_list = [EmailOutbox.to_email, EmailOutbox.subject]
    column_sortable_list = [EmailOutbox.id, EmailOutbox.status, EmailOutbox.attempts, EmailOutbox.sent_at]
    column_default_sort = ("id", True)
    column_details_exclude_list = [EmailOutbox.text_body, EmailOutbox.html_body]  # bodies may hold one-time codes
