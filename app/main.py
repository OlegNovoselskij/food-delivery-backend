from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.admin import setup_admin
from app.api import dev_pages, health
from app.api.error_handlers import register_error_handlers
from app.api.v1 import (
    auth,
    categories,
    certificates,
    courses,
    curriculum,
    enrollments,
    learning,
    media,
    notifications,
    quizzes,
    recommendations,
    reports,
    reviews,
    users,
)
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.patterns.observer.subscribers import register_subscribers

configure_logging()

app = FastAPI(title="Online Courses API", version="1.0.0")

register_error_handlers(app)
register_subscribers()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,  # authentication is a bearer token in a header, never a cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Cache", "Retry-After", "Content-Disposition"],
    max_age=600,
)
app.add_middleware(RequestContextMiddleware)  # added last = outermost: it sees every request

app.include_router(health.router)
for module in (
    auth,
    users,
    categories,
    courses,
    curriculum,
    media,
    enrollments,
    learning,
    quizzes,
    notifications,
    certificates,
    reviews,
    reports,
    recommendations,
):
    app.include_router(module.router, prefix="/api/v1")

if config.GOOGLE_TEST_PAGE_ENABLED:  # a development helper, never enabled in production
    app.include_router(dev_pages.router)

setup_admin(app)
