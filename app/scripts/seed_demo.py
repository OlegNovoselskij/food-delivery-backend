import random
import re
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.models.catalog import Category, Course, Lesson, Module
from app.models.quiz import AnswerOption, Question, Quiz
from app.models.user import User
from app.patterns.adapters.payment_gateway import MockPaymentGateway
from app.patterns.observer.subscribers import register_subscribers
from app.repository import quiz_repository, user_repository
from app.schemas.enrollment import PayRequest
from app.schemas.quiz import AnswerIn, ReviewGrade, ReviewRequest, SubmitRequest
from app.schemas.review import ReviewCreate
from app.security import hash_password
from app.services import attempt_service, enrollment_service, progress_service, review_service

PASSWORD = "Demo12345!"
ADMIN_EMAIL = "admin@demo.example.com"

TEACHERS = [
    (
        "Olena",
        "Kovalenko",
        "olena@demo.example.com",
        "Senior software engineer with 12 years in backend development. Loves clean code and teaching.",
    ),
    (
        "Taras",
        "Melnyk",
        "taras@demo.example.com",
        "Product designer who has shipped interfaces for fintech and education startups.",
    ),
    (
        "Iryna",
        "Bondar",
        "iryna@demo.example.com",
        "Data scientist and marketing analyst, former head of analytics at an e-commerce company.",
    ),
]
STUDENTS = [
    ("Andrii", "Shevchenko"),
    ("Maria", "Lysenko"),
    ("Dmytro", "Koval"),
    ("Sofiia", "Tkachenko"),
    ("Bohdan", "Savchuk"),
    ("Kateryna", "Moroz"),
    ("Yurii", "Petrenko"),
    ("Anna", "Hrytsenko"),
]
CATEGORIES = ["Programming", "Design", "Data Science", "Marketing"]


def _quiz(single, multiple, open_text):
    return [
        {"text": single[0], "type": "single_choice", "points": 2, "options": single[1], "explanation": single[2]},
        {
            "text": multiple[0],
            "type": "multiple_choice",
            "points": 3,
            "options": multiple[1],
            "explanation": multiple[2],
        },
        {"text": open_text, "type": "open_text", "points": 5, "options": [], "explanation": None},
    ]


QUIZ_BANK = {
    "Python for Beginners": _quiz(
        (
            "Which keyword defines a function in Python?",
            [("def", True), ("func", False), ("function", False), ("define", False)],
            "Functions are introduced with the def keyword.",
        ),
        (
            "Which of these are built-in Python types?",
            [("list", True), ("dict", True), ("array", False), ("struct", False)],
            "list and dict are built in; array and struct are not.",
        ),
        "Explain the difference between a list and a tuple.",
    ),
    "FastAPI in Practice": _quiz(
        (
            "Which library does FastAPI use for data validation?",
            [("Pydantic", True), ("Marshmallow", False), ("Cerberus", False), ("Colander", False)],
            "FastAPI builds on Pydantic models.",
        ),
        (
            "Which status codes describe a client error?",
            [("404", True), ("422", True), ("500", False), ("201", False)],
            "4xx codes are client errors.",
        ),
        "Describe how dependency injection works in FastAPI.",
    ),
    "UI Design Fundamentals": _quiz(
        (
            "What does good contrast improve most?",
            [("Readability", True), ("Loading speed", False), ("Server cost", False), ("SEO ranking", False)],
            "Contrast separates content from the background.",
        ),
        (
            "Which tools create visual hierarchy?",
            [("Size", True), ("Colour", True), ("Spacing", True), ("Random placement", False)],
            "Size, colour and spacing guide the eye.",
        ),
        "Describe an interface you improved and why your change worked.",
    ),
    "Data Analysis with Pandas": _quiz(
        (
            "Which method shows the first rows of a DataFrame?",
            [("head()", True), ("top()", False), ("first_rows()", False), ("peek()", False)],
            "head() returns the first five rows by default.",
        ),
        (
            "Which functions load tabular data?",
            [("read_csv", True), ("read_excel", True), ("load_all", False), ("open_table", False)],
            "read_csv and read_excel are standard loaders.",
        ),
        "Explain what groupby does and give an example.",
    ),
}

