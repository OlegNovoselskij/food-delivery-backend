from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress, pending_review, graded
    score = Column(Integer)
    passed = Column(Boolean)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))

    enrollment = relationship("Enrollment", back_populates="attempts")
    quiz = relationship("Quiz")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("answer_options.id", ondelete="SET NULL"))
    text_answer = Column(Text)
    is_correct = Column(Boolean)
    points_awarded = Column(Integer)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question")
    selected_option = relationship("AnswerOption")