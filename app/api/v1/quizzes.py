from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_current_user, require_role
from app.models.user import User
from app.schemas.curriculum import OrderUpdate
from app.schemas.quiz import (
    AttemptOut,
    AttemptSummaryOut,
    PendingReviewOut,
    QuestionIn,
    QuestionManageOut,
    QuizCreate,
    QuizManageOut,
    QuizUpdate,
    ReviewRequest,
    SubmitRequest,
)
from app.services import attempt_service, quiz_service

router = APIRouter(tags=["quizzes"])

staff_only = require_role("teacher", "admin")


@router.post("/modules/{module_id}/quiz", response_model=QuizManageOut, status_code=status.HTTP_201_CREATED)
def create_quiz(module_id: int, data: QuizCreate, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return quiz_service.create_quiz(db, module_id, user, data)


@router.get("/quizzes/{quiz_id}/manage", response_model=QuizManageOut)
def get_quiz_manage(quiz_id: int, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return quiz_service.get_quiz_manage(db, quiz_id, user)


@router.patch("/quizzes/{quiz_id}", response_model=QuizManageOut)
def update_quiz(quiz_id: int, data: QuizUpdate, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return quiz_service.update_quiz(db, quiz_id, user, data)


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(quiz_id: int, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    quiz_service.delete_quiz(db, quiz_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/quizzes/{quiz_id}/questions", response_model=QuestionManageOut, status_code=status.HTTP_201_CREATED)
def add_question(quiz_id: int, data: QuestionIn, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return quiz_service.add_question(db, quiz_id, user, data)


@router.put("/quizzes/{quiz_id}/questions/order", response_model=QuizManageOut)
def reorder_questions(quiz_id: int, data: OrderUpdate, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return quiz_service.reorder_questions(db, quiz_id, user, data.ids)


@router.put("/questions/{question_id}", response_model=QuestionManageOut)
def update_question(
    question_id: int, data: QuestionIn, user: User = Depends(staff_only), db: Session = Depends(get_db)
):
    return quiz_service.update_question(db, question_id, user, data)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    quiz_service.delete_question(db, question_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reviews/pending", response_model=list[PendingReviewOut])
def pending_reviews(user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return attempt_service.pending_reviews(db, user)


@router.post("/attempts/{attempt_id}/review", response_model=AttemptOut)
def review_attempt(
    attempt_id: int, data: ReviewRequest, user: User = Depends(staff_only), db: Session = Depends(get_db)
):
    return attempt_service.review_attempt(db, attempt_id, user, data)


@router.post("/quizzes/{quiz_id}/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def start_attempt(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return attempt_service.start_attempt(db, quiz_id, user)


@router.get("/quizzes/{quiz_id}/my-attempts", response_model=list[AttemptSummaryOut])
def my_attempts(quiz_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return attempt_service.list_my_attempts(db, quiz_id, user)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def get_attempt(attempt_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return attempt_service.get_attempt(db, attempt_id, user)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptOut)
def submit_attempt(
    attempt_id: int, data: SubmitRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return attempt_service.submit_attempt(db, attempt_id, user, data)