COURSES = [
    {
        "teacher": 0,
        "category": "Programming",
        "title": "Python for Beginners",
        "level": "beginner",
        "price": "0",
        "status": "published",
        "description": "Learn Python from scratch: syntax, data types, functions and your first real programs. No experience required.",
        "modules": [
            {
                "title": "Getting started",
                "quiz": True,
                "lessons": [
                    ("Welcome and setup", "video", 12, True),
                    ("Variables and types", "video", 18, False),
                    ("Control flow", "article", 15, False),
                ],
            },
            {
                "title": "Functions and modules",
                "quiz": False,
                "lessons": [
                    ("Writing functions", "video", 20, False),
                    ("Working with modules", "article", 14, False),
                    ("Your first project", "video", 25, False),
                ],
            },
        ],
    },
    {
        "teacher": 0,
        "category": "Programming",
        "title": "FastAPI in Practice",
        "level": "intermediate",
        "price": "49.00",
        "status": "published",
        "description": "Build a production-style REST API with FastAPI, PostgreSQL and authentication, then test and deploy it.",
        "modules": [
            {
                "title": "API fundamentals",
                "quiz": True,
                "lessons": [
                    ("Routing and validation", "video", 22, True),
                    ("Dependency injection", "video", 19, False),
                    ("Database access", "article", 17, False),
                ],
            },
            {
                "title": "Going to production",
                "quiz": False,
                "lessons": [
                    ("Authentication", "video", 24, False),
                    ("Testing the API", "video", 21, False),
                    ("Docker and deployment", "article", 16, False),
                ],
            },
        ],
    },
    {
        "teacher": 1,
        "category": "Design",
        "title": "UI Design Fundamentals",
        "level": "beginner",
        "price": "0",
        "status": "published",
        "description": "Master layout, typography and colour, and learn to design clean interfaces people enjoy using.",
        "modules": [
            {
                "title": "Visual basics",
                "quiz": True,
                "lessons": [
                    ("Layout and grids", "video", 16, True),
                    ("Typography", "video", 18, False),
                    ("Colour and contrast", "article", 14, False),
                ],
            },
            {
                "title": "Interfaces that work",
                "quiz": False,
                "lessons": [
                    ("Components and states", "video", 20, False),
                    ("Forms and feedback", "article", 12, False),
                    ("Design review", "video", 22, False),
                ],
            },
        ],
    },
    {
        "teacher": 1,
        "category": "Design",
        "title": "Design Systems with Figma",
        "level": "intermediate",
        "price": "39.00",
        "status": "published",
        "description": "Create a scalable design system in Figma: tokens, components, variants and documentation.",
        "modules": [
            {
                "title": "Foundations",
                "quiz": False,
                "lessons": [
                    ("Design tokens", "video", 15, True),
                    ("Component anatomy", "video", 20, False),
                    ("Variants and properties", "article", 13, False),
                ],
            },
            {
                "title": "Scaling up",
                "quiz": False,
                "lessons": [("Documentation", "article", 11, False), ("Versioning libraries", "video", 17, False)],
            },
        ],
    },
    {
        "teacher": 2,
        "category": "Data Science",
        "title": "Data Analysis with Pandas",
        "level": "intermediate",
        "price": "59.00",
        "status": "published",
        "description": "Clean, transform and explore real datasets with pandas and turn raw tables into clear answers.",
        "modules": [
            {
                "title": "Working with data",
                "quiz": True,
                "lessons": [
                    ("Loading data", "video", 14, True),
                    ("Cleaning and types", "video", 23, False),
                    ("Filtering and sorting", "article", 15, False),
                ],
            },
            {
                "title": "Insights",
                "quiz": False,
                "lessons": [
                    ("Grouping and aggregation", "video", 25, False),
                    ("Joining tables", "video", 19, False),
                    ("Visual summaries", "article", 13, False),
                ],
            },
        ],
    },
    {
        "teacher": 2,
        "category": "Marketing",
        "title": "Marketing Analytics 101",
        "level": "beginner",
        "price": "29.00",
        "status": "published",
        "description": "Measure what matters: funnels, attribution and the metrics that show whether campaigns really work.",
        "modules": [
            {
                "title": "Metrics that matter",
                "quiz": False,
                "lessons": [
                    ("The marketing funnel", "video", 13, True),
                    ("Attribution models", "video", 18, False),
                    ("Reading dashboards", "article", 12, False),
                ],
            },
            {
                "title": "From data to decisions",
                "quiz": False,
                "lessons": [
                    ("Running experiments", "video", 21, False),
                    ("Reporting to stakeholders", "article", 10, False),
                ],
            },
        ],
    },
    {
        "teacher": 0,
        "category": "Programming",
        "title": "Advanced SQL",
        "level": "advanced",
        "price": "45.00",
        "status": "draft",
        "description": "Window functions, recursive queries and query planning for data-heavy applications.",
        "modules": [
            {
                "title": "Window functions",
                "quiz": False,
                "lessons": [("Ranking and partitions", "video", 20, False), ("Running totals", "article", 12, False)],
            }
        ],
    },
    {
        "teacher": 0,
        "category": "Programming",
        "title": "Intro to jQuery",
        "level": "beginner",
        "price": "0",
        "status": "archived",
        "description": "A short, legacy introduction to jQuery, kept for students who already joined.",
        "modules": [
            {
                "title": "The basics",
                "quiz": False,
                "lessons": [("Selecting elements", "video", 10, True), ("Handling events", "article", 9, False)],
            }
        ],
    },
]

