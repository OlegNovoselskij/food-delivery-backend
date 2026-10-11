from fastapi import FastAPI
from sqladmin import Admin

from app import config
from app.admin import views
from app.admin.auth import AdminAuth
from app.database import engine

VIEWS = (
    views.UserAdmin,
    views.CategoryAdmin,
    views.CourseAdmin,
    views.ReviewAdmin,
    views.EnrollmentAdmin,
    views.PaymentAdmin,
    views.CertificateAdmin,
    views.EmailOutboxAdmin,
)


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(config.ADMIN_SESSION_SECRET),
        base_url="/admin",
        title="Courses admin",
    )
    for view in VIEWS:
        admin.add_view(view)
    return admin
