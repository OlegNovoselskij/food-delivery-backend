from sqlalchemy.orm import Session

from app.exceptions import (
    AttemptAwaitingReview,
    AttemptLimitReached,
    AttemptNotFound,
    EnrollmentNotActive,
    InvalidAnswers,
    InvalidAttemptState,
    InvalidReview,
    QuizAccessDenied,
    QuizAlreadyPassed,
    QuizNotFound,
    QuizNotReady,
)
from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.enrollment import Enrollment
from app.models.user import User
from app.patterns.factories.grading_factory import GradingStrategyFactory
from app.patterns.states.attempt_state import IN_PROGRESS, AttemptStateMachine
from app.patterns.strategies.grading import StudentAnswer
from app.repository import attempt_repository, enrollment_repository, quiz_repository
from app.schemas.quiz import ReviewRequest, SubmitRequest
from app.services import progress_service
from app.services.access import can_manage_course


def _attempt_view(attempt: QuizAttempt) -> dict:
    quiz = attempt.quiz
    view = {
        "id": attempt.id,
        "quiz_id": quiz.id,
        "quiz_title": quiz.title,
        "status": attempt.status,
        "passing_score": quiz.passing_score,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "passed": attempt.passed,
        "points_earned": attempt.points_earned,
        "points_total": attempt.points_total,
        "questions": None,
        "review": None,
    }
    if attempt.status == IN_PROGRESS:
        view["questions"] = quiz.questions  # the public schema has no "is_correct"
        return view

    answers = {answer.question_id: answer for answer in attempt.answers}
    review = []
    for question in quiz.questions:
        answer = answers.get(question.id)
        if answer is None:
            continue  # the question was added after this attempt was submitted
        review.append(
            {
                "question_id": question.id,
                "question_text": question.text,
                "question_type": question.question_type,
                "points": question.points,
                "options": question.options,
                "selected_option_ids": answer.selected_option_ids,
                "text_answer": answer.text_answer,
                "correct_option_ids": [option.id for option in question.options if option.is_correct],
                "is_correct": answer.is_correct,
                "points_awarded": answer.points_awarded,
                "needs_review": question.question_type == "open_text" and answer.points_awarded is None,
                "explanation": question.explanation,
                "teacher_comment": answer.teacher_comment,
            }
        )
    view["review"] = review
    return view


def _load_view(db: Session, attempt_id: int) -> dict:
    return _attempt_view(attempt_repository.get_full(db, attempt_id))


def _finalize(db: Session, attempt: QuizAttempt, enrollment: Enrollment, earned: int) -> None:
    attempt.points_earned = earned
    attempt.score = earned * 100 // attempt.points_total if attempt.points_total else 0
    attempt.passed = attempt.score >= attempt.quiz.passing_score
    db.flush()
    progress_service.complete_if_finished(db, enrollment)


def start_attempt(db: Session, quiz_id: int, student: User) -> dict:
    quiz = quiz_repository.get_quiz(db, quiz_id)
    if quiz is None:
        raise QuizNotFound()

    enrollment = enrollment_repository.get_by_student_and_course(db, student.id, quiz.module.course_id)
    if enrollment is None or enrollment.status in ("pending_payment", "cancelled"):
        raise QuizAccessDenied()

    # row lock: two parallel clicks on "start" must not create two attempts
    enrollment = enrollment_repository.get_by_id_for_update(db, enrollment.id)
    if enrollment.status != "active":
        raise EnrollmentNotActive()
    if not quiz.questions:
        raise QuizNotReady()

    open_attempt = attempt_repository.find_open(db, enrollment.id, quiz.id)
    if open_attempt is not None:
        return _load_view(db, open_attempt.id)

    if attempt_repository.has_passed(db, enrollment.id, quiz.id):
        raise QuizAlreadyPassed()
    if attempt_repository.has_pending(db, enrollment.id, quiz.id):
        raise AttemptAwaitingReview()
    if quiz.max_attempts is not None and attempt_repository.count_submitted(db, enrollment.id, quiz.id) >= quiz.max_attempts:
        raise AttemptLimitReached()

    attempt = attempt_repository.add(db, QuizAttempt(enrollment_id=enrollment.id, quiz_id=quiz.id))
    db.commit()
    return _load_view(db, attempt.id)