PLAN = [
    (0, "Python for Beginners", "complete"),
    (1, "Python for Beginners", "complete"),
    (2, "Python for Beginners", "partial:4"),
    (3, "Python for Beginners", "quiz_failed"),
    (4, "Python for Beginners", "partial:2"),
    (0, "FastAPI in Practice", "partial:3"),
    (1, "FastAPI in Practice", "complete"),
    (5, "FastAPI in Practice", "unpaid"),
    (2, "UI Design Fundamentals", "complete"),
    (3, "UI Design Fundamentals", "partial:5"),
    (6, "UI Design Fundamentals", "partial:1"),
    (4, "Design Systems with Figma", "complete"),
    (7, "Design Systems with Figma", "partial:2"),
    (5, "Data Analysis with Pandas", "complete"),
    (6, "Data Analysis with Pandas", "partial:3"),
    (7, "Data Analysis with Pandas", "unpaid"),
    (0, "Marketing Analytics 101", "partial:2"),
    (3, "Marketing Analytics 101", "complete"),
]

REVIEWS = [
    "Clear explanations and very practical examples.",
    "Well structured, I could apply everything right away.",
    "Good pace and useful exercises. Would love even more examples.",
    "The best course on this topic I have taken so far.",
    "Solid content, the instructor answers questions quickly.",
]
OPEN_ANSWER = "A list can be changed after creation, while a tuple is fixed, so tuples are safer for constant data."


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def create_user(db: Session, first: str, last: str, email: str, role: str, bio: str | None = None) -> User:
    user = User(
        name=first,
        surname=last,
        email=email,
        role=role,
        bio=bio,
        password_hash=hash_password(PASSWORD),
        email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def add_quiz(db: Session, module: Module, questions: list[dict]) -> None:
    quiz = Quiz(module_id=module.id, title=f"{module.title}: checkpoint", passing_score=60, max_attempts=3)
    db.add(quiz)
    db.flush()
    for position, item in enumerate(questions):
        question = Question(
            quiz_id=quiz.id,
            text=item["text"],
            question_type=item["type"],
            points=item["points"],
            explanation=item["explanation"],
            position=position,
        )
        question.options = [AnswerOption(text=option, is_correct=correct) for option, correct in item["options"]]
        db.add(question)
    db.flush()


def create_course(db: Session, teacher: User, category: Category, spec: dict) -> Course:
    course = Course(
        teacher_id=teacher.id,
        category_id=category.id,
        title=spec["title"],
        description=spec["description"],
        level=spec["level"],
        price=Decimal(spec["price"]),
        status=spec["status"],
        cover_url=f"https://picsum.photos/seed/{_slug(spec['title'])}/800/450",
    )
    db.add(course)
    db.flush()
    for module_position, module_spec in enumerate(spec["modules"]):
        module = Module(course_id=course.id, title=module_spec["title"], position=module_position)
        db.add(module)
        db.flush()
        for lesson_position, (title, kind, minutes, preview) in enumerate(module_spec["lessons"]):
            db.add(
                Lesson(
                    module_id=module.id,
                    title=title,
                    lesson_type=kind,
                    duration_minutes=minutes,
                    position=lesson_position,
                    is_preview=preview,
                    content=f"{title}. A focused lesson with short explanations, examples and a recap.",
                )
            )
        if module_spec["quiz"] and spec["title"] in QUIZ_BANK:
            add_quiz(db, module, QUIZ_BANK[spec["title"]])
    db.flush()
    return course


def lesson_ids_of(db: Session, course: Course) -> list[int]:
    rows = (
        db.query(Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course.id)
        .order_by(Module.position, Lesson.position)
        .all()
    )
    return [lesson_id for (lesson_id,) in rows]


def take_quiz(db: Session, student: User, teacher: User, course: Course, passing: bool) -> None:
    quiz = db.query(Quiz).join(Module, Quiz.module_id == Module.id).filter(Module.course_id == course.id).first()
    if quiz is None:
        return
    attempt = attempt_service.start_attempt(db, quiz.id, student)
    questions = quiz_repository.get_quiz(db, quiz.id).questions
    answers = []
    for question in questions:
        correct = [option.id for option in question.options if option.is_correct]
        wrong = [option.id for option in question.options if not option.is_correct]
        if question.question_type == "open_text":
            answers.append(AnswerIn(question_id=question.id, text=OPEN_ANSWER if passing else None))
        else:
            answers.append(AnswerIn(question_id=question.id, option_ids=correct if passing else wrong[:1]))
    result = attempt_service.submit_attempt(db, attempt["id"], student, SubmitRequest(answers=answers))
    if result["status"] == "pending_review":
        grades = [
            ReviewGrade(question_id=q.id, points=q.points, comment="Clear and complete answer.")
            for q in questions
            if q.question_type == "open_text"
        ]
        attempt_service.review_attempt(db, attempt["id"], teacher, ReviewRequest(grades=grades))


def run_story(db: Session, student: User, course: Course, teacher: User, behavior: str, rng: random.Random) -> None:
    gateway = MockPaymentGateway()
    enrollment = enrollment_service.enroll(db, student, course.id)
    if enrollment.status == "pending_payment":
        if behavior == "unpaid":
            return
        enrollment_service.pay(db, enrollment.id, student, PayRequest(method="card", payment_token="tok_visa"), gateway)

    lessons = lesson_ids_of(db, course)
    count = int(behavior.split(":")[1]) if behavior.startswith("partial:") else len(lessons)
    for lesson_id in lessons[:count]:
        progress_service.mark_lesson(db, enrollment.id, lesson_id, student)

    if behavior in ("complete", "quiz_failed"):
        take_quiz(db, student, teacher, course, passing=behavior == "complete")
    if behavior == "complete" or (behavior.startswith("partial:") and count >= 2):
        review_service.create_review(
            db, student, course.id, ReviewCreate(rating=rng.choice([4, 4, 5, 5, 3]), comment=rng.choice(REVIEWS))
        )


SPREAD_DATES = [
    "UPDATE users SET created_at = now() - interval '110 days' + random() * interval '20 days' WHERE email LIKE '%@demo.example.com'",
    "UPDATE courses SET created_at = now() - interval '105 days' + random() * interval '10 days'",
    "UPDATE enrollments SET enrolled_at = now() - random() * interval '85 days'",
    "UPDATE enrollments SET completed_at = LEAST(now(), enrolled_at + interval '10 days') WHERE status = 'completed'",
    "UPDATE payments SET created_at = e.enrolled_at + interval '2 minutes' FROM enrollments e WHERE e.id = payments.enrollment_id",
    "UPDATE lesson_progress SET completed_at = LEAST(now(), e.enrolled_at + random() * interval '10 days') FROM enrollments e WHERE e.id = lesson_progress.enrollment_id",
    "UPDATE quiz_attempts SET started_at = LEAST(now(), e.enrolled_at + interval '9 days'), submitted_at = LEAST(now(), e.enrolled_at + interval '9 days 5 minutes') FROM enrollments e WHERE e.id = quiz_attempts.enrollment_id AND quiz_attempts.submitted_at IS NOT NULL",
    "UPDATE certificates SET issued_at = e.completed_at FROM enrollments e WHERE e.id = certificates.enrollment_id",
    "UPDATE reviews SET created_at = LEAST(now(), e.enrolled_at + interval '11 days') FROM enrollments e WHERE e.student_id = reviews.student_id AND e.course_id = reviews.course_id",
]


def main() -> None:
    if config.APP_ENV == "production":
        raise SystemExit("Refusing to create demo data in production")
    register_subscribers()
    rng = random.Random(42)

    with SessionLocal() as db:
        if user_repository.get_by_email(db, ADMIN_EMAIL):
            print("Demo data already exists. Run `docker compose down -v` to start from an empty database.")
            return

        create_user(db, "Admin", "Demo", ADMIN_EMAIL, "admin")
        teachers = [create_user(db, first, last, email, "teacher", bio) for first, last, email, bio in TEACHERS]
        students = [
            create_user(db, first, last, f"{first.lower()}@demo.example.com", "student") for first, last in STUDENTS
        ]
        categories = {name: Category(name=name) for name in CATEGORIES}
        db.add_all(categories.values())
        db.flush()
        courses = {
            spec["title"]: create_course(db, teachers[spec["teacher"]], categories[spec["category"]], spec)
            for spec in COURSES
        }
        db.commit()

        for student_index, title, behavior in PLAN:
            course = courses[title]
            teacher = next(t for t in teachers if t.id == course.teacher_id)
            run_story(db, students[student_index], course, teacher, behavior, rng)

        for statement in SPREAD_DATES:
            db.execute(text(statement))
        db.commit()

    print("Demo data created.")
    print(f"  admin:    {ADMIN_EMAIL}")
    print("  teachers: " + ", ".join(email for _, _, email, _ in TEACHERS))
    print("  students: " + ", ".join(f"{first.lower()}@demo.example.com" for first, _ in STUDENTS[:3]) + ", ...")
    print(f"  password for everyone: {PASSWORD}")


if __name__ == "__main__":
    main()
