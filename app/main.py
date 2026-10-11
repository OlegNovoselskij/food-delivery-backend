from fastapi import FastAPI

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
    users,
)
from app.patterns.observer.subscribers import register_subscribers

app = FastAPI(title="Online Courses API")

register_subscribers()

register_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(curriculum.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(enrollments.router, prefix="/api/v1")
app.include_router(learning.router, prefix="/api/v1")
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}