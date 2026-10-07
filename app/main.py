from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1 import auth, categories, courses, users

app = FastAPI(title="Online Courses API")

register_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}