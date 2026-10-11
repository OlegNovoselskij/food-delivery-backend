import re

import bcrypt

from app import security
from app.models.catalog import Category
from app.models.email_outbox import EmailOutbox
from app.models.user import User

PASSWORD = "Password123!"
API = "/api/v1"


def create_user(
    db, role: str = "student", email: str | None = None, verified: bool = True, password: str | None = PASSWORD
) -> User:
    user = User(
        name="Test",
        surname="User",
        email=email or f"user{db.query(User).count() + 1}@example.com",
        role=role,
        email_verified=verified,
        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode() if password else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_category(db, name: str = "Programming") -> Category:
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user.id, user.role)}"}


def last_code(db, email: str) -> str:
    db.expire_all()
    row = db.query(EmailOutbox).filter(EmailOutbox.to_email == email).order_by(EmailOutbox.id.desc()).first()
    assert row is not None, f"no email was queued for {email}"
    match = re.search(r"\b(\d{6})\b", row.text_body)
    assert match is not None, "the email contains no code"
    return match.group(1)


def build_course(
    client,
    teacher,
    category_id: int,
    *,
    price: str = "0",
    lessons: int = 2,
    publish: bool = True,
    title: str = "Sample course",
) -> dict:
    headers = auth(teacher)
    course = client.post(
        f"{API}/courses",
        headers=headers,
        json={
            "category_id": category_id,
            "title": title,
            "description": "Description",
            "level": "beginner",
            "price": price,
        },
    )
    assert course.status_code == 201, course.text
    course_id = course.json()["id"]
    module = client.post(f"{API}/courses/{course_id}/modules", headers=headers, json={"title": "Module 1"})
    assert module.status_code == 201, module.text
    module_id = module.json()["id"]
    lesson_ids = []
    for index in range(lessons):
        lesson = client.post(
            f"{API}/modules/{module_id}/lessons",
            headers=headers,
            json={
                "title": f"Lesson {index + 1}",
                "lesson_type": "article",
                "content": "Text",
                "duration_minutes": 10,
                "is_preview": index == 0,
            },
        )
        assert lesson.status_code == 201, lesson.text
        lesson_ids.append(lesson.json()["id"])
    if publish:
        published = client.post(f"{API}/courses/{course_id}/publish", headers=headers)
        assert published.status_code == 200, published.text
    return {"course_id": course_id, "module_id": module_id, "lesson_ids": lesson_ids}


def add_quiz(client, teacher, module_id: int, *, max_attempts: int = 3) -> dict:
    headers = auth(teacher)
    quiz = client.post(
        f"{API}/modules/{module_id}/quiz",
        headers=headers,
        json={"title": "Quiz", "passing_score": 60, "max_attempts": max_attempts},
    )
    assert quiz.status_code == 201, quiz.text
    quiz_id = quiz.json()["id"]

    def question(payload: dict) -> dict:
        response = client.post(f"{API}/quizzes/{quiz_id}/questions", headers=headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return {
        "quiz_id": quiz_id,
        "single": question(
            {
                "text": "Pick the right one",
                "question_type": "single_choice",
                "points": 2,
                "options": [{"text": "Right", "is_correct": True}, {"text": "Wrong"}],
            }
        ),
        "multiple": question(
            {
                "text": "Pick all right ones",
                "question_type": "multiple_choice",
                "points": 3,
                "options": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": True},
                    {"text": "C"},
                ],
            }
        ),
        "open": question({"text": "Explain your choice", "question_type": "open_text", "points": 5}),
    }


def option_ids(question: dict, *, correct: bool) -> list[int]:
    return [option["id"] for option in question["options"] if option["is_correct"] is correct]
