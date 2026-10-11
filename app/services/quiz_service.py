from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import InvalidQuestion, QuizAlreadyExists, QuizHasAttempts
from app.models.quiz import AnswerOption, Question, Quiz
from app.models.user import User
from app.repository import quiz_repository
from app.schemas.quiz import QuestionIn, QuizCreate, QuizUpdate
from app.services.access import get_module_for_edit, get_question_for_edit, get_quiz_for_edit
from app.services.ordering import apply_order


def _manage_view(db: Session, quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "module_id": quiz.module_id,
        "title": quiz.title,
        "passing_score": quiz.passing_score,
        "max_attempts": quiz.max_attempts,
        "has_attempts": quiz_repository.has_attempts(db, quiz.id),
        "total_points": sum(question.points for question in quiz.questions),
        "questions": quiz.questions,
    }


def _fresh_view(db: Session, quiz_id: int) -> dict:
    return _manage_view(db, quiz_repository.get_quiz(db, quiz_id))


def create_quiz(db: Session, module_id: int, user: User, data: QuizCreate) -> dict:
    module = get_module_for_edit(db, module_id, user)
    if module.quiz is not None:
        raise QuizAlreadyExists()
    quiz = Quiz(module_id=module.id, **data.model_dump())
    try:
        quiz_repository.add(db, quiz)
        db.commit()
    except IntegrityError:  # parallel requests: the unique constraint lets only one through
        db.rollback()
        raise QuizAlreadyExists()
    return _fresh_view(db, quiz.id)


def get_quiz_manage(db: Session, quiz_id: int, user: User) -> dict:
    return _manage_view(db, get_quiz_for_edit(db, quiz_id, user))


def update_quiz(db: Session, quiz_id: int, user: User, data: QuizUpdate) -> dict:
    quiz = get_quiz_for_edit(db, quiz_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(quiz, field, value)
    db.commit()
    return _fresh_view(db, quiz_id)


def delete_quiz(db: Session, quiz_id: int, user: User) -> None:
    quiz = get_quiz_for_edit(db, quiz_id, user)
    if quiz_repository.has_attempts(db, quiz.id):
        raise QuizHasAttempts()
    quiz_repository.delete(db, quiz)
    db.commit()


def add_question(db: Session, quiz_id: int, user: User, data: QuestionIn) -> Question:
    quiz = get_quiz_for_edit(db, quiz_id, user)
    question = Question(
        quiz_id=quiz.id,
        text=data.text,
        question_type=data.question_type,
        points=data.points,
        explanation=data.explanation,
        position=quiz_repository.next_question_position(db, quiz.id),
    )
    question.options = [AnswerOption(text=o.text, is_correct=o.is_correct) for o in data.options]
    quiz_repository.add(db, question)
    db.commit()
    return quiz_repository.get_question(db, question.id)


def update_question(db: Session, question_id: int, user: User, data: QuestionIn) -> Question:
    question = get_question_for_edit(db, question_id, user)
    existing = {option.id: option for option in question.options}

    incoming_ids = [option.id for option in data.options if option.id is not None]
    if not set(incoming_ids) <= set(existing):
        raise InvalidQuestion()

    if quiz_repository.has_attempts(db, question.quiz_id):
        same_grading = (
            data.question_type == question.question_type
            and data.points == question.points
            and len(incoming_ids) == len(data.options)
            and set(incoming_ids) == set(existing)
            and all(option.is_correct == existing[option.id].is_correct for option in data.options)
        )
        if not same_grading:
            raise QuizHasAttempts()

    question.text = data.text
    question.question_type = data.question_type
    question.points = data.points
    question.explanation = data.explanation

    options = []
    for option_in in data.options:
        if option_in.id is None:
            options.append(AnswerOption(text=option_in.text, is_correct=option_in.is_correct))
        else:
            option = existing[option_in.id]
            option.text = option_in.text
            option.is_correct = option_in.is_correct
            options.append(option)
    question.options = options  # options missing from the list are deleted (delete-orphan)

    db.commit()
    return quiz_repository.get_question(db, question_id)


def delete_question(db: Session, question_id: int, user: User) -> None:
    question = get_question_for_edit(db, question_id, user)
    if quiz_repository.has_attempts(db, question.quiz_id):
        raise QuizHasAttempts()
    quiz_repository.delete(db, question)
    db.commit()


def reorder_questions(db: Session, quiz_id: int, user: User, ids: list[int]) -> dict:
    quiz = get_quiz_for_edit(db, quiz_id, user)
    apply_order(list(quiz.questions), ids)
    db.commit()
    return _fresh_view(db, quiz_id)