def submit_attempt(db: Session, attempt_id: int, student: User, data: SubmitRequest) -> dict:
    locked = attempt_repository.get_for_update(db, attempt_id)
    if locked is None or locked.enrollment.student_id != student.id:
        raise AttemptNotFound()  # 404 instead of 403: do not reveal that someone else's attempt exists

    attempt = attempt_repository.get_full(db, attempt_id)
    machine = AttemptStateMachine(attempt)
    if not machine.accepts_answers():
        raise InvalidAttemptState()

    enrollment = enrollment_repository.get_by_id_for_update(db, attempt.enrollment_id)
    if enrollment.status != "active":
        raise EnrollmentNotActive()

    quiz = attempt.quiz
    questions = {question.id: question for question in quiz.questions}

    given: dict[int, StudentAnswer] = {}
    for item in data.answers:
        question = questions.get(item.question_id)
        if question is None:
            raise InvalidAnswers()
        option_ids = frozenset(item.option_ids)
        if not option_ids <= {option.id for option in question.options}:
            raise InvalidAnswers()
        if question.question_type == "open_text":
            if option_ids:
                raise InvalidAnswers()
        else:
            if item.text:
                raise InvalidAnswers()
            if question.question_type == "single_choice" and len(option_ids) > 1:
                raise InvalidAnswers()
        given[question.id] = StudentAnswer(option_ids=option_ids, text=item.text)

    results = {}
    for question in quiz.questions:
        answer = given.get(question.id, StudentAnswer())
        results[question.id] = (answer, GradingStrategyFactory.for_question(question).grade(question, answer))
    needs_review = any(result.needs_review for _, result in results.values())

    machine.submit(needs_review)
    for question in quiz.questions:
        answer, result = results[question.id]
        attempt_repository.add_answer(
            db,
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_ids=sorted(answer.option_ids),
                text_answer=answer.text,
                is_correct=result.is_correct,
                points_awarded=result.points,
            ),
        )
    attempt.points_total = sum(question.points for question in quiz.questions)

    if not needs_review:
        earned = sum(result.points or 0 for _, result in results.values())
        _finalize(db, attempt, enrollment, earned)

    db.commit()
    return _load_view(db, attempt.id)


def review_attempt(db: Session, attempt_id: int, reviewer: User, data: ReviewRequest) -> dict:
    if attempt_repository.get_for_update(db, attempt_id) is None:
        raise AttemptNotFound()

    attempt = attempt_repository.get_full(db, attempt_id)
    if not can_manage_course(attempt.quiz.module.course, reviewer):
        raise AttemptNotFound()

    machine = AttemptStateMachine(attempt)
    if not machine.accepts_review():
        raise InvalidAttemptState()

    questions = {question.id: question for question in attempt.quiz.questions}
    waiting = {answer.question_id: answer for answer in attempt.answers if answer.points_awarded is None}
    grades = {grade.question_id: grade for grade in data.grades}

    if set(grades) != set(waiting):
        raise InvalidReview()
    for question_id, grade in grades.items():
        if grade.points > questions[question_id].points:
            raise InvalidReview()

    for question_id, grade in grades.items():
        answer = waiting[question_id]
        answer.points_awarded = grade.points
        answer.is_correct = grade.points == questions[question_id].points
        answer.teacher_comment = grade.comment
    machine.grade()

    enrollment = enrollment_repository.get_by_id_for_update(db, attempt.enrollment_id)
    earned = sum(answer.points_awarded or 0 for answer in attempt.answers)
    _finalize(db, attempt, enrollment, earned)

    db.commit()
    return _load_view(db, attempt.id)


def pending_reviews(db: Session, reviewer: User) -> list[dict]:
    teacher_id = None if reviewer.role == "admin" else reviewer.id
    return [
        {
            "attempt_id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "quiz_title": attempt.quiz.title,
            "course_id": attempt.quiz.module.course_id,
            "course_title": attempt.quiz.module.course.title,
            "student": attempt.enrollment.student,
            "submitted_at": attempt.submitted_at,
        }
        for attempt in attempt_repository.list_pending_review(db, teacher_id)
    ]


def get_attempt(db: Session, attempt_id: int, viewer: User) -> dict:
    attempt = attempt_repository.get_full(db, attempt_id)
    is_owner = attempt is not None and attempt.enrollment.student_id == viewer.id
    if attempt is None or not (is_owner or can_manage_course(attempt.quiz.module.course, viewer)):
        raise AttemptNotFound()
    return _attempt_view(attempt)


def list_my_attempts(db: Session, quiz_id: int, student: User) -> list[QuizAttempt]:
    quiz = quiz_repository.get_quiz(db, quiz_id)
    if quiz is None:
        raise QuizNotFound()
    enrollment = enrollment_repository.get_by_student_and_course(db, student.id, quiz.module.course_id)
    if enrollment is None:
        raise QuizAccessDenied()
    return attempt_repository.list_for_enrollment(db, enrollment.id, quiz.id)
